import boto3
import pandas as ps
from Services import *

service_types=[
    "Elasticache",
    "Lambda",
    "EC2",          #DONE
    "RDS",          #DONE
    "RedShift",     #DONE
    "ALB/NLB",      #DONE
    # "NAT Gateway"   
    "ECS"           #DONE
]

test_sg_id="sg-0bdcc4b9d44ff7566"

test_rds_services=Redshift.get_services_in_security_group(test_sg_id)

print(test_rds_services)