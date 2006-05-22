import threading, Queue

class logThread(threading.Thread):
	def __init__(self,logQueue,logFile = None):
		threading.Thread.__init__(self)
		self.logFile = logFile
		self.logQueue = logQueue

	def run(self):
		try:
			if self.logFile:
				logfile = open(self.logFile, 'w')
			item = self.logQueue.get()
			while item != None:
				print item
				if self.logFile:
					logfile.write(item)
					logfile.write('\n')
				item = self.logQueue.get()

		finally:
			if self.logFile:
				logfile.flush()
				logfile.close()
