import socket
from dataclasses import dataclass
from typing import Optional


class SCPIError(RuntimeError):
    pass


@dataclass
class F4TSCPI:
    host: str = "192.168.0.100"
    port: int = 5025  # SCPI over Ethernet port 5025 per Watlow manual
    timeout_s: float = 2.0
    recv_bytes: int = 4096
    eol: str = "\n"

    _sock: Optional[socket.socket] = None

    def connect(self) -> None:
        """Open a TCP connection to the F4T SCPI port."""
        if self._sock:
            return
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(self.timeout_s)
        s.connect((self.host, self.port))
        self._sock = s

    def close(self) -> None:
        """Close the TCP connection."""
        if self._sock:
            try:
                self._sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            self._sock.close()
            self._sock = None

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()

    def _send_line(self, line: str) -> None:
        if not self._sock:
            raise SCPIError("Socket not connected. Call connect() first.")
        payload = (line + self.eol).encode("ascii", errors="strict")
        self._sock.sendall(payload)

    def write(self, cmd: str) -> None:
        """
        Send a SCPI command that does NOT return data.
        Example: ':SOURce:CLOop1:SPOint 75'
        """
        self._send_line(cmd.strip())

    def query(self, cmd: str) -> str:
        """
        Send a SCPI query and return the response as a string.
        Example: '*IDN?'
        """
        cmd = cmd.strip()
        if not cmd.endswith("?"):
            raise ValueError("query() expects a SCPI query ending with '?'")
        self._send_line(cmd)

        # Many SCPI devices terminate responses with newline.
        # We'll read until newline or until timeout.
        if not self._sock:
            raise SCPIError("Socket not connected.")
        chunks: list[bytes] = []
        while True:
            data = self._sock.recv(self.recv_bytes)
            if not data:
                break
            chunks.append(data)
            if b"\n" in data or b"\r" in data:
                break

        resp = b"".join(chunks).decode("ascii", errors="replace").strip()
        return resp

    # --- Convenience methods for common F4T operations ---

    def idn(self) -> str:
        """Read identification string."""
        return self.query("*IDN?")

    def get_pv(self, loop: int = 1) -> float:
        """
        Read process value (PV) for control loop #.
        SCPI: :SOURce:CLOop#:PVALue?
        """
        resp = self.query(f":SOURce:CLOop{loop}:PVALue?")
        return float(resp)

    def get_sp(self, loop: int = 1) -> float:
        """
        Read setpoint (SP) for control loop #.
        SCPI: :SOURce:CLOop#:SPOint?
        """
        resp = self.query(f":SOURce:CLOop{loop}:SPOint?")
        return float(resp)

    def set_sp(self, value: float, loop: int = 1) -> None:
        """
        Write setpoint (SP) for control loop #.
        SCPI: :SOURce:CLOop#:SPOint <value>
        """
        # Keep formatting simple; F4T accepts ASCII numeric values.
        self.write(f":SOURce:CLOop{loop}:SPOint {value}")

    def get_error(self, loop: int = 1) -> float:
        """
        Read input error for control loop #.
        SCPI: :SOURce:CLOop#:ERRor?
        """
        resp = self.query(f":SOURce:CLOop{loop}:ERRor?")
        return float(resp)


if __name__ == "__main__":
    # Example usage:
    with F4TSCPI(host="192.168.0.100") as f4t:
        print("IDN:", f4t.idn())
        print("PV loop1:", f4t.get_pv(1))
        print("SP loop1:", f4t.get_sp(1))

        # Set SP to 10 (units depend on your loop configuration)
        #f4t.set_sp(10, loop=1)
        #print("SP loop1 after set:", f4t.get_sp(1))
