import urllib.request, urllib.parse, urllib.error

from pyparsing import makeHTMLTags, SkipTo

# read HTML from a web page
serverListPage = urllib.request.urlopen( "http://www.yahoo.com" )
htmlText = serverListPage.read()
serverListPage.close()

# using makeHTMLTags to define opening and closing tags
anchorStart,anchorEnd = makeHTMLTags("a")

# compose an expression for an anchored reference
anchor = anchorStart + SkipTo(anchorEnd)("body") + anchorEnd

# use scanString to scan through the HTML source, extracting
# just the anchor tags and their associated body text
# (note the href attribute of the opening A tag is available
# as an attribute in the returned parse results)
for tokens,start,end in anchor.scanString(htmlText):
    print(tokens.body,'->',tokens.href)
