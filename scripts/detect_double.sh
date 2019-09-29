#!/usr/bin/env bash
set -e


#  NOT WORKING FIXME

# extract page number and page width
page_pattern="^Page[^[:digit:]]*([[:digit:]]+) size[^[:digit:]]*([[:digit:]]+).[[:digit:]]+[^[:digit:]]*([[:digit:]]+).[[:digit:]]+[^[:digit:]]*"



for f in $(find $1 -type f -name "*.pdf"); do
  num_pages=$(qpdf --show-npages $f)

  echo $f
  pdfinfo -f 1 -l $num_pages $f | while read -r line ; do
    if [[ $line =~ $page_pattern ]]; then
      pn=${BASH_REMATCH[1]}
      if [[ ${BASH_REMATCH[2]} -gt ${BASH_REMATCH[3]} ]]; then
        echo 'doubled page'
        echo $pn
      fi
    fi
  done
done



