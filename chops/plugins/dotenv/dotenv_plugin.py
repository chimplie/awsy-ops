import filecmp
import os
import shutil

from dotenv import load_dotenv
from invoke import task

import chops.core
from chops import utils


class DotEnvPlugin(chops.core.Plugin):
    name = 'dotenv'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if os.path.isfile(self.config['env_files']['main_dotenv_path']):
            load_dotenv(self.config['env_files']['main_dotenv_path'])

    def install(self):
        dotenv_file_paths = list(self.config['env_files'].values())
        dotenv_file_paths.append(self.config['template_lock'])

        for dotenv_path in dotenv_file_paths:
            if not os.path.exists(dotenv_path):
                self.logger.warning('Creating "{dotenv_path}"...'.format(dotenv_path=dotenv_path))
                shutil.copyfile(self.config['template'], dotenv_path)

        if not filecmp.cmp(self.config['template'], self.config['template_lock']):
            self.logger.error('Template file ({filename}) was changed during the last run!'.format(
                filename=self.config['template']
            ))
            exit(-1)

    def get_tasks(self):
        @task
        def show_env(ctx):
            """Prints environment variables."""
            ctx.info('Print environment variables.')
            ctx.run('env')

        return [show_env]


PLUGIN_CLASS = DotEnvPlugin
