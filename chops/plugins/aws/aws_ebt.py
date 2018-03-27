import os
import zipfile

from invoke import task

from chops.plugins.aws.aws_service_plugin import AwsServicePlugin
from chops.utils import create_id, create_simple_id, short_uuid


class AwsEbtPlugin(AwsServicePlugin):
    name = 'aws_ebt'
    dependencies = ['aws', 'aws_envs']
    service_name = 'elasticbeanstalk'
    required_keys = ['app_name']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.s3_client = self.aws_plugin.boto_session.client('s3')
        self.iam_client = self.aws_plugin.boto_session.client('iam')

    def install(self):
        self.allow_instances_to_pull_from_ecr_repos()

    def envs_from_string(self, value):
        return self.app.plugins['aws_envs'].envs_from_string(value)

    def create_app_bucket(self, bucket):
        response = self.s3_client.create_bucket(
            ACL='bucket-owner-full-control',
            Bucket=bucket['name'],
        )

        self.logger.info('Created Elastic Beanstalk application S3 bucket: \n{}'.format(self.app.format(response)))
        self.app.store.set('aws_ebt.app_bucket', bucket)

    def delete_app_bucket(self):
        if not self.app.store.has('aws_ebt.app_bucket'):
            return

        bucket = self.app.store.get('aws_ebt.app_bucket')
        response = self.s3_client.delete_bucket(
            Bucket=bucket['name'],
        )

        self.logger.info('Deleted Elastic Beanstalk application S3 bucket: \n{}'.format(self.app.format(response)))
        self.app.store.delete('aws_ebt.app_bucket')

    def get_app_bucket(self):
        if self.app.store.has('aws_ebt.app_bucket'):
            return self.app.store.get('aws_ebt.app_bucket')
        else:
            bucket = {
                'name': create_id(self.config['app_name']),
            }
            self.create_app_bucket(bucket)
            return bucket

    def get_app_bucket_name(self):
        return self.get_app_bucket()['name']

    def allow_instances_to_pull_from_ecr_repos(self):
        response = self.iam_client.attach_role_policy(
            RoleName='aws-elasticbeanstalk-ec2-role',
            PolicyArn='arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly'
        )
        self.logger.info('Add policy to allow Elastic Beanstalk instances to read from ECR: {}'.format(response))

    def list_stacks(self):
        response = self.client.list_available_solution_stacks()
        self.logger.info('Available Elastic Beanstalk solution stacks: \n{}'.format(self.app.format(response)))

    def create_app(self):
        response = self.client.create_application(
            ApplicationName=self.config['app_name'],
        )
        self.logger.info('Created Elastic Beanstalk application: \n{}'.format(self.app.format(response)))
        self.logger.info('Created Elastic Beanstalk application "{app_name}" bucket is "{bucket_name}".'.format(
            app_name=self.config['app_name'],
            bucket_name=self.get_app_bucket()['name'],
        ))

    def get_full_env_name(self, env_name):
        return create_simple_id('{app_name}-{env_name}'.format(
            app_name=self.config['app_name'],
            env_name=env_name,
        ))

    def create_environment(self, env_name, version):
        if self.app.store.has('aws_ebt.environments.{}'.format(env_name)):
            raise RuntimeError('Elastic Beanstalk environment "{}" already exists.'.format(env_name))

        self.app.store.init('aws_ebt.environments', {})
        full_env_name = self.get_full_env_name(env_name)
        self.app.store.set('aws_ebt.environments.{}'.format(env_name), {
            'name': full_env_name,
        })

        response = self.client.create_environment(
            ApplicationName=self.config['app_name'],
            EnvironmentName=full_env_name,
            Tier={
                'Name': 'WebServer',
                'Type': 'Standard',
                'Version': '1.0',
            },
            SolutionStackName='64bit Amazon Linux 2017.09 v2.8.4 running Multi-container Docker 17.09.1-ce (Generic)',
            VersionLabel=version,
            OptionSettings=[
                {
                    'Namespace': 'aws:autoscaling:launchconfiguration',
                    'OptionName': 'InstanceType',
                    'Value': 't2.nano',
                },
                {
                    'Namespace': 'aws:autoscaling:updatepolicy:rollingupdate',
                    'OptionName': 'RollingUpdateType',
                    'Value': 'Health',
                },
                {
                    'Namespace': 'aws:autoscaling:updatepolicy:rollingupdate',
                    'OptionName': 'RollingUpdateEnabled',
                    'Value': True,
                },
                {
                    "Namespace": "aws:elasticbeanstalk:application",
                    "OptionName": "Application Healthcheck URL",
                    "Value": "/"
                },
                {
                    'Namespace': 'aws:elasticbeanstalk:command',
                    'OptionName': 'DeploymentPolicy',
                    'Value': 'Rolling',
                },
                {
                    'Namespace': 'aws:elasticbeanstalk:command',
                    'OptionName': 'BatchSize',
                    'Value': '30',
                }
            ],
        )

        self.logger.info('Created Elastic Beanstalk environment "{env_name}": \n{response}'.format(
            env_name=response,
            response=self.app.format(response),
        ))

    @staticmethod
    def get_new_version_value():
        return short_uuid()

    def get_version_object_key(self, version):
        return 'Versions/{app_name}-{version}.zip'.format(
            app_name=self.config['app_name'],
            version=version,
        )

    def get_bundle_path(self):
        return os.path.join(
            self.app.config['build_path'],
            '{}.eb.bundle.zip'.format(self.config['app_name'])
        )

    def create_app_bundle(self):
        bundle_path = self.get_bundle_path()

        if os.path.exists(bundle_path):
            os.unlink(bundle_path)

        with zipfile.ZipFile(bundle_path, 'w') as myzip:
            for filename in ['Dockerrun.aws.json']:
                myzip.write(os.path.join(self.app.config['build_path'], filename), filename)

    def upload_new_version(self, version):
        bucket_name = self.get_app_bucket_name()
        s3_key = self.get_version_object_key(version)

        self.s3_client.upload_file(
            self.get_bundle_path(),
            bucket_name,
            s3_key,
        )

        self.logger.info('Uploaded new Elastic Beanstalk application version to "{bucket_name}/{s3_key}".'.format(
            bucket_name=bucket_name,
            s3_key=s3_key,
        ))

    def create_app_version(self):
        version = self.get_new_version_value()

        self.create_app_bundle()
        self.upload_new_version(version)

        response = self.client.create_application_version(
            ApplicationName=self.config['app_name'],
            VersionLabel=version,
            Description='Application "{app_name}" version "{version}".'.format(
                app_name=self.config['app_name'],
                version=version,
            ),
            SourceBundle={
                'S3Bucket': self.get_app_bucket_name(),
                'S3Key': self.get_version_object_key(version),
            },
            AutoCreateApplication=False,
            Process=True,
        )

        self.logger.info('Created Elastic Beanstalk application version: \n{}'.format(self.app.format(response)))

        return version

    def get_application_versions(self):
        response = self.client.describe_application_versions(
            ApplicationName=self.config['app_name']
        )
        return response['ApplicationVersions']

    def get_latest_app_version(self):
        sorted_versions = self.get_application_versions()
        sorted_versions.sort(key=lambda x: x['DateUpdated'])

        if len(sorted_versions) > 0:
            return sorted_versions[-1]
        else:
            return None

    def get_environments(self) -> dict:
        response = self.client.describe_environments(
            ApplicationName=self.config['app_name'],
        )
        environments = {}

        for env_description in response['Environments']:
            env_name = env_description['EnvironmentName']
            env = {
                'description': env_description,
            }

            # Configuration setting:
            response = self.client.describe_configuration_settings(
                ApplicationName=self.config['app_name'],
                EnvironmentName=env_name,
            )
            env['configuration_settings'] = response['ConfigurationSettings']

            # Resources:
            response = self.client.describe_environment_resources(
                EnvironmentName=env_name,
            )
            env['environment_resources'] = response['EnvironmentResources']

            # Save environment data
            environments[env_name] = env

        return environments

    def get_tasks(self):
        @task
        def create(ctx):
            """Creates Elastic Beanstalk application."""
            ctx.info('Creating Elastic Beanstalk application "{}"...'.format(self.config['app_name']))
            self.create_app()

        @task
        def create_app_version(ctx):
            """Creates Elastic Beanstalk application version."""
            ctx.info('Creating the new Elastic Beanstalk application "{app_name}" version.'.format(
                app_name=self.config['app_name'],
            ))
            self.create_app_version()

        @task(iterable=['env'])
        def create_env(ctx, env=None, version=None):
            """Creates Elastic Beanstalk environment."""
            if version is None:
                version = self.get_latest_app_version()['VersionLabel']

            for env_name in self.envs_from_string(env):
                ctx.info('Creating Elastic Beanstalk environment "{env_name}" for "{app_name}" application.'.format(
                    env_name=env_name, app_name=self.config['app_name'],
                ))
                self.create_environment(env_name, version)

        @task
        def describe_versions(ctx):
            """Describes Elastic Beanstalk application versions."""
            ctx.info('Elastic Beanstalk application "{}" versions:'.format(self.config['app_name']))
            self.app.pp.pprint(self.get_application_versions())

        @task
        def describe_envs(ctx):
            """Describes Elastic Beanstalk application environments."""
            ctx.info('Elastic Beanstalk application "{}" environments:'.format(self.config['app_name']))
            envs = self.get_environments()
            self.app.pp.pprint(envs)
            for env_name, data in envs.items():
                self.app.dump_yml(env_name, data)

        @task
        def stacks(ctx):
            """Lists Elastic Beanstalk solution stalks."""
            ctx.info('Listing Elastic Beanstalk solution stalks...')
            self.list_stacks()

        return [create, create_app_version, create_env, describe_versions, describe_envs, stacks]


PLUGIN_CLASS = AwsEbtPlugin
