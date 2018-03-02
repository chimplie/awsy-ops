import uuid

import boto3

import chops.core


class AwsPlugin(chops.core.Plugin):
    name = 'aws'
    required_keys = ['profile', 'project_name']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.boto_session = boto3.Session(profile_name=self.config['profile'])

    def install(self):
        default_settings = {
            'project_id': self.get_new_project_id(),
        }

        self.app.store.set(self.name, {
            **default_settings,
            **self.app.store.get(self.name, {})
        })

    def get_new_project_id(self):
        return '{project_name}-{uuid}'.format(
            project_name=self.config['project_name'],
            uuid=str(uuid.uuid4())[:8]
        )


PLUGIN_CLASS = AwsPlugin
