#!/usr/bin/env python3
# clean_man_unicode.py -- replace Unicode chars in man pages with nroff equivalents
# Copyright (C) 2026 Kris Kirby, KE4AHR -- Licensed GPLv3.0
#
# Usage:
#   python3 clean_man_unicode.py input.1 [output.1]
#   python3 clean_man_unicode.py input.1          (overwrites in place)
#
# Replaces Unicode characters that may not survive all man page pipeline
# tools (plain groff, man on BSD/macOS, etc.) with portable nroff escapes
# or ASCII equivalents.

import sys
import re

# Mapping: Unicode char -> nroff escape or ASCII equivalent
# nroff escapes: \(em = em dash, \(en = en dash, \(->  = right arrow, etc.
# Where no nroff glyph exists, a close ASCII approximation is used.
REPLACEMENTS = [
    # Dashes
    ("\u2014", r"\(em"),    # EM DASH                 —  ->  \(em
    ("\u2013", r"\(en"),    # EN DASH                 -  ->  \(en
    ("\u2012", "-"),        # FIGURE DASH             -  ->  -

    # Arrows
    ("\u2192", r"\(->"),    # RIGHTWARDS ARROW        ->  ->  \(->
    ("\u2190", r"\(<-"),    # LEFTWARDS ARROW         <-  ->  \(<-
    ("\u2194", "<->"),      # LEFT RIGHT ARROW        <-> ->  <->
    ("\u21d2", "=>"),       # RIGHTWARDS DOUBLE ARROW
    ("\u21d4", "<=>"),      # LEFT RIGHT DOUBLE ARROW

    # Quotation marks
    ("\u2018", "`"),         # LEFT SINGLE QUOTATION MARK
    ("\u2019", "'"),         # RIGHT SINGLE QUOTATION MARK
    ("\u201c", "``"),        # LEFT DOUBLE QUOTATION MARK
    ("\u201d", "''"),        # RIGHT DOUBLE QUOTATION MARK

    # Ellipsis
    ("\u2026", r"\&..."),   # HORIZONTAL ELLIPSIS

    # Mathematical operators
    ("\u00d7", r"\(mu"),    # MULTIPLICATION SIGN     x   ->  \(mu
    ("\u00f7", "/"),        # DIVISION SIGN
    ("\u00b1", r"\(+-"),    # PLUS-MINUS SIGN         +-  ->  \(+-
    ("\u2212", r"\(mi"),    # MINUS SIGN              -   ->  \(mi
    ("\u2260", r"!="),      # NOT EQUAL TO
    ("\u2264", "<="),       # LESS-THAN OR EQUAL TO
    ("\u2265", ">="),       # GREATER-THAN OR EQUAL TO
    ("\u221e", r"\(if"),    # INFINITY                inf ->  \(if
    ("\u2248", "~="),       # ALMOST EQUAL TO
    ("\u00b2", "^2"),       # SUPERSCRIPT TWO
    ("\u00b3", "^3"),       # SUPERSCRIPT THREE
    ("\u00b9", "^1"),       # SUPERSCRIPT ONE

    # Greek letters (common in technical/math contexts)
    ("\u03b1", r"\(*a"),    # alpha    ->  \(*a
    ("\u03b2", r"\(*b"),    # beta     ->  \(*b
    ("\u03b3", r"\(*g"),    # gamma    ->  \(*g
    ("\u03b4", r"\(*d"),    # delta    ->  \(*d
    ("\u03b5", r"\(*e"),    # epsilon  ->  \(*e
    ("\u03b8", r"\(*h"),    # theta    ->  \(*h
    ("\u03bb", r"\(*l"),    # lambda   ->  \(*l
    ("\u03bc", r"\(*m"),    # mu       ->  \(*m
    ("\u03c0", r"\(*p"),    # pi       ->  \(*p
    ("\u03c3", r"\(*s"),    # sigma    ->  \(*s
    ("\u03c4", r"\(*t"),    # tau      ->  \(*t
    ("\u03c6", r"\(*f"),    # phi      ->  \(*f
    ("\u03c9", r"\(*w"),    # omega    ->  \(*w
    ("\u0394", r"\(*D"),    # Delta    ->  \(*D
    ("\u03a3", r"\(*S"),    # Sigma    ->  \(*S
    ("\u03a9", r"\(*W"),    # Omega    ->  \(*W

    # Misc typographic
    ("\u00a9", r"\(co"),    # COPYRIGHT SIGN  (c)  ->  \(co
    ("\u00ae", r"\(rg"),    # REGISTERED SIGN  (R)  ->  \(rg
    ("\u2122", "TM"),       # TRADE MARK SIGN
    ("\u00a0", " "),        # NO-BREAK SPACE -> regular space
    ("\u00ad", ""),         # SOFT HYPHEN -> remove
    ("\u2022", r"\(bu"),    # BULLET  ->  \(bu
    ("\u2019", "'"),        # RIGHT SINGLE QUOTATION MARK -> apostrophe
    ("\u00e9", r"\('e"),    # e with acute accent
    ("\u00e8", r"\(`e"),    # e with grave accent
    ("\u00e4", r"\(:a"),    # a with diaeresis
    ("\u00f6", r"\(:o"),    # o with diaeresis
    ("\u00fc", r"\(:u"),    # u with diaeresis

    # Section sign
    ("\u00a7", "sec."),     # SECTION SIGN  sec.

    # Box drawing (commonly used in code comments, not valid in man pages)
    ("\u2500", "-"),        # BOX DRAWINGS LIGHT HORIZONTAL
    ("\u2502", "|"),        # BOX DRAWINGS LIGHT VERTICAL
    ("\u250c", "+"),        # BOX DRAWINGS LIGHT DOWN AND RIGHT
    ("\u2510", "+"),        # BOX DRAWINGS LIGHT DOWN AND LEFT
    ("\u2514", "+"),        # BOX DRAWINGS LIGHT UP AND RIGHT
    ("\u2518", "+"),        # BOX DRAWINGS LIGHT UP AND LEFT
    ("\u251c", "+"),        # BOX DRAWINGS LIGHT VERTICAL AND RIGHT
    ("\u2524", "+"),        # BOX DRAWINGS LIGHT VERTICAL AND LEFT
    ("\u252c", "+"),        # BOX DRAWINGS LIGHT DOWN AND HORIZONTAL
    ("\u2534", "+"),        # BOX DRAWINGS LIGHT UP AND HORIZONTAL
    ("\u253c", "+"),        # BOX DRAWINGS LIGHT VERTICAL AND HORIZONTAL
]


