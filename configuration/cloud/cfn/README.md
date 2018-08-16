
# EC2 Infra

Creation:

```
# Create the stack
aws cloudformation create-stack --stack-name TEST-EC2-INFRA --region us-west-2 --template-body file:///$(pwd)/configuration/cloud/cfn/trading-infrastructure.yml --parameters  ParameterKey=NumT2NanoPollingNodes,ParameterValue=6 --capabilities CAPABILITY_IAM
```

Deletion:

```
# Delete the stack
aws cloudformation delete-stack --stack-name TEST-EC2-INFRA
```
