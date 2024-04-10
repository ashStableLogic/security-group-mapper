from abc import ABC,abstractmethod
import boto3

class Service(ABC):
    """Service ABC, defines a common 1:m SG in -> services out method
    common to all services
    """

    @property
    @abstractmethod
    def client():
        raise NotImplementedError()
    
    @abstractmethod
    def set_client_region(region_name: str) -> None:
        raise NotImplementedError()
    
    @abstractmethod
    def get_services_in_security_group(security_group:dict) -> list[dict]:
        raise NotImplementedError()
    
    @abstractmethod
    def get_service_names_in_security_group(security_group: dict)->list[str]:
        raise NotImplementedError() 

class EC2(Service):

    client=boto3.client('ec2')
    resource=boto3.resource('ec2')
    
    @classmethod
    def set_client_region(cls,region_name: str) -> None:
        cls.client=boto3.client('ec2',region_name=region_name)
    
    @classmethod
    def get_service_names_in_security_group(cls,security_group: dict)->list[str]:
        services=cls.get_services_in_security_group(security_group)
                
        service_names=[]
        
        for service in services:
            tags=service['Tags']
            
            service_names.extend([tag['Value'] for tag in tags if tag['Key']=='Name'])
        
        return service_names

    @classmethod
    def get_services_in_security_group(cls,security_group:dict) -> list[dict]:
        instances=[]
        
        security_group_id=security_group['GroupId']
    
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
    def get_security_groups(cls)-> list[dict]:
        security_groups=[]
        
        response=cls.client.describe_security_groups()
        
        security_groups.extend(response['SecurityGroups'])
        
        if 'NextToken' in response.keys():
            next_token=response['NextToken']
        else:
            next_token=None
        
        while next_token!=None:
            response=cls.client.describe_security_groups(
                NextToken=next_token
            )
        
            security_groups.extend(response['SecurityGroups'])
            
            if 'NextToken' in response.keys():
                next_token=response['NextToken']
            else:
                next_token=None
                
        return security_groups

    @classmethod
    def get_network_interfaces_for_security_group(cls,security_group: dict) -> list[dict]:
        security_group_id=security_group['GroupId']
        
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
    def get_service_types_from_network_interfaces(network_interface_jsons:list[str]) -> set[Service]:
        services_to_lookup=set()            
        for network_interface_json in network_interface_jsons:
            
            interface_type=network_interface_json['InterfaceType']
            description=network_interface_json['Description']
            security_groups=network_interface_json['Groups']
            
            instance_id=None
            
            if 'Attachment' in network_interface_json.keys():
                if 'InstanceId' in network_interface_json['Attachment'].keys():
                    instance_id=network_interface_json['Attachment']['InstanceId']

            if interface_type=="lambda":
                services_to_lookup.add(Lambda)
            elif any(["ElasticMapReduce" in security_group['GroupName'] for security_group in security_groups]):
                services_to_lookup.add(EMR)
            elif instance_id!=None:
                services_to_lookup.add(EC2)
            elif "arn:aws:ecs" in description:
                services_to_lookup.add(ECS)
            elif "ELB app" in description:
                services_to_lookup.add(ALB)
            elif "RDSNetworkInterface" in description:
                services_to_lookup.add(RDS)
            elif "DMSNetworkInterface" in description:
                services_to_lookup.add(DMS)
            elif "RedshiftNetworkInterface" in description:
                services_to_lookup.add(Redshift)            
            elif "ElastiCache" in description:
                services_to_lookup.add(ElastiCache)

            
        return services_to_lookup
      
class NonLookupableService(Service):
    """For the different services that can't be queried directly for all
    services corresponding to a given security group.

    These will act the same, but store all their instances/containers etc. beforehand
    so that you can run your own lookup.
    
    This means that you'll only have to do one set of queries for each service.
    """

    @property
    @abstractmethod
    def services_by_security_group_id():
        raise NotImplementedError()

    @abstractmethod
    def load_services():
        """Loads services to a flat list 
        """
        raise NotImplementedError()
    
    @abstractmethod
    def get_service_names_in_security_group(cls,security_group: dict)->list[str]:
        raise NotImplementedError()

    @classmethod
    def get_services_in_security_group(cls,security_group:list[dict])->list[dict]:
        security_group_id=security_group['GroupId']
        
        if not cls.has_services():
            cls.load_services()

        if security_group_id in cls.services_by_security_group_id.keys():
            services=cls.services_by_security_group_id[security_group_id]
        else:
            services=[]
        
        return services

    @classmethod
    def has_services(cls):
        return len(cls.services_by_security_group_id.keys())>0        
        
