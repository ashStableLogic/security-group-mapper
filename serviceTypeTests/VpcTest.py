import boto3

ec2=boto3.resource('ec2')

vpc=ec2.Vpc('020a72b5b8ea9c394')

print(vpc.get_available_subresources())