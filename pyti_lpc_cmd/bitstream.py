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

"""LPC bitstream reader with bit-reversal.

Spec references: sec. 3.1, sec. 10.1, sec. 13.1
"""

from __future__ import annotations


class BitstreamReader:
    """Reads bits from a byte buffer LSB-first after per-byte bit reversal.

    Each byte is bit-reversed before extraction (MSB<->LSB swap).
    Reads past the end of the buffer return 0 bytes (spec sec. 13.1).
    """

    def __init__(self, data: bytes, reverse_bits: bool = True) -> None:
        self.data = data
        self.byte_pos: int = 0
        self.bit_pos: int = 0       # 0-7, current bit offset within current byte
        self.reverse: bool = reverse_bits
        self.bytes_consumed: int = 1  # initial byte counted per spec sec. 10.1

    @staticmethod
    def reverse_byte(b: int) -> int:
        """Reverse all 8 bits of a byte.

        Algorithm from spec sec. 3.1:
            swap nibbles -> swap pairs -> swap adjacent bits
        """
        b = ((b >> 4) | (b << 4)) & 0xFF
        b = (((b & 0xCC) >> 2) | ((b & 0x33) << 2)) & 0xFF
        b = (((b & 0xAA) >> 1) | ((b & 0x55) << 1)) & 0xFF
        return b

    def _get_byte(self, offset: int) -> int:
        """Return the byte at byte_pos+offset, optionally bit-reversed.

        Returns 0 for any access beyond the buffer end.
        """
        idx = self.byte_pos + offset
        if idx >= len(self.data):
            return 0
        b = self.data[idx]
        return self.reverse_byte(b) if self.reverse else b

    def get_bits(self, count: int) -> int:
        """Extract 'count' bits (1-8) from the stream and advance the cursor.

        Uses a 16-bit sliding window (two consecutive bytes) shifted by
        the current bit offset, then takes the top 'count' bits.

        Spec sec. 3.1, sec. 10.1.
        """
        data16 = self._get_byte(0) << 8
        if self.bit_pos + count > 8:
            data16 |= self._get_byte(1)

        data16 = (data16 << self.bit_pos) & 0xFFFF
        value = data16 >> (16 - count)

        self.bit_pos += count
        if self.bit_pos >= 8:
            self.bit_pos -= 8
            self.byte_pos += 1
            self.bytes_consumed += 1

        return value
