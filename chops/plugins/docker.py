import os

from invoke import task

import chops.core


class DockerPlugin(chops.core.Plugin):
    name = 'docker'
    dependencies = ['dotenv']
    required_keys = ['docker_root', 'project_name']

    def get_tag(self):
        return os.environ.get('DOCKER_TAG', self.app.config.get('build_number', 'local'))

    def get_docker_command(self, *args: str):
        return 'cd {docker_root} && DOCKER_TAG={tag} docker-compose {params} {args}'.format(
            docker_root=self.config['docker_root'],
            params=' '.join([
                '--project-name={}'.format(self.config['project_name'])
            ]),
            args=' '.join(args),
            tag=self.get_tag(),
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

        return [build, down, up, up_d, version]


class DockerPluginMixin:
    def get_docker_project_name(self):
        return self.app.plugins['docker'].config['project_name']

    def get_docker_tag(self):
        return self.app.plugins['docker'].get_tag()


PLUGIN_CLASS = DockerPlugin
