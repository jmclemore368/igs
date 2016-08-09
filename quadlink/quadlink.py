import time
import sys

import stomp

class Quadlink(stomp.ConnectionListener):
    def __init__(self,ip_address,port):
        self.conn = stomp.Connection([(ip_address,port)])
        self.conn.set_listener('',self)
        self.conn.start()
        self.conn.connect('admin','admin',wait=True)
        
        
        
    def on_error(self, headers, message):
        print('Quadlink received an error "%s"' % message)
        
    def on_message(self, headers, message):
        #TODO Parse messages
        print('received a message "%s"' % message)

        

