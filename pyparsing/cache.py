from collections import OrderedDict
from dataclasses import dataclass
from threading import RLock


@dataclass
class PackratStats:
    hit = 0
    miss = 0


class Cache:
    not_in_cache = object()

    def __init__(self):
        self.lock = RLock()
        self.stats = PackratStats()

    def get(self, key):
        pass

    def set(self, key, value):
        pass

    def len(self):
        return 0

    def clear(self):
        pass


class UnboundedCache(Cache):
    def __init__(self):
        Cache.__init__(self)
        self.cache = {}

    def get(self, key):
        output = self.cache.get(key)
        if output is None:
            self.stats.miss += 1
        else:
            self.stats.hit += 1
        return output

    def set(self, key, value):
        self.cache[key] = value

    def clear(self):
        self.stats = PackratStats()
        self.cache.clear()

    def len(self):
        return len(self.cache)


class FifoCache(Cache):
    def __init__(self, size):
        Cache.__init__(self)
        self.size = size
        self.cache = OrderedDict()

    def get(self, key):
        output = self.cache.get(key)
        if output is None:
            self.stats.miss += 1
        else:
            self.stats.hit += 1
        return output

    def set(self, key, value):
        self.cache[key] = value
        try:
            while len(self.cache) > self.size:
                self.cache.popitem(last=False)
        except KeyError:
            pass

    def clear(self):
        self.stats = PackratStats()
        self.cache.clear()

    def len(self):
        return len(self.cache)
