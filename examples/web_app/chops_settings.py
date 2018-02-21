import os


HERE = os.path.abspath(os.path.dirname(__file__))
SETTINGS = dict()


SETTINGS['project_name'] = 'Chops Project'
SETTINGS['project_path'] = HERE


SETTINGS['plugins'] = [
    'chops.plugins.dotenv',
    'chops.plugins.docker',
]


SETTINGS['dotenv'] = {
    'env_files': {
        'main_dotenv_path': os.path.join(SETTINGS['project_path'], 'docker', '.env'),
    },
    'template': os.path.join(SETTINGS['project_path'], 'env.template'),
    'template_lock': os.path.join(SETTINGS['project_path'], 'env.template.lock'),
}

SETTINGS['docker'] = {
    'docker_root': os.path.join(SETTINGS['project_path'], 'docker'),
    'project_name': 'chopsexamplewebapp',
    'repository_prefix': None,
}
