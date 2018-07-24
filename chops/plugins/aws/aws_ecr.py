from invoke import task
from invoke.exceptions import UnexpectedExit

from chops.plugins.aws.aws_service_plugin import AwsServicePlugin
from chops.plugins.docker import DockerPluginMixin


class AwsEcrPlugin(AwsServicePlugin, DockerPluginMixin):
    name = 'aws_ecr'
    dependencies = ['aws', 'docker']
    service_name = 'ecr'
    required_keys = ['services']

    def get_service_repo_name(self, service_name):
        """
        Returns service repository name.
        :param service_name: str service short name
        :return: str repository name
        """
        return '{project_name}/{service_name}'.format(
            service_name=service_name,
            project_name=self.get_aws_project_name()
        )

    def get_service_path(self, service_name):
        """
        Returns service path.
        :param service_name: str service short name
        :return: str service path
        """
        return '{project_name}/{service_name}'.format(
            project_name=self.get_aws_project_name(),
            service_name=service_name,
        )

    def describe_repositories(self):
        """
        Returns repository descriptions.
        :return: dict[] repository details
        """
        repository_names = [self.get_service_repo_name(service_name)
                            for service_name in self.config['services']]

        response = self.client.describe_repositories(
            repositoryNames=repository_names
        )

        repositories = {}
        for repo_entry in response.get('repositories', []):
            repositories[repo_entry['repositoryName']] = repo_entry
        return repositories

    def get_service_image_uri(self, service_name, docker_tag=None):
        """
        Returns repository URL for specified service and tag (current if empty).
        :param service_name: str name of the service
        :param docker_tag: str | None docker tag or None for the current one
        :return: str full repository URI
        """
        repositories = self.describe_repositories()
        return '{uri}:{tag}'.format(
            uri=repositories[self.get_service_repo_name(service_name)]['repositoryUri'],
            tag=docker_tag or self.get_docker_tag(),
        )

    def get_tasks(self):
        @task
        def create(ctx):
            """Creates Docker repositories for all publishable services."""
            for service_name in self.config['services']:
                ctx.info(
                    'Create repository in ECS Docker registry '
                    'for service_name "{service_name}" '
                    'of the "{project_name}" project:'.format(
                        service_name=service_name,
                        project_name=self.get_aws_project_name()
                    ))
                response = self.client.create_repository(
                    repositoryName='{project_name}/{service_name}'.format(
                        service_name=service_name,
                        project_name=self.get_aws_project_name()
                    )
                )
                ctx.pp.pprint(response)

        @task
        def describe(ctx):
            """Describes Docker repositories for all publishable services."""
            ctx.info('Repositories in ECS Docker registry '
                     'of the "{project_name}" project:'.format(project_name=self.get_aws_project_name()))
            ctx.pp.pprint(self.describe_repositories())

        @task
        def login(ctx):
            """Performs log-in to remote Docker registry."""
            ctx.info('Login to remote Docker registry '
                     'for "{aws_profile}" AWS profile.'.format(aws_profile=self.get_profile()))
            ctx.run("eval $(aws ecr get-login --no-include-email --profile {aws_profile} | sed 's|https://||')"
                    .format(aws_profile=self.get_profile()))

        @task
        def tag(ctx):
            """Tags Docker images according to AWS ECR registry."""
            ctx.info('Tag Docker images according to AWS ECR registry.')

            repositories = self.describe_repositories()

            for service_name in self.config['services']:
                for docker_tag in [self.get_docker_tag(), 'latest']:
                    service_path = self.get_service_path(service_name)
                    repo_uri = repositories[service_path]['repositoryUri']

                    ctx.info('Tag Docker "{service_name}" images with "{repo_uri}:{tag}" tag.'.format(
                        service_name=service_name, repo_uri=repo_uri, tag=docker_tag
                    ))

                    ctx.run('docker tag {project_name}_{service_name}:latest {repo_uri}:{tag}'.format(
                        project_name=self.get_docker_project_name(),
                        service_name=service_name,
                        repo_uri=repo_uri,
                        tag=docker_tag,
                    ))

        @task
        def pull(ctx):
            """Pulls latest Docker images from the AWS ECR registry."""
            ctx.info('Pull latest Docker images from the AWS ECR registry.')

            repositories = self.describe_repositories()

            for service_name in self.config['services']:
                for docker_tag in [self.get_docker_tag(), 'latest']:
                    service_path = self.get_service_path(service_name)
                    repo_uri = repositories[service_path]['repositoryUri']

                    ctx.info(f'Pulling Docker image of "{repo_uri}:{docker_tag}" from the AWS ECR registry.')
                    try:
                        ctx.run(f'docker pull {repo_uri}:{docker_tag}')
                    except UnexpectedExit:
                        ctx.info(f'Docker image "{repo_uri}:{docker_tag}" is missing in the AWS ECR registry.')

        @task
        def push(ctx):
            """Pushes Docker images to AWS ECR registry."""
            ctx.info('Push Docker images to AWS ECR registry.')

            repositories = self.describe_repositories()

            for service_name in self.config['services']:
                for docker_tag in [self.get_docker_tag(), 'latest']:
                    service_path = self.get_service_path(service_name)
                    repo_uri = repositories[service_path]['repositoryUri']

                    ctx.info(f'Push Docker image of "{repo_uri}:{docker_tag}" to AWS ECR registry.')
                    ctx.run(f'docker push {repo_uri}:{docker_tag}')

        @task(login, tag, push)
        def publish(ctx):
            """Logins to AWS ECR registry, tags and pushes Docker containers."""
            ctx.info('Successfully published all images to AWS Elastic Container Registry.')

        @task(login, pull)
        def sync(ctx):
            """Logins to AWS ECR registry, and pulls latest Docker containers."""
            ctx.info('Successfully synced all latest images with AWS Elastic Container Registry.')

        return [create, describe, login, tag, push, pull, publish, sync]


class AwsEcrPluginMixin:
    def get_service_image_uri(self, service_name, docker_tag=None):
        return self.app.plugins['aws_ecr'].get_service_image_uri(service_name, docker_tag)


PLUGIN_CLASS = AwsEcrPlugin
