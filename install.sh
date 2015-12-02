#!/bin/bash

# Install Paramiko (https://github.com/paramiko/paramiko)
pip install paramiko

# Install Requests (https://github.com/kennethreitz/requests)
pip install requests

# Get current directory
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Create a soft link to local bin folder
ln -s $DIR/master-ssh /usr/local/bin/master-ssh

# Make master-ssh executable
chmod o+x master-ssh
