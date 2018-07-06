import boto3

import chops.core


class AwsPlugin(chops.core.Plugin):
    name = 'aws'
    required_keys = ['profile', 'project_name']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.boto_session = boto3.Session(profile_name=self.config['profile'])

    def get_aws_region(self):
        """
        Returns AWS region
        :return: str AWS region
        """
        return self.boto_session.region_name


PLUGIN_CLASS = AwsPlugin
