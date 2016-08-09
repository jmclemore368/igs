import time
import sys

import stomp
import xml.etree.ElementTree as ET
from activemq.enemyCopter.enemyCopter import EnemyCopter

class EnemyListener(stomp.ConnectionListener):
    def __init__(self, field, ip='10.10.58.85', port=61617):
        """
            EnemyListener Constructor
            Inputs: field - the MainWindow object the field is on, so that
                            the listener can update the enemy dictionary
                    ip - IP address of ActiveMQ server as a string
                    port - port of the activeMQ server
        """
        self.conn = stomp.Connection([(ip,port)])
        self.field = field

    def on_error(self, headers, message):
        """
            Excutes when given an error message
        """
        print('received an error "%s"' % message)

    def on_message(self, headers, message):
        """
            Executes when activeMQ sends a message
        """
        self.activeMQParse(message)

    def startListener(self):
        """
            Start listening for messages
        """
        self.conn.set_listener('', self)
        self.conn.start()
        self.conn.connect('admin', 'admin', wait=True)
        self.conn.subscribe(destination='/topic/CopterInertialState', id=1, ack='auto')

        # print "sleeping..."
        # time.sleep(5)

    def connect(self, ip='10.10.58.85', port=61617):
        """
            Disconnect from current server
            Connect to server with parameters given
        """
        self.conn.disconnect()
        print "Listener connecting to ip: ", ip, ", port: ", str(port)
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

        # If its our copter, ignore the message
        if 'Soar1ng' in sourceID:
            return
        if 'Blue' in sourceID:
            return

        heading = root.find(namespace + 'Heading').text

        positionNode = root.find(namespace + 'XYZPosition')
        x = float(positionNode.findtext(namespace + 'X'))
        y = float(positionNode.findtext(namespace + 'Y'))
        z = float(positionNode.findtext(namespace + 'Z'))


        velocityNode = root.find(namespace + 'Velocity')
        vx = float(velocityNode.findtext(namespace + 'X'))
        vy = float(velocityNode.findtext(namespace + 'Y'))
        vz = float(velocityNode.findtext(namespace + 'Z'))


        attitudeNode = root.find(namespace + 'Attitude')
        yaw = float(attitudeNode.findtext(namespace + 'Yaw'))
        pitch = float(attitudeNode.findtext(namespace + 'Pitch'))
        roll = float(attitudeNode.findtext(namespace + 'Roll'))

        # print "sourceID = ", sourceID
        # print "heading = ", heading
        # print "x = ", x
        # print "y = ", y
        # print "z = ", z
        # print "vx = ", vx
        # print "vy = ", vy
        # print "vz = ", vz     
        # print "Yaw = ", yaw
        # print "Pitch = ", pitch
        # print "Roll = ", roll

        dictionary = self.field.enemyDict

        if sourceID in dictionary.keys():
            currentEnemy = dictionary[sourceID]
            currentEnemy.update(x, y, z, heading, vx, vy, vz, yaw, pitch, roll)         
        else:
            dictionary[sourceID] = EnemyCopter(sourceID, len(dictionary), x, y, z, heading, vx, vy, vz, yaw, pitch, roll)

        # print dictionary[sourceID] #Uncomment this if debugging ActiveMQ
        # print "Position Listener Running..."




# print "instantiate listener"
# listener = EnemyListener()
# print "starting listener"
# listener.startListener()
# print "disconnecting"
# listener.disconnect()