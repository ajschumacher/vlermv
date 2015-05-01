import os

from ._util import split, _get_fn
from ._fs import mktemp, _random_file_name, _reversed_directories
from ._exceptions import (
    OpenError, PermissionError,
    DeleteError, FileExistsError,
    out_of_space,
)
from .serializers import pickle
from .transformers import simple

class Vlermv:
    '''
    Fancy database with a :py:class:`dict` API.
    '''
    def __repr__(self):
        return 'Vlermv(%s)' % repr(self.cachedir)

    def __init__(self, cachedir,
            serializer = pickle,
            key_transformer = simple,
            mutable = True,
            tempdir = '.tmp',
            cache_exceptions = False):
        '''
        :param str cachedir: Top-level directory of the vlermv
        :param serializer: A thing with dump and load attribute functions,
            like json, yaml, dill, or anything in vlermv.serializers
        :param key_transformer: How to transform keys to filenames and back.
            Several are available in :py:mod:`vlermv.transformers`.
        :param bool mutable: Whether values can be updated and deleted
        :param str tempdir: Subdirectory inside of ``cachedir`` to use for temporary files

        This one is only relevant for initialization via :py:func:`vlermv.cache`.

        :param cache_exceptions: If the decorated function raises an exception,
            should the failure and exception be cached? The exception is raised
            either way.
        '''

        if cache_exceptions and not getattr(serializer, 'vlermv_cache_exceptions', True):
            msg = 'Serializer %s cannot cache exceptions.'
            raise TypeError(msg % repr(serializer))

        self.binary_mode = getattr(serializer, 'vlermv_binary_mode', False)

        # Default function, if called with ``Vlermv`` rather than ``cache``.
        self.func = self.__getitem__

        self.cachedir = os.path.expanduser(cachedir)
        self.serializer = serializer
        self.mutable = mutable
        self.transformer = key_transformer
        self.tempdir = os.path.join(self.cachedir, tempdir)
        self.cache_exceptions = cache_exceptions

        os.makedirs(self.tempdir, exist_ok = True)

    def __call__(self, *args, **kwargs):
        if args in self:
            output = self[args]
        else:
            try:
                result = self.func(*args, **kwargs)
            except Exception as error:
                if self.cache_exceptions:
                    output = error, None
                else:
                    raise error
            else:
                output = None, result
            self[args] = output

        if self.cache_exceptions:
            if len(output) != 2:
                msg = '''Deserializer returned %d elements,
but it is supposed to return only two (exception, object).
Perhaps the serializer doesn't implement exception caching properly?'''
                raise TypeError(msg % len(output))

            error, result = output
            if error != None and result != None:
                raise TypeError('''The exception or the object (or both) must be None.
There's probably a problem with the serializer.''')

            if error:
                raise error
        else:
            result = output

        return result

    def filename(self, index):
        '''
        Get the filename corresponding to a key; that is, run the
        transformer on the key.
        '''
        subpath = self.transformer.to_path(index)
        if len(subpath) == 0:
            raise KeyError('You specified an empty key.')

        if subpath[0] == '/':
            subpath = subpath[1:]

        return os.path.join(self.cachedir, *subpath)

    def __iter__(self):
        return (k for k in self.keys())

    def __setitem__(self, index, obj):
        fn = self.filename(index)
        os.makedirs(os.path.dirname(fn), exist_ok = True)
        if (not self.mutable) and os.path.exists(fn):
            raise PermissionError('This warehouse is immutable, and %s already exists.' % fn)
        else:
            tmp = mktemp(self.tempdir)
            with open(tmp, 'w' + self._b()) as fp:
                try:
                    self.serializer.dump(obj, fp)
                except Exception as e:
                    if out_of_space(e):
                        fp.close()
                        os.remove(tmp)
                        raise BufferError('Out of space')
                    else:
                        raise
            os.rename(tmp, fn)

    def __getitem__(self, index):
        return _get_fn(self.filename(index), 'r' + self._b(), self.serializer.load)

    def _b(self):
        return 'b' if self.binary_mode else ''

    def __delitem__(self, index):
        if not self.mutable:
            raise PermissionError('This warehouse is immutable, so you can\'t delete things.')

        fn = self.filename(index)
        try:
            os.remove(fn)
        except DeleteError as e:
            raise KeyError(*e.args)
        else:
            for fn in _reversed_directories(self.cachedir, os.path.dirname(fn)):
                if os.listdir(fn) == []:
                    os.rmdir(fn)
                else:
                    break

    def __contains__(self, index):
        fn = self.filename(index)
        return os.path.isfile(fn)

    def __len__(self):
        length = 0
        for dirpath, _, filenames in os.walk(self.cachedir):
            for filename in filenames:
                length += 1
        return length

    def keys(self):
        for dirpath, _, filenames in os.walk(self.cachedir):
            if dirpath != os.path.join(self.cachedir, self.tempdir):
                for filename in filenames:
                    path = os.path.relpath(os.path.join(dirpath, filename), self.cachedir)
                    yield self.transformer.from_path(split(path))

    def values(self):
        for key, value in self.items():
            yield value

    def items(self):
        for key in self.keys():
            yield key, self[key]

    def update(self, d):
        generator = d.items() if hasattr(d, 'items') else d
        for k, v in generator:
            self[k] = v

    def get(self, index, default = None):
        if index in self:
            return self[index]
        else:
            return default