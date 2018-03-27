import importlib
import os
import pprint
from shutil import copyfile
from typing import Dict, List

from invoke import Collection, Program, task
import yaml

from chops.settings_loader import load_chops_settings
from chops.store import Store
from chops import utils


class MissingPluginDependencyError(RuntimeError):
    pass


class IncompletePluginConfigError(RuntimeError):
    pass


class ChopsApplication(object):
    def __init__(self, logger=None):
        self.version: str = utils.version()
        self.config: dict = self.load_config()

        if logger is None:
            logger = utils.get_logger(self.config['project_name'])
        self.logger = logger
        self.pp = pprint.PrettyPrinter(indent=2, width=240, compact=True)

        self.store = Store(
            os.path.join(self.config['project_path'], utils.CHOPS_STORE_FILE),
            self.logger
        )
        self.init_store()

        self.plugins: Dict[Plugin] = {}
        self.load_plugins()
        self.ns: Collection = self.get_root_namespace()

        self.register_plugin_tasks()
        self.ns.configure(self.get_context())
        self.program = Program(namespace=self.ns, version=self.version)

        self.prepare_paths()

    @staticmethod
    def load_config():
        config = dict()

        # Load chops settings
        config = load_chops_settings(config)

        return config

    def prepare_paths(self):
        os.makedirs(self.config['build_path'], exist_ok=True)
        os.makedirs(self.config['log_dir'], exist_ok=True)

    def init_store(self):
        self.store.init('installed_plugins', [])

    def load_plugins(self):
        if not self.config['is_initialised']:
            return

        for name in self.config['plugins']:
            plugin = import_plugin(name, self.config, self, self.logger)
            for dependency in getattr(plugin, 'dependencies', []):
                if dependency not in self.plugins.keys():
                    raise MissingPluginDependencyError(
                        'Plugin "{name}" requires dependency "{dependency}" '
                        'to be loaded before its instantiation.'.format(name=plugin.name, dependency=dependency)
                    )
            self.plugins[plugin.name] = plugin

    def register_plugin_tasks(self):
        if not self.config['is_initialised']:
            return

        for plugin in self.plugins.values():
            plugin.register_tasks(self.ns)

    @staticmethod
    def info(x):
        print('\033[94m' + x + '\033[0m')

    def format(self, *args, **kwargs):
        return self.pp.pformat(*args, **kwargs)

    def dump_yml(self, name, obj):
        with open(os.path.join(self.config['log_dir'], '{}.yml'.format(name)), 'w') as f:
            yaml.dump(obj, f)

    def get_context(self) -> dict():
        context_extras = {
            'app': self,
            'pp': self.pp,
            'info': self.info,
            'logger': self.logger,
        }

        return {**self.config, **context_extras}

    def is_installed(self, plugin):
        return plugin.name not in self.store.get('installed_plugins')

    def install_plugins(self, force_install=False):
        for plugin in self.plugins.values():
            plugin.install_and_register(force_install)

    @staticmethod
    def get_root_namespace() -> Collection:
        @task
        def info(ctx):
            """Shows basic info about chops tools."""
            if ctx.is_initialised:
                ctx.info('Chops (Chimplie Ops) project "{project_name}" at "{project_path}":'.format(
                    project_path=ctx.project_path,
                    project_name=ctx.project_name,
                ))
                ctx.pp.pprint(ctx.app.config)
            else:
                ctx.info('Chops project is not initialised.')

        @task
        def plugins_info(ctx):
            """Shows basic info chops plugins."""
            if ctx.is_initialised:
                ctx.info('Plugins for Chops project "{project_name}" at "{project_path}":'.format(
                    project_path=ctx.project_path,
                    project_name=ctx.project_name,
                ))
                ctx.pp.pprint({k: v.__dict__ for k, v in ctx.app.plugins.items()})
            else:
                ctx.info('Chops project is not initialised.')

        @task
        def version(ctx):
            """Shows chops version."""
            print(ctx.app.version)

        @task
        def init(ctx):
            """Creates settings file."""
            template_path = os.path.join(utils.TEMPLATES_PATH, 'chops_settings_default.py')
            settings_path = os.path.join(os.getcwd(), 'chops_settings.py')
            if not os.path.isfile(settings_path):
                copyfile(template_path, settings_path)
                ctx.info('Chops settings created from template at {settings_path}.'.format(
                    settings_path=settings_path
                ))
            else:
                ctx.info('Chops project already initiated in {settings_path}.'.format(
                    settings_path=settings_path
                ))

        @task
        def install(ctx, force_install=False):
            """Installs chops plugins."""
            ctx.info('Installing chops plugins...')
            ctx.app.install_plugins(force_install=force_install)

        ns = Collection()
        ns.add_task(info)
        ns.add_task(plugins_info)
        ns.add_task(version)
        ns.add_task(init)
        ns.add_task(install)

        return ns


class Plugin(object):
    name = 'ChopsPlugin'
    dependencies: List[str] = []
    required_keys = []

    def __init__(self, config: dict, app: ChopsApplication, logger=None):
        if logger is None:
            logger = utils.get_logger(self.name)

        for key in self.required_keys:
            if key not in config:
                raise IncompletePluginConfigError(
                    'Key "{key}" is missing in "{name}" plugin config: \n{config}'.format(
                        key=key, name=self.name, config=config,
                    ))

        self.config = config
        self.app = app
        self.logger = logger

    def install(self):
        pass

    def install_and_register(self, force_install=False):
        if not self.is_installed() or force_install:
            if self.is_installable():
                self.app.info('Installing plugin "{}"...'.format(self.name))
                self.install()
            self.register()

    def is_installable(self):
        return not getattr(self.install, 'skip', False)

    def is_installed(self):
        return self.app.store.has_item('installed_plugins', self.name)

    def register(self):
        self.app.store.include('installed_plugins', self.name)

    def register_tasks(self, ns: Collection):
        @task
        def info(ctx):
            """Describes plugin."""
            ctx.info('Config for {name} plugin:'.format(name=self.name))
            ctx.pp.pprint(self.config)

        @task
        def install(ctx, force_install=False):
            """Installs plugin."""
            ctx.info('Installing {name} plugin...'.format(name=self.name))
            self.install_and_register(force_install)

        plugin_ns = Collection(self.name)

        plugin_ns.add_task(info)
        if self.is_installable():
            plugin_ns.add_task(install)

        if not self.is_installable() or self.is_installed():
            for t in self.get_tasks():
                plugin_ns.add_task(t)

        ns.add_collection(plugin_ns)

    def get_tasks(self):
        return []


# Mark `install` method as skipped which means that plugin is not installable:
Plugin.install.skip = True


def import_plugin(name: str, config: dict, app: ChopsApplication, logger) -> Plugin:
    mod = importlib.import_module(name)
    plugin_class: Plugin = mod.PLUGIN_CLASS
    return plugin_class(config[plugin_class.name], app, logger)
