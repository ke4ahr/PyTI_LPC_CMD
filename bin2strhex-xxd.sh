#!/bin/bash
xxd -p "$FILE" | sed 's/../&,/g; s/,$//'
