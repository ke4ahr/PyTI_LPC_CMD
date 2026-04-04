# pyti_lpc_cmd

Clean-room Python decoder for Texas Instruments TMS5xxx LPC speech synthesis chips.

Supports the TMS5100, TMS5110, TMS5200, and TMS5220 -- the chips used in the
*Speak & Spell* (1978) and many other products of that era.

**License:** GNU General Public License v3.0 or later
**Author:** Kris Kirby, KE4AHR
**Source:** https://github.com/ke4ahr/PyTI_LPC_CMD

---

## Features

- Decodes LPC bitstreams from binary files, inline CSV, hex CSV, or VSM ROM images
- 10th-order lattice filter vocal-tract model
- Voiced (chirp waveform) and unvoiced (Galois LFSR) excitation
- 8-sub-step parameter interpolation replicating original chip behaviour
- Windowed-sinc (QDSS) sample-rate converter for any output rate from 4 kHz to 192 kHz
- WAV, AU, AIFF, and raw PCM output; 8-bit or 16-bit; mono or stereo
- Four built-in chip variants; custom chip definition files supported
- Python library API for embedding in other projects
- No external dependencies -- standard library only

---

## Quick Start

### Install

```bash
git clone https://github.com/ke4ahr/PyTI_LPC_CMD.git
cd PyTI_LPC_CMD
```

Add `bin/` to your `PATH`, or run via `python -m pyti_lpc_cmd`.

### Install in a Python virtual environment (recommended)

```bash
git clone https://github.com/ke4ahr/PyTI_LPC_CMD.git
cd PyTI_LPC_CMD

# Create and activate venv
python3 -m venv .venv
source .venv/bin/activate        # Linux / macOS
# .venv\Scripts\activate         # Windows

# Install the package (no external dependencies)
pip install .

# Run
pyti_lpc_cmd mode=render chip=tms5220 strhex=A5,4F,7A,D3 wav=out.wav

# Deactivate when done
deactivate
```

### Install the man page

```bash
# User install (no sudo required)
bash docs/install_man.sh

# System-wide install
sudo bash docs/install_man.sh --system

# View the man page
man pyti_lpc_cmd
```

The install script copies `docs/pyti_lpc_cmd.1` to the appropriate `man1/`
directory and runs `mandb` to update the man database.

### Render a binary LPC file

```bash
pyti_lpc_cmd mode=render chip=tms5220 strbin=word.lpc wav=out.wav
```

### Render inline hex bytes

```bash
pyti_lpc_cmd mode=render chip=tms5220 strhex=A5,4F,7A,D3,3C,5A wav=out.wav
```

### Render inline decimal CSV

```bash
pyti_lpc_cmd mode=render chip=tms5100 str=isle:165,79,122,211 wav=out.wav
```

### Render at 44.1 kHz mono

```bash
pyti_lpc_cmd mode=render chip=tms5220 strbin=word.lpc \
    wav=out.wav srate=44100 output=mono
```

### Extract a word from a Speak & Spell ROM

```bash
pyti_lpc_cmd mode=render chip=tms5220 \
    rom0=speakspell_r0.bin rom1=speakspell_r1.bin \
    addr=0220 wav=affirmative.wav
```

### List all words in a ROM

```bash
pyti_lpc_cmd mode=romlist \
    rom0=speakspell_r0.bin rom1=speakspell_r1.bin \
    fnameout=word_list.txt
```

### Step through ROM words one at a time

```bash
# Each call advances the position counter in zzzline_index.txt
pyti_lpc_cmd mode=rendaddrfileseq \
    rom0=speakspell_r0.bin fnamein=word_list.txt wav=current.wav
```

---

## Chip Variants

| Chip    | Pitch bits | Chirp entries | Notes                        |
|---------|-----------|---------------|------------------------------|
| TMS5100 | 5         | 50            | Speak & Spell first edition  |
| TMS5110 | 5         | 32            | Later Speak & Spell variants |
| TMS5200 | 6         | 52            | Hex chirp table              |
| TMS5220 | 6         | 52            | Most common; default         |

---

## All Parameters

### Input (exactly one required for `render`)

| Parameter       | Description                                         |
|----------------|-----------------------------------------------------|
| `strbin=`       | Path to a raw binary LPC file (max 32 KB)           |
| `str=`          | Inline decimal CSV, optional `label:` prefix        |
| `strhex=`       | Inline hex CSV                                      |
| `strfile=`      | Path to a decimal CSV text file (max 1 MB)          |
| `strhexfile=`   | Path to a hex CSV text file (max 1 MB)              |
| `addr=`         | Hex address within a ROM image (requires `rom0=`)   |

### ROM

| Parameter | Description                                        |
|-----------|----------------------------------------------------|
| `rom0=`   | ROM binary file mapped at 0x0000 (max 16 KB)       |
| `rom1=`   | ROM binary file mapped at 0x4000 (max 16 KB)       |

### Audio Output

| Parameter   | Default       | Description                                       |
|-------------|---------------|---------------------------------------------------|
| `wav=`      | `zzzout.wav`  | Output file; format from extension (.wav .au .aiff .raw) |
| `srate=`    | `8000`        | Sample rate Hz (4000-192000)                      |
| `swidth=`   | `16`          | Bits per sample: `8` or `16`                      |
| `gain=`     | `90`          | Gain percent 0-300                                |
| `output=`   | `st`          | `st`/`stereo` or `mo`/`mono`                      |
| `ch=`       | `both`        | `both`, `left`/`l`/`0`, or `right`/`r`/`1`       |

