# URL extractor
# Copyright 2004, Paul McGuire
from pyparsing import makeHTMLTags, SkipTo, pyparsing_common
import urllib.request
from contextlib import closing
import pprint

linkOpenTag, linkCloseTag = makeHTMLTags('a')

linkBody = SkipTo(linkCloseTag)
linkBody.setParseAction(pyparsing_common.stripHTMLTags)
linkBody.addParseAction(lambda toks: ' '.join(toks[0].strip().split()))

link = linkOpenTag + linkBody("body") + linkCloseTag.suppress()

# Go get some HTML with some links in it.
with closing(urllib.request.urlopen("http://www.yahoo.com")) as serverListPage:
    htmlText = serverListPage.read().decode("UTF-8")

# scanString is a generator that loops through the input htmlText, and for each
# match yields the tokens and start and end locations (for this application, we are
# not interested in the start and end values).
for toks,strt,end in link.scanString(htmlText):
    print(toks.asList())

# Create dictionary from list comprehension, assembled from each pair of tokens returned 
# from a matched URL.
pprint.pprint( 
    dict((toks.body, toks.href) for toks,strt,end in link.scanString(htmlText))
    )



