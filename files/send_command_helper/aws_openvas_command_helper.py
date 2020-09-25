#!/usr/bin/env python3
import argparse
import boto3
import json
import lxml.etree as etree
import os
import os.path
import time

'''
Requirements:
    - ~/.aws/config
    - ~/.aws/credentials
    - python3 -m pip install requirements.txt
        - boto3
        - lxml

Usage:
    $ python3 aws_openvas_command_helper.py --cmd get_configs
    $ python3 aws_openvas_command_helper.py --cmd get_target --kv 'scan_target_id:0ace4c6a-95cd-4bf8-a869-a1643baecf78'
    $ python3 aws_openvas_command_helper.py --cmd create_target --kv 'scan_target_label:test;scan_target_host_csv:192.168.0.0/24;scan_port_list_id:33d0cd82-57c6-11e1-8ed1-406186ea4fc5'
    $ python3 aws_openvas_command_helper.py --cmd create_target --json_file create_test_target.json
    $ python3 aws_openvas_command_helper.py --id 663a1122-7c77-49a7-9e2a-f74f267127e1

Workflow:
    $ python3 aws_openvas_command_helper.py --cmd get_configs
    $ python3 aws_openvas_command_helper.py --cmd get_scanners
    $ python3 aws_openvas_command_helper.py --cmd get_port_lists
    $ python3 aws_openvas_command_helper.py --cmd create_credential --json_file credentials_data.json
    $ python3 aws_openvas_command_helper.py --cmd create_target --json_file target_data.json
    $ python3 aws_openvas_command_helper.py --cmd create_task --json_file task_data.json
    $ python3 aws_openvas_command_helper.py --cmd start_task --kv 'scan_task_id:<TASK_ID>'
    $ python3 aws_openvas_command_helper.py --cmd get_task --kv 'scan_task_id:<TASK_ID>' | grep -e '<status' -e '<progress'
    $ python3 aws_openvas_command_helper.py --cmd get_report_formats
    $ python3 aws_openvas_command_helper.py --cmd get_reports --kv 'scan_report_id:<REPORT_ID>;scan_report_format_id:<CSV_FORMAT_ID>'
'''
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--cmd') # Command name for SQS which gets mapped to an xml.j2 file.
    parser.add_argument('--kv') # Alternative to using the JSON file, specify key value pairs which are the command arguments.
    parser.add_argument('--json_file') # JSON file containing the command variables for SQS
    parser.add_argument('--id') # Unique message_id created by SQS when running a command. Output in S3 contains this ID.
    parser.add_argument('--aws_config', default='aws_config.json')
    args = parser.parse_args()

    if not os.path.exists(args.aws_config):
        print(f'AWS config file doesn\'t exist: {args.aws_config}')
        required_keys = ['sqs_command_template', 'sqs_queue_url', 'sqs_message_attributes', 's3_bucket_name']
        joined_keys = '\n - '.join(required_keys)
        print(f'The following keys are needed: \n - {joined_keys}')
        exit()

    aws_config = {}
    with open(args.aws_config, 'r') as aws_config_file:
        aws_config = json.load(aws_config_file)

    for key, value in aws_config.items():
        if not value:
            print(f'Missing value for AWS config key: \'{key}\' in {args.aws_config}.')
            exit()

    if args.kv and args.json_file:
        print('Only need to specify either --kv or --json.')
        exit()

    if not args.id and not args.cmd and not args.json:
        print('Must specify --cmd or --json_file (with scan_command inside) when running without --id.')
        exit()

    if (args.cmd or args.kv) and args.id:
        print('You only need to specify either --cmd and --kv or --id if the command was already sent.')
        exit()

    input_kvs = {}
    if args.kv:
        for key_value in args.kv.split(';'):
            key, value = key_value.split(':')
            key = key.strip()
            value = value.strip()
            input_kvs[key] = value
    elif args.json_file:
        with open(args.json_file, 'r') as h:
            input_kvs = json.load(h)

    if not args.id and not args.cmd and 'scan_command' not in input_kvs:
        print('You must specify --cmd or have the key \'scan_command\' inside your --json_file or --kv.')
        exit()

    message_id = args.id
    if not message_id:
        command_kv = {}

        if args.cmd:
            command_kv['scan_command'] = args.cmd

        for key, value in input_kvs.items():
            command_kv[key] = value

        print('Sending command...')
        sqs_command_template = aws_config['sqs_command_template']
        command_json = create_sqs_command_from_template(sqs_command_template, command_kv)
        sqs_queue_url = aws_config['sqs_queue_url']
        sqs_message_attributes = aws_config['sqs_message_attributes']
        message_id = send_sqs_command(sqs_queue_url, sqs_message_attributes, command_json)

    print(f'Fetching command output from S3 with message id {message_id}...')
    s3_bucket_name = aws_config['s3_bucket_name']
    filename, raw_output, seconds_elapsed = wait_and_download_file_s3(s3_bucket_name, message_id)

    if not 'error' in filename:
        pretty_xml = xml_prettify(raw_output)
        print(pretty_xml)
    else:
        print(raw_output)

    print(f'^^^ Contents of {filename} ^^^')
    print(f'Command took {seconds_elapsed}s to complete!')

def create_sqs_command_from_template(json_template_json, variables_kv):
    command = json_template_json
    for key, value in variables_kv.items():
        command['params']['variables'][key] = value

    return command

def send_sqs_command(queue_url, message_attributes, command_json):
    sqs = boto3.client('sqs')
    response = sqs.send_message(
        QueueUrl=queue_url,
        DelaySeconds=10,
        MessageAttributes=message_attributes,
        MessageBody=json.dumps(command_json)
    )
    return response['MessageId']

def wait_and_download_file_s3(bucket_name, expected_key):
    s3 = boto3.resource('s3')
    bucket = s3.Bucket(bucket_name)

    interesting_files = [
        f'{expected_key}-output.xml',
        f'{expected_key}-error.txt'
    ]

    seconds_elapsed = 0
    while True:
        all_filenames_in_s3 = {}
        all_file_object_summaries = bucket.objects.all() # TODO: Only look in expected output folder instead of all
        for file_object_summary in all_file_object_summaries:
            file_key = file_object_summary.key
            filename = file_key.split('/')[::-1][0]
            all_filenames_in_s3[filename] = file_object_summary

        for interesting_file in interesting_files:
            if interesting_file in all_filenames_in_s3:
                tmp_output_path = f'/tmp/{interesting_file}'
                file_object_summary = all_filenames_in_s3[interesting_file]
                file_object_summary.Object().download_file(tmp_output_path)

                command_output = None
                with open(tmp_output_path, 'r') as h:
                    command_output = h.read()

                os.remove(tmp_output_path)

                return interesting_file, command_output, seconds_elapsed

        wait_seconds = 1
        time.sleep(wait_seconds)
        seconds_elapsed += wait_seconds

def xml_prettify(xml_str):
    xml_obj = etree.fromstring(xml_str)
    return etree.tostring(xml_obj, pretty_print=True).decode()

if __name__ == '__main__':
    main()
