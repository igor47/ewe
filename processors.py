#!/usr/bin/env python

import os, sys
import signal
import baseProcessor

class basic(baseProcessor.baseProcessor):
	def __init__(self,logger):
		baseProcessor.baseProcessor.__init__(self,logger)
		
	def process(self,sock,address):
		self.serveRequest(sock,address)

	def quit(self):
		pass

class forked(baseProcessor.baseProcessor):
	def __init__(self,logger):
		baseProcessor.baseProcessor.__init__(self,logger)
		self.childlist = list()
		self.prevsignal = signal.signal(signal.SIGCHLD,self.reaper)

#	def reaper(self):
#		print "caught signal"
#		pid,status = os.waitpid(-1,os.WNOHANG)
#		print "it was for ", pid
#		while pid != 0 and len(self.childlist) != 0:
#			if os.WIFSIGNALED(status) or os.WIFEXITED(status):
#				self.childlist.remove(pid)
#				print "reaped child ", pid
#			pid,status = os.waitpid(-1,os.WNOHANG)

	def reaper(self,signal=None,frame=None):
		for pid in self.childlist:
			pid,status = os.waitpid(pid,os.WNOHANG)
			if os.WIFSIGNALED(status) or os.WIFEXITED(status):
				try:
					self.childlist.remove(pid)
				except ValueError:
					print "tried to remove ", pid, "which was not in the list"
		
	def sigswap(self):
		self.prevsignal = signal.signal(signal.SIGCHLD,self.prevsignal)
		
	def process(self,sock,address):
		print "processing"
		self.sigswap()
		pid = os.fork()
		if pid == 0:	#the child
			print "in the child - starting to serve"
			self.serveRequest(sock,address)
			print "child exiting"
			sys.exit(0)
		
		else:		#the parent
			print "created child ", pid
			self.childlist.append(pid)
			sock.close()
			self.sigswap()
			self.reaper()		#make sure we didn't miss any signalsa
			print "in the parent - going to serve another"

	def quit(self):
		while len(self.childlist) != 0:
			os.kill(self.childlist[0],signal.SIGKILL)
			signal.pause()
