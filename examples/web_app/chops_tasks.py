from invoke import task


def tasks(app, logger):
    @task
    def example(ctx):
        """Example local task."""
        ctx.info('This is an example local task for the project "{}".'.format(app.config['project_name']))

        ctx.info('Available tasks:')
        ctx.pp.pprint(app.program.collection.task_names)

        ctx.info('Chops version:')
        logger.warn('Executing chops version task...')
        app.program.collection.tasks['version'](ctx)

    return [example]
