client = boto3.client('codedeploy', 'us-west-2')

def get_all_applications():
    response = client.list_applications()
    applications = response['applications']
    next_token = applications['nextToken']
    while next_token:
        response = client.list_applications(nextToken=next_token)
        applications.extend(response['applications'])
        next_token = response['nextToken']
    return applications

def get_relay_application():
    def find_relay_app(applications):
        return [app for app in applications if 'relay' in app.lower

    response = client.list_applications()
    relay_app = find_relay_app(response['applications'])
    if relay_app:
        return relay_app
    next_token = applications['nextToken']
    while next_token:
        response = client.list_applications(nextToken=next_token)
        relay_app = find_relay_app(response['applications'])
        if relay_app:
            return relay_app
        next_token = response['nextToken']
    raise ValueError("Did not find relay app")

RELAY_APPLICATION_NAME = next(iter(get_relay_application()))
REVISIONS_BUCKET = 'test-pipeline-cdbucket-k1huvaurl9d1'
REVISIONS_PREFIX = 'test-pipeline-Pipeli/RelayBuild/


def get_all_deployments(next_token):
    kwargs = dict(
        applicationName=RELAY_APPLICATION_NAME,
        deploymentGroupName='string',
        includeOnlyStatuses=[
            'Created','Queued','InProgress','Succeeded',
        ],
        createTimeRange={
            'start': datetime(2018, 05, 01)
        },
    )
    if next_token:
        kwargs['nextToken'] = next_token
    response = client.list_deployments(**kwargs)
    rest = get_all_deployments(response['nextToken']) if 'nextToken' in response else []
    # No tail call recursion in python =(
    return rest + response['deployments']


def get_deployment_groups(app_name):
    response = client.list_deployment_groups(
        applicationName=app_name,
        nextToken='string'
    )
    deployment_groups = response['deployment_groups']
    next_token = response['nextToken']
    while next_token:
        response = client.list_deployment_groups(
            applicationName=app_name,
            nextToken=next_token
        )
        deployment_groups.extend(response['deployment_groups'])
    return deployment_groups

deployment_ids = get_all_deployments()
response = client.batch_get_deployments(deploymentIds=deployment_ids)
deployments = response['deployments']


client.create_deployment(
    applicationName=REVISIONS_BUCKET,
    deploymentGroupName='string',
    revision={
        'revisionType': 'S3'|'GitHub'|'String',
        's3Location': {
            'bucket': 'test-pipeline-cdbucket-k1huvaurl9d1',
            'key': 'test-pipeline-Pipeli/RelayBuild/06irpAA',
            'bundleType': 'zip',
            'version': 'string',
            'eTag': 'string'
        },
        'gitHubLocation': {
            'repository': 'string',
            'commitId': 'string'
        },
        'string': {
            'content': 'string',
            'sha256': 'string'
        }
    },
    deploymentConfigName='string',
    description='string',
    ignoreApplicationStopFailures=True|False,
    targetInstances={
        'tagFilters': [
            {
                'Key': 'polling-node',
                'Type': 'KEY_ONLY'
            },
        ],
    },
    autoRollbackConfiguration={
        'enabled': True,
        'events': [
            'DEPLOYMENT_FAILURE', 'DEPLOYMENT_STOP_ON_ALARM', 'DEPLOYMENT_STOP_ON_REQUEST',
        ]
    },
    updateOutdatedInstancesOnly=True|False,
    fileExistsBehavior='OVERWRITE'
)
