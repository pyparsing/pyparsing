# select_parser.py
# Copyright 2010,2019 Paul McGuire
#
# a simple SELECT statement parser, taken from SQLite's SELECT statement
# definition at https://www.sqlite.org/lang_select.html
#
import sys
from pyparsing import *

ParserElement.enablePackrat()

LPAR, RPAR, COMMA = map(Suppress, "(),")
DOT, STAR = map(Literal, ".*")
select_stmt = Forward().setName("select statement")

# keywords
keywords = {
    k: CaselessKeyword(k)
    for k in """\
    UNION ALL AND INTERSECT EXCEPT COLLATE ASC DESC ON USING NATURAL INNER CROSS LEFT OUTER JOIN AS INDEXED NOT
    SELECT DISTINCT FROM WHERE GROUP BY HAVING ORDER LIMIT OFFSET OR CAST ISNULL NOTNULL NULL IS BETWEEN ELSE END
    CASE WHEN THEN EXISTS IN LIKE GLOB REGEXP MATCH ESCAPE CURRENT_TIME CURRENT_DATE CURRENT_TIMESTAMP TRUE FALSE
    """.split()
}
vars().update(keywords)

keyword = MatchFirst(keywords.values())

identifier = ~keyword + Word(alphas, alphanums + "_")

quoted_identifier = QuotedString('"', escQuote='""')
identifier = (~keyword + Word(alphas, alphanums + "_")).setParseAction(
    pyparsing_common.downcaseTokens
) | quoted_identifier
collation_name = identifier.copy()
column_name = identifier.copy()
column_alias = identifier.copy()
table_name = identifier.copy()
table_alias = identifier.copy()
index_name = identifier.copy()
function_name = identifier.copy()
parameter_name = identifier.copy()
database_name = identifier.copy()

comment = "--" + restOfLine

# expression
expr = Forward().setName("expression")

numeric_literal = pyparsing_common.number
string_literal = QuotedString("'", escQuote="''")
blob_literal = Regex(r"[xX]'[0-9A-Fa-f]+'")
literal_value = (
    numeric_literal
    | string_literal
    | blob_literal
    | TRUE
    | FALSE
    | NULL
    | CURRENT_TIME
    | CURRENT_DATE
    | CURRENT_TIMESTAMP
)
bind_parameter = Word("?", nums) | Combine(oneOf(": @ $") + parameter_name)
type_name = oneOf("TEXT REAL INTEGER BLOB NULL")

expr_term = (
    CAST + LPAR + expr + AS + type_name + RPAR
    | EXISTS + LPAR + select_stmt + RPAR
    | function_name.setName("function_name")
    + LPAR
    + Optional(STAR | delimitedList(expr))
    + RPAR
    | literal_value
    | bind_parameter
    | Group(
        identifier("col_db") + DOT + identifier("col_tab") + DOT + identifier("col")
    )
    | Group(identifier("col_tab") + DOT + identifier("col"))
    | Group(identifier("col"))
)

NOT_NULL = Group(NOT + NULL)
NOT_BETWEEN = Group(NOT + BETWEEN)
NOT_IN = Group(NOT + IN)
NOT_LIKE = Group(NOT + LIKE)
NOT_MATCH = Group(NOT + MATCH)
NOT_GLOB = Group(NOT + GLOB)
NOT_REGEXP = Group(NOT + REGEXP)

UNARY, BINARY, TERNARY = 1, 2, 3
expr << infixNotation(
    expr_term,
    [
        (oneOf("- + ~") | NOT, UNARY, opAssoc.RIGHT),
        (ISNULL | NOTNULL | NOT_NULL, UNARY, opAssoc.LEFT),
        ("||", BINARY, opAssoc.LEFT),
        (oneOf("* / %"), BINARY, opAssoc.LEFT),
        (oneOf("+ -"), BINARY, opAssoc.LEFT),
        (oneOf("<< >> & |"), BINARY, opAssoc.LEFT),
        (oneOf("< <= > >="), BINARY, opAssoc.LEFT),
        (
            oneOf("= == != <>")
            | IS
            | IN
            | LIKE
            | GLOB
            | MATCH
            | REGEXP
            | NOT_IN
            | NOT_LIKE
            | NOT_GLOB
            | NOT_MATCH
            | NOT_REGEXP,
            BINARY,
            opAssoc.LEFT,
        ),
        ((BETWEEN | NOT_BETWEEN, AND), TERNARY, opAssoc.LEFT),
        (
            (IN | NOT_IN) + LPAR + Group(select_stmt | delimitedList(expr)) + RPAR,
            UNARY,
            opAssoc.LEFT,
        ),
        (AND, BINARY, opAssoc.LEFT),
        (OR, BINARY, opAssoc.LEFT),
    ],
)

compound_operator = UNION + Optional(ALL) | INTERSECT | EXCEPT

ordering_term = Group(
    expr("order_key")
    + Optional(COLLATE + collation_name("collate"))
    + Optional(ASC | DESC)("direction")
)

join_constraint = Group(
    Optional(ON + expr | USING + LPAR + Group(delimitedList(column_name)) + RPAR)
)

