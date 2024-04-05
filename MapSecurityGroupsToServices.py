import boto3
import pandas as ps
from Services import *

service_types=[
    "Elasticache",
    "Lambda",
    "EC2",          #DONE
    "RDS",          #DONE
    "RedShift",
    "ALB/NLB",      #DONE
    # "NAT Gateway"   
    "ECS"           #DONE
]

test_rds_services=RDS.get_services_in_security_group("sg-08dc033d9a5edf3db")

print(test_rds_services)