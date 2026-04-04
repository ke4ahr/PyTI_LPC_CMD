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

"""Audio file writers: WAV, AU/SND, AIFF, raw PCM.

Spec references: sec. 6.1-sec. 6.4, sec. 13.5
"""

from __future__ import annotations

import struct
import os
from typing import List, Optional


def _to_int_samples(
    samples: List[float],
    gain: float,
    bits: int,
) -> List[int]:
    """Convert float samples [-1.0, 1.0] to integer PCM.

    8-bit: unsigned, center at 128.
    16-bit: signed little-endian.
    Gain is applied first: sample x gain.
    Spec sec. 6.2, sec. 6.3, sec. 13.5.
    """
    if bits == 8:
        peak = 127
        result = []
        for s in samples:
            v = int(round(s * gain * peak))
            result.append(max(0, min(255, v + 128)))
    else:
        peak = 32767
        result = []
        for s in samples:
            v = int(round(s * gain * peak))
            result.append(max(-32768, min(32767, v)))
    return result


def _interleave(
    ch0: List[float],
    ch1: Optional[List[float]],
) -> List[float]:
    """Interleave two channel lists into one L-R-L-R... list."""
    if ch1 is None:
        return list(ch0)
    n = len(ch0)
    out: List[float] = []
    for i in range(n):
        out.append(ch0[i])
        out.append(ch1[i] if i < len(ch1) else 0.0)
    return out


# ---------------------------------------------------------------------------
# WAV writer
# ---------------------------------------------------------------------------

def write_wav(
    filename: str,
    samples_ch0: List[float],
    samples_ch1: Optional[List[float]],
    sample_rate: int,
    bits_per_sample: int,
    channels: int,
    gain: float = 1.0,
) -> None:
    """Write a standard RIFF WAV file.

    samples_ch0/ch1 are floats in [-1.0, 1.0].
    Spec sec. 6.3, sec. 13.5.
    """
    if channels == 2 and samples_ch1 is not None:
        data_floats = _interleave(samples_ch0, samples_ch1)
    else:
        data_floats = list(samples_ch0)

    int_samples = _to_int_samples(data_floats, gain, bits_per_sample)
    bytes_per_sample = bits_per_sample // 8
    total_samples = len(int_samples)
    data_size = total_samples * bytes_per_sample
    block_align = channels * bytes_per_sample
    avg_bytes_per_sec = sample_rate * block_align

    with open(filename, "wb") as f:
        # RIFF header
        f.write(b"RIFF")
        f.write(struct.pack("<I", data_size + 36))
        f.write(b"WAVE")
        # fmt chunk (16 bytes)
        f.write(b"fmt ")
        f.write(struct.pack("<I", 16))
        f.write(struct.pack("<H", 1))              # PCM format tag
        f.write(struct.pack("<H", channels))
        f.write(struct.pack("<I", sample_rate))
        f.write(struct.pack("<I", avg_bytes_per_sec))
        f.write(struct.pack("<H", block_align))
        f.write(struct.pack("<H", bits_per_sample))
        # data chunk
        f.write(b"data")
        f.write(struct.pack("<I", data_size))
        if bits_per_sample == 8:
            f.write(bytes(int_samples))
        else:
            for v in int_samples:
                f.write(struct.pack("<h", v))


# ---------------------------------------------------------------------------
# AU / SND writer
# ---------------------------------------------------------------------------

def write_au(
    filename: str,
    samples_ch0: List[float],
    samples_ch1: Optional[List[float]],
    sample_rate: int,
    bits_per_sample: int,
    channels: int,
    gain: float = 1.0,
) -> None:
    """Write a Sun/AU audio file (encoding 3 = 16-bit linear PCM, big-endian).

    Only 16-bit output is implemented; 8-bit AU uses unsigned 8-bit (encoding 2).
    Spec sec. 6.4.
    """
    if channels == 2 and samples_ch1 is not None:
        data_floats = _interleave(samples_ch0, samples_ch1)
    else:
        data_floats = list(samples_ch0)

    int_samples = _to_int_samples(data_floats, gain, bits_per_sample)
    bytes_per_sample = bits_per_sample // 8
    data_size = len(int_samples) * bytes_per_sample

    # AU encoding constants
    if bits_per_sample == 8:
        encoding = 2   # 8-bit G.711 mu-law -- use linear unsigned instead
    else:
        encoding = 3   # 16-bit linear PCM

    # AU header: magic, data_offset, data_size, encoding, sample_rate, channels
    header_size = 24
    with open(filename, "wb") as f:
        f.write(b".snd")
        f.write(struct.pack(">I", header_size))
        f.write(struct.pack(">I", data_size))
        f.write(struct.pack(">I", encoding))
        f.write(struct.pack(">I", sample_rate))
        f.write(struct.pack(">I", channels))
        if bits_per_sample == 8:
            f.write(bytes(int_samples))
        else:
            for v in int_samples:
                f.write(struct.pack(">h", v))


