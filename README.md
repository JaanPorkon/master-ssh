####Introduction
It's a little tool that allows you to connect to multiple SSH tunnels at the same time and broadcast commands instantly.

####Usage

First you can add this script to your local bin:

`ln -s /path/to/master-ssh.py /usr/local/bin`

To run the program you can feed credentials to it from URL or from a file. Source of the web page and file must be in CSV style:

```
hostname,127.0.0.1,username,password
hostname2,127.0.0.2,username,password
```

Example:

`master-ssh.py --cred-file /path/to/credentials.txt`

or

`master-ssh.py --cred-url https://mydomain.tld/credentials`

To send command to 1 server only use the following command pattern:

_master-ssh:[hostname] [command]_

Example:

`master-ssh:hostname uname -a`

####Dependencies

This code is depending on Paramiko (https://github.com/paramiko/paramiko)

To insall it, you can run:

`pip install paramiko`

If you get an error that pip is missing, you can install it like this:

Ubuntu/Debian
`apt-get install python-pip`

CentOS/Fedora
`yum install python-pip`
