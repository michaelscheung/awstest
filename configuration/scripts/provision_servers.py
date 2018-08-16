import boto3
import csv
import json
import os
import time
from argparse import ArgumentParser
from itertools import islice, permutations

#    ____  _                  _                    _
#   |  _ \| | __ _  ___ ___  | | _____ _   _ ___  | |__   ___ _ __ ___
#   | |_) | |/ _` |/ __/ _ \ | |/ / _ | | | / __| | '_ \ / _ | '__/ _ \
#   |  __/| | (_| | (_|  __/ |   |  __| |_| \__ \ | | | |  __| | |  __/
#   |_|   |_|\__,_|\___\___| |_|\_\___|\__, |___/ |_| |_|\___|_|  \___|
#                                      |___/
YUPPIESCUM_EC2_PUB="""
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIKGKbJ6HuDz5iiY24qi1vCx8lMI9/xmeJrR9kqLCINip james@cantor
"""

YUMMYBUM_EC2_PUB="""
ssh-rsa AAAAB3NzaC1yc2EAAAABJQAAAQEA2a+C/zBVNiqaH6+BZ7K0bxsXdnLg6SDqZoXYRsr3aol6M2sHeug3Eqti0VC7U84VblcYIhKxe6neRP11SmD0X2uTUGAqzjSgnRc6YHy+iao8Va1iWWq58/RkROwjUAseOkaIj0M7J1Otu49WqAuvZ3fmiSu44TshbxBADcFo7eGjDiqe4WNYpDeuyAD9Ls2ZD23KeS1n5NNIR3t1B6Zof/IACi2waYPYDEuTOQHXRLnEbT5SDMKpQpRHdWbXa0dFBJZ0BjI07jeNNH95JmEmV8WB10RLa4yxVaYXPe8iqXYwakIokru/l1ixDtidWHXkc75SqKksoX4nMg9GlbAhDQ==
"""

PARAM_EC2_PUB = """
ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQDI0zNEdfCknkRSw6JcFdjVIWZ+x5bIijXtPHU42C8MuVUtiaZWbWEZ5EcA6lhqB7m5tx2UofgYwfSq7Vq1j/v9areKdDg98voTLeCz8dgIQkrcZtx2TNy2smbLPo/3S1n75dBkrkvTpDq95oqwqMQOEWKagL5UbdeyXR8S76SIi6du2F59/IrreHhYnpNgDWrj7uzr8M3wLXb/n6OUyYkCHQ/pGrko9QDmqOREriPjfSiAkrc8u+X2cpO9UCndPPPAFSy9yda46+WTGHrvS2G4VOnabMgLEidsFrk/yYYXeyCiSJK9MREUh7x2YQ1TVeO6PAs97JkYKk8LQDBro4kH
"""


EC2_PUB_ACCESS_KEYS = [
    YUPPIESCUM_EC2_PUB,
    YUMMYBUM_EC2_PUB,
    PARAM_EC2_PUB,
]

#    ____              _ _     _____                _       ____       _
#   |  _ \  ___  _ __ ( | |_  |_   ____  _   _  ___| |__   | __ )  ___| | _____      __
#   | | | |/ _ \| '_ \|/| __|   | |/ _ \| | | |/ __| '_ \  |  _ \ / _ | |/ _ \ \ /\ / /
#   | |_| | (_) | | | | | |_    | | (_) | |_| | (__| | | | | |_) |  __| | (_) \ V  V /
#   |____/ \___/|_| |_|  \__|   |_|\___/ \__,_|\___|_| |_| |____/ \___|_|\___/ \_/\_/
#

INSTALL_CODEDEPLOY_AGENT="""
yum -y update
yum install -y ruby
cd /home/ec2-user
curl --connect-timeout 5 --max-time 10 --retry 5 --retry-delay 0 --retry-max-time 40 -O https://aws-codedeploy-us-west-2.s3.amazonaws.com/latest/install
chmod +x ./install
./install auto
service codedeploy-agent start
chkconfig --add codedeploy-agent
chkconfig codedeploy-agent on
"""
INSTALL_DEPENDENCIES = """
# TODO openjdk -> just jre when prodified
yum install -y java-1.8.0-openjdk
yum install -y python36 python36-pip
yum install -y tcpdump wireshark ec2-net-utils
yum -y erase ntp* && sleep 8s && yum -y install chrony &&  sleep 8s && service chronyd start
chkconfig --add chronyd
chkconfig chronyd on
yum install -y iftop htop
pip-3.6 install boto3
"""
INSTALL_EC2_PUB_KEYS='\n'.join([
    'echo "{pub_key}" >> /home/ec2-user/.ssh/authorized_keys'.format(pub_key=key.strip())
    for key in EC2_PUB_ACCESS_KEYS
])

