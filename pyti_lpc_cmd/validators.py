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

"""Input validation functions -- character-whitelist checking and size bounds.

Spec references: sec. 2.2, sec. 8.1, sec. 8.2
"""

import os

# Maximum file sizes per spec sec. 2.2, sec. 8.1
MAX_TEXT_FILE_BYTES = 1 * 1024 * 1024   # 1 MB
MAX_BINARY_LPC_BYTES = 32 * 1024         # 32 KB  (16384 * 2)
MAX_ROM_FILE_BYTES = 16 * 1024           # 16 KB per ROM slot

# Valid character sets per spec sec. 2.2
_DECIMAL_VALID = frozenset("0123456789,: -\t\r\n")
_HEX_VALID = frozenset("0123456789abcdefABCDEF,:xX \t\r\n")


class ValidationError(ValueError):
    """Raised when input validation fails."""


def validate_decimal_string(s: str) -> None:
    """Validate that s contains only decimal CSV characters.

    Allowed: digits 0-9, comma, colon, hyphen, space, tab, CR, LF.
    Raises ValidationError on first bad character.
    """
    if not s:
        raise ValidationError("Decimal CSV string is empty")
    for i, ch in enumerate(s):
        if ch not in _DECIMAL_VALID:
            raise ValidationError(
                f"Invalid character {ch!r} at position {i} in decimal CSV string"
            )


def validate_hex_string(s: str) -> None:
    """Validate that s contains only hex CSV characters.

    Allowed: hex digits, comma, colon, 'x', 'X', space, tab, CR, LF.
    Raises ValidationError on first bad character.
    """
    if not s:
        raise ValidationError("Hex CSV string is empty")
    for i, ch in enumerate(s):
        if ch not in _HEX_VALID:
            raise ValidationError(
                f"Invalid character {ch!r} at position {i} in hex CSV string"
            )


def validate_file_path(path: str) -> None:
    """Reject path traversal attempts.

    Raises ValidationError if path contains '..' components.
    """
    if not path:
        raise ValidationError("File path is empty")
    # Normalise and check for traversal
    norm = os.path.normpath(path)
    parts = norm.replace("\\", "/").split("/")
    if ".." in parts:
        raise ValidationError(f"Path traversal rejected: {path!r}")


def check_file_size(path: str, max_bytes: int) -> None:
    """Raise ValidationError if file at path exceeds max_bytes."""
    try:
        size = os.path.getsize(path)
    except OSError as exc:
        raise ValidationError(f"Cannot stat file {path!r}: {exc}") from exc
    if size > max_bytes:
        raise ValidationError(
            f"File {path!r} is {size} bytes, exceeds limit of {max_bytes} bytes"
        )
