# parital_gene_match.py
#
#  Example showing how to use the CloseMatch class, to find strings in a gene with up to 'n' mismatches
#
import pyparsing as pp

import urllib.request, urllib.parse, urllib.error
from contextlib import closing

# read in a bunch of genomic data
data_url = "http://toxodb.org/common/downloads/release-6.0/Tgondii/TgondiiApicoplastORFsNAs_ToxoDB-6.0.fasta"
with closing(urllib.request.urlopen(data_url)) as datafile:
    fastasrc = datafile.read().decode()

"""
Sample header:
>NC_001799-6-2978-2778 | organism=Toxoplasma_gondii_RH | location=NC_001799:2778-2978(-) | length=201
"""
integer = pp.Word(pp.nums).setParseAction(lambda t:int(t[0]))
genebit = pp.Group(">" + pp.Word(pp.alphanums.upper() + "-_")("gene_id")
                   + "|" + pp.Word(pp.printables)("organism")
                   + "|" + pp.Word(pp.printables)("location")
                   + "|" + "length=" + integer("gene_len")
                   + pp.LineEnd()
                   + pp.Word("ACGTN")[1, ...].addParseAction(''.join)("gene"))

# read gene data from .fasta file - takes just a few seconds
genedata = genebit[1, ...].parseString(fastasrc)

# using the genedata extracted above, look for close matches of a gene sequence
searchseq = pp.CloseMatch("TTAAATCTAGAAGAT", 3)

for g in genedata:
    show_header = True
    for t, startLoc, endLoc in searchseq.scanString(g.gene, overlap=True):
        if show_header:
            print("%s/%s/%s (%d)" % (g.gene_id, g.organism, g.location, g.gene_len))
            print("-" * 24)
            show_header = False

        matched = t[0]
        mismatches = t['mismatches']
        print("MATCH:", searchseq.match_string)
        print("FOUND:", matched)
        if mismatches:
            print("      ", ''.join('*' if i in mismatches else ' '
                                    for i, c in enumerate(searchseq.match_string)))
        else:
            print("<exact match>")
        print("at location", startLoc)
        print()
