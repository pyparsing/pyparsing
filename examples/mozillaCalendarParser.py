from pyparsing import (
    Optional,
    one_of,
    Literal,
    Word,
    printables,
    Group,
    OneOrMore,
    ZeroOrMore,
)

"""
A simple parser for calendar (*.ics) files,
as exported by the Mozilla calendar.

Any suggestions and comments welcome.

Version:   0.1
Copyright: Petri Savolainen <firstname.lastname@iki.fi>
License:   Free for any use
"""


# TERMINALS

BEGIN = Literal("BEGIN:").suppress()
END = Literal("END:").suppress()
valstr = printables + "\xe4\xf6\xe5\xd6\xc4\xc5 "

EQ = Literal("=").suppress()
SEMI = Literal(";").suppress()
COLON = Literal(":").suppress()

EVENT = Literal("VEVENT").suppress()
CALENDAR = Literal("VCALENDAR").suppress()
ALARM = Literal("VALARM").suppress()

# TOKENS

CALPROP = one_of("VERSION PRODID METHOD", as_keyword=True)
ALMPROP = one_of("TRIGGER", as_keyword=True)
EVTPROP = one_of(
    """X-MOZILLA-RECUR-DEFAULT-INTERVAL
       X-MOZILLA-RECUR-DEFAULT-UNITS
       UID DTSTAMP LAST-MODIFIED X RRULE EXDATE""", as_keyword=True
)

valuestr = Word(valstr).set_name("valuestr")
propval = valuestr
typeval = valuestr
typename = one_of("VALUE MEMBER FREQ UNTIL INTERVAL", as_keyword=True)

proptype = Group(SEMI + typename + EQ + typeval).set_name("proptype").suppress()

calprop = Group(CALPROP + ZeroOrMore(proptype) + COLON + propval)
almprop = Group(ALMPROP + ZeroOrMore(proptype) + COLON + propval)
evtprop = (
    Group(EVTPROP + ZeroOrMore(proptype) + COLON + propval).suppress()
    | "CATEGORIES" + COLON + propval.set_results_name("categories")
    | "CLASS" + COLON + propval.set_results_name("class")
    | "DESCRIPTION" + COLON + propval.set_results_name("description")
    | "DTSTART" + proptype + COLON + propval.set_results_name("begin")
    | "DTEND" + proptype + COLON + propval.set_results_name("end")
    | "LOCATION" + COLON + propval.set_results_name("location")
    | "PRIORITY" + COLON + propval.set_results_name("priority")
    | "STATUS" + COLON + propval.set_results_name("status")
    | "SUMMARY" + COLON + propval.set_results_name("summary")
    | "URL" + COLON + propval.set_results_name("url")
).set_name("evtprop")
calprops = Group(OneOrMore(calprop)).set_name("calprops").suppress()
evtprops = Group(OneOrMore(evtprop))
almprops = Group(OneOrMore(almprop)).set_name("almprops").suppress()

alarm = (BEGIN + ALARM + almprops + END + ALARM).set_name("alarm")
event = (BEGIN + EVENT + evtprops + Optional(alarm) + END + EVENT).set_name("event")
events = Group(OneOrMore(event))
calendar = (BEGIN + CALENDAR + calprops + ZeroOrMore(event) + END + CALENDAR).set_name("calendar")
calendars = OneOrMore(calendar)


# PARSE ACTIONS


def gotEvent(s, loc, toks):
    for event in toks:
        print(event.dump())


event.set_parse_action(gotEvent)


# MAIN PROGRAM

if __name__ == "__main__":

    calendars.parse_file("mozilla.ics")
