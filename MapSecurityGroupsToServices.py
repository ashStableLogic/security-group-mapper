import boto3
import pandas as ps
from Services import *

service_types=[
    "Elasticache",  #DONE
    "Lambda",       #DONE
    "EC2",          #DONE
    "RDS",          #DONE
    "RedShift",     #DONE
    "ALB/NLB",      #DONE
    # "NAT Gateway"   
    "ECS"           #DONE
]

test_sg_id="sg-0a41b0a316dee9bd9"

test_services=Elasticache.get_services_in_security_group(test_sg_id)

print(test_services)