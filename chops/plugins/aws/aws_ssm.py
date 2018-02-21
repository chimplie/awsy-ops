from invoke import task

from chops.plugins.aws.aws_service_plugin import AwsServicePlugin


PLUGIN_NAME = 'aws_ssm'


class AwsSsmPlugin(AwsServicePlugin):
    name = PLUGIN_NAME
    dependencies = ['aws', 'aws_envs']
    service_name = 'ssm'
    required_keys = ['namespace']

    def envs_from_string(self, value):
        return self.app.plugins['aws_envs'].envs_from_string(value)

    def get_path_for_env(self, env_name):
        return '{namespace}/{env_name}/'.format(
            namespace=self.config['namespace'],
            env_name=env_name
        )

    def get_tasks(self):
        @task(iterable=['env'], name='list')
        def list_parameters(ctx, decrypt=True, env=None):
            """
            Retrieves all AWS SSM parameters for the current (or specified) environment[s].
            Use --env=* to show all environments
            """
            for app_env in self.envs_from_string(env):
                ctx.info('AWS SSM parameters for environment "{app_env}":'.format(app_env=app_env))
                ctx.pp.pprint(self.client.get_parameters_by_path(
                    Path=self.get_path_for_env(app_env),
                    WithDecryption=decrypt
                ).get('Parameters', {}))

        @task(iterable=['env'])
        def get(ctx, name, decrypt=True, env=None):
            """Retrieves AWS SSM parameter by name for the current (or specified) environment[s]."""
            for app_env in self.envs_from_string(env):
                path = '{path}{name}'.format(path=self.get_path_for_env(app_env), name=name)

                ctx.info('AWS SSM parameter "{path}".'.format(path=path))
                ctx.pp.pprint(self.client.get_parameter(
                    Name=path,
                    WithDecryption=decrypt
                ).get('Parameter', {}))

        @task
        def get_by_path(ctx, path, decrypt=True):
            """Retrieves AWS SSM parameters by path."""
            ctx.info('AWS SSM parameters by path="{path}".'.format(path=path))
            ctx.pp.pprint(ctx.boto()['ssm'].get_parameters_by_path(
                Path=path,
                WithDecryption=decrypt
            ).get('Parameters', {}))

        @task(iterable=['env'])
        def put(ctx, name, value, param_type='String', description=None, env=None):
            """Puts AWS SSM parameter for the current (or specified) environment[s]."""
            for app_env in self.envs_from_string(env):
                path = '{path}{name}'.format(path=self.get_path_for_env(app_env), name=name)

                try:
                    param = self.client.get_parameter(
                        Name=path,
                        WithDecryption=True
                    ).get('Parameter')

                    param_type = param['Type']
                except:
                    if description is None:
                        description = 'UBI Access parameter {name} for "{app_env}" environment'.format(
                            name=name, app_env=app_env
                        )

                opts = {
                    'Name': path,
                    'Value': value,
                    'Overwrite': True,
                    'Type': param_type
                }

                if description is not None:
                    opts['Description'] = description

                ctx.info('Set AWS SSM parameter "{path}"="{value}" of type "{param_type}".'.format(
                    path=path, value=value, param_type=param_type
                ))
                ctx.pp.pprint(self.client.put_parameter(**opts))

        @task(iterable=['env'])
        def delete(ctx, name, env=None):
            """Deletes AWS SSM parameter by name for the current (or specified) environment[s]."""
            for app_env in self.envs_from_string(env):
                path = '{path}{name}'.format(path=self.get_path_for_env(app_env), name=name)
                ctx.info('AWS SSM parameter by name="{path}".'.format(path=path))
                ctx.pp.pprint(self.client.delete_parameter(Name=path))

        return [list_parameters, get, get_by_path, put, delete]


PLUGIN_CLASS = AwsSsmPlugin
