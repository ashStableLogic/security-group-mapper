{
    'Association': {
        'IpOwnerId': 'amazon',
        'PublicDnsName': 'ec2-35-177-96-192.eu-west-2.compute.amazonaws.com', 
        'PublicIp': '35.177.96.192'
    }, 
    'Attachment': {
        'AttachTime': datetime.datetime(2024, 3, 25, 8, 44, 20, tzinfo=tzutc()),
        'AttachmentId': 'eni-attach-0310cf8336bc48b51',
        'DeleteOnTermination': False,
        'DeviceIndex': 1,
        'NetworkCardIndex': 0,
        'InstanceOwnerId': '786829106431',
        'Status': 'attached'
    },
    'AvailabilityZone': 'eu-west-2a',
    'Description': 'arn:aws:ecs:eu-west-2:583957734022:attachment/665d4fbe-1dd1-426e-9f20-b8af371fcf97',
    'Groups': [
        {
            'GroupName': 'cscs-dev-ecs-zipkin-sg',
            'GroupId': 'sg-096b448a707db98be'
        }
    ],
    'InterfaceType': 'interface',
    'Ipv6Addresses': [],
    'MacAddress': '06:fc:f3:39:e0:15',
    'NetworkInterfaceId': 'eni-01ce1392f292846ce',
    'OwnerId': '583957734022',
    'PrivateDnsName': 'ip-10-0-1-243.eu-west-2.compute.internal',
    'PrivateIpAddress': '10.0.1.243',
    'PrivateIpAddresses': [
        {
            'Association': {
                'IpOwnerId': 'amazon',
                'PublicDnsName':'ec2-35-177-96-192.eu-west-2.compute.amazonaws.com',
                'PublicIp': '35.177.96.192'
            },
            'Primary': True,
            'PrivateDnsName': 'ip-10-0-1-243.eu-west-2.compute.internal',
            'PrivateIpAddress': '10.0.1.243'
        }
    ],
    'RequesterId': '716531411939',
    'RequesterManaged': True,
    'SourceDestCheck': True,
    'Status': 'in-use',
    'SubnetId': 'subnet-0a9395b9ee1f292f1',
    'TagSet': [
        {
            'Key': 'aws:ecs:clusterName',
            'Value': 'cscs'
        }
    ],
    'VpcId': 'vpc-020a72b5b8ea9c394'
}