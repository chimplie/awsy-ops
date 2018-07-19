import os

import chops.core


class TravisPlugin(chops.core.Plugin):
    name = 'bitbucket'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.app.config['build_number'] = os.environ.get('BITBUCKET_BUILD_NUMBER', 'local')


PLUGIN_CLASS = TravisPlugin
