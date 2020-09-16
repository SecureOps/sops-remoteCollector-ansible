#!/usr/bin/python3

import os, sys, subprocess, shlex
import boto3
import time
from datetime import datetime
import pprint
import json
import urllib3

http = urllib3.PoolManager()

with open('config.json','r') as json_file:
    config = json.load(json_file)

def getTimestamp():
    return datetime.now().strftime("%Y%m%d-%H%M%S")

def clip_text(text, clipsize=150):
    if len(text) > clipsize:
        start = len(text) - clipsize
        return text[start:]
    return text

def send(responseUrl, responseStatus, stackId, requestId, logicalResourceId, response_data, reason=None, noEcho=False, physicalResourceId="None"):
    print(responseUrl)

    responseBody = {}
    responseBody['Status'] = responseStatus
    responseBody['Reason'] = clip_text(reason)
    responseBody['PhysicalResourceId'] = physicalResourceId
    responseBody['StackId'] = stackId
    responseBody['RequestId'] = requestId
    responseBody['LogicalResourceId'] = logicalResourceId
    responseBody['NoEcho'] = noEcho
    responseBody['Data'] = response_data

    json_responseBody = "{}"
    json_responseBody = json.dumps(responseBody).encode('utf-8')
    print("Response body:\n" + str(json_responseBody))



    headers = {
        'content-type': 'application/json'
    }

    try:
        response = http.request('PUT',
                                responseUrl,
                                headers=headers,
                                body=json_responseBody
                            )
        # response = requests.put(responseUrl,
        #                         data=json_responseBody,
        #                         headers=headers)
        print("Status code: " + str(response.status))
    except Exception as e:
        print("send(..) failed executing http.request(..): " + str(e))


if __name__ == '__main__':
    while( True ):
        try:
            # Make sure we get a 'fresh' client every attempt, otherwise sqs will not send existing and not deleted messages in the queue
            sqs = boto3.client('sqs', region_name=config['aws_region_name'])
            responseStatus = 'SUCCESS'
            # Receive message from SQS queue
            response = sqs.receive_message(
                QueueUrl=config['queue_url'],
                AttributeNames=[
                    'All'
                ],
                MaxNumberOfMessages=1,
                MessageAttributeNames=[
                    'All'
                ],
                VisibilityTimeout=0,
                WaitTimeSeconds=0
            )

            if ( 'Messages' in response.keys() ):
                message = response['Messages'][0]
                messageBody = message['Body']
                receipt_handle = message['ReceiptHandle']
                responseStatus = "FAILED"
                try:
                    # Decoding Body (json)
                    payload = json.loads( messageBody )
                    pprint.pprint( payload )

                    if 'command' in payload:
                        print("command in payload")
                        if payload['command'] == 'ansible':
                            print("ansible in payload")
                            playbook = "notspecified.yaml"
                            variables = "{}"
                            if 'params' in payload:
                                print("params in payload")
                                host = payload['params']['host']
                                playbook = payload['params']['playbook']
                                if 'variables' in payload['params']:
                                    variables = json.dumps(payload['params']['variables'])
                            cmd = "ansible-playbook {} -e '{}' -e ansible_host={}"
                            cmd = cmd.format(playbook, variables, host)
                            print("Executing " + cmd)
                            process = subprocess.run(shlex.split(cmd), text=True, capture_output=True )
                            rc = process.returncode
                            output = ""
                            if rc is not None and rc > 0 :
                                output = output + '[WARNING] {}: Failed to run task ... \n'.format(getTimestamp() )
                                responseStatus = "FAILED"
                                output = output + process.stderr + '\n' + process.stdout + '\n'
                            else:
                                output = output + '[INFO] {}: task started... \n'.format(getTimestamp() )
                                output = output + process.stdout
                                responseStatus = "SUCCESS"
                            print(output)
                            response_data = {}
                            response_data['output'] = clip_text(output)
                    if 'cloudformation' in payload:
                        # CloudFormation doesn't like the reason to be too long, so clip it.

                        send( payload['cloudformation']['responseUrl'], responseStatus,
                            payload['cloudformation']['stackId'],
                            payload['cloudformation']['requestId'],
                            payload['cloudformation']['logicalResourceId'],
                            response_data,
                            reason=output
                        )
                except Exception as e:
                    print('[ERROR] {}: Failed to decode message: {} - {}'.format(getTimestamp(), messageBody, str(e)))

                # Delete received message from queue
                print("Deleting message: " + receipt_handle)
                sqs.delete_message(
                    QueueUrl=config['queue_url'],
                    ReceiptHandle=receipt_handle
                )

                print('[INFO] {}: Task received and being processed: {}'.format(getTimestamp(), message['MessageId']) )
            time.sleep(5)
        except Exception as err:
            # boto client can "miss" credentials calls to the metadata service sometimes.
            print(('[ERROR] {}: {}').format(getTimestamp(), str(err)))
