import boto3
import pandas as ps
from Services import *

service_types=[
    "Elasticache",
    "Lambda",
    "EC2",          #DONE
    "RDS",
    "RedShift",
    "ALB/NLB",      #DONE
    "NAT Gateway"
    "ECS"           #DONE
]

test_elb_service=ELB.get_services_in_security_group("sg-04eb8cea791cba8bc")

print(len(test_elb_service))