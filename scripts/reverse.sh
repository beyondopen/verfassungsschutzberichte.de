#!/usr/bin/env bash
set -e
set -x

pdftk $1 cat end-1 output $1.reversed