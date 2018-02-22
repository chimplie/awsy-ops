from invoke import task

from chops.plugins.aws.aws_service_plugin import AwsServicePlugin


class AwsEcrPlugin(AwsServicePlugin):
    name = 'aws_ecr'
    dependencies = ['aws', 'docker']
    service_name = 'ecr'

    def get_profile(self):
        return self.app.plugins['aws'].config['profile']

    def get_project_name(self):
        return self.app.plugins['aws'].config['project_name']

    def get_published_services(self):
        return self.app.plugins['docker'].config['published_services']

    def get_docker_tag(self):
        return self.app.plugins['docker'].config['tag']

    def describe_repositories(self):
        repository_names = ['{project_name}/{service_name}'.format(
            service_name=service_name,
            project_name=self.get_project_name()
        ) for service_name in self.get_published_services()]

        response = self.client.describe_repositories(
            repositoryNames=repository_names
        )

        repositories = {}
        for repo_entry in response.get('repositories', []):
            repositories[repo_entry['repositoryName']] = repo_entry
        return repositories

    def get_service_path(self, service_name):
        return '{project_name}/{service_name}'.format(
            project_name=self.get_project_name(),
            service_name=service_name,
        )

    def get_tasks(self):
        @task
        def create(ctx):
            """Creates Docker repositories for all publishable services."""
            for service_name in self.get_published_services():
                ctx.info(
                    'Create repository in ECS Docker registry '
                    'for service_name "{service_name}" '
                    'of the "{project_name}" project:'.format(
                        service_name=service_name,
                        project_name=self.get_project_name()
                    ))
                response = self.client.create_repository(
                    repositoryName='{project_name}/{service_name}'.format(
                        service_name=service_name,
                        project_name=self.get_project_name()
                    )
                )
                ctx.pp.pprint(response)

        @task
        def describe(ctx):
            """Describes Docker repositories for all publishable services."""
            ctx.info('Repositories in ECS Docker registry '
                     'of the "{project_name}" project:'.format(project_name=self.get_project_name()))
            ctx.pp.pprint(self.describe_repositories())

        @task
        def login(ctx):
            """Performs log-in to remote Docker registry."""
            ctx.info('Login to remote Docker registry '
                     'for "{aws_profile}" AWS profile.'.format(aws_profile=self.get_profile()))
            ctx.run('`aws ecr get-login --no-include-email --region us-east-1 --profile {aws_profile}`'
                    .format(aws_profile=self.get_profile()))

        @task
        def tag(ctx):
            """Tags Docker images according to AWS ECR registry."""
            ctx.info('Tag Docker images according to AWS ECR registry.')

            repositories = self.describe_repositories()

            for service_name in self.get_published_services():
                for docker_tag in [self.get_docker_tag(), 'latest']:
                    service_path = self.get_service_path(service_name)
                    repo_uri = repositories[service_path]['repositoryUri']

                    ctx.info('Tag Docker "{service_name}" images with "{repo_uri}:{tag}" tag.'.format(
                        service_name=service_name, repo_uri=repo_uri, tag=docker_tag
                    ))

                    ctx.run('docker tag {project_name}_{service_name}:latest {repo_uri}:{tag}'.format(
                        project_name=self.get_project_name(),
                        service_name=service_name,
                        repo_uri=repo_uri,
                        tag=docker_tag,
                    ))

        @task
        def push(ctx):
            """Pushes Docker images to AWS ECR registry."""
            ctx.info('Push Docker images to AWS ECR registry.')

            repositories = self.describe_repositories()

            for service_name in self.get_published_services():
                for docker_tag in [self.get_docker_tag(), 'latest']:
                    service_path = self.get_service_path(service_name)
                    repo_uri = repositories[service_path]['repositoryUri']

                    ctx.info('Push Docker image of "{repo_uri}:{docker_tag}" to AWS ECR registry.'.format(
                        repo_uri=repo_uri, docker_tag=docker_tag
                    ))

                    ctx.run('docker push {repo_uri}:{docker_tag}'.format(
                        repo_uri=repo_uri,
                        docker_tag=docker_tag
                    ))

        @task(login, tag, push)
        def publish(ctx):
            """Logins to AWS ECR registry, tags and pushes Docker containers."""
            pass

        return [create, describe, login, tag, push, publish]


PLUGIN_CLASS = AwsEcrPlugin
