import pyparsing as pp


def camel_to_snake(s: str) -> str:
    """
    Convert CamelCase to snake_case.
    """
    return "".join("_" + c.lower() if c.isupper() else c for c in s).lstrip("_")


pre_pep8_names = """
addCondition addParseAction anyCloseTag anyOpenTag asDict asList cStyleComment canParseNext conditionAsParseAction 
convertToDate convertToDatetime convertToFloat convertToInteger countedArray cppStyleComment dblQuotedString 
dblSlashComment defaultName dictOf disableMemoization downcaseTokens enableLeftRecursion enablePackrat getName 
htmlComment ignoreWhitespace indentedBlock infixNotation inlineLiteralsUsing javaStyleComment leaveWhitespace 
lineEnd lineStart locatedExpr matchOnlyAtCol matchPreviousExpr matchPreviousLiteral nestedExpr nullDebugAction oneOf 
originalTextFor parseFile parseString parseWithTabs pythonStyleComment quotedString removeQuotes replaceWith 
resetCache restOfLine runTests scanString searchString setBreak setDebug setDebugActions setDefaultWhitespaceChars 
setFailAction setName setParseAction setResultsName setWhitespaceChars sglQuotedString stringEnd stringStart tokenMap 
traceParseAction transformString tryParse unicodeString upcaseTokens withAttribute withClass
""".split()

special_changes = {
    "opAssoc": "OpAssoc",
    "delimitedList": "DelimitedList",
    "delimited_list": "DelimitedList",
    "replaceHTMLEntity": "replace_html_entity",
    "makeHTMLTags": "make_html_tags",
    "makeXMLTags": "make_xml_tags",
    "commonHTMLEntity": "common_html_entity",
    "stripHTMLTags": "strip_html_tags",
}

pre_pep8_name = pp.one_of(set(pre_pep8_names), as_keyword=True)
pre_pep8_name.set_parse_action(lambda t: camel_to_snake(t[0]))
special_pre_pep8_name = pp.one_of(special_changes, as_keyword=True)
special_pre_pep8_name.set_parse_action(lambda t: special_changes[t[0]])

pep8_converter = pre_pep8_name | special_pre_pep8_name

if __name__ == "__main__":
    from pathlib import Path
    import sys

    def usage():
        tool_name = Path(__file__).name
        print(
            f"{tool_name}\n"
            "Utility to convert Python pyparsing scripts using legacy"
            " camelCase names to use PEP8 snake_case names.\n\n"
            f"Usage: python {tool_name} <source_filename>...\n"
        )
        exit()

    if len(sys.argv) == 1:
        usage()
        sys.exit(1)

    for filename_pattern in sys.argv[1:]:

        for filename in Path().glob(filename_pattern):
            if not Path(filename).is_file():
                continue

            try:
                modified_contents = pep8_converter.transform_string(
                    Path(filename).read_text()
                )
                Path(filename).write_text(modified_contents)
                print(f"Converted {filename}")
            except Exception as e:
                print(f"Failed to convert {filename}: {type(e).__name__}: {e}")
