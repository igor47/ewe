#!/usr/bin/env python

import os, sys
import signal,threading,Queue
import baseProcessor

class basic(baseProcessor.baseProcessor):
	def __init__(self,logger,config):
		baseProcessor.baseProcessor.__init__(self,logger,config)
		
	def process(self,sock,address):
		self.serveRequest(sock,address)

	def quit(self):
		pass

class forked(baseProcessor.baseProcessor):
	def __init__(self,logger,config):
		baseProcessor.baseProcessor.__init__(self,logger,config)
	
		self.childlist = list()
		self.ischild = False

	def reaper(self):
		for pid in self.childlist:
			pid,status = os.waitpid(pid,os.WNOHANG)
			if pid == 0:
				continue
			if os.WIFSIGNALED(status) or os.WIFEXITED(status):
				self.childlist.remove(pid)
		
	def sigswap(self):
		self.prevsignal = signal.signal(signal.SIGCHLD,self.prevsignal)
		
	def process(self,sock,address):
		pid = os.fork()
		if pid == 0:	#the child
			self.ischild = True
			self.serveRequest(sock,address)
			sys.exit(0)
		
		else:		#the parent
			self.childlist.append(pid)
			sock.close()
			self.reaper()		#make sure we didn't miss any signalsa

	def quit(self):
		if self.ischild: return
		while len(self.childlist) != 0:
			os.kill(self.childlist[0],signal.SIGKILL)
			self.reaper()

class threaded:
	def __init__(self,logger,config):
		self.logger = logger
		self.config = config

		self.threadList = list()
		self.cond = threading.Condition()
	
	def process(self,sock,address):
		thread = threading.Thread(target=self.runThread,
									args=(sock,address))
		thread.start()

		#make sure we don't start more then 250 threads
		#or we run out of file descriptors
		self.cond.acquire()
		while len(self.threadList) > 250:
			self.cond.wait()
		self.cond.release()
			
	def runThread(self,sock,address):
		processor = baseProcessor.baseProcessor(self.logger, self.config)

		me = threading.currentThread().getName()
		self.cond.acquire()
		self.threadList.append(me)
		self.cond.release()

		try:
			processor.serveRequest(sock,address)
		except:
			print "Server thread ", me, "encounted an error"
			print sys.exc_info()

		self.cond.acquire()
		self.threadList.remove(me)
		self.cond.notifyAll()
		self.cond.release()

	def quit(self):
		if len(self.threadList) > 0:
			print "Warning:", left, " threads are still running"

class threadpool:
	def __init__(self,logger,config):
		self.logger = logger
		self.config = config
		self.threads = config["poolthreads"]
		
		self.queue = Queue.Queue(self.threads)
		
		for i in xrange(self.threads):
			worker = poolThread(logger,config,self.queue)
			thread = threading.Thread(target=worker.listen)
			thread.start()
	
	def process(self,sock,address):
		try:
			self.queue.put((sock,address),timeout=20)
		except Queue.Full:
			self.sendBusy(sock)
	
	def sendBusy(self,sock):
		packet = "HTTP/1.0 503 Service Unavailable \r\n\
		Server: Ewe/1.0 \r\n\
		Content-type: text/html \r\n\
		\r\n\
		<html>\n\
		<head><title>503 Service Unavailable</title></head>\n\
		<body>\n\
		<h1>Service Unavailable</h1>\n\
		<hr>\n\
		Please try your request again later\n\
		</body></html>"

		sock.sendall(packet)
		sock.close()

	def quit(self):
		for i in xrange(self.threads):
			self.queue.put(None)
			
class poolThread(baseProcessor.baseProcessor):
	def __init__(self,logger,config,queue):
		baseProcessor.baseProcessor.__init__(self,logger,config)
		self.queue = queue
	
	def listen(self):
		me = threading.currentThread().getName()
		while True:
			job = self.queue.get()
			if job == None:
				return;
			else:
				try:
					self.serveRequest(job[0],job[1])
				except:
					print "Server thread ", me, "encounted an error"
					print sys.exc_info()
