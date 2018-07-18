from invoke import task

from botocore.exceptions import ClientError

from chops.plugins.aws.aws_envs import AwsEnvsPluginMixin
from chops.plugins.aws.aws_service_plugin import AwsServicePlugin


class AwsEc2Plugin(AwsServicePlugin, AwsEnvsPluginMixin):
    name = 'aws_ec2'
    dependencies = ['aws', 'aws_envs']
    service_name = 'ec2'
    required_keys = ['vpc_name', 'availability_zone_azs']

    def get_security_group_name(self, env=None):
        """
        Returns security group name.
        :param env: str | None environment name
        :return: str security group name
        """
        return '{}-{}'.format(
            self.get_aws_project_name(),
            env or self.get_current_env()
        )

    def get_vpc_id(self):
        """
        Returns project VPC ID
        :return: str VPC ID
        """
        response = self.client.describe_vpcs(
            Filters=[
                {
                    'Name': 'tag:Name',
                    'Values': [self.config['vpc_name']],
                },
            ]
        )
        assert response['ResponseMetadata']['HTTPStatusCode'] == 200

        return response['Vpcs'][0]['VpcId']

    def get_security_group_info(self, group_name=None):
        """
        Returns security group details or None if group with specified name does not exist.
        :param group_name: str security group name
        :return: dict | None security group info or None
        """
        try:
            response = self.client.describe_security_groups(
                GroupNames=[group_name],
                Filters=[
                    {
                        'Name': 'vpc-id',
                        'Values': [self.get_vpc_id()],
                    }
                ]
            )
            assert response['ResponseMetadata']['HTTPStatusCode'] == 200

            matching_groups = [group for group in response['SecurityGroups'] if group['GroupName'] == group_name]

            return matching_groups[0]
        except ClientError:
            return None

    def get_security_group_id(self, group_name):
        """
        Returns security group ID or None if group with the specified name does not exist.
        :param group_name: str security group name
        :return: str | None group ID or None
        """
        security_group_info = self.get_security_group_info(group_name)
        if security_group_info is None:
            return None
        else:
            return security_group_info['GroupId']

    def security_group_exists(self, group_name):
        """
        Returns whether security group with the specified name exists.
        :param group_name: str group name
        :return: bool whether group exists or not
        """
        return self.get_security_group_info(group_name) is not None

    def create_security_group(self, group_name):
        """
        Creates default security group for the specified name.
        :param group_name: str security group name
        :return: str security group id
        """
        response = self.client.create_security_group(
            GroupName=group_name,
            Description='Default security group {}.'.format(self.get_security_group_name()),
            VpcId=self.get_vpc_id()
        )
        assert response['ResponseMetadata']['HTTPStatusCode'] == 200
        security_group_id = response['GroupId']

        self.logger.info('Security Group Created {group} in vpc {vpc}.'.format(
            group=security_group_id,
            vpc=self.get_vpc_id(),
        ))

        ingress_response = self.client.authorize_security_group_ingress(
            GroupId=security_group_id,
            IpPermissions=[
                {
                    'IpProtocol': 'tcp',
                    'FromPort': 80,
                    'ToPort': 80,
                    'IpRanges': [{'CidrIp': '0.0.0.0/0'}],
                },
            ])
        assert ingress_response['ResponseMetadata']['HTTPStatusCode'] == 200

        return security_group_id

    def delete_security_group(self, group_name):
        """
        Deletes security group specified by its name.
        :param group_name: str group name
        """
        response = self.client.delete_security_group(
            GroupId=self.get_security_group_id(group_name),
        )
        assert response['ResponseMetadata']['HTTPStatusCode'] == 200

    def get_availability_zones_info(self):
        """
        Returns availability zones details for the default session.
        :return: dict zones details
        """
        response = self.client.describe_availability_zones()
        assert response['ResponseMetadata']['HTTPStatusCode'] == 200

        zones = {}
        for zone in response['AvailabilityZones']:
            zones[zone['ZoneName']] = {
                'name': zone['ZoneName'],
                'region': zone['RegionName'],
                'state': zone['State'],
            }

        return zones

    def get_availability_zones(self):
        """
        Returns availability zones names defined in the `availability_zone_azs` plugin config section.
        :return: str[] zone names
        """
        zones_info = self.get_availability_zones_info()
        letters = self.config['availability_zone_azs']

        zones = []
        for zone_name in zones_info:
            for letter in letters:
                if zone_name.endswith(letter):
                    zones.append(zone_name)

        return zones

    def get_subnets_info(self):
        """
        Returns subnets details for the current VPC
        :return: dict subnets details
        """
        response = self.client.describe_subnets(
            Filters=[
                {
                    'Name': 'vpc-id',
                    'Values': [self.get_vpc_id()]
                }
            ]
        )
        assert response['ResponseMetadata']['HTTPStatusCode'] == 200

        return response['Subnets']

    def get_availability_zones_subnets(self):
        """
        Returns 1 subnet per each enabled availability zone.
        :return:
        """
        zones = self.get_availability_zones()
        subnets_info = self.get_subnets_info()

        subnets = {}
        for subnet_details in subnets_info:
            for zone_name in zones:
                if subnet_details['DefaultForAz'] and subnet_details['AvailabilityZone'] == zone_name:
                    subnets[zone_name] = subnet_details

        return subnets

    def get_subnet_ids(self):
        """
        Returns subnet IDs for default subnets of enabled availability zones.
        :return: str[] subnet ids
        """
        return [subnet['SubnetId'] for subnet in self.get_availability_zones_subnets().values()]

    def get_tasks(self):
        @task(iterable=['env'])
        def create_security_group(ctx, env=None):
            """
            Creates security group for current or specified environment[s].
            Use --env=* for all environments
            """
            for app_env in self.envs_from_string(env):
                security_group_name = self.get_security_group_name(app_env)

                if not self.security_group_exists(security_group_name):
                    security_group_id = self.create_security_group(security_group_name)
                    ctx.info('Security group "{name}" (id) successfully created.'.format(
                        name=security_group_name,
                        id=security_group_id,
                    ))
                else:
                    ctx.info('Security group "{}" already exists, nothing to create.'.format(security_group_name))

        @task(iterable=['env'])
        def describe_security_group(ctx, env=None):
            """
            Describes security group for current or specified environment[s].
            Use --env=* for all environments
            """
            for app_env in self.envs_from_string(env):
                security_group_name = self.get_security_group_name(app_env)
                security_group_info = self.get_security_group_info(security_group_name)

                if security_group_info is not None:
                    ctx.info('Security group "{}":'.format(security_group_name))
                    ctx.pp.pprint(security_group_info)
                else:
                    ctx.info('Security group "{}" does not exists.'.format(security_group_name))

        @task(iterable=['env'])
        def delete_security_group(ctx, env=None):
            """
            Deletes security group for current or specified environment[s].
            Use --env=* for all environments
            """
            for app_env in self.envs_from_string(env):
                security_group_name = self.get_security_group_name(app_env)

                if self.security_group_exists(security_group_name):
                    self.delete_security_group(security_group_name)
                    ctx.info('Security group "{}" successfully deleted.'.format(security_group_name))
                else:
                    ctx.info('Security group "{}" does not exists, nothing to delete.'.format(security_group_name))

        @task
        def describe_availability_zones(ctx):
            """Describes availability zones"""
            data = self.get_availability_zones_info()
            ctx.info('Availability zones:')
            ctx.pp.pprint(data)

        @task
        def describe_all_subnets(ctx):
            """Describes availability zones"""
            data = self.get_subnets_info()
            ctx.info('Available subnets:')
            ctx.pp.pprint(data)

        @task
        def list_subnets(ctx):
            """Lists default subnets for enabled availability zones"""
            data = self.get_availability_zones_subnets()
            ctx.info('Defaults subnets:')
            ctx.pp.pprint(data)

        return [
            create_security_group, describe_security_group, delete_security_group,
            describe_availability_zones, describe_all_subnets, list_subnets,
        ]


class AwsEc2PluginMixin:
    def get_security_group_name(self, env=None):
        return self.app.plugins['aws_ec2'].get_security_group_name(env)

    def get_security_group_id(self, env=None):
        return self.app.plugins['aws_ec2'].get_security_group_id(self.get_security_group_name(env))

    def get_subnet_ids(self):
        return self.app.plugins['aws_ec2'].get_subnet_ids()

    def get_vpc_id(self):
        return self.app.plugins['aws_ec2'].get_vpc_id()

    @property
    def ec2_client(self):
        return self.app.plugins['aws_ec2'].client


PLUGIN_CLASS = AwsEc2Plugin
