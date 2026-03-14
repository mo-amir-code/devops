import boto3
import csv

def describe_ec2_regions():
    ec2 = boto3.client("ec2")
    # With AllRegions=True this will return all the regions including disabled regions
    # response = ec2.describe_regions(AllRegions=True)
    
    print("[INFO] Fetching regions...")
    
    response = ec2.describe_regions()
    regions = [r["RegionName"] for r in response["Regions"]]
    # print("Regions: ", regions)

    print("[INFO] Regions fetched!")
    return regions


def describe_instance_type(region):
    ec2 = boto3.client("ec2", region_name=region)
    
    print(f"[INFO] Fetching instance types for {region} region...")
    
    paginator = ec2.get_paginator("describe_instance_types")

    instance_types = []

    for page in paginator.paginate():
        # print("PAGE: ", page)
        for itype in page["InstanceTypes"]:
            # print("ITYPE: ", itype)
            instance_types.append(itype["InstanceType"])

    print(f"[INFO] Instance types fetched for {region} region!")

    return ",".join(instance_types)



def write_csv(data, filename="ec2_instance_types.csv"):
    print("[INFO] Writing data to CSV...")

    with open(filename, "w", newline="") as csvfile:
        writer = csv.writer(csvfile)

        writer.writerow(["region", "instance_types"])

        for region, instance_types in data.items():
            writer.writerow([region, instance_types])

    print(f"[INFO] CSV file created: {filename}")


    
if __name__ == "__main__":
    all_regions = describe_ec2_regions()

    all_instance_types_with_region = {}
    
    for region in all_regions:
        instance_types = describe_instance_type(region)
        all_instance_types_with_region.update({
            region: instance_types
        })

    print("[INFO] Instance types fetching has been completed!")
        
    # print(all_instance_types_with_region)
    write_csv(all_instance_types_with_region)
