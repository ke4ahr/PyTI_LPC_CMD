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

"""TMS5100 chip parameter tables.

Values sourced from tms5100.txt (chip definition file).
Chirp values are decimal uint8; K values are int16 pre-scaled by 512.
Spec reference: sec. 11.1, sec. 11.2
"""

from ..chip_params import ChipParams

PARAMS = ChipParams(
    processor="tms5100",
    chirp=[
        0, 42, 212, 50, 178, 18, 37, 20, 2, 225,
        197, 2, 95, 90, 5, 15, 38, 252, 165, 165,
        214, 221, 220, 252, 37, 43, 34, 33, 15, 255,
        248, 238, 237, 239, 247, 246, 250, 0, 3, 2,
        1, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    ],
    energy=[0, 0, 1, 1, 2, 3, 5, 7, 10, 15, 21, 30, 43, 61, 86, 0],
    pitch_count=32,
    pitch=[
        0, 41, 43, 45, 47, 49, 51, 53, 55, 58,
        60, 63, 66, 70, 73, 76, 79, 83, 87, 90,
        94, 99, 103, 107, 112, 118, 123, 129, 134, 140,
        147, 153,
    ],
    k0=[
        -501, -497, -493, -488, -480, -471, -460, -446,
        -427, -405, -378, -344, -305, -259, -206, -148,
        -86, -21, 45, 110, 171, 227, 277, 320,
        357, 388, 413, 434, 451, 464, 474, 498,
    ],
    k1=[
        -349, -328, -305, -280, -252, -223, -192, -158,
        -124, -88, -51, -14, 23, 60, 97, 133,
        167, 199, 230, 259, 286, 310, 333, 354,
        372, 389, 404, 417, 429, 439, 449, 506,
    ],
    k2=[
        -397, -365, -327, -282, -229, -170, -104, -36,
        35, 104, 169, 228, 281, 326, 364, 396,
    ],
    k3=[
        -369, -334, -293, -245, -191, -131, -67, -1,
        64, 128, 188, 243, 291, 332, 367, 397,
    ],
    k4=[
        -319, -286, -250, -211, -168, -122, -74, -25,
        24, 73, 121, 167, 210, 249, 285, 318,
    ],
    k5=[
        -290, -252, -209, -163, -114, -62, -9, 44,
        97, 147, 194, 238, 278, 313, 344, 371,
    ],
    k6=[
        -291, -256, -216, -174, -128, -80, -31, 19,
        69, 117, 163, 206, 246, 283, 316, 345,
    ],
    k7=[-218, -133, -38, 59, 152, 235, 305, 361],
    k8=[-226, -157, -82, -3, 76, 151, 220, 280],
    k9=[-179, -122, -61, 1, 62, 123, 179, 231],
)
