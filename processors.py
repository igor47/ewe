#!/usr/bin/env python

import os, sys
import signal,threading,Queue
import baseProcessor

class basic(baseProcessor.baseProcessor):
	def __init__(self,logger,indexes,defaultindex,documentroot):
		baseProcessor.baseProcessor.__init__(self,logger)
		self.indexes = indexes
		self.defaultindex = defaultindex
		self.documentroot = documentroot
		
	def process(self,sock,address):
		self.serveRequest(sock,address)

	def quit(self):
		pass

class forked(baseProcessor.baseProcessor):
	def __init__(self,logger,indexes,defaultindex,documentroot):
		baseProcessor.baseProcessor.__init__(self,logger)
		self.indexes = indexes
		self.defaultindex = defaultindex
		self.documentroot = documentroot
	
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
	def __init__(self,logger,indexes,defaultindex,documentroot):
		self.logger = logger
		self.indexes = indexes
		self.defaultindex = defaultindex
		self.documentroot = documentroot
		
		self.threadList = list()
		self.mutex = threading.Lock()
	
	def process(self,sock,address):
		thread = threading.Thread(target=self.runThread,
									args=(sock,address))
		thread.start()
	
	def runThread(self,sock,address):
		processor = baseProcessor.baseProcessor(self.logger)
		processor.indexes = self.indexes
		processor.defaultindex = self.defaultindex
		processor.documentroot = self.documentroot

		me = threading.currentThread().getName()
		self.mutex.acquire()
		self.threadList.append(me)
		self.mutex.release()

		try:
			processor.serveRequest(sock,address)
		except:
			print "Server thread ", me, "encounted an error"
			print sys.exc_info()

		self.mutex.acquire()
		self.threadList.remove(me)
		self.mutex.release()

	def quit(self):
		self.mutex.acquire()
		left = len(self.threadList)
		self.mutex.release()
		if left > 0:
			print "Warning:", left, " threads are still running"

class threadpool:
	def __init__(self,logger,indexes,defaultindex,documentroot,threads=5):
		self.logger = logger
		self.indexes = indexes
		self.defaultindex = defaultindex
		self.documentroot = documentroot
		self.threads = threads
		
		self.queue = Queue.Queue(threads)
		
		for i in xrange(threads):
			worker = poolThread(logger,self.queue)
			worker.indexes = self.indexes
			worker.defaultindex = self.defaultindex
			worker.documentroot = self.documentroot

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
	def __init__(self,logger,queue):
		baseProcessor.baseProcessor.__init__(self,logger)
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
