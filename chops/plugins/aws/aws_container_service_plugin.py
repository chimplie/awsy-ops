from chops.plugins.aws.aws_service_plugin import AwsServicePlugin


class AwsContainerServicePlugin(AwsServicePlugin):
    name = 'aws_container_service_plugin'
    dependencies = ['aws']
    service_name = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def get_service_path(self, service_name):
        return '{project_name}/{service_name}'.format(
            project_name=self.get_aws_project_name(),
            service_name=service_name,
        )
