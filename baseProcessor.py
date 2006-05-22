#!/usr/bin/python

class baseProcessor:
	def log(self,message,level)
		if level == 0:
			print message
		self.logQueue.put((message,level))
	
	def readRequest(self,socket):
		socket.settimeout(2)
		timeouts = 0
		pieces = list()
		while True:
			try:
				piece = socket.recv(128)
			except socket.timeout:
				timeouts += 1
				if timeouts > 15:
					return
				continue
			else:
				timeouts = 0
			
			if len(piece) <= 3:			#if we get small pieces, we might miss
				piece = pieces.pop(-1) + piece	#the CRLFCRLF
	
			parts = piece.split("\r\n\r\n")	#break the string up on CRLFCRLF
			pieces.append(parts[0])			#the part before goes in the list

			if len(parts) > 1:		#if we had two parts, CRLFCRLF encountered
				break

		socket.shutdown(socket.SHUT_RD)
		request = "".join(pieces)
		processRequest(request)
					
