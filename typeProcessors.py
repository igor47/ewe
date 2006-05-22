#!/usr/bin/env python

class basic:
	def __init__(self):
		pass
		
	def process(self,sock,address):
		self.sock = sock
		self.peer = address
		self.error = 0
		
		try:
			self.readRequest()
			self.parseRequest()
			self.openResponse()
		except self.Error:
			self.sendError()
		else:
			self.sendResponse()
		
	def quit(self):
		pass

class forked:
	def __init__(self):
		self.childlist = list()
		self.prevsignal = signal.signal(signal.SIGCHLD,self.reaper)

	def reaper(self):
		pid,status = os.waitpid(-1,os.WNOHANG)
		while pid != 0:
			if WIFSIGNALED(status) or WIFEXITED(status):
				self.childlist.remove(pid)
			pid,status = os.waitpid(-1,os.WNOHANG)
		
	def sigswap(self):
		self.prevsignal = signal.signal(signal.SIGCHLD,self.prevsignal)
		
	def process(self,sock,address):
		
		self.sigswap()
		pid = os.fork()
		if pid == 0:	#the child
			basic.process(self,sock,address)
			sys.exit(0)
		
		else:		#the parent
			self.childlist.append(pid)
			self.sigswap()
			self.reaper()		#make sure we didn't miss any signals

	def quit(self):
		while len(self.childlist) != 0:
			os.kill(self.childlist[0],signal.SIGKILL)
			signal.pause()
	
class threaded:
	def __init__(self):
		
