import csv
import boto3
from botocore.exceptions import ClientError


# ──────────────────────────────────────────────
# Helper utilities
# ──────────────────────────────────────────────

def write_csv(filename, headers, rows):
    """Write rows to a CSV file."""
    with open(filename, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)
    print(f"  [saved] {filename}  ({len(rows)} record(s))")


def policy_has_wildcard_action(policy_document):
    """
    Return True if ANY statement in the policy document contains
    a wildcard ('*') inside its Action field.
    Works for both string and list Action values.
    """
    statements = policy_document.get("Statement", [])
    for stmt in statements:
        if stmt.get("Effect") != "Allow":
            continue
        actions = stmt.get("Action", [])
        if isinstance(actions, str):
            actions = [actions]
        for action in actions:
            if "*" in action:          # catches "*", "s3:*", "iam:*", etc.
                return True
    return False


# ──────────────────────────────────────────────
# Check 1 – IAM roles with overly permissive policies
# ──────────────────────────────────────────────

def check_overly_permissive_iam_roles():
    """
    List all IAM roles and flag any attached / inline policy whose
    Action contains a wildcard ('*').  Judgement is based purely on
    the policy content, NOT the policy name.

    Output CSV columns: IAMRoleName, PolicyName
    """
    print("\n[Check 1] Scanning IAM roles for wildcard actions …")
    iam = boto3.client("iam")
    flagged_rows = []

    paginator = iam.get_paginator("list_roles")
    for page in paginator.paginate():
        for role in page["Roles"]:
            role_name = role["RoleName"]

            # ── attached (managed) policies ──────────────────────────
            attached = iam.list_attached_role_policies(RoleName=role_name)
            for policy_meta in attached["AttachedPolicies"]:
                policy_arn = policy_meta["PolicyArn"]
                policy_name = policy_meta["PolicyName"]

                version_id = iam.get_policy(PolicyArn=policy_arn)["Policy"]["DefaultVersionId"]
                policy_doc = iam.get_policy_version(
                    PolicyArn=policy_arn, VersionId=version_id
                )["PolicyVersion"]["Document"]

                if policy_has_wildcard_action(policy_doc):
                    flagged_rows.append([role_name, policy_name])

            # ── inline policies ──────────────────────────────────────
            inline_names = iam.list_role_policies(RoleName=role_name)["PolicyNames"]
            for inline_name in inline_names:
                policy_doc = iam.get_role_policy(
                    RoleName=role_name, PolicyName=inline_name
                )["PolicyDocument"]

                if policy_has_wildcard_action(policy_doc):
                    flagged_rows.append([role_name, inline_name])

    write_csv(
        "check1_overly_permissive_roles.csv",
        ["IAMRoleName", "PolicyName"],
        flagged_rows,
    )
    return flagged_rows


# ──────────────────────────────────────────────
# Check 2 – IAM users MFA status
# ──────────────────────────────────────────────

def check_iam_users_mfa_status():
    """
    List every IAM user and report whether MFA is enabled.

    Output CSV columns: IAMUserName, MFAEnabled
    """
    print("\n[Check 2] Checking MFA status for all IAM users …")
    iam = boto3.client("iam")
    rows = []

    paginator = iam.get_paginator("list_users")
    for page in paginator.paginate():
        for user in page["Users"]:
            user_name = user["UserName"]
            mfa_devices = iam.list_mfa_devices(UserName=user_name)["MFADevices"]
            mfa_enabled = len(mfa_devices) > 0
            rows.append([user_name, mfa_enabled])

    write_csv(
        "check2_iam_users_mfa.csv",
        ["IAMUserName", "MFAEnabled"],
        rows,
    )
    return rows


# ──────────────────────────────────────────────
# Check 3 – Security groups with public access
# ──────────────────────────────────────────────

SENSITIVE_PORTS = {22, 80, 443}
PUBLIC_CIDRS    = {"0.0.0.0/0", "::/0"}


