# GVM (OpenVAS) deployment on a remote node agent

This can only be performed after the creation of the CloudStack infrastruture and the setup of a remote node. The remote node will subscribe to a SQS queue and will be ready to receive remote commands.

We have to instruct the remote node to run the following ansible playbooks to install and configured GVM:

1. _hosted_playbooks/disable_selinux_reboot.yaml_
2. _hosted_playbooks/gvm_deploy.yaml_

To do that, follow these steps:

1. In the AWS SQS Dashboard, select the correct region and find a queue named _<customer_name>-CommandResponseQueue_.
2. Copy the URL of the queue.
3. In the AWS SQS Dashboard, select the correct region and find a queue named _<customer_name>-AnsibleCommandQueue_.
3. Click in `Send and receive messages`.
4. Add the following attribute in "Message attributes" (replace the value with a proper node name):
    ```
    name: node_target
    type: String
    value: <_Node Name_>
    ```
5. Add this json in the "Message Body" (replace the url with a valid sqs queue url): 
    ```
    {
      "command": "ansible-pull",
      "params": {
        "playbook": "hosted_playbooks/disable_selinux_reboot.yaml",
        "branch": "centos8",
        "playbook_url": "https://github.com/SecureOps/sops-remoteCollector-ansible.git",
        "host": "localhost"
      },
      "sqs_response": {
        "sqs_queue_url": "<_Paste the URL copied in step 2_>"
      }
    }
6. Click "Send Message"
7. Wait a few minutes for the remote node to reboot (* a 'beacon' will be implemented in the future)
8. Send the second message (command) using the same attributes and json, but change the playbook value:
    ```
     {
      "command": "ansible-pull",
      "params": {
        "playbook": "hosted_playbooks/gvm_deploy.yaml",
        "branch": "centos8",
        "playbook_url": "https://github.com/SecureOps/sops-remoteCollector-ansible.git",
        "host": "localhost"
      },
      "sqs_response": {
        "sqs_queue_url": "<_Paste the URL copied in step 2_>"
      }
    }
    ```
9. After a few more minutes the GVM will be installed and ready to receive scan commands.

