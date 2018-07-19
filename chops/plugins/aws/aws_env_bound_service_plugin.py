from chops.plugins.aws.aws_service_plugin import AwsServicePlugin
from chops.plugins.aws.aws_envs import AwsEnvsPluginMixin


class AwsEnvBoundServicePlugin(AwsServicePlugin, AwsEnvsPluginMixin):
    """
    This plugin is designed to operate on the fixed environment.
    It overrides the config with the data picked from the '__environments__.<env_name>' key
    and leaves the original config under the '__config'.

    Use this to simplify the plugins which operates only on the current environment.
    """

    name = 'aws_env_bound_service_plugin'
    dependencies = ['aws', 'aws_envs']
    service_name = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__raw_config = self.config
        self.config = self.env_config(from_config=self.__raw_config)

