#!/usr/bin/python

import sys,os
import socket,ConfigParser
import logger,processors

def generateConfig():
	filename = raw_input("What do you want to name your config file?")
	try:
		fd = open(filename,"w")
	except IOError, e:
		print "Unable to create file: ",e
		sys.exit(5)
	
	fd.write(configfile)
	fd.flush()
	fd.close()
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
		print "Configuration file " + filename + " could not be parsed.\
				Try creating a new one with the -n option"
		sys.exit(3)
	else:
		if not (opts.has_section("files and paths")	
				or opts.has_section("server features")):
			print "Required sections are missing from the config file.\
					Try creating a new one with the -n option"
			sys.exit(4)
		return opts

def buildLogger(opts):
	logfile=opts.get("files and paths","logfile")
	loglevel=opts.get("server features","loglevel")	
	
	logThread = logger.logThread(loglevel,logfile)
	logThread.start()
	return logThread
	
def initProcessor(opts,logger):
	concurrency = opts.get("server features","concurency")

	if concurrency == "none":
		processor = processors.basic(logger)
	elif concurrency == "processes":
		processor = processors.forked(logger)
	
	processor.indexes = opts.getboolean("server features", "indexes")
	processor.defaultindex = opts.get("files and paths", "defaultindex")
	processor.documentroot = opts.get("files and paths", "document root")

	return processor
	
def serveRequests(processor,port):
	sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	sock.bind(('',port))
	sock.listen(5)
	while True:
		con,address = sock.accept()
		processor.process(con,address)
	
def main():
	opts = readConfigFile()
	try:
		try:
			logger = buildLogger(opts)
			try:
				processor = initProcessor(opts,logger)
				serveRequests(opts,processor)
			finally:
				if processor: processor.quit()
		finally:
			if logger: logger.quit()
	except ConfigParser.NoOptionError, e:
		print e + "\nOption missing.  Add it or generate a new config file\
					using the -n switch"
		exit(7)

	except socket.error, e:
		if len(e) == 2:
			print "Socket Error %d: %s ... Quiting" % (e[0],e[1])
		else:
			print "Socket Error: %s ... Quiting" % (e)
		sys.exit(8)
		
	except KeyboardInterrupt:
		print "Interrupt caught ... Quiting"
		sys.exit(9)
			
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
#    log verbosity: (0 = no logfile, 3 = max verbosity)
loglevel = 0

[Files And Paths]
#    what is the path to the '/' URI? (default: . )
documentroot = .
#    where should the log be written? (default: ewe.log)
logfile = ewe.log
#    what should the server return if it recieves a request for a directory (default: index.html)
defaultindex = index.html
"""

if __name__ == "__main__":
	main()
	sys.exit(0)