def is_port_in_range(port, from_port, to_port):
    """Return True when 'port' falls inside [from_port, to_port]."""
    return from_port <= port <= to_port


def check_public_security_groups():
    """
    Inspect every security group's inbound rules and flag rules that
    allow traffic from 0.0.0.0/0 or ::/0 on ports 22, 80, or 443.

    Output CSV columns: SGName, Port, AllowedIP
    """
    print("\n[Check 3] Scanning security groups for public inbound access …")
    ec2 = boto3.client("ec2")
    flagged_rows = []

    response = ec2.describe_security_groups()
    for sg in response["SecurityGroups"]:
        sg_name = sg.get("GroupName", sg["GroupId"])

        for rule in sg.get("IpPermissions", []):
            from_port = rule.get("FromPort", 0)
            to_port   = rule.get("ToPort",   65535)

            # Collect all public CIDR ranges in this rule
            public_cidrs_in_rule = []
            for ip_range in rule.get("IpRanges", []):
                if ip_range.get("CidrIp") in PUBLIC_CIDRS:
                    public_cidrs_in_rule.append(ip_range["CidrIp"])
            for ipv6_range in rule.get("Ipv6Ranges", []):
                if ipv6_range.get("CidrIpv6") in PUBLIC_CIDRS:
                    public_cidrs_in_rule.append(ipv6_range["CidrIpv6"])

            if not public_cidrs_in_rule:
                continue

            # Record a row for each sensitive port exposed publicly
            for port in SENSITIVE_PORTS:
                if is_port_in_range(port, from_port, to_port):
                    for cidr in public_cidrs_in_rule:
                        flagged_rows.append([sg_name, port, cidr])

    write_csv(
        "check3_public_security_groups.csv",
        ["SGName", "Port", "AllowedIP"],
        flagged_rows,
    )
    return flagged_rows


# ──────────────────────────────────────────────
# Check 4 – Unused EC2 key pairs
# ──────────────────────────────────────────────

def get_key_pairs_in_use():
    """Return a set of key-pair names currently attached to running instances."""
    ec2 = boto3.client("ec2")
    in_use = set()

    paginator = ec2.get_paginator("describe_instances")
    for page in paginator.paginate():
        for reservation in page["Reservations"]:
            for instance in reservation["Instances"]:
                key_name = instance.get("KeyName")
                if key_name:
                    in_use.add(key_name)

    return in_use


def check_unused_ec2_key_pairs():
    """
    List all EC2 key pairs and flag any that are not attached to an
    existing EC2 instance.

    Output CSV columns: KeyPairName, InUse
    """
    print("\n[Check 4] Identifying unused EC2 key pairs …")
    ec2 = boto3.client("ec2")

    all_key_pairs = ec2.describe_key_pairs()["KeyPairs"]
    keys_in_use   = get_key_pairs_in_use()

    rows = []
    for kp in all_key_pairs:
        key_name = kp["KeyName"]
        in_use   = key_name in keys_in_use
        rows.append([key_name, in_use])

    write_csv(
        "check4_unused_ec2_key_pairs.csv",
        ["KeyPairName", "InUse"],
        rows,
    )
    return rows


# ──────────────────────────────────────────────
# Entry point
# ──────────────────────────────────────────────

def run_all_checks():
    print("=" * 55)
    print("  AWS Security Best Practices Audit")
    print("=" * 55)

    try:
        check_overly_permissive_iam_roles()
    except ClientError as e:
        print(f"  [error] Check 1 failed: {e}")

    try:
        check_iam_users_mfa_status()
    except ClientError as e:
        print(f"  [error] Check 2 failed: {e}")

    try:
        check_public_security_groups()
    except ClientError as e:
        print(f"  [error] Check 3 failed: {e}")

    try:
        check_unused_ec2_key_pairs()
    except ClientError as e:
        print(f"  [error] Check 4 failed: {e}")

    print("\nAudit complete. Review the generated CSV files.")


if __name__ == "__main__":
    run_all_checks()