# ---------------------------------------------------------------------------
# AIFF writer
# ---------------------------------------------------------------------------

def write_aiff(
    filename: str,
    samples_ch0: List[float],
    samples_ch1: Optional[List[float]],
    sample_rate: int,
    bits_per_sample: int,
    channels: int,
    gain: float = 1.0,
) -> None:
    """Write an AIFF file (big-endian signed integer samples).

    Spec sec. 6.4.
    """
    if channels == 2 and samples_ch1 is not None:
        data_floats = _interleave(samples_ch0, samples_ch1)
    else:
        data_floats = list(samples_ch0)

    int_samples = _to_int_samples(data_floats, gain, bits_per_sample)
    bytes_per_sample = bits_per_sample // 8
    num_sample_frames = len(int_samples) // channels
    data_size = len(int_samples) * bytes_per_sample

    # 80-bit IEEE 754 extended for sample rate
    rate_extended = _float_to_extended(float(sample_rate))

    # COMM chunk size = 18 bytes
    comm_size = 18
    # SSND chunk size = 8 (offset + blockSize) + data_size
    ssnd_size = 8 + data_size

    form_size = 4 + (8 + comm_size) + (8 + ssnd_size)

    with open(filename, "wb") as f:
        # FORM chunk
        f.write(b"FORM")
        f.write(struct.pack(">I", form_size))
        f.write(b"AIFF")
        # COMM chunk
        f.write(b"COMM")
        f.write(struct.pack(">I", comm_size))
        f.write(struct.pack(">h", channels))
        f.write(struct.pack(">I", num_sample_frames))
        f.write(struct.pack(">h", bits_per_sample))
        f.write(rate_extended)
        # SSND chunk
        f.write(b"SSND")
        f.write(struct.pack(">I", ssnd_size))
        f.write(struct.pack(">I", 0))   # offset
        f.write(struct.pack(">I", 0))   # blockSize
        if bits_per_sample == 8:
            # AIFF uses signed 8-bit (unlike WAV which is unsigned)
            for v in int_samples:
                sv = v - 128  # convert unsigned center-128 back to signed
                f.write(struct.pack("b", max(-128, min(127, sv))))
        else:
            for v in int_samples:
                f.write(struct.pack(">h", v))


def _float_to_extended(value: float) -> bytes:
    """Encode a float as an 80-bit IEEE 754 extended (10 bytes, big-endian)."""
    import math
    if value == 0.0:
        return b"\x00" * 10
    sign = 0
    if value < 0.0:
        sign = 0x8000
        value = -value
    exponent = int(math.floor(math.log2(value))) + 16383
    mantissa = int(value / (2.0 ** (exponent - 16383)) * (2 ** 63))
    return struct.pack(">HQ", sign | exponent, mantissa)


# ---------------------------------------------------------------------------
# Raw PCM writer
# ---------------------------------------------------------------------------

def write_raw(
    filename: str,
    samples_ch0: List[float],
    samples_ch1: Optional[List[float]],
    bits_per_sample: int,
    channels: int,
    gain: float = 1.0,
) -> None:
    """Write raw PCM bytes with no header.  Spec sec. 6.4."""
    if channels == 2 and samples_ch1 is not None:
        data_floats = _interleave(samples_ch0, samples_ch1)
    else:
        data_floats = list(samples_ch0)

    int_samples = _to_int_samples(data_floats, gain, bits_per_sample)
    with open(filename, "wb") as f:
        if bits_per_sample == 8:
            f.write(bytes(int_samples))
        else:
            for v in int_samples:
                f.write(struct.pack("<h", v))


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------

def write_audio(
    filename: str,
    samples_ch0: List[float],
    samples_ch1: Optional[List[float]],
    sample_rate: int,
    bits_per_sample: int,
    channels: int,
    gain: float = 1.0,
) -> None:
    """Write audio to filename, auto-detecting format from extension.

    Supported extensions: .wav, .au, .snd, .aiff, .aif, .raw, .pcm
    Defaults to WAV for unknown extensions.  Spec sec. 6.4.
    """
    ext = os.path.splitext(filename)[1].lower()
    if ext in (".au", ".snd"):
        write_au(filename, samples_ch0, samples_ch1, sample_rate,
                 bits_per_sample, channels, gain)
    elif ext in (".aiff", ".aif"):
        write_aiff(filename, samples_ch0, samples_ch1, sample_rate,
                   bits_per_sample, channels, gain)
    elif ext in (".raw", ".pcm"):
        write_raw(filename, samples_ch0, samples_ch1,
                  bits_per_sample, channels, gain)
    else:
        # Default: WAV
        write_wav(filename, samples_ch0, samples_ch1, sample_rate,
                  bits_per_sample, channels, gain)
