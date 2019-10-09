#!/usr/bin/env bash
set -e
set -x

# download but through away
wget -e robots=off --delete-after --verbose --recursive --level 2 https://vsb.app.vis.one 
