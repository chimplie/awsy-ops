import hashlib

from botocore.exceptions import ClientError
from invoke import task

from chops.plugins.aws.aws_ec2 import AwsEc2PluginMixin
from chops.plugins.aws.aws_envs import AwsEnvsPluginMixin
from chops.plugins.aws.aws_service_plugin import AwsServicePlugin


class AwsElbPlugin(AwsServicePlugin, AwsEnvsPluginMixin, AwsEc2PluginMixin):
    name = 'aws_elb'
    dependencies = ['aws', 'aws_envs', 'aws_ec2']
    service_name = 'elbv2'
    required_keys = ['namespace', 'target_groups']

    def get_balancer_name(self, env=None):
        """
        Returns load balancer name for the specified or current environment.
        :param env: str | None environment name, None for the current environment
        :return: str balancer name
        """
        return '{}-{}'.format(
            self.config['namespace'],
            env or self.get_current_env(),
        )

    def get_target_group_fully_qualified_name(self, short_name, env=None):
        """
        Returns the fully qualified name of the target group for the specified environment.
        :param short_name: str short name of the target group
        :param env: str | None environment name, None for the current environment
        :return: str full name of the target group
        """
        return '{}-{}'.format(
            self.get_balancer_name(env),
            short_name,
        )

    def get_target_group_name(self, short_name, env=None):
        """
        Returns the unique name of the target group for the specified environment.
        The difference between this function and `get_target_group_fully_qualified_name`
        is that fits the name into 32 characters.
        :param short_name: str short name of the target group
        :param env: str | None environment name, None for the current environment
        :return: str full name of the target group
        """
        env = env or self.get_current_env()
        full_name = self.get_target_group_fully_qualified_name(short_name, env=env)
        namespace = self.config['namespace']

        if len(full_name) <= 32:
            return full_name
        elif len(namespace) + 10 <= 32:
            env_target_hash = hashlib.md5((short_name + env).encode()).hexdigest()[:9]
            return '{}-{}'.format(namespace, env_target_hash)
        else:
            return hashlib.md5(full_name.encode()).hexdigest()

    def get_target_groups_config(self):
        """
        Returns target groups configuration.
        :return: dict target groups config
        """
        return self.config['target_groups']

    def get_balancer_info(self, env=None):
        """
        Returns load balancer details for the specified environment.
        :param env: str | None environment name, None for the current environment
        :return: dict balancer details
        """
        try:
            response = self.client.describe_load_balancers(
                Names=[self.get_balancer_name(env)],
            )
            assert response['ResponseMetadata']['HTTPStatusCode'] == 200

            vpc_id = self.get_vpc_id()
            balancers = [balancer for balancer in response['LoadBalancers'] if balancer['VpcId'] == vpc_id]

            return balancers[0]
        except ClientError:
            self.logger.debug('Unable to find load balancer {}.'.format(self.get_balancer_name(env)))
            return None

    def balancer_exists(self, env=None):
        """
        Returns whether load balancer exists in the specified environment.
        :param env: str | None environment name, None for the current environment
        :return: bool whether balancer exists or not
        """
        return self.get_balancer_info(env) is not None

    def get_balancer_arn(self, env=None):
        """
        Returns load balancer ARN for the specified environment.
        :param env: str | None environment name, None for the current environment
        :return: str balancer ARN
        """
        return self.get_balancer_info(env)['LoadBalancerArn']

    def get_target_group_info(self, short_name, env=None):
        """
        Returns specified target group details for the selected environment (None for the current one).
        :param short_name: str target group short name
        :param env: str | None environment name, None for the current environment
        :return: dict target group details
        """
        try:
            response = self.client.describe_target_groups(
                Names=[self.get_target_group_name(short_name, env=env)],
            )
            assert response['ResponseMetadata']['HTTPStatusCode'] == 200

            return response['TargetGroups'][0]
        except ClientError:
            self.logger.debug('Unable to find load balancer {balancer} target group {group}.'.format(
                balancer=self.get_balancer_name(env),
                group=self.get_target_group_name(short_name, env=env)
            ))
            return None

    def get_target_groups_info(self, env=None):
        """
        Returns all target groups details for the selected environment (None for the current one).
        :param env: str | None environment name, None for the current environment
        :return: dict[] target groups details
        """
        env = env or self.get_current_env()
        target_groups_config = self.get_target_groups_config()
        groups_info = {}

        for short_name in target_groups_config.keys():
            target_group_name = self.get_target_group_name(short_name, env=env)
            data = self.get_target_group_info(short_name, env=env)
            if data is not None:
                groups_info[target_group_name] = data

        return groups_info

    def target_group_exists(self, short_name, env=None):
        """
        Returns whether target group exists in the environment.
        :param short_name: str target group short name
        :param env: str | None environment name, None for the current environment
        :return: bool whether target group exists
        """
        return self.get_target_group_info(short_name, env=env) is not None

    def get_target_group_arn(self, short_name, env=None):
        """
        Returns target group ARN for the specified environment (None for the current one).
        :param short_name: str target group short name
        :param env: str | None environment name, None for the current environment
        :return: str target group ARN
        """
        target_group_info = self.get_target_group_info(short_name, env=env)
        return target_group_info['TargetGroupArn']

    def create_balancer(self, env=None):
        """
        Creates load balancer in the specified environment (None for the current one).
        :param env: str | None environment name, None for the current environment
        :return: dict balancer info
        """
        env = env or self.get_current_env()

        balancer_name = self.get_balancer_name(env)
        subnet_ids = self.get_subnet_ids()

        response = self.client.create_load_balancer(
            Name=balancer_name,
            Subnets=subnet_ids,
            SecurityGroups=[self.get_security_group_id()],
            Scheme='internet-facing',
            Tags=[
                {
                    'Key': 'chops-aws-project',
                    'Value': self.get_aws_project_name(),
                },
                {
                    'Key': 'environment',
                    'Value': env,
                },
            ],
            Type='application',
            IpAddressType='ipv4',
        )
        assert response['ResponseMetadata']['HTTPStatusCode'] == 200

        return response['LoadBalancers'][0]

    def delete_balancer(self, env=None):
        """
        Deletes load balancer in the specified environment (None for the current one).
        :param env: str | None environment name, None for the current environment
        """
        env = env or self.get_current_env()
        response = self.client.delete_load_balancer(
            LoadBalancerArn=self.get_balancer_arn(env)
        )
        assert response['ResponseMetadata']['HTTPStatusCode'] == 200

    def create_target_groups(self, env=None):
        """
        Creates target groups for the specified environment (None for the current one).
        :param env: str | None environment name, None for the current environment
        :return: dict created target groups details
        """
        env = env or self.get_current_env()
        target_groups_config = self.get_target_groups_config()
        vpc_id = self.get_vpc_id()
        response_data = {}

        for short_name in target_groups_config.keys():
            target_group_name = self.get_target_group_name(short_name, env=env)

            if self.target_group_exists(short_name, env=env):
                self.logger.info('Target group {} exists, skipping creation.'.format(target_group_name))
                continue

            response = self.client.create_target_group(
                Name=target_group_name,
                VpcId=vpc_id,
                **target_groups_config[short_name],
            )
            assert response['ResponseMetadata']['HTTPStatusCode'] == 200

            self.logger.info('Target group {} created.'.format(target_group_name))
            response_data[target_group_name] = response['TargetGroups']

        return response_data

    def delete_target_groups(self, env=None):
        """
        Deletes target groups for the specified environment (None for the current one).
        :param env: str | None environment name, None for the current environment
        """
        env = env or self.get_current_env()
        target_groups_config = self.get_target_groups_config()

        for short_name in target_groups_config.keys():
            if not self.target_group_exists(short_name, env=env):
                self.logger.info('Target group {} does not exists, nothing to delete.'.format(
                    self.get_target_group_name(short_name, env=env)
                ))
                continue

            response = self.client.delete_target_group(
                TargetGroupArn=self.get_target_group_arn(short_name, env=env)
            )
            assert response['ResponseMetadata']['HTTPStatusCode'] == 200
            self.logger.info('Target group {} deleted.'.format(self.get_target_group_name(short_name, env=env)))

    def create_listeners(self, env=None):
        """
        Creates listeners for the default balancer of the specified environment (None for the current one).
        :param env: str | None environment name, None for the current environment
        :return: dict created listeners details
        """
        env = env or self.get_current_env()
        target_groups_config = self.get_target_groups_config()
        balancer_arn = self.get_balancer_arn(env)
        response_data = {}

        for short_name in target_groups_config.keys():
            target_group_name = self.get_target_group_name(short_name, env=env)

            response = self.client.create_listener(
                LoadBalancerArn=balancer_arn,
                DefaultActions=[
                    {
                        'Type': 'forward',
                        'TargetGroupArn': self.get_target_group_arn(short_name, env=env)
                    }
                ],
                **target_groups_config[short_name],
            )
            assert response['ResponseMetadata']['HTTPStatusCode'] == 200

            self.logger.info('Target group {group} bound to {balancer} load balancer.'.format(
                group=target_group_name,
                balancer=self.get_balancer_name(env),
            ))
            response_data[target_group_name] = response['Listeners']

        return response_data

    def describe_listeners(self, env=None):
        """
        Describes listeners for the default balancer of the specified environment (None for the current one).
        :param env: str | None environment name, None for the current environment
        :return: dict created listeners details
        """
        env = env or self.get_current_env()
        balancer_arn = self.get_balancer_arn(env)

        response = self.client.describe_listeners(
            LoadBalancerArn=balancer_arn,
        )
        assert response['ResponseMetadata']['HTTPStatusCode'] == 200

        return response['Listeners']

    def delete_listeners(self, env=None):
        """
        Deletes listeners for the default balancer of the specified environment (None for the current one).
        :param env: str | None environment name, None for the current environment
        """
        listeners_info = self.describe_listeners(env)

        for listener in listeners_info:
            response = self.client.delete_listener(
                ListenerArn=listener['ListenerArn']
            )
            assert response['ResponseMetadata']['HTTPStatusCode'] == 200

            self.logger.info('Successfully deleted listener {listener_arn} for balancer {balancer}.'.format(
                listener_arn=listener['ListenerArn'],
                balancer=self.get_balancer_name(env),
            ))

    def get_tasks(self):
        @task(iterable=['env'])
        def create_balancer(ctx, env=None):
            """
            Creates balancer for current or specified environment[s].
            Use --env=* for all environments
            """
            for app_env in self.envs_from_string(env):
                if not self.balancer_exists(app_env):
                    data = self.create_balancer(app_env)
                    ctx.info('Successfully created load balancer {}:'.format(self.get_balancer_name(app_env)))
                    ctx.pp.pprint(data)
                else:
                    ctx.info('Load balancer {} already exists, nothing to create.'.format(
                        self.get_balancer_name(app_env)
                    ))

        @task(iterable=['env'])
        def delete_balancer(ctx, env=None):
            """
            Deletes balancer for current or specified environment[s].
            Use --env=* for all environments
            """
            for app_env in self.envs_from_string(env):
                if self.balancer_exists(app_env):
                    self.delete_balancer(app_env)
                    ctx.info('Successfully deleted load balancer {}:'.format(self.get_balancer_name(app_env)))
                else:
                    ctx.info('Load balancer {} does not exist, nothing to delete.'.format(
                        self.get_balancer_name(app_env)
                    ))

        @task(iterable=['env'])
        def describe_balancer(ctx, env=None):
            """
            Describes balancer for current or specified environment[s].
            Use --env=* for all environments
            """
            for app_env in self.envs_from_string(env):
                data = self.get_balancer_info(app_env)
                if data is not None:
                    ctx.info('Load balancer {} details:'.format(self.get_balancer_name(app_env)))
                    ctx.pp.pprint(data)
                else:
                    ctx.info('Load balancer {} does not exist.'.format(self.get_balancer_name(app_env)))

        @task(iterable=['env'])
        def create_target_groups(ctx, env=None):
            """
            Creates load balancer target groups for current or specified environment[s].
            Use --env=* for all environments
            """
            for app_env in self.envs_from_string(env):
                data = self.create_target_groups(app_env)
                ctx.info('Created target groups for the load balancer {}:'.format(self.get_balancer_name(app_env)))
                ctx.pp.pprint(data)

        @task(iterable=['env'])
        def delete_target_groups(ctx, env=None):
            """
            Creates load balancer target groups for current or specified environment[s].
            Use --env=* for all environments
            """
            for app_env in self.envs_from_string(env):
                self.delete_target_groups(app_env)
                ctx.info('Deleted target groups for the load balancer {}:'.format(self.get_balancer_name(app_env)))

        @task(iterable=['env'])
        def describe_target_groups(ctx, env=None):
            """
            Describes target groups for current or specified environment[s].
            Use --env=* for all environments
            """
            for app_env in self.envs_from_string(env):
                data = self.get_target_groups_info(app_env)
                ctx.info('Target groups details for load balancer {}:'.format(self.get_balancer_name(app_env)))
                ctx.pp.pprint(data)

        @task(iterable=['env'])
        def create_listeners(ctx, env=None):
            """
            Creates listeners between load balancer and target groups for current or specified environment[s].
            Use --env=* for all environments
            """
            for app_env in self.envs_from_string(env):
                data = self.create_listeners(app_env)
                ctx.info('Created listeners for load balancer {}:'.format(
                    self.get_balancer_name(app_env)
                ))
                ctx.pp.pprint(data)

        @task(iterable=['env'])
        def delete_listeners(ctx, env=None):
            """
            Deletes listeners for current or specified environment[s].
            Use --env=* for all environments
            """
            for app_env in self.envs_from_string(env):
                if self.balancer_exists(app_env):
                    self.delete_listeners(app_env)
                    ctx.info('Deleted all listeners for load balancer {}:'.format(self.get_balancer_name(app_env)))
                else:
                    ctx.info('Load balancer {} does not exist, no listeners to remove.'.format(self.get_balancer_name(app_env)))

        @task(iterable=['env'])
        def describe_listeners(ctx, env=None):
            """
            Describes listeners for current or specified environment[s].
            Use --env=* for all environments
            """
            for app_env in self.envs_from_string(env):
                data = self.describe_listeners(app_env)
                ctx.info('Listeners details for load balancer {}:'.format(self.get_balancer_name(app_env)))
                ctx.pp.pprint(data)

        @task(iterable=['env'])
        def create(ctx, env=None):
            """Creates fully operational load balancer setup for the current environment."""
            create_target_groups(ctx, env)
            create_balancer(ctx, env)
            create_listeners(ctx, env)

            ctx.info('Load balancer {} setup completed.')

        @task(iterable=['env'])
        def delete(ctx, env=None):
            """Deletes load balancer for current environment and all related resources."""
            delete_listeners(ctx, env)
            delete_balancer(ctx, env)
            delete_target_groups(ctx, env)

            ctx.info('Load balancers deletion completed.')

        @task(iterable=['env'])
        def reset(ctx, env=None):
            """Resets load balancer setup for the current environment."""
            delete(ctx, env)
            create(ctx, env)

            ctx.info('Load balancers reset completed.')

        return [
            create_balancer, delete_balancer, describe_balancer,
            create_target_groups, delete_target_groups, describe_target_groups,
            create_listeners, delete_listeners, describe_listeners,
            create, delete, reset,
        ]


class AwsElbPluginMixin:
    def get_balancer_arn(self, env=None):
        return self.app.plugins['aws_elb'].get_balancer_arn(env)

    def get_target_group_arn(self, short_name, env=None):
        return self.app.plugins['aws_elb'].get_target_group_arn(short_name, env=env)


PLUGIN_CLASS = AwsElbPlugin
