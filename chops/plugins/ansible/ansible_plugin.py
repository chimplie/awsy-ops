import chops.core


class AnsiblePlugin(chops.core.Plugin):
    name = 'ansible'
    dependencies = ['dotenv']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        raise NotImplementedError('Ansible Chops plugin is not implemented!')

    def get_tasks(self):
        return []


PLUGIN_CLASS = AnsiblePlugin