class ECS(NonLookupableService):
    """Deals with lookup for ECS services
    """

    client=boto3.client('ecs')
    services_by_security_group_id:dict[str,list]={}

    ###boto3 docs state ecs client.describe_services can only
    ###take a max of take 10 services at a time
    lookup_batch_size=10
    
    @classmethod
    def set_client_region(cls,region_name: str) -> None:
        cls.client=boto3.client('ecs',region_name=region_name)

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

    @classmethod
    def get_service_names_in_security_group(cls,security_group: dict)->list[str]:
        services=cls.get_services_in_security_group(security_group)
        
        service_names=[service['serviceName'] for service in services]
        
        return service_names

class ALB(NonLookupableService):

    client=boto3.client('elbv2')
    services_by_security_group_id:dict[str,list]={}
    
    @classmethod
    def set_client_region(cls,region_name: str) -> None:
        cls.client=boto3.client('elbv2',region_name=region_name)
    
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
    
    @classmethod
    def get_service_names_in_security_group(cls,security_group: dict)->list[str]:
        
        services=cls.get_services_in_security_group(security_group)
        
        service_names=[service['LoadBalancerName'] for service in services]
        
        return service_names
    
class RDS(NonLookupableService):
    
    client=boto3.client('rds')
    services_by_security_group_id:dict[str,list]={}
    
    @classmethod
    def set_client_region(cls,region_name: str) -> None:
        cls.client=boto3.client('rds',region_name=region_name)
    
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
    
    @classmethod
    def get_service_names_in_security_group(cls,security_group:dict)-> list[str]:
        services=cls.get_services_in_security_group(security_group)
        
        service_names=[service['DBInstanceIdentifier'] for service in services]
        
        return service_names
    
class Redshift(NonLookupableService):
    
    client=boto3.client('redshift')
    services_by_security_group_id:dict[str,list]={}
    
    @classmethod
    def set_client_region(cls,region_name: str) -> None:
        cls.client=boto3.client('redshift',region_name=region_name)
    
    @classmethod
    def load_services(cls)->None:        
        services=[]

        service_response=cls.client.describe_clusters()

        if 'NextMarker' in service_response.keys():
            next_token=service_response['NextMarker']
        else:
            next_token=None

        services.extend(service_response['Clusters'])

        while next_token!=None:
            service_response=cls.client.describe_db_instances(
                Marker=next_token
            )

            if 'NextMarker' in service_response.keys():
                next_token=service_response['NextMarker']
            else:
                next_token=None

            services.extend(service_response['Clusters'])

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
    
    @classmethod
    def get_service_names_in_security_group(cls,security_group: dict)-> list[str]:
        services=cls.get_services_in_security_group(security_group)
        
        service_names=[service['ClusterIdentifier'] for service in services]
        
        return service_names
    
class Lambda(NonLookupableService):
    
    client=boto3.client('lambda')
    services_by_security_group_id:dict[str,list]={}
    
    @classmethod
    def set_client_region(cls,region_name: str) -> None:
        cls.client=boto3.client('lambda',region_name=region_name)
    
    @classmethod
    def load_services(cls)->None:        
        services=[]

        service_response=cls.client.list_functions()

        if 'NextMarker' in service_response.keys():
            next_token=service_response['NextMarker']
        else:
            next_token=None

        services.extend(service_response['Functions'])

        while next_token!=None:
            service_response=cls.client.describe_db_instances(
                Marker=next_token
            )

            if 'NextMarker' in service_response.keys():
                next_token=service_response['NextMarker']
            else:
                next_token=None

            services.extend(service_response['Functions'])

        for service in services:
            if 'VpcConfig' in service.keys():
                security_group_ids=service['VpcConfig']['SecurityGroupIds']

                for security_group_id in security_group_ids:
                    if security_group_id not in cls.services_by_security_group_id.keys():
                        cls.services_by_security_group_id[security_group_id]=[service]
                    else:
                        cls.services_by_security_group_id[security_group_id].append(service)
                        
        return
    
    @classmethod
    def get_service_names_in_security_group(cls,security_group: dict)-> list[str]:
        services=cls.get_services_in_security_group(security_group)
        
        service_names=[service['FunctionName'] for service in services]
        
        return service_names
    
class ElastiCache(NonLookupableService):

    client=boto3.client('elasticache')
    services_by_security_group_id:dict[str,list]={}
    
    @classmethod
    def set_client_region(cls,region_name: str) -> None:
        cls.client=boto3.client('elasticache',region_name=region_name)
    
    @classmethod
    def load_services(cls) -> None:
        
        services=[]

        service_response=cls.client.describe_cache_clusters()

        if 'NextMarker' in service_response.keys():
            next_token=service_response['NextMarker']
        else:
            next_token=None

        services.extend(service_response['CacheClusters'])

        while next_token!=None:
            service_response=cls.client.describe_load_balancers(
                Marker=next_token
            )

            if 'NextMarker' in service_response.keys():
                next_token=service_response['NextMarker']
            else:
                next_token=None

            services.extend(service_response['CacheClusters'])

        for service in services:
            if 'SecurityGroups' in service.keys():
                security_groups=service['SecurityGroups']

                for security_group in security_groups:
                    security_group_id=security_group['SecurityGroupId']
                    if security_group_id not in cls.services_by_security_group_id.keys():
                        cls.services_by_security_group_id[security_group_id]=[service]
                    else:
                        cls.services_by_security_group_id[security_group_id].append(service)
                        
        return
    
    @classmethod
    def get_service_names_in_security_group(cls,security_group: dict)-> list[str]:
        services=cls.get_services_in_security_group(security_group)
        
        service_names=[service['CacheClusterId'] for service in services]
        
        return service_names

