#
# documentSignoffDemo.py
#
# Example of a state machine modeling the state of a document in a document
# control system, using named state transitions
#
import statemachine
import documentsignoffstate


class Document:
    def __init__(self):
        # start light in Red state
        self._state = documentsignoffstate.New()

    @property
    def state(self):
        return self._state

    # get behavior/properties from current state
    def __getattr__(self, attrname):
        attr = getattr(self._state, attrname)
        if isinstance(getattr(documentsignoffstate, attrname, None),
                      documentsignoffstate.DocumentRevisionStateTransition):
            return lambda : setattr(self, '_state', attr())
        return attr

    def __str__(self):
        return "{0}: {1}".format(self.__class__.__name__, self._state)


def run_demo():
    import random

    doc = Document()
    print(doc)

    # begin editing document
    doc.create()
    print(doc)
    print(doc.state.description)

    while not isinstance(doc._state, documentsignoffstate.Approved):

        print('...submit')
        doc.submit()
        print(doc)
        print(doc.state.description)

        if random.randint(1,10) > 3:
            print('...reject')
            doc.reject()
        else:
            print('...approve')
            doc.approve()

        print(doc)
        print(doc.state.description)

    doc.activate()
    print(doc)
    print(doc.state.description)

if __name__ == '__main__':
    run_demo()
