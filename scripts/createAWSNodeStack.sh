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

## Create Node Stack
echo
echo "Creating Node stack 'sopsCustomer-${CUSTOMER_NAME}-${REMOTE_NODE_NAME}' using ${REMOTE_NODE_CF_FILE}"
aws cloudformation deploy --stack-name "sopsCustomer-${CUSTOMER_NAME}-${REMOTE_NODE_NAME}" \
                                  --capabilities CAPABILITY_NAMED_IAM \
                                  --template-file ${CF_DIR}/${REMOTE_NODE_CF_FILE} \
                                  --parameter-overrides RemoteNodeName=${REMOTE_NODE_NAME} CustomerName=${CUSTOMER_NAME} CustomerS3BucketName=${CUSTOMER_LOWER}
echo "--------------------"

