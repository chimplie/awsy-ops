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
    required_keys = ['namespace', 'target_groups', 'security_group']

    def get_balancer_name(self):
        """
        Returns load balancer name for the current environment.
        :return: str balancer name
        """
        return '{}-{}'.format(
            self.config['namespace'],
            self.get_current_env(),
        )

    def get_security_group_short_name(self):
        """
        Returns load balancer security group short name.
        :return: str security group short name.
        """
        return self.config['security_group']

    def get_target_group_fully_qualified_name(self, short_name):
        """
        Returns the fully qualified name of the target group for the current environment.
        :param short_name: str short name of the target group
        :return: str full name of the target group
        """
        return '{}-{}'.format(
            self.get_balancer_name(),
            short_name,
        )

    def get_target_group_name(self, short_name):
        """
        Returns the unique name of the target group for the current environment.
        The difference between this function and `get_target_group_fully_qualified_name`
        is that fits the name into 32 characters.
        :param short_name: str short name of the target group
        :return: str full name of the target group
        """
        app_env = self.get_current_env()
        full_name = self.get_target_group_fully_qualified_name(short_name)
        namespace = self.config['namespace']

        if len(full_name) <= 32:
            return full_name
        elif len(namespace) + 10 <= 32:
            env_target_hash = hashlib.md5((short_name + app_env).encode()).hexdigest()[:9]
            return '{}-{}'.format(namespace, env_target_hash)
        else:
            return hashlib.md5(full_name.encode()).hexdigest()

    def get_target_groups_config(self):
        """
        Returns target groups configuration.
        :return: dict target groups config
        """
        return self.config['target_groups']

    def get_balancer_info(self):
        """
        Returns load balancer details for the current environment.
        :return: dict balancer details
        """
        try:
            response = self.client.describe_load_balancers(
                Names=[self.get_balancer_name()],
            )
            assert response['ResponseMetadata']['HTTPStatusCode'] == 200

            vpc_id = self.get_vpc_id()
            balancers = [balancer for balancer in response['LoadBalancers'] if balancer['VpcId'] == vpc_id]

            return balancers[0]
        except ClientError:
            self.logger.debug('Unable to find load balancer {}.'.format(self.get_balancer_name()))
            return None

    def balancer_exists(self):
        """
        Returns whether load balancer exists in the current environment.
        :return: bool whether balancer exists or not
        """
        return self.get_balancer_info() is not None

    def get_balancer_arn(self):
        """
        Returns load balancer ARN for the current environment.
        :return: str balancer ARN
        """
        return self.get_balancer_info()['LoadBalancerArn']

    def get_balancer_dns(self):
        """
        Returns load balancer DNS name for the current environment.
        :return: str balancer DNS name
        """
        return self.get_balancer_info()['DNSName']

    def get_target_group_info(self, short_name):
        """
        Returns specified target group details for the current environment.
        :param short_name: str target group short name
        :return: dict target group details
        """
        try:
            response = self.client.describe_target_groups(
                Names=[self.get_target_group_name(short_name)],
            )
            assert response['ResponseMetadata']['HTTPStatusCode'] == 200

            return response['TargetGroups'][0]
        except ClientError:
            self.logger.debug('Unable to find load balancer {balancer} target group {group}.'.format(
                balancer=self.get_balancer_name(),
                group=self.get_target_group_name(short_name)
            ))
            return None

    def get_target_groups_info(self):
        """
        Returns all target groups details for the current environment.
        :return: dict[] target groups details
        """
        target_groups_config = self.get_target_groups_config()
        groups_info = {}

        for short_name in target_groups_config.keys():
            target_group_name = self.get_target_group_name(short_name)
            data = self.get_target_group_info(short_name)
            if data is not None:
                groups_info[target_group_name] = data

        return groups_info

    def target_group_exists(self, short_name):
        """
        Returns whether target group exists in the current environment.
        :param short_name: str target group short name
        :return: bool whether target group exists
        """
        return self.get_target_group_info(short_name) is not None

    def get_target_group_arn(self, short_name):
        """
        Returns target group ARN for the current environment.
        :param short_name: str target group short name
        :return: str target group ARN
        """
        target_group_info = self.get_target_group_info(short_name)
        return target_group_info['TargetGroupArn']

    def create_balancer(self):
        """
        Creates load balancer in the current environment.
        :return: dict balancer info
        """
        app_env = self.get_current_env()
        balancer_name = self.get_balancer_name()
        subnet_ids = self.get_subnet_ids()

        response = self.client.create_load_balancer(
            Name=balancer_name,
            Subnets=subnet_ids,
            SecurityGroups=[self.get_security_group_id(self.get_security_group_short_name())],
            Scheme='internet-facing',
            Tags=[
                {
                    'Key': 'chops-aws-project',
                    'Value': self.get_aws_project_name(),
                },
                {
                    'Key': 'environment',
                    'Value': app_env,
                },
            ],
            Type='application',
            IpAddressType='ipv4',
        )
        assert response['ResponseMetadata']['HTTPStatusCode'] == 200

        return response['LoadBalancers'][0]

    def delete_balancer(self):
        """
        Deletes load balancer in the current environment.
        """
        response = self.client.delete_load_balancer(
            LoadBalancerArn=self.get_balancer_arn()
        )
        assert response['ResponseMetadata']['HTTPStatusCode'] == 200

    def create_target_groups(self):
        """
        Creates target groups for the current environment.
        :return: dict created target groups details
        """
        target_groups_config = self.get_target_groups_config()
        vpc_id = self.get_vpc_id()
        response_data = {}

        for short_name in target_groups_config.keys():
            target_group_name = self.get_target_group_name(short_name)

            if self.target_group_exists(short_name):
                self.logger.info(f'Target group {target_group_name} exists, skipping creation.')
                continue

            response = self.client.create_target_group(
                Name=target_group_name,
                VpcId=vpc_id,
                **target_groups_config[short_name],
            )
            assert response['ResponseMetadata']['HTTPStatusCode'] == 200

            self.logger.info(f'Target group {target_group_name} created.')
            response_data[target_group_name] = response['TargetGroups']

        return response_data

    def delete_target_groups(self):
        """
        Deletes target groups for the current environment.
        """
        target_groups_config = self.get_target_groups_config()

        for short_name in target_groups_config.keys():
            if not self.target_group_exists(short_name):
                self.logger.info('Target group {} does not exists, nothing to delete.'.format(
                    self.get_target_group_name(short_name)
                ))
                continue

            response = self.client.delete_target_group(
                TargetGroupArn=self.get_target_group_arn(short_name)
            )
            assert response['ResponseMetadata']['HTTPStatusCode'] == 200
            self.logger.info('Target group {} deleted.'.format(self.get_target_group_name(short_name)))

    def create_listeners(self):
        """
        Creates listeners for the default balancer of the current environment.
        :return: dict created listeners details
        """
        target_groups_config = self.get_target_groups_config()
        balancer_arn = self.get_balancer_arn()
        response_data = {}

        for short_name in target_groups_config.keys():
            target_group_name = self.get_target_group_name(short_name)

            response = self.client.create_listener(
                LoadBalancerArn=balancer_arn,
                DefaultActions=[
                    {
                        'Type': 'forward',
                        'TargetGroupArn': self.get_target_group_arn(short_name)
                    }
                ],
                **target_groups_config[short_name],
            )
            assert response['ResponseMetadata']['HTTPStatusCode'] == 200

            self.logger.info('Target group {group} bound to {balancer} load balancer.'.format(
                group=target_group_name,
                balancer=self.get_balancer_name(),
            ))
            response_data[target_group_name] = response['Listeners']

        return response_data

    def describe_listeners(self):
        """
        Describes listeners for the default balancer of the current environment.
        :return: dict created listeners details
        """
        balancer_arn = self.get_balancer_arn()

        response = self.client.describe_listeners(
            LoadBalancerArn=balancer_arn,
        )
        assert response['ResponseMetadata']['HTTPStatusCode'] == 200

        return response['Listeners']

    def delete_listeners(self):
        """
        Deletes listeners for the default balancer of the current environment.
        """
        listeners_info = self.describe_listeners()

        for listener in listeners_info:
            response = self.client.delete_listener(
                ListenerArn=listener['ListenerArn']
            )
            assert response['ResponseMetadata']['HTTPStatusCode'] == 200

            self.logger.info('Successfully deleted listener {listener_arn} for balancer {balancer}.'.format(
                listener_arn=listener['ListenerArn'],
                balancer=self.get_balancer_name(),
            ))

    def get_tasks(self):
        @task
        def create_balancer(ctx):
            """
            Creates balancer for current environment.
            """
            if not self.balancer_exists():
                data = self.create_balancer()
                ctx.info('Successfully created load balancer {}:'.format(self.get_balancer_name()))
                ctx.pp.pprint(data)
            else:
                ctx.info('Load balancer {} already exists, nothing to create.'.format(
                    self.get_balancer_name()
                ))

        @task
        def delete_balancer(ctx):
            """
            Deletes balancer for current environment.
            """
            if self.balancer_exists():
                self.delete_balancer()
                ctx.info('Successfully deleted load balancer {}:'.format(self.get_balancer_name()))
            else:
                ctx.info('Load balancer {} does not exist, nothing to delete.'.format(
                    self.get_balancer_name()
                    ))

        @task
        def describe_balancer(ctx):
            """
            Describes balancer for current environment.
            """
            data = self.get_balancer_info()
            if data is not None:
                ctx.info('Load balancer {} details:'.format(self.get_balancer_name()))
                ctx.pp.pprint(data)
            else:
                ctx.info('Load balancer {} does not exist.'.format(self.get_balancer_name()))

        @task
        def create_target_groups(ctx):
            """
            Creates load balancer target groups for current environment.
            """
            data = self.create_target_groups()
            ctx.info('Created target groups for the load balancer {}:'.format(self.get_balancer_name()))
            ctx.pp.pprint(data)

        @task
        def delete_target_groups(ctx):
            """
            Creates load balancer target groups for current environment.
            """
            self.delete_target_groups()
            ctx.info('Deleted target groups for the load balancer {}:'.format(self.get_balancer_name()))

        @task
        def describe_target_groups(ctx):
            """
            Describes target groups for current environment.
            """
            data = self.get_target_groups_info()
            ctx.info('Target groups details for load balancer {}:'.format(self.get_balancer_name()))
            ctx.pp.pprint(data)

        @task
        def create_listeners(ctx):
            """
            Creates listeners between load balancer and target groups for current environment.
            """
            data = self.create_listeners()
            ctx.info('Created listeners for load balancer {}:'.format(
                self.get_balancer_name()
            ))
            ctx.pp.pprint(data)

        @task
        def delete_listeners(ctx):
            """
            Deletes listeners for current environment.
            """
            if self.balancer_exists():
                self.delete_listeners()
                ctx.info('Deleted all listeners for load balancer {}:'.format(self.get_balancer_name()))
            else:
                ctx.info('Load balancer {} does not exist, no listeners to remove.'.format(self.get_balancer_name()))

        @task
        def describe_listeners(ctx):
            """
            Describes listeners for current environment.
            """
            data = self.describe_listeners()
            ctx.info('Listeners details for load balancer {}:'.format(self.get_balancer_name()))
            ctx.pp.pprint(data)

        @task
        def create(ctx):
            """Creates fully operational load balancer setup for the current environment."""
            create_target_groups(ctx)
            create_balancer(ctx)
            create_listeners(ctx)

            ctx.info('Load balancers setup completed.')

        @task
        def delete(ctx):
            """Deletes load balancer for current environment and all related resources."""
            delete_listeners(ctx)
            delete_balancer(ctx)
            delete_target_groups(ctx)

            ctx.info('Load balancers deletion completed.')

        @task
        def reset(ctx):
            """Resets load balancer setup for the current environment."""
            delete(ctx)
            create(ctx)

            ctx.info('Load balancers reset completed.')

        @task
        def describe(ctx):
            describe_balancer(ctx)
            describe_target_groups(ctx)
            describe_listeners(ctx)

        return [
            create_balancer, delete_balancer, describe_balancer,
            create_target_groups, delete_target_groups, describe_target_groups,
            create_listeners, delete_listeners, describe_listeners,
            create, delete, reset, describe,
        ]


class AwsElbPluginMixin:
    def get_balancer_arn(self, env=None):
        return self.app.plugins['aws_elb'].get_balancer_arn(env)

    def get_target_group_arn(self, short_name, env=None):
        return self.app.plugins['aws_elb'].get_target_group_arn(short_name, env=env)

    def get_balancer_dns(self, env=None):
        return self.app.plugins['aws_elb'].get_balancer_dns(env)

    def balancer_exists(self, env=None):
        return self.app.plugins['aws_elb'].balancer_exists(env)


PLUGIN_CLASS = AwsElbPlugin
