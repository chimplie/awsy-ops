import boto3

import chops.core


PLUGIN_NAME = 'aws'


class AwsPlugin(chops.core.Plugin):
    name = PLUGIN_NAME
    required_keys = ['profile', 'project_name']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.boto_session = boto3.Session(profile_name=self.config['profile'])


PLUGIN_CLASS = AwsPlugin
