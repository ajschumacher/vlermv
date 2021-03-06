import os
from ...serializers import pickle
from shutil import rmtree

from ..._vlermv import Vlermv

class Base:
    def teardown_method(self, method):
        rmtree(self.directory)

class identity_transformer:
    @staticmethod
    def to_path(key):
        return key

    @staticmethod
    def from_path(path):
        return path

def simple_vlermv(cachedir):
    return Vlermv(cachedir, key_transformer = identity_transformer,
        serializer = pickle)
