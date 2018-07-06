import time

from invoke import task

from chops.plugins.aws.aws_container_service_plugin import AwsContainerServicePlugin
from chops.plugins.aws.aws_envs import AwsEnvsPluginMixin
from chops.plugins.docker import DockerPluginMixin


class AwsEcsPlugin(AwsContainerServicePlugin, AwsEnvsPluginMixin, DockerPluginMixin):
    name = 'aws_ecs'
    dependencies = ['aws', 'aws_ecr', 'aws_envs', 'docker']
    service_name = 'ecs'
    required_keys = ['containers', 'service_name']

    def get_containers(self):
        """
        Returns container definitions
        :return: dict[] container definitions
        """
        return self.config['containers']

    def get_cluster_prefix(self):
        """
        Returns cluster prefix
        :return: str cluster prefix
        """
        return self.get_aws_project_name() + '-'

    def get_cluster_name(self, env=None):
        """
        Returns the name of the cluster for the current or specified environment in a form of
        '<AWS project name>-<env name>'.
        :param env: str environment name
        :return: canonical cluster name
        """
        return self.get_cluster_prefix() + (env or self.get_current_env())

    def get_task_definition_name(self):
        """
        Returns task definition name.
        :return: str task definition name
        """
        return '{project_name}-{service_name}'.format(
            project_name=self.get_aws_project_name(),
            service_name=self.config['service_name'],
        )

    def get_service_name(self):
        """
        Returns default service name
        :return: str service name
        """
        return '{project_name}-{service_name}'.format(
            project_name=self.get_aws_project_name(),
            service_name=self.config['service_name'],
        )

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

    def get_container_instances(self, cluster_name):
        """
        Returns cluster container instances details
        :param cluster_name: str cluster name
        :return: dict[] cluster instances details
        """
        container_instances_list = self.client.list_container_instances(
            cluster=cluster_name
        ).get('containerInstanceArns', [])
        return self.client.describe_container_instances(
            cluster=cluster_name,
            containerInstances=container_instances_list
        ).get('containerInstances', [])

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

    def get_task_def_arns(self):
        """
        Returns task definition ARNs
        :return: str[] list of task definition ARNs
        """
        response = self.client.list_task_definitions(familyPrefix=self.get_task_definition_name())
        return response.get('taskDefinitionArns', [])

    def register_task(self):
        """
        Registers new task definition for default task family
        :return: dict created task definition
        """
        response = self.client.register_task_definition(
            family=self.get_task_definition_name(),
            containerDefinitions=self.get_containers()
        )
        assert response['ResponseMetadata']['HTTPStatusCode'] == 200
        return response['taskDefinition']

    def create_service(self):
        """
        Creates default service and returns API response.
        The service desired tasks count is set to zero.
        :return: dict JSON response from API
        """
        response = self.client.create_service(
            cluster=self.get_cluster_name(),
            serviceName=self.get_service_name(),
            taskDefinition=self.get_task_definition_name(),
            desiredCount=0,
            deploymentConfiguration={
                'maximumPercent': 100,
                'minimumHealthyPercent': 50,
            }
        )
        assert response['ResponseMetadata']['HTTPStatusCode'] == 200
        return response['service']

    def set_service_desired_tasks_count(self, desired_count):
        """
        Sets the number of desired tasks.
        :param desired_count: int number of desired tasks
        """
        response = self.client.update_service(
            cluster=self.get_cluster_name(),
            service=self.get_service_name(),
            desiredCount=desired_count,
        )
        assert response['ResponseMetadata']['HTTPStatusCode'] == 200

        self.logger.info(
            'Service {service_name} at cluster {cluster_name} desired count set to {desired_count}.'.format(
                service_name=self.get_service_name(),
                cluster_name=self.get_cluster_name(),
                desired_count=desired_count,
            ))

    def stop_service(self):
        """
        Starts the service by setting desired tasks count to one
        """
        self.set_service_desired_tasks_count(0)

    def start_service(self):
        """
        Stops the service by setting desired tasks count to zero
        """
        self.set_service_desired_tasks_count(1)

    def get_service_info(self):
        """
        Describes default service
        :return: dict|None service description or None if service does not exist
        """
        services = self.client.describe_services(
            cluster=self.get_cluster_name(),
            services=[self.get_service_name()]
        ).get('services', [])

        for service in services:
            if service['serviceName'] == self.get_service_name():
                return service

    def service_exists(self):
        """
        Returns whether default server exists
        :return: bool whether default server exists or not
        """
        service_info = self.get_service_info()
        return service_info is not None and service_info['status'] != 'INACTIVE'

    def get_service_running_count(self):
        """
        Returns number of running tasks.
        :return: int number of running tasks
        """
        service = self.get_service_info()
        if service is not None:
            return service['runningCount']

    def await_service_running_count(self, count, timeout=1, retries=30):
        """
        Awaits service running count became equal to the specified value
        :param count: int how many running instances we want
        :param timeout: float timeout between retries in seconds
        :param retries: int number of retries
        :return: bool whether specified running count was reached or not
        """
        for i in range(retries):
            current_count = self.get_service_running_count()
            if current_count is None:
                return False
            elif current_count == count:
                return True

            self.logger.info(
                'Awaiting service {service_name} at cluster {cluster_name} '
                'to reach {count} running tasks (retries left: {left})...'.format(
                    service_name=self.get_service_name(),
                    cluster_name=self.get_cluster_name(),
                    count=count, left=retries-i,
                ))
            time.sleep(timeout)

        return False

    def delete_service(self, force=False):
        """
        Deletes the current service.
        :param force: whether to remove service forcefully
        :return: dict JSON response from API
        """
        response = self.client.delete_service(
            cluster=self.get_cluster_name(),
            service=self.get_service_name(),
            force=force,
        )
        assert response['ResponseMetadata']['HTTPStatusCode'] == 200

        self.logger.info('Service {service_name} at cluster {cluster_name} deletion requested.'.format(
            cluster_name=self.get_cluster_name(),
            service_name=self.get_service_name(),
        ))

    def await_service_absence(self, timeout=1, retries=30):
        for i in range(retries):
            if not self.service_exists():
                return True

            self.logger.info(
                'Awaiting service {service_name} at cluster {cluster_name} '
                'to be deleted (retries left: {left})...'.format(
                    service_name=self.get_service_name(),
                    cluster_name=self.get_cluster_name(),
                    left=retries-i,
                ))
            time.sleep(timeout)

        return False

    def get_tasks(self):
        @task
        def list_clusters(ctx):
            """Lists clusters."""
            ctx.pp.pprint(self.get_cluster_arns())

        @task(iterable=['env'])
        def describe_clusters(ctx, env=None):
            """Describes cluster, use --env=* for all environments."""
            ctx.pp.pprint(self.get_clusters_info(self.get_cluster_names(env)))

        @task
        def describe_task_defs(ctx):
            """Describes task definitions."""
            for arn in self.get_task_def_arns():
                response = self.client.describe_task_definition(taskDefinition=arn)
                ctx.pp.pprint(response['taskDefinition'])

        @task
        def register_task(ctx):
            """Registers main task definition."""
            task_def = self.register_task()
            ctx.pp.pprint('Tasks definition {family}:{revision} successfully created.'.format(
                family=task_def['family'],
                revision=task_def['revision'],
            ))

        @task
        def create_service(ctx):
            """Creates service for the latest task definition"""
            if not self.service_exists():
                self.create_service()
                ctx.pp.pprint('Service {service_name} at cluster {cluster_name} successfully created.'.format(
                    service_name=self.get_service_name(),
                    cluster_name=self.get_cluster_name(),
                ))
            else:
                ctx.pp.pprint('Service {service_name} at cluster {cluster_name} already exists.'.format(
                    service_name=self.get_service_name(),
                    cluster_name=self.get_cluster_name(),
                ))

        @task
        def start_service(ctx):
            """Starts the ECS service"""
            self.start_service()
            ctx.pp.pprint('Requested service {service_name} start at cluster {cluster_name}.'.format(
                service_name=self.get_service_name(),
                cluster_name=self.get_cluster_name(),
            ))

            is_server_started = self.await_service_running_count(1)
            ctx.pp.pprint('Service {service_name} at cluster {cluster_name} started: {started}'.format(
                service_name=self.get_service_name(),
                cluster_name=self.get_cluster_name(),
                started=is_server_started,
            ))

        @task
        def stop_service(ctx):
            """Stops the ECS service"""
            self.stop_service()
            ctx.pp.pprint('Service {} stopped: {}'.format(
                self.get_service_name(),
                self.await_service_running_count(0),
            ))

        @task
        def delete_service(ctx, force=False):
            """Stops the ECS service"""
            if not self.service_exists():
                ctx.pp.pprint('Service {service_name} at {cluster_name} does not exist, nothing to delete.'.format(
                    service_name=self.get_service_name(),
                    cluster_name=self.get_cluster_name(),
                ))
                return

            self.stop_service()

            if force:
                service_stopped = self.await_service_running_count(0)
                ctx.pp.pprint('Service {} stopped: {}'.format(
                    self.get_service_name(),
                    service_stopped,
                ))

            self.delete_service(force)
            self.await_service_absence()
            ctx.pp.pprint('Service {service_name} at {cluster_name} successfully deleted.'.format(
                service_name=self.get_service_name(),
                cluster_name=self.get_cluster_name(),
            ))

        @task(delete_service, register_task, create_service, start_service)
        def deploy(ctx):
            ctx.pp.pprint('Service {service_name} successfully deployed to cluster {cluster_name}.'.format(
                service_name=self.get_service_name(),
                cluster_name=self.get_cluster_name(),
            ))

        return [
            list_clusters, describe_clusters, describe_task_defs,
            register_task,
            create_service, start_service, stop_service, delete_service,
            deploy,
        ]


PLUGIN_CLASS = AwsEcsPlugin
