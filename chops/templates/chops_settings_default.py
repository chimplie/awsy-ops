import os

import chops


HERE = os.path.abspath(os.path.dirname(__file__))
SETTINGS = dict()


# Specify project name here:
SETTINGS['project_name'] = 'chops' * 3

# Add project description:
SETTINGS['project_description'] = 'Chops Project'


# This path will be used as a project root:
SETTINGS['project_path'] = HERE

# This path will be used for all build stuff:
SETTINGS['build_path'] = os.path.join(HERE, '.build')

# This path will be used for logs:
SETTINGS['log_dir'] = os.path.join(HERE, '.logs')


SETTINGS['plugins'] = [
    'chops.plugins.dotenv',

    # Uncomment to use Docker plugin
    # 'chops.plugins.docker',

    # Uncomment to use Travis CI plugin
    # 'chops.plugins.travis',

    # Uncomment to use AWS plugin
    # 'chops.plugins.aws',

    # Uncomment to use AWS Environments plugin
    # 'chops.plugins.aws.aws_envs',

    # Uncomment to use AWS SSM plugin
    # 'chops.plugins.aws.aws_ssm',

    # Uncomment to use AWS Elastic Container Registry plugin
    # 'chops.plugins.aws.aws_ecr',

    # Uncomment to use AWS Elastic Beanstalk plugin
    # 'chops.plugins.aws.aws_ebt',
]


SETTINGS['dotenv'] = {
    'env_files': {
        'main_dotenv_path': os.path.join(SETTINGS['project_path'], '.env'),
    },
    'template': os.path.join(chops.utils.PLUGINS_PATH, 'dotenv', 'env.template'),
    'template_lock': os.path.join(SETTINGS['project_path'], 'env.template.lock'),
}

SETTINGS['docker'] = {
    'docker_root': os.path.join(SETTINGS['project_path'], 'docker'),
    'project_name': SETTINGS['project_name'],
}

SETTINGS['aws'] = {
    'profile': 'specify AWS profile here',
    'project_name': SETTINGS['project_name'],
}

SETTINGS['aws_ssm'] = {
    'namespace': '/{}'.format(SETTINGS['aws']['project_name']),
}

SETTINGS['aws_envs'] = {
    'environments': {
        'prod': {}
    },
    'default': 'prod',
}

SETTINGS['aws_ecr'] = {
    'services': [],
}

SETTINGS['aws_ebt'] = {
    'app_name': SETTINGS['aws']['project_name'],
}
