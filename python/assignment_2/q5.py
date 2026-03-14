"""
AWS Cost Optimization Audit Script
Checks:
  1. EC2 instances with average CPU < 10% over the last 30 days
  2. RDS instances with zero database connections over the last 7 days
  3. Lambda functions not invoked in the last 30 days
  4. S3 buckets that are empty or have had no recent access
"""

import boto3
from datetime import datetime, timezone, timedelta


# ──────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────

LOW_CPU_THRESHOLD_PERCENT   = 10.0   # flag EC2 if avg CPU is below this
RDS_IDLE_DAYS               = 7      # flag RDS if no connections for this many days
LAMBDA_INACTIVE_DAYS        = 30     # flag Lambda if no invocations for this many days
S3_RECENT_ACCESS_DAYS       = 30     # flag S3 if no objects accessed within this window

NOW        = datetime.now(timezone.utc)
DAYS_30    = NOW - timedelta(days=30)
DAYS_7     = NOW - timedelta(days=7)


# ──────────────────────────────────────────────
# Helper – CloudWatch metric average
# ──────────────────────────────────────────────

def get_cloudwatch_metric_average(cw_client, namespace, metric_name,
                                   dimensions, start_time, end_time,
                                   period_seconds=86400):
    """
    Return the average of all datapoints for a CloudWatch metric,
    or None when no data is available.
    """
    response = cw_client.get_metric_statistics(
        Namespace=namespace,
        MetricName=metric_name,
        Dimensions=dimensions,
        StartTime=start_time,
        EndTime=end_time,
        Period=period_seconds,
        Statistics=["Average"],
    )
    datapoints = response.get("Datapoints", [])
    if not datapoints:
        return None
    return sum(dp["Average"] for dp in datapoints) / len(datapoints)


def get_cloudwatch_metric_sum(cw_client, namespace, metric_name,
                               dimensions, start_time, end_time,
                               period_seconds=86400):
    """
    Return the sum of all datapoints for a CloudWatch metric,
    or None when no data is available.
    """
    response = cw_client.get_metric_statistics(
        Namespace=namespace,
        MetricName=metric_name,
        Dimensions=dimensions,
        StartTime=start_time,
        EndTime=end_time,
        Period=period_seconds,
        Statistics=["Sum"],
    )
    datapoints = response.get("Datapoints", [])
    if not datapoints:
        return None
    return sum(dp["Sum"] for dp in datapoints)


# ──────────────────────────────────────────────
# Check 1 – Underutilised EC2 instances
# ──────────────────────────────────────────────

def find_underutilised_ec2_instances():
    """
    Return a list of dicts for running EC2 instances whose average
    CPU utilisation over the last 30 days is below LOW_CPU_THRESHOLD_PERCENT.
    """
    ec2 = boto3.client("ec2")
    cw  = boto3.client("cloudwatch")
    flagged = []

    paginator = ec2.get_paginator("describe_instances")
    for page in paginator.paginate(
        Filters=[{"Name": "instance-state-name", "Values": ["running"]}]
    ):
        for reservation in page["Reservations"]:
            for instance in reservation["Instances"]:
                instance_id   = instance["InstanceId"]
                instance_type = instance["InstanceType"]

                # Derive a friendly name from tags when available
                name_tag = next(
                    (t["Value"] for t in instance.get("Tags", []) if t["Key"] == "Name"),
                    instance_id,
                )

                avg_cpu = get_cloudwatch_metric_average(
                    cw,
                    namespace="AWS/EC2",
                    metric_name="CPUUtilization",
                    dimensions=[{"Name": "InstanceId", "Value": instance_id}],
                    start_time=DAYS_30,
                    end_time=NOW,
                )

                # No data at all means the instance is almost certainly idle
                if avg_cpu is None or avg_cpu < LOW_CPU_THRESHOLD_PERCENT:
                    flagged.append({
                        "InstanceId":   instance_id,
                        "Name":         name_tag,
                        "InstanceType": instance_type,
                        "AvgCPU":       round(avg_cpu, 2) if avg_cpu is not None else "N/A",
                    })

    return flagged


# ──────────────────────────────────────────────
# Check 2 – Idle RDS instances
# ──────────────────────────────────────────────

