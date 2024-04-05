import boto3

ec2=boto3.client('ec2')

network_interfaces=ec2.describe_network_interfaces(
    Filters=[
        {
            'Name':'group-id',
            'Values':[
                'sg-096b448a707db98be'
            ]
        }
    ]
)['NetworkInterfaces']

print(network_interfaces)