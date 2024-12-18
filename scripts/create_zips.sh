#!/usr/bin/env bash
set -x

mkdir -p /mnt/data/temp-data && rm -rf /mnt/data/temp-data/* && cd /mnt/data/temp-data && /usr/bin/zip -r -j /mnt/data/temp-data/vsberichte.zip /mnt/data/vsb/vsb-data/pdfs

mkdir -p /mnt/data/temp-data/tmp-texts/ &&
  rm /mnt/data/temp-data/tmp-texts/*
curl https://verfassungsschutzberichte.de/api | jq -r '.reports[].jurisdiction_escaped' | while read -r line; do
  for y in {1950..2030}; do
    wget https://verfassungsschutzberichte.de/$line-$y.txt -P /mnt/data/temp-data/tmp-texts
  done
done

cd /mnt/data/temp-data &&
  rm /mnt/data/temp-data/vsberichte-texts.zip
/usr/bin/zip -r -j /mnt/data/temp-data/vsberichte-texts.zip /mnt/data/temp-data/tmp-texts &&
  mv /mnt/data/temp-data/vsberichte*.zip /mnt/data/data-portal/ &&
  rm -rf /mnt/data/temp-data
