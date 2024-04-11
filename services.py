from abc import ABC,abstractmethod
import boto3

class Service(ABC):
    
    _aws_access_key_id=''
    _aws_secret_access_key=''
    _aws_session_token=''
    
    @classmethod
    def set_creds(
        cls,
        aws_access_key_id='',
        aws_secret_access_key='',
        aws_session_token=''
    ) -> None:
        
        cls._aws_access_key_id=aws_access_key_id
        cls._aws_secret_access_key=aws_secret_access_key
        cls._aws_session_token=aws_session_token
        
        return
        
    @property
    @abstractmethod
    def client():
        raise NotImplementedError()
    
    @abstractmethod
    def set_client(region: str)->None:
        raise NotImplementedError()
    
    @classmethod
    def get_client(cls) -> boto3.Session:
        return cls._client


class GlobalService(Service):
    
    @classmethod
    def set_client(cls) -> None:
        cls._client=boto3.client(
            cls._client_name,
            aws_access_key_id=Service._aws_access_key_id,
            aws_secret_access_key=Service._aws_secret_access_key,
            aws_session_token=Service._aws_session_token,
        )
    
class STS(GlobalService):
    
    _client_name='sts'
    
    @classmethod
    def get_account_id(cls) -> str:
        
        account_id=cls._client.get_caller_identity()['Account']
        
        return account_id
        
class Account(GlobalService):
    
    _client_name='account'

    __regions_to_list=[
        'ENABLED'#,
        #'ENABLING,
        #'DISABLING,
        #'DISABLED',
        #'ENABLED_BY_DEFAULT
    ]
    
    @classmethod
    def list_available_regions(cls) -> list[dict[str,str]]:
        
        regions=[]
        account_id=STS.get_account_id()

        region_response=cls._client.list_regions(
            AccountId=account_id
        )

        if 'nextToken' in region_response.keys():
            next_token=region_response['nextToken']
        else:
            next_token=None

        regions.extend(region_response['clusterArns'])

        while next_token!=None:
            region_response=cls._client.list_clusters(
                AccountId=account_id,
                nextToken=next_token
            )

            if 'nextToken' in region_response.keys():
                next_token=region_response['nextToken']
            else:
                next_token=None

            regions.extend(region_response['clusterArns'])
            
        return [region['RegionName'] for region in regions]      

class IAM(GlobalService):
    
    _client_name='iam'
    
    @classmethod
    def get_project_name(cls) -> str:
        alias_response=cls._client.list_account_aliases()
        
        return alias_response['AccountAliases'][0]


class RegionalService(Service):
    """Service ABC, defines a common 1:m SG in -> services out method
    common to all services
    """
    
    @classmethod
    def set_client(cls,region: str):
        cls._client=boto3.client(
            cls._client_name,
            aws_access_key_id=Service._aws_access_key_id,
            aws_secret_access_key=Service._aws_secret_access_key,
            aws_session_token=Service._aws_session_token,
            region_name=region
        )
    
    @abstractmethod
    def get_services_in_security_group(security_group:dict) -> list[dict]:
        raise NotImplementedError()
    
    @abstractmethod
    def get_service_names_in_security_group(security_group: dict)->list[str]:
        raise NotImplementedError()

