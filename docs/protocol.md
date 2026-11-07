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
| `ESC ! ?` | `00` | status byte, see below |
| `ESC ! o` | `00 0c 01 12 03 00 03 01 12 12 15 28 0f 0e ed 03` | byte 0 = status byte; bytes 2–13 are all zero while no roll is detected, so they likely carry the roll (RFID) info; last 2 bytes vary; rest *unknown* |
| `BATTERY?` | `BATTERY 75 00 \r\n` | battery, raw bytes after the space (*encoding unknown*) |
| `CONFIG?` | `CONFIG 00 cb 00 00 03 04 02 04 02 00 \r\n` | `00 cb` = 203 dpi; rest *unknown* |
| `~!T`, `~!I`, `~!@` | – | no reply |

### Status byte (`ESC ! ?`)

Observed values:

| Value | Observed when | LED |
|---|---|---|
| `00` | ready, roll detected – prints fine | green |
| `01` | lid open, or roll not detected after pulling paper out | red, beeps |
| `04` | paper error (roll misaligned); print jobs are silently ignored | – |

Matches standard TSPL (`0x01` head open, `0x04` out of paper). A power cycle
cleared the error state after re-seating the roll.

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
- Bitmap rows are MSB-first; a `0` bit prints black (**confirmed**).
- **Confirmed on 14×40 mm labels:** the job above with a 96×320 bitmap prints
  the full label, centred (≈1 mm unprinted margin on each long side), correct
  orientation with `DIRECTION 1,1`, no extra label fed.
- The printer sends no reply to a print job.
- `FORMFEED` gets no reply (feed effect not yet verified).
