import importlib
import logging

from invoke import Collection, task


class Plugin(object):
    name = 'ChopsPlugin'

    def __init__(self, config, app, logger=None):
        if logger is None:
            logger = logging.getLogger(self.name)

        self.config = config
        self.app = app
        self.logger = logger

    def install(self):
        pass

    def register_tasks(self, ns: Collection):
        @task
        def info(ctx):
            """Describes plugin."""
            ctx.info('Config for {name} plugin:'.format(name=self.name))
            ctx.pp.pprint(self.config)

        @task
        def install(ctx):
            """Installs plugin."""
            ctx.info('Installing {name} plugin...'.format(name=self.name))
            self.install()

        plugin_ns = Collection(self.name)

        plugin_ns.add_task(info)
        plugin_ns.add_task(install)

        for t in self.get_tasks():
            plugin_ns.add_task(t)

        ns.add_collection(plugin_ns)

    def get_tasks(self):
        return []


def import_plugin(name: str, config: dict, app) -> Plugin:
    mod = importlib.import_module(name)
    plugin_class: Plugin = mod.PLUGIN_CLASS
    return plugin_class(config[plugin_class.name], app)
