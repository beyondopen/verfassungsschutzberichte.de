#!/usr/bin/env bash
set -x

# Arguments:
# $1: location of a folder with PDF files
# $2: `process` or `upload`

# Usage:
# ./new_docs thefolder process
# ./new_docs thefolder upload

# Right now, you have to manually create a `thefolder.raw` folder to upload raw files.

if [[ "$1" != /* ]]; then
    echo "only absolute paths"
    exit 1
fi

path=$1
if [[ "${path: -1}" == "/" ]]; then
    echo "remove trailing slash"
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
