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

"""Entry point for pyti_lpc_cmd.

Run as:  python -m pyti_lpc_cmd  [args...]

Spec references: sec. 7.1, sec. 7.2, sec. 12.1-sec. 12.4
"""

from __future__ import annotations

import os
import sys
from typing import List, Optional, Tuple

from .audio_output import write_audio
from .chip_params import ChipParams, get_builtin_chip, load_chip_file
from .cli import (
    HELP_TEXT,
    get_int_param,
    get_str_param,
    parse_args,
)
from .input_loader import (
    build_rom,
    extract_rom_word_list,
    load_binary_file,
    load_decimal_csv,
    load_decimal_csv_file,
    load_hex_csv,
    load_hex_csv_file,
    load_rom_address,
    load_rom_file,
)
from .resampler import resample_qdss
from .synthesizer import LPCSynthesizer
from .validators import ValidationError


# ---------------------------------------------------------------------------
# Chip resolution
# ---------------------------------------------------------------------------

def _resolve_chip(args: dict) -> ChipParams:
    """Load chip parameters from args.

    Tries: 1) named built-in, 2) path to .txt file.
    Defaults to tms5220 if chip= is absent.
    """
    chip_name = get_str_param(args, "chip", "tms5220")
    # Try built-in first
    try:
        return get_builtin_chip(chip_name)
    except ValueError:
        pass
    # Treat as file path
    if os.path.isfile(chip_name):
        return load_chip_file(chip_name)
    raise SystemExit(f"Error: unknown chip {chip_name!r} (not a built-in name or file path)")


# ---------------------------------------------------------------------------
# Input data resolution
# ---------------------------------------------------------------------------

def _resolve_input(args: dict) -> bytes:
    """Load LPC bitstream bytes from whichever input source was specified."""
    if "strbin" in args:
        return load_binary_file(args["strbin"])

    if "str" in args:
        return load_decimal_csv(args["str"])

    if "strhex" in args:
        return load_hex_csv(args["strhex"])

    if "strfile" in args:
        return load_decimal_csv_file(args["strfile"])

    if "strhexfile" in args:
        return load_hex_csv_file(args["strhexfile"])

    if "addr" in args:
        rom_data = _load_rom(args)
        addr = int(args["addr"], 16)
        return load_rom_address(rom_data, addr)

    raise SystemExit(
        "Error: no LPC input specified. Use str=, strhex=, strbin=, "
        "strfile=, strhexfile=, or addr="
    )


def _load_rom(args: dict) -> bytes:
    """Load and combine rom0= and rom1= into a flat address space."""
    rom0 = load_rom_file(args["rom0"]) if "rom0" in args else None
    rom1 = load_rom_file(args["rom1"]) if "rom1" in args else None
    if rom0 is None and rom1 is None:
        raise SystemExit("Error: addr= requires at least rom0=")
    return build_rom(rom0, rom1)


# ---------------------------------------------------------------------------
# Channel routing
# ---------------------------------------------------------------------------

def _build_channels(
    samples: List[float],
    output_mode: str,
    ch_select: str,
) -> Tuple[List[float], Optional[List[float]], int]:
    """Return (ch0_samples, ch1_samples_or_None, num_channels) for output.

    Spec sec. 6.1.
    """
    silence = [0.0] * len(samples)
    mono_mode = output_mode.lower() in ("mo", "mono")

    if mono_mode:
        return samples, None, 1

    # Stereo
    ch = ch_select.lower()
    if ch in ("left", "l", "0"):
        return samples, silence, 2
    if ch in ("right", "r", "1"):
        return silence, samples, 2
    # Default: both channels
    return samples, samples, 2


# ---------------------------------------------------------------------------
# Mode: render
# ---------------------------------------------------------------------------

