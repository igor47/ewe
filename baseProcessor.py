#!/usr/bin/python

import os
import os.path, re, time, socket
from features import *

#the main shebang!
class baseProcessor:
	def __init__(self,logger,config):
		self.logger = logger
		self.indexes = config['indexes']
		self.defaultindex = config['defaultindex']
		self.documentroot = config['documentroot']
		self.cgipath = config['cgipath']

		self.persistence = config['persistent']

	#some regular expressions used in parsing requests
	reqRe = re.compile(r"^(\w+)\s+(\S+?)\s+HTTP/(\d.\d)\s*(.*)",
										re.MULTILINE|re.DOTALL)
	multilineHeader = re.compile(r",\s*$\s+",re.MULTILINE)
	headerLineRe = re.compile(r"^(\S+?):\s*(.+)$")
	headerValues = re.compile(r"\s*(\S+?)\s*(?:$|,)")
	
	schemeUrl = re.compile(r"http://(.*)")
	hostUrl = re.compile(r"^([^/]+)(.*)")
	queryString = re.compile(r"([^\?]+)(\?.*)?")

	#the error exception class
	class Error(Exception):
		"""Used to propogate any error condition in request parsing"""
		
	#reads the request and returns a string with the request in it
	def readRequest(self):
		self.sock.settimeout(10)
		request = list()			#list to hold request chunks
	
		while True:					#looping to get a single request
			try:
				line = list()
				while True:
					c = self.sock.recv(1)
					line.append(c)
					if c == '\n': break
			except socket.timeout:	#if we have a timeout
				if self.persistent:		#if we had a persistent connection
					self.persistent = False	#make it unpersistent
					#if we haven't gotten any data, we can just close the connection
					if len(request) == 0 and len(line) == 0:	
						self.sock.close()
						raise socket.timeout				#reraise the timeout so that processor knows

				#if the connection is not persistent or we we read some data in this request
				self.code = 408			#send error 408
				self.persistent = False
				raise self.Error

			if line == ['\n'] or line == ['\r','\n']:
				break
			else:
				request += line
		
		self.sock.settimeout(None)
		request = "".join(request)
		self.request = request

	#parse the request headers into a dictionary
	def parseHeaders(self,headerstring):
		self.multilineHeader.sub(',',headerstring)	#put all headers spanning 
													#multiple lines on one line
		headerlines = headerstring.lower().split('\n')
		headers = dict()
		
		for line in headerlines:
			match = self.headerLineRe.match(line)
			if match:
				header, values = match.groups()
				if header == "if-modified-since" or header == "date" \
									or header == "if-unmodified-since":
					headers[header] = values
				else:
					headers[header] = self.headerValues.findall(values)
		return headers

	#parse the request into a dictionary
	def parseRequest(self):
		match = self.reqRe.match(self.request)
		if not match:
			self.code = 400
			raise self.Error

		request = dict()
		request['method'] = match.group(1).lower()
		request['url'] = urlDecode(match.group(2))
		request['version'] = match.group(3)
		request['headers'] = self.parseHeaders(match.group(4))

		if request['method'] not in ('get','head','post'):
			self.code = 501
			raise self.Error
			
		if request['version'] == "1.0":
			self.persistent = False
		else:
			if not 'host' in request['headers'].keys():
				self.code = 400				#bad request
				raise self.Error
		
		try:
			if request['headers']['connection'] == 'close':	#if the client wants to close
				self.persistent = False					#don't serve any more requests
		except KeyError:
			pass
			
		self.request = request
	
	#parse the url into its constituent parts
	def parseUrl(self):
		url = self.request['url']
		
		#separate the url into the request and the query string
		url,queryString = self.queryString.match(url).groups()
		if queryString: 
			queryString = queryString.lstrip('?')
			self.request['url'] = url			#save the url w/o query
		self.request["query"] = queryString		#save the query string
		
		match = self.schemeUrl.match(url) 
		if match:	#if this url had a scheme
			url = match.group(1)	#get rid of the scheme
		match = self.hostUrl.match(url) 
		if match: 					#if this url had a host
			url = match.group(2)	#get rid of the host in the url

	#try to open the response file
	def openResponse(self):
		try:
			#first, check if this is a cgi request
			url = self.request['url']
			if url.startswith('/cgi-bin'):  #if its in the cgi directory
				path = self.cgipath + '/' + url.replace('/cgi-bin','',1)
				path = os.path.normpath(path)
				if not os.path.exists(path):	#if it doesn't exist, 
					self.code = 404					#404 error
					raise self.Error
				if os.path.isfile(path):		#if it is a file
					if os.access(path,os.X_OK):		#if executable
						try:
							self.entity = runCgi(path,self.request,self.sock)
						except:
							self.code = 500			#any problems result in 500
							self.persistent = False	#can't recover since there
							raise self.Error		#	might be POST data
						#everything went ok
						self.code = 200			
						self.request['isCgi'] = True
						self.persistent = False		#since we can't determine content-legnth
						return						#just close the connection
			
			#if it wasn't an executable file, just process normally
			self.request['isCgi'] = False
			if self.request['method'] == 'post': #only CGI accepts the post method
				self.code = 405
				self.responseHeaders.append("Allow: GET, HEAD\r\n")
				self.presistent = False			#we cannot persist since there
				raise self.Error				#	might be POST data waiting
				
			rpath = os.path.normpath(self.documentroot + url)
			if os.path.commonprefix((self.documentroot,rpath)) != self.documentroot:
				self.code = 403		#attempted to request above document root
				raise self.Error
	
			else:
				self.request['isCgi'] = False
	
			if os.path.isdir(rpath): 	#if the request is a directory
				if self.request['url'][-1] != '/': 	#if the url didn't come with a trailing slash:
					self.code = 301						#redirect
					loc = "http://" + self.request['headers']['host'][0] + self.request['url'] + '/'
					self.responseHeaders.append("Location: " + loc + "\r\n")
					raise self.Error
	
				rfile = os.path.join(rpath,self.defaultindex)
				if os.path.exists(rfile): 	#if there is a default index there
					rpath = rfile				#we return that
					
				else:						#otherwise
					if not self.indexes:			#if we don't generate indexes
						self.code = 403					#error 403
						raise self.Error
					else:							#if we do generate indexes
						self.entity = genIndex(rpath,self.request['query'],self.request['url'])
						stats = os.stat(rpath)
						self.code = 200
						self.responseHeaders.append("Content-Type: text/html\r\n")
						self.responseHeaders.append("Last-Modified: " + httpdate(stats.st_mtime) + "\r\n")
						self.responseHeaders.append("Content-Length: %d\r\n" % (len(self.entity)))
						return
			
			#if we got this far, rpath is a file request
			rfile = open(rpath)
			stats = os.stat(rpath)
					
			#we could open the file for reading, so everything is OK
			self.code = 200
			self.entity = rfile
			self.responseHeaders.append("Content-Type: " + gettype(rpath) + "\r\n")
			self.responseHeaders.append("Last-Modified: " + httpdate(stats.st_mtime) + "\r\n")
			self.responseHeaders.append("Content-Length: " + str(stats.st_size) + "\r\n")

		except IOError, err:	#this catches any IOError in this function
			errno = err[0]
			if errno == 2:		#no such file
				self.code = 404
			elif errno == 13:	#permission denied
				self.code = 403
			else:				#some other error - raise 500
				self.code = 500
			raise self.Error

	def sendResponseHeader(self):
		headers = ["HTTP/1.1 %d %s\r\n" % (self.code, codes[self.code])]
		headers.append("Date: " + httpdate(time.time()) + "\r\n")
		
		if not self.persistent and self.request['version'] == '1.1':
			headers.append("Connection: close\r\n")

		headers.extend(self.responseHeaders)
		if not self.request['isCgi']:		#don't send the blank line if cgi
			headers.append("\r\n")

		self.sock.sendall("".join(headers))

	def sendError(self):
		print "error - ", self.request['url']
		page = """
		<html>
		<head><title>Error</title></head>
		<body>
		<h1>%d - %s</h1><br>
		<hr>
		Ewe Server - version 1.0 - CMSC 33300
		</body>
		</html>""" % (self.code, codes[self.code])

		self.request['isCgi'] = False	#need this in header-sender
		self.responseHeaders.append("Content-type: text/html\r\n")
		self.responseHeaders.append("Content-length: %d\r\n" % (len(page)))
		self.sendResponseHeader()
		
		if self.request['method'] == 'head': return		#don't send the page for GET
		else: self.sock.sendall(page)
	
	def sendResponse(self):
		self.sendResponseHeader()
		response = self.entity
		
		if self.request['method'] == 'head':
			try: response.close()	
			except: pass
			return
			
		if type(response) == type(str()):	#its a string - probably the directory index
			self.sock.sendall(response)
		else:							#its an open file - read in chunks
			chunk = response.read(32768)
			while len(chunk) != 0:
				self.sock.sendall(chunk)
				chunk = response.read(32768)
			response.close()

	def serveRequest(self,sock,address):
		print "new socket"
		self.persistent = self.persistence

		try:
			while True:
				self.sock = sock
				self.peer = address
				self.request = None
				self.responseHeaders = ["Server: Ewe/1.1\r\n"]
				self.entity = None

				try:
					try:
						self.readRequest()
					except socket.timeout:	#this means persistent connection closed
						return
					self.parseRequest()
					print 'url is ', self.request['url']
					self.parseUrl()
					self.openResponse()
				except self.Error:
					self.sendError()
				else:
					self.sendResponse()

				if not self.persistent:
					self.sock.close()
					break
		except socket.error, e:
			print "Error communicating with ", address, ": ", e
