from argparse import ArgumentParser

import pandas as ps
import csv

from services import *

global data_headers


def get_all_subclasses(cls):
    """Gets all leaves in the class tree starting
    from the specified class.

    Args:
        cls (Class):                    Any class.

    Returns:
        all_subclasses (list[Class]):   List of subclasses with no subclasses themselves.
    """
    all_subclasses = []

    for subclass in cls.__subclasses__():
        if len(subclass.__subclasses__()) == 0:
            all_subclasses.append(subclass)

        all_subclasses.extend(get_all_subclasses(subclass))

    return all_subclasses


def setup(keys_csv_path: str) -> None:
    """Applies supplied access keys to service classes and
    defines dict for storing data to write.

    Args:
        keys_csv_path (str): path to csv containing access keys.
    """

    global data
    global data_headers

    aws_access_key_id = ""
    aws_secret_access_key = ""
    aws_session_token = ""

    with open(keys_csv_path, "r") as keys_file:
        reader = csv.reader(keys_file)
        keys_data = list(reader)[1]

    if len(keys_data) == 2:
        aws_access_key_id = keys_data[0]
        aws_secret_access_key = keys_data[1]
    elif len(keys_data) == 3:
        aws_session_token = keys_data[2]

    Service.set_keys(aws_access_key_id, aws_secret_access_key, aws_session_token)

    [subclass.set_client() for subclass in get_all_subclasses(GlobalService)]

    EC2.set_client(region=None)
    EC2.set_resource()

    ##Only add headers that are to be manually added in the main script

    data_headers = ["Security Group ID", "Security Group Name", "Securty Group Region"]

    ##Adding names of all regional services

    data_headers.extend(
        [subclass.__name__ for subclass in get_all_subclasses(RegionalService)]
    )

    data = {header: [] for header in data_headers}

    return


def get_associations(region: str) -> None:
    """Main loop of the tool, takes a region
    and write all services for all sercurity groups
    in that region to the main 'data' dict.

    Args:
        region (str): region name
    """

    EC2.set_client(region)

    security_groups = EC2.get_security_groups()

    # security_groups=[
    #     {
    #         "GroupId":"sg-0039ab3c5e6379086",
    #         "GroupName":"Test"
    #     }
    # ]

    for security_group in security_groups:

        new_record = [""] * len(data.keys())

        new_record[0] = security_group["GroupId"]
        new_record[1] = security_group["GroupName"]
        new_record[2] = region

        network_interfaces = EC2.get_network_interfaces_for_security_group(
            security_group
        )

        regional_service_types_to_lookup = (
            EC2.get_service_types_from_network_interfaces(network_interfaces)
        )

        for regional_service in regional_service_types_to_lookup:
            if region != None:
                regional_service.set_client(region)
            new_record[data_headers.index(regional_service.__name__)] = "\n".join(
                regional_service.get_service_names_in_security_group(security_group)
            )

        for header, field in zip(data_headers, new_record):
            data[header].append(field)

    print(f"fetched services for {region}")

    return


if __name__ == "__main__":

    # Args are in the form:
    # this_program -k path_to_csv.csv -r eu-west-1 us-east-1 us-east-2 etc.

    parser = ArgumentParser()

    parser.add_argument(
        "-k",
        "--access-keys-csv-path",
        dest="access_keys_csv_path",
        help="Access keys CSV path",
        required=True,
        type=str,
    )

    parser.add_argument(
        "-r",
        "--regions",
        nargs="+",
        dest="regions",
        help="Space-separated regions, type 'all' for all enabled regions",
        required=True,
        type=str,
    )

    args = parser.parse_args()

    access_keys_csv_path = args.access_keys_csv_path
    regions = args.regions

    setup(access_keys_csv_path)

    project_name = IAM.get_project_name()

    write_csv_filename = f"{project_name} security groups and associated services.xlsx"

    # all_regions=Account.list_available_regions()
    all_regions = EC2.list_available_regions()

    assert all(region in all_regions for region in regions)

    for region in regions:
        get_associations(region)

    with ps.ExcelWriter(write_csv_filename, engine="xlsxwriter", mode="w") as writer:
        df = ps.DataFrame.from_dict(data)
        df.to_excel(writer)
        print("written table")
