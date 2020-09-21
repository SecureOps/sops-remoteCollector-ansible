#!/bin/bash
set -e
set -u

## LOAD required customer related vars
SCRIPT=$( basename ${BASH_SOURCE[0]} )
SCRIPT_DIR=$( dirname ${BASH_SOURCE[0]} )
CF_DIR="${SCRIPT_DIR}/../CloudFormation/"
# SCRIPT_DIR=$( readlink ${SCRIPT_DIR} )
. ${SCRIPT_DIR}/../vars.sh
echo "Script Dir: ${SCRIPT_DIR}"
echo "CloudFormation Dir: ${CF_DIR}"
echo "Customer: ${CUSTOMER_NAME}"
CUSTOMER_LOWER=$(echo "${CUSTOMER_NAME}" | tr '[:upper:]' '[:lower:]')
echo "Customer Lower: ${CUSTOMER_LOWER}"

# Check if the customer stack exists
CUST_STACK_CHECK=$(aws cloudformation describe-stacks --stack-name "sopsCustomer-${CUSTOMER_NAME}" || echo "Does not exist")
if [[ $CUST_STACK_CHECK =~ "not exist" ]]; then
  aws cloudformation create-stack --stack-name "sopsCustomer-${CUSTOMER_NAME}" \
                                  --capabilities CAPABILITY_NAMED_IAM \
                                  --template-body file://${CF_DIR}/${CF_FILE} \
                                  --parameters ParameterKey=CustomerName,ParameterValue=${CUSTOMER_NAME} ParameterKey=CustomerS3BucketName,ParameterValue=${CUSTOMER_LOWER}
else

  aws cloudformation deploy --stack-name "sopsCustomer-${CUSTOMER_NAME}" \
                                  --capabilities CAPABILITY_NAMED_IAM \
                                  --template-file ${CF_DIR}/${CF_FILE} \
                                  --parameter-overrides ParameterKey=CustomerName,ParameterValue=${CUSTOMER_NAME} ParameterKey=CustomerS3BucketName,ParameterValue=${CUSTOMER_LOWER}
fi

echo ${CF_SQS_RESP_FILE}
if [[ ! -z "${CF_SQS_RESP_FILE}" ]]; then
  # Check if the SQS response stack exists
  SQS_RESPONSE_STACK_CHECK=$(aws cloudformation describe-stacks --stack-name "sopsCustomer-${CUSTOMER_NAME}-sqs-command-response" || echo "Does not exist")
  if [[ $SQS_RESPONSE_STACK_CHECK =~ "not exist" ]]; then
    aws cloudformation create-stack --stack-name "sopsCustomer-${CUSTOMER_NAME}-sqs-command-response" \
                                    --capabilities CAPABILITY_NAMED_IAM \
                                    --template-body file://${CF_DIR}/${CF_SQS_RESP_FILE} \
                                    --parameters ParameterKey=CustomerName,ParameterValue=${CUSTOMER_NAME}
  else

    aws cloudformation deploy --stack-name "sopsCustomer-${CUSTOMER_NAME}-sqs-command-response" \
                                    --capabilities CAPABILITY_NAMED_IAM \
                                    --template-file ${CF_DIR}/${CF_SQS_RESP_FILE} \
                                    --parameter-overrides ParameterKey=CustomerName,ParameterValue=${CUSTOMER_NAME}
  fi
fi
