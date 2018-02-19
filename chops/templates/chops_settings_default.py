import os

import chops


HERE = os.path.abspath(os.path.dirname(__file__))
SETTINGS = dict()


SETTINGS['project_name'] = 'Chops Project'
SETTINGS['project_path'] = HERE


SETTINGS['loaded_plugins'] = [
    'chops.plugins.dotenv_plugin',
]


SETTINGS['dotenv'] = {
    'env_files': {
        'main_dotenv_path': os.path.join(SETTINGS['project_path'], '.env'),
    },
    'template': os.path.join(chops.utils.PLUGINS_PATH, 'env.template'),
    'template_lock': os.path.join(SETTINGS['project_path'], 'env.template.lock'),
}
