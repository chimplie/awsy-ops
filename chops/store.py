import logging
import os
from typing import Dict, Optional
import yaml


class Store(object):
    def __init__(self, path, logger=None):
        if logger is None:
            logger = logging.getLogger('chops.Store')

        self.path = path
        self.logger = logger
        self._store = {}

        self.load()

    def has(self, path):
        """
        Returns whether path exists in the store.
        :param path:
        :return:
        """
        parts = path.split('.')
        node: Optional[Dict] = self._store

        for p in parts[:-1]:
            if p not in node:
                return False
            node = node[p]

        return parts[-1] in node

    def init(self, path, value=None):
        """
        Initialize store item at the given path with a given value if path does not exist.
        Dumps store when operation completed.
        :param path:
        :param value:
        :return:
        """
        if not self.has(path):
            self.set(path, value)
            self.dump()

    def get(self, path: str, default=None):
        """
        Returns value of the given path or default value if path does not exist.
        :param path:
        :param default:
        :return:
        """
        parts = path.split('.')
        node: Optional[Dict] = self._store

        for p in parts[:-1]:
            node = node.get(p)
            if node is None:
                return default

        return node.get(parts[-1], default)

    def set(self, key: str, value):
        """
        Set's value of the given path.
        If parent nodes does not exist the function will create dictionaries for them.
        Dumps store when operation completed.
        :param key:
        :param value:
        :return:
        """
        parts = key.split('.')
        node: Optional[Dict] = self._store

        for p in parts[:-1]:
            if p in node:
                node = node.get(p)
            else:
                node[p] = {}
                node = node[p]

        node[parts[-1]] = value

        self.dump()

    def delete(self, path):
        """
        Deletes path from the storage.
        :param path:
        :return:
        """
        if not self.has(path):
            raise KeyError('Path "{}" does not belong to storage.'.format(path))

        parts = path.split('.')
        parent = self.get('.'.join(path[:-1]))
        del parent[parts[-1]]

    def append(self, path, value):
        """
        Appends value to the iterable at the path.
        If necessary, creates a list at the path.
        Dumps store when operation completed.
        :param path:
        :param value:
        :return:
        """
        self.init(path, [])
        node = self.get(path)
        node.append(value)
        self.dump()

    def include(self, path, value):
        """
        Includes value to the iterable at the path treating it as a set.
        If necessary, creates a list at the path.
        Dumps store when operation completed.
        :param path:
        :param value:
        :return:
        """
        self.init(path, [])
        node = self.get(path)

        if value not in node:
            node.append(value)
            self.dump()

    def has_item(self, path, item):
        """
        Returns whether item exists in the iterable of the given path.
        :param path:
        :param item:
        :return:
        """
        return self.has(path) and item in self.get(path)

    def load(self):
        """
        Loads store from the filesystem.
        Dumps current store if store file does not exist.
        :return:
        """
        if os.path.isfile(self.path):
            with open(self.path) as f:
                self._store = yaml.load(f)
        else:
            self.dump()

    def dump(self):
        """
        Dumps store to the filesystem.
        :return:
        """
        self.logger.debug('Writing store to {path}...'.format(path=self.path))
        with open(self.path, 'w') as f:
            return yaml.dump(self._store, f)
