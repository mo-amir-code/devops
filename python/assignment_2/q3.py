import boto3
from datetime import date, timedelta


def get_regions_from_billing():
    
    # Cost Explorer client
    ce = boto3.client("ce")   

    end = date.today()
    start = end - timedelta(days=30)

    response = ce.get_cost_and_usage(
        TimePeriod={
            "Start": start.strftime("%Y-%m-%d"),
            "End": end.strftime("%Y-%m-%d")
        },
        Granularity="MONTHLY",
        Metrics=["UnblendedCost"],
        GroupBy=[
            {
                "Type": "DIMENSION",
                "Key": "REGION"
            }
        ]
    )

    regions = []

    for group in response["ResultsByTime"][0]["Groups"]:
        region = group["Keys"][0]
        cost = float(group["Metrics"]["UnblendedCost"]["Amount"])

        if cost > 0:
            regions.append(region)

    return regions


if __name__ == "__main__":

    regions = get_regions_from_billing()

    print("Regions where customer is billed:")

    for r in regions:
        print(r)