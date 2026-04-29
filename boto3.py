import boto3
import time

region = "ap-south-1"

ec2 = boto3.client('ec2', region_name=region)
elbv2 = boto3.client('elbv2', region_name=region)
rds = boto3.client('rds', region_name=region)

# 🔹 YOUR VALUES (UPDATED)
KEY_NAME = "mayur2777"
DB_PASSWORD = "Mayur123!"
VPC_ID = "vpc-0d6d9f78d366471c0"
SUBNETS = ["subnet-099363d6c6c16971b", "subnet-0374f6a4c502b68b0"]
AMI_ID = "ami-05d2d839d4f73aafb"

# -------------------------------
# 1️⃣ CREATE SECURITY GROUPS
# -------------------------------

def create_sg(name, desc):
    sg = ec2.create_security_group(
        GroupName=name,
        Description=desc,
        VpcId=VPC_ID
    )
    sg_id = sg['GroupId']

    ec2.authorize_security_group_ingress(
        GroupId=sg_id,
        IpPermissions=[
            {'IpProtocol': 'tcp', 'FromPort': 80, 'ToPort': 80,
             'IpRanges': [{'CidrIp': '0.0.0.0/0'}]},
            {'IpProtocol': 'tcp', 'FromPort': 22, 'ToPort': 22,
             'IpRanges': [{'CidrIp': '0.0.0.0/0'}]}
        ]
    )
    return sg_id

frontend_sg = create_sg("frontend-sg", "Frontend SG")
backend_sg = create_sg("backend-sg", "Backend SG")
db_sg = create_sg("db-sg", "DB SG")


print("✅ Security Groups created")

# -------------------------------
# 2️⃣ CREATE RDS
# -------------------------------

print("⏳ Creating RDS...")

rds.create_db_instance(
    DBInstanceIdentifier='mydb',
    AllocatedStorage=20,
    DBName='mydb',
    Engine='mysql',
    MasterUsername='admin',
    MasterUserPassword=DB_PASSWORD,
    DBInstanceClass='db.t3.micro',
    VpcSecurityGroupIds=[db_sg],
    PubliclyAccessible=True
)

print("⏳ Waiting for DB (5 min)...")
time.sleep(300)

# -------------------------------
# 3️⃣ BACKEND EC2
# -------------------------------

backend_user_data = """#!/bin/bash
yum update -y
yum install python3 -y
pip3 install flask

cat <<EOF > app.py
from flask import Flask
app = Flask(__name__)

@app.route("/")
def home():
    return "Backend Running 🚀"

app.run(host='0.0.0.0', port=5000)
EOF

python3 app.py &
"""

backend = ec2.run_instances(
    ImageId=AMI_ID,
    InstanceType='t3.micro',   # ✅ CHANGED
    KeyName=KEY_NAME,
    MinCount=1,
    MaxCount=1,
    SecurityGroupIds=[backend_sg],
    SubnetId=SUBNETS[0],
    UserData=backend_user_data
)

backend_id = backend['Instances'][0]['InstanceId']
print("✅ Backend Instance:", backend_id)

# -------------------------------
# 4️⃣ FRONTEND EC2
# -------------------------------

frontend_user_data = """#!/bin/bash
yum update -y
yum install nginx -y
systemctl start nginx

echo "Frontend Working 🚀" > /usr/share/nginx/html/index.html
"""

frontend = ec2.run_instances(
    ImageId=AMI_ID,
    InstanceType='t3.micro',   # ✅ CHANGED
    KeyName=KEY_NAME,
    MinCount=1,
    MaxCount=1,
    SecurityGroupIds=[frontend_sg],
    SubnetId=SUBNETS[1],
    UserData=frontend_user_data
)

frontend_id = frontend['Instances'][0]['InstanceId']
print("✅ Frontend Instance:", frontend_id)

time.sleep(60)

# -------------------------------
# 5️⃣ CREATE ALB
# -------------------------------

lb = elbv2.create_load_balancer(
    Name='mayur-alb',
    Subnets=SUBNETS,
    SecurityGroups=[frontend_sg],
    Scheme='internet-facing',
    Type='application'
)

lb_arn = lb['LoadBalancers'][0]['LoadBalancerArn']
dns = lb['LoadBalancers'][0]['DNSName']

print("🌐 ALB DNS:", dns)

# -------------------------------
# 6️⃣ TARGET GROUP
# -------------------------------

tg = elbv2.create_target_group(
    Name='mayur-tg',
    Protocol='HTTP',
    Port=80,
    VpcId=VPC_ID,
    TargetType='instance'
)

tg_arn = tg['TargetGroups'][0]['TargetGroupArn']

elbv2.register_targets(
    TargetGroupArn=tg_arn,
    Targets=[{'Id': frontend_id}]
)

# -------------------------------
# 7️⃣ LISTENER
# -------------------------------

elbv2.create_listener(
    LoadBalancerArn=lb_arn,
    Protocol='HTTP',
    Port=80,
    DefaultActions=[{
        'Type': 'forward',
        'TargetGroupArn': tg_arn
    }]
)

print("🎉 DEPLOYMENT COMPLETE")
print("👉 Open in browser:", dns) 
