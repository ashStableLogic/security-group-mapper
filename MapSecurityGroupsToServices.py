from abc import ABC,abstractmethod
import boto3
import pandas as ps

class Service(ABC):

    @abstractmethod
    @staticmethod
    def get_services(NextToken: str|None):
        """Return list of services from client"""
        pass
    
    @abstractmethod
    @staticmethod
    def return_services_in_security_group(services:list,security_group_id:str):
        pass

class EC2(Service):

    client=boto3.client('ec2')
    resource=boto3.resource('ec2')

    @classmethod
    def get_services(NextToken):
        pass

    @classmethod
    def return_services_in_security_group(security_group_id):
        pass

    @classmethod
    def get_network_interfaces_for_security_group(security_group_id) -> list:
        network_interfaces=EC2.client.describe_network_interfaces(
                Filters=[
                    {
                        'Name':'group-id',
                        'Values':[
                            f'{security_group_id}'
                        ]
                    }
                ]
            )['NetworkInterfaces'] 

        return network_interfaces

    def get_service_type_from_network_interface_description(network_interface_description:str) -> Service:
        pass

service_types=[
    "Elasticache",
    "Lambda",
    "EC2",
    "RDS",
    "ALB",
    "ECS"
]

ec2_client=boto3.client('ec2')

# security_group_response=ec2_client.describe_security_groups()

# security_groups=security_group_response['SecurityGroups']

# security_group_map={
#     security_group['GroupId']:[security_group['GroupName']].extend(['']*len(service_types)) for security_group in security_groups
# }

security_groups=[
    {"GroupId":"sg-039f6c6227fc240b7"}
]

for security_group in security_groups:
    ###PLAN

    ##ITERATE THROUGH NETWORK INTERFACES FOR EACH SERVICE GROUP
    ##TO CHECK WHAT SERVICES NEED RETRIEVING
    ##LINEAR SEARCH FOR EACH SERVICE TO MATCH SECURITY GROUPS :(
    
    response=ec2_client.describe_instances(
        Filters=[
            {
                'Name':'instance.group-id',
                'Values':[
                    f'{security_group['GroupId']}'
                ]
            }
        ]
    )

    print(response)