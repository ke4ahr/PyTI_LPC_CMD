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

"""Chip parameter container and loader.

Spec references: sec. 2.3, sec. 3.3, sec. 11.1, sec. 11.2
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List


@dataclass
class ChipParams:
    """Immutable parameter tables for one TMS5xxx chip variant."""

    processor: str = ""
    chirp: List[int] = field(default_factory=list)   # uint8 values, len 50/32/52
    energy: List[int] = field(default_factory=list)  # 16 int16 levels
    pitch_count: int = 32                             # 32 or 64
    pitch: List[int] = field(default_factory=list)   # pitch period lookup
    k0: List[int] = field(default_factory=list)      # 32 int16, scaled x512
    k1: List[int] = field(default_factory=list)      # 32 int16
    k2: List[int] = field(default_factory=list)      # 16 int16
    k3: List[int] = field(default_factory=list)      # 16 int16
    k4: List[int] = field(default_factory=list)      # 16 int16
    k5: List[int] = field(default_factory=list)      # 16 int16
    k6: List[int] = field(default_factory=list)      # 16 int16
    k7: List[int] = field(default_factory=list)      # 8 int16
    k8: List[int] = field(default_factory=list)      # 8 int16
    k9: List[int] = field(default_factory=list)      # 8 int16

    def k_table(self, n: int) -> List[int]:
        """Return the k-coefficient table for coefficient index n (0-9)."""
        return [self.k0, self.k1, self.k2, self.k3, self.k4,
                self.k5, self.k6, self.k7, self.k8, self.k9][n]


def _parse_int_list(text: str) -> List[int]:
    """Parse a comma-separated list of decimal or hex integers."""
    result = []
    for token in re.split(r"[\s,]+", text.strip()):
        token = token.strip()
        if not token:
            continue
        result.append(int(token, 0))   # int(x, 0) handles 0x prefixes
    return result


def load_chip_file(path: str) -> ChipParams:
    """Load a chip definition text file and return a ChipParams instance.

    File format is key=value pairs, one per line.  Spec sec. 2.3.
    """
    params = ChipParams()

    with open(path, "r", encoding="ascii", errors="replace") as fh:
        for raw_line in fh:
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, _, val = line.partition("=")
            key = key.strip().lower()
            val = val.strip()

            if key == "processor":
                params.processor = val.lower()
            elif key == "chirp":
                params.chirp = _parse_int_list(val)
            elif key == "chirp_hx":
                params.chirp = _parse_int_list(val)
            elif key == "energy":
                params.energy = _parse_int_list(val)
            elif key == "energy_hx":
                params.energy = _parse_int_list(val)
            elif key == "pitch_count":
                params.pitch_count = int(val, 0)
            elif key == "pitch":
                params.pitch = _parse_int_list(val)
            elif key == "pitch_hx":
                params.pitch = _parse_int_list(val)
            elif key == "k0":
                params.k0 = _parse_int_list(val)
            elif key == "k1":
                params.k1 = _parse_int_list(val)
            elif key == "k2":
                params.k2 = _parse_int_list(val)
            elif key == "k3":
                params.k3 = _parse_int_list(val)
            elif key == "k4":
                params.k4 = _parse_int_list(val)
            elif key == "k5":
                params.k5 = _parse_int_list(val)
            elif key == "k6":
                params.k6 = _parse_int_list(val)
            elif key == "k7":
                params.k7 = _parse_int_list(val)
            elif key == "k8":
                params.k8 = _parse_int_list(val)
            elif key == "k9":
                params.k9 = _parse_int_list(val)

    return params


def get_builtin_chip(name: str) -> ChipParams:
    """Return the built-in ChipParams for the given chip name.

    Accepted names (case-insensitive): tms5100, tms5110, tms5200, tms5220.
    Raises ValueError for unknown names.
    """
    name_lc = name.strip().lower()
    # Strip optional .txt extension
    if name_lc.endswith(".txt"):
        name_lc = name_lc[:-4]

    if name_lc == "tms5100":
        from .chips.tms5100 import PARAMS
    elif name_lc == "tms5110":
        from .chips.tms5110 import PARAMS
    elif name_lc == "tms5200":
        from .chips.tms5200 import PARAMS
    elif name_lc == "tms5220":
        from .chips.tms5220 import PARAMS
    else:
        raise ValueError(f"Unknown built-in chip: {name!r}")

    return PARAMS
