# delta_time.py
#
# Parser to convert a conversational time reference such as "in a minute" or
# "noon tomorrow" and convert it to a Python datetime. The returned
# ParseResults object contains
#   - original - the original time expression string
#   - computed_dt - the Python datetime representing the computed time
#   - relative_to - the reference "now" time
#   - time_offset - the difference between the reference time and the computed time
#
# BNF:
#     time_and_day ::= time_reference [day_reference] | day_reference 'at' absolute_time_of_day
#     day_reference ::= absolute_day_reference | relative_day_reference
#     absolute_day_reference ::= 'today' | 'tomorrow' | 'yesterday' | ('next' | 'last') weekday_name
#     relative_day_reference ::= 'in' qty day_units
#                                | qty day_units 'ago'
#                                | 'qty day_units ('from' | 'before' | 'after') absolute_day_reference
#     day_units ::= 'days' | 'weeks'
#
#     time_reference ::= absolute_time_of_day | relative_time_reference
#     relative_time_reference ::= qty time_units ('from' | 'before' | 'after') absolute_time_of_day
#                                 | qty time_units 'ago'
#                                 | 'in' qty time_units
#     time_units ::= 'hours' | 'minutes' | 'seconds'
#     absolute_time_of_day ::= 'noon' | 'midnight' | 'now' | absolute_time
#     absolute_time ::=  24hour_time | hour ("o'clock" | ':' minute) ('AM'|'PM')
#
#     qty ::= integer | integer_words | 'a couple of' | 'a' | 'the'
#
# Copyright 2010, 2019 by Paul McGuire
#

import calendar
from datetime import datetime, time as datetime_time, timedelta
from typing import Optional

import pyparsing as pp

__all__ = ["time_expression"]


# basic grammar definitions
def _make_integer_word_expr(int_name: str, int_value: int) -> pp.CaselessKeyword:
    return pp.CaselessKeyword(
        int_name, ident_chars=pp.srange("[A-Za-z-]")
    ).add_parse_action(pp.replace_with(int_value))


integer_word = pp.MatchFirst(
    _make_integer_word_expr(int_str, int_value)
    for int_value, int_str in enumerate(
        "one two three four five six seven eight nine ten"
        " eleven twelve thirteen fourteen fifteen sixteen"
        " seventeen eighteen nineteen twenty twenty-one"
        " twenty-two twenty-three twenty-four".split(),
        start=1,
    )
).set_name("integer_word")

integer = pp.pyparsing_common.integer | integer_word
integer.set_name("numeric")

CK = pp.CaselessKeyword
CL = pp.CaselessLiteral
today, tomorrow, yesterday, noon, midnight, now = CK.using_each(
    "today tomorrow yesterday noon midnight now".split()
)


def _singular_or_plural(s: str) -> pp.ParserElement:
    return CK(s) | CK(s + "s").add_parse_action(pp.replace_with(s))


week, day, hour, minute, second = map(
    _singular_or_plural, "week day hour minute second".split()
)
time_units = hour | minute | second
any_time_units = (week | day | time_units).set_name("any_time_units")

am = CL("am")
pm = CL("pm")
COLON = pp.Suppress(":")

in_ = CK("in").set_parse_action(pp.replace_with(1))
from_ = CK("from").set_parse_action(pp.replace_with(1))
before = CK("before").set_parse_action(pp.replace_with(-1))
after = CK("after").set_parse_action(pp.replace_with(1))
ago = CK("ago").set_parse_action(pp.replace_with(-1))
next_ = CK("next").set_parse_action(pp.replace_with(1))
last_ = CK("last").set_parse_action(pp.replace_with(-1))
at_ = CK("at")
on_ = CK("on")
a_ = CK("a")
an_ = CK("an")
of_ = CK("of")
the_ = CK("the")
adverb_ = pp.MatchFirst(CK.using_each("just only exactly".split())).suppress()

couple = (
    (pp.Opt(CK("a")) + CK("couple") + pp.Opt(CK("of")))
    .set_parse_action(pp.replace_with(2))
    .set_name("couple")
)

a_qty = (a_ | an_).set_parse_action(pp.replace_with(1))
the_qty = the_.set_parse_action(pp.replace_with(1))
qty = pp.ungroup(
    pp.Opt(adverb_) + (integer | couple | a_qty | the_qty).set_name("qty_expression")
).set_name("qty")
time_ref_present = pp.Empty().add_parse_action(pp.replace_with(True))(
    "time_ref_present"
)


def _fill_24hr_time_fields(t: pp.ParseResults) -> None:
    t["HH"] = t[0]
    t["MM"] = t[1]
    t["SS"] = 0
    t["ampm"] = "am" if t.HH < 12 else "pm"


