# URL extractor
# Copyright 2004, Paul McGuire
from pyparsing import make_html_tags, pyparsing_common as ppc
from urllib.request import urlopen
import pprint

linkOpenTag, linkCloseTag = make_html_tags("a")

linkBody = linkOpenTag.tag_body
linkBody.set_parse_action(ppc.strip_html_tags)
linkBody.add_parse_action(lambda toks: " ".join(toks[0].strip().split()))

link = linkOpenTag + linkBody("body") + linkCloseTag.suppress()

# Go get some HTML with some links in it.
with urlopen("https://www.cnn.com/") as serverListPage:
    htmlText = serverListPage.read().decode("UTF-8")

# scan_string is a generator that loops through the input htmlText, and for each
# match yields the tokens and start and end locations (for this application, we are
# not interested in the start and end values).
for toks, strt, end in link.scan_string(htmlText):
    print(toks.as_list())

# Create dictionary from list comprehension, assembled from each pair of tokens returned
# from a matched URL.
pprint.pprint({toks.body: toks.href for toks, strt, end in link.scan_string(htmlText)})
