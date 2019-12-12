#!/usr/bin/env bash
set -e
set -x

# convert -compress Zip -density 150x150 $1 compressed.$1

# gs -sDEVICE=pdfwrite -dCompatibilityLevel=1.4 -dPDFSETTINGS=/printer -dNOPAUSE -dQUIET -dBATCH -sOutputFile=output.pdf ~/Desktop/vs.pdf

gs -sDEVICE=pdfwrite -dCompatibilityLevel=1.4 -dPDFSETTINGS=/default \
    -dNOPAUSE -dQUIET -dBATCH -dDetectDuplicateImages \
    -dCompressFonts=true -r150 -sOutputFile=$1.output.pdf $1