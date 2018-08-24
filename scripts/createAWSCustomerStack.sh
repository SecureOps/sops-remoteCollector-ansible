#!/bin/bash
set -e
set -u

## LOAD required customer related vars
SCRIPT_DIR=$( dirname ${BASH_SOURCE[0]} )
SCRIPT_DIR=$( readlink -f ${SCRIPT_DIR} )
. ${SCRIPT_DIR}/../vars.sh


aws cloudformation create-stack --stack-name "${CUSTOMER_NAME}Stack" \
                                --capabilities CAPABILITY_NAMED_IAM \
                                --template-body file:///${SCRIPT_DIR}/${CF_FILE} \
                                --parameters ParameterKey=CustomerName,ParameterValue=${CUSTOMER_NAME} ParameterKey=CustomerS3BucketName,ParameterValue=${CUSTOMER_NAME,,}



aws cloudformation describe-stacks --stack-name "${CUSTOMER_NAME}Stack"

