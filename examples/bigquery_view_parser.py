# bigquery_view_parser.py
#
# A parser to extract table names from BigQuery view definitions.
# This is based on the `select_parser.py` sample in pyparsing:
# https://github.com/pyparsing/pyparsing/blob/master/examples/select_parser.py
#
# Michael Smedberg
#
import sys

from pyparsing import ParserElement, Suppress, Forward, CaselessKeyword
from pyparsing import MatchFirst, alphas, alphanums, Combine, Word
from pyparsing import QuotedString, CharsNotIn, Optional, Group, ZeroOrMore
from pyparsing import oneOf, delimitedList, restOfLine, cStyleComment
from pyparsing import infixNotation, opAssoc, Regex, nums

sys.setrecursionlimit(3000)

ParserElement.enablePackrat()


class BigQueryViewParser:
    """Parser to extract table info from BigQuery view definitions"""

    _parser = None
    _table_identifiers = set()
    _with_aliases = set()
    _external_query_name = None

    def get_table_names(self, sql_stmt):
        table_identifiers, with_aliases = self._parse(sql_stmt)

        # Table names and alias names might differ by case, but that's not
        # relevant- aliases are not case sensitive
        lower_aliases = BigQueryViewParser.lowercase_set_of_tuples(with_aliases)
        tables = {
            x
            for x in table_identifiers
            if not BigQueryViewParser.lowercase_of_tuple(x) in lower_aliases
        }

        # Table names ARE case sensitive as described at
        # https://cloud.google.com/bigquery/docs/reference/standard-sql/lexical#case_sensitivity
        return tables

    def _parse(self, sql_stmt):
        BigQueryViewParser._table_identifiers.clear()
        BigQueryViewParser._with_aliases.clear()
        BigQueryViewParser._get_parser().parseString(sql_stmt)

        return BigQueryViewParser._table_identifiers, BigQueryViewParser._with_aliases

    @classmethod
    def lowercase_of_tuple(cls, tuple_to_lowercase):
        return tuple(x.lower() if x else None for x in tuple_to_lowercase)

    @classmethod
    def lowercase_set_of_tuples(cls, set_of_tuples):
        return {BigQueryViewParser.lowercase_of_tuple(x) for x in set_of_tuples}

    @classmethod
    def _get_parser(cls):
        if cls._parser is not None:
            return cls._parser

        ParserElement.enablePackrat()

        LPAR, RPAR, COMMA, LBRACKET, RBRACKET, LT, GT = map(Suppress, "(),[]<>")
        QUOT, APOS, ACC, DOT = map(Suppress, "\"'`.")
        ungrouped_select_stmt = Forward().setName("select statement")

        QUOTED_QUOT = QuotedString('"')
        QUOTED_APOS = QuotedString("'")
        QUOTED_ACC = QuotedString("`")

        # fmt: off
        # keywords
        (
            UNION, ALL, AND, INTERSECT, EXCEPT, COLLATE, ASC, DESC, ON, USING, NATURAL,
            INNER, CROSS, LEFT, RIGHT, OUTER, FULL, JOIN, AS, INDEXED, NOT, SELECT,
            DISTINCT, FROM, WHERE, GROUP, BY, HAVING, ORDER, BY, LIMIT, OFFSET, OR,
            CAST, ISNULL, NOTNULL, NULL, IS, BETWEEN, ELSE, END, CASE, WHEN, THEN,
            EXISTS, COLLATE, IN, LIKE, GLOB, REGEXP, MATCH, ESCAPE, CURRENT_TIME,
            CURRENT_DATE, CURRENT_TIMESTAMP, WITH, EXTRACT, PARTITION, ROWS, RANGE,
            UNBOUNDED, PRECEDING, CURRENT, ROW, FOLLOWING, OVER, INTERVAL, DATE_ADD,
            DATE_SUB, ADDDATE, SUBDATE, REGEXP_EXTRACT, SPLIT, ORDINAL, FIRST_VALUE,
            LAST_VALUE, NTH_VALUE, LEAD, LAG, PERCENTILE_CONT, PRECENTILE_DISC, RANK,
            DENSE_RANK, PERCENT_RANK, CUME_DIST, NTILE, ROW_NUMBER, DATE, TIME, DATETIME,
            TIMESTAMP, UNNEST, INT64, NUMERIC, FLOAT64, BOOL, BYTES, GEOGRAPHY, ARRAY,
            STRUCT, SAFE_CAST, ANY_VALUE, ARRAY_AGG, ARRAY_CONCAT_AGG, AVG, BIT_AND,
            BIT_OR, BIT_XOR, COUNT, COUNTIF, LOGICAL_AND, LOGICAL_OR, MAX, MIN,
            STRING_AGG, SUM, CORR, COVAR_POP, COVAR_SAMP, STDDEV_POP, STDDEV_SAMP,
            STDDEV, VAR_POP, VAR_SAMP, VARIANCE, TIMESTAMP_ADD, TIMESTAMP_SUB,
            GENERATE_ARRAY, GENERATE_DATE_ARRAY, GENERATE_TIMESTAMP_ARRAY, FOR,
            SYSTEMTIME, AS, OF, WINDOW, RESPECT, IGNORE, NULLS, ANY, ASSERT_ROWS_MODIFIED,
            AT, BOOLEAN, CONTAINS, CREATE, CUBE, DEFAULT, DEFINE, ENUM, EXCLUDE,
            EXTERNAL_QUERY, FALSE, FETCH, GROUPING, GROUPS, HASH, IF, INFORMATION_SCHEMA,
            INTO, LATERAL, LOOKUP, MERGE, NEW, NO, PIVOT, PROTO, QUALIFY, RECURSIVE,
            REPLACE, ROLLUP, SAFE_OFFSET, SAFE_ORDINAL, SET, SOME, TABLESAMPLE, TO, TREAT,
            TRUE, WITHIN
        ) = map(
            CaselessKeyword,
            """
            UNION, ALL, AND, INTERSECT, EXCEPT, COLLATE, ASC, DESC, ON, USING, NATURAL,
            INNER, CROSS, LEFT, RIGHT, OUTER, FULL, JOIN, AS, INDEXED, NOT, SELECT,
            DISTINCT, FROM, WHERE, GROUP, BY, HAVING, ORDER, BY, LIMIT, OFFSET, OR,
            CAST, ISNULL, NOTNULL, NULL, IS, BETWEEN, ELSE, END, CASE, WHEN, THEN,
            EXISTS, COLLATE, IN, LIKE, GLOB, REGEXP, MATCH, ESCAPE, CURRENT_TIME,
            CURRENT_DATE, CURRENT_TIMESTAMP, WITH, EXTRACT, PARTITION, ROWS, RANGE,
            UNBOUNDED, PRECEDING, CURRENT, ROW, FOLLOWING, OVER, INTERVAL, DATE_ADD,
            DATE_SUB, ADDDATE, SUBDATE, REGEXP_EXTRACT, SPLIT, ORDINAL, FIRST_VALUE,
            LAST_VALUE, NTH_VALUE, LEAD, LAG, PERCENTILE_CONT, PRECENTILE_DISC, RANK,
            DENSE_RANK, PERCENT_RANK, CUME_DIST, NTILE, ROW_NUMBER, DATE, TIME, DATETIME,
            TIMESTAMP, UNNEST, INT64, NUMERIC, FLOAT64, BOOL, BYTES, GEOGRAPHY, ARRAY,
            STRUCT, SAFE_CAST, ANY_VALUE, ARRAY_AGG, ARRAY_CONCAT_AGG, AVG, BIT_AND,
            BIT_OR, BIT_XOR, COUNT, COUNTIF, LOGICAL_AND, LOGICAL_OR, MAX, MIN,
            STRING_AGG, SUM, CORR, COVAR_POP, COVAR_SAMP, STDDEV_POP, STDDEV_SAMP,
            STDDEV, VAR_POP, VAR_SAMP, VARIANCE, TIMESTAMP_ADD, TIMESTAMP_SUB,
            GENERATE_ARRAY, GENERATE_DATE_ARRAY, GENERATE_TIMESTAMP_ARRAY, FOR,
            SYSTEMTIME, AS, OF, WINDOW, RESPECT, IGNORE, NULLS, ANY, ASSERT_ROWS_MODIFIED,
            AT, BOOLEAN, CONTAINS, CREATE, CUBE, DEFAULT, DEFINE, ENUM, EXCLUDE,
            EXTERNAL_QUERY, FALSE, FETCH, GROUPING, GROUPS, HASH, IF, INFORMATION_SCHEMA,
            INTO, LATERAL, LOOKUP, MERGE, NEW, NO, PIVOT, PROTO, QUALIFY, RECURSIVE,
            REPLACE, ROLLUP, SAFE_OFFSET, SAFE_ORDINAL, SET, SOME, TABLESAMPLE, TO, TREAT,
            TRUE, WITHIN
            """.replace(",", "").split(),
        )

        keyword_nonfunctions = MatchFirst(
            (UNION, ALL, INTERSECT, EXCEPT, COLLATE, ASC, DESC, ON, USING,
             NATURAL, INNER, CROSS, LEFT, RIGHT, OUTER, FULL, JOIN, AS, INDEXED,
             NOT, SELECT, DISTINCT, FROM, WHERE, GROUP, BY, HAVING, ORDER, BY,
             LIMIT, OFFSET, CAST, ISNULL, NOTNULL, NULL, IS, BETWEEN, ELSE, END,
             CASE, WHEN, THEN, EXISTS, COLLATE, IN, LIKE, GLOB, REGEXP, MATCH,
             STRUCT, WINDOW,
             )
        )

        keyword = MatchFirst((
            ALL, AND, ANY, ARRAY, AS, ASC, ASSERT_ROWS_MODIFIED, AT, BETWEEN, BY, CASE, CAST,
            COLLATE, CONTAINS, CREATE, CROSS, CUBE, CURRENT, DEFAULT, DEFINE, DESC, DISTINCT,
            ELSE, END, ENUM, ESCAPE, EXCEPT, EXCLUDE, EXISTS, EXTERNAL_QUERY, EXTRACT, FALSE,
            FETCH, FOLLOWING, FOR, FROM, FULL, GROUP, GROUPING, GROUPS, HASH, HAVING, IF,
            IGNORE, IN, INNER, INTERSECT, INTERVAL, INTO, IS, JOIN, LATERAL, LEFT, LIKE, LIMIT,
            LOOKUP, MERGE, NATURAL, NEW, NO, NOT, NULL, NULLS, OF, ON, OR, ORDER, OUTER, OVER,
            PARTITION, PIVOT, PRECEDING, PROTO, RANGE, RECURSIVE, RESPECT, RIGHT, ROLLUP, ROWS,
            SELECT, SET, SOME, STRUCT, TABLESAMPLE, THEN, TO, TREAT, TRUE, UNBOUNDED, UNION,
            UNNEST, USING, WHEN, WHERE, WINDOW, WITH, WITHIN))

        # those are keywords that are function names
        keyword_funcs = MatchFirst((
            TREAT, WITHIN, TABLESAMPLE, SOME, SET, RIGHT, PROTO, MERGE,
            LOOKUP, LEFT, LATERAL, FETCH, CURRENT
        ))
        # fmt: on

        identifier_word = Word(alphas + "_@#", alphanums + "@$#_")
        identifier = ~keyword + identifier_word.copy()
        collation_name = identifier.copy()
        # NOTE: Column names can't be keywords unless they are quoted
        column_name = identifier.copy() | Suppress('`') + identifier_word + Suppress('`')
        # first part of multi part column name can't be keyword, other parts can
        qualified_column_name = Combine(column_name + (
            ZeroOrMore(' ') + '.' + ZeroOrMore(' ') + identifier_word) * (0, 6))
        qualified_column_name = qualified_column_name | Suppress('`') + qualified_column_name + Suppress('`')
        # NOTE: As with column names, column aliases can be keywords, e.g. functions like `current_time`.  Other
        # keywords, e.g. `from` make parsing pretty difficult (e.g. "SELECT a from from b" is confusing.)
        # We will specifically exclude `from`, since we need to support trailing commas in the SELECT list, and
        # SQL like `SELECT a, FROM b` becomes ambiguous if we support `from`.  In that SQL, is `FROM` a column name with
        # alias `b`, or are we selecting a single column from table `b`?
        column_alias = identifier.copy()
        table_name = identifier.copy()
        table_alias = identifier.copy()
        index_name = identifier.copy()
        function_name = identifier.copy()
        parameter_name = identifier.copy()
        standard_name_part = ~keyword + Word(alphanums + "_" + "-") | keyword_funcs
        quoted_name_part = Suppress("`") + CharsNotIn("`") + Suppress("`")
        # table names can't have dots
        quoted_tablename_part = Suppress("`") + CharsNotIn("`.") + Suppress("`")

        # function_name has optional project.dataset [[project_name.]dataset_name.]function_name
        # https://cloud.google.com/bigquery/docs/reference/standard-sql/user-defined-functions#temporary-udf-syntax
        function_name = (Optional((quoted_name_part | standard_name_part) + Suppress('.'))
                         + Optional((quoted_name_part | standard_name_part) + Suppress('.'))
                         + (quoted_name_part | standard_name_part)
                         )
        function_name = function_name | (Suppress("`") + CharsNotIn("`") + Suppress("`"))
        parameter_name = identifier.copy()

        # expression
        expr = Forward().setName("expression")

        integer = Regex(r"[+-]?\d+")
        numeric_literal = Regex(r"[+-]?\d*\.?\d+([eE][+-]?\d+)?")
        bool_literal = TRUE | FALSE
        string_literal = QUOTED_APOS | QUOTED_QUOT | QUOTED_ACC
        regex_literal = "r" + string_literal
        blob_literal = Regex(r"[xX]'[0-9A-Fa-f]+'")
        date_or_time_literal = (DATE | TIME | DATETIME | TIMESTAMP) + string_literal
        literal_value = (
            numeric_literal
            | string_literal
            | bool_literal
            | regex_literal
            | blob_literal
            | date_or_time_literal
            | NULL
            | CURRENT_TIME + Optional(LPAR + Optional(string_literal) + RPAR)
            | CURRENT_DATE + Optional(LPAR + Optional(string_literal) + RPAR)
            | CURRENT_TIMESTAMP + Optional(LPAR + Optional(string_literal) + RPAR)
        )
        bind_parameter = Word("?", nums) | Combine(oneOf(": @ $") + parameter_name)
        type_name = oneOf("""TEXT REAL INTEGER BLOB NULL TIMESTAMP STRING DATE
            INT64 NUMERIC FLOAT64 BOOL BOOLEAN BYTES DATETIME GEOGRAPHY TIME ARRAY
            STRUCT""", caseless=True)
        date_part = oneOf("""MICROSECOND MILLISECOND SECOND MINUTE HOUR DAYOFWEEK
            DAY DAYOFYEAR WEEK ISOWEEK MONTH QUARTER YEAR ISOYEAR DATE TIME
            """, caseless=True)
        datetime_operators = (
            DATE_ADD | DATE_SUB | ADDDATE | SUBDATE | TIMESTAMP_ADD | TIMESTAMP_SUB
        )

        grouping_term = expr.copy()
        ordering_term = Group(
            expr("order_key")
            + Optional(COLLATE + collation_name("collate"))
            + Optional(ASC | DESC)("direction")
        )("ordering_term")

        function_arg = expr.copy()("function_arg")
        function_args = Optional(
            "*"
            | Optional(DISTINCT)
            + delimitedList(function_arg)
            + Optional((RESPECT | IGNORE) + NULLS)
        )("function_args")
        function_call = (
            function_name("function_name")
            + LPAR
            + Group(function_args)("function_args_group")
            + RPAR
        )

        navigation_function_name = (
            FIRST_VALUE
            | LAST_VALUE
            | NTH_VALUE
            | LEAD
            | LAG
            | PERCENTILE_CONT
            | PRECENTILE_DISC
        )
        aggregate_function_name = (
            ANY_VALUE
            | ARRAY_AGG
            | ARRAY_CONCAT_AGG
            | AVG
            | BIT_AND
            | BIT_OR
            | BIT_XOR
            | COUNT
            | COUNTIF
            | LOGICAL_AND
            | LOGICAL_OR
            | MAX
            | MIN
            | STRING_AGG
            | SUM
        )
        statistical_aggregate_function_name = (
            CORR
            | COVAR_POP
            | COVAR_SAMP
            | STDDEV_POP
            | STDDEV_SAMP
            | STDDEV
            | VAR_POP
            | VAR_SAMP
            | VARIANCE
        )
        numbering_function_name = (
            RANK | DENSE_RANK | PERCENT_RANK | CUME_DIST | NTILE | ROW_NUMBER
        )
        analytic_function_name = (
            navigation_function_name
            | aggregate_function_name
            | statistical_aggregate_function_name
            | numbering_function_name
        )("analytic_function_name")
        partition_expression_list = delimitedList(grouping_term)(
            "partition_expression_list"
        )
        window_frame_boundary_start = (
            UNBOUNDED + PRECEDING
            | numeric_literal + (PRECEDING | FOLLOWING)
            | CURRENT + ROW
        )
        window_frame_boundary_end = (
            UNBOUNDED + FOLLOWING
            | numeric_literal + (PRECEDING | FOLLOWING)
            | CURRENT + ROW
        )
        window_frame_clause = (ROWS | RANGE) + (
            ((UNBOUNDED + PRECEDING) | (numeric_literal + PRECEDING) | (CURRENT + ROW))
            | (BETWEEN + window_frame_boundary_start + AND + window_frame_boundary_end)
        )
        window_name = identifier.copy()("window_name")
        window_specification = (
            Optional(window_name)
            + Optional(PARTITION + BY + partition_expression_list)
            + Optional(ORDER + BY + delimitedList(ordering_term))
            + Optional(window_frame_clause)("window_specification")
        )
        analytic_function = (
            analytic_function_name
            + LPAR
            + function_args
            + RPAR
            + OVER
            + (window_name | LPAR + Optional(window_specification) + RPAR)
        )("analytic_function")

        string_agg_term = (
            STRING_AGG
            + LPAR
            + Optional(DISTINCT)
            + expr
            + Optional(COMMA + string_literal)
            + Optional(
                ORDER + BY + expr + Optional(ASC | DESC) + Optional(LIMIT + integer)
            )
            + RPAR
        )("string_agg")
        array_literal = (
            Optional(ARRAY + Optional(LT + delimitedList(type_name) + GT))
            + LBRACKET
            + delimitedList(expr)
            + RBRACKET
        )
        interval = INTERVAL + expr + date_part
        array_generator = (
            GENERATE_ARRAY
            + LPAR
            + numeric_literal
            + COMMA
            + numeric_literal
            + COMMA
            + numeric_literal
            + RPAR
        )
        date_array_generator = (
            (GENERATE_DATE_ARRAY | GENERATE_TIMESTAMP_ARRAY)
            + LPAR
            + expr("start_date")
            + COMMA
            + expr("end_date")
            + Optional(COMMA + interval)
            + RPAR
        )

        explicit_struct = (
            STRUCT
            + Optional(LT + delimitedList(type_name) + GT)
            + LPAR
            + Optional(delimitedList(expr + Optional(AS + identifier)))
            + RPAR
        )

        case_when = WHEN + expr.copy()("when")
        case_then = THEN + expr.copy()("then")
        case_clauses = Group((case_when + case_then)[...])
        case_else = ELSE + expr.copy()("else")
        case_stmt = (
            CASE
            + Optional(expr.copy())
            + case_clauses("case_clauses")
            + Optional(case_else) + END
        )("case")
        if_expr = IF + LPAR + expr + COMMA + expr + COMMA + expr + RPAR

        expr_term = (
            (analytic_function)("analytic_function")
            | (CAST + LPAR + expr + AS + type_name + RPAR)("cast")
            | (SAFE_CAST + LPAR + expr + AS + type_name + RPAR)("safe_cast")
            | (Optional(EXISTS) + LPAR + ungrouped_select_stmt + RPAR)("subselect")
            | (literal_value)("literal")
            | (bind_parameter)("bind_parameter")
            | (EXTRACT + LPAR + expr + FROM + expr + RPAR)("extract")
            | case_stmt
            | (datetime_operators + LPAR + expr + COMMA + interval + RPAR)(
                "date_operation"
            )
            | string_agg_term("string_agg_term")
            | array_literal("array_literal")
            | array_generator("array_generator")
            | date_array_generator("date_array_generator")
            | explicit_struct("explicit_struct")
            | function_call("function_call")
            | qualified_column_name("column")
        ) + Optional(LBRACKET + (OFFSET | ORDINAL) + LPAR + expr + RPAR + RBRACKET)(
            "offset_ordinal"
        )

        struct_term = LPAR + delimitedList(expr_term) + RPAR

        UNARY, BINARY, TERNARY = 1, 2, 3
        expr <<= infixNotation(
            (expr_term | struct_term),
            [
                (oneOf("- + ~") | NOT, UNARY, opAssoc.RIGHT),
                (ISNULL | NOTNULL | NOT + NULL, UNARY, opAssoc.LEFT),
                ("||", BINARY, opAssoc.LEFT),
                (oneOf("* / %"), BINARY, opAssoc.LEFT),
                (oneOf("+ -"), BINARY, opAssoc.LEFT),
                (oneOf("<< >> & |"), BINARY, opAssoc.LEFT),
                (oneOf("= > < >= <= <> != !< !>"), BINARY, opAssoc.LEFT),
                (
                    IS + Optional(NOT)
                    | Optional(NOT) + IN + Optional(UNNEST)
                    | Optional(NOT) + LIKE
                    | GLOB
                    | MATCH
                    | REGEXP,
                    BINARY,
                    opAssoc.LEFT,
                ),
                ((BETWEEN, AND), TERNARY, opAssoc.LEFT),
                (
                    Optional(NOT)
                    + IN
                    + LPAR
                    + Group(ungrouped_select_stmt | delimitedList(expr))
                    + RPAR,
                    UNARY,
                    opAssoc.LEFT,
                ),
                (AND, BINARY, opAssoc.LEFT),
                (OR, BINARY, opAssoc.LEFT),
            ],
        )
        quoted_expr = (
            expr | QUOT + expr + QUOT | APOS + expr + APOS | ACC + expr + ACC
        )("quoted_expr")

        compound_operator = (
            UNION + Optional(ALL | DISTINCT)
            | INTERSECT + DISTINCT
            | EXCEPT + DISTINCT
            | INTERSECT
            | EXCEPT
        )("compound_operator")

        join_constraint = Group(
            Optional(
                ON + expr
                | USING + LPAR + Group(delimitedList(qualified_column_name)) + RPAR
            )
        )("join_constraint")

        join_op = (
            COMMA
            | Group(
                Optional(NATURAL)
                + Optional(
                    INNER
                    | CROSS
                    | LEFT + OUTER
                    | LEFT
                    | RIGHT + OUTER
                    | RIGHT
                    | FULL + OUTER
                    | OUTER
                    | FULL
                )
                + JOIN
            )
        )("join_op")

        join_source = Forward()

        # We support a few kinds of table identifiers.
        #
        # First, dot delimited info like project.dataset.table, where
        # each component follows the rules described in the BigQuery
        # docs, namely:
        #  Contain letters (upper or lower case), numbers, and underscores
        #
        # Second, a dot delimited quoted string.  Since it's quoted, we'll be
        # liberal w.r.t. what characters we allow.  E.g.:
        #  `project.dataset.name-with-dashes`
        #
        # Third, a series of quoted strings, delimited by dots, e.g.:
        #  `project`.`dataset`.`name-with-dashes`
        #
        # We also support combinations, like:
        #  project.dataset.`name-with-dashes`
        #  `project`.`dataset.name-with-dashes`
        #
        # In some cases, the identifier might include more than 3 dots.
        # Metadata view names include dots, e.g.
        # project.dataset.INFORMATION_SCHEMA.TABLES.
        # In this case, the trailing information is a "table" we're selecting
        # from.

        def record_quoted_table_identifier(t):
            identifier_list = t.asList()[0].split('.')
            # If the next to last item is "INFORMATION_SCHEMA", then combine
            # it with the last item; they're essentially the view name.
            if (len(identifier_list) > 1) and (identifier_list[-2].upper() == "INFORMATION_SCHEMA"):
                identifier_list[-2] = identifier_list[-2] + "." + identifier_list[-1]
                del identifier_list[-1]

            first = ".".join(identifier_list[0:-2]) or None
            second = identifier_list[-2]
            third = identifier_list[-1]
            identifier_list = [first, second, third]
            padded_list = [None] * (3 - len(identifier_list)) + identifier_list
            cls._table_identifiers.add(tuple(padded_list))

        def record_unquoted_table_identifier(t):
            identifier_list = t.asList()
            if cls._external_query_name is not None:
                if len(identifier_list) != 1:
                    raise Exception(
                        (f"_external_query_name is {cls._external_query_name} but identifier_list is not only " +
                         f"table name: {identifier_list}"))
                else:
                    identifier_list.insert(0, cls._external_query_name)
            padded_list = [None] * (3 - len(identifier_list)) + identifier_list
            # If padded list has more than 3 elements, combine the "trailing"
            # elements into a single identifier
            if len(padded_list) > 3:
                padded_list = [padded_list[0], padded_list[1], ".".join(padded_list[2:])]
            cls._table_identifiers.add(tuple(padded_list))

        quoted_table_parts_identifier = (
            Optional((quoted_name_part.copy()("project") | standard_name_part.copy()("project")) + Suppress('.'))
            + Optional((quoted_name_part.copy()("dataset") | standard_name_part.copy()("dataset")) + Suppress('.'))
            + Optional(INFORMATION_SCHEMA + Suppress('.'))
            + (quoted_tablename_part.copy()("table") | standard_name_part.copy()("table"))
        ).setParseAction(lambda t: record_unquoted_table_identifier(t))

        quotable_table_parts_identifier = (
            Suppress("`") + CharsNotIn("`") + Suppress("`")
        ).setParseAction(lambda t: record_quoted_table_identifier(t))

        table_identifier = quoted_table_parts_identifier | quotable_table_parts_identifier

        def unset_external_query_name(tokens):
            cls._external_query_name = None

        def set_external_query_name(tokens):
            if cls._external_query_name is not None:
                raise Exception(
                    (f"external_query_name value is {cls._external_query_name} and trying to set it to {tokens[0]}." +
                     " Nested external queries?"))
            cls._external_query_name = tokens[0]

        external_query = (EXTERNAL_QUERY + LPAR + QuotedString('"').setParseAction(set_external_query_name) + ","
                          + Suppress('"') + ungrouped_select_stmt + Suppress('"')
                          + RPAR).setParseAction(unset_external_query_name)

        single_source = (
            (
                table_identifier
                + Optional(Optional(AS) + table_alias("table_alias*"))
                + Optional(FOR + SYSTEMTIME + AS + OF + string_literal)
                + Optional(INDEXED + BY + index_name("name") | NOT + INDEXED)
            )("index")
            | (LPAR + ungrouped_select_stmt + RPAR)
            | (LPAR + join_source + RPAR)
            | (UNNEST + LPAR + expr + RPAR)
        ) + Optional(Optional(AS) + table_alias)

        join_source <<= single_source + (join_op + single_source + join_constraint)[...]

        over_partition = (PARTITION + BY + delimitedList(partition_expression_list))(
            "over_partition"
        )
        over_order = ORDER + BY + delimitedList(ordering_term)
        over_unsigned_value_specification = expr
        over_window_frame_preceding = (
            UNBOUNDED + PRECEDING
            | over_unsigned_value_specification + PRECEDING
            | CURRENT + ROW
        )
        over_window_frame_following = (
            UNBOUNDED + FOLLOWING
            | over_unsigned_value_specification + FOLLOWING
            | CURRENT + ROW
        )
        over_window_frame_bound = (
            over_window_frame_preceding | over_window_frame_following
        )
        over_window_frame_between = (
            BETWEEN + over_window_frame_bound + AND + over_window_frame_bound
        )
        over_window_frame_extent = (
            over_window_frame_preceding | over_window_frame_between
        )
        over_row_or_range = (ROWS | RANGE) + over_window_frame_extent
        over = (
            OVER
            + LPAR
            + Optional(over_partition)
            + Optional(over_order)
            + Optional(over_row_or_range)
            + RPAR
        )("over")

        replace_col_expr = expr + Optional(AS) + column_name

        result_column = Optional(table_name + ".") + "*" + Optional(
            EXCEPT + LPAR + delimitedList(column_name) + RPAR
        ) + Optional(
            REPLACE + LPAR + delimitedList(replace_col_expr) + RPAR
        ) | Group(quoted_expr + Optional(over) + Optional(Optional(AS) + column_alias))

        window_select_clause = (
            WINDOW + identifier + AS + LPAR + window_specification + RPAR
        )

        with_stmt = Forward().setName("with statement")
        ungrouped_select_no_with = (
            SELECT
            + Optional(DISTINCT | ALL)
            + Group(delimitedList(result_column))("columns")
            + Optional(FROM + join_source("from*"))
            + Optional(WHERE + expr)
            + Optional(QUALIFY + expr)
            + Optional(
                GROUP + BY + Group(delimitedList(grouping_term))("group_by_terms")
            )
            + Optional(HAVING + expr("having_expr"))
            + Optional(
                ORDER + BY + Group(delimitedList(ordering_term))("order_by_terms")
            )
            + Optional(delimitedList(window_select_clause))
        )
        select_no_with = ungrouped_select_no_with | (
            LPAR + ungrouped_select_no_with + RPAR
        )
        select_core = Optional(with_stmt) + select_no_with
        grouped_select_core = select_core | (LPAR + select_core + RPAR)

        ungrouped_select_stmt <<= (
            grouped_select_core
            + (compound_operator + grouped_select_core)[...]
            + Optional(
                LIMIT
                + (Group(expr + OFFSET + expr) | Group(expr + COMMA + expr) | expr)(
                    "limit"
                )
            )
        )("select")
        select_stmt = ungrouped_select_stmt | (LPAR + ungrouped_select_stmt + RPAR)

        # define comment format, and ignore them
        sql_comment = oneOf("-- #") + restOfLine | cStyleComment
        select_stmt.ignore(sql_comment)

        def record_with_alias(t):
            identifier_list = t.asList()
            padded_list = [None] * (3 - len(identifier_list)) + identifier_list
            cls._with_aliases.add(tuple(padded_list))

        with_clause = Group(
            identifier.setParseAction(record_with_alias)
            + AS
            + LPAR
            + select_stmt
            + RPAR
        )
        with_stmt <<= WITH + delimitedList(with_clause)
        with_stmt.ignore(sql_comment)

        cls._parser = select_stmt
        return cls._parser

    def test(self, sql_stmt, expected_tables, verbose=False):
        def print_(*args):
            if verbose:
                print(*args)

        print_(sql_stmt.strip())
        found_tables = self.get_table_names(sql_stmt)
        print_(found_tables)
        expected_tables_set = set(expected_tables)

        if expected_tables_set != found_tables:
            raise Exception(
                f"Test {test_index} failed- expected {expected_tables_set} but got {found_tables}"
            )
        print_()