def _fill_default_time_fields(t: pp.ParseResults) -> None:
    for fld in "HH MM SS".split():
        if fld not in t:
            t[fld] = 0


# get weekday names from the calendar module
weekday_names = list(calendar.day_name)
weekday_name = pp.MatchFirst(CK.using_each(weekday_names)).set_name("weekday_name")

# expressions for military 2400 time
_24hour_time = ~(pp.Word(pp.nums) + any_time_units).set_name(
    "numbered_time_units"
) + pp.Word(pp.nums, exact=4, as_keyword=True).set_name("HHMM").add_parse_action(
    lambda t: [int(t[0][:2]), int(t[0][2:])], _fill_24hr_time_fields
)
_24hour_time.set_name("0000 time")
ampm = am | pm
o_clock = CK("o'clock", ident_chars=pp.srange("[A-Za-z']"))
timespec = (
    integer("HH")
    + pp.Opt(o_clock | COLON + integer("MM") + pp.Opt(COLON + integer("SS")))
    + (am | pm)("ampm")
).add_parse_action(_fill_default_time_fields)
absolute_time = _24hour_time | timespec
absolute_time.set_name("absolute time")

absolute_time_of_day = noon | midnight | now | absolute_time
absolute_time_of_day.set_name("time of day")


def _add_computed_time(t: pp.ParseResults) -> None:
    initial_word = t[0]
    if initial_word in "now noon midnight".split():
        t["computed_time"] = {
            "now": datetime.now().time().replace(microsecond=0),
            "noon": datetime_time(hour=12),
            "midnight": datetime_time(hour=0),
        }[initial_word]
    else:
        t["HH"] = {"am": int(t["HH"]) % 12, "pm": int(t["HH"]) % 12 + 12}[t.ampm]
        t["computed_time"] = datetime_time(hour=t.HH, minute=t.MM, second=t.SS)


absolute_time_of_day.add_parse_action(_add_computed_time)


#     relative_time_reference ::= qty time_units ('ago' | ('from' | 'before' | 'after') absolute_time_of_day)
#                                 | 'in' qty time_units
time_units = (hour | minute | second).set_name("time unit")
relative_time_reference = (
    (
        qty("qty")
        + time_units("units")
        + (
            ago("dir")
            | (from_ | before | after)("dir")
            + pp.Group(absolute_time_of_day)("ref_time")
        )
    )
    | in_("dir") + qty("qty") + time_units("units")
).set_name("relative time")


def _compute_relative_time(t: pp.ParseResults) -> None:
    if "ref_time" not in t:
        t["ref_time"] = datetime.now().time().replace(microsecond=0)
    else:
        t["ref_time"] = t.ref_time.computed_time
    delta_seconds = {"hour": 3600, "minute": 60, "second": 1}[t.units] * t.qty
    t["time_delta"] = timedelta(seconds=t.dir * delta_seconds)


relative_time_reference.add_parse_action(_compute_relative_time)

time_reference = absolute_time_of_day | relative_time_reference
time_reference.set_name("time reference")


def _add_default_time_ref_fields(t: pp.ParseResults) -> None:
    if "time_delta" not in t:
        t["time_delta"] = timedelta()


time_reference.add_parse_action(_add_default_time_ref_fields)

#     absolute_day_reference ::= 'today' | 'tomorrow' | 'yesterday' | ('next' | 'last') weekday_name
#     day_units ::= 'days' | 'weeks'

day_units = day | week
weekday_reference = pp.Opt(next_ | last_, 1)("dir") + weekday_name("day_name")


def _convert_abs_day_reference_to_date(t: pp.ParseResults) -> None:
    now_ref = datetime.now().replace(microsecond=0)

    # handle day reference by weekday name
    if "day_name" in t:
        today_num = now_ref.weekday()
        day_names = [n.lower() for n in weekday_names]
        named_day_num = day_names.index(t.day_name.lower())
        # compute difference in days - if current weekday name is referenced, then
        # computed 0 offset is changed to 7
        if t.dir > 0:
            day_diff = (named_day_num + 7 - today_num) % 7 or 7
        else:
            day_diff = -((today_num + 7 - named_day_num) % 7 or 7)
        t["abs_date"] = datetime(now_ref.year, now_ref.month, now_ref.day) + timedelta(
            day_diff
        )
    else:
        name = t[0]
        t["abs_date"] = {
            "now": now_ref,
            "today": datetime(now_ref.year, now_ref.month, now_ref.day),
            "yesterday": datetime(now_ref.year, now_ref.month, now_ref.day)
            + timedelta(days=-1),
            "tomorrow": datetime(now_ref.year, now_ref.month, now_ref.day)
            + timedelta(days=+1),
        }[name]


absolute_day_reference = (
    today | tomorrow | yesterday | (now + time_ref_present) | weekday_reference
)
absolute_day_reference.add_parse_action(_convert_abs_day_reference_to_date)
absolute_day_reference.set_name("absolute day")