class DMS(NonLookupableService):
    
    client=boto3.client('dms')
    services_by_security_group_id:dict[str,list]={}
    
    @classmethod
    def set_client_region(cls,region_name: str) -> None:
        cls.client=boto3.client('dms',region_name=region_name)
    
    @classmethod
    def load_services(cls) -> None:
        
        services=[]

        service_response=cls.client.describe_replication_instances()

        if 'NextMarker' in service_response.keys():
            next_token=service_response['NextMarker']
        else:
            next_token=None

        services.extend(service_response['ReplicationInstances'])

        while next_token!=None:
            service_response=cls.client.describe_load_balancers(
                Marker=next_token
            )

            if 'NextMarker' in service_response.keys():
                next_token=service_response['NextMarker']
            else:
                next_token=None

            services.extend(service_response['ReplicationInstances'])

        for service in services:
            if 'VpcSecurityGroups' in service.keys():
                security_groups=service['VpcSecurityGroups']

                for security_group in security_groups:
                    security_group_id=security_group['VpcSecurityGroupId']
                    if security_group_id not in cls.services_by_security_group_id.keys():
                        cls.services_by_security_group_id[security_group_id]=[service]
                    else:
                        cls.services_by_security_group_id[security_group_id].append(service)
                        
        return
        
    @classmethod
    def get_service_names_in_security_group(cls,security_group: dict)-> list[str]:
        services=cls.get_services_in_security_group(security_group)
        
        service_names=[service['ReplicationInstanceIdentifier'] for service in services]
        
        return service_names
    
class EMR(NonLookupableService):
    
    client=boto3.client('emr')
    services_by_security_group_id:dict[str,list]={}
    
    @classmethod
    def set_client_region(cls,region_name: str) -> None:
        cls.client=boto3.client('emr',region_name=region_name)
    
    #Look for clusters in these states only
    cluster_states=[
        'STARTING',
        'BOOTSTRAPPING',
        'RUNNING',
        'WAITING'
        #'TERMINATING',
        # 'TERMINATED',
        # 'TERMINATED_WITH_ERRORS'
    ]
    
    @classmethod
    def load_services(cls) -> None:
        
        cluster_ids=[]
        
        cluster_list_response=cls.client.list_clusters(ClusterStates=cls.cluster_states)
        
        cluster_ids.extend([cluster['Id'] for cluster in cluster_list_response['Clusters']])
        
        if 'NextMarker' in cluster_list_response.keys():
            next_token=cluster_list_response['NextMarker']
        else:
            next_token=None
            
        while next_token!=None:
            cluster_list_response=cls.client.list_clusters(
                ClusterStates=cls.cluster_states,
                Marker=next_token
            )
        
            cluster_ids.extend([cluster['Id'] for cluster in cluster_list_response['Clusters']])
            
        for cluster_id in cluster_ids:
            security_group_ids=[]
            
            cluster_response=cls.client.describe_cluster(ClusterId=cluster_id)
            
            cluster=cluster_response['Cluster']
            ec2_attributes=cluster['Ec2InstanceAttributes']
            
            security_group_ids.append(ec2_attributes['EmrManagedMasterSecurityGroup'])
            security_group_ids.append(ec2_attributes['EmrManagedSlaveSecurityGroup'])
            
            if 'ServiceAccessSecurityGroup' in ec2_attributes.keys():
                #This one is for a SG that allows acces to private subnets (I don't 100% understand that)
                security_group_ids.append(ec2_attributes['ServiceAccessSecurityGroup'])
         
            #These two may contain many security groups   
            if 'AdditionalMasterSecurityGroups' in ec2_attributes.keys():
                security_group_ids.extend(ec2_attributes['AdditionalMasterSecurityGroups'])
            if 'AdditionalSlaveSecurityGroups' in ec2_attributes.keys():
                security_group_ids.extend(ec2_attributes['AdditionalSlaveSecurityGroups'])
            
            for security_group_id in security_group_ids:
                if security_group_id not in cls.services_by_security_group_id.keys():
                    cls.services_by_security_group_id[security_group_id]=[cluster]
                else:
                    cls.services_by_security_group_id[security_group_id].append(cluster)
        
        return
    
    @classmethod
    def get_service_names_in_security_group(cls,security_group: dict)-> list[str]:
        services=cls.get_services_in_security_group(security_group)
        
        service_names=[service['Name'] for service in services]
        
        return service_names           
            
            
