from invoke import task

from botocore.exceptions import ClientError

from chops.plugins.aws.aws_envs import AwsEnvsPluginMixin
from chops.plugins.aws.aws_service_plugin import AwsServicePlugin


class AwsEc2Plugin(AwsServicePlugin, AwsEnvsPluginMixin):
    name = 'aws_ec2'
    dependencies = ['aws', 'aws_envs']
    service_name = 'ec2'
    required_keys = ['vpc_name', 'availability_zone_azs', 'security_groups']

    def get_security_group_names(self):
        """
        Returns short names for security groups.
        :return: str security groups short names
        """
        return list(self.config['security_groups'].keys())

    def get_security_group_full_name(self, group_name):
        """
        Returns security group full name.
        :param group_name: str group short name
        :return: str security group name
        """
        base = '{}-{}'.format(
            self.get_aws_project_name(),
            self.get_current_env()
        )
        if group_name == 'default':
            return base
        else:
            return f'{base}-{group_name}'

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

    def get_security_group_config(self, group_name):
        """
        Returns security group config
        :param group_name: str group short name
        :return: dict config
        """
        return self.config['security_groups'][group_name]

    def get_security_group_info(self, group_name=None):
        """
        Returns security group details or None if group with specified name does not exist.
        :param group_name: str security group short name
        :return: dict | None security group info or None
        """
        full_name = self.get_security_group_full_name(group_name)
        try:
            response = self.client.describe_security_groups(
                GroupNames=[full_name],
                Filters=[
                    {
                        'Name': 'vpc-id',
                        'Values': [self.get_vpc_id()],
                    }
                ]
            )
            assert response['ResponseMetadata']['HTTPStatusCode'] == 200

            matching_groups = [group for group in response['SecurityGroups'] if group['GroupName'] == full_name]

            return matching_groups[0]
        except ClientError:
            return None

    def get_security_group_id(self, group_name):
        """
        Returns security group ID or None if group with the specified name does not exist.
        :param group_name: str security group short name
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
        :param group_name: str group short name
        :return: bool whether group exists or not
        """
        return self.get_security_group_info(group_name) is not None

    def create_security_group(self, group_name):
        """
        Creates default security group for the specified name.
        :param group_name: str security group short name
        :return: str security group id
        """
        vpc_id = self.get_vpc_id()
        full_name = self.get_security_group_full_name(group_name)

        response = self.client.create_security_group(
            GroupName=full_name,
            Description='Security group {name} for {env} environment.'.format(
                name=group_name,
                env=self.get_current_env()
            ),
            VpcId=vpc_id
        )
        assert response['ResponseMetadata']['HTTPStatusCode'] == 200
        security_group_id = response['GroupId']

        self.logger.info(f'Security group "{full_name}" (ID={security_group_id}) created in vpc {vpc_id}.')

        config = self.get_security_group_config(group_name)
        ingress_response = self.client.authorize_security_group_ingress(
            GroupId=security_group_id,
            IpPermissions=config['ip_permissions'])
        assert ingress_response['ResponseMetadata']['HTTPStatusCode'] == 200

        for target_config in config.get('attach_to', []).values():
            auth_response = self.client.authorize_security_group_ingress(
                GroupId=target_config['target_group']['id'],
                IpPermissions=[
                    {
                        **target_config['ip_permission'],
                        'UserIdGroupPairs': [
                            {
                                'GroupId': security_group_id,
                            }
                        ],
                    }
                ],
            )
            assert auth_response['ResponseMetadata']['HTTPStatusCode'] == 200

            self.logger.info('Security group {name} attached to {target_name}.'.format(
                name=full_name,
                target_name=target_config['target_group']['id'],
            ))

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
        @task
        def create_security_groups(ctx):
            """
            Creates security groups for current environment.
            """
            for group_name in self.get_security_group_names():
                full_name = self.get_security_group_full_name(group_name)

                if not self.security_group_exists(group_name):
                    security_group_id = self.create_security_group(group_name)
                    ctx.info(f'Security group "{full_name}" ({security_group_id}) successfully created.')
                else:
                    ctx.info(f'Security group "{full_name}" already exists, nothing to create.')

        @task
        def describe_security_groups(ctx):
            """
            Describes security groups for current environment.
            """
            for group_name in self.get_security_group_names():
                security_group_info = self.get_security_group_info(group_name)
                full_name = self.get_security_group_full_name(group_name)

                if security_group_info is not None:
                    ctx.info(f'Security group "{full_name}":')
                    ctx.pp.pprint(security_group_info)
                else:
                    ctx.info(f'Security group "{full_name}" does not exists.')

        @task
        def delete_security_groups(ctx):
            """
            Deletes security groups for current environment.
            """
            for group_name in self.get_security_group_names():
                full_name = self.get_security_group_full_name(group_name)

                if self.security_group_exists(group_name):
                    self.delete_security_group(group_name)
                    ctx.info(f'Security group "{full_name}" successfully deleted.')
                else:
                    ctx.info(f'Security group "{full_name}" does not exists, nothing to delete.')

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
            create_security_groups, describe_security_groups, delete_security_groups,
            describe_availability_zones, describe_all_subnets, list_subnets,
        ]


class AwsEc2PluginMixin:
    def get_security_group_id(self, group_name):
        return self.app.plugins['aws_ec2'].get_security_group_id(group_name)

    def get_subnet_ids(self):
        return self.app.plugins['aws_ec2'].get_subnet_ids()

    def get_vpc_id(self):
        return self.app.plugins['aws_ec2'].get_vpc_id()

    @property
    def ec2_client(self):
        return self.app.plugins['aws_ec2'].client


PLUGIN_CLASS = AwsEc2Plugin
