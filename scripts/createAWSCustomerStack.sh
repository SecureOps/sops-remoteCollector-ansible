#!/bin/bash
set -e
set -u

## LOAD required customer related vars
SCRIPT_DIR=$( dirname ${BASH_SOURCE[0]} )
# SCRIPT_DIR=$( readlink ${SCRIPT_DIR} )
. ${SCRIPT_DIR}/../vars.sh
echo "Script Dir: ${SCRIPT_DIR}"
echo "Customer: ${CUSTOMER_NAME}"
CUSTOMER_LOWER=$(echo "${CUSTOMER_NAME}" | tr '[:upper:]' '[:lower:]')
echo "Customer Lower: ${CUSTOMER_LOWER}"

# Check if the stack exists
CUST_STACK_CHECK=$(aws cloudformation describe-stacks --stack-name "sopsCustomer-${CUSTOMER_NAME}" || echo "Does not exist")
if [[ $CUST_STACK_CHECK =~ "not exist" ]]; then
  aws cloudformation create-stack --stack-name "sopsCustomer-${CUSTOMER_NAME}" \
                                  --capabilities CAPABILITY_NAMED_IAM \
                                  --template-body file://${SCRIPT_DIR}/${CF_FILE} \
                                  --parameters ParameterKey=CustomerName,ParameterValue=${CUSTOMER_NAME} ParameterKey=CustomerS3BucketName,ParameterValue=${CUSTOMER_LOWER}
else

  aws cloudformation deploy --stack-name "sopsCustomer-${CUSTOMER_NAME}" \
                                  --capabilities CAPABILITY_NAMED_IAM \
                                  --template-file ${SCRIPT_DIR}/${CF_FILE} \
                                  --parameter-overrides ParameterKey=CustomerName,ParameterValue=${CUSTOMER_NAME} ParameterKey=CustomerS3BucketName,ParameterValue=${CUSTOMER_LOWER}
fi

REMOTE_STACK_CHECK=$(aws cloudformation describe-stacks --stack-name "sopsCustomer-${CUSTOMER_NAME}-${REMOTE_NODE_NAME}" || echo "Does not exist")
if [[ $REMOTE_STACK_CHECK =~ "not exist" ]]; then
  aws cloudformation create-stack --stack-name "sopsCustomer-${CUSTOMER_NAME}-${REMOTE_NODE_NAME}" \
                                  --capabilities CAPABILITY_NAMED_IAM \
                                  --template-body file://${SCRIPT_DIR}/${REMOTE_NODE_CF_FILE} \
                                  --parameters ParameterKey=RemoteNodeName,ParameterValue=${REMOTE_NODE_NAME} ParameterKey=CustomerName,ParameterValue=${CUSTOMER_NAME} ParameterKey=CustomerS3BucketName,ParameterValue=${CUSTOMER_LOWER}

else
  aws cloudformation deploy --stack-name "sopsCustomer-${CUSTOMER_NAME}-${REMOTE_NODE_NAME}" \
                                  --capabilities CAPABILITY_NAMED_IAM \
                                  --template-file ${SCRIPT_DIR}/${REMOTE_NODE_CF_FILE} \
                                  --parameter-overrides ParameterKey=RemoteNodeName,ParameterValue=${REMOTE_NODE_NAME} ParameterKey=CustomerName,ParameterValue=${CUSTOMER_NAME} ParameterKey=CustomerS3BucketName,ParameterValue=${CUSTOMER_LOWER}
fi
