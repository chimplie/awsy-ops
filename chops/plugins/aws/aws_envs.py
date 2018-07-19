import os

import chops.core
from chops.plugins.aws.aws_core import AwsPlugin
from chops import utils


class AwsEnvsPlugin(chops.core.Plugin):
    name = 'aws_envs'
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


class AwsEnvsPluginMixin:
    def envs_from_string(self, value):
        return self.app.plugins['aws_envs'].envs_from_string(value)

    def get_current_env(self):
        return self.app.plugins['aws_envs'].current

    def env_config(self, app_env=None, from_config=None):
        app_env = app_env or self.get_current_env()
        from_config = from_config or self.config

        env_overrides = from_config.get('__environments__', {}).get(app_env, {})
        env_specific_config = utils.deep_merge(from_config, env_overrides)

        if '__environments__' in env_specific_config:
            del env_specific_config['__environments__']

        return env_specific_config


PLUGIN_CLASS = AwsEnvsPlugin
