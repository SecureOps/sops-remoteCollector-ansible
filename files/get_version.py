import boto3
import json
from gvmtools.helper import pretty_print
import xml.etree.cElementTree as etree


def check_args(args):
    len_args = len(args.script) - 1
    if len_args is not 3:
        message = """
        This script gets the GVM version and outputs the result to an AWS SQS queue
        Two parameters after the script name is required.
        1. <region_name>      --- AWS region name for AWS (us-east-1, eu-central-1, etc.)
        1. <sqs_response_url>        -- URL of the SQS queue to respond to
        2. <node_name>  -- Node name as registered with the system
        """
        print(message)
        quit()

def main(gmp, args):
  check_args(args)
  aws_region_name = args.script[1]
  sqs_response_url = args.script[2]
  node_name = args.script[3]

  version = gmp.get_version()
  messageBody = etree.tostring(version).decode('utf-8')
  sqs = boto3.client('sqs', region_name=aws_region_name)
  try:
      sqs.send_message(
          QueueUrl=sqs_response_url,
          MessageBody = str(messageBody),
          MessageAttributes={
              'origin_message_id': {
                  'StringValue': 'MESSAGE_ID_TBD',
                  'DataType': 'String'
              },
              'responding_node': {
                  'StringValue': node_name,
                  'DataType': 'String'
              }
          }
      )
  except TypeError as te:
      print(f"Send output didn't work: {te}")
  except NameError as ne:
      print(f"Send output didn't work: {ne}")
  except Exception as e:
      print(e)

if __name__ == '__gmp__':
  main(gmp, args)
