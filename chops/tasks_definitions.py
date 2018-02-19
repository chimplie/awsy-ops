from invoke import task

from chops import helpers


@task
def info(ctx):
    """Shows basic info about chops tools."""
    ctx.info('Chops (Chimplie Ops) toolset of {version}.'.format(version=helpers.version()))
