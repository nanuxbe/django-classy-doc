from collections import OrderedDict


class DefaultOrderedDict(OrderedDict):

    def __init__(self, default_factory, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.default_factory = default_factory

    def __missing__(self, key):
        value = self.default_factory()
        self[key] = value
        return value
