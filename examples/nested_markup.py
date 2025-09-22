#
# nested_markup.py
#
# Example markup parser to recursively transform nested markup directives.
#
# Copyright 2019, Paul McGuire
#
import pyparsing as pp

wiki_markup = pp.Forward()

# a method that will construct and return a parse action that will
# do the proper wrapping in opening and closing HTML, and recursively call
# wiki_markup.transform_string on the markup body text
def convert_markup_to_html(opening, closing):
    def conversionParseAction(s, l, t):
        return opening + wiki_markup.transform_string(t[1][1:-1]) + closing

    return conversionParseAction


# use a nested_expr with original_text_for to parse nested braces, but return the
# parsed text as a single string containing the outermost nested braces instead
# of a nested list of parsed tokens
markup_body = pp.original_text_for(pp.nested_expr("{", "}"))
italicized = ("ital" + markup_body).set_parse_action(
    convert_markup_to_html("<I>", "</I>")
)
bolded = ("bold" + markup_body).set_parse_action(convert_markup_to_html("<B>", "</B>"))

# another markup and parse action to parse links - again using transform string
# to recursively parse any markup in the link text
def convert_link_to_html(s, l, t):
    link_text, url = t._skipped
    t["link_text"] = wiki_markup.transform_string(link_text)
    t["url"] = url
    return '<A href="{url}">{link_text}</A>'.format_map(t)


urlRef = (pp.Keyword("link") + "{" + ... + "->" + ... + "}").set_parse_action(
    convert_link_to_html
)

# now inject all the markup bits as possible markup expressions
wiki_markup <<= urlRef | italicized | bolded

# try it out!
wiki_input = """
Here is a simple Wiki input:

  ital{This is in italics}.
  bold{This is in bold}!
  bold{This is in ital{bold italics}! But this is just bold.}
  Here's a URL to link{Pyparsing's bold{Wiki Page}!->https://github.com/pyparsing/pyparsing/wiki}
"""
print(wiki_markup.transform_string(wiki_input))