def _mode_render(args: dict) -> None:
    chip = _resolve_chip(args)
    data = _resolve_input(args)

    srate = get_int_param(args, "srate", 8000)
    if not (4000 <= srate <= 192000):
        raise SystemExit(f"Error: srate={srate} out of range 4000-192000")

    swidth = get_int_param(args, "swidth", 16)
    if swidth not in (8, 16):
        raise SystemExit(f"Error: swidth={swidth} must be 8 or 16")

    gain_pct = get_int_param(args, "gain", 90)
    if not (0 <= gain_pct <= 300):
        raise SystemExit(f"Error: gain={gain_pct} out of range 0-300")
    gain = gain_pct / 100.0

    use_filt = get_str_param(args, "filt", "on").lower() != "off"
    use_loopguard = get_str_param(args, "loopguard", "on").lower() != "off"
    verbose = get_str_param(args, "verb", "off").lower() == "on"
    wav_out = get_str_param(args, "wav", "zzzout.wav")
    output_mode = get_str_param(args, "output", "st")
    ch_select = get_str_param(args, "ch", "both")
    max_frames = 200

    synth = LPCSynthesizer()
    raw_samples = synth.synthesize(
        data,
        chip,
        use_interp=True,
        max_frames=max_frames,
        verbose=verbose,
        use_loopguard=use_loopguard,
    )

    if verbose:
        print(f"[render] {len(raw_samples)} samples @ 8000 Hz")

    # Disable filter output if filt=off (replace with silence)
    if not use_filt:
        raw_samples = [0.0] * len(raw_samples)

    # Resample if needed
    if srate != LPCSynthesizer.LPC_SAMPLE_RATE:
        if verbose:
            print(f"[render] resampling 8000 -> {srate} Hz")
        raw_samples = resample_qdss(raw_samples, float(LPCSynthesizer.LPC_SAMPLE_RATE), float(srate))

    ch0, ch1, num_ch = _build_channels(raw_samples, output_mode, ch_select)

    write_audio(wav_out, ch0, ch1, srate, swidth, num_ch, gain)

    if verbose:
        print(f"[render] wrote {wav_out}")


# ---------------------------------------------------------------------------
# Mode: romlist
# ---------------------------------------------------------------------------

def _mode_romlist(args: dict) -> None:
    if "rom0" not in args:
        raise SystemExit("Error: romlist mode requires rom0=")

    rom_data = _load_rom(args)
    entries = extract_rom_word_list(rom_data)
    out_file = get_str_param(args, "fnameout", "zzzaddr_list.txt")

    lines = [f"{addr:04X} {label}" for addr, label in entries]
    with open(out_file, "w", encoding="ascii") as f:
        f.write("\n".join(lines) + "\n")
    print(f"Wrote {len(entries)} entries to {out_file}")


# ---------------------------------------------------------------------------
# Mode: rendaddrfileseq
# ---------------------------------------------------------------------------

def _mode_rendaddrfileseq(args: dict) -> None:
    """Render the LPC at the address on a specific line of an address-word file."""
    fnamein = get_str_param(args, "fnamein", "")
    if not fnamein:
        raise SystemExit("Error: rendaddrfileseq requires fnamein=")

    line_idx = _get_and_bump_line_index(args)
    step = get_int_param(args, "step", 1)

    with open(fnamein, "r", encoding="ascii") as f:
        lines = [l.strip() for l in f if l.strip()]

    if line_idx < 0 or line_idx >= len(lines):
        raise SystemExit(f"Error: line index {line_idx} out of range (0-{len(lines)-1})")

    parts = lines[line_idx].split()
    addr_str = parts[0]
    label = parts[1] if len(parts) > 1 else addr_str

    rom_data = _load_rom(args)
    addr = int(addr_str, 16)
    lpc_data = load_rom_address(rom_data, addr)

    # Override addr= so _mode_render can proceed
    args = dict(args)
    args.pop("addr", None)
    args.pop("strbin", None)
    args.pop("str", None)
    args.pop("strhex", None)

    # Write lpc_data to a temp path and use strbin
    import tempfile, os
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".lpc")
    try:
        tmp.write(lpc_data)
        tmp.close()
        args["strbin"] = tmp.name
        _mode_render(args)
    finally:
        os.unlink(tmp.name)

    _write_line_index(line_idx + step)
    print(f"Rendered {label} (line {line_idx}, addr 0x{addr:04X})")


# ---------------------------------------------------------------------------
# Mode: rendstrfileseq
# ---------------------------------------------------------------------------