def clean_line(line):
    for char, replacement in REPLACEMENTS:
        line = line.replace(char, replacement)
    return line


def clean_file(text):
    lines = text.split("\n")
    cleaned = [clean_line(line) for line in lines]
    return "\n".join(cleaned)


def check_remaining(text):
    """Return list of (char, codepoint, count) for any remaining non-ASCII chars."""
    counts = {}
    for ch in text:
        if ord(ch) > 127:
            counts[ch] = counts.get(ch, 0) + 1
    return [(ch, hex(ord(ch)), n) for ch, n in sorted(counts.items())]


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print(__doc__)
        print("Usage: clean_man_unicode.py input.1 [output.1]")
        return 0

    inpath = sys.argv[1]
    outpath = sys.argv[2] if len(sys.argv) > 2 else inpath

    try:
        with open(inpath, encoding="utf-8") as f:
            text = f.read()
    except OSError as e:
        print(f"Error reading {inpath}: {e}", file=sys.stderr)
        return 1

    cleaned = clean_file(text)

    remaining = check_remaining(cleaned)
    if remaining:
        print(f"Warning: {len(remaining)} unmapped non-ASCII character(s) remain:", file=sys.stderr)
        for ch, cp, n in remaining:
            print(f"  U+{ord(ch):04X} ({cp})  '{ch}'  x{n}", file=sys.stderr)

    try:
        with open(outpath, "w", encoding="utf-8") as f:
            f.write(cleaned)
    except OSError as e:
        print(f"Error writing {outpath}: {e}", file=sys.stderr)
        return 1

    action = "overwritten" if outpath == inpath else f"written to {outpath}"
    print(f"{inpath}: {action}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
