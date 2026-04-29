import boto3
import time
import os

# -----------------------------
# CONFIG (YOUR VALUES)
# -----------------------------
REGION = "ap-south-1"
BUCKET_NAME = "mayur-auto-bucket-98765432111"   # CHANGE if error (must be unique)
KEY_NAME = "mayur2777"
SECURITY_GROUP_NAME = "mayurr-sg"
AMI_ID = "ami-0e12ffc2dd465f6e4"
INSTANCE_TYPE = "t3.micro"

# -----------------------------
# CLIENTS
# -----------------------------
ec2 = boto3.client('ec2', region_name=REGION)
s3 = boto3.client('s3', region_name=REGION)

# -----------------------------
# 1. CREATE S3 BUCKET
# -----------------------------
def create_bucket():
    try:
        print("Creating S3 bucket...")
        s3.create_bucket(
            Bucket=BUCKET_NAME,
            CreateBucketConfiguration={'LocationConstraint': REGION}
        )
        print("✅ S3 Bucket Created")
    except Exception as e:
        print("⚠️ Bucket issue:", e)

# -----------------------------
# 2. CREATE KEY PAIR (ONLY IF NOT EXISTS)
# -----------------------------
def create_keypair():
    try:
        print("Checking/Creating Key Pair...")
        response = ec2.create_key_pair(KeyName=KEY_NAME)

        with open(KEY_NAME + ".pem", "w") as f:
            f.write(response['KeyMaterial'])

        os.chmod(KEY_NAME + ".pem", 0o400)
        print("✅ Key Pair Created & Saved")
    except Exception:
        print("⚠️ Key already exists, skipping...")

# -----------------------------
# 3. CREATE SECURITY GROUP
# -----------------------------
def create_security_group():
    print("Creating Security Group...")

    vpc_id = ec2.describe_vpcs()['Vpcs'][0]['VpcId']

    try:
        response = ec2.create_security_group(
            GroupName=SECURITY_GROUP_NAME,
            Description='Allow HTTP & SSH',
            VpcId=vpc_id
        )
        sg_id = response['GroupId']

        ec2.authorize_security_group_ingress(
            GroupId=sg_id,
            IpPermissions=[
                {
                    'IpProtocol': 'tcp',
                    'FromPort': 22,
                    'ToPort': 22,
                    'IpRanges': [{'CidrIp': '0.0.0.0/0'}]
                },
                {
                    'IpProtocol': 'tcp',
                    'FromPort': 80,
                    'ToPort': 80,
                    'IpRanges': [{'CidrIp': '0.0.0.0/0'}]
                }
            ]
        )

        print("✅ Security Group Created:", sg_id)
        return sg_id

    except Exception:
        print("⚠️ SG exists, fetching existing...")

        groups = ec2.describe_security_groups(GroupNames=[SECURITY_GROUP_NAME])
        return groups['SecurityGroups'][0]['GroupId']

# -----------------------------
# 4. LAUNCH EC2
# -----------------------------
def launch_instance(sg_id):
    print("Launching EC2...")

    user_data = '''#!/bin/bash
    yum update -y
    yum install -y httpd
    systemctl start httpd
    systemctl enable httpd
    echo "Hello Mayur 🚀 from t3.micro" > /var/www/html/index.html
    '''

    response = ec2.run_instances(
        ImageId=AMI_ID,
        InstanceType=INSTANCE_TYPE,
        KeyName=KEY_NAME,
        SecurityGroupIds=[sg_id],
        MinCount=1,
        MaxCount=1,
        UserData=user_data
    )

    instance_id = response['Instances'][0]['InstanceId']
    print("✅ Instance ID:", instance_id)
    return instance_id

# -----------------------------
# 5. GET PUBLIC IP
# -----------------------------
def get_ip(instance_id):
    print("Waiting for instance to run...")

    waiter = ec2.get_waiter('instance_running')
    waiter.wait(InstanceIds=[instance_id])

    desc = ec2.describe_instances(InstanceIds=[instance_id])
    ip = desc['Reservations'][0]['Instances'][0]['PublicIpAddress']

    print("\n🌐 WEBSITE READY:")
    print(f"http://{ip}")

# -----------------------------
# MAIN
# -----------------------------
def main():
    create_bucket()
    create_keypair()
    sg_id = create_security_group()
    instance_id = launch_instance(sg_id)
    get_ip(instance_id)

if __name__ == "__main__":
    main()
