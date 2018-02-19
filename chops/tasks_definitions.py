import os
from shutil import copyfile

from invoke import task

from chops import utils


@task
def info(ctx):
    """Shows basic info about chops tools."""
    if ctx.is_initialised:
        ctx.info('Chops (Chimplie Ops) project "{project_name}" at "{project_path}".'.format(
            project_path=ctx.project_path,
            project_name=ctx.project_name,
        ))
    else:
        ctx.info('Chops project is not initialised.')


@task
def version(ctx):
    """Shows chops version."""
    print(utils.version())


@task
def init(ctx):
    """Creates settings file."""
    template_path = os.path.join(utils.TEMPLATES_PATH, 'chops_settings_default.py')
    settings_path = os.path.join(os.getcwd(), 'chops_settings.py')
    copyfile(template_path, settings_path)
    ctx.info('Creating chops settings from template at {settings_path}.'.format(settings_path=settings_path))
