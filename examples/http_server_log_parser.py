# httpServerLogParser.py
#
# Copyright (c) 2016, Paul McGuire
# Updated 2026 to newer Python and pyparsing styles, plus railroad
# diagram, timezone handling, Paul McGuire
#
"""
Parser for HTTP server log output, of the form:

195.146.134.15 - - [20/Jan/2003:08:55:36 -0800]
"GET /path/to/page.html HTTP/1.0" 200 4649 "http://www.somedomain.com/020602/page.html"
"Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1)"
127.0.0.1 - u.surname@domain.com [12/Sep/2006:14:13:53 +0300]
"GET /skins/monobook/external.png HTTP/1.0" 304 - "http://wiki.mysite.com/skins/monobook/main.css"
"Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US; rv:1.8.0.6) Gecko/20060728 Firefox/1.5.0.6"

You can then break it up as follows:
IP ADDRESS - -
Server Date / Time [SPACE]
"GET /path/to/page HTTP/Type Request"
Success Code
Bytes Sent To Client
Referer
Client Software
"""

import calendar
from datetime import datetime, timedelta, timezone

import pyparsing as pp


def _get_command_fields(t: pp.ParseResults) -> None:
    # strip quotes and split into parts
    t["method"], t["request_uri"], t["protocol_version"] = t[0].strip('"').split()


def _make_timezone(offset: str) -> timezone:
    """
    Convert a time zone offset string like "+0200" to a timezone object.
    (Must have a leading "+" or "-", and two digits for hours and minutes.)
    """
    if offset in ("+0000", "-0000"):
        return timezone.utc

    sign = 1 if offset[0] == "+" else -1
    hours = int(offset[1:3])
    minutes = int(offset[3:5])
    return timezone(sign * timedelta(hours=hours, minutes=minutes))


def _make_datetime(t: pp.ParseResults) -> None:
    """
    Parse action to compose a Python datetime object from the parsed timestamp fields.
    """
    year = int(t.year or 0)
    month = list(calendar.month_abbr).index(t.month)
    day = int(t.day or 1)
    hour = int(t.hour or 0)
    minute = int(t.minute or 0)
    second = int(t.second or 0)
    tz = _make_timezone(t.tz_offset) if t.tz_offset else None

    # add datetime as another named result
    t["datetime"] = datetime(
        year, month, day, hour, minute, second, tzinfo=tz
    )

def _restructure_timestamp(t: pp.ParseResults) -> None:
    """
    Parse action to restructure the parsed structure,
    adding a Python datetime field
    representation of the timestamp, and converting the nested ParseResults to a string.
    """
    _make_datetime(t[0])

    # convert nested ParseResults to string
    t[0][0] = ''.join(t[0][:-1])
    del t[0][1:-1]


log_line_bnf: pp.ParserElement = pp.NoMatch()


def get_log_line_bnf() -> pp.ParserElement:
    global log_line_bnf

    if isinstance(log_line_bnf, pp.NoMatch):
        integer = pp.Word(pp.nums)
        # use parse action to auto-convert parsed numeric string to int
        integer_value = integer().set_parse_action(lambda t: int(t[0]))
        ip_address = pp.DelimitedList(integer, ".", combine=True)

        # build up fields for timestamp
        _, *month_abbreviations = calendar.month_abbr
        month_abbr = pp.one_of(month_abbreviations).set_name("month_abbr")

        timestamp = (
            integer("day") + "/" + month_abbr("month") + "/" + integer("year")
            + ":"
            + integer("hour") + ":" + integer("minute") + ":" + integer("second")
        )

        time_zone_offset = pp.Word("+-", pp.nums)

        server_date_time = pp.Group(
            pp.Suppress("[") + timestamp + time_zone_offset("tz_offset") + pp.Suppress("]")
        ).add_parse_action(_restructure_timestamp)


        # add set_name() to all local vars that are ParserElements, for nice diagramming
        pp.autoname_elements()

        log_line_bnf = (
            ip_address("client_ip_addr")
            + ("-" | pp.Word(pp.alphanums + "@._"))("user_ident")
            + ("-" | pp.Word(pp.alphanums + "@._"))("auth")
            + server_date_time("timestamp")
            + pp.dbl_quoted_string("cmd_uri_protocol_version").set_parse_action(_get_command_fields)
            + (integer_value | "-")("status_code")
            + (integer_value | "-")("num_bytes_sent")
            + pp.dbl_quoted_string("referrer").set_parse_action(pp.remove_quotes)
            + pp.dbl_quoted_string("client_software").set_parse_action(pp.remove_quotes)
        ).set_name("log_line_bnf")

    return log_line_bnf


if __name__ == '__main__':

    get_log_line_bnf().create_diagram("http_server_log_parser_diagram.html", show_results_names=True)

    testdata = """
    195.146.134.15 - - [20/Jan/2003:08:55:36 +0000] "GET /path/to/page.html HTTP/1.0" 200 4649 "http://www.somedomain.com/020602/page.html" "Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1)"
    111.111.111.11 - - [16/Feb/2004:04:09:49 -0800] "GET /ads/redirectads/336x280redirect.htm HTTP/1.1" 304 - "http://www.foobarp.org/theme_detail.php?type=vs&cat=0&mid=27512" "Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1)"
    11.111.11.111 - - [16/Feb/2004:10:35:12 -0800] "GET /ads/redirectads/468x60redirect.htm HTTP/1.1" 200 541 "http://11.11.111.11/adframe.php?n=ad1f311a&what=zone:56" "Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1) Opera 7.20  [ru\"]"
    127.0.0.1 - u.surname@domain.com [12/Sep/2006:14:13:53 +0300] "GET /skins/monobook/external.png HTTP/1.0" 304 - "http://wiki.mysite.com/skins/monobook/main.css" "Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US; rv:1.8.0.6) Gecko/20060728 Firefox/1.5.0.6"
    """
    for line in testdata.splitlines():
        line = line.strip()
        if not line:
            continue

        print("\n------------------------")
        print(line)
        fields = get_log_line_bnf().parse_string(line)
        print(fields.dump())
