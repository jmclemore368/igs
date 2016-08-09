from PySide.QtGui import *
from PySide.QtCore import *
import sys
from gui.igs import MainWindow
from controller.controller import Controller
from activemq.EnemyListener import EnemyListener
from activemq.QuaffleListener import QuaffleListener

import threading
import time


if __name__ == '__main__':
    # Instantiate app and controller
    app = QApplication(sys.argv)
    controller = Controller("config/config.xml")

    # get parsed attributes from controller
    copters = controller.copters # list
    wayPoints = controller.wayPtDict #dictionary
    dropPoints = controller.dropPtDict           # Dictionary of Drop Points
    blockPoints = controller.blockPtDict         # Dictionary of Block Points
    flipPoints = controller.flipPtDict           # Dictionary of Flip Points
    otherPoints = controller.etcPtDict           # Dictionary of Other Points
    arenaWidth = controller.arenaWidth # float
    arenaHeight = controller.arenaHeight # float
    takeoffAlt = controller.takeoffAlt # float
    ip = controller.ip # string
    port = controller.port # int
    activeMQenabled = controller.enableActiveMQ #boolean
    paramsDict = controller.copterParamDict #dictionary


    # Print friendly messages
    print "Total number of copters read: %s" % len(copters)
    print "Arena width: %s, Arena height: %s" % (arenaWidth, arenaHeight)
    print "Takeoff altitude: %s" % (takeoffAlt)
    print "IP: %s" % (ip)
    print "port: %s" % (port)
    print "ActiveMQ Enabled: %s" % (activeMQenabled)
    print "Copter Parameters: %s" % (paramsDict)

    print "Total number of waypoints read: %s" % (len(wayPoints.keys()))
    # print "Total number of drop points read: %s" % (len(dropPoints.keys()))
    # print dropPoints
    # print "Total number of block points read: %s" % (len(blockPoints.keys()))
    # print blockPoints
    # print "Total number of flip points read: %s" % (len(flipPoints.keys()))
    # print flipPoints

    # Configure mainWin
    mainWin = MainWindow(arenaWidth, arenaHeight)
    mainWin.setTakeoffAlt(takeoffAlt)
    mainWin.setWaypointDicts(wayPoints, dropPoints, blockPoints, flipPoints, otherPoints)
    mainWin.setCopterParams(paramsDict)

    # Start Listener if ActiveMQ is enabled
    if activeMQenabled:
        try:
            listener1 = EnemyListener(mainWin, ip, port)
            listenThread1 = threading.Thread(target=listener1.startListener,args=())
            listenThread1.start()
            listener2 = QuaffleListener(mainWin, ip, port)
            listenThread2 = threading.Thread(target=listener2.startListener,args=())
            listenThread2.start()
        except:
            print "No active MQ enabled, continuing without activeMQ"
            activeMQenabled = False
        
    # Connect and add each copter using a separate thread for each
    for copter in copters:
        t = threading.Thread(target=controller.instantiate, args=(copter, mainWin,))
        t.start()

    # Send ADSB messages
    t = threading.Thread(target=mainWin.sendADSBtoAll, args = ())
    #t.start()

    # Exit stuff
    ret = app.exec_() 

    mainWin.stopADSB()
    
    # Disconnect from ActiveMQ
    if activeMQenabled:
        listener1.disconnect()
        listener2.disconnect()

    mainWin.closeThreads()
    mainWin.close_sitls()

    sys.exit( ret )
    
    

    
    
###Reference Only###
'''
self.show()

scene.addText("Testing IGS Field")

def mousePressEvent(self, event):
        print "Mouse pressed"
        
#controller.instantiate(copter, mainWin)
'''

