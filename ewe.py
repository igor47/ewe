#!/usr/bin/python

import sys,os
import socket
import logger,processors

config = {
"concurrency":"none",	#default concurrency model
"port":4000,			#default port number

"poolthreads":5, #if preforking, how many threads to create
"indexes":True, 	#generate directory indexes?
"persistent":True,

"loglevel":0,	#log verbosity (0 = no logfile, 3 = maximum logging)
"logfile":"ewe.log", #where to put the log

"defaultindex":"index.html",	#the default file to open in a directory
"documentroot":"htdocs",			#the location of the / url
"cgipath":"cgi-bin"					#location of cgi-bin directory
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
					port = int(arg)
				except ValueError:
					raise optionError, "Invalid argument " + arg
				if port < 1 or port > 65535:
						raise optionError, "Invalid port number: %d" % (port)
				config["port"] = int(arg)

	except optionError, e:
		print "Error parsing arguments:", e
		print "Syntax: %s [-f|-t|-p] [port]" % (sys.argv[0])
		sys.exit(1)

def buildLogger():
	logThread = logger.logThread(config["loglevel"],config["logfile"])
	logThread.start()
	return logThread
	
def initProcessor(logger):

	#make sure configfile has proper values
	config['documentroot'] = os.path.abspath(config['documentroot'])
	config['cgipath'] = os.path.abspath(config['cgipath'])

	#mapping of processor types to classes
	procTypes = {"none":processors.basic,
				"forked":processors.forked,
				"threaded":processors.threaded,
				"threadpool":processors.threadpool
				}

	#make the processor
	processor = procTypes[config["concurrency"]](logger,config)
	
	return processor

def serveRequests(processor):
	sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	sock.bind(('',config["port"]))
	sock.listen(5)
	while True:
		con,address = sock.accept()
		processor.process(con,address)
	
def main():
	parseArguments()
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
		print "Socket Error: %s ... Quiting" % (e)
		sys.exit(8)
	except KeyboardInterrupt:
		print "Interrupt caught ... Quiting"
		sys.exit(9)
	
if __name__ == "__main__":
	main()
	sys.exit(0)