#     relative_day_reference ::=  'in' qty day_units
#                                   | qty day_units
#                                     ('ago'
#                                      | ('from' | 'before' | 'after') absolute_day_reference)
relative_day_reference = in_("dir") + qty("qty") + day_units("units") | qty(
    "qty"
) + day_units("units") + (
    ago("dir") | ((from_ | before | after)("dir") + absolute_day_reference("ref_day"))
)
relative_day_reference.set_name("relative day")


def _compute_relative_date(t: pp.ParseResults) -> None:
    now = datetime.now().replace(microsecond=0)
    if "ref_day" in t:
        t["computed_date"] = t.ref_day
    else:
        t["computed_date"] = now.date()
    day_diff = t.dir * t.qty * {"week": 7, "day": 1}[t.units]
    t["date_delta"] = timedelta(days=day_diff)


relative_day_reference.add_parse_action(_compute_relative_date)

# combine expressions for absolute and relative day references
day_reference = relative_day_reference | absolute_day_reference
day_reference.set_name("day reference")


def _add_default_date_fields(t: pp.ParseResults) -> None:
    if "date_delta" not in t:
        t["date_delta"] = timedelta()


day_reference.add_parse_action(_add_default_date_fields)

# combine date and time expressions into single overall parser
time_and_day = time_reference + time_ref_present + pp.Opt(
    pp.Opt(on_) + day_reference
) | day_reference + pp.Opt(at_ + absolute_time_of_day + time_ref_present)
time_and_day.set_name("time and day")


# parse actions for total time_and_day expression
def _save_original_string(s: str, _: int, t: pp.ParseResults) -> None:
    # save original input string and reference time
    t["original"] = " ".join(s.strip().split())
    t["relative_to"] = datetime.now().replace(microsecond=0)


def _compute_timestamp(t: pp.ParseResults) -> None:
    # accumulate values from parsed time and day subexpressions - fill in defaults for omitted parts
    now = datetime.now().replace(microsecond=0)
    if "computed_time" not in t:
        t["computed_time"] = t.ref_time or now.time()
    if "abs_date" not in t:
        t["abs_date"] = now

    # roll up all fields and apply any time or day deltas
    t["computed_dt"] = (
        t.abs_date.replace(
            hour=t.computed_time.hour,
            minute=t.computed_time.minute,
            second=t.computed_time.second,
        )
        + (t.time_delta or timedelta(0))
        + (t.date_delta or timedelta(0))
    )

    # if time just given in terms of day expressions, zero out time fields
    if not t.time_ref_present:
        t["computed_dt"] = t.computed_dt.replace(hour=0, minute=0, second=0)

    # add results name compatible with previous version
    t["calculatedTime"] = t.computed_dt

    # add time_offset fields
    t["time_offset"] = t.computed_dt - t.relative_to


def _remove_temp_keys(t: pp.ParseResults) -> None:
    # strip out keys that are just used internally
    all_keys = list(t.keys())
    for k in all_keys:
        if k not in (
            "computed_dt",
            "original",
            "relative_to",
            "time_offset",
            "calculatedTime",
        ):
            del t[k]


time_and_day.add_parse_action(
    _save_original_string, _compute_timestamp, _remove_temp_keys
)


time_expression = time_and_day

_GENERATE_DIAGRAM = False
if _GENERATE_DIAGRAM:
    pp.autoname_elements()
    time_expression.create_diagram("delta_time.html")


