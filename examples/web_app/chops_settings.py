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
    'chops.plugins.docker',
    'chops.plugins.aws',
    'chops.plugins.aws.aws_envs',
    'chops.plugins.aws.aws_ssm',
    'chops.plugins.aws.aws_ecr',
    'chops.plugins.aws.aws_ecs',
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

SETTINGS['aws_ecs'] = {
    'service_name': 'Web',
    'containers': [
        {
            'name': 'apiserver',
            'image': '899190935332.dkr.ecr.us-east-1.amazonaws.com/chopsexamplewebapp/apiserver:latest',
            'memory': 500,
            'essential': True,
        },
        {
            'name': 'webclient',
            'image': '899190935332.dkr.ecr.us-east-1.amazonaws.com/chopsexamplewebapp/webclient:latest',
            'memory': 300,
            'essential': True,
        },
        {
            'name': 'frontserver',
            'image': '899190935332.dkr.ecr.us-east-1.amazonaws.com/chopsexamplewebapp/frontserver:latest',
            'memory': 200,
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
            'logConfiguration': {
                'logDriver': 'awslogs',
                'options': {
                    'awslogs-group': 'chopsexamplewebapp-prod',
                    'awslogs-region': 'us-east-1',
                    'awslogs-stream-prefix': 'awslogs-local',
                }
            },
        },
    ],
}

SETTINGS['aws_ebt'] = {
    'app_name': SETTINGS['aws']['project_name'],
}
