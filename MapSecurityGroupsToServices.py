import boto3
import pandas as ps

vpc=boto3.client('vpc')
ec2=boto3.client('ec2')
resource_explorer=boto3.client('resource-explorer-2')

### Plan is get SGs with vpc -> network interfaces from SGs with ec2 ->
### get ARNs somehow -> get service name and type from ARNs with resource explorer ->
### Add to set associated with SG, note down services in Excel at coincidence of service type and SG

