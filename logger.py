import threading, Queue

class logThread(threading.Thread):
	def __init__(self,logLevel,logFile):
		threading.Thread.__init__(self)
		self.logLevel = logLevel
		self.logFile = logFile
		self.logQueue = Queue.Queue()

	def quit(self):
		self.logQueue.put(None)

	def log(self,message,level):
		if level == 0:
			print message
		if logLevel > level:
			self.logQueue.put(message)

	def run(self):
		if self.logLevel == 0:
			return
		try:
			logfile = open(self.logFile, 'w')
			item = self.logQueue.get()
			while item != None:
				logfile.write(item)
				logfile.write('\n')
				item = self.logQueue.get()

		finally:
			if self.logFile:
				logfile.flush()
				logfile.close()
