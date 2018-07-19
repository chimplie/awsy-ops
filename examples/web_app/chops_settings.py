import os


HERE = os.path.abspath(os.path.dirname(__file__))
SETTINGS = dict()


# Specify project name here:
SETTINGS['project_name'] = 'chopsexamplewebapp'

# Add project description:
SETTINGS['project_description'] = 'Example Chops web application'


# This path will be used as a project root:
SETTINGS['project_path'] = HERE

# You can list here paths from which plugins can be loaded in addition to the project path
SETTINGS['plugin_paths'] = []

# This path will be used for all build stuff:
SETTINGS['build_path'] = os.path.join(HERE, '.build')

# This path will be used for logs:
SETTINGS['log_dir'] = os.path.join(HERE, '.logs')


SETTINGS['plugins'] = [
    'chops.plugins.dotenv',

    # Uncomment to use Docker plugin
    'chops.plugins.docker',

    # Uncomment to use Travis CI plugin
    # 'chops.plugins.travis',

    # Uncomment to use AWS plugin
    'chops.plugins.aws',

    # Uncomment to use AWS Environments plugin
    'chops.plugins.aws.aws_envs',

    # Uncomment to use AWS SSM plugin
    'chops.plugins.aws.aws_ssm',

    # Uncomment to use AWS S3 plugin
    'chops.plugins.aws.aws_s3',

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

    # Uncomment to use AWS Application Auto Scaling Service plugin
    'chops.plugins.aws.aws_app_scale',

    # Uncomment to use AWS EC2 Auto Scaling Service plugin
    'chops.plugins.aws.aws_ec2_scale',

    # Uncomment to use AWS Elastic Beanstalk plugin
    'chops.plugins.aws.aws_ebt',

    # ----------------------------
    # Put your local plugins here
    # ----------------------------

    # Uncomment to use local tasks
    # (we suggest to postpone initialization of this plugin as much as possible)
    'chops.plugins.local',
]


SETTINGS['dotenv'] = {
    'env_files': {
        'main_dotenv_path': os.path.join(SETTINGS['project_path'], 'docker', '.env'),
    },
    'template': os.path.join(SETTINGS['project_path'], 'env.template'),
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
    'profile': 'chops-example-web-app',
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
        'Web': {
            'Port': 80,
            'Protocol': 'HTTP',
        },
    },
}

SETTINGS['aws_ecs'] = {
    'namespace': SETTINGS['aws']['project_name'],
    'task_definitions': {
        'Web': {
            'environments': {
                'prod': {
                    'container_overrides': {
                        'apiserver': {
                            'memory': 250,
                        },
                        'webclient': {
                            'memory': 100,
                        },
                        'frontserver': {
                            'memory': 100,
                        }
                    },
                },
            },
            'containers': [
                {
                    'name': 'apiserver',
                    '__image__': 'apiserver',
                    'essential': True,
                    '__requires_aws_env_setup__': True,
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
            'volumes': [],
        },
    },
    'services': {
        'Web': {
            'task_definition': 'Web',
            'environments': {
                'prod': {
                    'tasks_count': 1,
                    'load_balancers': [
                        {
                            '__target_group__': 'Web',
                            'containerName': 'frontserver',
                            'containerPort': 8080,
                        },
                    ]
                },
            },
            'config': {
                'healthCheckGracePeriodSeconds': 60,
            },
            'tasks_count': 1,
        }
    },
}

SETTINGS['aws_app_scale'] = {
    'environments': {
        'prod': {
            'Web': {
                'target': {
                    'MinCapacity': 1,
                    'MaxCapacity': 2,
                },
            },
        },
    },
    'services': {
        'Web': {
            'target': {
                'MinCapacity': 1,
                'MaxCapacity': 1,
            },
            'policies': {
                'CPU': {
                    'PolicyType': 'TargetTrackingScaling',
                    'TargetTrackingScalingPolicyConfiguration': {
                        'TargetValue': 70,
                        'PredefinedMetricSpecification': {
                            'PredefinedMetricType': 'ECSServiceAverageCPUUtilization'
                        },
                        'ScaleOutCooldown': 300,
                        'ScaleInCooldown': 300,
                    },
                },
                'RAM': {
                    'PolicyType': 'TargetTrackingScaling',
                    'TargetTrackingScalingPolicyConfiguration': {
                        'TargetValue': 70,
                        'PredefinedMetricSpecification': {
                            'PredefinedMetricType': 'ECSServiceAverageMemoryUtilization'
                        },
                        'ScaleOutCooldown': 300,
                        'ScaleInCooldown': 300,
                    },
                },
            },
        },
    },
}

SETTINGS['aws_ec2_scale'] = {
    'policies': {
        'CPU': {
            'PolicyType': 'TargetTrackingScaling',
            'TargetTrackingConfiguration': {
                'PredefinedMetricSpecification': {
                    'PredefinedMetricType': 'ASGAverageCPUUtilization',
                },
                'TargetValue': 70,
            }
        }
    },
    'environments': {
        'prod': {
            'MinSize': 1,
            'MaxSize': 2,
            'DesiredCapacity': 2,
        }
    }
}

SETTINGS['aws_ebt'] = {
    'app_name': SETTINGS['aws']['project_name'],
}
