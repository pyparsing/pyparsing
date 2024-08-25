#
# mongodb_conditional_expression.py
#
# Pyparsing parser and wrapper method to parse infix arithmetic and boolean
# expressions and transform them to MongoDB's nested dict queries with
# associated operator tags.
#
# Example:
#    mongo_query = transform_query("100 < a <= 200")
#    print(mongo_query)
#
# Prints:
#    {'$and': [{'a': {'$gt': 100}}, {'a': {'$lte': 200}}]}
#
# Copyright 2024, Paul McGuire
#

from functools import reduce
from operator import or_
from typing import Union, Dict

import pyparsing as pp
pp.ParserElement.enable_packrat()

ppc = pp.common

__all__ = [
    "query_condition_expr",
    "query_condition_expr_with_comment",
    "transform_query",
]


class InvalidExpressionException(pp.ParseFatalException):
    pass

def key_phrase(expr: Union[str, pp.ParserElement]) -> pp.ParserElement:
    if isinstance(expr, str):
        expr = pp.And(pp.CaselessKeyword.using_each(expr.split()))
    return pp.Combine(expr, adjacent=False, join_string=" ")


ident = ppc.identifier()
integer = ppc.integer()
num = ppc.number()
LBRACK, RBRACK = pp.Suppress.using_each("[]")

operand = ident | (pp.QuotedString('"') | pp.QuotedString("'")).set_name("quoted_string") | num
operand.set_name("operand")
operand_list = pp.Group(LBRACK + pp.DelimitedList(operand) + RBRACK, aslist=True)

AND, OR, NOT, IN, CONTAINS, ALL, NONE = pp.CaselessKeyword.using_each(
    "and or not in contains all none".split()
)
NOT_IN = key_phrase(NOT + IN)
CONTAINS_ALL = key_phrase(CONTAINS + ALL)
CONTAINS_NONE = key_phrase(CONTAINS + NONE)


def binary_eq_neq(s, l, tokens):
    a, op, b = tokens[0]
    try:
        {a: None}
    except TypeError as te:
        raise InvalidExpressionException(
            s, l, f"Could not create query expression using field {a!r}"
        ) from te

    if op in ("=", "=="):
        return {a: b}
    return { a: { "$ne": b } }


def binary_comparison_op(s, l, tokens):
    tokens = tokens[0]
    binary_map = {
        "<": "$lt",
        ">": "$gt",
        "<=": "$lte",
        ">=": "$gte",
        "!=": "$ne",
        "in": "$in",
        "not in": "$nin",
        "contains all": "$all",
        # add Unicode operators, because we can
        "≤": "$lte",
        "≥": "$gte",
        "≠": "$ne",
        "⊇": "$all",
        "∈": "$in",
        "∉": "$nin",
    }
    inequality_inv_map = {
        "<": "$gt",
        ">": "$lt",
        "<=": "$gte",
        ">=": "$lte",
        "≤": "$gte",
        "≥": "$lte",
    }
    operator_compatibility_map = {
        "<": {"<", "<=", "≤"},
        ">": {">", ">=", "≥"},
        "<=": {"<", "<=", "≤"},
        ">=": {">", ">=", "≥"},
        "≤": {"<", "<=", "≤"},
        "≥": {">", ">=", "≥"},
    }

    try:
        field, op, value = tokens
    except ValueError:
        # special handling for 'x < field < y'
        if len(tokens) == 5:
            a, op1, field, op2, b = tokens
            for op_ in (op1, op2):
                if op_ not in inequality_inv_map:
                    raise InvalidExpressionException(
                        s, l, f"{op_} cannot be used in a chained expression"
                    )
            if op2 not in operator_compatibility_map[op1]:
                raise InvalidExpressionException(
                    s, l, f"cannot chain {op1!r} and {op2!r} in the same expression"
                )
            op1 = inequality_inv_map[op1]
            op2 = binary_map[op2]
            return binary_multi_op(
                [
                    [{field: {op1: a}}, "and", {field: {op2: b}}]
                ]
            )
        raise InvalidExpressionException(
            s, l,
            f"{tokens[1]!r} comparison operator may not be chained with more than 2 terms"
        )

    if op == "contains none":
        return {
            "$nor": [
                {field: {"$elemMatch": {"$eq": v}}}
                for v in value
            ]
        }

    return {field: {binary_map[op]: value}}


def binary_multi_op(tokens):
    tokens = tokens[0]
    oper_map = {
        "and": "$and",
        "or": "$or",
        "not": "$not",
    }
    op = oper_map[tokens[1]]
    values = tokens[::2]

    # detect 'and' with all equality checks, collapse to single dict
    if (
        op == "$and"
        and not any(
            isinstance(v, (dict, list))
            for dd in values
            for v in dd.values()
        )
    ):
        try:
            ret = reduce(or_, values)
        except TypeError:
            # compatibility for pre-Python 3.9 versions
            ret = {}
            for v in values:
                ret = {**ret, **v}
        return ret

    return {op: values}


