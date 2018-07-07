from invoke import task

from chops.plugins.aws.aws_envs import AwsEnvsPluginMixin
from chops.plugins.aws.aws_service_plugin import AwsServicePlugin


class AwsLogsPlugin(AwsServicePlugin, AwsEnvsPluginMixin):
    name = 'aws_logs'
    dependencies = ['aws', 'aws_envs']
    service_name = 'logs'
    required_keys = ['namespace']

    def get_log_group_name(self, app_env=None):
        """
        Returns log group name for specified or current environment.
        :param app_env: str | None application environment
        :return: str log group name
        """
        return '{namespace}/{env_name}'.format(
            namespace=self.config['namespace'],
            env_name=app_env or self.get_current_env(),
        )

    def create_log_group(self, name):
        """
        Creates log group
        :param name: str log group name
        """
        response = self.client.create_log_group(
            logGroupName=name,
            tags={
                'chops-project': self.app.config['project_name'],
                'chops-aws-project': self.app.config['aws']['project_name'],
            }
        )
        assert response['ResponseMetadata']['HTTPStatusCode'] == 200

    def delete_log_group(self, name):
        """
        Deletes log group
        :param name: str log group name
        """
        response = self.client.delete_log_group(logGroupName=name)
        assert response['ResponseMetadata']['HTTPStatusCode'] == 200

    def get_tasks(self):
        @task(iterable=['env'])
        def create_group(ctx, env=None):
            """
            Creates log group for current or specified environment[s].
            Use --env=* for all environments
            """
            for app_env in self.envs_from_string(env):
                log_group_name = self.get_log_group_name(app_env)
                self.create_log_group(log_group_name)
                ctx.info('Log group "{}" successfully created.'.format(log_group_name))

        @task(iterable=['env'])
        def delete_group(ctx, env=None):
            """
            Delete log group for current or specified environment[s].
            Use --env=* for all environments
            """
            for app_env in self.envs_from_string(env):
                log_group_name = self.get_log_group_name(app_env)
                self.delete_log_group(log_group_name)
                ctx.info('Log group "{}" successfully deleted.'.format(log_group_name))

        return [create_group, delete_group]


class AwsLogsPluginMixin:
    def get_log_group_name(self):
        return self.app.plugins['aws_logs'].get_log_group_name()


PLUGIN_CLASS = AwsLogsPlugin
