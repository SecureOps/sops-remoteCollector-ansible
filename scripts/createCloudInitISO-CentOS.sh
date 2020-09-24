#!/bin/bash
set -e
set -u

## LOAD required customer related vars
SCRIPT=$( basename ${BASH_SOURCE[0]} )
SCRIPT_DIR=$( dirname ${BASH_SOURCE[0]} )
CF_DIR="${SCRIPT_DIR}/../CloudFormation/"
#SCRIPT_DIR=$( readlink -f ${SCRIPT_DIR} )
. ${SCRIPT_DIR}/../vars.sh


# Hostname
TARGET_HOSTNAME="sopsCollector-${CUSTOMER_NAME}-${REMOTE_NODE_NAME:-01}"

# Where to look for ansible playbook
ANSIBLE_PULL_URL="https://github.com/SecureOps/sops-remoteCollector-ansible.git"
ANSIBLE_PULL_BRANCH=centos8
ANSIBLE_PULL_PLAYBOOK="collector-setup.yaml"

# Phone Home Url, it's called when cloud-init is finished and also via cron every N mins (set in ansible)
PHONE_HOME_URL="https://s3.amazonaws.com"

# Some converted values
CUSTOMER_LOWER=$(echo "${CUSTOMER_NAME}" | tr '[:upper:]' '[:lower:]')

#Set random root password
ROOT_PWD="$( pwgen 20 -1 )"
#ROOT_PWD="root"

# Temporary dir for cloud-init ISO creation
TMPDIR="iso_temp_dir"
rm -rf "${TMPDIR}"
mkdir -p "${TMPDIR}"

cat <<EOF > "${TMPDIR}/user-data"
#cloud-config
debug: True
disable_root: True
ssh_deletekeys: True
ssh_pwauth: False

growpart:
  mode: auto
  devices: ['/']
  ignore_growroot_disabled: false

users:
  - name: ${INITIAL_USER_NAME}
    gecos: ${INITIAL_USER_GECOS}
    sudo: ["ALL=(ALL) NOPASSWD:ALL"]
    groups: users
    shell: /bin/bash
    ssh-authorized-keys:
      - ${INITIAL_USER_SSH_KEY}
  - name: ansible_poller
    shell: /usr/sbin/nologin
    sudo: ["ALL=(ALL) NOPASSWD:ALL"]
chpasswd:
  list: |
    ${INITIAL_USER_NAME}:${ROOT_PWD}
  expire: False

write_files:
  - path: /etc/ansible/facts.d/secureops.fact
    content: |
      [customer_info]
      name=${CUSTOMER_NAME}
      node=${REMOTE_NODE_NAME}
      aws_region=${AWS_DEFAULT_REGION}
      aws_key_id=${AWS_KEY_ID}
      aws_sec_key=${AWS_SEC_KEY}
      #
      [devops]
      ansible_pull_url=${ANSIBLE_PULL_URL}
      ansible_pull_playbook=${ANSIBLE_PULL_PLAYBOOK}
      ansible_pull_branch=${ANSIBLE_PULL_BRANCH:-centos8}
      phone_home_url=${PHONE_HOME_URL}


#do this via ansible ? #-> package_upgrade: True

yum_repos:
  centos-ansible-29:
    baseurl: http://mirrorlist.centos.org/?release=\$releasever&arch=\$basearch&repo=configmanagement-ansible-29
    name: CentOS Configmanagement SIG - ansible-29
    enabled: true
    gpgcheck: 0
    baseurl: http://mirror.centos.org/\$contentdir/\$releasever/configmanagement/\$basearch/ansible-29/
    mirrorlist: http://mirrorlist.centos.org/?release=\$releasever&arch=\$basearch&repo=configmanagement-ansible-29

packages:
  - git
  - ansible
  - python3-pip

runcmd:
#  - 'echo "IP: \4" >> /etc/issue'
  - curl -s ${PHONE_HOME_URL}/sops-public/cloudsiem@secureops.com.asc | gpg --import --batch
  - ansible-pull -C ${ANSIBLE_PULL_BRANCH:-centos8} -U ${ANSIBLE_PULL_URL} ${ANSIBLE_PULL_PLAYBOOK}


# phone_home:
#  url: ${PHONE_HOME_URL}/sopscustomer-${CUSTOMER_LOWER}/\$INSTANCE_ID/_data/cloud-init-report
#  post:
#   - pub_key_rsa
#   - instance_id
#   - fqdn
#  tries: 3
EOF

# Confirmation of VM settings:
echo "Before providing the ISO image to the customer, please make sure that these parameters are correct:"

cat <<EOF > "${TMPDIR}/meta-data"
instance-id: ${TARGET_HOSTNAME}
local-hostname: ${TARGET_HOSTNAME}
EOF
cat "${TMPDIR}/meta-data"

set +u
## Generate network-config file if all network info have been provided
##   * The default behaviour is DHCP on the first NIC.
if [[ "${MAC_ADDR}" != "" ]] &&
   [[ "${IP_CIDR}" != "" ]] &&
   [[ "${GATEWAY}" != "" ]] &&
   [[ "${NAMESERVER[0]}" != "" ]] &&
   [[ "${NAMESERVER[1]}" != "" ]]
then
    cat <<EOF > "${TMPDIR}/network-config"
version: 2
ethernets:
  eth0:
    match:
      macaddress: "${MAC_ADDR}"
    addresses:
      - ${IP_CIDR}
    gateway4: ${GATEWAY}
    nameservers:
      addresses:
        - ${NAMESERVER[0]}
        - ${NAMESERVER[1]}

EOF
    cat "${TMPDIR}/network-config"
fi
set -u

# generate the seed images
mkisofs -output ${CUSTOMER_NAME}-ci-img.iso -volid cidata -joliet -rock ${TMPDIR}/
## alternative method ##-> cloud-localds -v --network-config=${TMPDIR}/network-config ${CUSTOMER_NAME}-ci-img.iso ${TMPDIR}/user-data ${TMPDIR}/meta-data


# Create stunnel client config file
cat <<EOF > "${TMPDIR}/${TARGET_HOSTNAME}-stunnel.conf"
pid = /var/run/stunnel.pid
[ssh-psk-client]
client=yes
accept = 0.0.0.0:2222
connect = ${STUNNEL_GW}
ciphers = PSK
PSKsecrets = /etc/stunnel/psk.txt
EOF

aws s3 cp "${TMPDIR}/${TARGET_HOSTNAME}-stunnel.conf" "s3://sopscustomer-${CUSTOMER_LOWER}/nodes/${REMOTE_NODE_NAME}/stunnel_client.conf"
rm -f "${TMPDIR}/${TARGET_HOSTNAME}-stunnel.conf"

