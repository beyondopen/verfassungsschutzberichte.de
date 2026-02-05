#!/usr/bin/env bash
set -x

ssh md -t "dokku run vsb flask update-docs '*' && dokku run vsb flask clear-cache && dokku run vsb flask create-zips"
