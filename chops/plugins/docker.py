import os

from invoke import task

import chops.plugin


PLUGIN_NAME = 'docker'


class DockerPlugin(chops.plugin.Plugin):
    name = PLUGIN_NAME

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.config['project_name'] = os.environ.get('COMPOSE_PROJECT_NAME', self.config['project_name'])
        self.config['repository_prefix'] = os.environ.get('DOCKER_REPOSITORY_PREFIX', self.config['repository_prefix'])
        self.config['tag'] = os.environ.get('DOCKER_TAG')

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

        return [build, down, up, up_d]


PLUGIN_CLASS = DockerPlugin
