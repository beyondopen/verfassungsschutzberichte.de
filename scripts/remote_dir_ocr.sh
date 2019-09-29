#!/usr/bin/env bash
set -e
set -x

# loop over whole dir for OCR

for f in $(find $1 -type f -name "*.pdf"); do
    ./remote_ocr.sh $f
done
