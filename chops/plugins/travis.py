import os

import chops.core


PLUGIN_NAME = 'travis'


class TravisPlugin(chops.core.Plugin):
    name = PLUGIN_NAME
    dependencies = ['travis']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.app.config['build_number'] = os.environ.get('TRAVIS_BUILD_NUMBER', 'local')


PLUGIN_CLASS = TravisPlugin
