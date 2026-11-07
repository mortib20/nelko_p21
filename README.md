# nelko-p21

Unofficial Linux driver / CLI for the **Nelko P21** Bluetooth label printer –
print labels from your PC instead of the phone app.

> Not affiliated with Nelko. Protocol knowledge is reverse-engineered, see
> [docs/protocol.md](docs/protocol.md).

## Status

- [x] Bluetooth connection (RFCOMM / SPP)
- [x] Raw status queries
- [ ] Decoded status (paper, battery, lid)
- [ ] Verified print output

## Setup

1. Pair the printer in your desktop Bluetooth settings (it shows up as `P21`).
   A message like *"No more profiles to connect to"* is expected and harmless.
2. Install:

   ```sh
   uv tool install --python /usr/bin/python3 .   # or: pip install .
   ```

   Use your **system Python**: uv's downloadable standalone Pythons are built
   without Bluetooth socket support (`AttributeError: ... AF_BLUETOOTH`).

## Usage

```sh
nelko-p21 status                         # raw replies of read-only queries
nelko-p21 test --label 14x40             # calibration pattern
nelko-p21 print-text "Hello" --label 14x40
nelko-p21 print-image logo.png
nelko-p21 print-text "Hi" --dry-run --save-preview preview.png
```

The printer is found automatically among paired devices named `P21*`.
Override with `--address AA:BB:CC:DD:EE:FF` or `NELKO_P21_ADDRESS`.

## License

MIT
