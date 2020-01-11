#!/usr/bin/env bash
set -x

rm /mnt/data/temp-data/vsberichte.zip;
cd /mnt/data/temp-data && /usr/bin/zip -r -j /mnt/data/temp-data/vsberichte.zip /mnt/data/vsb/vsb-data/pdfs

mkdir -p /mnt/data/temp-data/tmp-texts/ &&
rm /mnt/data/temp-data/tmp-texts/* &&
curl https://vsb.app.vis.one/api/ | jq -r '.reports[].jurisdiction_escaped' | while read -r line; do
  for y in {1950..2020}; do
    wget https://vsb.app.vis.one/$line-$y.txt -P /mnt/data/temp-data/tmp-texts
  done
done

cd /mnt/data/temp-data &&
	rm /mnt/data/temp-data/vsberichte-texts.zip;
	/usr/bin/zip -r -j /mnt/data/temp-data/vsberichte-texts.zip /mnt/data/temp-data/tmp-texts &&
	scp /mnt/data/temp-data/vsberichte*.zip filter@berlin.jfilter.de:/var/www/data.jfilter.de/html/ &&
  rm /mnt/data/temp-data/vsberichte*.zip && rm -rf /mnt/data/temp-data/tmp-texts
