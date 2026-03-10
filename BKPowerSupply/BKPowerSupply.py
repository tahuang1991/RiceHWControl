"""
Simplified SCPI Power Supply
Adapted from https://github.com/MatthewNutt5/Cerebellum
By Matthew Nutt, 2026 March
"""
from abc import ABC, abstractmethod
import serial, socketscpi, time, re, logging

SCPI_WRITE_DELAY = 0.1 # default delay after writing an SCPI command, to allow the PSU time to process it before sending another command or a query. Adjust as needed for your specific PSU and communication protocol.



# Config class (simply holds configuration values, like a struct)
class PSUConfig:

    def __init__(self):
        self.protocol           = ""                # Communication protocol (IP / Serial)
        self.IP                 = ""                # IP address
        self.COM                = ""                # COM port (e.g. /dev/ttyACM0, COM1)
        self.baudrate           = 115200            # COM baudrate



# Power supply class (takes a PSUConfig at initialization)
class BKPowerSupply:

    """
    Interface Methods ======================================================
    """

    # Initialize connection, log ID
    def __init__(self, config: PSUConfig):

        self.config = config

        if (self.config.protocol == "Serial"):
            try:
                self.ser = serial.Serial(
                    port=self.config.COM,
                    baudrate=self.config.baudrate,
                    timeout=1.0
                )
                logging.info(f"Opened serial port {self.config.COM}.")
                self.ser.reset_input_buffer()
                self.ser.reset_output_buffer()
            except serial.SerialException as e:
                raise RuntimeError(f"Failed to open serial port {self.config.COM}: {e}")
        elif (self.config.protocol == "IP"):
            try:
                self.socket = socketscpi.SocketInstrument(self.config.IP)
            except socketscpi.SockInstError as e:
                raise RuntimeError(f"Failed to open IP socket {self.config.IP}: {e}")
        else:
            raise ValueError(f"Invalid protocol value: {self.config.protocol}")
        
        logging.info(self.get_id())

    # Attempt to close any open connections when deallocated
    def __del__(self):
        if ("ser" in vars(self)) and self.ser and self.ser.is_open:
            self.ser.close()
            logging.info(f"Closed serial port {self.config.COM}.")
        if ("socket" in vars(self)) and self.socket:
            self.socket.close()
            logging.info(f"Closed IP socket {self.config.IP}.")
    
    # Get any identification data
    def get_id(self):
        IDN = self._query_scpi("*IDN?\n")
        VERS = self._query_scpi("SYST:VERS?\n")
        return f"IDN: {IDN}, SCPI Version: {VERS}"

    # Set the voltage setting of the given channel
    def set_voltage(self, voltage: float, channel: int = 0):
        self._write_scpi(f"INST:SEL {channel}\n")
        self._write_scpi(f"VOLT {voltage}\n")

    # Set the current setting of the given channel
    def set_current(self, current: float, channel: int = 0):
        self._write_scpi(f"INST:SEL {channel}\n")
        self._write_scpi(f"CURR {current}\n")

    # Get the voltage setting of the given channel
    def get_voltage(self, channel: int = 0):
        self._write_scpi(f"INST:SEL {channel}\n")
        return self._parse_float_scpi(self._query_scpi("VOLT?\n"))

    # Get the current setting of the given channel
    def get_current(self, channel: int = 0):
        self._write_scpi(f"INST:SEL {channel}\n")
        return self._parse_float_scpi(self._query_scpi("CURR?\n"))
    
    # Measure the voltage at the given channel
    def measure_voltage(self, channel: int = 0):
        self._write_scpi(f"INST:SEL {channel}\n")
        return self._parse_float_scpi(self._query_scpi("MEAS:VOLT?\n"))
    
    # Measure the current at the given channel
    def measure_current(self, channel: int = 0):
        self._write_scpi(f"INST:SEL {channel}\n")
        return self._parse_float_scpi(self._query_scpi("MEAS:CURR?\n"))
    
    # Measure the power at the given channel
    def measure_power(self, channel: int = 0):
        self._write_scpi(f"INST:SEL {channel}\n")
        return self._parse_float_scpi(self._query_scpi("MEAS:POW?\n"))
    
    # Disable the given channel
    def disable_channel(self, channel: int = 0):
        self._write_scpi(f"INST:SEL {channel}\n")
        self._write_scpi(f"OUTP:STAT 0\n")
    
    # Enable the given channel
    def enable_channel(self, channel: int = 0):
        self._write_scpi(f"INST:SEL {channel}\n")
        self._write_scpi(f"OUTP:STAT 1\n")

    # Return the enable/disable state of the given channel
    def get_channel_state(self, channel: int = 0):
        self._write_scpi(f"INST:SEL {channel}\n")
        return bool(int(self._query_scpi(f"OUTP:STAT?\n")))
    
    # Shutdown all channels
    def shutdown(self):
        self._write_scpi(f"OUTP:ALL 0\n")



    """
    Helper Methods =========================================================
    """

    # Send an SCPI command without reading a response
    def _write_scpi(self, cmd: str):

        if (self.config.protocol == "Serial"):
            if not self.ser or not self.ser.is_open:
                raise RuntimeError(f"Serial port {self.config.COM} is not open.")
            self.ser.reset_input_buffer()
            self.ser.write(cmd.encode())
            self.ser.flush()
        elif (self.config.protocol == "IP"):
            if not self.socket:
                raise RuntimeError(f"IP socket {self.config.IP} is not open.")
            self.socket.write(cmd)
        else:
            raise ValueError(f"Invalid protocol value: {self.config.protocol}")

        time.sleep(SCPI_WRITE_DELAY)

    # Send an SCPI command and return the decoded response
    # Pass to _parse_float_scpi to extract float
    def _query_scpi(self, cmd: str):

        if (self.config.protocol == "Serial"):
            if not self.ser or not self.ser.is_open:
                raise RuntimeError(f"Serial port {self.config.COM} is not open.")
            self.ser.reset_input_buffer()
            self.ser.write(cmd.encode())
            self.ser.flush()
            time.sleep(SCPI_WRITE_DELAY)
            response = self.ser.readline()
            try:
                return response.decode().strip() if response else ""
            except UnicodeDecodeError:
                logging.warning(f"Unreadable response: {response}")
                return ""
        elif (self.config.protocol == "IP"):
            if not self.socket:
                raise RuntimeError(f"IP socket {self.config.IP} is not open.")
            return self.socket.query(cmd)
        else:
            raise ValueError(f"Invalid protocol value: {self.config.protocol}")

    # Extract a float (e.g. voltage) from a decoded SCPI response
    @staticmethod
    def _parse_float_scpi(response: str):
        match = re.search(r"[-+]?\d*\.?\d+", response)
        if not match:
            raise RuntimeError(f"Unable to locate value in response: {response}")
        return float(match.group(0))



