import boto3
import pandas as ps
from Services import *

service_types=[
    "Elasticache",
    "Lambda",       #DONE
    "EC2",          #DONE
    "RDS",          #DONE
    "RedShift",     #DONE
    "ALB/NLB",      #DONE
    # "NAT Gateway"   
    "ECS"           #DONE
]

test_sg_id="sg-088fedfb35f162d49"

test_services=Lambda.get_services_in_security_group(test_sg_id)

print(test_services)