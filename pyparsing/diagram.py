import railroad
import pyparsing

def make_diagram(element):
    diagram = railroad.Diagram(element.name)
    items = []

def to_diagram_element(element):
    """
    Recursively converts a PyParsing Element to a railroad Element
    """
    if isinstance(element, pyparsing.And):
        return railroad.Sequence([to_diagram_element(child) for child in element.exprs])
    elif isinstance(element, (pyparsing.Or, pyparsing.MatchFirst)):
        return railroad.Choice([[to_diagram_element(child) for child in element.exprs]])
    elif
