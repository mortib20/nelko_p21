# Nelko P21 – protocol notes

Findings from talking to the printer directly. Everything here is
reverse-engineered; treat values marked *unconfirmed* as guesses.

## Transport

- Bluetooth Classic, Serial Port Profile (UUID `00001101-…`), RFCOMM channel 1.
- No BLE needed. Pairing via the desktop Bluetooth settings is enough.
- KDE/bluedevil shows `No more profiles to connect to` after pairing. That is
  expected: SPP is not auto-connected, the driver opens the socket itself.
- Advertised manufacturer data: key `0x7262`, value `32 32 78 78 11 22 33 44 55 66 aa bb 00 00`.

## Command language

TSPL (TSC printer language) dialect. Commands are ASCII lines terminated by `\r\n`.

### Queries

| Command | Example reply | Meaning |
|---|---|---|
| `ESC ! ?` | `04` | TSPL status byte. In standard TSPL `0x04` = out of paper (*unconfirmed for P21*) |
| `ESC ! o` | `04 0c 01 12 03 00 03 01 12 12 15 28 0f 0e 29 06` | *unknown*, 16 bytes |
| `BATTERY?` | `BATTERY 75 00 \r\n` | battery, raw bytes after the space (*encoding unknown*) |
| `CONFIG?` | `CONFIG 00 cb 00 00 03 04 02 04 02 00 \r\n` | `00 cb` = 203 dpi; rest *unknown* |
| `~!T`, `~!I`, `~!@` | – | no reply |

### Printing

```
SIZE 14.0 mm,40.0 mm
GAP 5.0 mm,0 mm
DIRECTION 1,1
DENSITY 15
CLS
BITMAP 0,0,<width_bytes>,<height>,1,<raw bitmap>
PRINT 1
```

- Print head: 96 dots (12 bytes) wide, 203 dpi ≈ 8 dots/mm.
- Bitmap rows are MSB-first; per TSPL a `0` bit prints black.
