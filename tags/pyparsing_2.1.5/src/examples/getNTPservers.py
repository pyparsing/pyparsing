# getNTPservers.py
#
# Demonstration of the parsing module, implementing a HTML page scanner,
# to extract a list of NTP time servers from the NIST web site.
#
# Copyright 2004, by Paul McGuire
#
from pyparsing import Word, Combine, Suppress, CharsNotIn, nums
import urllib.request, urllib.parse, urllib.error

integer = Word(nums)
ipAddress = Combine( integer + "." + integer + "." + integer + "." + integer )
tdStart = Suppress("<td>")
tdEnd = Suppress("</td>")
timeServerPattern =  tdStart + ipAddress.setResultsName("ipAddr") + tdEnd + \
        tdStart + CharsNotIn("<").setResultsName("loc") + tdEnd

# get list of time servers
nistTimeServerURL = "http://www.boulder.nist.gov/timefreq/service/time-servers.html"
serverListPage = urllib.request.urlopen( nistTimeServerURL )
serverListHTML = serverListPage.read()
serverListPage.close()

addrs = {}
for srvr,startloc,endloc in timeServerPattern.scanString( serverListHTML ):
    print(srvr.ipAddr, "-", srvr.loc)
    addrs[srvr.ipAddr] = srvr.loc
    # or do this:
    #~ addr,loc = srvr
    #~ print addr, "-", loc
