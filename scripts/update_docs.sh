#!/usr/bin/env bash
set -x

ssh app -t "dokku run vsb flask update-docs '*' && dokku run vsb flask clear-cache && cd /home/filter/code/verfassungsschutzberichte.de/scripts && bash prefill_cache.sh && sudo bash create_zips.sh"
