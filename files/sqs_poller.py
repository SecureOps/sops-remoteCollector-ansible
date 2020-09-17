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

def process_payload(payload, message_id):
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
        elif command == 'ansible-pull':
            variables = "{}"
            if 'params' not in payload:
                output['message'] = "Failed, ansible-pull command needs params specified in payload"
            else:
                params = payload.get('params')
                if 'playbook' not in params:
                    output['message'] = "Failed, ansible-pull command needs to have playbook attribute set in params"
                else:
                    playbook = params.get('playbook')
                    if 'host' not in params:
                        output['message'] = "Failed, ansible-pull command needs to have host attribute set in params"
                    if 'playbook_url' not in params:
                        output['message'] = "Failed, ansible-pull needs to have playbook_url set in params"
                    else:
                        host_cli = str(f"-e ansible_host={params.get('host')}")
                        branch_cli = ""
                        if 'branch' in params:
                            branch_cli = str(f"-C {params.get('branch')}")

                        playbook_url_cli = str(f"-U {params.get('playbook_url')}")
                        variables_cli = ""
                        if 'variables' in params:
                            try:
                                variables = json.dumps(command['params']['variables'])
                                variable_cli = str(f"-e '{variables}'" )
                            except Exception as e:
                                output['message'] = str("Failed to parse variables: {}").format(e.message)

                        cmd = str(f'ansible-pull {branch_cli} {playbook_url_cli} {playbook} {host_cli} {variables_cli}')

        if cmd:
            process = subprocess.run(
                shlex.split(cmd),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            rc = process.returncode
            output['shell'] = cmd
            output['stderr'] +=  str(process.stderr) + '\n'
            output['stdout'] +=  str(process.stdout) + '\n'
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
    if payload.get('sqs_response'):
        sqs_response = payload.get('sqs_response')
        if 'sqs_queue_url' not in sqs_response:
            print("Failed to send response, sqs_response needs an sqs_queue_url attribute to be set")
        else:
            sqs = sqs = boto3.client('sqs', region_name=config['aws_region_name'])
            sqs.send_message(
                QueueUrl=sqs_response.get('sqs_queue_url'),
                MessageBody=json.dumps(output),
                MessageAttributes={
                    'origin_message_id': {
                        'StringValue': message_id,
                        'DataType': 'string'
                    },
                    'responding_node': {
                        'StringValue': config.get('node_name'),
                        'DataType': 'string'
                    }
                }
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

            if 'Messages' in response.keys():
                for message in response.get('Messages'):
                    messageBody = message['Body']
                    receipt_handle = message.get('ReceiptHandle')
                    message_id = message.get('MessageId')
                    if message.get('MessageAttributes') and 'node_target' in message.get('MessageAttributes') and 'StringValue' in message.get('MessageAttributes').get('node_target'):
                        if config.get('node_name') and config.get('node_name') == message.get('MessageAttributes').get('node_target').get('StringValue'):
                            try:
                                # Decoding Body (json)
                                payload = json.loads( messageBody )
                                pprint.pprint( payload )
                                # Spawn a new process to handle the payload
                                payload_processor = mp.Process(target=process_payload, args=(payload,message_id,))
                                payload_processor.start()
                                print(f'Spawned process ID {payload_processor.pid}')
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
