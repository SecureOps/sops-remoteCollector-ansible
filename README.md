# sops-remoteCollector-ansible
Ansible Playbooks to configure a Remote Agent

1) Copy _vars.sh.example_ to _vars.sh_

2) Modify _vars.sh_ parameters with customer's information:
  ```
  AWS_DEFAULT_REGION
  CUSTOMER_NAME
  REMOTE_NODE_NAME
  ```

3) Modify _vars.sh_ for cloud-init user parameters (not required)L
  ```
  INITIAL_USER_NAME
  INITIAL_USER_GECOS
  INITIAL_USER_SSH_KEY
  ```

4) Modify _vars.sh_ for cloud-init network parameters (comment to use DHCP):
  ```
  MAC_ADDR
  IP_CIDR
  GATEWAY
  NAMESERVER[0]
  NAMESERVER[1]
  ```

5) To Create or Update the main CloudFormation and Node(s) Stacks run:
  ```
   $ cd scripts/
   $ ./createAWSCustomerStack.sh
   $ ./createAWSNodeStack.sh.sh
  ```

5.5) Make sure all AWS Resources are created before going to the next step.

6) Create Cloud-Init Image to be used in the agent VM/instance:
  ```
  $ cd scripts
  $ ./createCloudInitISO-CentOS.sh
  ```

7) Create a new VM/instance with the MAC Address of the main NIC matching the address set in _vars.sh_.

8) Download the latest official Centos8 Cloud Image. (from your preferred trusted source)

9) Attach the CentOS 8 Cloud Image and the generated cloud-init images to the VM

10) Expand the VM/instance main disk volume to at least 50Gb.

11) Start the VM and auto configration should kick in.

12) The following command will run during first boot: 
  ```
  $ ansible-pull -c "<GIT_BRANCH>" -U https://github.com/SecureOps/sops-remoteCollector-ansible.git collector-setup.yaml
  ```

