import statemachine
import librarybookstate


class Book:
    def __init__(self):
        self._state = librarybookstate.New()

    @property
    def state(self):
        return self._state

    # get behavior/properties from current state
    def __getattr__(self, attrname):
        attr = getattr(self._state, attrname)
        if isinstance(getattr(librarybookstate, attrname, None),
                      librarybookstate.BookStateTransition):
            return lambda: setattr(self, '_state', attr())
        return attr

    def __str__(self):
        return "{0}: {1}".format(self.__class__.__name__, self._state)


class RestrictedBook(Book):
    def __init__(self):
        super(RestrictedBook, self).__init__()
        self._authorized_users = []

    def authorize(self, name):
        self._authorized_users.append(name)

    # specialized checkout to check permission of user first
    def checkout(self, user=None):
        if user in self._authorized_users:
            self._state = self._state.checkout()
        else:
            raise Exception("{0} could not check out restricted book".format((user, "anonymous")[user is None]))


def run_demo():
    book = Book()
    book.shelve()
    print(book)
    book.checkout()
    print(book)
    book.checkin()
    print(book)
    book.reserve()
    print(book)
    try:
        book.checkout()
    except statemachine.InvalidTransitionException:
        print('..cannot check out reserved book')
    book.release()
    print(book)
    book.checkout()
    print(book)
    print()

    restricted_book = RestrictedBook()
    restricted_book.authorize("BOB")
    restricted_book.restrict()
    print(restricted_book)
    for name in [None, "BILL", "BOB"]:
        try:
            restricted_book.checkout(name)
        except Exception as e:
            print('..' + str(e))
        else:
            print('checkout to', name)
    print(restricted_book)
    restricted_book.checkin()
    print(restricted_book)


if __name__ == '__main__':
    run_demo()
