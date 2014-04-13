# select_parser.py
# Copyright 2010, Paul McGuire
#
# a simple SELECT statement parser, taken from SQLite's SELECT statement
# definition at http://www.sqlite.org/lang_select.html
#
from pyparsing import *
ParserElement.enablePackrat()

LPAR,RPAR,COMMA = map(Suppress,"(),")
select_stmt = Forward().setName("select statement")

# keywords
(UNION, ALL, AND, INTERSECT, EXCEPT, COLLATE, ASC, DESC, ON, USING, NATURAL, INNER, 
 CROSS, LEFT, OUTER, JOIN, AS, INDEXED, NOT, SELECT, DISTINCT, FROM, WHERE, GROUP, BY,
 HAVING, ORDER, BY, LIMIT, OFFSET, OR) =  map(CaselessKeyword, """UNION, ALL, AND, INTERSECT, 
 EXCEPT, COLLATE, ASC, DESC, ON, USING, NATURAL, INNER, CROSS, LEFT, OUTER, JOIN, AS, INDEXED, NOT, SELECT, 
 DISTINCT, FROM, WHERE, GROUP, BY, HAVING, ORDER, BY, LIMIT, OFFSET, OR""".replace(",","").split())
(CAST, ISNULL, NOTNULL, NULL, IS, BETWEEN, ELSE, END, CASE, WHEN, THEN, EXISTS,
 COLLATE, IN, LIKE, GLOB, REGEXP, MATCH, ESCAPE, CURRENT_TIME, CURRENT_DATE, 
 CURRENT_TIMESTAMP) = map(CaselessKeyword, """CAST, ISNULL, NOTNULL, NULL, IS, BETWEEN, ELSE, 
 END, CASE, WHEN, THEN, EXISTS, COLLATE, IN, LIKE, GLOB, REGEXP, MATCH, ESCAPE, 
 CURRENT_TIME, CURRENT_DATE, CURRENT_TIMESTAMP""".replace(",","").split())
keyword = MatchFirst((UNION, ALL, INTERSECT, EXCEPT, COLLATE, ASC, DESC, ON, USING, NATURAL, INNER, 
 CROSS, LEFT, OUTER, JOIN, AS, INDEXED, NOT, SELECT, DISTINCT, FROM, WHERE, GROUP, BY,
 HAVING, ORDER, BY, LIMIT, OFFSET, CAST, ISNULL, NOTNULL, NULL, IS, BETWEEN, ELSE, END, CASE, WHEN, THEN, EXISTS,
 COLLATE, IN, LIKE, GLOB, REGEXP, MATCH, ESCAPE, CURRENT_TIME, CURRENT_DATE, 
 CURRENT_TIMESTAMP))
 
identifier = ~keyword + Word(alphas, alphanums+"_")
collation_name = identifier.copy()
column_name = identifier.copy()
column_alias = identifier.copy()
table_name = identifier.copy()
table_alias = identifier.copy()
index_name = identifier.copy()
function_name = identifier.copy()
parameter_name = identifier.copy()
database_name = identifier.copy()

# expression
expr = Forward().setName("expression")

integer = Regex(r"[+-]?\d+")
numeric_literal = Regex(r"\d+(\.\d*)?([eE][+-]?\d+)?")
string_literal = QuotedString("'")
blob_literal = Regex(r"[xX]'[0-9A-Fa-f]+'")
literal_value = ( numeric_literal | string_literal | blob_literal |
    NULL | CURRENT_TIME | CURRENT_DATE | CURRENT_TIMESTAMP )
bind_parameter = (
    Word("?",nums) |
    Combine(oneOf(": @ $") + parameter_name)
    )
type_name = oneOf("TEXT REAL INTEGER BLOB NULL")

expr_term = (
    CAST + LPAR + expr + AS + type_name + RPAR |
    EXISTS + LPAR + select_stmt + RPAR |
    function_name.setName("function_name") + LPAR + Optional(delimitedList(expr)) + RPAR |
    literal_value |
    bind_parameter |
    Combine(identifier+('.'+identifier)*(0,2)).setName("ident")
    )

