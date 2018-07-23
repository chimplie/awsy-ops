import time

from invoke import task

from chops.plugins.aws.aws_env_bound_service_plugin import AwsEnvBoundServicePlugin
from chops.plugins.aws.aws_ec2 import AwsEc2PluginMixin
from chops.plugins.aws.aws_ecr import AwsEcrPluginMixin
from chops.plugins.aws.aws_elb import AwsElbPluginMixin
from chops.plugins.aws.aws_logs import AwsLogsPluginMixin
from chops.plugins.aws.aws_s3 import AwsS3PluginMixin
from chops.plugins.docker import DockerPluginMixin


class AwsEcsPlugin(AwsEnvBoundServicePlugin,
                   AwsEcrPluginMixin, AwsLogsPluginMixin,
                   AwsElbPluginMixin, AwsS3PluginMixin, AwsEc2PluginMixin,
                   DockerPluginMixin):
    name = 'aws_ecs'
    dependencies = ['aws', 'aws_ecr', 'aws_envs', 'aws_elb', 'aws_s3', 'aws_ec2', 'docker']
    service_name = 'ecs'
    required_keys = ['namespace', 'services', 'task_definitions']

    def get_task_def_names(self):
        """
        Returns task definitions short names
        :return: str[] task definition names
        """
        return list(self.config['task_definitions'].keys())

    def get_services_names(self):
        """
        Returns services short names
        :return: str[] services short names
        """
        return list(self.config['services'].keys())

    def get_task_definition(self, task_name):
        """
        Returns task definition config specific to the current environment.
        :param task_name: str task short name
        :return: dict task definition
        """
        return self.config['task_definitions'][task_name]

    def get_containers(self, task_name):
        """
        Returns container definitions for the specified task
        :param task_name: str task name
        :return: dict[] container definitions
        """
        env = self.get_current_env()
        task_config = self.get_task_definition(task_name)
        containers = task_config['containers']

        for container_name, container in containers.items():
            if 'image' not in container:
                if '__image__' in container:
                    image_name = container['__image__']
                    del container['__image__']
                else:
                    image_name = container_name
                container['image'] = self.get_service_image_uri(image_name)

            if 'logConfiguration' not in container:
                container['logConfiguration'] = {
                    'logDriver': 'awslogs',
                    'options': {
                        'awslogs-group': self.get_log_group_name(env),
                        'awslogs-region': self.get_aws_region(),
                        'awslogs-stream-prefix': 'ecs-local',
                    }
                }

            if '__requires_aws_env_setup__' in container:
                container['environment'] = container.get('environment', [])
                container['environment'].extend([
                    {'name': 'APP_ENV', 'value': env},
                    {'name': 'AWS_REGION', 'value': self.get_aws_region()},
                    {'name': 'AWS_ACCESS_KEY_ID', 'value': self.get_credentials().access_key},
                    {'name': 'AWS_SECRET_ACCESS_KEY', 'value': self.get_credentials().secret_key},
                    {'name': 'AWS_STORAGE_BUCKET_NAME', 'value': self.get_bucket_name(env)},
                    {'name': 'PROJECT_NAME', 'value': self.get_aws_project_name()},
                    {'name': 'ALLOW_HOSTS', 'value': ','.join(self.get_access_hosts())},
                ])
                del container['__requires_aws_env_setup__']

        #
        aws_containers = []
        for container_name in containers.keys():
            aws_containers.append({'name': container_name, **containers[container_name]})

        # Finally convert container definitions from dictionary to list format
        return [{'name': name, **container} for name, container in containers.items()]

    def get_access_hosts(self):
        """
        Returns a list of hosts by which the ECS application can be accessed.
        Includes load balancer DNS and EC2 instance public DNS and IPs.
        :return: str[] list of hosts
        """
        # Working on the current environment
        env = self.get_current_env()
        # Working with set to deduplicate
        get_access_hosts = set()

        # Add balancer DNS name if exists
        if self.balancer_exists():
            get_access_hosts.add(self.get_balancer_dns())

        # Iterate over EC2 instances
        for container_instance in self.get_container_instances(self.get_cluster_name(env)):
            if 'ec2_instance' in container_instance:
                # and for each instance interface
                for interface in container_instance['ec2_instance']['NetworkInterfaces']:
                    # add all possible access hosts
                    for section_name in ['Association', 'Attachment']:
                        section = interface.get(section_name, {})
                        for key in ['PublicDnsName', 'PublicIp', 'PrivateDnsName', 'PrivateIpAddress']:
                            if key in section:
                                get_access_hosts.add(section[key])

        return list(get_access_hosts)

    def get_volumes(self, task_name):
        """
        Returns the list of the task's defined volumes or the empty list.
        :param task_name: str task short name
        :return: dict[] list of volumes
        """
        return self.get_task_definition(task_name).get('volumes', [])

    def get_cluster_prefix(self):
        """
        Returns cluster prefix
        :return: str cluster prefix
        """
        return '{}-'.format(self.config['namespace'])

    def get_cluster_name(self, env=None):
        """
        Returns the name of the cluster for the current or specified environment in a form of
        '<AWS project name>-<env name>'.
        :param env: str environment name
        :return: canonical cluster name
        """
        return self.get_cluster_prefix() + (env or self.get_current_env())

    def get_task_definition_name(self, task_name):
        """
        Returns the task definition full name.
        :param task_name: str task short name
        :return: str task definition name
        """
        return '{}-{}'.format(self.config['namespace'], task_name)

    def get_service_task_definition_name(self, service_name):
        """
        Returns the task definition full name for the specified service.
        The task definition by default equals to the server name
        and could be overridden in the service's `task_definition` config key.
        :param service_name: str service short name
        :return: str task definition name
        """
        return self.get_task_definition_name(self.get_service_config(service_name).get('task_definition', service_name))

    def get_service_name(self, service_name):
        """
        Returns default service name
        :param service_name: str service short name
        :return: str service short name
        """
        return '{}-{}'.format(self.config['namespace'], service_name)

    def get_cluster_names(self, env):
        """
        Returns cluster names for specified environment (* for all environments).
        :param env: str environment name or wildcard (* for all environments)
        :return: str[] list of cluster names
        """
        return [self.get_cluster_name(env_name) for env_name in self.envs_from_string(env)]

    def get_cluster_arns(self):
        """
        Returns existing clusters matching the '<AWS project name>-*' pattern.
        :return: str[] list of cluster ARNs
        """
        response = self.client.list_clusters()
        return [cluster for cluster in response.get('clusterArns', [])
                if ':cluster/' + self.get_cluster_prefix() in cluster]

    def get_load_balancers(self, service_name):
        """
        Returns load balancers config if exists or an empty list.
        :param service_name: str service short name
        :return: dict[] load balancers config
        """
        balancers = self.get_service_config(service_name).get('load_balancers', [])
        for balancer in balancers:
            if 'targetGroupArn' not in balancer:
                if '__target_group__' in balancer:
                    target_group_name = balancer['__target_group__']
                    del balancer['__target_group__']
                else:
                    target_group_name = service_name
                balancer['targetGroupArn'] = self.get_target_group_arn(target_group_name)
        return balancers

    def get_service_config(self, service_name):
        """
        Returns service configuration.
        :param service_name: str service short name
        :return: dict service config
        """
        return self.config['services'][service_name]

    def get_service_ecs_config(self, service_name):
        """
        Returns service configuration or an empty dictionary.
        :param service_name: str service short name
        :return: dict service ECS config
        """
        return self.get_service_config(service_name).get('config', {})

    def get_tasks_count(self, service_name):
        """
        Returns desired tasks count for the specified service.
        :param service_name: str service short name
        :return: int tasks count
        """
        return self.get_service_config(service_name).get('tasks_count', 1)

    def get_container_instances(self, cluster_name):
        """
        Returns cluster container instances details
        :param cluster_name: str cluster name
        :return: dict[] cluster instances details
        """
        container_instances_list = self.client.list_container_instances(
            cluster=cluster_name
        ).get('containerInstanceArns', [])

        if len(container_instances_list) == 0:
            return []

        container_instances = self.client.describe_container_instances(
            cluster=cluster_name,
            containerInstances=container_instances_list
        ).get('containerInstances', [])

        for instance in container_instances:
            try:
                instance['ec2_instance'] = self.ec2_client.describe_instances(
                    InstanceIds=[instance['ec2InstanceId']]
                )['Reservations'][0]['Instances'][0]
            except (IndexError, KeyError):
                pass

        return container_instances

    def get_clusters_info(self, clusters):
        """
        Returns descriptions for specified clusters
        :param clusters: str[] list of clusters to inspect
        :return: dict[] list of cluster descriptions with instance details
        """
        response = self.client.describe_clusters(clusters=clusters, include=['STATISTICS'])
        clusters = response.get('clusters', [])
        for cluster in clusters:
            cluster['containerInstances'] = self.get_container_instances(cluster['clusterName'])
        return clusters

    def get_task_def_arns(self, task_name):
        """
        Returns task definition ARNs
        :param task_name: str task definition short names
        :return: str[] list of task definition ARNs
        """
        response = self.client.list_task_definitions(familyPrefix=self.get_task_definition_name(task_name))
        return response.get('taskDefinitionArns', [])

    def register_task(self, task_name):
        """
        Registers new task definition for the specified default task family short name
        :param task_name: str task definition short name
        :return: dict created task definition
        """
        response = self.client.register_task_definition(
            family=self.get_task_definition_name(task_name),
            containerDefinitions=self.get_containers(task_name),
            volumes=self.get_volumes(task_name),
        )
        assert response['ResponseMetadata']['HTTPStatusCode'] == 200
        return response['taskDefinition']

    def create_service(self, service_name):
        """
        Creates specified service and returns API response.
        The service desired tasks count is set to zero.
        :param service_name: str service short name
        :return: dict JSON response from API
        """
        response = self.client.create_service(
            cluster=self.get_cluster_name(),
            serviceName=self.get_service_name(service_name),
            taskDefinition=self.get_service_task_definition_name(service_name),
            desiredCount=0,
            deploymentConfiguration={
                'maximumPercent': 100,
                'minimumHealthyPercent': 50,
            },
            loadBalancers=self.get_load_balancers(service_name),
            **self.get_service_ecs_config(service_name),
        )
        assert response['ResponseMetadata']['HTTPStatusCode'] == 200
        return response['service']

    def set_service_desired_tasks_count(self, service_name, desired_count):
        """
        Sets the number of desired tasks.
        :param service_name: str service short name
        :param desired_count: int number of desired tasks
        """
        full_service_name = self.get_service_name(service_name)
        response = self.client.update_service(
            cluster=self.get_cluster_name(),
            service=full_service_name,
            desiredCount=desired_count,
        )
        assert response['ResponseMetadata']['HTTPStatusCode'] == 200

        self.logger.info(
            'Service {service_name} at cluster {cluster_name} desired count set to {desired_count}.'.format(
                service_name=full_service_name,
                cluster_name=self.get_cluster_name(),
                desired_count=desired_count,
            ))

    def stop_all_service_tasks(self, service_name):
        """
        Stops all service tasks.
        :param service_name: str service short name
        """
        full_service_name = self.get_service_name(service_name)

        # Get tasks list
        response = self.client.list_tasks(
            cluster=self.get_cluster_name(),
            serviceName=full_service_name,
        )
        assert response['ResponseMetadata']['HTTPStatusCode'] == 200

        tasks_arns = response['taskArns']
        for task_arn in tasks_arns:
            response = self.client.stop_task(
                cluster=self.get_cluster_name(),
                task=task_arn,
                reason='Service {} shutdown.'.format(full_service_name)
            )
            assert response['ResponseMetadata']['HTTPStatusCode'] == 200
            self.logger.info('Task {arn} stop requested for service {service} at cluster {cluster}.'.format(
                arn=task_arn,
                cluster=self.get_cluster_name(),
                service=full_service_name,
            ))

    def stop_service(self, service_name):
        """
        Stops the service by setting desired tasks count to one
        :param service_name: str service short name
        """
        self.set_service_desired_tasks_count(service_name, 0)
        self.stop_all_service_tasks(service_name)

    def start_service(self, service_name):
        """
        Stops the service by setting desired tasks count to zero
        :param service_name: str service short name
        """
        self.set_service_desired_tasks_count(service_name, self.get_tasks_count(service_name))

    def get_service_info(self, service_name):
        """
        Describes specified service
        :param service_name: str service short name
        :return: dict|None service description or None if service does not exist
        """
        full_service_name = self.get_service_name(service_name)

        services = self.client.describe_services(
            cluster=self.get_cluster_name(),
            services=[full_service_name]
        ).get('services', [])

        for service in services:
            if service['serviceName'] == full_service_name:
                return service

    def service_exists(self, service_name):
        """
        Returns whether specified server exists
        :param service_name: str service short name
        :return: bool whether default server exists or not
        """
        service_info = self.get_service_info(service_name)
        return service_info is not None and service_info['status'] != 'INACTIVE'

    def get_service_running_count(self, service_name):
        """
        Returns number of running tasks.
        :param service_name: str service short name
        :return: int number of running tasks
        """
        service = self.get_service_info(service_name)
        if service is not None:
            return service['runningCount']

    def await_service_running_count(self, service_name, count, timeout=1, retries=90):
        """
        Awaits service running count became equal to the specified value
        :param service_name: str service short name
        :param count: int how many running instances we want
        :param timeout: float timeout between retries in seconds
        :param retries: int number of retries
        :return: bool whether specified running count was reached or not
        """
        for i in range(retries):
            current_count = self.get_service_running_count(service_name)
            if current_count is None:
                return False
            elif current_count == count:
                return True

            self.logger.info(
                'Awaiting service {service_name} at cluster {cluster_name} '
                'to reach {count} running tasks (retries left: {left})...'.format(
                    service_name=self.get_service_name(service_name),
                    cluster_name=self.get_cluster_name(),
                    count=count, left=retries-i,
                ))
            time.sleep(timeout)

        return False

    def delete_service(self, service_name, force=False):
        """
        Deletes the current service.
        :param service_name: str service short name
        :param force: whether to remove service forcefully
        :return: dict JSON response from API
        """
        full_service_name = self.get_service_name(service_name)

        response = self.client.delete_service(
            cluster=self.get_cluster_name(),
            service=full_service_name,
            force=force,
        )
        assert response['ResponseMetadata']['HTTPStatusCode'] == 200

        self.logger.info('Service {service_name} at cluster {cluster_name} deletion requested.'.format(
            cluster_name=self.get_cluster_name(),
            service_name=full_service_name,
        ))

    def await_service_absence(self, service_name, timeout=1, retries=90):
        """
        Waits until service become absent.
        :param service_name: str service short name
        :param timeout: int timeout between retries in seconds
        :param retries: int number of retries
        :return: bool whether service is finally absent
        """
        for i in range(retries):
            if not self.service_exists(service_name):
                return True

            self.logger.info(
                'Awaiting service {service_name} at cluster {cluster_name} '
                'to be deleted (retries left: {left})...'.format(
                    service_name=self.get_service_name(service_name),
                    cluster_name=self.get_cluster_name(),
                    left=retries-i,
                ))
            time.sleep(timeout)

        return False

    def get_tasks(self):
        @task
        def list_clusters(ctx):
            """Lists clusters."""
            ctx.info('Available cluster ARNs:')
            ctx.pp.pprint(self.get_cluster_arns())

        @task(iterable=['env'])
        def describe_clusters(ctx, env=None):
            """Describes cluster, use --env=* for all environments."""
            ctx.info('Available cluster info:')
            ctx.pp.pprint(self.get_clusters_info(self.get_cluster_names(env)))

        @task
        def describe_task_defs(ctx):
            """Describes task definitions."""
            for task_name in self.get_task_def_names():
                for arn in self.get_task_def_arns(task_name):
                    response = self.client.describe_task_definition(taskDefinition=arn)
                    ctx.info('Task definition of {}:'.format(arn))
                    ctx.pp.pprint(response['taskDefinition'])

        @task
        def list_hosts(ctx):
            """Lists access hosts for the current environment."""
            ctx.info('Available access hosts for {} environment:'.format(self.get_current_env()))
            ctx.pp.pprint(self.get_access_hosts())

        @task
        def register_tasks(ctx):
            """Registers main task definition."""
            for task_name in self.get_task_def_names():
                task_def = self.register_task(task_name)
                ctx.info('Tasks definition {family}:{revision} successfully created for {env} environment.'.format(
                    family=task_def['family'],
                    revision=task_def['revision'],
                    env=self.get_current_env(),
                ))

        @task
        def create_services(ctx):
            """Creates services for the latest task definitions"""
            for service_name in self.get_services_names():
                if not self.service_exists(service_name):
                    self.create_service(service_name)
                    ctx.info('Service {service_name} at cluster {cluster_name} successfully created.'.format(
                        service_name=self.get_service_name(service_name),
                        cluster_name=self.get_cluster_name(),
                    ))
                else:
                    ctx.info('Service {service_name} at cluster {cluster_name} already exists.'.format(
                        service_name=self.get_service_name(service_name),
                        cluster_name=self.get_cluster_name(),
                    ))

        @task
        def start_services(ctx):
            """Starts the ECS services"""
            for service_name in self.get_services_names():
                self.start_service(service_name)
                ctx.info('Requested service {service_name} start at cluster {cluster_name}.'.format(
                    service_name=self.get_service_name(service_name),
                    cluster_name=self.get_cluster_name(),
                ))

                is_server_started = self.await_service_running_count(
                    service_name,
                    self.get_tasks_count(service_name)
                )
                ctx.info('Service {service_name} at cluster {cluster_name} started: {started}'.format(
                    service_name=self.get_service_name(service_name),
                    cluster_name=self.get_cluster_name(),
                    started=is_server_started,
                ))

        @task
        def stop_services(ctx):
            """Stops the ECS services"""
            for service_name in self.get_services_names():
                self.stop_service(service_name)
                ctx.info('Service {} stopped: {}'.format(
                    self.get_service_name(service_name),
                    self.await_service_running_count(service_name, 0),
                ))

        @task
        def delete_services(ctx, force=False):
            """Deletes the ECS services"""
            for service_name in self.get_services_names():
                service_full_name = self.get_service_name(service_name)
                if not self.service_exists(service_name):
                    ctx.info('Service {service_name} at {cluster_name} does not exist, nothing to delete.'.format(
                        service_name=service_full_name,
                        cluster_name=self.get_cluster_name(),
                    ))
                    return

                ctx.info('Stopping service {service_name} at {cluster_name}...'.format(
                    service_name=service_full_name,
                    cluster_name=self.get_cluster_name(),
                ))
                self.stop_service(service_name)

                if not force:
                    service_stopped = self.await_service_running_count(service_name, 0)
                    ctx.info('Service {} stopped: {}'.format(
                        service_full_name,
                        service_stopped,
                    ))

                ctx.info('Deliting service {service_name} at {cluster_name}...'.format(
                    service_name=service_full_name,
                    cluster_name=self.get_cluster_name(),
                ))
                self.delete_service(service_name, force)

                self.await_service_absence(service_name)
                ctx.info('Service {service_name} at {cluster_name} successfully deleted.'.format(
                    service_name=service_full_name,
                    cluster_name=self.get_cluster_name(),
                ))

        @task(delete_services, register_tasks, create_services, start_services)
        def deploy(ctx):
            """Deploys services to the default cluster removing old service if necessary"""
            ctx.info('Services {services_names} successfully deployed to cluster {cluster_name}.'.format(
                services_names=self.get_services_names(),
                cluster_name=self.get_cluster_name(),
            ))

        return [
            list_clusters, describe_clusters, describe_task_defs,
            register_tasks,
            create_services, start_services, stop_services, delete_services,
            list_hosts,
            deploy,
        ]


class AwsEcsPluginMixin:
    def get_ecs_services_names(self):
        return self.app.plugins['aws_ecs'].get_services_names()

    def get_ecs_cluster_name(self, env=None):
        return self.app.plugins['aws_ecs'].get_cluster_name(env)

    def get_ecs_service_name(self, service_name):
        return self.app.plugins['aws_ecs'].get_service_name(service_name)

    def get_ecs_container_instances(self, env=None):
        return self.app.plugins['aws_ecs'].get_container_instances(
            self.get_ecs_cluster_name(env)
        )


PLUGIN_CLASS = AwsEcsPlugin
