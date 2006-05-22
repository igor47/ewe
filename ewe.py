#!/usr/bin/python

import sys,os
import ConfigParser
import logger

def generateConfig():
	filename = raw_input("What do you want to name your config file?")
	try:
		file = open("filename")
	except IOError, e:
		print "Unable to create file: " + e
		sys.exit(4)
	
	file.write(configfile)
	file.flush()
	file.close()
	print "Configuration file written"

def readConfigFile():
	if len(sys.argv) != 2:
		print "Usage: "+sys.argv[0]+"[<configuration file>|-n]"
		sys.exit(1)
	
	filename = sys.argv[1]
	if filename == '-n':
		generateConfig()
		sys.exit(0)
	
	if not os.access(filename,os.R_OK):
		print "Cannot read file " + filename + " - please make sure that\
		the file exists and that you have appropriate permissions to read it."
		sys.exit(2)
	
	opts = ConfigParser.ConfigParser()
	try:
		opts.read(filename)
	except ConfigParser.ParsingError:
		print "Configuration file " + filename + " could not be parsed."
		sys.exit(3)
	else:
		return opts

def buildLogger(opts):
	try:
		logfile = opts.get("files and paths", "logfile")
	except (ConfigParser.NoSectionError, ConfigParser.NoOptionError):
		logfile = "ewe.log"
	
	logQueue = Queue.Queue()
	logThread = logger.logThread(logQueue,logfile)
	logThread.start()
	return logQueue
	
def buildProcessor(opts):
	class processor	
	
	
def serveRequests(processor,port):
	sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	sock.bind(('',port))
	sock.listen(5)
	try:
		
	
def main():
	opts = readConfigFile()
	logger = buildLogger(opts)
	processor,port = buildProcessor(opts)
	serveRequests(processor,port,debugger)
	exit(0)
	
configfile = """\
[Server Features]
#   which concurency model should the server use? valid models are 
#	none, processes, threads and threadpool (default: none)
concurency = none
#   if concurency is threadpool, how many threads should the server pre-fork? (default: 5)
poolthreads = 5
#    generate directory indexes? (default: no)
indexes = no
#    should the server maintaign persistent connections? (default: no)
persistence = no
#    log verbosity: (default: 0 max: 3)
debug = 0

[Files And Paths]
#    what is the path to the '/' URI? (default: . )
documentroot = .
#    where should the log be written? (default: ewe.log)
logfile = ewe.log
#    what should the server return if it recieves a request for a directory (default: index.html)
defaultindex = index.html
"""

if __init__ == "__main__":
	main()
	sys.exit(0)
