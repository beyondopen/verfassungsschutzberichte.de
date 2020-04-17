#!/usr/bin/env bash
set -e
set -x

# OCRs a PDF on a server and then get's it back
# Maker sure to check the roation of the pages manually

# pdfsizeopt
# --use-pngout=no because it was __VERY__ slow

# 1. Repair corrupted PDFs
# 2. Unlock PDFs
# 3. OCR
# 4. Further Reduce File Size

# https://github.com/jbarlow83/OCRmyPDF/issues/316
# hocr renderer prevents 'clobbing of words' (ThereIsNoSpaceBetweenUs)

server="sn"
location="~/pdfproc"
out=$1
echo $1

ssh $server 'mkdir -p ~/pdfproc' &&
scp $1 $server:$location/tmp.pdf &&
ssh $server 'cd ~/pdfproc &&
   mutool clean tmp.pdf tmp.pdf &&
   qpdf --decrypt tmp.pdf tmp2.pdf && mv tmp2.pdf tmp.pdf &&
   docker run --rm -v "$(pwd):/data" jbarlow83/ocrmypdf -l deu --pdf-renderer hocr --deskew --output-type pdf --clean --skip-text --optimize 1  --jbig2-lossy /data/tmp.pdf /data/tmp_ocr.pdf &&
   docker run --rm -v "$PWD:/workdir" -u "$(id -u):$(id -g)" ptspts/pdfsizeopt pdfsizeopt --use-pngout=no tmp_ocr.pdf tmp_ocr_cleaned.pdf &&
   rm tmp.pdf && rm tmp_ocr.pdf' &&
scp $server:$location/tmp_ocr_cleaned.pdf $out

   # docker run --rm -v "$(pwd):/data" jbarlow83/ocrmypdf -l deu --pdf-renderer hocr --output-type pdf  --skip-text --optimize 0  --jbig2-lossy /data/tmp.pdf /data/tmp_ocr.pdf &&





# ssh $server 'mkdir -p ~/pdfproc' &&
# scp $1 $server:$location/tmp.pdf &&
# ssh $server 'cd ~/pdfproc &&
#    mutool clean tmp.pdf tmp.pdf &&
#    pdftocairo -pdf tmp.pdf tmp2.pdf && mv tmp2.pdf tmp.pdf &&
#    qpdf --decrypt tmp.pdf tmp2.pdf && mv tmp2.pdf tmp.pdf &&
#    docker run --rm -v "$(pwd):/home/docker" jbarlow83/ocrmypdf -l deu --pdf-renderer hocr --deskew --output-type pdf --clean --skip-text --optimize 0 --jbig2-lossy tmp.pdf tmp_ocr.pdf &&
#    docker run --rm -v "$PWD:/workdir" -u "$(id -u):$(id -g)" ptspts/pdfsizeopt pdfsizeopt --use-pngout=no tmp_ocr.pdf tmp_ocr_cleaned.pdf &&
#    rm tmp.pdf && rm tmp_ocr.pdf' &&
# scp $server:$location/tmp_ocr_cleaned.pdf $out

