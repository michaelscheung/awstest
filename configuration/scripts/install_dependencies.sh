#!/bin/bash
echo "All the installation has been moved to provisioning time (under UserData)"
echo "Creating directories"
mkdir -p /etc/yc-info
INSTANCE_ID=`wget -qO- http://instance-data/latest/meta-data/instance-id`
REGION=`wget -qO- http://instance-data/latest/meta-data/placement/availability-zone | sed 's/.$//'`
echo "Getting tag data"
aws ec2 describe-tags --region $REGION --filter "Name=resource-id,Values=$INSTANCE_ID" --output=text | sed -r 's/TAGS\t(.*)\t.*\t.*\t(.*)/\1="\2"/' > /etc/yc-info/ec2-tags
echo "Writing $INSTANCE_ID"
echo $INSTANCE_ID > /etc/yc-info/instance_id
echo "Writing $REGION"
echo $REGION > /etc/yc-info/region

echo "Cleaning up temp"
rm -Rf /tmp/*