def find_idle_rds_instances():
    """
    Return a list of dicts for available RDS instances that have had
    zero database connections over the last RDS_IDLE_DAYS days.
    """
    rds = boto3.client("rds")
    cw  = boto3.client("cloudwatch")
    flagged = []

    paginator = rds.get_paginator("describe_db_instances")
    for page in paginator.paginate():
        for db in page["DBInstances"]:
            if db["DBInstanceStatus"] != "available":
                continue

            db_id     = db["DBInstanceIdentifier"]
            db_engine = db["Engine"]

            total_connections = get_cloudwatch_metric_sum(
                cw,
                namespace="AWS/RDS",
                metric_name="DatabaseConnections",
                dimensions=[{"Name": "DBInstanceIdentifier", "Value": db_id}],
                start_time=NOW - timedelta(days=RDS_IDLE_DAYS),
                end_time=NOW,
            )

            # Zero or no data means the database has been idle
            if total_connections is None or total_connections == 0:
                flagged.append({
                    "DBInstanceId":     db_id,
                    "Engine":           db_engine,
                    "TotalConnections": total_connections if total_connections is not None else "N/A",
                })

    return flagged


# ──────────────────────────────────────────────
# Check 3 – Inactive Lambda functions
# ──────────────────────────────────────────────

def find_inactive_lambda_functions():
    """
    Return a list of dicts for Lambda functions that have had zero
    invocations over the last LAMBDA_INACTIVE_DAYS days.
    """
    lam = boto3.client("lambda")
    cw  = boto3.client("cloudwatch")
    flagged = []

    paginator = lam.get_paginator("list_functions")
    for page in paginator.paginate():
        for fn in page["Functions"]:
            fn_name    = fn["FunctionName"]
            runtime    = fn.get("Runtime", "N/A")
            last_mod   = fn.get("LastModified", "N/A")

            total_invocations = get_cloudwatch_metric_sum(
                cw,
                namespace="AWS/Lambda",
                metric_name="Invocations",
                dimensions=[{"Name": "FunctionName", "Value": fn_name}],
                start_time=DAYS_30,
                end_time=NOW,
            )

            if total_invocations is None or total_invocations == 0:
                flagged.append({
                    "FunctionName":      fn_name,
                    "Runtime":           runtime,
                    "LastModified":      last_mod,
                    "TotalInvocations":  total_invocations if total_invocations is not None else "N/A",
                })

    return flagged


# ──────────────────────────────────────────────
# Check 4 – Unused / empty S3 buckets
# ──────────────────────────────────────────────

def get_bucket_object_count(s3_client, bucket_name):
    """Return the number of objects in a bucket (0 means empty)."""
    response = s3_client.list_objects_v2(Bucket=bucket_name, MaxKeys=1)
    return response.get("KeyCount", 0)


def get_bucket_last_access(cw_client, bucket_name):
    """
    Use the S3 NumberOfObjects and BucketSizeBytes metrics as a proxy.
    For a true last-access check we look at S3 request metrics; fall back
    to None when request-level metrics are not enabled.
    """
    total_requests = get_cloudwatch_metric_sum(
        cw_client,
        namespace="AWS/S3",
        metric_name="AllRequests",
        dimensions=[
            {"Name": "BucketName",  "Value": bucket_name},
            {"Name": "FilterId",    "Value": "EntireBucket"},
        ],
        start_time=NOW - timedelta(days=S3_RECENT_ACCESS_DAYS),
        end_time=NOW,
    )
    return total_requests


def find_unused_s3_buckets():
    """
    Return a list of dicts for S3 buckets that are either empty or have
    had no recorded requests in the last S3_RECENT_ACCESS_DAYS days.
    """
    s3  = boto3.client("s3")
    cw  = boto3.client("cloudwatch")
    flagged = []

    buckets = s3.list_buckets().get("Buckets", [])
    for bucket in buckets:
        bucket_name    = bucket["Name"]
        creation_date  = bucket["CreationDate"].strftime("%Y-%m-%d")

        object_count   = get_bucket_object_count(s3, bucket_name)
        recent_requests = get_bucket_last_access(cw, bucket_name)

        is_empty         = object_count == 0
        # None means S3 request metrics aren't enabled for this bucket
        has_recent_access = (recent_requests is not None and recent_requests > 0)

        if is_empty or not has_recent_access:
            flagged.append({
                "BucketName":     bucket_name,
                "CreationDate":   creation_date,
                "ObjectCount":    object_count,
                "RecentRequests": recent_requests if recent_requests is not None else "metrics-not-enabled",
                "IsEmpty":        is_empty,
            })

    return flagged