### Synthesis Control

| Parameter     | Default | Description                                     |
|---------------|---------|-------------------------------------------------|
| `chip=`       | `tms5220` | Chip variant or path to `.txt` file             |
| `filt=`       | `on`    | `off` to disable the lattice filter             |
| `loopguard=`  | `on`    | `off` to disable the 200-frame silence guard    |
| `verb=`       | `off`   | `on` for per-frame diagnostic output            |

### Sequential Modes

| Parameter   | Description                                              |
|-------------|----------------------------------------------------------|
| `fnamein=`  | Input file for `rendaddrfileseq` / `rendstrfileseq`      |
| `fnameout=` | Output file for `romlist`, `cleanbrace`, `cleanquote`    |
| `line=`     | Explicit zero-based line index (default: read from file) |
| `step=`     | Lines to advance per call (default: 1)                   |

---

## Library API

```python
import pyti_lpc_cmd as lpc

# One-call render to file
with open("word.lpc", "rb") as f:
    data = f.read()

samples = lpc.render(data, chip="tms5220", wav="out.wav")

# Mono 44.1 kHz
lpc.render(data, chip="tms5220", wav="out_44k.wav",
           srate=44100, output="mono")

# Raw float samples, no file
samples = lpc.render(data, chip="tms5220")

# From hex CSV
data = lpc.load_hex_csv("A5,4F,7A,D3,3C,5A")
samples = lpc.render(data, chip="tms5220", wav="snippet.wav")

# Mid-level: synthesize then resample manually
chip   = lpc.get_builtin_chip("tms5220")
synth  = lpc.LPCSynthesizer()
pcm    = synth.synthesize(data, chip)
pcm44k = lpc.resample_qdss(pcm, 8000.0, 44100.0)
lpc.write_wav("out.wav", pcm44k, pcm44k, 44100, 16, 2, 0.90)
```

See [docs/pyti_lpc_cmd_paper.pdf](docs/pyti_lpc_cmd_paper.pdf) for the
full technical paper covering architecture, bitstream format, synthesis engine,
and complete API reference.

---

## Reference Test Vector

File: `0220_Affirmative.lpc` (TMS5220), 223 bytes
First 16 bytes: `A5 4F 7A D3 3C 5A 8F AE C8 A9 70 ED BD BA 2A 3B`

| Format                | Expected size |
|-----------------------|---------------|
| Stereo 16-bit 8 kHz WAV | 28044 bytes |
| Mono 16-bit 8 kHz WAV   | 14044 bytes |
| Mono 8-bit 8 kHz WAV    | 7044 bytes  |

35 frames total (33 data + 2 drain) = 7000 samples.

---

## Files

```
PyTI_LPC_CMD/
bin/
    pyti_lpc_cmd          -- executable wrapper script
docs/
    pyti_lpc_cmd.1        -- man page
    pyti_lpc_cmd_paper.tex               -- LaTeX source (LuaLaTeX)
    pyti_lpc_cmd_paper.pdf               -- compiled paper
    refs.bib              -- bibliography
    build_pdf.sh          -- PDF build script (lualatex + biber)
pyti_lpc_cmd/
    __init__.py           -- public library API
    __main__.py           -- CLI entry point
    cli.py                -- argument parser
    validators.py         -- input validation
    chip_params.py        -- ChipParams dataclass + .txt loader
    bitstream.py          -- BitstreamReader with bit-reversal
    frame_decoder.py      -- LPCFrame + decode_frame()
    synthesizer.py        -- LPCSynthesizer
    resampler.py          -- resample_qdss() windowed-sinc SRC
    audio_output.py       -- WAV / AU / AIFF / raw PCM writers
    input_loader.py       -- binary, CSV, hex-CSV, ROM loaders
    chips/
        tms5100.py        -- TMS5100 parameter tables
        tms5110.py        -- TMS5110 parameter tables
        tms5200.py        -- TMS5200 parameter tables
        tms5220.py        -- TMS5220 parameter tables
LICENSE                   -- GNU General Public License v3.0
README.md                 -- this file
```

---

## Implementation Notes

- Clean-room implementation -- no GPL source code was referenced
- Derived exclusively from TI patent literature, MAME (BSD), and the
  Talkie/Arduino community
- Bit reversal: each byte is reversed (nibble swap -> pair swap -> bit swap)
  before extraction, matching the original hardware's LSB-first ROM shifting
- Chirp values are stored as uint8 and reinterpreted as signed int8 before use
- The `from_` interpolation quirk: synthesis uses pre-interpolation parameter
  values at each sub-step, replicating original chip behaviour
- LFSR polynomial: 0xB800 (taps at bits 15, 14, 11, 10 of a 16-bit register)
- Infinite-loop guard: halts after 200 consecutive silence frames (~5 seconds)

---

## Copyright

Copyright (C) 2026 Kris Kirby, KE4AHR.
Licensed under the GNU General Public License v3.0 or later.
See [LICENSE](LICENSE) or https://www.gnu.org/licenses/gpl-3.0.html