UNARY,BINARY,TERNARY=1,2,3
expr << operatorPrecedence(expr_term,
    [
    (oneOf('- + ~') | NOT, UNARY, opAssoc.RIGHT),
    (ISNULL | NOTNULL | NOT + NULL, UNARY, opAssoc.LEFT),
    ('||', BINARY, opAssoc.LEFT),
    (oneOf('* / %'), BINARY, opAssoc.LEFT),
    (oneOf('+ -'), BINARY, opAssoc.LEFT),
    (oneOf('<< >> & |'), BINARY, opAssoc.LEFT),
    (oneOf('< <= > >='), BINARY, opAssoc.LEFT),
    (oneOf('= == != <>') | IS | IN | LIKE | GLOB | MATCH | REGEXP, BINARY, opAssoc.LEFT),
    ('||', BINARY, opAssoc.LEFT),
    ((BETWEEN,AND), TERNARY, opAssoc.LEFT),
    (IN + LPAR + Group(select_stmt | delimitedList(expr)) + RPAR, UNARY, opAssoc.LEFT),
    (AND, BINARY, opAssoc.LEFT),
    (OR, BINARY, opAssoc.LEFT),
    ])

compound_operator = (UNION + Optional(ALL) | INTERSECT | EXCEPT)

ordering_term = Group(expr('order_key') + Optional(COLLATE + collation_name('collate')) + Optional(ASC | DESC)('direction'))

join_constraint = Group(Optional(ON + expr | USING + LPAR + Group(delimitedList(column_name)) + RPAR))

join_op = COMMA | Group(Optional(NATURAL) + Optional(INNER | CROSS | LEFT + OUTER | LEFT | OUTER) + JOIN)

join_source = Forward()
single_source = ( (Group(database_name("database") + "." + table_name("table")) | table_name("table")) + 
                    Optional(Optional(AS) + table_alias("table_alias")) +
                    Optional(INDEXED + BY + index_name("name") | NOT + INDEXED)("index") | 
                  (LPAR + select_stmt + RPAR + Optional(Optional(AS) + table_alias)) | 
                  (LPAR + join_source + RPAR) )

join_source << (Group(single_source + OneOrMore(join_op + single_source + join_constraint)) | 
                single_source)

result_column = "*" | table_name + "." + "*" | Group(expr + Optional(Optional(AS) + column_alias))
select_core = (SELECT + Optional(DISTINCT | ALL) + Group(delimitedList(result_column))("columns") +
                Optional(FROM + join_source("from")) +
                Optional(WHERE + expr("where_expr")) +
                Optional(GROUP + BY + Group(delimitedList(ordering_term)("group_by_terms")) + 
                        Optional(HAVING + expr("having_expr"))))

select_stmt << (select_core + ZeroOrMore(compound_operator + select_core) +
                Optional(ORDER + BY + Group(delimitedList(ordering_term))("order_by_terms")) +
                Optional(LIMIT + (Group(expr + OFFSET + expr) | Group(expr + COMMA + expr) | expr)("limit")))

tests = """\
    select * from xyzzy where z > 100
    select * from xyzzy where z > 100 order by zz
    select * from xyzzy
    select z.* from xyzzy""".splitlines()
tests = """\
    select a, b from test_table where 1=1 and b='yes'
    select a, b from test_table where 1=1 and b in (select bb from foo)
    select z.a, b from test_table where 1=1 and b in (select bb from foo)
    select z.a, b from test_table where 1=1 and b in (select bb from foo) order by b,c desc,d
    select z.a, b from test_table left join test2_table where 1=1 and b in (select bb from foo)
    select a, db.table.b as BBB from db.table where 1=1 and BBB='yes'
    select a, db.table.b as BBB from test_table,db.table where 1=1 and BBB='yes'
    select a, db.table.b as BBB from test_table,db.table where 1=1 and BBB='yes' limit 50
    """.splitlines()
for t in tests:
    t = t.strip()
    if not t: continue
    print(t)
    try:
        print(select_stmt.parseString(t).dump())
    except ParseException as pe:
        print(pe.msg)
    print()
