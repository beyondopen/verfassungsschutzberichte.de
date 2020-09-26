#!/usr/bin/env bash
set -x

ssh md -t "dokku run vsb flask update-docs '*' && dokku run vsb flask clear-cache && cd /home/filter/code/verfassungsschutzberichte.de/scripts && sudo bash create_zips.sh"