INSTALLATION_SCRIPT="""
#!/bin/bash -xe
{install_ec2_keys}
{install_deps}
{install_cdagent}
""".format(
    install_deps=INSTALL_DEPENDENCIES,
    install_cdagent=INSTALL_CODEDEPLOY_AGENT,
    install_ec2_keys=INSTALL_EC2_PUB_KEYS,
)

TAGS = [
    'polling-node',
    'transaction-node',
    'provisioning-status'
]
POLLING_NODE, TRANSACTION_NODE, PROVISION_STATUS  = TAGS

def get_currency_pairs():
    with open(os.path.join(os.path.dirname(__file__), "..", "data", "currencies.csv")) as fin:
        # TODO prolly don't need csv
        reader = csv.reader(fin)
        return frozenset(x[0].strip() for x in reader)

_CURRENCY_PAIRS = get_currency_pairs()


class InfraMangler:
    AMI_ID = 'ami-f2d3638a'

    # TODO yamlify
    CURRENCY_PAIRS = _CURRENCY_PAIRS
    """
        There is a default limit of 20 t2 instances in an account by default (of any size).
        We can request more, and I'd asssume we're likely to get them since we never burst
        up to limits + we're using nanos.  Until then, we would need to use two accounts or
        two regions, which makes deploying harder.  Gonna stick with 20 cap for now.
        Keep in mind, nothing prevents you from running on the trading server directly.
        https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/t2-instances.html#t2-instance-limits
    """
    #NUM_POLLING_INSTANCES = 25
    #NUM_POLLING_INSTANCES = 5
    NUM_NANO_POLLING_INSTANCES = 15
    NUM_MICRO_POLLING_INSTANCES = 4
    NUM_SMALL_POLLING_INSTANCES = 1
    NUM_TRANSACTION_POLLING_INSTANCES = 1


    def __init__(self,  **kwargs):
        _default_region = 'us-west-2'
        # FUTURE we could do more once we're trying to figure out where to put this shit
        self.ec2_resource =  boto3.resource('ec2', kwargs.get(os.environ.get('AWS_REGION', _default_region)))
        self.currencies = self.CURRENCY_PAIRS

    @classmethod
    def OPERATIONS(cls):
        return {
            'provision': cls.provision,
            'deploy': cls.deploy,
            'print': cls.display,
            'destructive_wipe': cls.terminate_instances,
        }
    @classmethod
    def get_args(cls, parser=ArgumentParser()):
        print(cls.OPERATIONS())
        parser.add_argument('--operation', choices=cls.OPERATIONS().keys(), required=True, default='print')
        parser.add_argument('--tags', choices=TAGS, required=True)
        parser.add_argument('--seriously', action='store_true', help='You reallllly want to do this?  You sure?')
        return parser.parse_args()

    def run(self):
        args = self.get_args()
        self.chosen_tags = args.tags.split(',')
        self.OPERATIONS()[args.operation](self, args)

    def provision(self, args):
        existing_instances = self._get_living_instances(tag_keys=self.chosen_tags)

        existing_nano_instances = self._get_living_instances(instance_type='t2.nano',
            tag_keys=[POLLING_NODE])
        existing_micro_instances = self._get_living_instances(instance_type='t2.micro',
            tag_keys=[POLLING_NODE])
        existing_small_instances = self._get_living_instances(instance_type='t2.small',
            tag_keys=[POLLING_NODE])
        existing_transaction_nodes = self._get_living_instances(instance_type='c5.xlarge',
            tag_keys=[TRANSACTION_NODE])

        num_nano_to_create = self.NUM_NANO_POLLING_INSTANCES - len(existing_nano_instances)
        num_micro_to_create = self.NUM_MICRO_POLLING_INSTANCES - len(existing_micro_instances)
        num_small_to_create = self.NUM_SMALL_POLLING_INSTANCES - len(existing_small_instances)
        num_transaction_to_create = 1 - len(existing_nano_instances)

        new_nano_instances = self._create_resources(num_nano_to_create, 't2.nano', tags=[POLLING_NODE])
        new_micro_instances = self._create_resources(num_micro_to_create, 't2.micro', tags=[POLLING_NODE])
        new_small_instances = self._create_resources(num_small_to_create, 't2.small', tags=[POLLING_NODE])
        new_transaction_instances = self._create_resources(num_transaction_to_create, 'c5.xlarge', tags=[TRANSACTION_NODE])

        all_polling_instances = \
            list(new_small_instances) + list(existing_small_instances) + \
            list(new_micro_instances) + list(existing_micro_instances) + \
            list(new_nano_instances) + list(existing_nano_instances)
        self._retag_instances(all_polling_instances)
        print(all_polling_instances)

    def deploy(self, args):
        pass

    def display(self, args):
        pass

    def terminate_instances(self, args):
        if not args.seriously:
            raise ValueError("You're not serious enough about wrecking our shit, try again")
        else:
            self._terminate_instances_for_tags(tag_keys=self.chosen_tags)

    def _group_tags(self, instances):
        return [ {
                'instance': instance,
                'id': idx,
            }
            for idx, instance in enumerate(instances)
        ]

    def _retag_instances(self, instances_to_tag):
        tag_groups = self._group_tags(instances_to_tag)
        print(tag_groups)
        print('Retagging instances')
        tagged = [
            instance.create_tags(Tags=[{'Key':POLLING_NODE,'Value':str(idx)}])
            for idx, instance in enumerate(instances_to_tag)
        ]
        return tag_groups

    def _terminate_instances_for_tags(self, tag_keys=TAGS):
        instances = self._get_living_instances(tag_keys=tag_keys)
        print ('Killing every instance matching tag(s) '+','.join(tag_keys))
        print ('Instances to be killed: '+','.join(instance.id for instance in instances))
        time.sleep(1)
        for instance in instances:
            print ('Terminating instance '+instance.id)
            time.sleep(0.2)
            instance.terminate()
        return self._get_living_instances(tag_keys=tag_keys)

    def _create_resources(self, num_to_create, instance_type, tags):
        if num_to_create < 1:
            print('Do not need to create any instances for '+str(tags))
            return set()
        elif not tags:
            raise ValueError("Invalid tag param "+str(tags))
        instances = self.ec2_resource.create_instances(
            ImageId=self.AMI_ID,
            InstanceType=instance_type,
            MinCount=num_to_create,
            MaxCount=num_to_create,
            KeyName='galois_rsa',
            #KeyName='cantor_rsa',
            UserData=INSTALLATION_SCRIPT,
            SecurityGroups=['arbitchrag'],
            IamInstanceProfile={'Name': 'Addy'},
            #IamInstanceProfile={'Name': 'Poller-Deployer'},
            Placement={
                'AvailabilityZone':'us-west-2c',
            },
            TagSpecifications=[ {
                    'ResourceType': 'instance',
                    'Tags': [ {
                            'Key': tag_key,
                            'Value': '',
                        }
                        for tag_key in tags
                    ]
            },],
        )
        print ('Created instances with ids: '+','.join(i.id for i in instances))
        return set(instances)

    def _get_living_instances(self, *, instance_type=None, tag_keys=TAGS, tag_values=[]):
        # AWS is fucking lame and doesn't provide collections with a len
        tag_keys = [{
                'Name': 'tag-key',
                'Values':  tag_keys,
        }]
        tag_values = [{
                'Name': 'tag:'+str(key),
                'Values': values,
            }
            for key, values in tag_values
        ]
        state = [{'Name': 'instance-state-name', 'Values': ['running', 'pending']}]
        size = [{'Name': 'instance-type', 'Values': [instance_type]}] if instance_type else []
        filters = tag_keys + tag_values + state + size
        # boto3 is cunty and returns an iterable without a __len__ TODO pull request those sexual beasts
        return set(self.ec2_resource.instances.filter(Filters=filters))

    def _instances_to_ids(self, creation_response):
        return [instance.id for instance in creation_response]

if __name__ == '__main__':
    InfraMangler().run()