if __name__ == "__main__":
    # fmt: off
    TEST_CASES = [
        [
            """
            SELECT x FROM y.a, b
            """,
            [
                (None, "y", "a"),
                (None, None, "b"),
            ],
        ],
        [
            """
            SELECT x FROM y.a JOIN b
            """,
            [
                (None, "y", "a"),
                (None, None, "b"),
            ],
        ],
        [
            """
            select * from xyzzy where z > 100
            """,
            [
                (None, None, "xyzzy"),
            ],
        ],
        [
            """
            select * from xyzzy where z > 100 order by zz
            """,
            [
                (None, None, "xyzzy"),
            ],
        ],
        [
            """
            select * from xyzzy
            """,
            [
                (None, None, "xyzzy"),
            ],
        ],
        [
            """
            select z.* from xyzzy
            """,
            [
                (None, None, "xyzzy"),
            ],
        ],
        [
            """
            select a, b from test_table where 1=1 and b='yes'
            """,
            [
                (None, None, "test_table"),
            ],
        ],
        [
            """
            select a, b from test_table where 1=1 and b in (select bb from foo)
            """,
            [
                (None, None, "test_table"),
                (None, None, "foo"),
            ],
        ],
        [
            """
            select z.a, b from test_table where 1=1 and b in (select bb from foo)
            """,
            [
                (None, None, "test_table"),
                (None, None, "foo"),
            ],
        ],
        [
            """
            select z.a, b from test_table where 1=1 and b in (select bb from foo) order by b,c desc,d
            """,
            [
                (None, None, "test_table"),
                (None, None, "foo"),
            ],
        ],
        [
            """
            select z.a, b from test_table left join test2_table where 1=1 and b in (select bb from foo)
            """,
            [
                (None, None, "test_table"),
                (None, None, "test2_table"),
                (None, None, "foo"),
            ],
        ],
        [
            """
            select a, db.table.b as BBB from db.table where 1=1 and BBB='yes'
            """,
            [
                (None, "db", "table"),
            ],
        ],
        [
            """
            select a, db.table.b as BBB from test_table,db.table where 1=1 and BBB='yes'
            """,
            [
                (None, None, "test_table"),
                (None, "db", "table"),
            ],
        ],
        [
            """
            select a, db.table.b as BBB from test_table,db.table where 1=1 and BBB='yes' limit 50
            """,
            [
                (None, None, "test_table"),
                (None, "db", "table"),
            ],
        ],
        [
            """
            select a, b from test_table where (1=1 or 2=3) and b='yes' group by zx having b=2 order by 1
            """,
            [
                (None, None, "test_table"),
            ],
        ],
        [
            """
            select
                a,
                b
                # this is a comment
            from
                test_table
                # another comment
            where (1=1 or 2=3) and b='yes'
            #yup, a comment
            group by zx having b=2 order by 1
            """,
            [
                (None, None, "test_table"),
            ],
        ],
        [
            """
            SELECT COUNT(DISTINCT foo) FROM bar JOIN baz ON bar.baz_id = baz.id
            """,
            [
                (None, None, "bar"),
                (None, None, "baz"),
            ],
        ],
        [
            """
            SELECT COUNT(DISTINCT foo) FROM bar, baz WHERE bar.baz_id = baz.id
            """,
            [
                (None, None, "bar"),
                (None, None, "baz"),
            ],
        ],
        [
            """
            WITH one AS (SELECT id FROM foo) SELECT one.id
            """,
            [
                (None, None, "foo"),
            ],
        ],
        [
            """
            WITH one AS (SELECT id FROM foo), two AS (select id FROM bar) SELECT one.id, two.id
            """,
            [
                (None, None, "foo"),
                (None, None, "bar"),
            ],
        ],
        [
            """
            SELECT x,
              RANK() OVER (ORDER BY x ASC) AS rank,
              DENSE_RANK() OVER (ORDER BY x ASC) AS dense_rank,
              ROW_NUMBER() OVER (PARTITION BY x ORDER BY y) AS row_num
            FROM a
            """,
            [
                (None, None, "a"),
            ],
        ],
        [
            """
            SELECT x, COUNT(*) OVER ( ORDER BY x
              RANGE BETWEEN 2 PRECEDING AND 2 FOLLOWING ) AS count_x
            FROM T
            """,
            [
                (None, None, "T"),
            ],
        ],
        [
            """
            SELECT firstname, department, startdate,
              RANK() OVER ( PARTITION BY department ORDER BY startdate ) AS rank
            FROM Employees
            """,
            [
                (None, None, "Employees"),
            ],
        ],
        # A fragment from https://cloud.google.com/bigquery/docs/reference/standard-sql/navigation_functions
        [
            """
            SELECT 'Sophia Liu' as name,
              TIMESTAMP '2016-10-18 2:51:45' as finish_time,
              'F30-34' as division
              UNION ALL SELECT 'Lisa Stelzner', TIMESTAMP '2016-10-18 2:54:11', 'F35-39'
              UNION ALL SELECT 'Nikki Leith', TIMESTAMP '2016-10-18 2:59:01', 'F30-34'
              UNION ALL SELECT 'Lauren Matthews', TIMESTAMP '2016-10-18 3:01:17', 'F35-39'
              UNION ALL SELECT 'Desiree Berry', TIMESTAMP '2016-10-18 3:05:42', 'F35-39'
              UNION ALL SELECT 'Suzy Slane', TIMESTAMP '2016-10-18 3:06:24', 'F35-39'
              UNION ALL SELECT 'Jen Edwards', TIMESTAMP '2016-10-18 3:06:36', 'F30-34'
              UNION ALL SELECT 'Meghan Lederer', TIMESTAMP '2016-10-18 3:07:41', 'F30-34'
              UNION ALL SELECT 'Carly Forte', TIMESTAMP '2016-10-18 3:08:58', 'F25-29'
              UNION ALL SELECT 'Lauren Reasoner', TIMESTAMP '2016-10-18 3:10:14', 'F30-34'
            """,
            [],
        ],
        # From https://cloud.google.com/bigquery/docs/reference/standard-sql/navigation_functions
        [
            """
            WITH finishers AS
             (SELECT 'Sophia Liu' as name,
              TIMESTAMP '2016-10-18 2:51:45' as finish_time,
              'F30-34' as division
              UNION ALL SELECT 'Lisa Stelzner', TIMESTAMP '2016-10-18 2:54:11', 'F35-39'
              UNION ALL SELECT 'Nikki Leith', TIMESTAMP '2016-10-18 2:59:01', 'F30-34'
              UNION ALL SELECT 'Lauren Matthews', TIMESTAMP '2016-10-18 3:01:17', 'F35-39'
              UNION ALL SELECT 'Desiree Berry', TIMESTAMP '2016-10-18 3:05:42', 'F35-39'
              UNION ALL SELECT 'Suzy Slane', TIMESTAMP '2016-10-18 3:06:24', 'F35-39'
              UNION ALL SELECT 'Jen Edwards', TIMESTAMP '2016-10-18 3:06:36', 'F30-34'
              UNION ALL SELECT 'Meghan Lederer', TIMESTAMP '2016-10-18 3:07:41', 'F30-34'
              UNION ALL SELECT 'Carly Forte', TIMESTAMP '2016-10-18 3:08:58', 'F25-29'
              UNION ALL SELECT 'Lauren Reasoner', TIMESTAMP '2016-10-18 3:10:14', 'F30-34')
            SELECT name,
              FORMAT_TIMESTAMP('%X', finish_time) AS finish_time,
              division,
              FORMAT_TIMESTAMP('%X', fastest_time) AS fastest_time,
              TIMESTAMP_DIFF(finish_time, fastest_time, SECOND) AS delta_in_seconds
            FROM (
              SELECT name,
              finish_time,
              division,
              FIRST_VALUE(finish_time)
                OVER (PARTITION BY division ORDER BY finish_time ASC
                ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING) AS fastest_time
              FROM finishers)
            """,
            [],
        ],
        # From https://cloud.google.com/bigquery/docs/reference/standard-sql/navigation_functions
        [
            """
                WITH finishers AS
                 (SELECT 'Sophia Liu' as name,
                  TIMESTAMP '2016-10-18 2:51:45' as finish_time,
                  'F30-34' as division
                  UNION ALL SELECT 'Lisa Stelzner', TIMESTAMP '2016-10-18 2:54:11', 'F35-39'
                  UNION ALL SELECT 'Nikki Leith', TIMESTAMP '2016-10-18 2:59:01', 'F30-34'
                  UNION ALL SELECT 'Lauren Matthews', TIMESTAMP '2016-10-18 3:01:17', 'F35-39'
                  UNION ALL SELECT 'Desiree Berry', TIMESTAMP '2016-10-18 3:05:42', 'F35-39'
                  UNION ALL SELECT 'Suzy Slane', TIMESTAMP '2016-10-18 3:06:24', 'F35-39'
                  UNION ALL SELECT 'Jen Edwards', TIMESTAMP '2016-10-18 3:06:36', 'F30-34'
                  UNION ALL SELECT 'Meghan Lederer', TIMESTAMP '2016-10-18 3:07:41', 'F30-34'
                  UNION ALL SELECT 'Carly Forte', TIMESTAMP '2016-10-18 3:08:58', 'F25-29'
                  UNION ALL SELECT 'Lauren Reasoner', TIMESTAMP '2016-10-18 3:10:14', 'F30-34')
                SELECT name,
                  FORMAT_TIMESTAMP('%X', finish_time) AS finish_time,
                  division,
                  FORMAT_TIMESTAMP('%X', slowest_time) AS slowest_time,
                  TIMESTAMP_DIFF(slowest_time, finish_time, SECOND) AS delta_in_seconds
                FROM (
                  SELECT name,
                  finish_time,
                  division,
                  LAST_VALUE(finish_time)
                    OVER (PARTITION BY division ORDER BY finish_time ASC
                    ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING) AS slowest_time
                  FROM finishers)
            """,
            [],
        ],
        # From https://cloud.google.com/bigquery/docs/reference/standard-sql/navigation_functions
        [
            """
            WITH finishers AS
             (SELECT 'Sophia Liu' as name,
              TIMESTAMP '2016-10-18 2:51:45' as finish_time,
              'F30-34' as division
              UNION ALL SELECT 'Lisa Stelzner', TIMESTAMP '2016-10-18 2:54:11', 'F35-39'
              UNION ALL SELECT 'Nikki Leith', TIMESTAMP '2016-10-18 2:59:01', 'F30-34'
              UNION ALL SELECT 'Lauren Matthews', TIMESTAMP '2016-10-18 3:01:17', 'F35-39'
              UNION ALL SELECT 'Desiree Berry', TIMESTAMP '2016-10-18 3:05:42', 'F35-39'
              UNION ALL SELECT 'Suzy Slane', TIMESTAMP '2016-10-18 3:06:24', 'F35-39'
              UNION ALL SELECT 'Jen Edwards', TIMESTAMP '2016-10-18 3:06:36', 'F30-34'
              UNION ALL SELECT 'Meghan Lederer', TIMESTAMP '2016-10-18 3:07:41', 'F30-34'
              UNION ALL SELECT 'Carly Forte', TIMESTAMP '2016-10-18 3:08:58', 'F25-29'
              UNION ALL SELECT 'Lauren Reasoner', TIMESTAMP '2016-10-18 3:10:14', 'F30-34')
            SELECT name,
              FORMAT_TIMESTAMP('%X', finish_time) AS finish_time,
              division,
              FORMAT_TIMESTAMP('%X', fastest_time) AS fastest_time,
              FORMAT_TIMESTAMP('%X', second_fastest) AS second_fastest
            FROM (
              SELECT name,
              finish_time,
              division,finishers,
              FIRST_VALUE(finish_time)
                OVER w1 AS fastest_time,
              NTH_VALUE(finish_time, 2)
                OVER w1 as second_fastest
              FROM finishers
              WINDOW w1 AS (
                PARTITION BY division ORDER BY finish_time ASC
                ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING))
            """,
            [],
        ],
        # From https://cloud.google.com/bigquery/docs/reference/standard-sql/navigation_functions
        [
            """
            WITH finishers AS
             (SELECT 'Sophia Liu' as name,
              TIMESTAMP '2016-10-18 2:51:45' as finish_time,
              'F30-34' as division
              UNION ALL SELECT 'Lisa Stelzner', TIMESTAMP '2016-10-18 2:54:11', 'F35-39'
              UNION ALL SELECT 'Nikki Leith', TIMESTAMP '2016-10-18 2:59:01', 'F30-34'
              UNION ALL SELECT 'Lauren Matthews', TIMESTAMP '2016-10-18 3:01:17', 'F35-39'
              UNION ALL SELECT 'Desiree Berry', TIMESTAMP '2016-10-18 3:05:42', 'F35-39'
              UNION ALL SELECT 'Suzy Slane', TIMESTAMP '2016-10-18 3:06:24', 'F35-39'
              UNION ALL SELECT 'Jen Edwards', TIMESTAMP '2016-10-18 3:06:36', 'F30-34'
              UNION ALL SELECT 'Meghan Lederer', TIMESTAMP '2016-10-18 3:07:41', 'F30-34'
              UNION ALL SELECT 'Carly Forte', TIMESTAMP '2016-10-18 3:08:58', 'F25-29'
              UNION ALL SELECT 'Lauren Reasoner', TIMESTAMP '2016-10-18 3:10:14', 'F30-34')
            SELECT name,
              finish_time,
              division,
              LEAD(name)
                OVER (PARTITION BY division ORDER BY finish_time ASC) AS followed_by
            FROM finishers
            """,
            [],
        ],
        # From https://cloud.google.com/bigquery/docs/reference/standard-sql/navigation_functions
        [
            """
            WITH finishers AS
             (SELECT 'Sophia Liu' as name,
              TIMESTAMP '2016-10-18 2:51:45' as finish_time,
              'F30-34' as division
              UNION ALL SELECT 'Lisa Stelzner', TIMESTAMP '2016-10-18 2:54:11', 'F35-39'
              UNION ALL SELECT 'Nikki Leith', TIMESTAMP '2016-10-18 2:59:01', 'F30-34'
              UNION ALL SELECT 'Lauren Matthews', TIMESTAMP '2016-10-18 3:01:17', 'F35-39'
              UNION ALL SELECT 'Desiree Berry', TIMESTAMP '2016-10-18 3:05:42', 'F35-39'
              UNION ALL SELECT 'Suzy Slane', TIMESTAMP '2016-10-18 3:06:24', 'F35-39'
              UNION ALL SELECT 'Jen Edwards', TIMESTAMP '2016-10-18 3:06:36', 'F30-34'
              UNION ALL SELECT 'Meghan Lederer', TIMESTAMP '2016-10-18 3:07:41', 'F30-34'
              UNION ALL SELECT 'Carly Forte', TIMESTAMP '2016-10-18 3:08:58', 'F25-29'
              UNION ALL SELECT 'Lauren Reasoner', TIMESTAMP '2016-10-18 3:10:14', 'F30-34')
            SELECT name,
              finish_time,
              division,
              LEAD(name, 2)
                OVER (PARTITION BY division ORDER BY finish_time ASC) AS two_runners_back
            FROM finishers
            """,
            [],
        ],
        # From https://cloud.google.com/bigquery/docs/reference/standard-sql/navigation_functions
        [
            """
            WITH finishers AS
             (SELECT 'Sophia Liu' as name,
              TIMESTAMP '2016-10-18 2:51:45' as finish_time,
              'F30-34' as division
              UNION ALL SELECT 'Lisa Stelzner', TIMESTAMP '2016-10-18 2:54:11', 'F35-39'
              UNION ALL SELECT 'Nikki Leith', TIMESTAMP '2016-10-18 2:59:01', 'F30-34'
              UNION ALL SELECT 'Lauren Matthews', TIMESTAMP '2016-10-18 3:01:17', 'F35-39'
              UNION ALL SELECT 'Desiree Berry', TIMESTAMP '2016-10-18 3:05:42', 'F35-39'
              UNION ALL SELECT 'Suzy Slane', TIMESTAMP '2016-10-18 3:06:24', 'F35-39'
              UNION ALL SELECT 'Jen Edwards', TIMESTAMP '2016-10-18 3:06:36', 'F30-34'
              UNION ALL SELECT 'Meghan Lederer', TIMESTAMP '2016-10-18 3:07:41', 'F30-34'
              UNION ALL SELECT 'Carly Forte', TIMESTAMP '2016-10-18 3:08:58', 'F25-29'
              UNION ALL SELECT 'Lauren Reasoner', TIMESTAMP '2016-10-18 3:10:14', 'F30-34')
            SELECT name,
              finish_time,
              division,
              LAG(name)
                OVER (PARTITION BY division ORDER BY finish_time ASC) AS preceding_runner
            FROM finishers
            """,
            [],
        ],
        # From https://cloud.google.com/bigquery/docs/reference/standard-sql/navigation_functions
        [
            """
            SELECT
              PERCENTILE_CONT(x, 0) OVER() AS min,
              PERCENTILE_CONT(x, 0.01) OVER() AS percentile1,
              PERCENTILE_CONT(x, 0.5) OVER() AS median,
              PERCENTILE_CONT(x, 0.9) OVER() AS percentile90,
              PERCENTILE_CONT(x, 1) OVER() AS max
            FROM UNNEST([0, 3, NULL, 1, 2]) AS x LIMIT 1
            """,
            [],
        ],
        # From https://cloud.google.com/bigquery/docs/reference/standard-sql/navigation_functions
        [
            """
            SELECT
              x,
              PERCENTILE_DISC(x, 0) OVER() AS min,
              PERCENTILE_DISC(x, 0.5) OVER() AS median,
              PERCENTILE_DISC(x, 1) OVER() AS max
            FROM UNNEST(['c', NULL, 'b', 'a']) AS x
            """,
            [],
        ],
        # From https://cloud.google.com/bigquery/docs/reference/standard-sql/timestamp_functions
        [
            """
            SELECT
              TIMESTAMP "2008-12-25 15:30:00 UTC" as original,
              TIMESTAMP_ADD(TIMESTAMP "2008-12-25 15:30:00 UTC", INTERVAL 10 MINUTE) AS later
            """,
            [],
        ],
        # Previously hosted on https://cloud.google.com/bigquery/docs/reference/standard-sql/timestamp_functions, but
        # appears to no longer be there
        [
            """
            WITH date_hour_slots AS (
             SELECT
               [
                    STRUCT(
                        " 00:00:00 UTC" as hrs,
                        GENERATE_DATE_ARRAY('2016-01-01', current_date(), INTERVAL 1 DAY) as dt_range),
                    STRUCT(
                        " 01:00:00 UTC" as hrs,
                        GENERATE_DATE_ARRAY('2016-01-01',current_date(), INTERVAL 1 DAY) as dt_range),
                    STRUCT(
                        " 02:00:00 UTC" as hrs,
                        GENERATE_DATE_ARRAY('2016-01-01', current_date(), INTERVAL 1 DAY) as dt_range),
                    STRUCT(
                        " 03:00:00 UTC" as hrs,
                        GENERATE_DATE_ARRAY('2016-01-01', current_date(), INTERVAL 1 DAY) as dt_range),
                    STRUCT(
                        " 04:00:00 UTC" as hrs,
                        GENERATE_DATE_ARRAY('2016-01-01', current_date(), INTERVAL 1 DAY) as dt_range),
                    STRUCT(
                        " 05:00:00 UTC" as hrs,
                        GENERATE_DATE_ARRAY('2016-01-01', current_date(), INTERVAL 1 DAY) as dt_range),
                    STRUCT(
                        " 06:00:00 UTC" as hrs,
                        GENERATE_DATE_ARRAY('2016-01-01', current_date(), INTERVAL 1 DAY) as dt_range),
                    STRUCT(
                        " 07:00:00 UTC" as hrs,
                        GENERATE_DATE_ARRAY('2016-01-01', current_date(), INTERVAL 1 DAY) as dt_range),
                    STRUCT(
                        " 08:00:00 UTC" as hrs,
                        GENERATE_DATE_ARRAY('2016-01-01', current_date(), INTERVAL 1 DAY ) as dt_range),
                    STRUCT(
                        " 09:00:00 UTC" as hrs,
                        GENERATE_DATE_ARRAY('2016-01-01', current_date(), INTERVAL 1 DAY) as dt_range),
                    STRUCT(
                        " 10:00:00 UTC" as hrs,
                        GENERATE_DATE_ARRAY('2016-01-01',current_date(), INTERVAL 1 DAY) as dt_range),
                    STRUCT(
                        " 11:00:00 UTC" as hrs,
                        GENERATE_DATE_ARRAY('2016-01-01',current_date(), INTERVAL 1 DAY) as dt_range),
                    STRUCT(
                        " 12:00:00 UTC" as hrs,
                        GENERATE_DATE_ARRAY('2016-01-01',current_date(), INTERVAL 1 DAY) as dt_range),
                    STRUCT(
                        " 13:00:00 UTC" as hrs,
                        GENERATE_DATE_ARRAY('2016-01-01',current_date(), INTERVAL 1 DAY) as dt_range),
                    STRUCT(
                        " 14:00:00 UTC" as hrs,
                        GENERATE_DATE_ARRAY('2016-01-01',current_date(), INTERVAL 1 DAY) as dt_range),
                    STRUCT(
                        " 15:00:00 UTC" as hrs,
                        GENERATE_DATE_ARRAY('2016-01-01',current_date(), INTERVAL 1 DAY) as dt_range),
                    STRUCT(
                        " 16:00:00 UTC" as hrs,
                        GENERATE_DATE_ARRAY('2016-01-01',current_date(), INTERVAL 1 DAY) as dt_range),
                    STRUCT(
                        " 17:00:00 UTC" as hrs,
                        GENERATE_DATE_ARRAY('2016-01-01',current_date(), INTERVAL 1 DAY) as dt_range),
                    STRUCT(
                        " 18:00:00 UTC" as hrs,
                        GENERATE_DATE_ARRAY('2016-01-01',current_date(), INTERVAL 1 DAY) as dt_range),
                    STRUCT(
                        " 19:00:00 UTC" as hrs,
                        GENERATE_DATE_ARRAY('2016-01-01',current_date(), INTERVAL 1 DAY) as dt_range),
                    STRUCT(
                        " 20:00:00 UTC" as hrs,
                        GENERATE_DATE_ARRAY('2016-01-01',current_date(), INTERVAL 1 DAY) as dt_range),
                    STRUCT(
                        " 21:00:00 UTC" as hrs,
                        GENERATE_DATE_ARRAY('2016-01-01',current_date(), INTERVAL 1 DAY) as dt_range),
                    STRUCT(
                        " 22:00:00 UTC" as hrs,
                        GENERATE_DATE_ARRAY('2016-01-01',current_date(), INTERVAL 1 DAY) as dt_range),
                    STRUCT(
                        " 23:00:00 UTC" as hrs,
                        GENERATE_DATE_ARRAY('2016-01-01',current_date(), INTERVAL 1 DAY) as dt_range)
                ]
                AS full_timestamps)
                SELECT
              dt AS dates, hrs, CAST(CONCAT( CAST(dt as STRING), CAST(hrs as STRING)) as TIMESTAMP) as timestamp_value
              FROM `date_hour_slots`, date_hour_slots.full_timestamps LEFT JOIN full_timestamps.dt_range as dt
            """,
            [
                (None, "date_hour_slots", "full_timestamps"),
                (None, "full_timestamps", "dt_range"),
            ],
        ],
        [
            """
            SELECT
                [foo],
                ARRAY[foo],
                ARRAY<int64, STRING>[foo, bar],
                STRUCT(1, 3),
                STRUCT<int64, STRING>(2, 'foo'),
                current_date(),
                GENERATE_ARRAY(5, NULL, 1),
                GENERATE_DATE_ARRAY('2016-10-05', '2016-10-01', INTERVAL 1 DAY),
                GENERATE_DATE_ARRAY('2016-10-05', NULL),
                GENERATE_DATE_ARRAY('2016-01-01', '2016-12-31', INTERVAL 2 MONTH),
                GENERATE_DATE_ARRAY('2000-02-01',current_date(), INTERVAL 1 DAY),
                GENERATE_TIMESTAMP_ARRAY('2016-10-05 00:00:00', '2016-10-05 00:00:02', INTERVAL 1 SECOND)
            FROM
                bar
            """,
            [
                (None, None, "bar"),
            ],
        ],
        [
            """
            SELECT GENERATE_ARRAY(start, 5) AS example_array
            FROM UNNEST([3, 4, 5]) AS start
            """,
            [],
        ],
        [
            """
            WITH StartsAndEnds AS (
              SELECT DATE '2016-01-01' AS date_start, DATE '2016-01-31' AS date_end
              UNION ALL SELECT DATE "2016-04-01", DATE "2016-04-30"
              UNION ALL SELECT DATE "2016-07-01", DATE "2016-07-31"
              UNION ALL SELECT DATE "2016-10-01", DATE "2016-10-31"
            )
            SELECT GENERATE_DATE_ARRAY(date_start, date_end, INTERVAL 1 WEEK) AS date_range
            FROM StartsAndEnds
            """,
            [],
        ],
        [
            """
            SELECT GENERATE_TIMESTAMP_ARRAY(start_timestamp, end_timestamp, INTERVAL 1 HOUR)
              AS timestamp_array
            FROM
              (SELECT
                TIMESTAMP '2016-10-05 00:00:00' AS start_timestamp,
                TIMESTAMP '2016-10-05 02:00:00' AS end_timestamp
               UNION ALL
               SELECT
                TIMESTAMP '2016-10-05 12:00:00' AS start_timestamp,
                TIMESTAMP '2016-10-05 14:00:00' AS end_timestamp
               UNION ALL
               SELECT
                TIMESTAMP '2016-10-05 23:59:00' AS start_timestamp,
                TIMESTAMP '2016-10-06 01:59:00' AS end_timestamp)
            """,
            [],
        ],
        [
            """
            SELECT DATE_SUB(current_date("-08:00")), INTERVAL 2 DAY)
            """,
            [],
        ],
        [
            """
            SELECT
                case when (a) then b else c end
            FROM d
            """,
            [
                (None, None, "d"),
            ],
        ],
        [
            """
            SELECT
                e,
                case when (f) then g else h end
            FROM i
            """,
            [
                (None, None, "i"),
            ],
        ],
        [
            """
            SELECT
                case when j then k else l end
            FROM m
            """,
            [
                (None, None, "m",),
            ],
        ],
        [
            """
            SELECT
                n,
                case when o then p else q end
            FROM r
            """,
            [
                (None, None, "r"),
            ],
        ],
        [
            """
            SELECT
                case s when (t) then u else v end
            FROM w
            """,
            [
                (None, None, "w"),
            ],
        ],
        [
            """
            SELECT
                x,
                case y when (z) then aa else ab end
            FROM ac
            """,
            [
                (None, None, "ac"),
            ],
        ],
        [
            """
            SELECT
                case ad when ae then af else ag end
            FROM ah
            """,
            [
                (None, None, "ah"),
            ],
        ],
        [
            """
            SELECT
                ai,
                case aj when ak then al else am end
            FROM an
            """,
            [
                (None, None, "an"),
            ],
        ],
        [
            """
            WITH
                ONE AS (SELECT x FROM y),
                TWO AS (select a FROM b)
            SELECT y FROM onE JOIN TWo
            """,
            [
                (None, None, "y"),
                (None, None, "b"),
            ],
        ],
        [
            """
            SELECT
                a,
                (SELECT b FROM oNE)
            FROM OnE
            """,
            [
                (None, None, "oNE"),
                (None, None, "OnE"),
            ],
        ],
        [
            """
            SELECT * FROM `a.b.c`
            """,
            [
                ("a", "b", "c"),
            ],
        ],
        [
            """
            SELECT * FROM `b.c`
            """,
            [
                (None, "b", "c"),
            ],
        ],
        [
            """
            SELECT * FROM `c`
            """,
            [
                (None, None, "c"),
            ],
        ],
        [
            """
            SELECT * FROM a.b.c
            """,
            [
                ("a", "b", "c"),
            ],
        ],
        [
            """
            SELECT * FROM `a`.`b`.`c`
            """,
            [
                ("a", "b", "c"),
            ],
        ],
        [
            """
            SELECT * FROM `a.b.c`
            """,
            [
                ("a", "b", "c"),
            ],
        ],
        [
            """
            SELECT *
            FROM t1
            WHERE t1.a IN (SELECT t2.a
                           FROM t2 ) FOR SYSTEM_TIME AS OF t1.timestamp_column)
            """,
            [
                (None, None, "t1"),
                (None, None, "t2"),
            ],
        ],
        [
            """
            WITH a AS (SELECT b FROM c)
            SELECT d FROM A JOIN e ON f = g JOIN E ON h = i
            """,
            [
                (None, None, "c"),
                (None, None, "e"),
                (None, None, "E"),
            ],
        ],
        [
            """
            with
            a as (
                (
                    select b from
                    (
                        select c from d
                    )
                    Union all
                    (
                        select e from f
                    )
                )
            )

            select g from h
            """,
            [
                (None, None, "d"),
                (None, None, "f"),
                (None, None, "h"),
            ],
        ],
        [
            """
            WITH x AS (
                SELECT a
                FROM b
                WINDOW w as (PARTITION BY a)
            )
            SELECT y FROM z
            """,
            [
                (None, None, "b"),
                (None, None, "z")
            ],
        ],
        [
            """
            SELECT DISTINCT
                FIRST_VALUE(x IGNORE NULLS) OVER (PARTITION BY y)
            FROM z
            """,
            [
                (None, None, "z")
            ],
        ],
        [
            """
            SELECT a . b .   c
            FROM d
            """,
            [
                (None, None, "d")
            ],
        ],
        [
            """
            WITH a AS (
                SELECT b FROM c
                UNION ALL
                (
                    WITH d AS (
                        SELECT e FROM f
                    )
                    SELECT g FROM d
                )
            )
            SELECT h FROM a
            """,
            [
                (None, None, "c"),
                (None, None, "f")
            ],
        ],
        [
            """
            WITH a AS (
                SELECT b FROM c
                UNION ALL
                (
                    WITH d AS (
                        SELECT e FROM f
                    )
                    SELECT g FROM d
                )
            )
            (SELECT h FROM a)
            """,
            [
                (None, None, "c"),
                (None, None, "f")
            ],
        ],
        [
            """
            SELECT * FROM a.b.`c`
            """,
            [
                ("a", "b", "c"),
            ],
        ],
    ]
    # fmt: on

    parser = BigQueryViewParser()
    for test_index, test_case in enumerate(TEST_CASES):
        sql, expected = test_case
        parser.test(sql_stmt=sql, expected_tables=expected, verbose=True)
