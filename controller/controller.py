import xml.etree.ElementTree as ET
from waypoints.waypoints import WayPoints
from copters.copters import Copters
import sys

DEFAULT_TAKEOFF_ALT = 2
DEFAULT_ARENA_WIDTH = 25
DEFAULT_ARENA_HEIGHT = 25
DEFAULT_IP_ADDRESS = '10.10.58.85'
DEFAULT_PORT = 61617

class Controller(object):
    def __init__(self, filename):
        """
            Constructor for the Controller Class

            Input: 
                filename:   
                    a configuration file in xml format 
                    containing copter and waypoint information

            Data Members:
                self.wayoints = dict of waypoints
                self.copter = list ofcopters
        """

        # Read in the xmlTree and find the root node, xmlRoot
        xmlTree = ET.parse(filename)
        xmlRoot = xmlTree.getroot()

        # Create dict of WayPoints from <waypoint>children nodes of xmlRoot
        self.wayPtDict = {}          # Dictionary of Waypoints
        self.dropPtDict = {}            # Dictionary of Drop Points
        self.blockPtDict = {}           # Dictionary of Block Points
        self.flipPtDict = {}            # Dictionary of Flip Points
        self.etcPtDict = {}             # Dictionary of Other Points
        xmlWaypointNodes = xmlRoot.findall("./waypoints/waypoint")
        for xmlWayPointNode in xmlWaypointNodes:
            nextWayPoint = WayPoints(xmlWayPointNode)
            self.wayPtDict[nextWayPoint.id] = nextWayPoint

            # Also place waypoint in correct dictionary
            if nextWayPoint.type == "drop":
                self.dropPtDict[nextWayPoint.id] = nextWayPoint
            elif nextWayPoint.type == "block":
                self.blockPtDict[nextWayPoint.id] = nextWayPoint
            elif nextWayPoint.type == "flip":
                self.flipPtDict[nextWayPoint.id] = nextWayPoint
            else:
                self.etcPtDict[nextWayPoint.id] = nextWayPoint


        # Create list of Copters from <copter> children nodes of xmlRoot
        # Each copter needs an "instance", hence the enumeration
        self.copters = []
        slotsFilled = []
        xmlCopterNodes = xmlRoot.findall("./copters/copter")
        for i, xmlCopterNode in enumerate(xmlCopterNodes):
            nextCopter = Copters(i, xmlCopterNode)
            if nextCopter.enabled == "1":
                if nextCopter.slot in slotsFilled:
                    print "Slots already filled: ", slotsFilled
                    print "Slot ", nextCopter.slot, "is already filled"
                    raise SyntaxError('Multiple copters assigned to same slot')
                slotsFilled.append(nextCopter.slot)
                self.copters.append(nextCopter)

        # Get the takeoff alt from <alt> child node of xmlRoot
        self.takeoffAlt = DEFAULT_TAKEOFF_ALT if \
                          xmlRoot.find("./etc/takeoff/alt").text is None \
                          else float(xmlRoot.find("./etc/takeoff/alt").text)

        # Get the arenaWidth and arenaHeight from <arena> child node of xmlRoot
        arenaNode = xmlRoot.find("./etc/arena")
        self.arenaWidth = DEFAULT_ARENA_WIDTH if \
                          arenaNode.find("width") is None \
                          else float(arenaNode.find("width").text)
        
        self.arenaHeight = DEFAULT_ARENA_HEIGHT if \
                           arenaNode.find("height") is None \
                           else float(arenaNode.find("height").text)

        # Get the arenaWidth and arenaHeight from <arena> child node of xmlRoot
        activemq = xmlRoot.find("./etc/activemq")
        self.ip = DEFAULT_IP_ADDRESS if \
                           activemq.find("ipaddress") is None \
                           else activemq.find("ipaddress").text

        self.port = DEFAULT_PORT if \
                           activemq.find("portnumber") is None \
                           else int(activemq.find("portnumber").text)

        if activemq.find("enabled") is None:
            self.enableActiveMQ = False
        elif int(activemq.find("enabled").text)==1:
            self.enableActiveMQ = True
        else:
            self.enableActiveMQ = False

        self.copterParamDict = {}
        paramNode = xmlRoot.find("./etc/copter-param")
        for param in list(paramNode):
            self.copterParamDict[param.tag] = float(param.text)

    def instantiate(self, copter, field):
        """
            Connect to the simulation or actual copter
        """
        if int(copter.enabled):
            if (copter.type == "sitl") or (copter.connect == "sim"):
                 copter.connection = None
            # use function to avoid race condition between thread prints
            tempConnect = "Simulation" if copter.connection is None else copter.connection
            self.thread_safe_print("\n------------------\n"
                                   + "id:" + str(copter.id)
                                   + "\ntype:" + str(copter.type)
                                   + "\ndx:" + str(copter.dx)
                                   + "\ndy: " + str(copter.dy)
                                   + "\ndz: " + str(copter.dz)
                                   + "\nconnection: " + str(tempConnect)
                                   + "\n------------------\n")

            field.add_vehicle(copter)

        
    def thread_safe_print(self, content):
        print "{0}\n".format(content)


         
        
    
