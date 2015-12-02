#!/usr/bin/env python

import paramiko
import requests
import optparse
import sys
import time
import threading

class MasterSSH:

	connectionPool = {}
	creditials = []

	def __init__(self):
		parser = optparse.OptionParser()
		parser.add_option('--cred-url', dest='cred_url', default=None)
		parser.add_option('--cred-file', dest='cred_file', default=None)

		options, remainder = parser.parse_args()

		credSourceType = None
		credSourcePath = None

		if options.cred_file != None:
			credSourcePath = options.cred_file
			credSourceType = 'file'
			
		if options.cred_url != None:
			credSourcePath = options.cred_url
			credSourceType = 'url'

		if credSourcePath == None:
			print "You need to specify a creditials path [--cred-url, --cred-path]"
			sys.exit(1)

		if credSourceType == 'file':
			with open(credSourcePath, 'r') as f:
				for line in r.readlines():
					data = line.strip().split(',')

					self.creditials.append({
						'name': data[0],
						'host': data[1],
						'username': data[2],
						'password': data[3]
					})

		if credSourceType == 'url':
			response = requests.get(credSourcePath)

			for line in response.text.strip().split('\n'):
				data = line.split(',')

				self.creditials.append({
					'name': data[0],
					'host': data[1],
					'username': data[2],
					'password': data[3]
				})

	def createConnections(self):	

		threadPool = {}
		threadPos = 1		

		for cred in self.creditials:
			threadPool[threadPos] = threading.Thread(target=self.connect, args=(cred['name'], cred['host'], cred['username'], cred['password'],))
			threadPool[threadPos].daemon = True
			threadPool[threadPos].start()
			threadPos += 1
			
		for i in range(1, threadPos):
			threadPool[i].join()
			

	def connect(self, name, host, username, password):

		tries = 1
		maxTries = 5

		while True:

			if tries == maxTries:
				print "Unable to connect to: " + cred['name']
				break

			try:
				self.connectionPool[name] = paramiko.SSHClient()
				self.connectionPool[name].set_missing_host_key_policy(paramiko.AutoAddPolicy()) 
				self.connectionPool[name].connect(host, username=username, password=password)

				connected = True
			except:
				print "\033[91mFailed to connect to: " + name + "... retrying (" + str(tries) + "/" + str(maxTries) + ")\033[0m"
				connected = False
				tries += 1
				time.sleep(3)

			if connected:
				print "\033[92mSuccessfully connected to: " + name + '\033[0m'
				break


	def closeConnections(self):

		threadPool = {}
		threadPos = 1	

		for name in self.connectionPool:	
			threadPool[threadPos] = threading.Thread(target=self.exit, args=(name,))
			threadPool[threadPos].daemon = True
			threadPool[threadPos].start()
			threadPos += 1
							
		for i in range(1, threadPos):
			threadPool[i].join()	

	def exit(self, name):
			self.connectionPool[name].exec_command('exit')
			self.connectionPool[name].close()
			print '\033[92m\033[1m\033[4m[' + name + ']\033[0m: disconnected...'

	def listen(self):
		
		while True:
			cmd = raw_input('\nmaster-ssh$ ').strip()

			if cmd == "exit":
				self.closeConnections()
				break
			else:

				if cmd.startswith('master-ssh'):
					findSpace = cmd.find(' ')
					command = cmd[(findSpace + 1):len(cmd)].strip()
					server = cmd[11:findSpace].strip()

					stdin, stdout, stderr = self.connectionPool[server].exec_command(command)

					response = '\033[92m\033[1m\033[4m[' + server + ']\033[0m: \n'

					for line in stderr:
						response += '\033[91m' + line + '\033[0m'

					for line in stdout:
						response += line

					print response.strip('\n')

				else:
					threadPool = {}
					threadPos = 1	

					for name,con in self.connectionPool.iteritems():							

						threadPool[threadPos] = threading.Thread(target=self.execute, args=(cmd, name, con,))
						threadPool[threadPos].daemon = True
						threadPool[threadPos].start()
						threadPos += 1
							
					for i in range(1, threadPos):
						threadPool[i].join()
							
						

	def execute(self, cmd, name, con):
		stdin, stdout, stderr = con.exec_command(cmd)

		response = '\n\033[92m\033[1m\033[4m[' + name + ']\033[0m: \n'

		for line in stderr:
			response += '\033[91m' + line + '\033[0m'

		for line in stdout:
			response += line

		print response.strip('\n')


m = MasterSSH()
m.createConnections()
m.listen()

print "SSH sessions ended, closing..."
sys.exit(0)
