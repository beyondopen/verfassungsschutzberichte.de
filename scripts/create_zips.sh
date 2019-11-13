#!/usr/bin/env bash
set -x

rm /home/filter/data/data-portal/vsberichte.zip;
cd /home/filter/data/data-portal && /usr/bin/zip -r -j /home/filter/data/data-portal/vsberichte.zip /home/filter/data/vsb-data/pdfs

rm -rf /home/filter/data/vsb-data/tmp_texts &&
curl https://vsb.app.vis.one/api/ | jq -r '.reports[].jurisdiction_escaped' | while read -r line; do
  for y in {1950..2020}; do
    wget https://vsb.app.vis.one/$line-$y.txt -P /home/filter/data/vsb-data/tmp_texts
  done
done

cd /home/filter/data/data-portal &&
	rm /home/filter/data/data-portal/vsberichte-texts.zip;
	/usr/bin/zip -r -j /home/filter/data/data-portal/vsberichte-texts.zip /home/filter/data/vsb-data/tmp_texts &&
	scp /home/filter/data/data-portal/vsberichte*.zip filter@berlin.jfilter.de:/var/www/data.jfilter.de/html/
