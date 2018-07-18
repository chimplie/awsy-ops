from invoke import task

from chops.plugins.aws.aws_ecs import AwsEcsPluginMixin
from chops.plugins.aws.aws_envs import AwsEnvsPluginMixin
from chops.plugins.aws.aws_service_plugin import AwsServicePlugin


class AwsEc2ScalePlugin(AwsServicePlugin, AwsEnvsPluginMixin, AwsEcsPluginMixin):
    name = 'aws_ec2_scale'
    dependencies = ['aws', 'aws_envs', 'aws_ec2', 'aws_ecs']
    service_name = 'autoscaling'
    required_keys = ['policies', 'environments']

    def get_policies_short_names(self):
        """
        Returns short names for policies to be defined.
        :return: str[] policy short names
        """
        return list(self.config['policies'].keys())

    def get_ecs_policy_full_name(self, policy_name):
        return '{}-{}'.format(self.get_ecs_cluster_name(), policy_name)

    def get_ecs_autoscaling_groups_names(self):
        """
        Returns ECS autoscaling groups names for the current environment cluster.
        :return: str[] autoscaling group names
        """
        group_names = set()

        for instance in self.get_ecs_container_instances():
            for tag in instance['ec2_instance']['Tags']:
                if tag['Key'] == 'aws:autoscaling:groupName':
                    group_names.add(tag['Value'])

        return list(group_names)

    def get_ecs_autoscaling_groups_info(self):
        """
        Returns ECS autoscaling groups details for the current environment cluster.
        :return: dit[] autoscaling groups info
        """
        return self.client.describe_auto_scaling_groups(
            AutoScalingGroupNames=self.get_ecs_autoscaling_groups_names()
        ).get('AutoScalingGroups')

    def get_ecs_group_policies_info(self, group_name):
        """
        Returns ECS scaling policies details for the specified autoscaling group of the current environment cluster.
        :param group_name: str autoscaling group name
        :return: dit[] autoscaling groups info
        """
        return self.client.describe_policies(
            AutoScalingGroupName=group_name,
        ).get('ScalingPolicies')

    def put_scaling_policy(self, group_name, policy_name):
        """
        Creates scaling policy for the specified autoscale gpoup.
        :param group_name: str autoscaling group name
        :param policy_name: str policy short name
        :return: dict created policy ARN and Alarms
        """
        response = self.client.put_scaling_policy(
            AutoScalingGroupName=group_name,
            PolicyName=self.get_ecs_policy_full_name(policy_name),
            **self.config['policies'][policy_name]
        )
        return {
            'PolicyARN': response['PolicyARN'],
            'Alarms': response['Alarms'],
        }

    def delete_scaling_policy(self, group_name, policy_name):
        """
        Deletes scaling policy for the specified autoscale gpoup.
        :param group_name: str autoscaling group name
        :param policy_name: str policy short name
        """
        self.client.delete_policy(
            AutoScalingGroupName=group_name,
            PolicyName=policy_name
        )

    def update_group(self, group_name):
        """
        Updates settings for the specified autoscaling of the current environment.
        :param group_name: str autoscaling group name
        """
        app_env = self.get_current_env()
        if app_env in self.config['environments']:
            self.client.update_auto_scaling_group(
                AutoScalingGroupName=group_name,
                **self.config['environments'][app_env]
            )

    def get_tasks(self):
        @task
        def groups(ctx):
            """Describes autoscaling groups for the current environment."""
            ctx.info('Autoscaling groups:')
            ctx.pp.pprint(self.get_ecs_autoscaling_groups_info())

        @task
        def policies(ctx):
            """Describes scaling policies."""
            for group_name in self.get_ecs_autoscaling_groups_names():
                ctx.info(f'Scaling policies for autoscaling group "{group_name}":')
                ctx.pp.pprint(self.get_ecs_group_policies_info(group_name))

        @task
        def put_policies(ctx):
            """Creates scaling policies for the current environment."""
            for group_name in self.get_ecs_autoscaling_groups_names():
                for policy_name in self.get_policies_short_names():
                    ctx.info(f'Created scaling policy "{policy_name}" for autoscaling group {group_name}:')
                    ctx.pp.pprint(self.put_scaling_policy(group_name, policy_name))

        @task
        def delete_policies(ctx):
            """Deletes all scaling policies for the current environment."""
            for group_name in self.get_ecs_autoscaling_groups_names():
                for policy in self.get_ecs_group_policies_info(group_name):
                    policy_name = policy['PolicyName']
                    self.delete_scaling_policy(group_name, policy_name)
                    ctx.info(f'Successfully deleted scaling policy "{policy_name}" '
                             f'for autoscaling group {group_name}:')

        @task
        def update_groups(ctx):
            """Updates autoscaling groups of the current environment."""
            for group_name in self.get_ecs_autoscaling_groups_names():
                self.update_group(group_name)
                ctx.info(f'Successfully updated autoscaling group {group_name}.')

        @task(put_policies, update_groups)
        def scale(ctx):
            """Updates the current environment."""
            ctx.info('Successfully scaled "{}" environment.'.format(self.get_current_env()))

        @task(groups, policies)
        def describe(ctx):
            """Describes the current environment."""

        return [describe, scale, groups, policies, put_policies, delete_policies, update_groups]


PLUGIN_CLASS = AwsEc2ScalePlugin
