import boto3
import pandas as ps
from Services import *

service_types=[
    "Elasticache",
    "Lambda",
    "EC2",
    "RDS",
    "ALB",
    "ECS"
]

test_ec2_services=EC2.get_services_in_security_group("sg-039f6c6227fc240b7")

print(len(test_ec2_services))