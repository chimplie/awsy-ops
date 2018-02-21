import os

import chops.core
from chops.plugins.aws.aws_core import AwsPlugin


PLUGIN_NAME = 'aws_envs'


class AwsEnvsPlugin(chops.core.Plugin):
    name = PLUGIN_NAME
    dependencies = ['aws', 'dotenv']
    required_keys = ['environments', 'default']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.aws_plugin: AwsPlugin = self.app.plugins['aws']
        self.names = self.config['environments'].keys()
        self.current = os.getenv('APP_ENV', self.config['default'])

    def envs_from_string(self, env):
        environments = set()

        for e in env:
            if e == 'all' or e == '*':
                environments.update(set(self.names))
            else:
                environments.add(e)

        if not environments:
            environments.add(self.current)

        return environments


PLUGIN_CLASS = AwsEnvsPlugin