def unary_op(tokens):
    tokens = tokens[0]
    oper_map = {
        "not": "$not",
    }
    op, value = tokens

    # detect 'not not'
    k, v = next(iter(value.items()))
    if k == "$not":
        return v

    return {oper_map[op]: value}


comparison_expr = pp.infix_notation(
    operand | operand_list,
    [
        (pp.one_of("<= >= < > ≤ ≥"), 2, pp.OpAssoc.LEFT, binary_comparison_op),
        (pp.one_of("= == != ≠"), 2, pp.OpAssoc.LEFT, binary_eq_neq),
        (IN | NOT_IN | CONTAINS_ALL | CONTAINS_NONE | pp.one_of("⊇ ∈ ∉"), 2, pp.OpAssoc.LEFT, binary_comparison_op),
    ]
)

# "not" operator only matches if not followed by "in"
NOT_OP = NOT + ~IN
AND_OP = AND | pp.Literal("∧").add_parse_action(pp.replace_with("and"))
OR_OP = OR | pp.Literal("∨").add_parse_action(pp.replace_with("or"))

query_condition_expr = pp.infix_notation(
    comparison_expr | ident,
    [
        (NOT_OP, 1, pp.OpAssoc.RIGHT, unary_op),
        (AND_OP, 2, pp.OpAssoc.LEFT, binary_multi_op),
        (OR_OP, 2, pp.OpAssoc.LEFT, binary_multi_op),
    ]
)

# add $comment containing the original expression string
query_condition_expr_with_comment = pp.And([query_condition_expr])
query_condition_expr_with_comment.add_parse_action(
    lambda s, l, t: t[0].__setitem__("$comment", s)
)


def transform_query(query_string: str, include_comment: bool = False) -> Dict:
    """
    Parse a query string using boolean and arithmetic comparison operations,
    and convert it to a dict for the expression equivalent using MongoDB query
    expression structure.

    Examples:
        a = 100 and b = 200
        {'a': 100, 'b': 200}

        a==100 and b>=200
        {'$and': [{'a': 100}, {'b': {'$gte': 200}}]}

        a==100 and not (b>=200 or c<200)
        {'$and': [{'a': 100}, {'$not': {'$or': [{'b': {'$gte': 200}}, {'c': {'$lt': 200}}]}}]}

        name in ["Alice", "Bob"]
        {'name': {'$in': ['Alice', 'Bob']}}

    Also supported:
    - chained inequalities
        100 < a < 200
        {'$and': [{'a': {'$gt': 100}}, {'a': {'$lt': 200}}]}

    - `in` and `not in`
        name in ["Alice", "Bob"]
        {'name': {'$in': ['Alice', 'Bob']}}

    - `contains all`
        names contains all ["Alice", "Bob"]
        {'names': {'$all': ['Alice', 'Bob']}}

    - Unicode operators
        100 < a ≤ 200 and 300 > b ≥ 200 or c ≠ -1
        100 < a ≤ 200 ∧ 300 > b ≥ 200 ∨ c ≠ -1
        name ∈ ["Alice", "Bob"]
        name ∉ ["Alice", "Bob"]
        names ⊇ ["Alice", "Bob"]

    """
    generator_expr = (
        query_condition_expr_with_comment
        if include_comment
        else query_condition_expr
    )
    return generator_expr.parse_string(query_string)[0]


def main():
    from textwrap import dedent
    for test in dedent("""\
        a = 100
        a = 100 and b = 200
        a > b
        a==100 and b>=200
        a==100 and b>=200 or c<200
        a==100 and (b>=200 or c<200)
        a==100 and not (b>=200 or c<200)
        xyz < 2000 and abc > 32
        xyz < 2000 and abc > 32 and def == 100
        xyz == 2000 and abc == 32 and def == 100
        xyz == 2000 or abc == '32' or def == "foo"
        100 < a < 200
        a==100 and not (100 < b <= 200)
        1900 < "wine vintage" < 2000
        name > "M"
        100 < a ≤ 200 or 300 > b ≥ 200 or c ≠ -1
        100 < a ≤ 200 ∧ 300 > b ≥ 200 ∧ c ≠ -1
        100 < a ≤ 200 ∨ 300 > b ≥ 200 ∨ c ≠ -1
        a==100 and not not (a > 100)
        a==100 and not not not (a > 100)
        a==100 and not not not not (a > 100)
        name in ["Alice", "Bob"]
        name ∈ ["Alice", "Bob"]
        name not in ["Alice", "Bob"]
        name ∉ ["Alice", "Bob"]
        names contains all ["Alice", "Bob"]
        names ⊇ ["Alice", "Bob"]
        names contains none ["Alice", "Bob"]
    """).splitlines():
        print(test)
        print(transform_query(test))
        print()


if __name__ == '__main__':
    main()