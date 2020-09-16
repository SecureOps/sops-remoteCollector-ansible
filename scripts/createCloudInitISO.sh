#!/bin/bash
set -e
set -u

## LOAD required customer related vars
SCRIPT=$( basename ${BASH_SOURCE[0]} )
SCRIPT_DIR=$( dirname ${BASH_SOURCE[0]} )
#SCRIPT_DIR=$( readlink -f ${SCRIPT_DIR} )
. ${SCRIPT_DIR}/../vars.sh


# Hostname
TARGET_HOSTNAME="sopsCollector-${CUSTOMER_NAME}-${REMOTE_NODE_NAME:-01}"

# Where to look for ansible playbook
ANSIBLE_PULL_URL="https://github.com/SecureOps/sops-remoteCollector-ansible.git"
ANSIBLE_PULL_PLAYBOOK="collector-setup.yaml"

# Phone Home Url, it's called when cloud-init is finished and also via cron every N mins (set in ansible)
PHONE_HOME_URL="https://s3.amazonaws.com"

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
    ssh_pwauth: False
    ssh-authorized-keys:
      - ${INITIAL_USER_SSH_KEY}

chpasswd:
  list: |
    ${INITIAL_USER_NAME}:${ROOT_PWD}
  expire: False

  apt:
    sources:
      elastic-6.x.list:
        source: "deb https://artifacts.elastic.co/packages/6.x/apt stable main"
        key: |
          -----BEGIN PGP PUBLIC KEY BLOCK-----
          Version: GnuPG v2.0.14 (GNU/Linux)

          mQENBFI3HsoBCADXDtbNJnxbPqB1vDNtCsqhe49vFYsZN9IOZsZXgp7aHjh6CJBD
          A+bGFOwyhbd7at35jQjWAw1O3cfYsKAmFy+Ar3LHCMkV3oZspJACTIgCrwnkic/9
          CUliQe324qvObU2QRtP4Fl0zWcfb/S8UYzWXWIFuJqMvE9MaRY1bwUBvzoqavLGZ
          j3SF1SPO+TB5QrHkrQHBsmX+Jda6d4Ylt8/t6CvMwgQNlrlzIO9WT+YN6zS+sqHd
          1YK/aY5qhoLNhp9G/HxhcSVCkLq8SStj1ZZ1S9juBPoXV1ZWNbxFNGwOh/NYGldD
          2kmBf3YgCqeLzHahsAEpvAm8TBa7Q9W21C8vABEBAAG0RUVsYXN0aWNzZWFyY2gg
          KEVsYXN0aWNzZWFyY2ggU2lnbmluZyBLZXkpIDxkZXZfb3BzQGVsYXN0aWNzZWFy
          Y2gub3JnPokBOAQTAQIAIgUCUjceygIbAwYLCQgHAwIGFQgCCQoLBBYCAwECHgEC
          F4AACgkQ0n1mbNiOQrRzjAgAlTUQ1mgo3nK6BGXbj4XAJvuZDG0HILiUt+pPnz75
          nsf0NWhqR4yGFlmpuctgCmTD+HzYtV9fp9qW/bwVuJCNtKXk3sdzYABY+Yl0Cez/
          7C2GuGCOlbn0luCNT9BxJnh4mC9h/cKI3y5jvZ7wavwe41teqG14V+EoFSn3NPKm
          TxcDTFrV7SmVPxCBcQze00cJhprKxkuZMPPVqpBS+JfDQtzUQD/LSFfhHj9eD+Xe
          8d7sw+XvxB2aN4gnTlRzjL1nTRp0h2/IOGkqYfIG9rWmSLNlxhB2t+c0RsjdGM4/
          eRlPWylFbVMc5pmDpItrkWSnzBfkmXL3vO2X3WvwmSFiQbkBDQRSNx7KAQgA5JUl
          zcMW5/cuyZR8alSacKqhSbvoSqqbzHKcUQZmlzNMKGTABFG1yRx9r+wa/fvqP6OT
          RzRDvVS/cycws8YX7Ddum7x8uI95b9ye1/Xy5noPEm8cD+hplnpU+PBQZJ5XJ2I+
          1l9Nixx47wPGXeClLqcdn0ayd+v+Rwf3/XUJrvccG2YZUiQ4jWZkoxsA07xx7Bj+
          Lt8/FKG7sHRFvePFU0ZS6JFx9GJqjSBbHRRkam+4emW3uWgVfZxuwcUCn1ayNgRt
          KiFv9jQrg2TIWEvzYx9tywTCxc+FFMWAlbCzi+m4WD+QUWWfDQ009U/WM0ks0Kww
          EwSk/UDuToxGnKU2dQARAQABiQEfBBgBAgAJBQJSNx7KAhsMAAoJENJ9ZmzYjkK0
          c3MIAIE9hAR20mqJWLcsxLtrRs6uNF1VrpB+4n/55QU7oxA1iVBO6IFu4qgsF12J
          TavnJ5MLaETlggXY+zDef9syTPXoQctpzcaNVDmedwo1SiL03uMoblOvWpMR/Y0j
          6rm7IgrMWUDXDPvoPGjMl2q1iTeyHkMZEyUJ8SKsaHh4jV9wp9KmC8C+9CwMukL7
          vM5w8cgvJoAwsp3Fn59AxWthN3XJYcnMfStkIuWgR7U2r+a210W6vnUxU4oN0PmM
          cursYPyeV0NX/KQeUeNMwGTFB6QHS/anRaGQewijkrYYoTNtfllxIu9XYmiBERQ/
          qPDlGRlOgVTd9xUfHFkzB52c70E=
          =92oX
          -----END PGP PUBLIC KEY BLOCK-----

      treasure-data.list:
        source: "deb http://packages.treasuredata.com/3/ubuntu/bionic/ bionic contrib"
        key: |
          -----BEGIN PGP PUBLIC KEY BLOCK-----
          Version: GnuPG v2

          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
          5Ow=
          =Me4L
          -----END PGP PUBLIC KEY BLOCK-----

write_files:
  - path: /etc/ansible/facts.d/secureops.fact
    content: |
      [customer_info]
      name=${CUSTOMER_NAME}
      aws_region=${AWS_DEFAULT_REGION}
      aws_key_id=${AWS_KEY_ID}
      aws_sec_key=${AWS_SEC_KEY}
      #
      [devops]
      ansible_pull_url=${ANSIBLE_PULL_URL}
      ansible_pull_playbook=${ANSIBLE_PULL_PLAYBOOK}
      phone_home_url=${PHONE_HOME_URL}


#do this via ansible ? #-> package_upgrade: True

packages:
  - git
  - ansible
  - centos-release-ansible-29
#  - build-essential
#  - python-minimal

runcmd:
#  - 'echo "IP: \4" >> /etc/issue'
  - curl -s ${PHONE_HOME_URL}/sops-public/cloudsiem@secureops.com.asc | gpg --import --batch
  - ansible-pull -U ${ANSIBLE_PULL_URL} ${ANSIBLE_PULL_PLAYBOOK}


#phone_home:
#  url: ${PHONE_HOME_URL}/${CUSTOMER_NAME}_data/cloud-init-report
#  post: [ "${CUSTOMER_NAME}", pub_key_dsa, pub_key_rsa, pub_key_ecdsa, instance_id ]

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
  id0:
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
