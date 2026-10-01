from itertools import chain

__all__ = ['flatten']

def flatten(l):
    return list(chain.from_iterable(l))

