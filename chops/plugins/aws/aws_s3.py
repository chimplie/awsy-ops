from botocore.exceptions import ClientError
from invoke import task

from chops.plugins.aws.aws_envs import AwsEnvsPluginMixin
from chops.plugins.aws.aws_service_plugin import AwsServicePlugin


class AwsS3Plugin(AwsServicePlugin, AwsEnvsPluginMixin):
    name = 'aws_s3'
    dependencies = ['aws', 'aws_envs']
    service_name = 's3'
    required_keys = ['namespace']

    def get_bucket_name(self, app_env=None):
        """
        Returns bucket name for specified or current environment.
        :param app_env: str | None application environment
        :return: str bucket name
        """
        return '{namespace}-{env_name}'.format(
            namespace=self.config['namespace'],
            env_name=app_env or self.get_current_env(),
        )

    def get_bucket_names(self):
        """
        Lists S3 buckets
        :return: str[] bucket names list
        """
        response = self.client.list_buckets()
        assert response['ResponseMetadata']['HTTPStatusCode'] == 200
        return [b['Name'] for b in response['Buckets']]

    def get_bucket_details(self, name):
        """
        Describes S3 bucket details
        :param name: bucket name
        :return: dict bucket info
        """
        bucket = {
            'name': name,
        }

        response = self.client.get_bucket_acl(Bucket=name)
        assert response['ResponseMetadata']['HTTPStatusCode'] == 200
        bucket['acl'] = {
            'Owner': response['Owner'],
            'Grants': response['Grants'],
        }

        try:
            response = self.client.get_bucket_policy(Bucket=name)
            assert response['ResponseMetadata']['HTTPStatusCode'] == 200
            bucket['policy'] = response['Policy']
        except ClientError:
            pass

        response = self.client.get_bucket_location(Bucket=name)
        assert response['ResponseMetadata']['HTTPStatusCode'] == 200
        bucket['location'] = response['LocationConstraint']

        return bucket

    def get_buckets(self):
        """
        Describes available S3 buckets.
        :return: dict[] buckets details
        """
        return {name: self.get_bucket_details(name) for name in self.get_bucket_names()}

    def create_bucket(self, name):
        """
        Creates S3 bucket
        :param name: str log group name
        """
        # We can't specify "us-east-1" as a location constraint since it is the default bucket location.
        # Sounds peculiar? Check https://github.com/boto/boto3/issues/125.
        region = self.get_aws_region()
        extra_args = {} if region == 'us-east-1' else {
            'CreateBucketConfiguration': {'LocationConstraint': region}
        }
        response = self.client.create_bucket(
            ACL='public-read',
            Bucket=name,
            **extra_args,
        )
        assert response['ResponseMetadata']['HTTPStatusCode'] == 200

    def delete_bucket(self, name):
        """
        Deletes S3 bucket
        :param name: str log group name
        """
        response = self.client.delete_bucket(Bucket=name)
        assert 200 <= response['ResponseMetadata']['HTTPStatusCode'] < 300

    def get_tasks(self):
        @task(iterable=['env'])
        def create(ctx, env=None):
            """
            Creates S3 bucket for current or specified environment[s].
            Use --env=* for all environments
            """
            for app_env in self.envs_from_string(env):
                bucket_name = self.get_bucket_name(app_env)
                self.create_bucket(bucket_name)
                ctx.info('Bucket "{}" successfully created.'.format(bucket_name))

        @task(iterable=['env'])
        def delete(ctx, env=None):
            """
            Delete S3 bucket for current or specified environment[s].
            Use --env=* for all environments
            """
            for app_env in self.envs_from_string(env):
                bucket_name = self.get_bucket_name(app_env)
                self.delete_bucket(bucket_name)
                ctx.info('Bucket "{}" successfully deleted.'.format(bucket_name))

        @task(name='list')
        def list_buckets(ctx):
            """
            Lists S3 buckets.
            """
            ctx.info('Available buckets: {}.'.format(self.get_bucket_names()))

        @task
        def describe(ctx):
            """
            Describes S3 buckets.
            """
            ctx.info('Available buckets:')
            ctx.pp.pprint(self.get_buckets())

        return [create, delete, list_buckets, describe]


class AwsS3PluginMixin:
    def get_bucket_name(self):
        return self.app.plugins['aws_s3'].get_bucket_name()


PLUGIN_CLASS = AwsS3Plugin
