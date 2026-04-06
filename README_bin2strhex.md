# bin2strhex.py

Convert a binary file to a comma-separated hex string (strhex).

## Requirements

- Python 3.6+
- No third-party dependencies

## Usage

```
python3 bin2strhex.py [OPTIONS] bin_file
```

## Arguments

| Argument | Description |
|---|---|
| `bin_file` | Input binary file |

## Options

| Option | Default | Description |
|---|---|---|
| `--endian {little,lsb,big,msb}` | `little` | Byte order for multi-byte words. `little` and `lsb` are equivalent; `big` and `msb` are equivalent. Has no effect when `--word-size 1`. |
| `--word-size {1,2,4}` | `1` | Word size in bytes. Bytes are grouped into words before hex formatting. |
| `--prefix TEXT` | `0x` | Prefix prepended to each hex value. |
| `--no-prefix` | off | Omit the hex prefix entirely. |
| `-o, --output FILE` | stdout | Write output to FILE instead of stdout. |

## Output Format

Each word is formatted as uppercase hex with leading zeros to fill the word width,
separated by commas, with no trailing comma. One line of output is produced.

## Examples

### Byte-by-byte (default)

```
python3 bin2strhex.py data.lpc
```

```
0xA5,0x4F,0x7A,0xD3,0x3C,0x5A,...
```

### 16-bit little-endian (LSB first)

```
python3 bin2strhex.py --word-size 2 --endian lsb data.lpc
```

```
0x4FA5,0xD37A,0x5A3C,...
```

### 16-bit big-endian (MSB first)

```
python3 bin2strhex.py --word-size 2 --endian msb data.lpc
```

```
0xA54F,0x7AD3,0x3C5A,...
```

### 32-bit big-endian, no prefix

```
python3 bin2strhex.py --word-size 4 --endian big --no-prefix data.lpc
```

```
A54F7AD3,3C5A8FAE,...
```

### Write to file

```
python3 bin2strhex.py -o output.txt data.lpc
```

## Notes

- If the file size is not a multiple of `--word-size`, trailing bytes are zero-padded
  and a warning is printed to stderr.
- Endian setting only affects output when `--word-size` is 2 or 4.
- TMS5xxx LPC bitstream data is LSB-first; use `--endian little` (default) for
  byte-accurate representation when grouping into words.
