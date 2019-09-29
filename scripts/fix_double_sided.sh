#!/usr/bin/env bash
set -e
set -x

# take over last and first page

# mutool clean $1 $1 &&
# n1=$(qpdf --show-npages $1) &&
# mutool poster -x 2 $1 split.pdf &&
# n2=$(qpdf --show-npages split.pdf)
# n22=2
# n2=$((n2-n22))
# pdftk $1 cat 1 output 1.pdf &&
# pdftk $1 cat $n1 output 2.pdf &&
# pdftk split.pdf cat 3-$n2 output cut.pdf &&
# pdftk 1.pdf cut.pdf 2.pdf cat output final.pdf


# take over first to pages

# mutool clean $1 $1 &&
# n1=$(qpdf --show-npages $1) &&
# mutool poster -x 2 $1 split.pdf &&
# n2=$(qpdf --show-npages split.pdf)
# n22=2
# n2=$((n2-n22))
# pdftk $1 cat 1-2 output 1.pdf &&
# pdftk split.pdf cat 5-end output cut.pdf &&
# pdftk 1.pdf cut.pdf cat output final.pdf