import pandas as ps
from services import *

data={
    'Security Group ID':[],
    'Security Group Name':[],
    'ElastiCache':[],
    'Lambda':[],
    'EC2':[],
    'RDS':[],
    'ALB':[],
    'ECS':[],
    'Redshift':[],
    'DMS':[],
    'EMR':[]
}

data_keys=list(data.keys())

write_csv_filename='CSCS EMR test security groups and associated services.xlsx'

if __name__=="__main__":
    
    security_groups=EC2.get_security_groups()
    
    # security_groups=[
    #     {
    #         "GroupId":"sg-0039ab3c5e6379086",
    #         "GroupName":"Test"
    #     }
    # ]
    
    for security_group in security_groups:
        
        new_record=['']*len(data.keys())
        
        new_record[0]=security_group['GroupId']        
        new_record[1]=security_group['GroupName']        
        
        network_interfaces=EC2.get_network_interfaces_for_security_group(security_group)
        
        service_types_to_lookup=EC2.get_service_types_from_network_interfaces(network_interfaces)
        
        for service in service_types_to_lookup:               
            new_record[data_keys.index(service.__name__)]='\n'.join(service.get_service_names_in_security_group(security_group))
            
        for key,field in zip(data.keys(),new_record):
            data[key].append(field)
            
    print("fetched services")
                        
    with ps.ExcelWriter(write_csv_filename,engine='xlsxwriter',mode='w') as writer:
        df=ps.DataFrame.from_dict(data)
        df.to_excel(writer)
        print("written")
    