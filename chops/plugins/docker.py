import os

from invoke import task

import chops.core


class DockerPlugin(chops.core.Plugin):
    name = 'docker'
    dependencies = ['dotenv']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.config['project_name'] = os.environ.get('COMPOSE_PROJECT_NAME', self.config['project_name'])
        self.config['repository_prefix'] = os.environ.get('DOCKER_REPOSITORY_PREFIX', self.config['repository_prefix'])
        self.config['tag'] = os.environ.get('DOCKER_TAG', self.app.config.get('build_number', 'local'))
        self.config['published_services'] = self.config.get('published_services', [])

    def get_docker_command(self, *args: str):
        return 'cd {docker_root} && docker-compose {args}'.format(
            docker_root=self.config['docker_root'],
            args=' '.join(args)
        )

    def get_tasks(self):
        @task
        def build(ctx):
            """Builds docker containers."""
            ctx.info('Build docker containers.')
            ctx.run(self.get_docker_command('build'))

        @task
        def down(ctx):
            """Stops local dockerized application."""
            ctx.info('Stop local dockerized application.')
            ctx.run(self.get_docker_command('down'))

        @task
        def up(ctx):
            """Starts dockerized application locally."""
            ctx.info('Start dockerized application locally.')
            ctx.run(self.get_docker_command('up'))

        @task
        def up_d(ctx):
            """Starts dockerized application locally in background."""
            ctx.info('Start dockerized application locally in background.')
            ctx.run(self.get_docker_command('up', '-d', '--force-recreate', '--remove-orphans', '--no-build'))

        @task
        def version(ctx):
            """Retrieves docker-compose version."""
            ctx.run(self.get_docker_command('--version'))

        @task
        def tag(ctx):
            """Tags Docker images."""
            ctx.info('Tag Docker images.')
            for service in self.config['published_services']:
                for docker_tag in [self.config['tag'], 'latest']:
                    repo_uri = '{repository_prefix}/{service}'.format(
                        service=service,
                        repository_prefix=self.config['repository_prefix'],
                        tag=docker_tag
                    )
                    ctx.info('Tag Docker {service} images with "{repo_uri}:{tag}" tag.'.format(
                        service=service, repo_uri=repo_uri, tag=docker_tag
                    ))
                    ctx.run('docker tag {project_name}_{service}:latest {repo_uri}:{tag}'.format(
                        service=service,
                        project_name=self.config['project_name'],
                        repo_uri=repo_uri,
                        tag=docker_tag,
                    ))

        @task
        def push(ctx):
            """Pushes Docker images to remote registry."""
            ctx.info('Push Docker images to remote registry.')
            for service in self.config['published_services']:
                for docker_tag in [self.config['tag'], 'latest']:
                    ctx.info('Push Docker image of {service}:{docker_tag} to remote registry.'.format(
                        service=service, docker_tag=docker_tag
                    ))
                    ctx.run('docker push {repository_prefix}/{service}:{docker_tag}'.format(
                        service=service,
                        repository_prefix=ctx.docker.repository_prefix,
                        docker_tag=docker_tag
                    ))

        @task(build, tag, push)
        def release(ctx):
            """Builds, tags and pushes Docker containers."""
            pass

        return [build, down, up, up_d, version, tag, push, release]


PLUGIN_CLASS = DockerPlugin
