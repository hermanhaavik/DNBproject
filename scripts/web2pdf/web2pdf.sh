#!/bin/sh

pdf_directory="./pdfs"
rm -rf $pdf_directory
mkdir $pdf_directory
while read i; do  
    # wkhtmltopdf --javascript-delay 10000 "$i" "${pdf_directory}/$(basename "$i").pdf";
    wkhtmltopdf -n "$i" "${pdf_directory}/$(basename "$i").pdf";
    # wkhtmltopdf "$i" "$(basename "$i").pdf";
    # wkhtmltopdf "$i" "$(echo "$i" | sed -e 's/https\?:\/\///' -e 's/\//-/g' ).pdf"
done
