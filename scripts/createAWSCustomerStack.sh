#!/bin/bash
set -u

## LOAD required customer related vars
SCRIPT=$( basename ${BASH_SOURCE[0]} )
SCRIPT_DIR=$( dirname ${BASH_SOURCE[0]} )
CF_DIR="${SCRIPT_DIR}/../CloudFormation/"
. ${SCRIPT_DIR}/../vars.sh

echo "Script Dir: ${SCRIPT_DIR}"
echo "CloudFormation Dir: ${CF_DIR}"
echo "Customer: ${CUSTOMER_NAME}"
CUSTOMER_LOWER=$(echo "${CUSTOMER_NAME}" | tr '[:upper:]' '[:lower:]')
echo "Customer Lower: ${CUSTOMER_LOWER}"

## Create the main Stack
echo
echo "Creating Main customers stack 'sopsCustomer-${CUSTOMER_NAME}' using ${CF_FILE}"
aws cloudformation deploy --stack-name "sopsCustomer-${CUSTOMER_NAME}" \
                                  --capabilities CAPABILITY_NAMED_IAM \
                                  --template-file ${CF_DIR}/${CF_FILE} \
                                  --parameter-overrides CustomerName=${CUSTOMER_NAME} CustomerS3BucketName=${CUSTOMER_LOWER}
echo "--------------------"

# Create SQS Reponse Stack
echo
echo "Creating SQS Response stack 'sopsCustomer-${CUSTOMER_NAME}-sqs-command-response' using ${CF_SQS_RESP_FILE}"
if [[ ! -z "${CF_SQS_RESP_FILE}" ]]; then
  #SQS_RESPONSE_STACK_CHECK=$(aws cloudformation describe-stacks --stack-name "sopsCustomer-${CUSTOMER_NAME}-sqs-command-response" || echo "Does not exist")
  aws cloudformation deploy --stack-name "sopsCustomer-${CUSTOMER_NAME}-sqs-command-response" \
                            --capabilities CAPABILITY_NAMED_IAM \
                            --template-file ${CF_DIR}/${CF_SQS_RESP_FILE} \
                            --parameter-overrides CustomerName=${CUSTOMER_NAME}
fi
echo "--------------------"
