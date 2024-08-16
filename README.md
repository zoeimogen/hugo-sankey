Convers Hugo voting data into pretty graphs. For basic use, as long as you have python installed,
this should work with the provided input files. The input is simply copied and pasted from the
results PDFs, but some editing is needed to remove PDF ligitures (eg ti is often represented
by the number 7), insert newlines to make the data look nicer and remove any extra runoff rounds
against No Award.

The default output is suitable for pasting into [SankeyMatic.com](https://www.sankeymatic.com/build/),
or you can use the `-u` argument to get a direct URL.

For the hardcore user, if you have selenium installed then you can rapidly generate all the PNGs:

    for i in 2024/*txt; do ./generate_sankey.py --selenium --base-url 'http://localhost:8090/?i=' $i; done

The cookie banner on the actual website will likely break this, hence the locally running copy:

    git clone https://github.com/nowthis/sankeymatic.git
    cd sankeymatic/build
    python3 -m http.server 8090