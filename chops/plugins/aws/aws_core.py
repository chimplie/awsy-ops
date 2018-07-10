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

    def get_credentials(self):
        """
        Returns current session credentials (e.g. AWS key ID, secret key et c.).
        :return: dict session credentials
        """
        return self.boto_session.get_credentials()


PLUGIN_CLASS = AwsPlugin
