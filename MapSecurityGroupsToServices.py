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

ECS.load_services()

test_ecs_services=ECS.get_services_in_security_group("sg-0e0fb363ead3cc7d3")

print(len(test_ecs_services))