import os


PACKAGE_PATH = os.path.abspath(os.path.dirname(__file__))
PLUGINS_PATH = os.path.join(PACKAGE_PATH, 'plugins')
TEMPLATES_PATH = os.path.join(PACKAGE_PATH, 'templates')

CHOPS_SETTINGS_FILE = 'chops_settings.py'

TEMPLATES = {
    CHOPS_SETTINGS_FILE: os.path.join(TEMPLATES_PATH, 'chops_settings_default.py'),
}


def version():
    with open(os.path.join(PACKAGE_PATH, 'VERSION'), encoding='utf-8') as f:
        return f.read()
