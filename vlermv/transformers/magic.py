'''
Come up with a reasonable file name from a wide range of possible
input formats. (Multiple inputs can map to the same file name.)
'''
import os
try:
    from urllib.parse import urlsplit
except ImportError:
    import urllib2
    urlsplit = urllib2.urlparse.urlsplit
import warnings
import itertools
import datetime

# For Python 2 compatibility
try:
    basestring
except NameError:
    basestring = str

def from_path(obj):
    return obj

def to_path(index):
    if not safe_type(index):
        warnings.warn(UserWarning('You should pass an object with a deterministic order. (probably not a %s)' % type(index).__name__))

    return tuple(filter(lambda x: x!= '', replace_special(parse(index))))

def parse(index):
    for theclass in [basestring, datetime.date, datetime.datetime, int, type(None)]:
        if isinstance(index, theclass):
            yield from parse_partial(index) # tuple
            break
    else:
        yield from itertools.chain(*map(parse, index)) # iterable

_special = {'.': '\\.', '..': '\\..', '.tmp': '\\.tmp'}
def replace_special(path):
    for item in path:
        if item in _special:
            yield _special[item]
        else:
            yield item

def parse_partial(item):
    if isinstance(item, basestring):
        func = parse_partial_text
    elif isinstance(item, int):
        func = lambda x: (str(x),)
    elif isinstance(item, datetime.date) or isinstance(item, datetime.datetime):
        func = parse_partial_date
    elif item == None:
        func = lambda _: ('',)
    else:
        raise ValueError('item must be string, datetime.date, datetime.datetime or int')
    return tuple(func(item))
#   yield from func(item)

def parse_partial_text(item):
    for a in parse_partial_url(item):
        for b in a.split('\\'):
            if b != '':
                yield b

def parse_partial_url(item):
    url = urlsplit(item)
    path = []

    if url.scheme:
        path.append(url.scheme)

    if url.netloc:
        path.append(url.netloc)

    if url.path:
        for y in filter(None, url.path.split('/')):
            path.append(y)

    if len(path) == 0:
        path = ['']

    if url.query:
        path[-1] += '?' + url.query

    if url.fragment:
        path[-1] += '#' + url.fragment

    return tuple(path)

def parse_partial_date(item):
    return ('%04d' % item.year, '%02d' % item.month, '%02d' % item.day)

def safe_type(index):
    for bad in [set,dict]:
        if isinstance(index, bad):
            return False
    else:
        return True
