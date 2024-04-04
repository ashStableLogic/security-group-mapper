import csv
import pandas as ps
import boto3

read_csv_filename='security groups.csv'
write_csv_filename='security groups and interfaces.xlsx'

write_headers=[
    "GroupId",
    "GroupName",
    "Description",
    "Tags",
]

ec2=boto3.resource('ec2')

with open(read_csv_filename,'r') as read_file, ps.ExcelWriter(write_csv_filename,engine='xlsxwriter',mode='w') as writer:
    reader=csv.reader(read_file)

    read_headers=next(reader)

    write_headers_names_to_indices=dict()

    for write_header in write_headers:
        write_headers_names_to_indices[write_header]=read_headers.index(write_header)

    write_headers.append("Associated Network Interfaces")

    entries=[]

    for row_index,row in enumerate(reader):
        entry=[]

        for write_headers_index in write_headers_names_to_indices.values():
            entry.append(row[write_headers_index])

        network_interface_iterator=ec2.network_interfaces.filter(
            Filters=[
                {
                    'Name':'group-id',
                    'Values':[
                        f'{entry[write_headers_names_to_indices["GroupId"]]}'
                    ]
                }
            ]
        )

        associated_tasks_string='\n'.join([interface.description for interface in network_interface_iterator])

        entry.append(associated_tasks_string)

        entries.append(entry)

    ps.DataFrame(entries,columns=write_headers).to_excel(writer)
    




