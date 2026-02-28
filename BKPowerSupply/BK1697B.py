import serial
import time
from typing import Optional
import re

def fix_BKResponse_list(lst):
    """
    When 49 is found and there are 6 elements after it (instead of 5),
    remove the element immediately following 49.
    """
    i = 0
    while i < len(lst):
        if lst[i] == 46: ## 46 in list is the decimal point
            # Check how many elements come after
            after = len(lst) - (i + 1)
            if after == 6:
                # Remove the element immediately after 49
                removed = lst.pop(i + 1)
                #print(f"Removed element {removed} after index {i} (value 49): {lst}")
                # Only done it once
                break
        i += 1
    return lst

def parse_value(response: bytes) -> Optional[str]:
    """Extracts the first numeric value (float) from a serial response."""
    try:
        if bytes([65]) in response and bytes([46]) in response:#[65] = A; [46] = .
            """bug response for current when it is 1.1 / 2.2 .. : check [65] and [46] in response"""
            #print(f"The bug response {list(response)}")
            res_list = fix_BKResponse_list(list(response))
            #print(f"The fixed response {res_list}")
            response =  bytes(res_list)
        #print(f"parse_value: response={response} ", list(response))
        text = response.decode().strip()  # e.g. '5.00V' or '1.23A'
        #print("parse_value ", text)
        match = re.search(r"[-+]?\d*\.?\d+", text)
        if match:
            return float(match.group(0))
    except Exception as e:
        print(f"Failed to parse value from {response!r}: {e}")
    return -1.0  # or None to indicate failure

class BK1697B:
    """Class to control BK Precision 1697B DC Power Supply via SCPI commands."""
    """Default unit: V for votlage, A for current, and Watt for power."""

    def __init__(self, port: str = '/dev/ttyACM0', baudrate: int = 115200, timeout: float = 1.0):
        """Initialize serial connection."""
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.ser = None

        try:
            self.ser = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                bytesize=serial.EIGHTBITS,
                timeout=self.timeout
            )
            time.sleep(2)  # Wait for connection to establish
            print(f"Connected to {self.port}")
            self.ser.reset_input_buffer()
            self.ser.reset_output_buffer()

        except serial.SerialException as e:
            raise RuntimeError(f"Failed to open serial port {self.port}: {e}")

    # ----------------------------------------------------------------------
    # Internal helper
    # ----------------------------------------------------------------------
    def _query(self, cmd: str, delay: float = 0.1) -> Optional[str]:
        """Send SCPI query and return decoded response."""
        if not self.ser or not self.ser.is_open:
            raise RuntimeError("Serial port is not open.")
        self.ser.reset_input_buffer()
        self.ser.write(cmd.encode())
        self.ser.flush()
        time.sleep(delay)
        response = self.ser.readline()
        try:
            return response.decode('utf-8').strip() if response else None
        except UnicodeDecodeError:
            print("Warning: unreadable response:", response)
            return None

    def _fquery(self, cmd: str, delay: float = 0.1) -> Optional[float]:
        """Send SCPI query and return decoded response as float."""
        if not self.ser or not self.ser.is_open:
            raise RuntimeError("Serial port is not open.")
        self.ser.reset_input_buffer()
        self.ser.write(cmd.encode())
        self.ser.flush()
        time.sleep(delay)
        response = self.ser.readline()
        return parse_value(response)
        
    def _write(self, cmd: str, delay: float = 0.1):
        """Send SCPI command without expecting a response."""
        if not self.ser or not self.ser.is_open:
            raise RuntimeError("Serial port is not open.")
        self.ser.reset_input_buffer()
        self.ser.write(cmd.encode())
        self.ser.flush()
        time.sleep(delay)

    # ----------------------------------------------------------------------
    # Basic commands
    # ----------------------------------------------------------------------
    def get_idn(self):
        return self._query("*IDN?\n")

    def get_version(self):
        return self._query("SYST:VER?\n")

    def set_voltage(self, voltage: float):
        """Set output voltage in Volts."""
        self._write(f"VOLT {voltage:.2f}V\n")

    def set_current(self, current_limit: float):
        """Set output current limit in A."""
        self._write(f"CURR {current_limit:.2f}A\n")

    def get_voltage_setting(self):
        """Return the programmed voltage."""
        return self._fquery("VOLT?\n")

    def get_current_setting(self):
        """Return the programmed voltage."""
        return self._fquery("CURR?\n")

    def measure_voltage(self):
        """Return the measured (actual) output voltage."""
        return self._fquery("MEAS:VOLT?\n")

    def measure_current(self):
        """Return the measured output current."""
        #return self._fquery("MEAS:CURR?\n")
        return self._fquery("MEAS:SCAL:CURR:DC?\n")

    def measure_power(self):
        """Return the measured output power."""
        return self._fquery("MEAS:POW?\n")

    def turnon_output(self):
        """Turn on the power output. 0 for ON and 1 for OFF."""
        self._write("OUTP 0\n")

    def turnoff_output(self):
        """Turn off the power output. 0 for ON and 1 for OFF."""
        self._write("OUTP 1\n")

    def get_output_state(self) -> Optional[bool]:
        """Return True if output is ON. 0 for ON and 1 for OFF."""
        state = self._query("OUTP?\n")
        off = bool(int(state)) if state is not None else True
        return not off # true is ON; false is off

    def set_upperlimit_voltage(self, voltage: float):
        """Set output voltage in Volts."""
        self._write(f"VOLT:LIM {voltage:.2f}V\n")

    def set_upperlimit_current(self, current_limit: float):
        """Set output current limit."""
        self._write(f"CURR:LIM {current_limit:.2f}A\n")

    def get_upperlimit_voltage_setting(self):
        """Return the programmed voltage."""
        return self._fquery("VOLT:LIM?\n")

    def get_upperlimit_current_setting(self):
        """Return the programmed voltage."""
        return self._fquery("CURR:LIM?\n")

    # ----------------------------------------------------------------------
    # Cleanup
    # ----------------------------------------------------------------------
    def close(self):
        """Close the serial port."""
        if self.ser and self.ser.is_open:
            self.ser.close()
            print(f"Closed serial port {self.port}")

    def __del__(self):
        self.close()


# ----------------------------------------------------------------------
# Example usage
# ----------------------------------------------------------------------
if __name__ == "__main__":
    psu = BK1697B('/dev/ttyACM0')

    print("Device:", psu.get_idn())
    #print("SCPI version:", psu.get_version())

    #psu.set_voltage(9.0)
    #psu.set_current(2.5)
    #print("Voltage setting:", psu.get_voltage_setting())
    #print("Current limit setting:", psu.get_current_setting())

    out_status = psu.get_output_state()
    print("output status: ", "ON" if out_status else "OFF")

    if not out_status:
        psu.turnon_output()
        time.sleep(3)
        print("Output enabled")

    print(f"Measured voltage: {psu.measure_voltage()} V")
    print(f"Measured current: {psu.measure_current()} A")
    print(f"Measured power: {psu.measure_power()} W")
    vol = psu.measure_voltage();
    curr = psu.measure_current()
    power = psu.measure_power()
    if abs(vol*curr - power) > 0.05*power:
        print(f"\033[93mWarning: Power measurement discrepancy detected: {vol*curr} vs {power}!\033[0m")

    psu.turnoff_output()
    out_status = psu.get_output_state()
    print("output status before closing: ", "ON" if out_status else "OFF")
    psu.close()
