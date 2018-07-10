import chops.core
from chops.plugins.aws.aws_core import AwsPlugin


class AwsServicePlugin(chops.core.Plugin):
    name = 'aws_service_plugin'
    dependencies = ['aws']
    service_name = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.aws_plugin: AwsPlugin = self.app.plugins['aws']
        self.client = self.aws_plugin.boto_session.client(self.service_name)

    def get_profile(self):
        return self.app.plugins['aws'].config['profile']

    def get_aws_region(self):
        return self.app.plugins['aws'].get_aws_region()

    def get_aws_project_name(self):
        return self.app.plugins['aws'].config['project_name']

    def get_credentials(self):
        return self.app.plugins['aws'].get_credentials()
