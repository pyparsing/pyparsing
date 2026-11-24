import unittest

import pyparsing as pp
from examples.indented_if_else import Branch, Conditional, make_parser, parse


class TestIndentedConditionalExample(unittest.TestCase):
    def setUp(self):
        self.context = pp.testing.reset_pyparsing_context().save()
        self.addCleanup(self.context.restore)
        pp.ParserElement.set_default_whitespace_chars(" \t\r\n")

    def test_outer_branches_after_inner_if(self):
        source = "if A:\n    a\n    if B:\n        b\nelif C:\n    c\nelse:\n    d\n"
        self.assertEqual(
            parse(source),
            (
                Conditional(
                    (
                        Branch("A", ("a", Conditional((Branch("B", ("b",)),)))),
                        Branch("C", ("c",)),
                        Branch(None, ("d",)),
                    )
                ),
            ),
        )

    def test_inner_and_outer_branches(self):
        source = "if A:\n    if B:\n        b\n    elif C:\n        c\n    else:\n        d\nelse:\n    e\n"
        self.assertEqual(
            parse(source),
            (
                Conditional(
                    (
                        Branch(
                            "A",
                            (
                                Conditional(
                                    (
                                        Branch("B", ("b",)),
                                        Branch("C", ("c",)),
                                        Branch(None, ("d",)),
                                    )
                                ),
                            ),
                        ),
                        Branch(None, ("e",)),
                    )
                ),
            ),
        )

    def test_simple_and_separate_conditionals(self):
        self.assertEqual(
            parse("a\nif A:\n  b\nif B:\n  c\nz"),
            (
                "a",
                Conditional((Branch("A", ("b",)),)),
                Conditional((Branch("B", ("c",)),)),
                "z",
            ),
        )

    def test_crlf_blank_lines_tabs_and_condition_text(self):
        self.assertEqual(
            parse("\r\nif x > 2:\r\n\ta\r\n\r\nelse:\r\n\tb\r\n"),
            (Conditional((Branch("x > 2", ("a",)), Branch(None, ("b",)))),),
        )

    def test_invalid_branches_and_suites(self):
        invalid = [
            "elif A:\n    a\n",
            "else:\n    a\n",
            "if A:\n    a\nelse:\n    b\nelif C:\n    c\n",
            "if A:\n    a\nelse:\n    b\nelse:\n    c\n",
            "if A:\n    a\nx\nelif B:\n    b\n",
            "if A:\na\n",
            "if A:\n",
            "if A: a\n",
            "if A:\n    a\n  else:\n    b\n",
            "if\nA:\n  a\n",
            "if A\n:\n  a\n",
            "if A:\n  a\nelse\n:\n  b\n",
            "if :\n    a\n",
            "if A:\n    if B:\n    b\n",
        ]
        for source in invalid:
            with self.subTest(source=source), self.assertRaises(pp.ParseBaseException):
                parse(source)

    def test_repeat_after_failure_and_independent_grammars(self):
        first, second = make_parser(), make_parser()
        source = "if A:\n    a\nelse:\n    b\n"
        expected = parse(source)
        for parser in (first, second, first):
            with self.assertRaises(pp.ParseBaseException):
                parser.parse_string("else:\n    a\n", parse_all=True)
            self.assertEqual(parser.parse_string(source, parse_all=True)[0], expected)


if __name__ == "__main__":
    unittest.main()
