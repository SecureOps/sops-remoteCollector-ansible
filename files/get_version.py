import boto3
import json


def check_args(args):
    len_args = len(args.script) - 1
    if len_args is not 2:
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
  from gvmtools.helper import pretty_print
  pretty_print(version)
  sqs = sqs = boto3.client('sqs', region_name=aws_region_name)
  try:
      sqs.send_message(
          QueueUrl=sqs_response_url,
          MessageBody=json.dumps(version),
          MessageAttributes={
              'origin_message_id': {
                  'StringValue': message_id,
                  'DataType': 'String'
              },
              'responding_node': {
                  'StringValue': node_name,
                  'DataType': 'String'
              }
          }
      )
  except Exception as e:
      print(f"JSON dump of the output didn't work: {e.message}")

if __name__ == '__gmp__':
  main(gmp, args)
