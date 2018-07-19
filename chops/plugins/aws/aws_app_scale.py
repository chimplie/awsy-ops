from invoke import task

from chops.plugins.aws.aws_ecs import AwsEcsPluginMixin
from chops.plugins.aws.aws_env_bound_service_plugin import AwsEnvBoundServicePlugin


class AwsAppScalePlugin(AwsEnvBoundServicePlugin, AwsEcsPluginMixin):
    name = 'aws_app_scale'
    dependencies = ['aws', 'aws_envs', 'aws_ec2', 'aws_ecs']
    service_name = 'application-autoscaling'
    required_keys = ['services']

    def get_ecs_scalable_services_names(self):
        return list(self.config['services'].keys())

    def get_ecs_scalable_service_config(self, service_name):
        return self.config['services'][service_name]

    def get_ecs_service_resource_id(self, service_name):
        return 'service/{cluster}/{service}'.format(
            cluster=self.get_ecs_cluster_name(),
            service=self.get_ecs_service_name(service_name),
        )

    def get_ecs_service_policy_name(self, service_name, policy_name):
        return f'{self.get_ecs_service_name(service_name)}-{policy_name}'

    def get_ecs_service_policy_names(self, service_name):
        return list(self.get_ecs_scalable_service_config(service_name)['policies'].keys())

    def get_ecs_service_resource_ids(self):
        return [
            self.get_ecs_service_resource_id(service_name)
            for service_name in self.get_ecs_services_names()
        ]

    def get_ecs_service_targets(self):
        return self.client.describe_scalable_targets(
            ServiceNamespace='ecs',
            ResourceIds=self.get_ecs_service_resource_ids(),
        ).get('ScalableTargets')

    def get_ecs_service_policies_info(self):
        policies = []

        for resource_id in self.get_ecs_service_resource_ids():
            policies.extend(
                self.client.describe_scaling_policies(
                    ServiceNamespace='ecs',
                    ResourceId=resource_id,
                ).get('ScalingPolicies')
            )

        return policies

    def get_ecs_service_scheduled_actions(self):
        actions = []

        for resource_id in self.get_ecs_service_resource_ids():
            actions.extend(
                self.client.describe_scheduled_actions(
                    ServiceNamespace='ecs',
                    ResourceId=resource_id,
                ).get('ScheduledActions')
            )

        return actions

    def get_all_targets(self, namespace):
        return self.client.describe_scalable_targets(ServiceNamespace=namespace).get('ScalableTargets')

    def get_all_policies(self, namespace):
        return self.client.describe_scaling_policies(ServiceNamespace=namespace).get('ScalingPolicies')

    def get_all_scheduled_actions(self, namespace):
        return self.client.describe_scheduled_actions(ServiceNamespace=namespace).get('ScheduledActions')

    def get_all_scaling_activities(self, namespace):
        return self.client.describe_scaling_activities(ServiceNamespace=namespace).get('ScalingActivities')

    def register_ecs_service_target(self, service_name):
        resource_id = self.get_ecs_service_resource_id(service_name)
        self.client.register_scalable_target(
            ServiceNamespace='ecs',
            ResourceId=resource_id,
            ScalableDimension='ecs:service:DesiredCount',
            **self.get_ecs_scalable_service_config(service_name)['target']
        )

    def put_ecs_service_policy(self, service_name, policy_name):
        resource_id = self.get_ecs_service_resource_id(service_name)
        service_config = self.get_ecs_scalable_service_config(service_name)
        self.client.put_scaling_policy(
            PolicyName=self.get_ecs_service_policy_name(service_name, policy_name),
            ResourceId=resource_id,
            ScalableDimension='ecs:service:DesiredCount',
            ServiceNamespace='ecs',
            **service_config['policies'][policy_name]
        )

    def delete_ecs_service_policies(self):
        deleted_policies = []

        for policy in self.get_ecs_service_policies_info():
            self.client.delete_scaling_policy(
                PolicyName=policy['PolicyName'],
                ServiceNamespace=policy['ServiceNamespace'],
                ResourceId=policy['ResourceId'],
                ScalableDimension=policy['ScalableDimension'],
            )
            deleted_policies.append(policy['PolicyName'])

        return deleted_policies

    def get_modify_tasks(self):
        @task
        def register(ctx):
            """Registers scalable targets."""
            for service_name in self.get_ecs_scalable_services_names():
                self.register_ecs_service_target(service_name)
                ctx.info(f'Successfully registered "{service_name}" service as scalable target.')

        @task
        def put_policies(ctx):
            """Puts scaling policies."""
            for service_name in self.get_ecs_scalable_services_names():
                for police_name in self.get_ecs_service_policy_names(service_name):
                    self.put_ecs_service_policy(service_name, police_name)
                    ctx.info(f'Successfully registered scaling policy "{police_name}" for the '
                             f'"{self.get_ecs_service_resource_id(service_name)}" ECS service.')

        @task
        def delete_policies(ctx):
            """Deletes scaling policies"""
            deleted_policies = self.delete_ecs_service_policies()
            if len(deleted_policies) > 0:
                ctx.info(f'Successfully deleted ECS scaling policies: {deleted_policies}.')
            else:
                ctx.info('No ECS scaling policies to delete.')

        @task(register, put_policies)
        def scale(ctx):
            """Scale all services for the current environment"""
            ctx.info('Successfully scaled services for "{}" environment.'.format(self.get_current_env()))

        @task(delete_policies)
        def disable(ctx):
            """Disables scaling for the current environment"""
            ctx.info('Successfully disabled scaling for "{}" environment.'.format(self.get_current_env()))

        return [scale, disable, register, put_policies, delete_policies]

    def get_describe_tasks(self):
        @task
        def targets(ctx):
            """
            Describes available scalable targets for the current environment ECS services
            """
            ctx.info('ECS services scalable targets for "{}" cluster:'.format(self.get_ecs_cluster_name()))
            ctx.pp.pprint(self.get_ecs_service_targets())

        @task
        def policies(ctx):
            """
            Describes available scaling policies for the current environment ECS services
            """
            ctx.info('ECS services scaling policies for "{}" cluster:'.format(self.get_ecs_cluster_name()))
            ctx.pp.pprint(self.get_ecs_service_policies_info())

        @task
        def actions(ctx):
            """
            Describes scheduled actions for the current environment ECS services
            """
            ctx.info('Scheduled actions for ECS services scaling policies of the "{}" cluster:'.format(
                self.get_ecs_cluster_name()
            ))
            ctx.pp.pprint(self.get_ecs_service_scheduled_actions())

        @task
        def all_targets(ctx):
            """
            Describes all available scalable targets (ECS & EC2)
            """
            ctx.info('ECS scalable targets:')
            ctx.pp.pprint(self.get_all_targets('ecs'))

        @task
        def all_policies(ctx):
            """
            Describes all available scaling policies (ECS & EC2)
            """
            ctx.info('ECS scalable policies:')
            ctx.pp.pprint(self.get_all_policies('ecs'))

        @task
        def all_actions(ctx):
            """
            Describes all existing scheduled actions (ECS & EC2)
            """
            ctx.info('ECS scheduled actions:')
            ctx.pp.pprint(self.get_all_scheduled_actions('ecs'))

        @task
        def all_activities(ctx):
            """
            Describes all scaling activities (ECS & EC2)
            """
            ctx.info('ECS scaling activities:')
            ctx.pp.pprint(self.get_all_scaling_activities('ecs'))

        @task(targets, policies, actions)
        def describe(ctx):
            """Describe all context-related parts of the service"""

        @task(all_targets, all_policies, all_actions, all_activities)
        def describe_all(ctx):
            """Describe all parts of the auto-scaling service"""

        return [describe, targets, policies, actions, describe_all, all_policies, all_actions, all_activities]

    def get_tasks(self):
        return self.get_describe_tasks() + self.get_modify_tasks()


PLUGIN_CLASS = AwsAppScalePlugin
