import boto3


def main():
    print(f"--- Welcome to Boto3 ---")
    # Creating client of aws API's for a specific service
    # In our current case, the client will hold s3 features only here
    client = boto3.client('s3', region_name='ap-south-1')
    
    
    response = client.create_bucket(
        Bucket='test-with-boto3-2',
        CreateBucketConfiguration={'LocationConstraint': 'ap-south-1'}
    )
    
    print(f"Response: {response}")


if __name__ == "__main__":
    main()
