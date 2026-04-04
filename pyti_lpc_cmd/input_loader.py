# Copyright (C) 2026 Kris Kirby, KE4AHR
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""Input data loaders for all supported LPC data formats.

Spec references: sec. 2.1-sec. 2.4, sec. 8.1-sec. 8.2
"""

from __future__ import annotations

import struct
from typing import Optional

from .validators import (
    MAX_BINARY_LPC_BYTES,
    MAX_ROM_FILE_BYTES,
    MAX_TEXT_FILE_BYTES,
    ValidationError,
    check_file_size,
    validate_decimal_string,
    validate_file_path,
    validate_hex_string,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def strip_label_prefix(s: str) -> str:
    """Remove an optional 'label:' prefix from a CSV string.

    The spec (sec. 2.1) notes that str= values may begin with an ASCII label
    followed by a colon, e.g. ``str=isle:69,171,54,...``.  This function
    strips everything up to and including the first colon, but only when
    the portion before the colon contains no digits (i.e. it looks like
    a word label, not a decimal or hex value).
    """
    if ":" not in s:
        return s
    label, _, rest = s.partition(":")
    # Only strip if the label contains no digits -- avoid stripping hex addresses
    if not any(ch.isdigit() for ch in label):
        return rest
    return s


# ---------------------------------------------------------------------------
# Binary file
# ---------------------------------------------------------------------------

def load_binary_file(path: str) -> bytes:
    """Load a raw binary LPC file (max 32 KB).

    Spec sec. 2.1 (strbin=), sec. 8.2.
    """
    validate_file_path(path)
    check_file_size(path, MAX_BINARY_LPC_BYTES)
    with open(path, "rb") as f:
        data = f.read(MAX_BINARY_LPC_BYTES)
    if not data:
        raise ValidationError(f"Binary LPC file {path!r} is empty")
    return data


# ---------------------------------------------------------------------------
# Decimal CSV
# ---------------------------------------------------------------------------

def load_decimal_csv(s: str) -> bytes:
    """Parse a decimal CSV string into bytes.

    Accepts the str= format: optional label prefix, comma-separated
    decimal integers 0-255.  Spec sec. 2.1 (str=), sec. 2.2.
    """
    s = strip_label_prefix(s.strip())
    validate_decimal_string(s)
    values = []
    for token in s.split(","):
        token = token.strip()
        if not token:
            continue
        try:
            v = int(token)
        except ValueError as exc:
            raise ValidationError(f"Non-integer token in decimal CSV: {token!r}") from exc
        if not 0 <= v <= 255:
            raise ValidationError(f"Decimal byte value out of range: {v}")
        values.append(v)
    if not values:
        raise ValidationError("Decimal CSV produced no bytes")
    return bytes(values)


def load_decimal_csv_file(path: str) -> bytes:
    """Load a decimal CSV text file and parse it.

    Spec sec. 2.1 (strfile=), sec. 2.2.
    """
    validate_file_path(path)
    check_file_size(path, MAX_TEXT_FILE_BYTES)
    with open(path, "r", encoding="ascii", errors="replace") as f:
        content = f.read(MAX_TEXT_FILE_BYTES)
    if not content.strip():
        raise ValidationError(f"Decimal CSV file {path!r} is empty")
    return load_decimal_csv(content)


# ---------------------------------------------------------------------------
# Hex CSV
# ---------------------------------------------------------------------------

def load_hex_csv(s: str) -> bytes:
    """Parse a hex CSV string into bytes.

    Accepts the strhex= format: comma-separated hex values, optional 0x prefix,
    trailing commas acceptable.  Spec sec. 2.1 (strhex=), sec. 2.2.
    """
    s = strip_label_prefix(s.strip())
    validate_hex_string(s)
    values = []
    for token in s.split(","):
        token = token.strip().rstrip()
        if not token:
            continue
        try:
            v = int(token, 16)
        except ValueError as exc:
            raise ValidationError(f"Non-hex token in hex CSV: {token!r}") from exc
        if not 0 <= v <= 255:
            raise ValidationError(f"Hex byte value out of range: {v}")
        values.append(v)
    if not values:
        raise ValidationError("Hex CSV produced no bytes")
    return bytes(values)


def load_hex_csv_file(path: str) -> bytes:
    """Load a hex CSV text file and parse it.

    Spec sec. 2.1 (strhexfile=), sec. 2.2.
    """
    validate_file_path(path)
    check_file_size(path, MAX_TEXT_FILE_BYTES)
    with open(path, "r", encoding="ascii", errors="replace") as f:
        content = f.read(MAX_TEXT_FILE_BYTES)
    if not content.strip():
        raise ValidationError(f"Hex CSV file {path!r} is empty")
    return load_hex_csv(content)


# ---------------------------------------------------------------------------
# VSM ROM loader
# ---------------------------------------------------------------------------

def load_rom_file(path: str) -> bytes:
    """Load a VSM ROM binary file (max 16 KB per slot).

    Spec sec. 2.4, sec. 8.2.
    """
    validate_file_path(path)
    check_file_size(path, MAX_ROM_FILE_BYTES)
    with open(path, "rb") as f:
        data = f.read(MAX_ROM_FILE_BYTES)
    if not data:
        raise ValidationError(f"ROM file {path!r} is empty")
    return data


def load_rom_address(rom_data: bytes, addr: int) -> bytes:
    """Extract the LPC bitstream starting at addr within rom_data.

    The bitstream continues until a stop frame (energy_idx == 0xF) is
    encountered, or until the end of the ROM.  We return up to 1 KB
    starting at addr and let the synthesizer's frame decoder find the
    stop frame.

    Spec sec. 2.1 (addr=), sec. 2.4.
    """
    if addr < 0 or addr >= len(rom_data):
        raise ValidationError(
            f"ROM address 0x{addr:04X} is outside ROM data of {len(rom_data)} bytes"
        )
    # Return a slice from addr to end of ROM; synthesizer stops at stop frame
    return rom_data[addr:]


def build_rom(rom0_data: Optional[bytes], rom1_data: Optional[bytes]) -> bytes:
    """Combine up to two ROM slots into a flat 32 KB address space.

    rom0 is placed at offset 0x0000; rom1 at offset 0x4000.
    Spec sec. 2.4.
    """
    buf = bytearray(0x8000)
    if rom0_data:
        end = min(len(rom0_data), 0x4000)
        buf[0x0000:0x0000 + end] = rom0_data[:end]
    if rom1_data:
        end = min(len(rom1_data), 0x4000)
        buf[0x4000:0x4000 + end] = rom1_data[:end]
    return bytes(buf)


# ---------------------------------------------------------------------------
# ROM word list extractor (mode=romlist)
# ---------------------------------------------------------------------------

def _read_le16(data: bytes, offset: int) -> int:
    """Read a little-endian 16-bit unsigned integer."""
    if offset + 1 >= len(data):
        return 0
    return struct.unpack_from("<H", data, offset)[0]


def extract_rom_word_list(rom_data: bytes) -> list[tuple[int, str]]:
    """Extract (address, word) pairs from a VSM ROM.

    Layout per spec sec. 12.1:
      - 0x00-0x03: word counts for 4 word lists
      - 0x04-0x0B: pointers (16-bit LE) to 4 word list start addresses
      - 0x0C-0x43: 26 letter pointers (A-Z)
      - following: beep, digits 0-9, "10", phrase pointers

    Returns list of (lpc_address, label) tuples, sorted by address.
    """
    results: list[tuple[int, str]] = []

    # Letters A-Z at 0x0C (26 x 2 bytes = 52 bytes)
    for i in range(26):
        addr = _read_le16(rom_data, 0x0C + i * 2)
        if addr and addr < len(rom_data):
            results.append((addr, chr(ord("A") + i)))

    # Beep at 0x3E (offset after A-Z = 0x0C + 52 = 0x40; beep at 0x40)
    beep_addr = _read_le16(rom_data, 0x40)
    if beep_addr and beep_addr < len(rom_data):
        results.append((beep_addr, "BEEP"))

    # Digits 0-9 at 0x42 (10 x 2 = 20 bytes)
    for i in range(10):
        addr = _read_le16(rom_data, 0x42 + i * 2)
        if addr and addr < len(rom_data):
            results.append((addr, str(i)))

    results.sort(key=lambda t: t[0])
    return results
