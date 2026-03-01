# f4t_scpi.py
import socket
import time
from typing import Optional


class SCPIError(RuntimeError):
    pass


class F4TSCPI:
    """
    Watlow F4T SCPI client over Ethernet (TCP port 5025).  [oai_citation:2‡F4T Setup Operation Manual 16802414 Rev D.pdf](sediment://file_000000004d6871f5a893bf3b0a73265d)

    Implements SCPI commands listed on pages 226–227 (Chapter 6), including:
      - Control loops
      - Cascade loops
      - Units
      - Outputs
      - Profiles (Programs)
      - Soft keys
    """
    import socket
import time

class SCPIError(RuntimeError):
    pass

class F4TSCPI:
    def __init__(self, host, port=5025, timeout=3.0):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.sock = None
        self._rxbuf = b""
        self.last_scpi_error = None

    def connect(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(self.timeout)
        s.connect((self.host, self.port))
        self.sock = s
        self._rxbuf = b""
        self.last_scpi_error = None

    def close(self):
        if self.sock:
            try:
                self.sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            self.sock.close()
            self.sock = None

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()

    def _send(self, cmd: str):
        if not self.sock:
            raise RuntimeError("Not connected")
        # Use CRLF for SCPI
        #print(f"TX: cmd = {cmd}")
        self.sock.sendall((cmd.strip() + "\r\n").encode("ascii"))

    def _readline(self) -> str:
        """Read one raw line (can be empty)."""
        while b"\n" not in self._rxbuf:
            chunk = self.sock.recv(4096)
            if not chunk:
                raise ConnectionError("Socket closed by peer")
            self._rxbuf += chunk

        line, self._rxbuf = self._rxbuf.split(b"\n", 1)
        line = line.strip(b"\r").decode("ascii", errors="replace")
        return line  # may be ""

    def _readline_nonempty(self) -> str:
        """Read next non-empty line; also capture SCPI error lines."""
        while True:
            line = self._readline().strip()
            #print(f"while loop line from self._readline() {line} ")
            if not line:
                continue
            if line.startswith("Inbound SCPI ERROR:"):
                self.last_scpi_error = line
                # Keep reading so queries still return their real data
                continue
            return line

    def write(self, cmd: str):
        # IMPORTANT: writes do not read
        self._send(cmd)
        time.sleep(0.2)

    def query(self, cmd: str) -> str:
        if not cmd.strip().endswith("?"):
            raise ValueError("Query must end with '?'")
        self._send(cmd)
        return self._readline_nonempty()

    #def __init__(self, host="192.168.0.100", port=5025, timeout=3.0, recv_bytes=4096):
    #    self.host = host
    #    self.port = port
    #    self.timeout = timeout
    #    self.recv_bytes = recv_bytes
    #    self.sock: Optional[socket.socket] = None

    ## ---------------- connection ----------------
    #def connect(self) -> None:
    #    if self.sock:
    #        return
    #    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    #    s.settimeout(self.timeout)
    #    s.connect((self.host, self.port))
    #    self.sock = s

    #def close(self) -> None:
    #    if self.sock:
    #        try:
    #            self.sock.shutdown(socket.SHUT_RDWR)
    #        except OSError:
    #            pass
    #        self.sock.close()
    #        self.sock = None

    #def __enter__(self):
    #    self.connect()
    #    return self

    #def __exit__(self, exc_type, exc, tb):
    #    self.close()

    ## ---------------- low-level I/O ----------------
    #def _send(self, msg: str) -> None:
    #    if not self.sock:
    #        raise SCPIError("Not connected. Call connect() first.")
    #    self.sock.sendall((msg.strip() + "\n").encode("ascii", errors="strict"))

    #def write(self, cmd: str) -> None:
    #    """Send a SCPI command that does not return data."""
    #    print("TX:", cmd)
    #    self._send(cmd)

    #def query(self, cmd: str) -> str:
    #    """Send a SCPI query and return a single-line response."""
    #    cmd = cmd.strip()
    #    if not cmd.endswith("?"):
    #        raise ValueError("Query must end with '?'")
    #    self._send(cmd)

    #    if not self.sock:
    #        raise SCPIError("Not connected.")

    #    chunks = []
    #    while True:
    #        data = self.sock.recv(self.recv_bytes)
    #        print("query data ", data)
    #        if not data:
    #            break
    #        chunks.append(data)
    #        if b"\n" in data or b"\r" in data:
    #            break
    #    return b"".join(chunks).decode("ascii", errors="replace").strip()
    #def query(self, cmd: str) -> str:
    #    cmd = cmd.strip()
    #    if not cmd.endswith("?"):
    #        raise ValueError("Query must end with '?'")

    #    # Send with CRLF (SCPI safest)
    #    self.sock.sendall((cmd + "\r\n").encode("ascii"))

    #    # Read until we get a NON-empty line
    #    buf = b""
    #    while True:
    #        chunk = self.sock.recv(4096)
    #        if not chunk:
    #            raise ConnectionError("Socket closed by peer")
    #        print("query data ",chunk)
    #        buf += chunk

    #        # SCPI responses are line-based. Split on either \n or \r\n.
    #        if b"\n" in buf:
    #            line, buf = buf.split(b"\n", 1)  # keep remainder for later? (see note)
    #            line = line.strip(b"\r")         # remove CR if present
    #            if line.strip():                 # <-- skip empty lines
    #                return line.decode("ascii", errors="replace").strip()
    #            # else: it was blank line, keep waiting for the next line
    #            # continue

    # ---------------- helpers ----------------
    @staticmethod
    def _loop(loop: int) -> str:
        if not isinstance(loop, int) or loop < 1:
            raise ValueError("loop must be int >= 1")
        return f":SOURce:CLOop{loop}:"

    @staticmethod
    def _cascade(cas: int) -> str:
        if not isinstance(cas, int) or cas < 1:
            raise ValueError("cascade must be int >= 1")
        return f":SOURce:CAScade{cas}:"

    @staticmethod
    def _output(n: int) -> str:
        if not isinstance(n, int) or n < 1:
            raise ValueError("output must be int >= 1")
        return f":OUTPut{n}:"

    @staticmethod
    def _key(n: int) -> str:
        if not isinstance(n, int) or n < 1:
            raise ValueError("key must be int >= 1")
        return f":KEY{n}"

    # ---------------- Standard ----------------
    def idn(self) -> str:
        # *IDN?  [oai_citation:3‡F4T Setup Operation Manual 16802414 Rev D.pdf](sediment://file_000000004d6871f5a893bf3b0a73265d)
        return self.query("*IDN?")

    # ============================================================
    # Control loop commands (page 226)
    # ============================================================
    def get_pv(self, loop: int = 1) -> float:
        # :SOURce:CLOop#:PVALue?  [oai_citation:4‡F4T Setup Operation Manual 16802414 Rev D.pdf](sediment://file_000000004d6871f5a893bf3b0a73265d)
        return float(self.query(self._loop(loop) + "PVALue?"))

    def get_sp(self, loop: int = 1) -> float:
        # :SOURce:CLOop#:SPOint?  [oai_citation:5‡F4T Setup Operation Manual 16802414 Rev D.pdf](sediment://file_000000004d6871f5a893bf3b0a73265d)
        return float(self.query(self._loop(loop) + "SPOint?"))

    def set_sp(self, value: float, loop: int = 1) -> None:
        # :SOURce:CLOop#:SPOint <value>  [oai_citation:6‡F4T Setup Operation Manual 16802414 Rev D.pdf](sediment://file_000000004d6871f5a893bf3b0a73265d)
        self.write(self._loop(loop) + f"SPOint {value}")

    def get_ramp_time(self, loop: int = 1) -> float:
        # :SOURce:CLOop#:RTIMe?  [oai_citation:7‡F4T Setup Operation Manual 16802414 Rev D.pdf](sediment://file_000000004d6871f5a893bf3b0a73265d)
        return float(self.query(self._loop(loop) + "RTIMe?"))

    def set_ramp_time(self, value: float, loop: int = 1) -> None:
        # :SOURce:CLOop#:RTIMe <numeric value>  [oai_citation:8‡F4T Setup Operation Manual 16802414 Rev D.pdf](sediment://file_000000004d6871f5a893bf3b0a73265d)
        self.write(self._loop(loop) + f"RTIMe {value}")

    def set_ramp_scale_minutes(self, loop: int = 1) -> None:
        # :SOURce:CLOop#:RSCAle MINutes  [oai_citation:9‡F4T Setup Operation Manual 16802414 Rev D.pdf](sediment://file_000000004d6871f5a893bf3b0a73265d)
        self.write(self._loop(loop) + "RSCAle MINutes")

    def set_ramp_scale_hours(self, loop: int = 1) -> None:
        # :SOURce:CLOop#:RSCAle HOURS  [oai_citation:10‡F4T Setup Operation Manual 16802414 Rev D.pdf](sediment://file_000000004d6871f5a893bf3b0a73265d)
        self.write(self._loop(loop) + "RSCAle HOURS")

    def get_ramp_rate(self, loop: int = 1) -> float:
        # :SOURce:CLOop#:RRATe?  [oai_citation:11‡F4T Setup Operation Manual 16802414 Rev D.pdf](sediment://file_000000004d6871f5a893bf3b0a73265d)
        return float(self.query(self._loop(loop) + "RRATe?"))

    def set_ramp_rate(self, value: float, loop: int = 1) -> None:
        # :SOURce:CLOop#:RRATe <numericvalue>  [oai_citation:12‡F4T Setup Operation Manual 16802414 Rev D.pdf](sediment://file_000000004d6871f5a893bf3b0a73265d)
        self.write(self._loop(loop) + f"RRATe {value}")

    # ramp action
    def set_ramp_action_off(self, loop: int = 1) -> None:
        # :SOURce:CLOop#:RACTion OFF  [oai_citation:13‡F4T Setup Operation Manual 16802414 Rev D.pdf](sediment://file_000000004d6871f5a893bf3b0a73265d)
        self.write(self._loop(loop) + "RACTion OFF")

    def set_ramp_action_startup(self, loop: int = 1) -> None:
        self.write(self._loop(loop) + "RACTion STArtup")

    def set_ramp_action_setpoint(self, loop: int = 1) -> None:
        self.write(self._loop(loop) + "RACTion SETPoint")

    def set_ramp_action_both(self, loop: int = 1) -> None:
        self.write(self._loop(loop) + "RACTion BOTH")

    def get_error(self, loop: int = 1) -> float:
        # :SOURce:CLOop#:ERRor?  [oai_citation:14‡F4T Setup Operation Manual 16802414 Rev D.pdf](sediment://file_000000004d6871f5a893bf3b0a73265d)
        return float(self.query(self._loop(loop) + "ERRor?"))

    def get_idle(self, loop: int = 1) -> float:
        # :SOURce:CLOop#:IDLE?  [oai_citation:15‡F4T Setup Operation Manual 16802414 Rev D.pdf](sediment://file_000000004d6871f5a893bf3b0a73265d)
        return float(self.query(self._loop(loop) + "IDLE?"))

    def set_idle(self, value: float, loop: int = 1) -> None:
        # :SOURce:CLOop#:IDLE <numeric value>  [oai_citation:16‡F4T Setup Operation Manual 16802414 Rev D.pdf](sediment://file_000000004d6871f5a893bf3b0a73265d)
        self.write(self._loop(loop) + f"IDLE {value}")

    # ============================================================
    # Cascade loop commands (pages 226–227)
    # ============================================================
    def cascade_get_sp(self, cas: int = 1) -> float:
        # :SOURce:CAScade#:SPOint?  [oai_citation:17‡F4T Setup Operation Manual 16802414 Rev D.pdf](sediment://file_000000004d6871f5a893bf3b0a73265d)
        return float(self.query(self._cascade(cas) + "SPOint?"))

    def cascade_set_sp(self, value: float, cas: int = 1) -> None:
        # :SOURce:CAScade#:SPOint <numeric value>  [oai_citation:18‡F4T Setup Operation Manual 16802414 Rev D.pdf](sediment://file_000000004d6871f5a893bf3b0a73265d)
        self.write(self._cascade(cas) + f"SPOint {value}")

    def cascade_get_outer_pv(self, cas: int = 1) -> float:
        # :SOURce:CAScade#:OUTer:PVALue?  [oai_citation:19‡F4T Setup Operation Manual 16802414 Rev D.pdf](sediment://file_000000004d6871f5a893bf3b0a73265d)
        return float(self.query(self._cascade(cas) + "OUTer:PVALue?"))

    def cascade_get_outer_error(self, cas: int = 1) -> float:
        # :SOURce:CAScade#:OUTer:ERRor?  [oai_citation:20‡F4T Setup Operation Manual 16802414 Rev D.pdf](sediment://file_000000004d6871f5a893bf3b0a73265d)
        return float(self.query(self._cascade(cas) + "OUTer:ERRor?"))

    def cascade_get_inner_pv(self, cas: int = 1) -> float:
        # :SOURce:CAScade#:INNer:PVALue?  [oai_citation:21‡F4T Setup Operation Manual 16802414 Rev D.pdf](sediment://file_000000004d6871f5a893bf3b0a73265d)
        return float(self.query(self._cascade(cas) + "INNer:PVALue?"))

    def cascade_get_inner_error(self, cas: int = 1) -> float:
        # :SOURce:CAScade#:INNer:ERRor?  [oai_citation:22‡F4T Setup Operation Manual 16802414 Rev D.pdf](sediment://file_000000004d6871f5a893bf3b0a73265d)
        return float(self.query(self._cascade(cas) + "INNer:ERRor?"))

    def cascade_get_outer_sp(self, cas: int = 1) -> float:
        # :SOURce:CAScade#:OUTer:SPOint?  [oai_citation:23‡F4T Setup Operation Manual 16802414 Rev D.pdf](sediment://file_000000004d6871f5a893bf3b0a73265d)
        return float(self.query(self._cascade(cas) + "OUTer:SPOint?"))

    def cascade_get_inner_sp(self, cas: int = 1) -> float:
        # :SOURce:CAScade#:INNer:SPOint?  [oai_citation:24‡F4T Setup Operation Manual 16802414 Rev D.pdf](sediment://file_000000004d6871f5a893bf3b0a73265d)
        return float(self.query(self._cascade(cas) + "INNer:SPOint?"))

    def cascade_get_function(self, cas: int = 1) -> str:
        # :SOURce:CAScade#:FUNCtion?  [oai_citation:25‡F4T Setup Operation Manual 16802414 Rev D.pdf](sediment://file_000000004d6871f5a893bf3b0a73265d)
        return self.query(self._cascade(cas) + "FUNCtion?")

    def cascade_set_function_process(self, cas: int = 1) -> None:
        # :SOURce:CAScade#:FUNCtion PROCESS  [oai_citation:26‡F4T Setup Operation Manual 16802414 Rev D.pdf](sediment://file_000000004d6871f5a893bf3b0a73265d)
        self.write(self._cascade(cas) + "FUNCtion PROCESS")

    def cascade_set_function_deviation(self, cas: int = 1) -> None:
        # :SOURce:CAScade#:FUNCtion DEVIATION  [oai_citation:27‡F4T Setup Operation Manual 16802414 Rev D.pdf](sediment://file_000000004d6871f5a893bf3b0a73265d)
        self.write(self._cascade(cas) + "FUNCtion DEVIATION")

    def cascade_get_range_low(self, cas: int = 1) -> float:
        # :SOURce:CAScade#:RANGe:LOW?  [oai_citation:28‡F4T Setup Operation Manual 16802414 Rev D.pdf](sediment://file_000000004d6871f5a893bf3b0a73265d)
        return float(self.query(self._cascade(cas) + "RANGe:LOW?"))

    def cascade_set_range_low(self, value: float, cas: int = 1) -> None:
        # :SOURce:CAScade#:RANGe:LOW <numericvalue>  [oai_citation:29‡F4T Setup Operation Manual 16802414 Rev D.pdf](sediment://file_000000004d6871f5a893bf3b0a73265d)
        self.write(self._cascade(cas) + f"RANGe:LOW {value}")

    def cascade_get_range_high(self, cas: int = 1) -> float:
        # :SOURce:CAScade#:RANGe:HIGH?  [oai_citation:30‡F4T Setup Operation Manual 16802414 Rev D.pdf](sediment://file_000000004d6871f5a893bf3b0a73265d)
        return float(self.query(self._cascade(cas) + "RANGe:HIGH?"))

    def cascade_set_range_high(self, value: float, cas: int = 1) -> None:
        # :SOURce:CAScade#:RANGe:HIGH <numericvalue>  [oai_citation:31‡F4T Setup Operation Manual 16802414 Rev D.pdf](sediment://file_000000004d6871f5a893bf3b0a73265d)
        self.write(self._cascade(cas) + f"RANGe:HIGH {value}")

    def cascade_get_control(self, cas: int = 1) -> str:
        # :SOURce:CAScade#:CONTrol?  [oai_citation:32‡F4T Setup Operation Manual 16802414 Rev D.pdf](sediment://file_000000004d6871f5a893bf3b0a73265d)
        return self.query(self._cascade(cas) + "CONTrol?")

    def cascade_set_control_off(self, cas: int = 1) -> None:
        self.write(self._cascade(cas) + "CONTrol OFF")

    def cascade_set_control_cool(self, cas: int = 1) -> None:
        self.write(self._cascade(cas) + "CONTrol COOL")

    def cascade_set_control_heat(self, cas: int = 1) -> None:
        self.write(self._cascade(cas) + "CONTrol HEAT")

    def cascade_set_control_both(self, cas: int = 1) -> None:
        self.write(self._cascade(cas) + "CONTrol BOTH")

    def cascade_get_sspoint_control(self, cas: int = 1) -> str:
        # :SOURce:CAScade#:SSPoint:CONTrol?  [oai_citation:33‡F4T Setup Operation Manual 16802414 Rev D.pdf](sediment://file_000000004d6871f5a893bf3b0a73265d)
        return self.query(self._cascade(cas) + "SSPoint:CONTrol?")

    def cascade_set_sspoint_control_off(self, cas: int = 1) -> None:
        self.write(self._cascade(cas) + "SSPoint:CONTrol OFF")

    def cascade_set_sspoint_control_on(self, cas: int = 1) -> None:
        self.write(self._cascade(cas) + "SSPoint:CONTrol ON")

    # ============================================================
    # Units (page 227)
    # ============================================================
    def unit_temperature(self) -> str:
        # :UNIT:TEMPerature?  [oai_citation:34‡F4T Setup Operation Manual 16802414 Rev D.pdf](sediment://file_000000004d6871f5a893bf3b0a73265d)
        return self.query(":UNIT:TEMPerature?")

    def set_unit_temperature_c(self) -> None:
        self.write(":UNIT:TEMPerature C")

    def set_unit_temperature_f(self) -> None:
        self.write(":UNIT:TEMPerature F")

    def unit_temperature_display(self) -> str:
        # :UNIT:TEMPerature:DISPlay?  [oai_citation:35‡F4T Setup Operation Manual 16802414 Rev D.pdf](sediment://file_000000004d6871f5a893bf3b0a73265d)
        return self.query(":UNIT:TEMPerature:DISPlay?")

    def set_unit_temperature_display_c(self) -> None:
        self.write(":UNIT:TEMPerature:DISPlay C")

    def set_unit_temperature_display_f(self) -> None:
        self.write(":UNIT:TEMPerature:DISPlay F")

    # ============================================================
    # Outputs (page 227)
    # ============================================================
    def output_name(self, n: int) -> str:
        # :OUTPut#:NAME?  [oai_citation:36‡F4T Setup Operation Manual 16802414 Rev D.pdf](sediment://file_000000004d6871f5a893bf3b0a73265d)
        return self.query(self._output(n) + "NAME?")

    def output_state(self, n: int) -> str:
        # :OUTPut#:STATe?  [oai_citation:37‡F4T Setup Operation Manual 16802414 Rev D.pdf](sediment://file_000000004d6871f5a893bf3b0a73265d)
        return self.query(self._output(n) + "STATe?")

    def output_off(self, n: int) -> None:
        self.write(self._output(n) + "STATe OFF")

    def output_on(self, n: int) -> None:
        self.write(self._output(n) + "STATe ON")

    # ============================================================
    # Profiles / Programs (page 227)
    # ============================================================
    def program_select_number(self, n: int) -> None:
        # :PROGram:SELected:NUMBer <numeric value>  [oai_citation:38‡F4T Setup Operation Manual 16802414 Rev D.pdf](sediment://file_000000004d6871f5a893bf3b0a73265d)
        self.write(f":PROGram:SELected:NUMBer {n}")

    def program_selected_name(self) -> str:
        # :PROGram:SELected:NAME?  [oai_citation:39‡F4T Setup Operation Manual 16802414 Rev D.pdf](sediment://file_000000004d6871f5a893bf3b0a73265d)
        return self.query(":PROGram:SELected:NAME?")

    def program_set_step(self, step: int) -> None:
        self.write(f":PROGram:SELected:STEP {step}")

    def program_start(self) -> None:
        self.write(":PROGram:SELected:STATe STArt")

    def program_pause(self) -> None:
        self.write(":PROGram:SELected:STATe PAUSe")

    def program_resume(self) -> None:
        self.write(":PROGram:SELected:STATe RESume")

    def program_stop(self) -> None:
        self.write(":PROGram:SELected:STATe STOP")

    def program_number(self) -> int:
        # :PROGram[:SELected]:NUMBer?  [oai_citation:40‡F4T Setup Operation Manual 16802414 Rev D.pdf](sediment://file_000000004d6871f5a893bf3b0a73265d)
        return int(float(self.query(":PROGram:NUMBer?")))

    def program_state(self) -> str:
        # :PROGram[:SELected]:STATe?  [oai_citation:41‡F4T Setup Operation Manual 16802414 Rev D.pdf](sediment://file_000000004d6871f5a893bf3b0a73265d)
        return self.query(":PROGram:STATe?")

    def program_spoint(self, sp_index: int) -> str:
        # :PROGram[:SELected]:SPOint#?  [oai_citation:42‡F4T Setup Operation Manual 16802414 Rev D.pdf](sediment://file_000000004d6871f5a893bf3b0a73265d)
        return self.query(f":PROGram:SPOint{sp_index}?")

    def program_step(self) -> int:
        # :PROGram[:SELected]:STEP?  [oai_citation:43‡F4T Setup Operation Manual 16802414 Rev D.pdf](sediment://file_000000004d6871f5a893bf3b0a73265d)
        return int(float(self.query(":PROGram:STEP?")))

    def program_step_type(self) -> str:
        # :PROGram[:SELected]:STEP:TYPE?  [oai_citation:44‡F4T Setup Operation Manual 16802414 Rev D.pdf](sediment://file_000000004d6871f5a893bf3b0a73265d)
        return self.query(":PROGram:STEP:TYPE?")

    def program_step_time_elapsed(self) -> float:
        # :PROGram[:SELected]:STEP:TIME:ELApsed?  [oai_citation:45‡F4T Setup Operation Manual 16802414 Rev D.pdf](sediment://file_000000004d6871f5a893bf3b0a73265d)
        return float(self.query(":PROGram:STEP:TIME:ELApsed?"))

    def program_step_time_remain(self) -> float:
        # :PROGram[:SELected]:STEP:TIME:REMain?  [oai_citation:46‡F4T Setup Operation Manual 16802414 Rev D.pdf](sediment://file_000000004d6871f5a893bf3b0a73265d)
        return float(self.query(":PROGram:STEP:TIME:REMain?"))

    # ============================================================
    # Soft keys (page 227)
    # ============================================================
    def key_state(self, n: int) -> str:
        # :KEY#[:STATe]?  [oai_citation:47‡F4T Setup Operation Manual 16802414 Rev D.pdf](sediment://file_000000004d6871f5a893bf3b0a73265d)
        return self.query(self._key(n) + ":STATe?")

    def key_on(self, n: int) -> None:
        self.write(self._key(n) + ":STATe ON")

    def key_off(self, n: int) -> None:
        self.write(self._key(n) + ":STATe OFF")

    def key_name(self, n: int) -> str:
        # :KEY#:NAME?  [oai_citation:48‡F4T Setup Operation Manual 16802414 Rev D.pdf](sediment://file_000000004d6871f5a893bf3b0a73265d)
        return self.query(self._key(n) + ":NAME?")

import time
if __name__ == "__main__":
    # Example usage:
    with F4TSCPI(host="192.168.0.100") as f4t:
        print("IDN:", f4t.idn())

        print("PV loop1:", f4t.get_pv(1))
        print("SP loop1:", f4t.get_sp(1))

        print("start to ramp to 20C")
        f4t.set_sp(20, loop=1)
        f4t.set_ramp_action_setpoint(loop=1)
        f4t.set_ramp_scale_minutes(loop=1)
        f4t.set_ramp_rate(2, 1) 
        for itest in range(20):
            #time.sleep(1)
            #f4t.set_ramp_action_startup(loop=1)
            print(time.ctime(time.time()), f"{itest} PV loop1:", f4t.get_pv(loop=1))
            print(time.ctime(time.time()), f"{itest} SP loop1:", f4t.get_sp(loop=1))
            time.sleep(15)
            #print("PV loop1:", f4t.get_pv(loop=1))
            #print("SP loop1:", f4t.get_sp(loop=1))

        time.sleep(30)
        # Set SP to 10 (units depend on your loop configuration)
        print("PV loop1:", f4t.get_pv(1))
        print("SP loop1:", f4t.get_sp(1))
        print("start to ramp to 10C")
        f4t.set_sp(10, loop=1)
        f4t.set_ramp_action_setpoint(loop=1)
        f4t.set_ramp_scale_minutes(loop=1)
        f4t.set_ramp_rate(2, 1) 
        for itest in range(20):
            #time.sleep(1)
            #f4t.set_ramp_action_startup(loop=1)
            print(time.ctime(time.time()), f"{itest} PV loop1:", f4t.get_pv(loop=1))
            print(time.ctime(time.time()), f"{itest} SP loop1:", f4t.get_sp(loop=1))
            time.sleep(15)
