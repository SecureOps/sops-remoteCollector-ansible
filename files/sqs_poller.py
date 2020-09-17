#!/usr/bin/python3

import os, sys, subprocess, shlex
import boto3
import time
from datetime import datetime
import pprint
import json
import urllib3
import multiprocessing as mp

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

def cf_send(responseUrl, responseStatus, stackId, requestId, logicalResourceId, response_data, reason=None, noEcho=False, physicalResourceId="None"):
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

def process_payload(payload):
    output = {}

    # Preset this so we don't need to set it unless we have success
    output['responseStatus'] = "FAILED"
    output['stdout'] = ""
    output['stderr'] = ""
    if 'command' not in payload:
        output['message'] = "Failed, no command in payload"
    else:
        command = payload.get('command')
        output['command'] = command
        cmd = None
        if command == 'ansible':
            variables = "{}"
            if 'params' not in payload:
                output['message'] = "Failed, ansible command needs params specified in payload"
            else:
                params = payload.get('params')
                if 'playbook' not in params:
                    output['message'] = "Failed, ansible command needs to have playbook attribute set in params"
                else:
                    playbook = params.get('playbook')
                    if 'host' not in params:
                        output['message'] = "Failed, ansible command needs to have host attribute set in params"
                    else:
                        host = params.get('host')
                        if 'variables' in params:
                            try:
                                variables = json.dumps(command['params']['variables'])
                                cmd = "ansible-playbook {} -e '{}' -e ansible_host={}"
                                cmd = cmd.format(playbook, variables, host)
                            except Exception as e:
                                output['message'] = str("Failed to parse variables: {}").format(e.message)
                        else:
                            cmd = "ansible-playbook {} -e ansible_host={}"
                            cmd = cmd.format(playbook, host)
        elif command['command'] == 'ansible-pull':
            pass

        if cmd:
            process = subprocess.run(
                shlex.split(cmd),
                text=True,
                capture_output=True )
            rc = process.returncode
            output['shell'] = cmd
            output['stderr'] +=  process.stderr + '\n'
            output['stdout'] +=  process.stdout + '\n'
            output['rc'] = rc
            if rc is not None and rc > 0 :
                output['message'] = '[WARNING] {}: Failed to run task ... \n'.format(getTimestamp() )
            else:
                output['message'] = '[INFO] {}: task started... \n'.format(getTimestamp() )
                responseStatus = "SUCCESS"
                output['responseStatus'] = responseStatus
    print(output)

    # Process the outputs
    if 'cloudformation' in payload:
        # CloudFormation
        cloudformation = payload.get('cloudformation')
        cf_send( cloudformation.get('responseUrl'), output.get('responseStatus'),
            cloudformation.get('stackId'),
            cloudformation.get('requestId'),
            cloudformation.get('logicalResourceId'),
            clip_text(output.get('stderr' or output.get('message'))),
            reason=clip_text(output.get('stdout') or output.get('message'))
        )

if __name__ == '__main__':
    # Start our process pool
    mp.set_start_method('spawn')
    while( True ):
        try:
            # Make sure we get a 'fresh' client every attempt, otherwise sqs will not send existing and not deleted messages in the queue
            sqs = boto3.client('sqs', region_name=config['aws_region_name'])
            # responseStatus = 'SUCCESS'
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
                # responseStatus = "FAILED"
                try:
                    # Decoding Body (json)
                    payload = json.loads( messageBody )
                    pprint.pprint( payload )

                    # Spawn a new process to handle the payload
                    payload_processor = mp.Process(target=process_payload, args=(payload,))
                    payload_processor.start()
                    print(f'Spawned process ID {payload_processor.pid}')
                    # if 'command' in payload:
                    #     print("command in payload")
                    #     if payload['command'] == 'ansible':
                    #         print("ansible in payload")
                    #         playbook = "notspecified.yaml"
                    #         variables = "{}"
                    #         if 'params' in payload:
                    #             print("params in payload")
                    #             host = payload['params']['host']
                    #             playbook = payload['params']['playbook']
                    #             if 'variables' in payload['params']:
                    #                 variables = json.dumps(payload['params']['variables'])
                    #         cmd = "ansible-playbook {} -e '{}' -e ansible_host={}"
                    #         cmd = cmd.format(playbook, variables, host)
                    #         print("Executing " + cmd)
                    #         process = subprocess.run(shlex.split(cmd), text=True, capture_output=True )
                    #         rc = process.returncode
                    #         output = ""
                    #         if rc is not None and rc > 0 :
                    #             output = output + '[WARNING] {}: Failed to run task ... \n'.format(getTimestamp() )
                    #             responseStatus = "FAILED"
                    #             output = output + process.stderr + '\n' + process.stdout + '\n'
                    #         else:
                    #             output = output + '[INFO] {}: task started... \n'.format(getTimestamp() )
                    #             output = output + process.stdout
                    #             responseStatus = "SUCCESS"
                    #         print(output)
                    #         response_data = {}
                    #         response_data['output'] = clip_text(output)
                    # if 'cloudformation' in payload:
                    #     # CloudFormation doesn't like the reason to be too long, so clip it.
                    #
                    #     send( payload['cloudformation']['responseUrl'], responseStatus,
                    #         payload['cloudformation']['stackId'],
                    #         payload['cloudformation']['requestId'],
                    #         payload['cloudformation']['logicalResourceId'],
                    #         response_data,
                    #         reason=output
                    #     )
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
