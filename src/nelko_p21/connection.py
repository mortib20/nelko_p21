"""Bluetooth Classic (RFCOMM / Serial Port Profile) transport for the P21.

The printer exposes exactly one service, the Serial Port Profile on RFCOMM
channel 1. Desktop Bluetooth managers (e.g. KDE's bluedevil) report
"No more profiles to connect to" because they do not auto-connect SPP; that
is harmless. We open the RFCOMM socket ourselves, no `rfcomm bind` needed.
"""

from __future__ import annotations

import errno
import re
import socket
import subprocess
import time

RFCOMM_CHANNEL = 1


def find_paired_printer(name_prefix: str = "P21") -> str | None:
    """Return the MAC address of a paired device whose name starts with `name_prefix`."""
    try:
        out = subprocess.run(
            ["bluetoothctl", "devices", "Paired"],
            capture_output=True, text=True, timeout=10,
        ).stdout
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    for line in out.splitlines():
        m = re.match(r"Device ([0-9A-F:]{17}) (.+)", line.strip(), re.I)
        if m and m.group(2).startswith(name_prefix):
            return m.group(1)
    return None


class P21Connection:
    def __init__(self, address: str, channel: int = RFCOMM_CHANNEL, timeout: float = 10.0):
        self.address = address
        self.channel = channel
        self.timeout = timeout
        self.sock: socket.socket | None = None

    def __enter__(self) -> "P21Connection":
        self.open()
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def open(self, retries: int = 15) -> None:
        # Reconnecting right after a close fails with EBUSY until the
        # previous RFCOMM link is torn down (or while the printer is still
        # busy printing), so retry for a while.
        for attempt in range(retries):
            s = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
            s.settimeout(self.timeout)
            try:
                s.connect((self.address, self.channel))
            except OSError as e:
                s.close()
                if e.errno != errno.EBUSY or attempt == retries - 1:
                    raise
                time.sleep(1.0)
                continue
            self.sock = s
            return

    def close(self) -> None:
        if self.sock:
            self.sock.close()
            self.sock = None

    def send(self, data: bytes) -> None:
        assert self.sock, "not connected"
        self.sock.sendall(data)

    def read(self, wait: float = 1.0, idle: float = 0.3) -> bytes:
        """Collect whatever the printer sends within `wait` seconds."""
        assert self.sock, "not connected"
        buf = b""
        deadline = time.monotonic() + wait
        while time.monotonic() < deadline:
            self.sock.settimeout(idle)
            try:
                chunk = self.sock.recv(1024)
            except (TimeoutError, socket.timeout):
                if buf:
                    break
                continue
            if not chunk:
                break
            buf += chunk
        self.sock.settimeout(self.timeout)
        return buf

    def query(self, cmd: bytes, wait: float = 1.0) -> bytes:
        self.send(cmd)
        return self.read(wait)

    # --- status ---------------------------------------------------------

    STATUS_READY = 0x00
    STATUS_LID_OPEN = 0x01      # also: roll not detected
    STATUS_PAPER_ERROR = 0x04
    STATUS_BUSY = 0x20          # printing / receiving a job

    def status(self) -> int | None:
        """TSPL status byte (`ESC ! ?`), or None if the printer did not answer."""
        reply = self.query(b"\x1b!?\r\n", wait=1.0)
        return reply[0] if reply else None

    def wait_until_done(self, timeout: float = 60.0, poll: float = 0.5) -> int | None:
        """Poll until the printer leaves the busy state. Returns the final status.

        While rendering a dense image the printer does not answer status
        queries at all, so "no reply" counts as busy too.
        """
        deadline = time.monotonic() + timeout
        st = self.status()
        while st in (self.STATUS_BUSY, None) and time.monotonic() < deadline:
            time.sleep(poll)
            st = self.status()
        return st

    def print_job(self, job: bytes, timeout: float = 60.0) -> int | None:
        """Send a complete job and block until it has been printed.

        Closing the socket right after sendall() truncates the job: the printer
        then sits in status 0x20 (blue LED) waiting for the rest and has to be
        power-cycled. So always wait for it to finish before disconnecting.
        """
        st = self.status()
        if st not in (self.STATUS_READY, None):
            raise PrinterError(st)
        self.send(job)
        time.sleep(1.0)
        return self.wait_until_done(timeout)


class PrinterError(RuntimeError):
    MESSAGES = {
        0x01: "lid open or label roll not detected (re-seat roll, close lid, power-cycle)",
        0x04: "paper error (re-seat the roll; a power-cycle clears it)",
        0x20: "printer busy – still printing a previous job; wait, or power-cycle if it persists",
    }

    def __init__(self, status: int):
        self.status = status
        super().__init__(f"printer status 0x{status:02x}: {self.MESSAGES.get(status, 'unknown state')}")
