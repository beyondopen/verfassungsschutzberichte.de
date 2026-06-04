#!/usr/bin/env bash
set -x

ssh ubuntu@10.10.10.100 -t "sudo dokku run vsb flask update-docs '*' && sudo dokku run vsb flask clear-cache && sudo dokku run vsb flask create-zips"
