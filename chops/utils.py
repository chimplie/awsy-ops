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
