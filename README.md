# Security Group Mapper

## Description
This repo is for a script for mapping out security group info to the services that they currently form a network interface attachment to.

This is made possible with AWS' boto3 python module and custom written classes for each service of interest, as their handling differs to different extents.

## Structure of Script
The script first asks for a list of security groups and then for each security group:

1. Gets all network interfaces for that service,
2. Asks what service types are present in its associated network interfaces via *very* quick and dirty set of rules for each service (if this can be improved, pls do so),
3. Queries each present service type to get services associated with the current security group

After all services for each security group have been stored in a dict, it gets converted to a Pandas DataFrame and written out to an Excel file via Pandas' ExcelWriter class.

## Structure of Service Module
The Service module consists of a class for each service type of interest and different levels of abstract by which they are implemented.

### Service ABC
The Service class in an abstract base class representing a service type that can be queried for all services belonging to a given security group.
It has two abstract methods, one for getting service data via a given security group and one for distilling this info down to just service names.

### NonLookupableService ABC
The NonLookupableService is an abstract base class that inherits from the Service class.
This is for service types that can't just be asked to return all services that are under a given security group. Unfortunately, this happens to be pretty much all of them.
To get around this, these service types load all of the information pertaining to every single instance/cluster/whatever on-device, grouped by security group so that they can be queried later.

### Individual Service Types
Because the individual service types all have different ways of collecting information (different clients, json keys, etc.) they are implemented in different classes.
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

The rest aren't 'lookup-able', meaning there is no method present in boto3 for going straight from a security group ID to a list of services.
To get around this, each class stores a dict of json dicts for every service of its type, grouped by security group id to then be fetched later by the main script.

## Adding More Service Types
To add another service type, first of all figure out whether it is a service type that can be directly queried for all services within a given security group by checking the boto3 docs [here](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html).

If it is, make it inherit the `Service` class and implement its `client` attribute and get methods.
If it's not, make it inherit the `NonLookupableService` class and implement its `client` and `services_by_security_group` attributes, `load_services()` and `get_service_names_in_security_group` methods to load and store all services of its type into `NonLookupableService.services_by_security_group`.
You'll still need to implement its `NonLookupableService.get_service_names_in_security_group()` it inherits from the `Service` class.

After this, add a rule based on network interface information captured from a given security group in `EC2.get_service_types_from_network_interfaces()` that tells the main script that the service you're adding should be queried.

# Requirements
This repo has a conda requirements file.
In your conda prompt, run conda env create -f requirements.yml

# TODO
 - [x] Add EMR as a supported service type
 - [ ] Add support for multiple regions for each service type
 - [ ] Tidy up and comment everything
