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

"""Windowed-sinc sample rate converter (QDSS algorithm).

Spec references: sec. 5.1, sec. 5.2, sec. 13.4
Algorithm by Ronald H. Nicholson Jr., documented under BSD-style license.
"""

from __future__ import annotations

import math
from typing import List


def resample_qdss(
    input_buf: List[float],
    input_rate: float,
    output_rate: float,
) -> List[float]:
    """Convert sample rate using a windowed-sinc (von Hann) FIR filter.

    Args:
        input_buf:   Input samples at input_rate Hz.
        input_rate:  Source sample rate (e.g. 8000.0).
        output_rate: Desired output sample rate.

    Returns:
        Resampled samples at output_rate Hz.

    Spec sec. 5.1, sec. 5.2, sec. 13.4.
    """
    if output_rate == input_rate:
        return list(input_buf)

    ratio = input_rate / output_rate
    n_in = len(input_buf)

    if output_rate > input_rate:
        # Upsampling: less aggressive anti-alias filter
        fmax = output_rate * 0.55
        window_width = 64
    else:
        # Downsampling: wider filter to suppress aliasing
        fmax = output_rate * 0.375
        window_width = 256

    output_count = int(n_in / ratio)
    gain = 2.0 * fmax / output_rate
    two_pi = 2.0 * math.pi
    half_w = window_width // 2

    output: List[float] = []
    x = 0.0  # current position in the input buffer (float)

    for _ in range(output_count):
        y = 0.0
        for i in range(-half_w, half_w):
            j = int(x) + i
            if 0 <= j < n_in:
                # von Hann window (spec sec. 5.1)
                w = 0.5 - 0.5 * math.cos(two_pi * (0.5 + (j - x) / window_width))
                # Sinc function -- guard against division by zero (spec sec. 8.3)
                a = two_pi * (j - x) * fmax / output_rate
                sinc = math.sin(a) / a if a != 0.0 else 1.0
                y += gain * w * sinc * input_buf[j]
        output.append(y)
        x += ratio

    return output
