import railroad
import pyparsing

def get_name(element: pyparsing.ParserElement) -> str:
    return getattr(element, 'name', '')


def make_diagram(element: pyparsing.ParserElement) -> railroad.DiagramItem:
    return railroad.Diagram(get_name(element), to_diagram_element(element))


def to_diagram_element(element: pyparsing.ParserElement) -> railroad.DiagramItem:
    """
    Recursively converts a PyParsing Element to a railroad Element
    """
    if isinstance(element, pyparsing.And):
        if len(element.exprs) > 5:
            return railroad.Stack(
                [to_diagram_element(child) for child in element.exprs])
        else:
            return railroad.Sequence(
                [to_diagram_element(child) for child in element.exprs])
    elif isinstance(element, (pyparsing.Or, pyparsing.MatchFirst)):
        if len(element.exprs) > 5:
            return railroad.HorizontalChoice(
                [[to_diagram_element(child) for child in element.exprs]])
        else:
            return railroad.Choice(
                [[to_diagram_element(child) for child in element.exprs]])
    elif isinstance(element, pyparsing.Optional):
        return railroad.Optional(to_diagram_element(element.expr))
    elif isinstance(element, pyparsing.OneOrMore):
        return railroad.OneOrMore(to_diagram_element(element.expr))
    elif hasattr(element, 'expr'):
        return railroad.Group(to_diagram_element(element.expr), label=get_name(element.name))
    elif hasattr(element, 'exprs'):
        raise Exception()
    else:
        railroad.Terminal(element.name)
