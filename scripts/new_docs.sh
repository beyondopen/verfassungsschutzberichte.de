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
    # dokku01 VM (prague-1 infra); /mnt/data/vsb is owned by the container
    # user (32767), so stage via /tmp and install with sudo
    host=ubuntu@10.10.10.100
    ssh $host "mkdir -p /tmp/vsb-upload/cleaned /tmp/vsb-upload/pdfs /tmp/vsb-upload/raw"
    scp "$1"/* $host:/tmp/vsb-upload/cleaned/
    scp "$1".done/* $host:/tmp/vsb-upload/pdfs/
    [ -d "$1".raw ] && scp "$1".raw/* $host:/tmp/vsb-upload/raw/
    ssh $host "sudo install -o 32767 -g 32767 -m 644 /tmp/vsb-upload/cleaned/* /mnt/data/vsb/cleaned/ \
        && sudo install -o 32767 -g 32767 -m 644 /tmp/vsb-upload/pdfs/* /mnt/data/vsb/pdfs/ \
        && { ! ls /tmp/vsb-upload/raw/* >/dev/null 2>&1 || sudo install -o 32767 -g 32767 -m 644 /tmp/vsb-upload/raw/* /mnt/data/vsb/raw/; } \
        && rm -rf /tmp/vsb-upload"
    ./update_docs.sh
    exit 0
fi

echo 'invalid input'
exit 1
