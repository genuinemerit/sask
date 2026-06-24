#!/usr/bin/env bash
# Reference snippets for converting/optimizing jpg/png to webp.
#
# This file is NOT meant to be executed top-to-bottom — the input/output
# filenames below are placeholders. Copy the one line you need into your
# shell, substituting real paths.

# lossy webp, tuned
# cwebp -q 80 -m 6 -mt -af input.jpg -o output.webp

# target-bytes encode (WebP can aim at size!)
# cwebp input.png -size 100000 -o output.webp   # ~100KB target

# lossless (for UI with alpha if needed)
# cwebp -lossless -m 6 input.png -o output.webp

# great for tidying up sprites/UI
# pngquant --quality=60-90 --strip --speed 1 --force --output out.png in.png
# oxipng -o6 --strip all out.png