def _mode_rendstrfileseq(args: dict) -> None:
    """Render the hex LPC string on a specific line of a string file."""
    fnamein = get_str_param(args, "fnamein", "")
    if not fnamein:
        raise SystemExit("Error: rendstrfileseq requires fnamein=")

    line_idx = _get_and_bump_line_index(args)
    step = get_int_param(args, "step", 1)

    with open(fnamein, "r", encoding="ascii") as f:
        lines = [l.strip() for l in f if l.strip()]

    if line_idx < 0 or line_idx >= len(lines):
        raise SystemExit(f"Error: line index {line_idx} out of range (0-{len(lines)-1})")

    args = dict(args)
    args["strhex"] = lines[line_idx]
    _mode_render(args)
    _write_line_index(line_idx + step)
    print(f"Rendered line {line_idx}")


# ---------------------------------------------------------------------------
# Mode: cleanbrace / cleanquote
# ---------------------------------------------------------------------------

def _mode_cleanbrace(args: dict) -> None:
    """Extract content between { } on each line (Arduino C array cleanup)."""
    fnamein = get_str_param(args, "fnamein", "")
    if not fnamein:
        raise SystemExit("Error: cleanbrace requires fnamein=")
    fnameout = get_str_param(args, "fnameout", "zzzclean.txt")
    _clean_file(fnamein, fnameout, "{", "}")


def _mode_cleanquote(args: dict) -> None:
    """Extract content between \" \" on each line."""
    fnamein = get_str_param(args, "fnamein", "")
    if not fnamein:
        raise SystemExit("Error: cleanquote requires fnamein=")
    fnameout = get_str_param(args, "fnameout", "zzzclean.txt")
    _clean_file(fnamein, fnameout, '"', '"')


def _clean_file(src: str, dst: str, open_ch: str, close_ch: str) -> None:
    """Extract content between delimiters, strip 0x prefixes and spaces."""
    results = []
    with open(src, "r", encoding="ascii", errors="replace") as f:
        for line in f:
            line = line.rstrip("\r\n")
            s = line.find(open_ch)
            e = line.rfind(close_ch)
            if s == -1 or e <= s:
                continue
            content = line[s + 1:e]
            content = content.replace("0x", "").replace("0X", "")
            content = content.replace(" ", "").replace("\t", "").replace("\r", "")
            results.append(content)
    with open(dst, "w", encoding="ascii") as f:
        f.write("\n".join(results) + "\n")
    print(f"Wrote {len(results)} lines to {dst}")


# ---------------------------------------------------------------------------
# Persistent line index helpers
# ---------------------------------------------------------------------------

_LINE_INDEX_FILE = "zzzline_index.txt"


def _get_and_bump_line_index(args: dict) -> int:
    """Read the current line index from args or the persistent index file."""
    if "line" in args:
        return int(args["line"])
    try:
        with open(_LINE_INDEX_FILE, "r") as f:
            return int(f.read().strip())
    except (OSError, ValueError):
        return 0


def _write_line_index(idx: int) -> None:
    with open(_LINE_INDEX_FILE, "w") as f:
        f.write(str(idx))


# ---------------------------------------------------------------------------
# Main dispatcher
# ---------------------------------------------------------------------------

def main(argv: list = None) -> int:
    if argv is None:
        argv = sys.argv[1:]

    args = parse_args(argv)

    if "_help" in args or not args:
        print(HELP_TEXT)
        return 0

    mode = get_str_param(args, "mode", "").lower()

    try:
        if mode == "render":
            _mode_render(args)
        elif mode == "romlist":
            _mode_romlist(args)
        elif mode == "rendaddrfileseq":
            _mode_rendaddrfileseq(args)
        elif mode == "rendstrfileseq":
            _mode_rendstrfileseq(args)
        elif mode == "cleanbrace":
            _mode_cleanbrace(args)
        elif mode == "cleanquote":
            _mode_cleanquote(args)
        else:
            print(f"Error: unknown mode {mode!r}")
            print("Run with --help for usage.")
            return 1
    except ValidationError as exc:
        print(f"Validation error: {exc}", file=sys.stderr)
        return 1
    except SystemExit as exc:
        print(exc, file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
