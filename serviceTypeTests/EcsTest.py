import boto3

resource_explorer_client=boto3.client('resource-explorer-2')

arn='arn:aws:ecs:eu-west-2:583957734022:service/cscs-prod-master-service'

response=resource_explorer_client.search(
    QueryString=f"id:{arn}"
)

print(response)