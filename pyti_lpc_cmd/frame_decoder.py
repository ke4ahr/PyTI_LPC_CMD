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

"""LPC frame decoder -- parses energy, pitch, repeat flag, and K coefficients.

Spec references: sec. 3.2, sec. 3.3, sec. 10.2, sec. 13.2
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from .bitstream import BitstreamReader
from .chip_params import ChipParams


@dataclass
class LPCFrame:
    """Decoded parameters for one 25 ms LPC frame."""

    energy_idx: int = 0
    energy: int = 0        # looked-up energy level (raw integer)
    period: int = 0        # pitch period in samples (0 = unvoiced)
    repeat: bool = False
    k: List[int] = field(default_factory=lambda: [0] * 10)
    is_silence: bool = False
    is_stop: bool = False


def decode_frame(
    reader: BitstreamReader,
    chip: ChipParams,
    prev_k: List[int],
) -> LPCFrame:
    """Decode one LPC frame from the bitstream.

    Returns an LPCFrame.  The caller is responsible for managing the
    prev_k carry-forward for repeat frames.

    Spec sec. 3.2, sec. 10.2, sec. 13.2.
    """
    frame = LPCFrame()

    # --- 4-bit energy index ---
    frame.energy_idx = reader.get_bits(4)

    if frame.energy_idx == 0:
        # Silence frame: no further bits consumed (spec sec. 13.2)
        frame.is_silence = True
        frame.energy = 0
        return frame

    if frame.energy_idx == 0xF:
        # Stop frame: signals end of utterance (spec sec. 3.2)
        frame.is_stop = True
        return frame

    # --- Data frame (energy_idx 1..14) ---
    frame.energy = chip.energy[frame.energy_idx]

    # 1-bit repeat flag
    frame.repeat = bool(reader.get_bits(1))

    # 5-bit or 6-bit pitch index (depends on chip)
    pitch_bits = 6 if chip.pitch_count == 64 else 5
    pitch_idx = reader.get_bits(pitch_bits)
    frame.period = chip.pitch[pitch_idx]

    if frame.repeat:
        # Repeat: carry forward all K coefficients from previous frame
        frame.k = list(prev_k)
        return frame

    # --- New coefficients ---
    # k0, k1: 5-bit indices -> 32-entry tables
    frame.k[0] = chip.k0[reader.get_bits(5)]
    frame.k[1] = chip.k1[reader.get_bits(5)]
    # k2, k3: 4-bit indices -> 16-entry tables
    frame.k[2] = chip.k2[reader.get_bits(4)]
    frame.k[3] = chip.k3[reader.get_bits(4)]

    if frame.period != 0:
        # Voiced frame: read k4-k9
        frame.k[4] = chip.k4[reader.get_bits(4)]   # 16-entry table
        frame.k[5] = chip.k5[reader.get_bits(4)]
        frame.k[6] = chip.k6[reader.get_bits(4)]
        frame.k[7] = chip.k7[reader.get_bits(3)]   # 8-entry table
        frame.k[8] = chip.k8[reader.get_bits(3)]
        frame.k[9] = chip.k9[reader.get_bits(3)]
    else:
        # Unvoiced frame: k4-k9 are forced to zero (spec sec. 3.2, sec. 13.2)
        for i in range(4, 10):
            frame.k[i] = 0

    return frame
