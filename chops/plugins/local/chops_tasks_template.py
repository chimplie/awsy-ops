from invoke import task

from chops.core import ChopsApplication


def tasks(app: ChopsApplication):
    @task
    def example(ctx):
        """Example local task."""
        ctx.info('This is an example local task for the project "{}".'.format(app.config['project_name']))

        ctx.info('Available tasks:')
        ctx.pp.pprint(app.get_tasks())

        ctx.info('Chops version:')
        app.logger.warn('Executing chops version task...')
        app.run_task('version', ctx)

    return [example]
