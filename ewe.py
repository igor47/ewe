#!/usr/bin/python

import sys,os
import ConfigParser

def generateConfig():
	filename = raw_input("What do you want to name your config file?")
	try:
		file = open("filename")
	except IOError, e:
		print "Unable to create file: " + e
		sys.exit(4)
	
	file.write(configfile)
	file.close()

def readConfigFile():
	try:
		filename = sys.argv[1]
	except KeyError:
		print "Usage: "+sys.argv[0]+"[<configuration file>|-n]"
		sys.exit(1)
	
	if filename == '-n':
		generateConfig()
		sys.exit(0)
	
	if not os.access(filename,os.R_OK):
		print "Cannot read file " + filename + " - please make sure\
		you the file exists and you have appropriate permissions to read it."
		sys.exit(2)
	
	opts = ConfigParser.ConfigParser()
	try:
		opts.read(filename)
	except ConfigParser.ParsingError:
		print "Configuration file " + filename + " could not be parsed."
		sys.exit(3)
	else:
		return opts
		
def main():
	opts = readConfigFile()
	processor = buildProcessor(
	
configfile = """\
[Server Features]
#which concurency model should the server use? valid models are 
#	none, processes, threads and threadpool (default: none)
concurency = none
#if concurency is threadpool, how many threads should the server pre-fork? (default: 5)
poolthreads = 5
#what should the server return if it recieves a request for a directory (default: index.html)
defaultindex = index.html
#if the defaultindex is not available when a directory 
#	is requested, generate a directory listing?
indexes = off
#should the server maintaign persistent connections? (default: no)
persistence = no
#should be make a debug log? (default: no)
debug = no


[Files And Paths]
#what is the path to the '/' URI? (default: . )
documentroot = .
#where should the debug log be written? (default: debug.log)
debuglog = debug.log
"""

if __init__ == "__main__":
	main()
	sys.exit(0)
