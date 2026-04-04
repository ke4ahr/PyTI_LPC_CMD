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

"""Command-line argument parser for pyti_lpc_cmd.

Spec references: sec. 7.1, sec. 7.2

The tool uses a key=value argument style where each shell argument is one
key=value pair.  str= and strhex= values contain commas, which is fine
because the shell passes each argument as a single token.

For backward compatibility, a trailing '.' on str=/strhex= values is
silently stripped (it was the old end-delimiter convention).  Trailing
commas on any value are stripped gracefully.
"""

from __future__ import annotations

from typing import Dict, Optional


# All recognised parameter keys (sec. 7.2)
_KNOWN_KEYS = frozenset({
    "mode", "chip", "str", "strhex", "strbin", "strfile", "strhexfile",
    "addr", "rom0", "rom1", "wav", "srate", "swidth", "output", "ch",
    "gain", "filt", "loopguard", "verb", "fnamein", "fnameout", "line", "step",
})

# Keys whose values previously required a trailing '.' delimiter.
# We strip it silently so old command lines still work.
_STRIP_DOT_KEYS = frozenset({"str", "strhex"})


def parse_args(argv: list) -> Dict[str, str]:
    """Parse command-line arguments into a dict of key -> value strings.

    Each element of argv must be of the form 'key=value'.  Arguments that
    do not contain '=' are silently ignored (allows bare flags for future
    use).  Spec sec. 7.1, sec. 7.2.

    Backward-compatibility notes:
      - A trailing '.' on str= or strhex= values is stripped silently.
      - A trailing ',' on any value is stripped gracefully.

    Returns a dict with string values.  The caller is responsible for
    type-converting values as needed.
    """
    # Detect help flags early
    for arg in argv:
        if "-help" in arg or "--help" in arg:
            return {"_help": "1"}

    result: Dict[str, str] = {}

    for arg in argv:
        if "=" not in arg:
            continue
        key, _, val = arg.partition("=")
        key = key.strip().lower()
        if key not in _KNOWN_KEYS:
            continue
        val = val.strip()
        # Backward compat: strip trailing '.' from str=/strhex= (old delimiter)
        if key in _STRIP_DOT_KEYS and val.endswith("."):
            val = val[:-1]
        # Strip trailing comma gracefully
        val = val.rstrip(",").strip()
        result[key] = val

    return result


def get_int_param(args: Dict[str, str], key: str, default: int) -> int:
    """Safely extract an integer parameter with a default."""
    val = args.get(key)
    if val is None:
        return default
    try:
        return int(val, 0)
    except ValueError:
        return default


def get_str_param(args: Dict[str, str], key: str, default: str = "") -> str:
    """Safely extract a string parameter with a default."""
    return args.get(key, default)


HELP_TEXT = """\
pyti_lpc_cmd -- TMS5xxx LPC Speech Decoder
https://github.com/ke4ahr/PyTI_LPC_CMD

Usage:
  python -m pyti_lpc_cmd mode=<mode> [options...]
  pyti_lpc_cmd mode=<mode> [options...]

Modes:
  render            Decode LPC data and write audio file
  romlist           List word addresses from a VSM ROM
  rendaddrfileseq   Render word at next address in a romlist file
  rendstrfileseq    Render hex LPC string at next line in a data file
  cleanbrace        Strip C/Arduino { } array syntax from a file
  cleanquote        Strip quoted-string syntax from a file

Input (one required for render mode):
  str=<bytes>       Decimal CSV byte values (e.g. str=isle:165,79,122)
  strhex=<bytes>    Hex CSV byte values (e.g. strhex=A5,4F,7A)
  strbin=<file>     Raw binary LPC file
  strfile=<file>    Decimal CSV text file
  strhexfile=<file> Hex CSV text file
  addr=<hex>        ROM address (requires rom0=)

ROM:
  rom0=<file>       Primary ROM file (loaded at 0x0000)
  rom1=<file>       Secondary ROM file (loaded at 0x4000)

Output:
  wav=<file>        Output audio file (default: zzzout.wav)
                    Extension determines format: .wav .au .snd .aiff .aif .raw .pcm
  srate=<hz>        Output sample rate (default: 8000, range 4000-192000)
  swidth=<bits>     Bits per sample: 8 or 16 (default: 16)
  output=<mode>     Channel mode: st/stereo or mo/mono (default: st)
  ch=<chan>         Channel: left/l/0, right/r/1 (default: both)
  gain=<pct>        Audio gain percent 0-300 (default: 90)

Chip:
  chip=<name>       Chip variant: tms5100 tms5110 tms5200 tms5220
                    or path to a .txt chip definition file (default: tms5220)

Synthesis:
  filt=off          Disable the lattice filter
  loopguard=off     Disable the infinite-loop guard (200-frame / 5s limit)
  verb=on           Enable verbose per-frame output

Sequential modes:
  fnamein=<file>    Input address-list or data file
  fnameout=<file>   Output file for romlist/cleanbrace/cleanquote
  line=<n>          Explicit zero-based line index (default: from zzzline_index.txt)
  step=<n>          Lines to advance per call (default: 1)

Examples:
  pyti_lpc_cmd mode=render chip=tms5220 strhex=A5,4F,7A,D3 wav=out.wav
  pyti_lpc_cmd mode=render strbin=affirmative.lpc wav=out.wav srate=22050
  pyti_lpc_cmd mode=render str=isle:165,79,122,211 wav=out.wav
  pyti_lpc_cmd mode=romlist rom0=speak_spell.bin fnameout=words.txt
"""