class EC2(RegionalService):
    
    _client_name='ec2'
        
    @classmethod
    def get_resource(cls) -> boto3.Session:
        return cls.__resource

    @classmethod
    def set_resource(cls) -> boto3.Session:
        cls.__resource=boto3.resource(
            cls._client_name,
            aws_access_key_id=Service._aws_access_key_id,
            aws_secret_access_key=Service._aws_secret_access_key,
            aws_session_token=Service._aws_session_token,
        )
        
        return

    @classmethod    
    def list_available_regions(cls)-> list[str]:
        """Use when you don't have perms to use Account.list_regions()

        Returns:
            list[str]: List of enabled region names
        """
        return [region['RegionName'] for region in cls._client.describe_regions(AllRegions=False)['Regions']]
    
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
    
        service_response=cls._client.describe_instances(
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
            service_response=cls._client.describe_instances(
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
        
        response=cls._client.describe_security_groups()
        
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
        
        network_interfaces=cls._client.describe_network_interfaces(
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


class NonLookupableRegionalService(RegionalService):
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

        if security_group_id in cls._services_by_security_group_id.keys():
            services=cls._services_by_security_group_id[security_group_id]
        else:
            services=[]
        
        return services

    @classmethod
    def has_services(cls):
        return len(cls._services_by_security_group_id.keys())>0        
        
class ECS(NonLookupableRegionalService):
    """Deals with lookup for ECS services
    """

    _client_name='ecs' 
    _services_by_security_group_id:dict[str,list]={}

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

        cluster_arn_response=cls._client.list_clusters()

        if 'nextToken' in cluster_arn_response.keys():
            next_token=cluster_arn_response['nextToken']
        else:
            next_token=None

        cluster_arns.extend(cluster_arn_response['clusterArns'])

        while next_token!=None:
            cluster_arn_response=cls._client.list_clusters(
                nextToken=next_token
            )

            if 'nextToken' in cluster_arn_response.keys():
                next_token=cluster_arn_response['nextToken']
            else:
                next_token=None

            cluster_arns.extend(cluster_arn_response['clusterArns'])

        for cluster_arn in cluster_arns:
            service_arns=[]

            service_arn_response=cls._client.list_services(
                cluster=cluster_arn
            )

            if 'nextToken' in service_arn_response.keys():
                next_token=service_arn_response['nextToken']
            else:
                next_token=None

            service_arns.extend(service_arn_response['serviceArns'])

            while next_token!=None:
                service_arn_response=cls._client.list_services(
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
                    service_response=cls._client.describe_services(
                        cluster=cluster_arn,
                        services=service_arns[service_arn_index:]
                    )
                else:
                    service_response=cls._client.describe_services(
                        cluster=cluster_arn,
                        services=service_arns[service_arn_index:cls.lookup_batch_size]
                    )
                
                for service in service_response['services']:
                    security_groups=service['networkConfiguration']['awsvpcConfiguration']['securityGroups']

                    for security_group in security_groups:
                        if security_group not in cls._services_by_security_group_id.keys():
                            cls._services_by_security_group_id[security_group]=[service]
                        else:
                            cls._services_by_security_group_id[security_group].append(service)

        return

    @classmethod
    def get_service_names_in_security_group(cls,security_group: dict)->list[str]:
        services=cls.get_services_in_security_group(security_group)
        
        service_names=[service['serviceName'] for service in services]
        
        return service_names

class ALB(NonLookupableRegionalService):

    _client_name='elbv2'
    _services_by_security_group_id:dict[str,list]={}
    
    @classmethod
    def load_services(cls) -> None:
        
        services=[]

        service_response=cls._client.describe_load_balancers()

        if 'NextMarker' in service_response.keys():
            next_token=service_response['NextMarker']
        else:
            next_token=None

        services.extend(service_response['LoadBalancers'])

        while next_token!=None:
            service_response=cls._client.describe_load_balancers(
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
                    if security_group not in cls._services_by_security_group_id.keys():
                        cls._services_by_security_group_id[security_group]=[service]
                    else:
                        cls._services_by_security_group_id[security_group].append(service)
                        
        return
    
    @classmethod
    def get_service_names_in_security_group(cls,security_group: dict)->list[str]:
        
        services=cls.get_services_in_security_group(security_group)
        
        service_names=[service['LoadBalancerName'] for service in services]
        
        return service_names
    
class RDS(NonLookupableRegionalService):
    
    _client_name='rds'
    _services_by_security_group_id:dict[str,list]={}
    
    @classmethod
    def load_services(cls)->None:        
        services=[]

        service_response=cls._client.describe_db_instances()

        if 'NextMarker' in service_response.keys():
            next_token=service_response['NextMarker']
        else:
            next_token=None

        services.extend(service_response['DBInstances'])

        while next_token!=None:
            service_response=cls._client.describe_db_instances(
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
                    if security_group not in cls._services_by_security_group_id.keys():
                        cls._services_by_security_group_id[security_group]=[service]
                    else:
                        cls._services_by_security_group_id[security_group].append(service)
                        
        return
    
    @classmethod
    def get_service_names_in_security_group(cls,security_group:dict)-> list[str]:
        services=cls.get_services_in_security_group(security_group)
        
        service_names=[service['DBInstanceIdentifier'] for service in services]
        
        return service_names
    
class Redshift(NonLookupableRegionalService):
    
    _client_name='redshift'
    _services_by_security_group_id:dict[str,list]={}
    
    @classmethod
    def load_services(cls)->None:        
        services=[]

        service_response=cls._client.describe_clusters()

        if 'NextMarker' in service_response.keys():
            next_token=service_response['NextMarker']
        else:
            next_token=None

        services.extend(service_response['Clusters'])

        while next_token!=None:
            service_response=cls._client.describe_db_instances(
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
                    if security_group not in cls._services_by_security_group_id.keys():
                        cls._services_by_security_group_id[security_group]=[service]
                    else:
                        cls._services_by_security_group_id[security_group].append(service)
                        
        return
    
    @classmethod
    def get_service_names_in_security_group(cls,security_group: dict)-> list[str]:
        services=cls.get_services_in_security_group(security_group)
        
        service_names=[service['ClusterIdentifier'] for service in services]
        
        return service_names
    
class Lambda(NonLookupableRegionalService):
    
    _client_name='lambda'  
    _services_by_security_group_id:dict[str,list]={}

    @classmethod
    def load_services(cls)->None:        
        services=[]

        service_response=cls._client.list_functions()

        if 'NextMarker' in service_response.keys():
            next_token=service_response['NextMarker']
        else:
            next_token=None

        services.extend(service_response['Functions'])

        while next_token!=None:
            service_response=cls._client.describe_db_instances(
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
                    if security_group_id not in cls._services_by_security_group_id.keys():
                        cls._services_by_security_group_id[security_group_id]=[service]
                    else:
                        cls._services_by_security_group_id[security_group_id].append(service)
                        
        return
    
    @classmethod
    def get_service_names_in_security_group(cls,security_group: dict)-> list[str]:
        services=cls.get_services_in_security_group(security_group)
        
        service_names=[service['FunctionName'] for service in services]
        
        return service_names
    
class ElastiCache(NonLookupableRegionalService):

    _client_name='elasticache'
    _services_by_security_group_id:dict[str,list]={}
    
    @classmethod
    def load_services(cls) -> None:
        
        services=[]

        service_response=cls._client.describe_cache_clusters()

        if 'NextMarker' in service_response.keys():
            next_token=service_response['NextMarker']
        else:
            next_token=None

        services.extend(service_response['CacheClusters'])

        while next_token!=None:
            service_response=cls._client.describe_load_balancers(
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
                    if security_group_id not in cls._services_by_security_group_id.keys():
                        cls._services_by_security_group_id[security_group_id]=[service]
                    else:
                        cls._services_by_security_group_id[security_group_id].append(service)
                        
        return
    
    @classmethod
    def get_service_names_in_security_group(cls,security_group: dict)-> list[str]:
        services=cls.get_services_in_security_group(security_group)
        
        service_names=[service['CacheClusterId'] for service in services]
        
        return service_names

class DMS(NonLookupableRegionalService):
    
    _client_name='dms'
    _services_by_security_group_id:dict[str,list]={}
    
    @classmethod
    def load_services(cls) -> None:
        
        services=[]

        service_response=cls._client.describe_replication_instances()

        if 'NextMarker' in service_response.keys():
            next_token=service_response['NextMarker']
        else:
            next_token=None

        services.extend(service_response['ReplicationInstances'])

        while next_token!=None:
            service_response=cls._client.describe_load_balancers(
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
                    if security_group_id not in cls._services_by_security_group_id.keys():
                        cls._services_by_security_group_id[security_group_id]=[service]
                    else:
                        cls._services_by_security_group_id[security_group_id].append(service)
                        
        return
        
    @classmethod
    def get_service_names_in_security_group(cls,security_group: dict)-> list[str]:
        services=cls.get_services_in_security_group(security_group)
        
        service_names=[service['ReplicationInstanceIdentifier'] for service in services]
        
        return service_names
    
class EMR(NonLookupableRegionalService):
    
    _client_name='emr'
    _services_by_security_group_id:dict[str,list]={}
    
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
        
        cluster_list_response=cls._client.list_clusters(ClusterStates=cls.cluster_states)
        
        cluster_ids.extend([cluster['Id'] for cluster in cluster_list_response['Clusters']])
        
        if 'NextMarker' in cluster_list_response.keys():
            next_token=cluster_list_response['NextMarker']
        else:
            next_token=None
            
        while next_token!=None:
            cluster_list_response=cls._client.list_clusters(
                ClusterStates=cls.cluster_states,
                Marker=next_token
            )
        
            cluster_ids.extend([cluster['Id'] for cluster in cluster_list_response['Clusters']])
            
        for cluster_id in cluster_ids:
            security_group_ids=[]
            
            cluster_response=cls._client.describe_cluster(ClusterId=cluster_id)
            
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
                if security_group_id not in cls._services_by_security_group_id.keys():
                    cls._services_by_security_group_id[security_group_id]=[cluster]
                else:
                    cls._services_by_security_group_id[security_group_id].append(cluster)
        
        return
    
    @classmethod
    def get_service_names_in_security_group(cls,security_group: dict)-> list[str]:
        services=cls.get_services_in_security_group(security_group)
        
        service_names=[service['Name'] for service in services]
        
        return service_names           
            
            
