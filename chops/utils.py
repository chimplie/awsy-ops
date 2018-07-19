import collections
import copy
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


def deep_merge(dct: dict, merge_dct: dict, add_keys=True):
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

    Args:
        dct (dict) onto which the merge is executed
        merge_dct (dict): dct merged into dct
        add_keys (bool): whether to add new keys

    Returns:
        dict: updated dict
    """
    dct = dct.copy()
    if not add_keys:
        merge_dct = {
            k: merge_dct[k]
            for k in set(dct).intersection(set(merge_dct))
        }

    for k, v in merge_dct.items():
        if (k in dct and isinstance(dct[k], dict)
                and isinstance(merge_dct[k], collections.Mapping)):
            dct[k] = deep_merge(dct[k], merge_dct[k], add_keys=add_keys)
        else:
            dct[k] = merge_dct[k]

    return dct
