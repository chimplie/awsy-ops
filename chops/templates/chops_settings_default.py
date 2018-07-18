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

    # Uncomment to use AWS S3 plugin
    # 'chops.plugins.aws.aws_s3',

    # Uncomment to use AWS Elastic Container Registry plugin
    # 'chops.plugins.aws.aws_ecr',

    # Uncomment to use AWS CloudWatch Logs plugin
    # 'chops.plugins.aws.aws_logs',

    # Uncomment to use AWS Elastic Compute Service plugin
    # 'chops.plugins.aws.aws_ec2',

    # Uncomment to use AWS Elastic Load Balancer plugin
    # 'chops.plugins.aws.aws_elb',

    # Uncomment to use AWS Elastic Container Service plugin
    # 'chops.plugins.aws.aws_ecs',

    # Uncomment to use AWS Elastic Beanstalk plugin
    # 'chops.plugins.aws.aws_ebt',

    # Uncomment to use local tasks
    # (we suggest to postpone initialization of this plugin as much as possible)
    'chops.plugins.local',
]


SETTINGS['dotenv'] = {
    'env_files': {
        'main_dotenv_path': os.path.join(SETTINGS['project_path'], '.env'),
    },
    'template': os.path.join(chops.utils.PLUGINS_PATH, 'dotenv', 'env.template'),
    'template_lock': os.path.join(SETTINGS['project_path'], 'env.template.lock'),
}

SETTINGS['local'] = {
    'module': 'chops_tasks'
}

SETTINGS['docker'] = {
    'docker_root': os.path.join(SETTINGS['project_path'], 'docker'),
    'project_name': SETTINGS['project_name'],
}

SETTINGS['aws'] = {
    'profile': 'specify AWS profile here',
    'project_name': SETTINGS['project_name'],
}

SETTINGS['aws_envs'] = {
    'environments': {
        'prod': {}
    },
    'default': 'prod',
}

SETTINGS['aws_ssm'] = {
    'namespace': '/{}'.format(SETTINGS['aws']['project_name']),
}

SETTINGS['aws_s3'] = {
    'namespace': SETTINGS['aws']['project_name'],
}

SETTINGS['aws_ecr'] = {
    'services': [],
}

SETTINGS['aws_logs'] = {
    'namespace': '/{}'.format(SETTINGS['aws']['project_name']),
}

SETTINGS['aws_ec2'] = {
    'vpc_name': SETTINGS['aws']['project_name'],
    'availability_zone_azs': [
        'a', 'b',
    ],
}

SETTINGS['aws_elb'] = {
    'namespace': SETTINGS['aws']['project_name'],
    'target_groups': {
        #
        # EXAMPLE: uncomment the following to create a group
        #          targeting port 80 of the `frontserver` container.
        #
        # 'Web': {
        #     'Port': 80,
        #     'Protocol': 'HTTP',
        # },
    },
}

SETTINGS['aws_ecs'] = {
    'namespace': SETTINGS['aws']['project_name'],
    'task_definitions': {},
    'services': {},
}

SETTINGS['aws_ebt'] = {
    'app_name': SETTINGS['aws']['project_name'],
}
