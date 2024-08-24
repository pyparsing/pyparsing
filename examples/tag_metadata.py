#
# tag_metadata.py
#
# Copyright 2024, Paul McGuire
#

import pyparsing as pp
ppu = pp.unicode

# associate "alphabet" tag with different Unicode character sets
latin = pp.Word(ppu.Latin1.alphas) + pp.Tag("alphabet", "Latin")
greek = pp.Word(ppu.Greek.alphas) + pp.Tag("alphabet", "Greek")
japanese = pp.Word(ppu.Japanese.alphas) + pp.Tag("alphabet", "Japanese")

# associate "mood" tags with different end punctuation marks
end_punc = (
        ("." + pp.Tag("mood", "normal"))
        | ("!" + pp.Tag("mood", "excited"))
        | ("?" + pp.Tag("mood", "curious"))
)

greeting = "Hello," + (latin | greek | japanese) + end_punc

greeting.run_tests(
    """\
    Hello, World.
    Hello, World!
    Hello, κόσμος?
    Hello, 世界!
    """
)

greeting.create_diagram("tag_metadata_diagram.html")
