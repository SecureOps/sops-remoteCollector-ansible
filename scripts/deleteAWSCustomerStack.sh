#!/bin/bash
set -u

## LOAD required customer related vars
SCRIPT=$( basename ${BASH_SOURCE[0]} )
SCRIPT_DIR=$( dirname ${BASH_SOURCE[0]} )
CF_DIR="${SCRIPT_DIR}/../CloudFormation/"
. ${SCRIPT_DIR}/../vars.sh

aws cloudformation delete-stack --stack-name "sopsCustomer-${CUSTOMER_NAME}-sqs-command-response"
aws cloudformation delete-stack --stack-name "${CUSTOMER_NAME}Stack"
