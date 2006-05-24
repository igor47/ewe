#!/usr/bin/python

import os
import os.path, re, time, socket

codes = {
100:"Continue",
200:"OK",
202:"Accepted",
204:"No Content",
400:"Bad Request",
401:"Unauthorized",
403:"Forbidden",
404:"Not Found",
405:"Method Not Allowed",
406:"Not Acceptable",
408:"Request Timeout",
415:"Unsupported Media Type",
500:"Internal Server Error",
501:"Not Implemented",
503:"Service Unavailable",
505:"HTTP Version Not Supported"
}

types = {
".gif":"image/gif",
".jpeg":"image/jpeg",
".jpg":"image/jpeg",
".png":"image/png",
".tiff":"image/tiff",
".tff":"image/tiff",
".txt":"text/plain",
".log":"text/plain",
".htm":"text/html",
".html":"text/html",
".py":"text/plain"
}

#accepts time in seconds since the epoch, returns date in rfc822
def httpdate(rtime):
	return time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime(rtime))

#accepts filename, returns mime type based on extention, or
#application/octet-stream if type cannot be determined
def gettype(rpath):
	ext = os.path.splitext(rpath)[1]
	try:
		return types[ext]
	except KeyError:
		return 'application/octet-stream'
		
#accepts url, returns url with all the % characters decoded into ascii
escapeSeq = re.compile(r"%(..)")
def urlDecode(url):
	def unescaper(match):
		return chr( int(match.group(1),16) )
	
	return escapeSeq.sub(unescaper,url)

def genIndex(path,params,url):
	key = 0
	reverse = False
	reversing = [0,0,0]
	if params:
		paramList = params.split('&')
		for param in paramList:
			try:
				param,value = param.split('=')
			except ValueError:
				continue
			if param == "key":
				key = int(value)
			if param == "reverse":
				reverse = bool(int(value))
				
	listing = os.listdir(path)
	
	lines = list()
	for file in listing:
		if file[0] == '.': continue
		
		filepath = os.path.join(path,file)
		stats = os.stat(filepath)
		
		line = [file]
		line.append(stats.st_mtime)
		if os.path.isdir(filepath):
			line.append(None)
		else:
			line.append(stats.st_size)
		lines.append(line)
	
	#sort using the schwartizan transform
	#decorate:
	dec = [(line[key],line) for line in lines]
	#sort
	dec.sort()
	#undecorate
	lines = [line for d,line in dec]
	if reverse:
		lines.reverse()
	else:
		reversing[key] = 1

	#format the fields like they'll be displayed
	postfixes = ['','KB','MB','GB','TB','PB','EB','ZB','YB']
	for line in lines:
		line[1] = httpdate(line[1]) #convert date to http format
		
		if line[2] == None:		# if it was a directory, 
			line[0] += '/'			#append /
			line[2] = '-'			#replace size with '-'
		elif line[2] < 1024:	# if size is less then 1K
			line[2] = str(line[2])	#just convert it to a string
		else:					# otherwise
			postfix = 0
			size = float(line[2])	#format size properly
			while size > 1024:
				size /= 1024
				postfix += 1
			line[2] = "%.1f%s" % (size,postfixes[postfix])
	
	title = "Index of " + url
	cKey = str(key)
	page = ('<html>\n\t<head><title>%s</title></head>\n\
	\t<body>\n\t\t<h1>%s</h1>\n\
	<pre><a href="?key=0&reverse=%d">Name</a>' + ' '*36 + 
	'<a href="?key=1&reverse=%d">Last Modified</a>\t\t\t<a href="?key=2&reverse=%d">Size</a><hr>') % (
							title,title,reversing[0],reversing[1],reversing[2])
	for line in lines:
		page += ("""<a href="%s">%s</a>""" + ' '*(40-len(line[0])) + 
				"""%s\t%s\n""") % (line[0],line[0],line[1],line[2])
	
	page += "<hr></pre></body></html"
	return page

