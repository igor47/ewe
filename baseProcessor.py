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

def httpdate():
	return time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime())
	
escapeSeq = re.compile(r"%(..)")
def urlDecode(url):
	def unescaper(match):
		return chr( int(match.group(1),16) )
	
	return escapeSeq.sub(unescaper,url)

class baseProcessor:
	def __init__(self,logger):
		self.logger = logger

	reqRe = re.compile(r"^(\w+)\s+(\S+?)\s+HTTP/(\d.\d)\s*(.*)",
										re.MULTILINE|re.DOTALL)
	multilineHeader = re.compile(r",\s*$\s+",re.MULTILINE)
	headerLineRe = re.compile(r"^(\S+?):\s*(.+)$")
	headerValues = re.compile(r"\s*(\S+?)\s*(?:$|,)")
	
	schemeUrl = re.compile(r"http://(.*)")
	hostUrl = re.compile(r"^([^/]+)(.*)")
	queryString = re.compile(r"([^\?]+)(\?.*)?")

	class Error(Exception):
		"""Used to propogate any error condition in request parsing"""
		
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
		print self.request
	
	def parseHeaders(self,headerstring):
		self.multilineHeader.sub(',',headerstring)
		headerlines = headerstring.lower().split('\n')
		headers = dict()
		
		for line in headerlines:
			match = self.headerLineRe.match(line)
			if match:
				header, values = match.groups()
				headers[header] = self.headerValues.findall(values)
				
		return headers

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
	
	def parseUrl(self):
		url = self.request['url']
		match = self.schemeUrl.match(url)
		if match:
			url = match.group(1)
		match = self.hostUrl.match(url)
		if match:
			url = match.group(2)
			self.request["host"] = match.group(1)
			
		url,queryString = self.queryString.match(url).groups()
		if queryString:
			self.request["query"] = queryString.lstrip('?')

		self.documentroot = os.path.abspath(self.documentroot)
		self.request["path"] = os.path.normpath(self.documentroot + url)
	
	def openResponse(self):
		root = self.documentroot
		rpath = self.request["path"]
		
		if os.path.commonprefix((root,rpath)) != root:
			self.code = 403
			raise self.Error

		self.code = 200
		self.request["content-type"] = 'text/html'
		self.request["last-modified"] = httpdate()
	
	def sendResponseHeader(self):
		header = "HTTP/1.0 %d %s\r\n" % (self.code, codes[self.code])
		header += "Server: Ewe/1.0\r\n"
		header += "Date: " + httpdate() + "\r\n"

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
		page = """
		<html>
		<head><title>The page!</title></head>
		<body>
		<h1>the page!</h1>""" + str(self.request) + """
		</body></html>"""

		self.sock.sendall(page)
		self.sock.close()
		
		
