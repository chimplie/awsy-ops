import filecmp
import os
import shutil

from dotenv import load_dotenv

import chops.core


PLUGIN_NAME = 'dotenv'


class DotEnvPlugin(chops.core.Plugin):
    name = PLUGIN_NAME

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

        load_dotenv(self.config['env_files']['main_dotenv_path'])


PLUGIN_CLASS = DotEnvPlugin