join_op = COMMA | Group(
    Optional(NATURAL) + Optional(INNER | CROSS | LEFT + OUTER | LEFT | OUTER) + JOIN
)

join_source = Forward()
single_source = (
    Group(database_name("database") + DOT + table_name("table*") | table_name("table*"))
    + Optional(Optional(AS) + table_alias("table_alias*"))
    + Optional(INDEXED + BY + index_name("name") | NOT + INDEXED)("index")
    | (LPAR + select_stmt + RPAR + Optional(Optional(AS) + table_alias))
    | (LPAR + join_source + RPAR)
)

join_source <<= (
    Group(single_source + OneOrMore(join_op + single_source + join_constraint))
    | single_source
)

# result_column = "*" | table_name + "." + "*" | Group(expr + Optional(Optional(AS) + column_alias))
result_column = Group(
    STAR("col")
    | table_name("col_table") + DOT + STAR("col")
    | expr("col") + Optional(Optional(AS) + column_alias("alias"))
)

select_core = (
    SELECT
    + Optional(DISTINCT | ALL)
    + Group(delimitedList(result_column))("columns")
    + Optional(FROM + join_source("from*"))
    + Optional(WHERE + expr("where_expr"))
    + Optional(
        GROUP
        + BY
        + Group(delimitedList(ordering_term))("group_by_terms")
        + Optional(HAVING + expr("having_expr"))
    )
)

select_stmt << (
    select_core
    + ZeroOrMore(compound_operator + select_core)
    + Optional(ORDER + BY + Group(delimitedList(ordering_term))("order_by_terms"))
    + Optional(
        LIMIT
        + (Group(expr + OFFSET + expr) | Group(expr + COMMA + expr) | expr)("limit")
    )
)

select_stmt.ignore(comment)

if __name__ == "__main__":
    tests = """\
        select * from xyzzy where z > 100
        select * from xyzzy where z > 100 order by zz
        select * from xyzzy
        select z.* from xyzzy
        select a, b from test_table where 1=1 and b='yes'
        select a, b from test_table where 1=1 and b in (select bb from foo)
        select z.a, b from test_table where 1=1 and b in (select bb from foo)
        select z.a, b from test_table where 1=1 and b in (select bb from foo) order by b,c desc,d
        select z.a, b from test_table left join test2_table where 1=1 and b in (select bb from foo)
        select a, db.table.b as BBB from db.table where 1=1 and BBB='yes'
        select a, db.table.b as BBB from test_table,db.table where 1=1 and BBB='yes'
        select a, db.table.b as BBB from test_table,db.table where 1=1 and BBB='yes' limit 50
        select a, b from test_table where (1=1 or 2=3) and b='yes' group by zx having b=2 order by 1
        SELECT emp.ename as e FROM scott.employee as emp
        SELECT ename as e, fname as f FROM scott.employee as emp
        SELECT emp.eid, fname,lname FROM scott.employee as emp
        SELECT ename, lname, emp.eid FROM scott.employee as emp
        select emp.salary * (1.0 + emp.bonus) as salary_plus_bonus from scott.employee as emp
        SELECT * FROM abcd WHERE (ST_Overlaps("GEOM", 'POINT(0 0)'))
        SELECT * FROM abcd WHERE CAST(foo AS REAL) > -999.123
        SELECT * FROM abcd WHERE bar BETWEEN +180 AND +10E9
        SELECT * FROM abcd WHERE CAST(foo AS REAL) < (4 + -9.876E-4)
        SELECT SomeFunc(99)
        SELECT * FROM abcd WHERE ST_X(ST_Centroid(geom)) BETWEEN (-180*2) AND (180*2)
        SELECT * FROM abcd WHERE a
        SELECT * FROM abcd WHERE snowy_things REGEXP '[⛄️☃️☃🎿🏂🌨❄️⛷🏔🗻❄︎❆❅]'
        SELECT * FROM abcd WHERE a."b" IN 4
        SELECT * FROM abcd WHERE a."b" In ('4')
        SELECT * FROM "a".b AS "E" WHERE "E"."C" >= CURRENT_Time
        SELECT * FROM abcd WHERE "dave" != "Dave" -- names & things ☃️
        SELECT * FROM a WHERE a.dave is not null
        SELECT * FROM abcd WHERE pete == FALSE or peter is true
        SELECT * FROM abcd WHERE a >= 10 * (2 + 3)
        SELECT * FROM abcd WHERE frank = 'is ''scary'''
        SELECT * FROM abcd WHERE "identifier with ""quotes"" and a trailing space " IS NOT FALSE
        SELECT * FROM abcd WHERE blobby == x'C0FFEE'  -- hex
        SELECT * FROM abcd WHERE ff NOT IN (1,2,4,5)
        SELECT * FROM abcd WHERE ff not between 3 and 9
        SELECT * FROM abcd WHERE ff not like 'bob%'
    """

    success, _ = select_stmt.runTests(tests)
    print("\n{}".format("OK" if success else "FAIL"))
    sys.exit(0 if success else 1)