# ──────────────────────────────────────────────
# Summary report printer
# ──────────────────────────────────────────────

SEPARATOR = "─" * 60

def print_section_header(title):
    print(f"\n{SEPARATOR}")
    print(f"  {title}")
    print(SEPARATOR)


def print_summary_report(ec2_results, rds_results, lambda_results, s3_results):
    print("\n" + "=" * 60)
    print("   AWS COST OPTIMISATION AUDIT REPORT")
    print(f"   Generated: {NOW.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print("=" * 60)

    # ── EC2 ──────────────────────────────────
    print_section_header(
        f"Check 1: Underutilised EC2 Instances  "
        f"(avg CPU < {LOW_CPU_THRESHOLD_PERCENT}% over 30 days)"
    )
    if ec2_results:
        for r in ec2_results:
            cpu_display = f"{r['AvgCPU']}%" if r["AvgCPU"] != "N/A" else "No data"
            print(
                f"  • {r['InstanceId']} ({r['Name']})  |  "
                f"Type: {r['InstanceType']}  |  Avg CPU: {cpu_display}"
            )
        print(f"\n  Recommended action : Stop or rightsize these {len(ec2_results)} instance(s).")
    else:
        print("  ✓ No underutilised EC2 instances found.")

    # ── RDS ──────────────────────────────────
    print_section_header(
        f"Check 2: Idle RDS Instances  "
        f"(no connections in last {RDS_IDLE_DAYS} days)"
    )
    if rds_results:
        for r in rds_results:
            print(
                f"  • {r['DBInstanceId']}  |  "
                f"Engine: {r['Engine']}  |  "
                f"Connections (7d): {r['TotalConnections']}"
            )
        print(f"\n  Recommended action : Delete or stop these {len(rds_results)} RDS instance(s).")
    else:
        print("  ✓ No idle RDS instances found.")

    # ── Lambda ───────────────────────────────
    print_section_header(
        f"Check 3: Inactive Lambda Functions  "
        f"(no invocations in last {LAMBDA_INACTIVE_DAYS} days)"
    )
    if lambda_results:
        for r in lambda_results:
            print(
                f"  • {r['FunctionName']}  |  "
                f"Runtime: {r['Runtime']}  |  "
                f"Invocations (30d): {r['TotalInvocations']}"
            )
        print(f"\n  Recommended action : Review and delete these {len(lambda_results)} function(s) if no longer needed.")
    else:
        print("  ✓ No inactive Lambda functions found.")

    # ── S3 ───────────────────────────────────
    print_section_header(
        f"Check 4: Unused / Empty S3 Buckets  "
        f"(empty or no activity in last {S3_RECENT_ACCESS_DAYS} days)"
    )
    if s3_results:
        for r in s3_results:
            empty_label = "EMPTY" if r["IsEmpty"] else "no recent requests"
            print(
                f"  • {r['BucketName']}  |  "
                f"Created: {r['CreationDate']}  |  "
                f"Objects: {r['ObjectCount']}  |  "
                f"Status: {empty_label}"
            )
        print(f"\n  Recommended action : Delete or archive these {len(s3_results)} bucket(s).")
    else:
        print("  ✓ No unused S3 buckets found.")

    # ── Overall summary ──────────────────────
    total_issues = (
        len(ec2_results) + len(rds_results) +
        len(lambda_results) + len(s3_results)
    )
    print(f"\n{'=' * 60}")
    print(f"  TOTAL RESOURCES FLAGGED FOR COST SAVINGS: {total_issues}")
    print(f"{'=' * 60}\n")


# ──────────────────────────────────────────────
# Entry point
# ──────────────────────────────────────────────

def run_cost_optimisation_audit():
    print("Starting AWS Cost Optimisation Audit …")

    print("  [1/4] Checking EC2 CPU utilisation …")
    ec2_results = find_underutilised_ec2_instances()

    print("  [2/4] Checking RDS connection metrics …")
    rds_results = find_idle_rds_instances()

    print("  [3/4] Checking Lambda invocation metrics …")
    lambda_results = find_inactive_lambda_functions()

    print("  [4/4] Checking S3 bucket usage …")
    s3_results = find_unused_s3_buckets()

    print_summary_report(ec2_results, rds_results, lambda_results, s3_results)


if __name__ == "__main__":
    run_cost_optimisation_audit()