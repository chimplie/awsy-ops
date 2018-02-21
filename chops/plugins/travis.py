import os

import chops.core


class TravisPlugin(chops.core.Plugin):
    name = 'travis'
    dependencies = ['travis']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.app.config['build_number'] = os.environ.get('TRAVIS_BUILD_NUMBER', 'local')


PLUGIN_CLASS = TravisPlugin
