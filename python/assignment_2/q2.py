import boto3


def assume_role(role_arn, session_name, credentials=None):

    if credentials:
        sts = boto3.client(
            "sts",
            aws_access_key_id=credentials["AccessKeyId"],
            aws_secret_access_key=credentials["SecretAccessKey"],
            aws_session_token=credentials["SessionToken"],
        )
    else:
        session = boto3.Session(profile_name="mekyu")
        sts = session.client("sts")

    response = sts.assume_role(
        RoleArn=role_arn,
        RoleSessionName=session_name
    )

    return response["Credentials"]


account_b_role_arn = "arn:aws:iam::093996074872:role/Account_B_Role"
account_c_role_arn = "arn:aws:iam::873011686211:role/Account_C_Role"

print("[INFO] Assuming Account B role...")
account_b_credentials = assume_role(account_b_role_arn, "AtoB")
print("[INFO] Successfully assumed Account B role!")


print("[INFO] Assuming Account C role...")
account_c_credentials = assume_role(account_c_role_arn, "BtoC", account_b_credentials)
print("[INFO] Successfully assumed Account C role!")


ec2 = boto3.client(
    "ec2",
    region_name="us-east-1",
    aws_access_key_id=account_c_credentials["AccessKeyId"],
    aws_secret_access_key=account_c_credentials["SecretAccessKey"],
    aws_session_token=account_c_credentials["SessionToken"]
)


response = ec2.describe_instances()

print("\nEC2 Instances in Account C:")

for reservation in response["Reservations"]:
    for instance in reservation["Instances"]:
        print(instance["InstanceId"])

