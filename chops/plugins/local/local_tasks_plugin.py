import importlib
import os
import shutil

import chops.core
from chops import utils


class LocalTasksPlugin(chops.core.Plugin):
    name = 'local'
    dependencies = ['dotenv']
    required_keys = ['module']

    def install(self):
        template_path = os.path.join(utils.PLUGINS_PATH, 'local', 'chops_tasks_template.py')

        path_parts = self.config['module'].split('.')
        path_parts[-1] = path_parts[-1] + '.py'
        tasks_module_path = os.path.join(self.app.config['project_path'], *path_parts)

        if not os.path.exists(tasks_module_path):
            self.logger.warning('Creating "{tasks_module_path}"...'.format(tasks_module_path=tasks_module_path))
            shutil.copyfile(template_path, tasks_module_path)

    def get_tasks(self):
        mod = importlib.import_module(self.config['module'])
        return mod.tasks(self.app)


PLUGIN_CLASS = LocalTasksPlugin
