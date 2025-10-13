TINY parser (pyparsing)

This folder contains a minimal pyparsing grammar for the educational TINY language.

How to run quick self-tests
- python -m examples.tiny.tiny_parser

How to use from Python

    from examples.tiny.tiny_parser import parse_tiny
    src = "read x; y := 1 + 2; write y"
    result = parse_tiny(src)
    print(result.dump())

Grammar outline: see grammar.md
Best practices: python -m pyparsing.ai.show_best_practices
