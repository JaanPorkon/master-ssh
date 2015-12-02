####Introduction
It's a little tool that allows you to connect to multiple SSH tunnels at the same time and broadcast commands instantly.

####Installation

```
git clone https://github.com/JaanPorkon/master-ssh.git
cd master-ssh
chmod o+x install.sh
```

####Usage

To run the program you can feed credentials to it from URL or from a file. Source of the web page and file must be in CSV style:

```
hostname,127.0.0.1,username,password
hostname2,127.0.0.2,username,password
```

Example:

`master-ssh --cred-file /path/to/credentials.txt`

or

`master-ssh --cred-url https://mydomain.tld/credentials`

To send command to 1 server only use the following command pattern:

_master-ssh:[hostname] [command]_

Example:

`master-ssh$ master-ssh:hostname uname -a`

####Dependencies

This code is depending on:
* Paramiko (https://github.com/paramiko/paramiko)
* Requests (https://github.com/kennethreitz/requests)
* Optparse (https://docs.python.org/2/library/optparse.html)

If you get an error that pip is missing, you can install it like this:

Ubuntu/Debian
`apt-get install python-pip`

CentOS/Fedora
`yum install python-pip`
