#!/usr/bin/python

import sys
import ConfigParser

def readConfigFile():
	try:
		filename = sys.argv[1]
	except KeyError:
		print "Usage: "+sys.argv[0]+" <configuration file>"
		sys.exit(1)
	
	opts = ConfigParser.ConfigParser()
	try:
		opts.read(filename)
	except 
		
def main():
	opts = readConfigFile()
	
