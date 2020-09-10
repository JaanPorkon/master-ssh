#!/usr/bin/env python

import paramiko
import requests
import sys
import time
import threading
import os
import logging

from paramiko import SSHException
from termcolor import colored

logger = logging.getLogger('MasterSSH')
logger.setLevel(logging.INFO)
logging.basicConfig(format='[%(asctime)s] %(threadName)s: %(message)s', datefmt='%Y/%m/%d %H:%M:%S')


class MasterSSH:
    connection_pool = {}
    selected_servers = []
    credentials = []
    config = None

    commandPool = []

    """
    Initalize everything
    """

    def __init__(self, args):
        # Set logging to debug
        if args.verbose:
            logger.setLevel(logging.DEBUG)

        self.config = args

        cred_source_type = None
        cred_source_path = None

        # Validate that file exists and assign it as credentials source
        if args.cred_file:
            if os.path.isfile(args.cred_file):
                cred_source_path = args.cred_file
                cred_source_type = 'file'
            else:
                self.print_error("%s does not exist!" % args.cred_file)
                sys.exit(1)

        # Assign URL as credentials source
        if args.cred_url:
            cred_source_path = args.cred_url
            cred_source_type = 'url'

        # If there are specific servers selected, store their names
        if args.servers:
            self.selected_servers = args.servers.strip().split(',')

        # If credentials path has not been defined, show an error
        if cred_source_path and args.manual:
            self.print_error("You need to specify a credentials getting method [--cred-url, --cred-file, --manual]")
            sys.exit(1)

        # If credentials source is file, pull info from it
        if cred_source_type == 'file':
            with open(cred_source_path, 'r') as f:
                for line in f.readlines():
                    data = line.strip().split(',')

                    self.credentials.append({
                        'name': data[0],
                        'host': data[1],
                        'username': data[2],
                        'password': data[3]
                    })

        # If credentials source is an URL, download the data
        if cred_source_type == 'url':
            try:
                request = requests.get(cred_source_path)
            except requests.ConnectionError:
                self.print_error("Failed to download data! Please check your URL.")
                sys.exit(1)
            except requests.HTTPError:
                self.print_error("Bad HTTP request!")
                sys.exit(1)
            except requests.Timeout:
                self.print_error("Connection to your domain timed out, please check your server!")
                sys.exit(1)
            except requests.TooManyRedirects:
                self.print_error("There are too many redirects for your URL, check your server configuration!")
                sys.exit(1)
            except Exception as e:
                self.print_error("Something went wrong!")
                self.print_exception(e)
                sys.exit(1)

            response = request.text.strip()

            if request.status_code not in [200, 301, 302]:
                self.print_error("%s did not respond correctly: %s!" % (cred_source_path, request.status_code))
                sys.exit(1)

            if response == "":
                self.print_error("%s does not contain any data!" % cred_source_path)
                sys.exit(1)

            for line in response.split('\n'):
                data = line.split(',')

                if len(data) == 4:
                    self.credentials.append({
                        'name': data[0].strip(),
                        'host': data[1].strip(),
                        'username': data[2].strip(),
                        'password': data[3].strip()
                    })

    """
    Create connection threads
    """

    def create_connections(self):
        if self.credentials:
            self.print_message("Connecting to %s servers..." % len(self.credentials))

        thread_pool = {}
        thread_pos = 1
        use_selected_servers = False

        if len(self.selected_servers) > 0:
            use_selected_servers = True

        for cred in self.credentials:
            # If there are specific servers user wants to use, use them ...
            if use_selected_servers:
                if cred['name'] in self.selected_servers:
                    thread_pool[thread_pos] = threading.Thread(target=self.connect, name=cred['name'], args=(cred['name'], cred['host'], cred['username'], cred['password'], self.config.port, self.config.connection_timeout))
                    thread_pool[thread_pos].daemon = True
                    thread_pool[thread_pos].start()
                    thread_pos += 1

            # ... if not, use all of them
            else:
                thread_pool[thread_pos] = threading.Thread(target=self.connect, name=cred['name'], args=(cred['name'], cred['host'], cred['username'], cred['password'], self.config.port, self.config.connection_timeout))
                thread_pool[thread_pos].daemon = True
                thread_pool[thread_pos].start()
                thread_pos += 1

        for i in range(1, thread_pos):
            thread_pool[i].join()

        self.print_success("Welcome to master-ssh!")

    """
    Connect to the server
    """

    def connect(self, name, host, username, password, port, timeout):
        tries = 1
        max_tries = self.config.max_retries

        while tries <= max_tries:
            try:
                client = paramiko.SSHClient()
                client.set_log_channel('SSHClient')
                client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                client.connect(host, username=username, password=password, port=port, timeout=timeout)
                client.get_transport().set_keepalive(30)

                self.connection_pool[name] = client
                self.print_success("Successfully connected!")

                return
            except paramiko.ssh_exception.AuthenticationException:
                self.print_error("Failed to connect - Wrong login details!")
                return
            except Exception as e:
                self.print_error("Failed to connect! Retrying (%s/%s)" % (tries, max_tries))
                self.print_exception(e)

                tries += 1
                time.sleep(self.config.retry_delay)

        self.print_error("Unable to connect, giving up!")

    """
    Create connection closing threads
    """

    def close_connections(self):
        thread_pool = {}
        thread_pos = 1

        for name in self.connection_pool:
            thread_pool[thread_pos] = threading.Thread(target=self.exit, name=name, args=(name,))
            thread_pool[thread_pos].daemon = True
            thread_pool[thread_pos].start()
            thread_pos += 1

        for i in range(1, thread_pos):
            thread_pool[i].join()

        self.print_success("Bye, bye!")

    """
    Close all open connections
    """

    def exit(self, name):
        try:
            if self.connection_pool[name].get_transport():
                if self.connection_pool[name].get_transport().is_active():
                    self.connection_pool[name].exec_command('exit', timeout=self.config.exit_timeout)
        except Exception as e:
            self.print_exception(e)

        self.connection_pool[name].close()
        self.print_action("Disconnected!")

    """
    Listen for user commands
    """

    def listen(self):

        while True:
            # Listen for user input
            try:
                cmd = input('master-ssh$ ').strip()
            except KeyboardInterrupt:
                self.close_connections()
                break

            if cmd == "":
                self.print_error('Please enter your command!')
            elif cmd == "exit":
                self.close_connections()
                break
            else:

                # Check for internal commands
                if cmd.startswith('#'):

                    """
                    INTERNAL COMMANDS
                    """

                    if cmd == "#help" or cmd == "#":
                        print('{: <5}'.format('Welcome to MasterSSH!'))
                        print('Made by Jaan Porkon')
                        print('https://github.com/JaanPorkon/master-ssh')
                        print('')
                        print('Examples:')
                        print('')
                        print('{param: <55}{help}'.format(param='#list', help='Lists all connections.'))
                        print('{param: <55}{help}'.format(param='#connect [host] [user] [password] [port] [name]', help='Connects to a new server. Port and name are optional!'))
                        print('{param: <55}{help}'.format(param='#disconnect [host]', help='Disconnects the host.'))
                        print('{param: <55}{help}'.format(param='#ignore [host,host2,...] [command]', help='Does not send a command to ignored servers.'))
                        print('')

                    # List all connections
                    elif cmd == "#list":
                        for name, connection in self.connection_pool.items():
                            is_alive = connection.get_transport().is_active()

                            if is_alive:
                                self.print_action("%s is active!" % name)
                            else:
                                self.print_server_error("%s is disconnected!" % name)

                    elif cmd.startswith('#connect'):
                        data = cmd.replace('#connect', '').strip().split(' ')
                        data_length = len(data)

                        if data_length < 3:
                            self.print_error('Not enough arguments! Use: #connect [host] [user] [password] [port] [name] - port and name are optional!')
                        else:
                            fields = {'host': data[0], 'user': data[1], 'password': data[2], 'port': int(self.config.port), 'name': data[0]}

                            if data_length == 4:
                                fields['port'] = int(data[3])
                            elif data_length == 5:
                                fields['port'] = int(data[3])
                                fields['name'] = data[4]

                            self.connect(fields['name'], fields['host'], fields['user'], fields['password'], fields['port'])

                    # Disconnect specific servers from the pool
                    elif cmd.startswith('#disconnect'):
                        servers = cmd.replace('#disconnect', '').strip()

                        for server in servers.split(','):
                            if server in self.connection_pool:
                                server = server.strip()
                                connection = self.connection_pool[server]

                                try:
                                    if connection.get_transport().is_active():
                                        connection.exec_command('exit', timeout=self.config.exit_timeout)
                                        connection.close()

                                        self.connection_pool.pop(server)
                                        self.print_success("%s successfully disconnected!" % server)
                                    else:
                                        self.connection_pool.pop(server)

                                except Exception as e:
                                    self.print_error('Unable to disconnect: %s!' % server)
                                    self.print_exception(e)

                            else:
                                self.print_error("%s does not exist!" % server)

                        if len(self.connection_pool) == 0:
                            self.print_message("Connection pool is empty, closing the program..")
                            sys.exit(0)

                    else:

                        """
                        SERVER COMMANDS
                        """

                        # If user wishes to ignore specific servers, do so ...
                        use_ignore_list = cmd.startswith("#ignore")
                        ignored_server_list = []

                        servers, command = cmd.replace('#ignore ', '').split(' ', 1)

                        for server in servers.split(','):
                            ignored_server_list.append(server)

                        thread_pool = {}
                        thread_pos = 1

                        if use_ignore_list:
                            for name, connection in self.connection_pool.items():
                                if name not in ignored_server_list:
                                    thread_pool[thread_pos] = threading.Thread(target=self.execute, name=name, args=(command.strip(), connection,))
                                    thread_pool[thread_pos].daemon = True
                                    thread_pool[thread_pos].start()
                                    thread_pos += 1
                        else:
                            for name, connection in self.connection_pool.items():
                                thread_pool[thread_pos] = threading.Thread(target=self.execute, name=name, args=(command.strip(), connection,))
                                thread_pool[thread_pos].daemon = True
                                thread_pool[thread_pos].start()
                                thread_pos += 1

                        for i in range(1, thread_pos):
                            thread_pool[i].join()

                # If user haven't defined any internal commands, send user's command to all of the servers
                else:
                    if len(self.connection_pool) == 0:
                        self.print_error('There are no active connections!')
                    else:
                        thread_pool = {}
                        thread_pos = 1

                        for name, connection in self.connection_pool.items():
                            thread_pool[thread_pos] = threading.Thread(target=self.execute, name=name, args=(cmd, connection, self.config.cmd_timeout))
                            thread_pool[thread_pos].daemon = True
                            thread_pool[thread_pos].start()
                            thread_pos += 1

                        for i in range(1, thread_pos):
                            thread_pool[i].join()

    """
    Execute user's command
    """

    def execute(self, cmd, connection, timeout):
        try:
            stdin, stdout, stderr = connection.exec_command(cmd, timeout=timeout)

            error = ""

            for line in stderr:
                error += '%s\n' % line.strip()

            error = error.strip()

            if error != "":
                self.print_server_error(error)

            response = ""

            for line in stdout:
                response += '%s\n' % line.strip()

            response = response.strip()

            if response != "":
                self.print_server_action(response)
        except SSHException as e:
            self.print_error('Unable to execute the command!')
            self.print_exception(e)
        except Exception as e:
            self.print_error('Something went wrong!')
            self.print_exception(e)

    """
    Helper methods
    """

    def print_message(self, message):
        logger.info(colored(message, color='green'))

    def print_action(self, message):
        logger.info(colored(message, color='green'))

    def print_success(self, message):
        logger.info(colored(message, color='green'))

    def print_error(self, message):
        logger.error(colored(message, on_color='on_red', attrs=['bold']))

    def print_exception(self, err):
        logger.exception(err)

    def print_server_action(self, message):
        logger.info('\n%s' % colored(message, color='green'))

    def print_server_error(self, message):
        logger.error('\n%s' % colored(message, on_color='on_red', attrs=['bold']))