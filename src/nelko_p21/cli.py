"""Command line interface: `nelko-p21 status|print-text|print-image|test`."""

from __future__ import annotations

import argparse
import os
import sys

from PIL import Image

from .connection import P21Connection, find_paired_printer
from .render import test_pattern, text_label
from .tspl import LabelSize, build_print_job

# Read-only queries discovered so far (see docs/protocol.md)
QUERIES = {
    "status (ESC !?)": b"\x1b!?\r\n",
    "info (ESC !o)": b"\x1b!o\r\n",
    "battery": b"BATTERY?\r\n",
    "config": b"CONFIG?\r\n",
}


def resolve_address(arg: str | None) -> str:
    addr = arg or os.environ.get("NELKO_P21_ADDRESS") or find_paired_printer()
    if not addr:
        sys.exit("No printer address. Pair the printer, or pass --address / set NELKO_P21_ADDRESS.")
    return addr


def cmd_status(conn: P21Connection, _args) -> None:
    for name, q in QUERIES.items():
        reply = conn.query(q)
        print(f"{name:16} {reply.hex(' ') or '(no reply)'}   {reply!r}")


def _print(conn: P21Connection, img: Image.Image, args) -> None:
    label = LabelSize.parse(args.label)
    if args.save_preview:
        img.save(args.save_preview)
        print(f"preview saved to {args.save_preview}")
    if args.dry_run:
        return
    job = build_print_job(img, label, density=args.density, copies=args.copies)
    conn.send(job)
    reply = conn.read(wait=3.0)
    if reply:
        print(f"printer replied: {reply.hex(' ')}  {reply!r}")
    print("job sent")


def cmd_test(conn, args) -> None:
    _print(conn, test_pattern(LabelSize.parse(args.label)), args)


def cmd_text(conn, args) -> None:
    _print(conn, text_label(args.text, LabelSize.parse(args.label), border=not args.no_border), args)


def cmd_image(conn, args) -> None:
    label = LabelSize.parse(args.label)
    img = Image.open(args.path)
    if img.width > img.height:  # landscape artwork reads along the strip
        img = img.rotate(90, expand=True)
    img.thumbnail((label.width_dots, label.length_dots))
    _print(conn, img, args)


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(prog="nelko-p21", description=__doc__)
    p.add_argument("--address", help="Bluetooth MAC (default: $NELKO_P21_ADDRESS or paired device named P21*)")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("status", help="send read-only queries and show raw replies")

    def print_opts(sp):
        sp.add_argument("--label", default="14x40", help="label size WxL[+gap] in mm (default 14x40)")
        sp.add_argument("--density", type=int, default=15, help="print darkness 0-15")
        sp.add_argument("--copies", type=int, default=1)
        sp.add_argument("--save-preview", metavar="PNG", help="also save the rendered bitmap")
        sp.add_argument("--dry-run", action="store_true", help="render only, do not print")

    print_opts(sub.add_parser("test", help="print a calibration pattern"))
    t = sub.add_parser("print-text", help="print a line of text")
    t.add_argument("text")
    t.add_argument("--no-border", action="store_true")
    print_opts(t)
    i = sub.add_parser("print-image", help="print an image file")
    i.add_argument("path")
    print_opts(i)

    args = p.parse_args(argv)
    handler = {"status": cmd_status, "test": cmd_test, "print-text": cmd_text, "print-image": cmd_image}[args.cmd]

    if getattr(args, "dry_run", False):
        handler(None, args)
        return
    with P21Connection(resolve_address(args.address)) as conn:
        handler(conn, args)


if __name__ == "__main__":
    main()