# ----------------------------------------------------------------------
# Example usage
# ----------------------------------------------------------------------
if __name__ == "__main__":
    # Configure PSU settings here
    config = PSUConfig()
    config.protocol = "IP" # "IP" for Ethernet, "Serial" for USB
    config.IP = "192.168.0.40"
    #config.COM = "/dev/ttyACM0"

    psu = BKPowerSupply(config)
    PSUChannel = 0 # Set the channel you want to use here!

    # These are no longer necessary, since the PSU will print on its own during startup
    print("Device:", psu.get_id())
    #print("SCPI version:", psu.get_version())

    psu.set_voltage(9.0, PSUChannel) #V
    psu.set_current(5.0, PSUChannel) #A
    print("Voltage setting:", psu.get_voltage(PSUChannel))
    print("Current limit setting:", psu.get_current(PSUChannel))

    out_status = psu.get_channel_state(PSUChannel)
    print(f"output status {out_status}")
    if not out_status:
        psu.enable_channel(PSUChannel)
        time.sleep(2)
        print("Output enabled")

    print(f"BKPS Measured voltage: {psu.measure_voltage(PSUChannel)} V")
    print(f"BKPS Measured current: {psu.measure_current(PSUChannel)} A")
    print(f"BKPS Measured power: {psu.measure_power(PSUChannel)} W")
    measured_current = psu.measure_current(PSUChannel)
    measured_voltage = psu.measure_voltage(PSUChannel)
    measured_power = psu.measure_power(PSUChannel)
    if abs(measured_current*measured_voltage-measured_power) > 0.5:
        print("Power measurement discrepancy detected!")

