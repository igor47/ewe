#!/usr/bin/python

import sys,os
import socket
import logger,processors

config = {
"concurrency":"none",	#default concurrency model
"port":4000,			#default port number

"poolthreads":5, #if preforking, how many threads to create
"indexes":False, 	#generate directory indexes?

"loglevel":0,	#log verbosity (0 = no logfile, 3 = maximum logging)
"logfile":"ewe.log", #where to put the log

"defaultindex":"index.html",	#the default file to open in a directory
"documentroot":"."				#the location of the / url
}

def parseArguments():
	if len(sys.argv) == 1:
		return

	class optionError(Exception):
		pass

	try:
		if len(sys.argv) > 3:
			raise optionError, "Too many arguments"
		
		for arg in sys.argv[1:]:
			if arg in ("-f","-t","-p"): 
				if arg == '-f':
					config["concurrency"] = "forked"
				elif arg == '-t':
					config["concurrency"] = "threaded"
				else:
					config["concurrency"] = "threadpool"
			else:
				try:
					config["port"] = int(arg)
				except ValueError:
					raise optionError, "Invalid argument " + arg
	except optionError, e:
		print "Error parsing arguments:", e
		print "Syntax: %s [-f|-t|-p] [port]" % (sys.argv[0])
		sys.exit(1)

def buildLogger():
	logThread = logger.logThread(config["loglevel"],config["logfile"])
	logThread.start()
	return logThread
	
def initProcessor(logger):
	
	procTypes = {"none":processors.basic,
				"forked":processors.forked
				}
	processor = procTypes[config["concurrency"]](logger)
	
	processor.indexes = config["indexes"]
	processor.defaultindex = config["defaultindex"]
	processor.documentroot = config["documentroot"]

	return processor
	
def serveRequests(processor):
	sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	sock.bind(('',config["port"]))
	sock.listen(5)
	while True:
		con,address = sock.accept()
		processor.process(con,address)
	
def main():
	try:
		try:
			logger = None
			logger = buildLogger()
			try:
				processor = None
				processor = initProcessor(logger)
				serveRequests(processor)
			finally:
				if processor: processor.quit()
		finally:
			if logger: logger.quit()

	except socket.error, e:
		if len(e) == 2:
			print "Socket Error %d: %s ... Quiting" % (e[0],e[1])
		else:
			print "Socket Error: %s ... Quiting" % (e)
		sys.exit(8)
	except KeyboardInterrupt:
		print "Interrupt caught ... Quiting"
		sys.exit(9)
	
if __name__ == "__main__":
	main()
	sys.exit(0)
