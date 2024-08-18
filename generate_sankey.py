#!/usr/bin/env python3
# pylint: disable=cell-var-from-loop

'''A quick and dirty script to convert copy-pasted Hugo voting data into something that will
   work in Sankeymatic.'''

import re
import argparse
import tempfile
import os
import urllib.parse
import time

# Don't make lzstring mandatory
try:
    import lzstring
    x = lzstring.LZString()
except ImportError:
    x = None

# Most people aren't going to want to mess with Selenium
try:
    from selenium import webdriver
    browser = True
except ImportError:
    browser = None

# Footer for correct formatting. May require tweaking for size - 2000x800 is fine for most of 2024.
SANKEY_SETTINGS = '''
size w %WIDTH%
  h %HEIGHT%
margin l 12
  r 12
  t 18
  b 20
bg color #ffffff
  transparent N
node w 12
  h 50
  spacing 75
  border 0
  theme a
  color #888888
  opacity 1
flow curvature 0.5
  inheritfrom outside-in
  color #999999
  opacity 0.45
layout order exact
  justifyorigins N
  justifyends N
  reversegraph N
  attachincompletesto nearest
labels color #000000
  hide N
  highlight 0.75
  fontface sans-serif
  linespacing 0.2
  relativesize 110
  magnify 100
labelname appears Y
  size 16
  weight 400
labelvalue appears Y
  fullprecision Y
  position below
  weight 400
labelposition autoalign 0
  scheme auto
  first before
  breakpoint 7
value format ',.'
  prefix ''
  suffix ''
themeoffset a 9
  b 0
  c 0
  d 0
meta mentionsankeymatic Y
  listimbalances Y
'''

def read_candidates_from_file(filename, eph):
    '''Read candidates from file. (stdin or filename on command line)'''
    candidates = {}
    if eph:
        # EPH data: vote counts are floats
        r = re.compile(r'^(.*?)(\d+[\d\s.]*)$')
    else:
        r = re.compile(r'^(.*?)(\d+[\d\s]*)$')

    with open(filename, 'r') as f:
        for line in f:
            # This breaks on things like "Baldur's Gate 3" because "3" looks like a first round
            # vote count.
            match = r.match(line.strip())
            if match:
                candidate = match.group(1).strip()
                if eph:
                    # Floats and skip the first number (Raw nominations, uninteresting under EPH)
                    votes = list(map(float, match.group(2).split()))[1:]
                else:
                    votes = list(map(int, match.group(2).split()))
                candidates[candidate] = votes
    return candidates

def next_round_votes(candidates, i, x):
    '''Figure out how many votes Candidate X received in the next round, or zero if eliminated'''
    try:
        return candidates[x][i+1]
    except IndexError:
        return 0


def vote_fmt(votes, eph):
    if eph:
        return(f'{votes:.2f}')
    else:
        return(f'{votes}')

def print_transfers(candidates, rounds, eph, offset):
    '''Print the transfers for each round'''

    # Some data is cached and output last - the order in which a candidate is mentioned for each
    # round is critical as that affects the placement on the sankey chart when "Using the exact
    # input order" is selected.
    output = ""
    no_transfer = []
    transfer_output = []

    for i in range(rounds-1):
        # Get all candidates from this round
        eligible_candidates = [c for c in candidates.keys() if len(candidates[c]) > i]

        # Sort candidates into their position in the *next* round. This is because the first thing
        # we output is their self-transfer to the next round - and the order of those mentions is
        # what controls the position on the next round graph.
        sorted_candidates = sorted(eligible_candidates, reverse=True,
                                   key=lambda x: next_round_votes(candidates, i, x))

        for c in sorted_candidates:
            if len(candidates[c]) > i+1:
                # Transfer all the existing votes for this candidate to the next round
                output += f"{c}\\nRound {i + 1 + offset} [{vote_fmt(candidates[c][i], eph)}] {c}\\nRound {i + 2 + offset}\n"
            else:
                # Eliminate a candidate and transfer their votes, based on the diff to the next
                # round totals. Order matters here to put flows in the correct order on the output
                # graph. (i.e. avoids excessive overlapping flows.)
                transfers = [t for t in sorted_candidates if len(candidates[t]) > i+1]
                total = 0
                for t in transfers:
                    diff = candidates[t][i + 1] - candidates[t][i]
                    total += diff
                    if diff > 0:
                        # Don't bother outputting zero transfers.
                        transfer_output.append(f"{c}\\nRound {i + 1 + offset} [{vote_fmt(diff, eph)}] {t}\\nRound {i + 2 + offset}")
                remainder = candidates[c][i] - total
                if remainder > 0:
                    no_transfer.append(f"{c}\\nRound {i + 1 + offset} [{vote_fmt(remainder, eph)}] No Transfer")

    output += '\n'.join(transfer_output) + '\n'

    # No Transfer is last so it appears at the bottom right corner of the output.
    output += '\n'.join(reversed(no_transfer))
    return(output + "\n")

