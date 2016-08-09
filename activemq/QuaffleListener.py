import time
import sys

import stomp
import xml.etree.ElementTree as ET
from activemq.enemyCopter.enemyCopter import EnemyCopter

class QuaffleListener(stomp.ConnectionListener):
	def __init__(self, field, ip='10.64.127.10', port=61617):
		"""
			ActiveMQListener Constructor
			Inputs: field - the MainWindow object the field is on, so that
							the listener can update the enemy dictionary
					ip - IP address of ActiveMQ server as a string
					port - port of the activeMQ server
		"""
		self.conn = stomp.Connection([(ip,port)])
		self.field = field

	def on_error(self, headers, message):
		"""
			Executes when given an error message
		"""
		print('received an error "%s"' % message)

	def on_message(self, headers, message):
		"""
			Executes when ActiveMQ sends a message
		"""
		self.activeMQParse(message)

	def startListener(self):
		"""
			Start listening for messages
		"""
		self.conn.set_listener('', self)
		self.conn.start()
		self.conn.connect('admin', 'admin', wait=True)
		self.conn.subscribe(destination='/topic/QuafflePossession', id=2, ack='auto')

		# print "sleeping..."
		# time.sleep(5)

	def connect(self, ip='110.64.127.10', port=61617):
		"""
			Disconnect from current server
			Connect to server with parameters given
		"""
		self.conn.disconnect()
		print "Listener connecting to IP: ", ip, ", port: ", str(port)
		self.conn = stomp.Connection([(ip,port)])

	def disconnect(self):
		"""
			Disconnect from current activeMQ Server
		"""
		print "listener disconnecting from ActiveMQ"
		self.conn.disconnect()

	def activeMQParse(self, message):
		"""
			Parses the activeMQ message and updates the enemyCopter dictionary in
			the field associated with the listener
		"""
		root = ET.fromstring(message)

		# Namespace may not be the same for each one, see if we can modularize this
		namespace = "{http://www.ngc.com/quad/quadlink/icd}"

		sourceID = root.find(namespace + 'SourceID').text		
		ballHolder = root.find(namespace + 'AVID').text

		self.field.hasBall = ballHolder
		
		# Debugging purposes:
		# print "sourceID = ", sourceID
		# print "Possession = ", posession