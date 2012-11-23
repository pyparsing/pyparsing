# getNTPserversNew.py
#
# Demonstration of the parsing module, implementing a HTML page scanner,
# to extract a list of NTP time servers from the NIST web site.
#
# Copyright 2004-2010, by Paul McGuire
# September, 2010 - updated to more current use of setResultsName, new NIST URL
#
from pyparsing import (Word, Combine, Suppress, SkipTo, nums, makeHTMLTags,
                        delimitedList, alphas, alphanums)
import urllib.request, urllib.parse, urllib.error

integer = Word(nums)
ipAddress = Combine( integer + "." + integer + "." + integer + "." + integer )
hostname = delimitedList(Word(alphas,alphanums+"-_"),".",combine=True)
tdStart,tdEnd = makeHTMLTags("td")
timeServerPattern =  (tdStart + hostname("hostname") + tdEnd + 
                      tdStart + ipAddress("ipAddr") + tdEnd + 
                      tdStart + SkipTo(tdEnd)("loc") + tdEnd)

# get list of time servers
nistTimeServerURL = "http://tf.nist.gov/tf-cgi/servers.cgi#"
serverListPage = urllib.request.urlopen( nistTimeServerURL )
serverListHTML = serverListPage.read()
serverListPage.close()

addrs = {}
for srvr,startloc,endloc in timeServerPattern.scanString( serverListHTML ):
    print("%s (%s) - %s" % (srvr.ipAddr, srvr.hostname.strip(), srvr.loc.strip()))
    addrs[srvr.ipAddr] = srvr.loc