def download_file(url, filename):
    '''Download a file via the local selenium driver'''

    # Here be dragons!
    # This probably won't work without a local copy of sankeymatic, as there's a cookie banner. I
    # did a git clone of https://github.com/nowthis/sankeymatic.git, then ran 
    # "python3 -m http.server 8090" from the build directory. Using 
    # "--selenium --base-url 'http://localhost:8090/?i='" should then work. Selenium setups are
    # fragile, this may not work for you.

    profile = webdriver.FirefoxProfile()
    downloads = tempfile.TemporaryDirectory()
    options = webdriver.firefox.options.Options()
    options.set_preference("browser.download.folderList", 2)
    options.set_preference("browser.download.manager.showWhenStarting", False)
    options.set_preference('browser.download.dir', downloads.name)

    browser = webdriver.Firefox(options=options)
    browser.get(url)
    time.sleep(1)
    button = browser.find_element(webdriver.common.by.By.XPATH, "//*[text()='Save as a .PNG image']")
    button.click()
    time.sleep(1)
    files = [f for f in os.listdir(downloads.name) if os.path.isfile(os.path.join(downloads.name, f))]
    if len(files) != 1:
        print(f"Expected exactly one output PNG file, got {len(files)}")
    else:
        output_filename = os.path.join(os.path.dirname(os.path.realpath(filename)),
                               os.path.splitext(os.path.basename(filename))[0] + ".png")
        os.rename(os.path.join(downloads.name, files[0]),
                  output_filename)
        print(f"Saved {output_filename}")
    browser.close()
    browser.quit()
    downloads.cleanup()

def main():
    '''Main code entry point'''
    parser = argparse.ArgumentParser(
                    prog='generate_sankey',
                    description='Convert copy-pasted Hugo voting data into sankeymatic input',
                    epilog='Text at the bottom of help')
    
    parser.add_argument('filename', help='Input filename')

    parser.add_argument('-o', '--output',
                        help='Override default output filename')

    parser.add_argument('--width',
                        help='Override default width',
                        type=int,
                        default=2000)
    
    parser.add_argument('--height',
                        help='Override default height',
                        type=int,
                        default=800)

    parser.add_argument('--eph',
                    action='store_true',
                    help='Input data is E Pluribus Hugo format (Nominations data)')
    
    parser.add_argument('--initial-round',
                    help='Set initial round nubmber (Used for EPH nominations)',
                    default=1, type=int)

    parser.add_argument('-s', '--stdout',
                    action='store_true',
                    help='Output to stdout insted of file (for non-batch use)')
    
    parser.add_argument('-u', '--url-output',
                    action='store_true',
                    help='Output a sankeymatic URL rather than data string (Requires lzstring)')
    
    parser.add_argument('-b', '--base-url',
                    default='https://www.sankeymatic.com/build/?i=',
                    help='Base Sankeymatic URL (eg for locally hosted version)')
    
    parser.add_argument('--selenium',
                    action='store_true',
                    help='HARDCORE MODE: Use local selenium driver to automatically save PNG')
    
    args = parser.parse_args()

    if (args.url_output or args.selenium) and x is None:
        print("lzstring required for url or selenium output. (Hint: pip install lzstring)")
        exit(-1)

    if args.selenium and browser is None:
        print("You need a working Selenium/Firefox install. This is intended for expert users only, see https://pypi.org/project/selenium/")
        exit(-1)

    candidates = read_candidates_from_file(args.filename, args.eph)
    rounds = max(len(votes) for votes in candidates.values())

    output = print_transfers(candidates, rounds, args.eph, args.initial_round - 1)

    # Don't use Jinja so users don't need to install extra stuff if not using -u or --selenium
    output += SANKEY_SETTINGS.replace('%WIDTH%', f'{args.width}').replace('%HEIGHT%', f'{args.height}')

    if args.stdout:
        print(output)
    elif args.url_output:
        url = args.base_url + urllib.parse.quote(x.compressToEncodedURIComponent(output))
        print(url)
    elif args.selenium:
        url = args.base_url + urllib.parse.quote(x.compressToEncodedURIComponent(output))
        download_file(url, args.filename)
    else:
        if args.output:
            output_filename = args.output
        else:
            output_filename = os.path.splitext(args.filename)[0] + ".out"
        with open(output_filename, 'w') as f:
            f.write(output)
        print(f"Wrote {output_filename}")

if __name__ == "__main__":
    main()
