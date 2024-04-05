from abc import ABC,abstractmethod
import boto3

class Service(ABC):
    """Service ABC, defines a common SG in resources out method
    common to all services
    """

    @property
    @abstractmethod
    def client():
        raise NotImplementedError()
    
    @abstractmethod
    def get_services_in_security_group(security_group_id:str) -> list[dict]:
        raise NotImplementedError()

class EC2(Service):

    client=boto3.client('ec2')
    resource=boto3.resource('ec2')

    @classmethod
    def get_services_in_security_group(cls,security_group_id:str) -> list[dict]:
        instances=[]
    
        service_response=cls.client.describe_instances(
            Filters=[
                {
                    'Name':'instance.group-id',
                    'Values':[
                        f'{security_group_id}'
                    ]
                }
            ]
        )

        if 'nextToken' in service_response.keys():
            next_token=service_response['nextToken']
        else:
            next_token=None

        for reservation in service_response['Reservations']:
            instances.extend(reservation['Instances'])

        while next_token!=None:
            service_response=cls.client.describe_instances(
            Filters=[
                        {
                            'Name':'instance.group-id',
                            'Values':[
                                f'{security_group_id}'
                            ]
                        }
                    ]
                )

            if 'nextToken' in service_response.keys():
                next_token=service_response['nextToken']
            else:
                next_token=None

            for reservation in service_response['reservations']:
                instances.extend(reservation['Instances'])

        return instances

    @classmethod
    def get_network_interfaces_for_security_group(cls,security_group_id) -> list[dict]:
        network_interfaces=cls.client.describe_network_interfaces(
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

    @staticmethod
    def get_service_type_from_network_interface_json(network_interface_json:str) -> Service:
        description=network_interface_json['Description']

        if "arn:aws:ecs" in description:
            return ECS
      
class NonLookupableService(Service):
    """For the different services that can't be queried directly for all
    services corresponding to a given security group.

    These will act the same, but store all their instances/containers etc. beforehand
    so that I can run my own lookup.
    
    This means that I'll only have to do one set of queries for each service.
    """

    services_by_security_group_id:dict[str,list]={}

    @abstractmethod
    def load_services():
        """Loads services to a flat list 
        """
        raise NotImplementedError()

    @classmethod
    def get_services_in_security_group(cls,security_group_id:str)->list[dict]:
        if not cls.has_services():
            cls.load_services()

        return cls.services_by_security_group_id[security_group_id]

    @classmethod
    def has_services(cls):
        return len(cls.services_by_security_group_id.keys())>0        
        
class ECS(NonLookupableService):
    """Deals with lookup for ECS services
    """

    client=boto3.client('ecs')

    ###boto3 docs state ecs client.describe_services can only
    ###take a max of take 10 services at a time
    lookup_batch_size=10

    @classmethod
    def load_services(cls) -> None:
        """Loads services to inherited NonLookupableService.services_by_security_group_id dict
        by iterating through clusters and getting their ARNs to do the same thing for their
        individual services.

        From these service ARNs, I can describe them and log what security group they belong to
        for a later lookup.
        """

        service_arns_by_cluster_arn={}

        cluster_arns=[]

        cluster_arn_response=cls.client.list_clusters()

        if 'nextToken' in cluster_arn_response.keys():
            next_token=cluster_arn_response['nextToken']
        else:
            next_token=None

        cluster_arns.extend(cluster_arn_response['clusterArns'])

        while next_token!=None:
            cluster_arn_response=cls.client.list_clusters(
                nextToken=next_token
            )

            if 'nextToken' in cluster_arn_response.keys():
                next_token=cluster_arn_response['nextToken']
            else:
                next_token=None

            cluster_arns=cluster_arn_response['clusterArns']

        for cluster_arn in cluster_arns:
            service_arns=[]

            service_arn_response=cls.client.list_services(
                cluster=cluster_arn
            )

            if 'nextToken' in service_arn_response.keys():
                next_token=service_arn_response['nextToken']
            else:
                next_token=None

            service_arns.extend(service_arn_response['serviceArns'])

            while next_token!=None:
                service_arn_response=cls.client.list_services(
                    cluster=cluster_arn,
                    nextToken=next_token
                )

                if 'nextToken' in service_arn_response.keys():
                    next_token=service_arn_response['nextToken']
                else:
                    next_token=None
                
                service_arns.extend(service_arn_response['serviceArns'])

            service_arns_by_cluster_arn[cluster_arn]=service_arns

        for cluster_arn in service_arns_by_cluster_arn.keys():

            service_arns=service_arns_by_cluster_arn[cluster_arn]

            service_arns_len=len(service_arns)

            for service_arn_index in range(0,service_arns_len,cls.lookup_batch_size):
                
                if service_arns_len-service_arn_index<cls.lookup_batch_size:
                    service_response=cls.client.describe_services(
                        cluster=cluster_arn,
                        services=service_arns[service_arn_index:]
                    )
                else:
                    service_response=cls.client.describe_services(
                        cluster=cluster_arn,
                        services=service_arns[service_arn_index:cls.lookup_batch_size]
                    )
                
                for service in service_response['services']:
                    security_groups=service['networkConfiguration']['awsvpcConfiguration']['securityGroups']

                    for security_group in security_groups:
                        if security_group not in cls.services_by_security_group_id.keys():
                            cls.services_by_security_group_id[security_group]=[service]
                        else:
                            cls.services_by_security_group_id[security_group].append(service)

        return

class ELB(NonLookupableService):

    client=boto3.client('elbv2')
    
    @classmethod
    def load_services(cls) -> None:
        
        services=[]

        service_response=cls.client.describe_load_balancers()

        if 'NextMarker' in service_response.keys():
            next_token=service_response['NextMarker']
        else:
            next_token=None

        services.extend(service_response['LoadBalancers'])

        while next_token!=None:
            service_response=cls.client.describe_load_balancers(
                Marker=next_token
            )

            if 'NextMarker' in service_response.keys():
                next_token=service_response['NextMarker']
            else:
                next_token=None

            services.extend(service_response['LoadBalancers'])

        for service in services:
            if 'SecurityGroups' in service.keys():
                security_groups=service['SecurityGroups']

                for security_group in security_groups:
                    if security_group not in cls.services_by_security_group_id.keys():
                        cls.services_by_security_group_id[security_group]=[service]
                    else:
                        cls.services_by_security_group_id[security_group].append(service)
                        
        return
    
class RDS(NonLookupableService):
    
    client=boto3.client('rds')
    
    @classmethod
    def load_services(cls)->None:        
        services=[]

        service_response=cls.client.describe_db_instances()

        if 'NextMarker' in service_response.keys():
            next_token=service_response['NextMarker']
        else:
            next_token=None

        services.extend(service_response['DBInstances'])

        while next_token!=None:
            service_response=cls.client.describe_db_instances(
                Marker=next_token
            )

            if 'NextMarker' in service_response.keys():
                next_token=service_response['NextMarker']
            else:
                next_token=None

            services.extend(service_response['DBInstances'])

        for service in services:
            if 'VpcSecurityGroups' in service.keys():
                security_groups=service['VpcSecurityGroups']

                for security_group in security_groups:
                    security_group=security_group['VpcSecurityGroupId']
                    if security_group not in cls.services_by_security_group_id.keys():
                        cls.services_by_security_group_id[security_group]=[service]
                    else:
                        cls.services_by_security_group_id[security_group].append(service)
                        
        return