#!/usr/bin/env python3
"""bin2strhex.py -- Convert binary file to comma-separated hex strings."""

import argparse
import sys


def parse_args():
    p = argparse.ArgumentParser(
        description="Convert binary file to comma-separated strhex."
    )
    p.add_argument("bin_file", help="Input binary file")
    p.add_argument(
        "--endian",
        choices=["little", "lsb", "big", "msb"],
        default="little",
        help="Byte order for multi-byte words: little/lsb or big/msb (default: little)",
    )
    p.add_argument(
        "--word-size",
        type=int,
        choices=[1, 2, 4],
        default=1,
        metavar="{1,2,4}",
        help="Word size in bytes (default: 1); endian applies when >1",
    )
    p.add_argument(
        "--prefix",
        default="0x",
        help="Hex prefix string (default: '0x')",
    )
    p.add_argument(
        "--no-prefix",
        action="store_true",
        help="Omit hex prefix",
    )
    p.add_argument(
        "--output", "-o",
        default="-",
        help="Output file (default: stdout)",
    )
    return p.parse_args()


def main():
    args = parse_args()
    prefix = "" if args.no_prefix else args.prefix
    word_size = args.word_size
    endian = "little" if args.endian in ("little", "lsb") else "big"

    try:
        with open(args.bin_file, "rb") as f:
            data = f.read()
    except OSError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    if len(data) % word_size != 0:
        tail = len(data) % word_size
        print(
            f"Warning: file size {len(data)} not a multiple of word size {word_size}; "
            f"last {tail} byte(s) padded with 0x00",
            file=sys.stderr,
        )
        data += b"\x00" * (word_size - tail)

    hex_width = word_size * 2  # digits per word
    tokens = []
    for i in range(0, len(data), word_size):
        chunk = data[i : i + word_size]
        value = int.from_bytes(chunk, byteorder=endian)
        tokens.append(f"{prefix}{value:0{hex_width}X}")

    result = ",".join(tokens)

    if args.output == "-":
        print(result)
    else:
        try:
            with open(args.output, "w") as f:
                f.write(result + "\n")
        except OSError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
