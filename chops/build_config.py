import os
import pprint

from chops import utils


def get_chops_settings_path():
    def chop_settings_path(path):
        return os.path.join(path, utils.CHOPS_SETTINGS_FILE)

    path = os.getcwd()
    while not os.path.isfile(chop_settings_path(path)):
        path = os.path.dirname(path)
        if os.path.ismount(path):
            break

    settings_path = chop_settings_path(path)
    if os.path.isfile(settings_path):
        return settings_path
    else:
        return None


def load_chops_settings(config):
    settings_path = get_chops_settings_path()

    if settings_path is not None:
        config['project_path'] = os.path.dirname(settings_path)
        config['is_initialised'] = True

        from importlib.machinery import SourceFileLoader
        mod = SourceFileLoader('chops.settings', settings_path).load_module()
        settings = mod.SETTINGS
    else:
        config['project_path'] = os.getcwd()
        config['is_initialised'] = False

        from chops.templates.chops_settings_default import SETTINGS
        settings = SETTINGS

    config = {**config, **settings}

    return config


def get_build_config():
    config = dict()

    # Print functions
    config['pp'] = pprint.PrettyPrinter(indent=4)
    config['info'] = lambda x: print('\033[94m' + x + '\033[0m')

    # Load chops settings
    config = load_chops_settings(config)

    return config
