# getNTPserversNew.py
#
# Demonstration of the parsing module, implementing a HTML page scanner,
# to extract a list of NTP time servers from the NIST web site.
#
# Copyright 2004-2010, by Paul McGuire
# September, 2010 - updated to more current use of set_results_name, new NIST URL
#
import pyparsing as pp

ppc = pp.pyparsing_common
from urllib.request import Request, urlopen

integer = pp.Word(pp.nums)
ipAddress = ppc.ipv4_address()
hostname = pp.DelimitedList(pp.Word(pp.alphas, pp.alphanums + "-_"), ".", combine=True)

# expressions to extract HTML table from fetched page
tdStart, tdEnd = pp.make_html_tags("td")
timeServerPattern = (
    tdStart
    + hostname("hostname")
    + tdEnd
    + tdStart
    + ipAddress("ipAddr")
    + tdEnd
    + tdStart
    + tdStart.tag_body("loc")
    + tdEnd
)

# get list of time servers from NIST
nistTimeServerURL = "https://tf.nist.gov/tf-cgi/servers.cgi#"
req = Request(
    nistTimeServerURL,
    headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                      " (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    },
)
with urlopen(req, timeout=15) as serverListPage:
    serverListHTML = serverListPage.read().decode("UTF-8")

addrs = {}
for srvr, startloc, endloc in timeServerPattern.scan_string(serverListHTML):
    print(f"{srvr.ipAddr} ({srvr.hostname.strip()}) - {srvr.loc.strip()}")
    addrs[srvr.ipAddr] = srvr.loc
