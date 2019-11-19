#!/usr/bin/env bash
set -e
set -x

convert -compress Zip -density 150x150 $1 compressed.$1