# fmt: off
def main():
    current_time = datetime.now()
    time_of_day = timedelta(
        hours=current_time.hour,
        minutes=current_time.minute,
        seconds=current_time.second,
    )

    def offset_weekday(day_name: str, offset_dir: int) -> timedelta:
        if offset_dir == 1:
            offset = 0
        else:
            offset = -7

        day_num = {d: i for i, d in enumerate("Monday Tuesday Wednesday Thursday Friday Saturday Sunday".split())}
        return timedelta(days=(0 - current_time.weekday() + day_num[day_name] + offset) % 7)

    def next_weekday_by_name(day_name: str) -> timedelta:
        return offset_weekday(day_name, 1)

    def last_weekday_by_name(day_name: str) -> timedelta:
        return offset_weekday(day_name, -1)

    # test grammar
    tests = {
        "now": timedelta(0),
        "midnight": -time_of_day,
        "noon": timedelta(hours=12 - current_time.hour),
        "today": -time_of_day,
        "tomorrow": timedelta(days=1) - time_of_day,
        "yesterday": timedelta(days=-1) - time_of_day,
        "10 seconds ago": timedelta(seconds=-10),
        "100 seconds ago": timedelta(seconds=-100),
        "1000 seconds ago": timedelta(seconds=-1000),
        "10000 seconds ago": timedelta(seconds=-10000),
        "10 minutes ago": timedelta(minutes=-10),
        "10 minutes from now": timedelta(minutes=10),
        "in 10 minutes": timedelta(minutes=10),
        "in a minute": timedelta(minutes=1),
        "in a couple of minutes": timedelta(minutes=2),
        "20 seconds ago": timedelta(seconds=-20),
        "in 30 seconds": timedelta(seconds=30),
        "in an hour": timedelta(hours=1),
        "in a couple hours": timedelta(hours=2),
        "a week from now": timedelta(days=7),
        "3 days from now": timedelta(days=3),
        "a couple of days from now": timedelta(days=2),
        "an hour ago": timedelta(hours=-1),
        "in a couple days": timedelta(days=2) - time_of_day,
        "a week from today": timedelta(days=7) - time_of_day,
        "three weeks ago": timedelta(days=-21) - time_of_day,
        "a day ago": timedelta(days=-1) - time_of_day,
        "in a couple of days": timedelta(days=2) - time_of_day,
        "a couple of days from today": timedelta(days=2) - time_of_day,
        "2 weeks after today": timedelta(days=14) - time_of_day,
        "in 2 weeks": timedelta(days=14) - time_of_day,
        "the day after tomorrow": timedelta(days=2) - time_of_day,
        "the day before yesterday": timedelta(days=-2) - time_of_day,
        "8am the day after tomorrow": timedelta(days=+2) - time_of_day + timedelta(hours=8),
        "in a day": timedelta(days=1) - time_of_day,
        "3 days ago": timedelta(days=-3) - time_of_day,
        "noon tomorrow": timedelta(days=1) - time_of_day + timedelta(hours=12),
        "6am tomorrow": timedelta(days=1) - time_of_day + timedelta(hours=6),
        "0800 yesterday": timedelta(days=-1) - time_of_day + timedelta(hours=8),
        "1700 tomorrow": timedelta(days=1) - time_of_day + timedelta(hours=17),
        "12:15 AM today": -time_of_day + timedelta(minutes=15),
        "3pm 2 days from today": timedelta(days=2) - time_of_day + timedelta(hours=15),
        "ten seconds before noon tomorrow": (
                timedelta(days=1)
                - time_of_day
                + timedelta(hours=12)
                + timedelta(seconds=-10)
        ),
        "20 seconds before noon": -time_of_day + timedelta(hours=12) + timedelta(seconds=-20),
        "in 3 days at 5pm": timedelta(days=3) - time_of_day + timedelta(hours=17),
        "noon next Sunday": timedelta(hours=12 - current_time.hour) + next_weekday_by_name("Sunday"),
        "2pm next Sunday": timedelta(hours=14 - current_time.hour) + next_weekday_by_name("Sunday"),
        "2pm Sunday": timedelta(hours=14 - current_time.hour) + next_weekday_by_name("Sunday"),
        "next Sunday at 2pm": timedelta(hours=14 - current_time.hour) + next_weekday_by_name("Sunday"),
        "noon Sunday": timedelta(hours=12 - current_time.hour) + next_weekday_by_name("Sunday"),
        "noon last Sunday": timedelta(hours=12 - current_time.hour) + last_weekday_by_name("Sunday"),
        "last Sunday at 2am": timedelta(hours=2 - current_time.hour) + last_weekday_by_name("Sunday"),
        "20 hours from now": timedelta(hours=20),
        "twenty hours from now": timedelta(hours=20),
        "twenty-four hours from now": timedelta(days=1),
        "Twenty-four hours from now": timedelta(days=1),
        "just twenty-four hours from now": timedelta(days=1),
        "in just 10 seconds": timedelta(seconds=10),
        "in just a couple of hours": timedelta(hours=2),
        "in exactly 1 hour": timedelta(hours=1),
        "only one hour from now": timedelta(hours=1),
        "only a couple of days ago": timedelta(days=-2),
    }
    # fmt: on

    def verify_offset(test_time_str: str, parsed: pp.ParseResults) -> Optional[str]:
        # allow up to a 1-second time discrepancy due to test processing time
        time_epsilon = timedelta(seconds=1)

        if (parsed.time_offset - tests[test_time_str]) <= time_epsilon:
            parsed["verify_offset"] = "PASS"
        else:
            parsed["verify_offset"] = "FAIL"

    print(f"(relative to {datetime.now()})")
    success, report = time_expression.run_tests(list(tests), post_parse=verify_offset)
    assert success

    fails = []
    for test, rpt in report:
        if rpt.get("verify_offset", "PASS") != "PASS":
            fails.append((test, rpt))

    if fails:
        print("\nFAILED")
        print("\n".join(f"- {test}" for test, rpt in fails))

    assert not fails


if __name__ == "__main__":
    main()
