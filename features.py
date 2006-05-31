#!/usr/bin/python

import os
import time,re
import sys

codes = {
100:"Continue",
200:"OK",
202:"Accepted",
204:"No Content",
301:"Moved Permanently",
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

def parseQuery(query):
	pairs = query.split('&')
	query = dict()
	for pair in pairs:
		try:
			key,value = pair.split('=')
		except ValueError:
			continue
		query[key] = value
	
	return query
		
def parseListing(listing,path,key):
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

	return lines

	
def genIndex(path,params,url):
	key = 0
	reverse = False
	reversing = [0,0,0]

	if params:
		query = parseQuery(params)
		try:
			key = int(query['key'])
		except KeyError:
			pass
		try:
			reverse = bool(query['reverse'])
		except KeyError:
			pass
	
	listing = os.listdir(path)
	listing = parseListing(listing,path,key)
	if reverse:
		listing.reverse()
	else:
		reversing[key] = 1

	#format the fields like they'll be displayed
	postfixes = ['','KB','MB','GB','TB','PB','EB','ZB','YB']
	for line in listing:
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
	page = ('<html>\n\t<head><title>%s</title></head>\n\
	\t<body>\n\t\t<h1>%s</h1>\n\
	<pre><a href="?key=0&reverse=%d">Name</a>' + ' '*36 + 
	'<a href="?key=1&reverse=%d">Last Modified</a>\t\t\t<a href="?key=2&reverse=%d">Size</a><hr>') % (
							title,title,reversing[0],reversing[1],reversing[2])
	for line in listing:
		page += ("""<a href="%s">%s</a>""" + ' '*(40-len(line[0])) + 
				"""%s\t%s\n""") % (line[0],line[0],line[1],line[2])
	
	page += "<hr></pre></body></html"
	return page

class cgiError(Exception):
	"""Used to signal cgi errors - DUH!"""

def buildEnviron(request,sock):
	environ = dict()

	if request['query']:
		environ['QUERY_STRING'] = request['query']
	else:
		environ['QUERY_STRING'] = ""

	environ['REQUEST_METHOD'] = request['method'].upper()	
	environ['REQUEST_URI'] = request['url']

	environ['SERVER_SOFTWARE'] = "Ewe/1.0"
	environ['SERVER_NAME'] = request['headers']['host'][0]
	environ['GATEWAY_INTERFACE'] = "CGI/1.1"
	environ['SERVER_PROTOCOL'] = "HTTP/" + request['version']
	environ['SERVER_PORT'] = str(sock.getpeername()[1])
	environ['SCRIPT_NAME'] = request['url']
	environ['REMOTE_ADDR'] = str(sock.getpeername()[0])

	for key,value in request['headers'].items():
		key = "HTTP_" + key.replace('-','_').upper()
		environ[key] = ",".join(value)

	return environ

def runCgi(path,request,sock):
	#build the environment dictionary
	environ = buildEnviron(request,sock)
	argv = [os.path.basename(path)]

	#check method
	if request['method'] == 'post':
		try:
			bodyLen = int(request['headers']['content-length'][0])
			environ['CONTENT_LENGTH'] = str(bodyLen)
			contType = request['headers']['content-type']
			environ['CONTENT_TYPE'] = str(contType)
		except:
			raise cgiError
	
		read = 0
		body = list()
		while read < bodyLen:
			piece = sock.recv(bodyLen - read)
			read += len(piece)
			body += piece
		body = "".join(body)

	else:
		body = None

	toChild = os.pipe()		#read, write
	fromChild = os.pipe()

	pid = os.fork()
	if pid == 0:	#child
		try:
			sock.close()

			os.close(toChild[1])		#close the write end
			os.dup2(toChild[0],0)		#dup
		
			os.close(fromChild[0])		#close the read end
			os.dup2(fromChild[1],1)		#dup
			
			os.execve(path,argv,environ)	#exec
		except:				#if anything goes wrong
			print "Content-type: text/html\r\n\r\n"
			print "<html><head><title>Error</title></head>"
			print "<body><h1>There was an error running the script.</h1>"
			print "</body></html>"
			sys.exit()

	os.close(toChild[0])		#close the read end
	toChild = os.fdopen(toChild[1],'w')		#make into python file
		
	os.close(fromChild[1])		#close the write end
	fromChild = os.fdopen(fromChild[0])	#make into python file

	if body:
		toChild.write(body)
		toChild.flush()
	toChild.close()

	entity = fromChild.read()
	fromChild.close()
	os.waitpid(pid,0)

	try:
		headers,body = entity.split('\r\n\r\n',1)
	except ValueError:
		try:
			headers,body = entity.split('\n\n',1)
		except ValueError:
			raise cgiError			#there were no headers in the script

	headers += '\r\n'		#we need to add the CRLF after the last header back
	if not "content-length" in headers.lower():
		headers += "Content-length: %d\r\n" % ( len(body) )
	return headers,body
