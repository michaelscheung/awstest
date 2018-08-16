#!/usr/bin/python36
import boto3
import json
import os
import sys
import csv
print("Starting servers..")
# import logging
# _LOGGER = logging.getLogger(__name__)
# _LOGGER.setLevel(logging.DEBUG)
# EC2 is a shit service and won't let you easily get the current region on ec2 unless you
# send a fucking http request to a magical static ip
# Whoever designed that is an asshole.  It's worse than global s3 bucket namespace.  Senseless.  Ugh.
ec2_resource = boto3.resource('ec2', region_name='us-west-2')
# TODO may want to use update-alternative instead of specifying java8

DEPLOYMENT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
JAR_PATH = os.path.join(DEPLOYMENT_PATH, 'target', 'esbenshade-1.0-SNAPSHOT-jar-with-dependencies.jar')

HEAP_SIZE = "2048m"

def get_agg_host():
    tag_keys = [{
        'Name': 'tag-key',
        'Values':  ['transaction-node'],
    }]
    state = [{'Name': 'instance-state-name', 'Values': ['running', 'pending']}]
    filters = tag_keys + state
    # boto3 is cunty and returns an iterable without a __len__ TODO pull request those sexual beasts
    return [instance.private_ip_address for instance in ec2_resource.instances.filter(Filters=filters)]


# TODO allow this to be an array
AGG_HOST = get_agg_host()[0]

def get_currency_pairs():
    if is_transaction_server():
        return []
    with open('/etc/yc-info/ec2-tags', 'r') as fin:
        # TODO currently returns something like 'polling-node="ETH/BTC"'
        for line in fin.readlines():
            if line.startswith('polling-node="'):
                instance_num = line[len('polling-node="'):-2]
                with open(os.path.join(os.path.dirname(__file__),'..','data', 'pair_data', 'instance-{}.json'.format(instance_num))) as fin:
                    return fin.read().strip().split(',')
        raise ValueError("Could not find tag for polling-node")

def is_transaction_server():
    with open('/etc/yc-info/ec2-tags', 'r') as fin:
        # TODO currently returns something like 'polling-node="ETH/BTC"'
        for line in fin.readlines():
            if line.startswith('transaction-node="'):
                return True
        return False

POLLING_SERVER_SCRIPT = """
export DEPLOYMENT_PATH="{deployment_path}"
export LOG_PATH=/tmp/$DEPLOYMENT_PATH
echo "Creating deployment path /tmp/"
mkdir -p $LOG_PATH/log/rolling-logs;
STAGE=prod AGG_HOST="{agg_host}" CONFIG_FILENAME="prod-relay.yaml" LOG_PATH=$LOG_PATH/log CURRENCY_PAIRS="{currency_pairs}" java8 -cp {jar_path} remote.polling.ExchangePollerKt  -Xmx512m > $LOG_PATH/polling-server.log  2> $LOG_PATH/polling-server-errors.log < /dev/null &
"""

TRANSACTION_SERVER_SCRIPT = """
export DEPLOYMENT_PATH="{deployment_path}"
export LOG_PATH=/tmp/$DEPLOYMENT_PATH
echo "Creating deployment path /tmp/"
mkdir -p $LOG_PATH/log/rolling-logs;
STAGE=prod CONFIG_FILENAME="prod-trader.yaml" LOG_PATH=$LOG_PATH/log java8 -cp {jar_path} AppKt -Xmx{heap_size} > $LOG_PATH/transaction-server.log 2> $LOG_PATH/transaction-server-errors.log < /dev/null &
"""
CURRENCY_PAIRS = ','.join(get_currency_pairs())

print("Currency Pairs: "+','.join(CURRENCY_PAIRS))


def start_polling_server():
    print("Starting process for currency pairs "+str(CURRENCY_PAIRS))
    cmd = POLLING_SERVER_SCRIPT.format(jar_path=JAR_PATH, agg_host=AGG_HOST, currency_pairs=CURRENCY_PAIRS, deployment_path=DEPLOYMENT_PATH)
    print ("running command "+str(cmd))
    os.system(cmd)


def start_transaction_server():
    print("Starting transaction server")
    cmd = TRANSACTION_SERVER_SCRIPT.format(jar_path=JAR_PATH, deployment_path=DEPLOYMENT_PATH, heap_size=HEAP_SIZE)
    print ("running command "+str(cmd))
    os.system(cmd)

if is_transaction_server():
    start_transaction_server()
else:
    print("Not a transaction node")

if CURRENCY_PAIRS:
    # hacky hook to start polling stuff
    start_polling_server()
    print("Started polling server")
else:
    print("Appears that we didn't specify any currency pairs for this server")