#the main shebang!
class baseProcessor:
	def __init__(self,logger):
		self.logger = logger

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
		self.sock.settimeout(2)
		timeouts = 0
		pieces = list()
		while True:
			try:
				piece = self.sock.recv(128)
			except socket.timeout:
				timeouts += 1
				if timeouts > 15:
					self.code = 408		#error 408 - timeout
					raise self.Error
				else:
					continue
			else:				#if we get a successful recv, reset timeouts
				timeouts = 0
			
			if len(piece) <= 3:			#if we get small pieces, we might miss
				piece = pieces.pop(-1) + piece	#the CRLFCRLF
	
			parts = piece.split("\r\n\r\n")	#break the string up on CRLFCRLF
			pieces.append(parts[0])			#the part before goes in the list

			if len(parts) > 1:		#if we had two parts, CRLFCRLF encountered
				break
			elif len(piece.split("\n\n")) > 1:	#also break on LFLF for robustness
				break

		self.sock.shutdown(socket.SHUT_RD)		#no more reading on the socket
		self.request = "".join(pieces)

	#parse the request headers into a dictionary
	def parseHeaders(self,headerstring):
		self.multilineHeader.sub(',',headerstring)
		headerlines = headerstring.lower().split('\n')
		headers = dict()
		
		for line in headerlines:
			match = self.headerLineRe.match(line)
			if match:
				header, values = match.groups()
				if header == "if-modified-since":
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
		if request['method'] not in ('get','head'):
			self.code = 501
			raise self.Error
			
		request['url'] = urlDecode(match.group(2))
		request['headers'] = self.parseHeaders(match.group(4))
		self.request = request
	
	#parse the url into an absolute path
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

		#resolve the url as an absolute normalized path
		self.request["path"] = os.path.normpath(self.documentroot + url)

	#try to open the response file
	def openResponse(self):
		root = self.documentroot
		rpath = self.request["path"]
		
		if os.path.commonprefix((root,rpath)) != root:
			self.code = 403		#attempted to request above document root
			raise self.Error

		if os.path.isdir(rpath): #if the request is a directory
			rfile = os.path.join(rpath,self.defaultindex)
			if os.path.exists(rfile): 	#if there is a default index there
				rpath = rfile				#we return that
			else:						#otherwise
				print 'does not exist'
				if not self.indexes:			#if we don't generate indexes
					self.code = 403					#error 403
					raise self.Error
				else:							#if we do generate indexes
					try:
						self.request['response'] = genIndex(rpath,self.request['query'],self.request['url'])
					except IOError, err:
						errno = err[0]
						if errno == 2:		#no such file
							self.code = 404
						elif errno == 13:	#permission denied
							self.code = 403
						else:				#some other error - raise 500
							self.code = 500
						raise self.Error
					else:
						self.code = 200	
						self.request['content-type'] = 'text/html'
						self.request['last-modified'] = httpdate(time.time())
						return
		
		#if we got this far, rpath is a file request
		try:
			rfile = open(rpath)
		except IOError, err:
			errno = err[0]
			if errno == 2:		#no such file
				self.code = 404
			elif errno == 13:	#permission denied
				self.code = 403
			else:				#some other error - raise 500
				self.code = 500
			raise self.Error
		
		#we could open the file for reading, so everything is OK
		self.code = 200
		self.request['response'] = rfile
		self.request['content-type'] = types[os.path.splitext(rpath)[1]]
		self.request['last-modified'] = httpdate(os.stat(rpath).st_mtime)
	
	def sendResponseHeader(self):
		header = "HTTP/1.0 %d %s\r\n" % (self.code, codes[self.code])
		header += "Server: Ewe/1.0\r\n"
		header += "Date: " + httpdate(time.time()) + "\r\n"

		if self.code == 200:
			header += "Last-Modified: " + self.request["last-modified"] + "\r\n"
			header += "Content-Type: " + self.request["content-type"] + "\r\n"

		else:
			header += "Content-Type: text/html\r\n"

		header += "\r\n"
		self.sock.sendall(header)

	def sendError(self):
		self.sendResponseHeader()
		page = """
		<html>
		<head><title>Error</title></head>
		<body>
		<h1>%d - %s</h1><br>
		<hr>
		Ewe Server - version 1.0 - CMSC 33300
		</body>
		</html>""" % (self.code, codes[self.code])

		self.sock.sendall(page)
		self.sock.close()
	
	def sendResponse(self):
		self.sendResponseHeader()
		response = self.request['response']
		if type(response) == type(str()):	#its a string - probably the directory index
			self.sock.sendall(response)
		else:							#its an open file - read in chunks
			chunk = response.read(32768)
			while len(chunk) != 0:
				self.sock.sendall(chunk)
				chunk = response.read(32768)
			response.close()

		self.sock.close()
		
	def serveRequest(self,sock,address):
		self.sock = sock
		self.peer = address

		try:
			self.readRequest()
			self.parseRequest()
			self.parseUrl()
			self.openResponse()
		except self.Error:
			self.sendError()
		else:
			self.sendResponse()
