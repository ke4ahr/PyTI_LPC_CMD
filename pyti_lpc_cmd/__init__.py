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

"""pyti_lpc_cmd -- Clean-room Python TMS5xxx LPC speech synthesizer decoder.

Based exclusively on tms5xxx_cleanroom_specification.md.
No GPL source code was referenced in this implementation.

Library usage
-------------
Quick render to a WAV file::

    import pyti_lpc_cmd as lpc
    lpc.render(open("word.lpc", "rb").read(), chip="tms5220", wav="out.wav")

Get raw float samples at 8 kHz::

    samples = lpc.render(data, chip="tms5220")

Resample to 44.1 kHz::

    samples = lpc.render(data, chip="tms5220", srate=44100)

Use the synthesizer directly::

    chip   = lpc.get_builtin_chip("tms5220")
    synth  = lpc.LPCSynthesizer()
    samples = synth.synthesize(data, chip)

Parse LPC input from different source formats::

    data = lpc.load_hex_csv("A5,4F,7A,D3")
    data = lpc.load_decimal_csv("isle:165,79,122,211")
    data = lpc.load_binary_file("word.lpc")
"""

__version__ = "1.0.0"

# ---------------------------------------------------------------------------
# Public API -- chip management
# ---------------------------------------------------------------------------
from .chip_params import ChipParams, get_builtin_chip, load_chip_file

# ---------------------------------------------------------------------------
# Public API -- synthesis pipeline
# ---------------------------------------------------------------------------
from .synthesizer import LPCSynthesizer
from .resampler import resample_qdss
from .frame_decoder import LPCFrame, decode_frame
from .bitstream import BitstreamReader

# ---------------------------------------------------------------------------
# Public API -- audio output
# ---------------------------------------------------------------------------
from .audio_output import (
    write_wav,
    write_au,
    write_aiff,
    write_raw,
    write_audio,
)

# ---------------------------------------------------------------------------
# Public API -- input loaders
# ---------------------------------------------------------------------------
from .input_loader import (
    load_binary_file,
    load_decimal_csv,
    load_decimal_csv_file,
    load_hex_csv,
    load_hex_csv_file,
    load_rom_file,
    load_rom_address,
    build_rom,
    strip_label_prefix,
)

# ---------------------------------------------------------------------------
# Public API -- validation
# ---------------------------------------------------------------------------
from .validators import (
    ValidationError,
    validate_decimal_string,
    validate_hex_string,
    validate_file_path,
)

# ---------------------------------------------------------------------------
# High-level convenience function
# ---------------------------------------------------------------------------

def render(
    data: bytes,
    chip: str = "tms5220",
    *,
    srate: int = 8000,
    swidth: int = 16,
    gain: int = 90,
    output: str = "stereo",
    ch: str = "both",
    wav: str = None,
    use_interp: bool = True,
    use_filter: bool = True,
    max_frames: int = 200,
    use_loopguard: bool = True,
    verbose: bool = False,
):
    """Decode an LPC bitstream and optionally write an audio file.

    Args:
        data:        Raw LPC bitstream bytes.
        chip:        Chip name (``"tms5100"``, ``"tms5110"``, ``"tms5200"``,
                     ``"tms5220"``) or path to a ``.txt`` chip definition file.
        srate:       Output sample rate in Hz (default 8000).  If not 8000,
                     the samples are resampled via windowed-sinc conversion.
        swidth:      Bits per sample for file output: 8 or 16 (default 16).
        gain:        Audio gain percentage 0-300 (default 90).
        output:      Channel mode for file output: ``"stereo"``/``"st"`` or
                     ``"mono"``/``"mo"`` (default ``"stereo"``).
        ch:          Channel selection for stereo output: ``"both"`` (default),
                     ``"left"``/``"l"``/``"0"``, or ``"right"``/``"r"``/``"1"``.
        wav:         Output file path.  Format is auto-detected from the
                     extension (``.wav``, ``.au``, ``.snd``, ``.aiff``,
                     ``.aif``, ``.raw``, ``.pcm``).  If ``None`` (default),
                     no file is written.
        use_interp:  Enable parameter interpolation (default ``True``).
        use_filter:  Enable the 10th-order lattice filter (default ``True``).
                     When ``False``, silence is produced.
        max_frames:  Infinite-loop guard: maximum frames before forced stop
                     (default 200 = 5 seconds).
        use_loopguard: Enable the infinite-loop guard (default ``True``).
                     Set to ``False`` to disable the guard.
        verbose:     Print per-frame debug information (default ``False``).

    Returns:
        List of ``float`` samples at *srate* Hz, nominally in [-1.0, 1.0]
        before the 1.5x internal gain stage.  The returned samples are the
        raw synthesizer output; gain/peak scaling is only applied when
        writing to a file.
    """
    import os as _os

    # Resolve chip
    try:
        chip_params = get_builtin_chip(chip)
    except ValueError:
        if _os.path.isfile(chip):
            chip_params = load_chip_file(chip)
        else:
            raise ValueError(
                f"Unknown chip {chip!r}: not a built-in name or existing file path"
            )

    # Synthesize at native 8 kHz
    synth = LPCSynthesizer()
    samples = synth.synthesize(
        data,
        chip_params,
        use_interp=use_interp,
        max_frames=max_frames,
        verbose=verbose,
        use_loopguard=use_loopguard,
    )

    # Silence if filter is disabled
    if not use_filter:
        samples = [0.0] * len(samples)

    # Resample if requested
    if srate != LPCSynthesizer.LPC_SAMPLE_RATE:
        samples = resample_qdss(
            samples,
            float(LPCSynthesizer.LPC_SAMPLE_RATE),
            float(srate),
        )

    # Write audio file if a path was given
    if wav is not None:
        gain_f = gain / 100.0
        mono_mode = output.lower() in ("mo", "mono")

        if mono_mode:
            ch0, ch1, num_ch = samples, None, 1
        else:
            silence = [0.0] * len(samples)
            ch_lc = ch.lower()
            if ch_lc in ("left", "l", "0"):
                ch0, ch1, num_ch = samples, silence, 2
            elif ch_lc in ("right", "r", "1"):
                ch0, ch1, num_ch = silence, samples, 2
            else:
                ch0, ch1, num_ch = samples, samples, 2

        write_audio(wav, ch0, ch1, srate, swidth, num_ch, gain_f)

    return samples


__all__ = [
    # version
    "__version__",
    # high-level
    "render",
    # chip management
    "ChipParams",
    "get_builtin_chip",
    "load_chip_file",
    # synthesis pipeline
    "LPCSynthesizer",
    "LPCFrame",
    "BitstreamReader",
    "decode_frame",
    "resample_qdss",
    # audio output
    "write_wav",
    "write_au",
    "write_aiff",
    "write_raw",
    "write_audio",
    # input loaders
    "load_binary_file",
    "load_decimal_csv",
    "load_decimal_csv_file",
    "load_hex_csv",
    "load_hex_csv_file",
    "load_rom_file",
    "load_rom_address",
    "build_rom",
    "strip_label_prefix",
    # validation
    "ValidationError",
    "validate_decimal_string",
    "validate_hex_string",
    "validate_file_path",
]
