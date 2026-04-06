#!/bin/bash
hexdump -v -e '/1 "0x%02x,"' "$FILE" | sed 's/,$//'
