""" Test for bibparse grammar """

import unittest
from pyparsing import ParseException
from .btpyparse import Macro
from . import btpyparse as bp


class TestBibparse(unittest.TestCase):
    def test_names(self):
        # check various types of names
        # All names can contains alphas, but not some special chars
        bad_chars = "\"#%'(),={}"
        for name_type, dig1f in (
            (bp.macro_def, False),
            (bp.field_name, False),
            (bp.entry_type, False),
            (bp.cite_key, True),
        ):
            if dig1f:  # can start with digit
                self.assertEqual("2t", name_type.parse_string("2t")[0])
            else:
                self.assertRaises(ParseException, name_type.parse_string, "2t")
            # All of the names cannot contain some characters
            for char in bad_chars:
                self.assertRaises(ParseException, name_type.parse_string, char)
            # standard strings all OK
            self.assertEqual("simple_test", name_type.parse_string("simple_test")[0])
        # Test macro ref
        mr = bp.macro_ref
        # can't start with digit
        self.assertRaises(ParseException, mr.parse_string, "2t")
        for char in bad_chars:
            self.assertRaises(ParseException, mr.parse_string, char)
        self.assertEqual("simple_test", mr.parse_string("simple_test")[0].name)

    def test_numbers(self):
        self.assertEqual("1066", bp.number.parse_string("1066")[0])
        self.assertEqual("0", bp.number.parse_string("0")[0])
        self.assertRaises(ParseException, bp.number.parse_string, "-4")
        self.assertRaises(ParseException, bp.number.parse_string, "+4")
        self.assertRaises(ParseException, bp.number.parse_string, ".4")
        # something point something leaves a trailing .4 unmatched
        self.assertEqual("0", bp.number.parse_string("0.4")[0])

    def test_parse_string(self):
        # test string building blocks
        self.assertEqual(bp.chars_no_quotecurly.parse_string("x")[0], "x")
        self.assertEqual(bp.chars_no_quotecurly.parse_string("a string")[0], "a string")
        self.assertEqual(bp.chars_no_quotecurly.parse_string('a "string')[0], "a ")
        self.assertEqual(bp.chars_no_curly.parse_string("x")[0], "x")
        self.assertEqual(bp.chars_no_curly.parse_string("a string")[0], "a string")
        self.assertEqual(bp.chars_no_curly.parse_string("a {string")[0], "a ")
        self.assertEqual(bp.chars_no_curly.parse_string("a }string")[0], "a ")
        # test more general strings together
        for obj in (bp.curly_string, bp.string, bp.field_value):
            self.assertEqual(obj.parse_string("{}").as_list(), [])
            self.assertEqual(obj.parse_string('{a "string}')[0], 'a "string')
            self.assertEqual(
                ["a ", ["nested"], " string"],
                obj.parse_string("{a {nested} string}").as_list(),
            )
            self.assertEqual(
                ["a ", ["double ", ["nested"]], " string"],
                obj.parse_string("{a {double {nested}} string}").as_list(),
            )
        for obj in (bp.quoted_string, bp.string, bp.field_value):
            self.assertEqual([], obj.parse_string('""').as_list())
            self.assertEqual("a string", obj.parse_string('"a string"')[0])
            self.assertEqual(
                ["a ", ["nested"], " string"],
                obj.parse_string('"a {nested} string"').as_list(),
            )
            self.assertEqual(
                ["a ", ["double ", ["nested"]], " string"],
                obj.parse_string('"a {double {nested}} string"').as_list(),
            )

        # check macro def in string
        self.assertEqual(Macro("someascii"), bp.string.parse_string("someascii")[0])
        self.assertRaises(ParseException, bp.string.parse_string, "%#= validstring")
        # check number in string
        self.assertEqual(bp.string.parse_string("1994")[0], "1994")

    def test_parse_field(self):
        # test field value - hashes included
        fv = bp.field_value
        # Macro
        self.assertEqual(Macro("aname"), fv.parse_string("aname")[0])
        self.assertEqual(Macro("aname"), fv.parse_string("ANAME")[0])
        # String and macro
        self.assertEqual(
            [Macro("aname"), "some string"],
            fv.parse_string('aname # "some string"').as_list(),
        )
        # Nested string
        self.assertEqual(
            [Macro("aname"), "some ", ["string"]],
            fv.parse_string("aname # {some {string}}").as_list(),
        )
        # String and number
        self.assertEqual(
            ["a string", "1994"], fv.parse_string('"a string" # 1994').as_list()
        )
        # String and number and macro
        self.assertEqual(
            ["a string", "1994", Macro("a_macro")],
            fv.parse_string('"a string" # 1994 # a_macro').as_list(),
        )

    def test_comments(self):
        res = bp.comment.parse_string("@Comment{about something}")
        self.assertEqual(res.as_list(), ["comment", "{about something}"])
        self.assertEqual(
            ["comment", "{about something"],
            bp.comment.parse_string("@COMMENT{about something").as_list(),
        )
        self.assertEqual(
            ["comment", "(about something"],
            bp.comment.parse_string("@comment(about something").as_list(),
        )
        self.assertEqual(
            ["comment", " about something"],
            bp.comment.parse_string("@COMment about something").as_list(),
        )
        self.assertRaises(
            ParseException, bp.comment.parse_string, "@commentabout something"
        )
        self.assertRaises(
            ParseException, bp.comment.parse_string, "@comment+about something"
        )
        self.assertRaises(
            ParseException, bp.comment.parse_string, '@comment"about something'
        )

    def test_preamble(self):
        res = bp.preamble.parse_string('@preamble{"about something"}')
        self.assertEqual(res.as_list(), ["preamble", "about something"])
        self.assertEqual(
            ["preamble", "about something"],
            bp.preamble.parse_string("@PREamble{{about something}}").as_list(),
        )
        self.assertEqual(
            ["preamble", "about something"],
            bp.preamble.parse_string(
                """@PREamble{
            {about something}
        }"""
            ).as_list(),
        )

    def test_macro(self):
        res = bp.macro.parse_string('@string{ANAME = "about something"}')
        self.assertEqual(res.as_list(), ["string", "aname", "about something"])
        self.assertEqual(
            ["string", "aname", "about something"],
            bp.macro.parse_string("@string{aname = {about something}}").as_list(),
        )

    def test_entry(self):
        txt = """@some_entry{akey, aname = "about something",
        another={something else}}"""
        res = bp.entry.parse_string(txt)
        self.assertEqual(
            [
                "some_entry",
                "akey",
                ["aname", "about something"],
                ["another", "something else"],
            ],
            res.as_list(),
        )
        # Case conversion
        txt = """@SOME_ENTRY{akey, ANAME = "about something",
        another={something else}}"""
        res = bp.entry.parse_string(txt)
        self.assertEqual(
            [
                "some_entry",
                "akey",
                ["aname", "about something"],
                ["another", "something else"],
            ],
            res.as_list(),
        )

    def test_bibfile(self):
        txt = """@some_entry{akey, aname = "about something",
        another={something else}}"""
        res = bp.bibfile.parse_string(txt)
        self.assertEqual(
            [
                [
                    "some_entry",
                    "akey",
                    ["aname", "about something"],
                    ["another", "something else"],
                ]
            ],
            res.as_list(),
        )

    def test_bib1(self):
        # First pass whole bib-like tests
        txt = """
    Some introductory text
    (implicit comment)

        @ARTICLE{Brett2002marsbar,
      author = {Matthew Brett and Jean-Luc Anton and Romain Valabregue and Jean-Baptise
                Poline},
      title = {{Region of interest analysis using an SPM toolbox}},
      journal = {Neuroimage},
      year = {2002},
      volume = {16},
      pages = {1140--1141},
      number = {2}
    }

    @some_entry{akey, aname = "about something",
    another={something else}}
    """
        res = bp.bibfile.parse_string(txt)
        self.assertEqual(len(res), 3)
        res2 = bp.parse_str(txt)
        self.assertEqual(res.as_list(), res2.as_list())
        res3 = [r.as_list()[0] for r, start, end in bp.definitions.scan_string(txt)]
        self.assertEqual(res.as_list(), res3)


if __name__ == "__main__":
    unittest.main()
