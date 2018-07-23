import collections.abc
import logging
import os
import uuid


PACKAGE_PATH = os.path.abspath(os.path.dirname(__file__))
PLUGINS_PATH = os.path.join(PACKAGE_PATH, 'plugins')
TEMPLATES_PATH = os.path.join(PACKAGE_PATH, 'templates')

CHOPS_SETTINGS_FILE = 'chops_settings.py'
CHOPS_STORE_FILE = 'chops_store.yml'

TEMPLATES = {
    CHOPS_SETTINGS_FILE: os.path.join(TEMPLATES_PATH, 'chops_settings_default.py'),
}


def version():
    with open(os.path.join(PACKAGE_PATH, 'VERSION'), encoding='utf-8') as f:
        return f.read()


def short_uuid():
    return str(uuid.uuid4())[:8]


def create_simple_id(prefix: str):
    return '{base}-{uuid}'.format(
        base=prefix,
        uuid=short_uuid()
    )


def create_id(prefix: str):
    return '{base}-{uuid}'.format(
        base=prefix,
        uuid=str(uuid.uuid4())[:13]
    )


_loggers = {}


def get_logger(name, level=None):
    if name in _loggers:
        return _loggers[name]

    if level is None:
        level = os.environ.get('LOG_LEVEL', logging.INFO)

    logger = logging.getLogger(name)
    logger.setLevel(level)

    ch = logging.StreamHandler()
    ch.setLevel(level)

    logger.addHandler(ch)

    _loggers[name] = logger
    return logger


def is_dict_like_list(obj):
    """ Checks whether the passed object can be considered as a dictionary-like list.
    By the dictionary-like list we mean a list which items are {'name': ..., 'value': ...}
    dictionaries.

    Args:
        obj (Any) an object ot test

    Returns:
        bool: whether passed object is a dictionary-like list
    """

    if not isinstance(obj, collections.abc.Iterable):
        return False
    for item in obj:
        if not isinstance(item, collections.abc.Mapping):
            return False
        if not ('name' in item and 'value' in item):
            return False
        if len(item.keys()) != 2:
            return False

    return True


def deep_merge(dct: dict, merge_dct: dict, add_keys=True, merge_list_maps=True):
    """ Recursive dict merge. Inspired by :meth:``dict.update()``, instead of
    updating only top-level keys, deep_merge recurses down into dicts nested
    to an arbitrary depth, updating keys. The ``merge_dct`` is merged into
    ``dct``.

    Copied from: https://gist.github.com/angstwad/bf22d1822c38a92ec0a9
    Thanks to: https://gist.github.com/DomWeldon

    This version will return a copy of the dictionary and leave the original
    arguments untouched.

    The optional argument ``add_keys``, determines whether keys which are
    present in ``merge_dict`` but not ``dct`` should be included in the
    new dict.

    Also if this function finds lists which elements are {'name': ..., 'value': ...}
    it tries to merge them as dictionaries. For example:

        ```
        A = {
            'foo': [
                {'name': 'First Name', 'value': 'John'},
                {'name': 'Second Name', 'value': 'Smith'},
            ]
        }

        B = {
            'foo': [
                {'name': 'Middle Name', 'value': 'V.'},
            ]
        }

        C = deep_merge(A, B)

        C == {
            'foo': [
                {'name': 'First Name', 'value': 'John'},
                {'name': 'Second Name', 'value': 'Smith'},
                {'name': 'Middle Name', 'value': 'V.'},
            ]
        }
        ```

    Args:
        dct (dict) onto which the merge is executed
        merge_dct (dict): dct merged into dct
        add_keys (bool): whether to add new keys
        merge_list_maps (bool): whether to merge dictionary-like lists

    Returns:
        dict: updated dict
    """
    dct = dct.copy()

    if merge_list_maps and is_dict_like_list(dct) and is_dict_like_list(merge_dct):
        as_dict = deep_merge(
            {item['name']: item for item in dct},
            {item['name']: item for item in merge_dct},
            add_keys=add_keys,
            merge_list_maps=merge_list_maps
        )
        return list(as_dict.values())

    if not add_keys:
        merge_dct = {
            k: merge_dct[k]
            for k in set(dct).intersection(set(merge_dct))
        }

    for k, v in merge_dct.items():
        if (k in dct and isinstance(dct[k], dict)
                and isinstance(merge_dct[k], collections.abc.Mapping)):
            dct[k] = deep_merge(dct[k], merge_dct[k], add_keys=add_keys)
        elif merge_list_maps and is_dict_like_list(merge_dct[k]) and (is_dict_like_list(dct[k]) or k not in dict):
            dct[k] = deep_merge(dct[k], merge_dct[k], add_keys=add_keys)
        else:
            dct[k] = merge_dct[k]

    return dct
