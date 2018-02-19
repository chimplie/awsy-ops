from invoke import Collection

from chops import tasks_definitions
from chops.config import get_config
from chops.plugin import register_plugin_tasks

# Obtain config
config = get_config()

# Create namespace and register tasks
ns = Collection.from_module(tasks_definitions)
register_plugin_tasks(ns, config)

# Configure namespace
ns.configure(config)
