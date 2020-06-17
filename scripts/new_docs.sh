#!/usr/bin/env bash
set -x

# $1: location of folder with PDF-files
# $2: `process` or `upload`

# TODO: right now, you have to manually create a .raw folder to upload raw files

if [[ "$1" != /* ]]; then
    echo "only absolute paths"
    exit 1
fi

if [ "$2" == "process" ]; then
    cp -r "$1" "$1".done
    cd ~/code/pdf-scripts && ./pipeline.sh -l deu -o 1 "$1".done
    exit 0
fi

if [ "$2" == "upload" ]; then
    echo 'uploading to server'
    scp "$1"/* md:/mnt/data/vsb/vsb-all/cleaned/
    scp "$1".done/* md:/mnt/data/vsb/vsb-data/pdfs/
    [ -d "$1".raw ] && scp "$1".raw/* md:/mnt/data/vsb/vsb-all/raw/
    ./update_docs.sh
    exit 0
fi

echo 'invalid input'
exit 1
