# Visualsing the Hugos

## Basic use

Converts Hugo voting data into pretty graphs. For basic use, as long as you have [python](https://www.python.org/downloads/) installed,
this should work with the provided input files. The input is simply copied and pasted from the
results PDFs, but some editing is needed to remove PDF ligitures (eg ti is often represented
by the number 7), insert newlines to make the data look nicer and remove any extra runoff rounds
against No Award.

The default output is suitable for pasting into [SankeyMatic.com](https://www.sankeymatic.com/build/):

    % ./generate_sankey.py 2024/best-novel-1.txt 
    Wrote 2024/best-novel-1.out

Or you can use the `-u` argument to get a direct URL:

    % pip install lzstring
    % ./generate_sankey.py -u 2024/best-novel-1.txt 
    https://www.sankeymatic.com/build/?i=MoewtgpgBAIhDOAHCAnAhgF2gcQD...

## Advanced users

For the hardcore user, if you have selenium installed then you can rapidly generate all the PNGs:

    % pip install lzstring selenium
    % for i in 2024/*txt; do ./generate_sankey.py --selenium --base-url 'http://localhost:8090/?i=' $i; done

The cookie banner on the actual website will likely break this, hence the locally running copy:

    % git clone https://github.com/nowthis/sankeymatic.git
    % cd sankeymatic/build
    % python3 -m http.server 8090