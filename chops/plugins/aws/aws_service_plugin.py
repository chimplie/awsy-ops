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
