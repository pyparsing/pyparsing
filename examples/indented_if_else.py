"""Parse a small indentation-sensitive if/elif/else language.

Each branch header is a statement at its suite's indentation level. Only
then are adjacent branches grouped. Attaching ``ZeroOrMore(elif_clause)``
to an if clause without an alignment check can consume an outer branch
while parsing an inner conditional (see issue #417).

This is a parser example, not a Python parser or evaluator. Conditions are
opaque single-line strings; simple statements are identifiers. Inline suites,
comments, and expressions containing a colon are intentionally unsupported.
Identifiers start with an ASCII letter and continue with letters, digits, or
underscores. The input must contain at least one statement; the outer suite
may be indented. This example assumes the default pyparsing whitespace set.
"""

from dataclasses import dataclass
from pprint import pprint
from typing import Optional, Tuple

import pyparsing as pp


@dataclass(frozen=True)
class Branch:
    condition: Optional[str]
    body: tuple


@dataclass(frozen=True)
class Conditional:
    branches: Tuple[Branch, ...]


@dataclass(frozen=True)
class _Clause:
    kind: str
    condition: Optional[str]
    body: tuple
    location: int


def make_parser():
    """Return a fresh grammar; do not change global whitespace settings."""
    statement = pp.Forward()
    suite = pp.IndentedBlock(statement)

    def group_branches(source, location, tokens):
        result = []
        for item in tokens[0]:
            if not isinstance(item, _Clause):
                result.append(item)
            elif item.kind == "if":
                result.append(Conditional((Branch(item.condition, item.body),)))
            else:
                if not result or not isinstance(result[-1], Conditional):
                    raise pp.ParseFatalException(
                        source, item.location, "branch without a preceding if"
                    )
                previous = result[-1]
                if previous.branches[-1].condition is None:
                    raise pp.ParseFatalException(
                        source, item.location, "branch after else"
                    )
                result[-1] = Conditional(
                    previous.branches + (Branch(item.condition, item.body),)
                )
        return [tuple(result)]

    suite.set_parse_action(group_branches)
    condition = pp.Regex(r"[^:\r\n]+").set_parse_action(lambda t: t[0].strip())
    condition.add_condition(lambda t: bool(t[0]))
    condition.set_whitespace_chars(" \t")
    header = (pp.Keyword("if") | pp.Keyword("elif"))("kind") + condition(
        "condition"
    ) | pp.Keyword("else")("kind")
    colon = pp.Suppress(":").set_whitespace_chars(" \t")
    clause = header + colon + pp.LineEnd().suppress() + pp.Located(suite)("suite")

    def make_clause(source, location, tokens):
        body_location = tokens.suite.locn_start
        if pp.col(body_location, source) <= pp.col(location, source):
            raise pp.ParseFatalException(
                source, body_location, "expected an indented suite"
            )
        return _Clause(
            tokens.kind, tokens.get("condition"), tokens.suite.value[0], location
        )

    clause.set_parse_action(make_clause)
    identifier = ~pp.one_of("if elif else", as_keyword=True) + pp.Word(
        pp.alphas, pp.alphanums + "_"
    )
    simple = identifier + pp.LineEnd().suppress()
    statement <<= clause | simple
    return suite


def parse(source):
    """Return a tuple of identifier statements and Conditional objects."""
    return make_parser().parse_string(source, parse_all=True)[0]


def main():
    pprint(parse("if A:\n    a\n    if B:\n        b\nelif C:\n    c\nelse:\n    d\n"))


if __name__ == "__main__":
    main()
