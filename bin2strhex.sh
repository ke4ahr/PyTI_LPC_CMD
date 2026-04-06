#!/bin/bash

# Check if a file was provided as an argument
if [ $# -eq 0 ]; then
    echo "Usage: $0 <binary_file>"
    exit 1
fi

FILE=$1

# 1. hexdump -v: display all input data (no '*' for repeated lines)
# 2. -e '/1 "%02x,"': format 1 byte as 2-digit hex followed by a comma
# 3. sed 's/,$//': remove the very last trailing comma
hexdump -v -e '/1 "%02x,"' "$FILE" | sed 's/,$//'
echo # Add a newline at the end
