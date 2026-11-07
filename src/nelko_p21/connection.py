"""Bluetooth Classic (RFCOMM / Serial Port Profile) transport for the P21.

The printer exposes exactly one service, the Serial Port Profile on RFCOMM
channel 1. Desktop Bluetooth managers (e.g. KDE's bluedevil) report
"No more profiles to connect to" because they do not auto-connect SPP; that
is harmless. We open the RFCOMM socket ourselves, no `rfcomm bind` needed.
"""

from __future__ import annotations

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

    def open(self) -> None:
        s = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
        s.settimeout(self.timeout)
        s.connect((self.address, self.channel))
        self.sock = s

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
