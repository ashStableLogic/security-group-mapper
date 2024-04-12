# Security Group Mapper
## Description
This repo is for a script for mapping out security group info to the services that they currently form a network interface attachment to.

This is made possible with AWS' boto3 python module and custom written classes for each service of interest, as their handling differs to different extents.

## Structure of Script
The script first asks for a list of security groups and then for each security group:

1. Gets all network interfaces for that service,
2. Asks what service types are present in its associated network interfaces via *very* quick and dirty set of rules for each regional service (if this can be improved, pls do so),
3. Queries each present regional service type to get services associated with the current security group

After all services for each security group have been stored in a dict, it gets converted to a Pandas DataFrame and written out to an Excel file via Pandas' ExcelWriter class, the name of which is pulled automatically from the account.

## Structure of Services Module
The Service module consists of a class for each service type of interest and different levels of abstraction by which they are implemented.

### Service
The Service class in an abstract base class representing a type of service offered by AWS.

It consists of a method for storing your access keys for use in each boto3 call and enforces that every service class must have a service type name that tells boto3 what type of client to use in its working.

### GlobalService
The GlobalService class inherits from the Service class.

Global services are those that are more tools for governance of the AWS project such as access and accounts management.

These are not of interest to the point of this tool and also do not take a region in their client definition. As such, they have their own base class.

### RegionalService
The RegionalService class inherits from the Service class.

These services are beholden to specific regions and are implement a way to query them for all services of that type that belong to a given security group.

This class implements a method for setting a regional service's client based on its hardcoded specific client name and a given region name.

### NonLookupableRegionalService
The NonLookupableRegionalService class inherits from the RegionalService class.

EC2 so far is the only Service sub-class that is 'lookup-able' i.e. you can use
```python
boto3.client('ec2').describe_instances(
    Filters=[
        {
            'Name': 'GroupId',
            'Values': [
                security_group_id,
            ]
        },
    ])
```
to get a list of services for that security group.

The rest aren't 'lookup-able', meaning there is no method present in boto3 for going straight from a security group ID to a list of services. Unfortunately, this happens to be pretty much all of them.

To get around this, these service types load all of the information pertaining to every single instance/cluster/whatever on-device, grouped by security group so that they can be queried later.

### Individual Regional Service Types
Because the individual regional service types all have different ways of collecting information (different clients, json keys, etc.) they are implemented in different classes.

## Adding More Service Types
To add another service type, first of all figure out whether it is a service type that can be directly queried for all services within a given security group by checking the boto3 docs [here](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html).

If it is, make it inherit the `RegionalService` class and implement its `client` attribute and `get_services_in_security_group` and `get_service_names_in_security_group` methods.

If it's not, make it inherit the `NonLookupableService` class and implement its `client` and `services_by_security_group` attributes, `load_services()` and `get_service_names_in_security_group` methods to load and store all services of its type into `NonLookupableService.services_by_security_group`.

You'll still need to implement its `NonLookupableService.get_service_names_in_security_group()` it inherits from the `Service` class.

After this, add a rule based on network interface information captured from a given security group in `EC2.get_service_types_from_network_interfaces()` that tells the main script that the service you're adding should be queried.

# Requirements
This repo has a conda requirements file.

In your conda prompt, run conda env create -f requirements.yml

# Running the tool
The tool takes two required parameters, a csv of access keys downloaded from IAM and a set of user defined regions to investigate.

Run the tool in the supplied conda environment as follows:

`python map_security_groups_to_services.py -k access_keys_csv_path.csv -r region-1 region-2 region-3 etc OR all`

# TODO
 - [x] Add EMR as a supported service type
 - [x] Add support for multiple regions for each service type
 - [x] Add support for inputting aws keys instead of relying on environment variables
 - [x] Tidy up and comment everything
 - [ ] Add any sort of error handling (insufficient perms for calling particular service types, bad keys etc.)
