import os


HERE = os.path.abspath(os.path.dirname(__file__))
SETTINGS = dict()


# Specify project name here:
SETTINGS['project_name'] = 'chopsexamplewebapp'

# Add project description:
SETTINGS['project_description'] = 'Example Chops web application'


# This path will be used as a project root:
SETTINGS['project_path'] = HERE

# This path will be used for all build stuff:
SETTINGS['build_path'] = os.path.join(HERE, '.build')

# This path will be used for logs:
SETTINGS['log_dir'] = os.path.join(HERE, '.logs')


SETTINGS['plugins'] = [
    'chops.plugins.dotenv',

    # Uncomment to use Docker plugin
    'chops.plugins.docker',

    # Uncomment to use Travis CI plugin
    'chops.plugins.travis',

    # Uncomment to use AWS plugin
    'chops.plugins.aws',

    # Uncomment to use AWS Environments plugin
    'chops.plugins.aws.aws_envs',

    # Uncomment to use AWS SSM plugin
    'chops.plugins.aws.aws_ssm',

    # Uncomment to use AWS Elastic Container Registry plugin
    'chops.plugins.aws.aws_ecr',

    # Uncomment to use AWS CloudWatch Logs plugin
    'chops.plugins.aws.aws_logs',

    # Uncomment to use AWS Elastic Compute Service plugin
    'chops.plugins.aws.aws_ec2',

    # Uncomment to use AWS Elastic Load Balancer plugin
    'chops.plugins.aws.aws_elb',

    # Uncomment to use AWS Elastic Container Service plugin
    'chops.plugins.aws.aws_ecs',

    # Uncomment to use AWS Elastic Beanstalk plugin
    'chops.plugins.aws.aws_ebt',
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
    'project_name': SETTINGS['project_name'],
}

SETTINGS['aws'] = {
    'profile': 'chops-example-web-app',
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
    'services': ['apiserver', 'webclient', 'frontserver'],
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
        'frontserver': {
            'Port': 80,
            'Protocol': 'HTTP',
        },
    },
}

SETTINGS['aws_ecs'] = {
    'cluster_prefix': '{}-'.format(SETTINGS['aws']['project_name']),
    'service_name': '{}-Web'.format(SETTINGS['aws']['project_name']),
    'task_definition_name': '{}-Web'.format(SETTINGS['aws']['project_name']),
    'service_config': {
        'healthCheckGracePeriodSeconds': 60,
    },
    'tasks_count': 1,
    'environments': {
        'prod': {
            'container_overrides': {
                'apiserver': {
                    'memory': 500,
                },
                'webclient': {
                    'memory': 300,
                },
                'frontserver': {
                    'memory': 200,
                }
            },
            'load_balancers': [
                {
                    'containerName': 'frontserver',
                    'containerPort': 8080,
                },
            ]
        },
    },
    'containers': [
        {
            'name': 'apiserver',
            'essential': True,
        },
        {
            'name': 'webclient',
            'essential': True,
        },
        {
            'name': 'frontserver',
            'portMappings': [
                {
                    'containerPort': 8080,
                    'hostPort': 80,
                    'protocol': 'tcp'
                },
            ],
            'links': [
                'webclient',
                'apiserver',
            ],
            'essential': True,
        },
    ],
}

SETTINGS['aws_ebt'] = {
    'app_name': SETTINGS['aws']['project_name'],
}
