import importlib
import logging

from invoke import Collection


class Plugin(object):
    name = 'ChopsPlugin'
    tasks = []

    def __init__(self, config, logger=None):
        if logger is None:
            logger = logging.getLogger(self.name)

        self.config = config
        self.logger = logger

    def install(self):
        pass

    def register_tasks(self, ns: Collection):
        plugin_ns = Collection(self.name)
        for t in self.tasks:
            plugin_ns.add_task(getattr(self, t))
        ns.add_collection(plugin_ns)


def import_plugin(name: str, config: dict) -> Plugin:
        mod = importlib.import_module(name)
        plugin_class: Plugin = mod.PLUGIN_CLASS
        return plugin_class(config[plugin_class.name])


def load_plugins(config: dict):
    if not config['is_initialised']:
        return

    config['plugins'] = {}

    for name in config['loaded_plugins']:
        plugin = import_plugin(name, config)
        config['plugins'][plugin.name] = plugin
        plugin.install()


def register_plugin_tasks(ns: Collection, config: dict):
    if not config['is_initialised']:
        return

    for plugin in config['plugins'].values():
        plugin.register_tasks(ns)
