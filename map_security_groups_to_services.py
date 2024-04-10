import sys

import pandas as ps
from services import *

global data
global data_headers

def get_all_subclasses(cls):
    all_subclasses=[]
    
    for subclass in cls.__subclasses__():
        if len(subclass.__subclasses__())==0:
            all_subclasses.append(subclass.__name__)
            
        all_subclasses.extend(get_all_subclasses(subclass))
        
    return all_subclasses

##Only add headers which you will manually add to in the main script below,
##the above function will handle adding the names of services to be searched using
##those implemented in the services module (Services must not be superclasses)

data_headers=[
    'Security Group ID',
    'Security Group Name',
    'Securty Group Region'
]

data_headers.extend(get_all_subclasses(Service))

data={header:[] for header in data_headers}

project_name=IAM.get_project_name()

write_csv_filename=f'{project_name} IAM alias test security groups and associated services.xlsx'

def get_associations(region=None):
    """Main loop of the tool, no region means all services will pull from default region """
        
    if region==None:
        region_to_write=EC2.get_client().region_name
    else:
        region_to_write=region
        EC2.set_client_region(region)
    
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
        new_record[2]=region_to_write
        
        network_interfaces=EC2.get_network_interfaces_for_security_group(security_group)
        
        service_types_to_lookup=EC2.get_service_types_from_network_interfaces(network_interfaces)
        
        for service in service_types_to_lookup:
            if region!=None:
                service.set_client_region(region)
            new_record[data_headers.index(service.__name__)]='\n'.join(service.get_service_names_in_security_group(security_group))
            
        for header,field in zip(data_headers,new_record):
            data[header].append(field)
            
    print(f"fetched services for {region_to_write}")

if __name__=="__main__":
    
    regions=[]
    
    all_regions=EC2.get_all_available_regions()
    
    if len(sys.argv)>0:
        if sys.argv[1]=="all":
            regions=all_regions
        else:
            regions=sys.argv[1:]
            assert(all(region in all_regions for region in regions))
    
    if len(regions)>0:
        for region in regions:
            get_associations(region)
    else:
        get_associations()
            
    with ps.ExcelWriter(write_csv_filename,engine='xlsxwriter',mode='w') as writer:
        df=ps.DataFrame.from_dict(data)
        df.to_excel(writer)
        print("written table")
    