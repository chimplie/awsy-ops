import filecmp
import os
import shutil

from dotenv import load_dotenv
from invoke import task

import chops.core


class DotEnvPlugin(chops.core.Plugin):
    name = 'dotenv'
    required_keys = ['dotenv_file', 'template', 'template_lock']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if os.path.isfile(self.config['dotenv_file']):
            load_dotenv(self.config['dotenv_file'])

        if self.is_installed():
            self.check_template_integrity()
            self.ensure_paths()

    def install(self):
        dotenv_path = self.config['dotenv_file']
        template_path = self.config['template']
        lock_path = self.config['template_lock']

        for file_path in [dotenv_path, lock_path]:
            if not os.path.exists(file_path):
                shutil.copyfile(template_path, file_path)
                self.logger.warning(f'Created "{file_path}" dotenv file.')
            else:
                self.logger.warning(f'Dotenv file "{file_path}" already exists, skipping.')

        self.check_template_integrity()
        self.ensure_paths()

    def check_template_integrity(self):
        if not filecmp.cmp(self.config['template'], self.config['template_lock']):
            self.logger.error('Template file ({filename}) was changed during the last run!'.format(
                filename=self.config['template']
            ))
            exit(-1)

    def ensure_paths(self):
        dotenv_path = self.config['dotenv_file']

        if not os.path.exists(dotenv_path):
            return

        for symlink_path in self.config.get('symlink_paths', []):
            if not os.path.exists(symlink_path):
                os.symlink(dotenv_path, symlink_path)
                self.logger.warning(f'Created symlink for {dotenv_path} at {symlink_path}.')
            elif os.path.islink(symlink_path):
                self.logger.debug(f'Symlink already exists at {symlink_path}.')
            else:
                self.logger.error(f'File {symlink_path} should be a symlink.')

    def get_tasks(self):
        @task
        def show_env(ctx):
            """Prints environment variables."""
            ctx.info('Print environment variables.')
            ctx.run('env')

        return [show_env]


PLUGIN_CLASS = DotEnvPlugin
