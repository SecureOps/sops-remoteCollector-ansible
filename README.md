# sops-remoteCollector-ansible
Ansible Playbooks to configure Log Collector


# Install requirements
ansible-galaxy install -r ./roles/requirements.yml -p ./roles/ --force


1) Set vars.sh with customer's parameters

2) Create/Update CloudFormation Stack:

   $ ./scripts/createAWSCustomerStack.sh
     
     or
   
  $ ./scripts/updateAWSCustomerStack.sh

2.5) Make sure all AWS Resources are created before going to the next step.

3) Create Cloud-Init Image

4) Create a new VM with MAC Address matching with one set in vars.sh

5) Download Official Ubuntu Cloud Image.

6) Attach the Ubuntu and cloud init images to the VM

7) Expand the main image to at least 50Gb.

8) Start the VM and auto configration should kick in.

9) The following command will run during first boot: 

  $ ansible-pull -U https://github.com/SecureOps/sops-remoteCollector-ansible.git collector-setup.yaml

