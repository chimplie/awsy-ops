from invoke import Collection

from chops import tasks_definitions
from chops.build_config import get_build_config

# Obtain build config
config = get_build_config()


ns = Collection.from_module(tasks_definitions)
ns.configure(config)
