import dronekit
import dronekit_sitl
import pymavlink
import socket 
import exceptions 
import argparse  
import time
import threading
from collections import deque
from math import floor, log10, sqrt
from utils.utils import *


####################################################################################################   
    
class Point:
    def __init__(self,x,y,z):
        self.x = x
        self.y = y
        self.z = z

    def __sub__(self, other):
        return Point(self.x - other.x, self.y - other.y, self.z - other.z)    

####################################################################################################
        
class Copters:
    def __init__(self, instance, node):
        self.instance = instance
        self.id = None if node.get("id") is None else node.get("id")
        self.enabled = None if node.find("enabled") is None else node.find("enabled").text
        self.type = None if node.find("type") is None else node.find("type").text
        self.slot = None if node.find("slot") is None else int(node.find("slot").text)
        self.dx = None if node.find("dx") is None else float(node.find("dx").text)
        self.dy = None if node.find("dy") is None else float(node.find("dy").text)
        self.dz = None if node.find("dz") is None else float(node.find("dz").text)
        self.connection = None if node.find("connect") is None else node.find("connect").text
        self.vehicle = None
        self.location = None
        self.destination = None     #holds the destination point, i.e. last goto sent
        self.heading = None
        self.sitl = None
        self.connecting = False
        self.path = deque()         #waypoints for the copter to follow
        self.following = False      #bool to check if copter is following a path, i.e. if _followPath is running
        self.followMe = None
        self.patrolList = []        #list of locations to patrol

        # For ADSB message creation
        self.adsb_enable = False if node.find("adsb") is None else (node.find("adsb").text=='1')        # bool: Set to True to enable ADSB for copter 
        self.adsb_lat = None
        self.adsb_long = None
        self.adsb_altitude = None
        self.adsb_heading = None
        self.adsb_hor_vel = None
        self.adsb_ver_vel = None
        
        self.samplesX = []               # list to store samples
        self.samplesY = []
        self.samplesZ = []
        
        self.x = None
        self.y = None
        self.z = None
        
        #uncomment this and sample section in onmessage to get logs
        #self.f = open(str(str(self.instance + 1) + 'posData.txt'),'w')

    def connect(self, connection_string):
        """
            Initializaes a vehicle in SITL or Real depending on
            whether the input connection string is None or a
            valid address

            Data Members:
            self.location       - current location of the quadcopter (x,y,z) in meters as a Point
            self.speed          - current velocity vectors of the quad (vx, vy, vz) in meters as a Point
            self.command        - ????
            self.command_lock   - a threading lock for the vehicle to prevent conflicts
            self.sitl           - a variable that binds SITL instance
            self.vehicle        - The dronekit vehicle, used to utilize the dronekit api
            self.commands       - The list of commands to give the copter

            Returns:
            False : If it fails to connect
            True : If the connection succeeds

        """
        #flag to show that the copter is trying to connect
        self.connecting = True
        
        # self.command = Point(None, None, None)
        self.location = Point(None, None, None)
        self.speed = Point(None, None, None)
        
        self.command_lock = threading.Lock()
        self.path_lock = threading.Lock()
        
        if not connection_string:
            self.sitl = self.start_sitl_instance(0.0,0.0, self.slot - 1)
            connection_string = "tcp:127.0.0.1:" + str((self.slot - 1) * 10 + 5760)
        
        vehicle = None       
        while vehicle is None:
            try:
                print("connecting to: " + connection_string)
                vehicle = dronekit.connect(connection_string, wait_ready=True, heartbeat_timeout = 15)

                vehicle.wait_ready('autopilot_version')
                
                '''
            # Bad TCP connection
            except socket.error:
                print '******************************'
                print 'No server exists!'
            
            # Bad TTY connection
            except exceptions.OSError as e:
                print '#############################'
                print 'No serial exists!'

            # API Error
            except dronekit.APIException as e:
                print '$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$'
                print 'Timeout! ' + e.message 
                '''         
                           
            # Other error
            except:
                print 'Failed to connect!'
                self.connecting = False
                return False
        
        # Listeners for mavlink messages
        vehicle.add_message_listener('GLOBAL_POSITION_INT',self.__onMessage_GLOBAL_POSITION_INT)
        
        if self.sitl != None:
            #Change sim voltage
            vehicle.parameters['SIM_BATT_VOLTAGE']=15.5

        # Variable to bind dronekit vehicle
        self.vehicle = vehicle

        self.commands = {
            'goto': self._goto,
            'arm_and_takeoff': self._arm_and_takeoff
            }
    
        self.connecting = False
        return True
    
    def setParams(self, parameterDict):
        """
            Sets the parameters of the vehicle using a dictionary of parameters
            Input:
                parameterDict - a dictionary of parameters of form: parameter:value
        """
        if self.sitl != None:
            return
        for key in parameterDict:
            if key not in self.vehicle.parameters:
                print "Parameter", key, "does not exist"
            elif self.vehicle.parameters[key] != parameterDict[key]:
                self.vehicle.parameters[key] = parameterDict[key]
                print "Set vehicle parameter: ", key, " with value: ", parameterDict[key]
            else:
                print "Parameter", key, "already set with value", parameterDict[key]

        # Add ADSB Param depending on Flag
        if self.adsb_enable:
            self.vehicle.ADSB_ENABLE = 1
        else:
            self.vehicle.ADSB_ENABLE = 0

        print "Finished setting parameters"

    ####################################################################################################

    #REQUIRES:   Latitude, longitude, instance number
    #MODIFIES:   N/A
    #EFFECTS:    Creates a SITL instance
    def start_sitl_instance(self,lat=None, lon=None, N = 0):
        """
            Starts an instance of SITL located at Lat, Lon with instance
            number N.
        """
        print("Starting copter simulator (SITL)") 
        sitl = dronekit_sitl.SITL() 
        sitl.download('copter', '3.3', verbose=True) 
        if ((lat is not None and lon is None) or 
            (lat is None and lon is not None)): 
            print("Supply both lat and lon, or neither") 
            exit(1) 
        sitl_args = ['-I0', '--model', 'quad', '--instance',str(N)] 
        if lat is not None: 
            sitl_args.append('--home=%f,%f,584,353' % (lat,lon,)) 
        sitl.launch(sitl_args, await_ready=True, restart=True) 
        return sitl 
        
    def __onMessage_GLOBAL_POSITION_INT(self, vself, event, msg):
        """
            Update Vehicle location based on mavlink's position messaging

            Message Documentation:
                https://pixhawk.ethz.ch/mavlink/#GLOBAL_POSITION_INT

            msg.lat = vehicle latitude (in degrees * 1e7)
            msg.lon = vehicle longitude (in degrees * 1e7)
            msg.alt = vehicle altitude (in meters * 1000, that is millimeters), 
                        relative to sea level
            msg.relative_alt = vehicle altitude in (millimeters) above ground
            msg.vx = ground x speed (m/s * 100)
            msg.vy = ground y speed (m/s * 100)
            msg.vz = ground z speed (m/s * 100)
            msg.hdg = vehicle heading (in degrees * 100) (centidegrees), if unknown, set UINT16_MAX
        """

        xDeg = msg.lon * 1.0e-7 
        yDeg = msg.lat * 1.0e-7
        z = msg.relative_alt / 1000.0

        x = lon_to_meters(xDeg)
        y = lat_to_meters(yDeg)

        self.location = Point(x, y, z)
        self.heading = msg.hdg/100.0
        
        self.x = x
        self.y = y
        self.z = z

        # update ADSB messages
        self.adsb_lat = msg.lat
        self.adsb_long = msg.lon
        self.adsb_altitude = msg.relative_alt
        self.adsb_heading = msg.hdg
        self.adsb_hor_vel = sqrt(msg.vx**2 + msg.vy**2)
        self.adsb_ver_vel = msg.vz
        
        
        '''
        #sample calculation
        if len(self.samplesX) < 10:
            self.samplesX.append(x)
            self.samplesY.append(y)
            self.samplesZ.append(z)
        else:
            
        
            avgX = sum(self.samplesX)/len(self.samplesX)
            avgY = sum(self.samplesY)/len(self.samplesY)
            avgZ = sum(self.samplesZ)/len(self.samplesZ)
            self.f.write(str('AvgX:'+str(avgX)+' AvgY: '+str(avgY)+' AvgZ: '+str(avgZ) + '\n'))

            
            
            
            num_items = len(self.samplesX)
            mean = sum(self.samplesX)/num_items
            differences = [x - mean for x in self.samplesX]
            sq_differences = [d ** 2 for d in differences]
            ssd = sum(sq_differences)
            variance = ssd/num_items
            sd = sqrt(variance)
            stdX = sd
            
            num_items = len(self.samplesY)
            mean = sum(self.samplesY)/num_items
            differences = [x - mean for x in self.samplesY]
            sq_differences = [d ** 2 for d in differences]
            ssd = sum(sq_differences)
            variance = ssd/num_items
            sd = sqrt(variance)
            stdY = sd
            
            num_items = len(self.samplesZ)
            mean = sum(self.samplesZ)/num_items
            differences = [x - mean for x in self.samplesZ]
            sq_differences = [d ** 2 for d in differences]
            ssd = sum(sq_differences)
            variance = ssd/num_items
            sd = sqrt(variance)
            stdZ = sd
            
            self.f.write(str('stdX:'+str(stdX)+' stdY: '+str(stdY)+' stdZ: '+str(stdZ) + '\n'))

            
            self.samplesX.pop(0)
            self.samplesY.pop(0)
            self.samplesZ.pop(0)
            
            '''
            
        
            
            
    def standard_deviation(lst, population = True):
        print 'starting'
        num_items = len(lst)
        print num_items
        mean = sum(lst)/num_items
        print mean
        differences = [x - mean for x in lst]
        print differences
        sq_differences = [d ** 2 for d in differences]
        print sq_differences
        ssd = sum(sq_differences)
        
        if population is True:
            variance = ssd/num_items
        else:
            variance = ssd/(num_items-1)
        sd = sqrt(variance)
        return sd
    
    #REQUIRES:  N/A
    #MODIFIES:  self.followMe
    #EFFECTS:   should return control to goto, i.e. clears all constantly threaded commands (follow, queue, etc.)
    def returnControl(self):
        with self.path_lock:
            self.followMe = None
            self.offset = None
            
            self.destination = None
            
            self.patrolList = []
    
    def arm_and_takeoff(self, alt=2):
        """ Spawns thread to command quad to arm and takeoff"""
        
        t = threading.Thread(target=self._arm_and_takeoff,args=(alt,)) #yes, the comma is important
        t.start()
        
    def _arm_and_takeoff(self, alt):
        """
            Commands the quad to takeoff to alt meters
            
            alt - meters above ground to rise
        """
        self.returnControl()
        
        with self.command_lock:
            timeout = 10  #keeps track of timeouts
            print "Basic pre-arm checks"
            # Don't try to arm until autopilot is ready
            while not self.vehicle.is_armable:
                print " Waiting for vehicle to initialize..."
                if timeout <= 0:
                    print 'Timeout: initialize'
                    return
                timeout -= 1
                time.sleep(1)

            # Arm in GUIDED mode
            self.vehicle.mode = dronekit.VehicleMode("GUIDED")
            self.vehicle.armed = True

            # Confirm vehicle armed before attempting to take off
            timeout = 10
            while not self.vehicle.armed:    
                print "Waiting for motors to arm..."
                if timeout <= 0:
                    print 'Timeout: arm motors'
                    return
                timeout -= 1
                time.sleep(1)

            print "motors armed, sleeping for 5 sec..."
            time.sleep(5)

            #ready to take off
            origX = self.location.x
            origY = self.location.y
            origH = self.heading
            print "Taking off!"
            print "Going to alt: ",alt," meters"
            self.vehicle.simple_takeoff(alt) # Take off to target altitude

            timeout = 10
            while True:
                print " Altitude: ", self.vehicle.location.global_relative_frame.alt
                #Break and return from function just below target altitude.
                if self.vehicle.location.global_relative_frame.alt>=alt*0.95:
                    print "Reached target altitude"
                    break
                if timeout <= 0:
                    print 'Timeout: target altitude not reached'
                    return
                timeout -= 1
                time.sleep(1)

            # In documentation, there is a limitation: condition_yaw message
            # will be ignored until first goto command is given

            # So, Give first goto command to stay in current position and
            # ascend to alt so that heading can be changed on takeoff

            self.goto(origX, origY, alt)
            

            print "Copter Ready for Instructions"
    
    #REQUIRES:  target, a copter object to follow
    #MODIFIES:  self.followMe, self.offset
    #EFFECTS:   spawns a thread that follows the target
    def follow(self, target):
        self.returnControl()
        with self.path_lock:
            self.followMe = target
            self.offset = (self.x - target.x, self.y - target.y, self.z - target.z)
        print "Offset:", self.offset
        t = threading.Thread(target=self._follow,args=()) #yes, the comma is important
        t.start()
        print 'started follow thread'
        
    #REQUIRES:  N/A
    #MODIFIES:  N/A
    #EFFECTS:   follows self.target at distance self.offset
    def _follow(self):
    
        buffer = .1    #acceptable error for following
        targetX = self.followMe.x
        targetY = self.followMe.y
        targetZ = self.followMe.z
        while self.followMe != None:
            if targetX != self.followMe.x or targetY != self.followMe.y or targetZ != self.followMe.z:
                with self.path_lock:
                    #print 'self x:',self.x
                    #print 'target x:', self.followMe.x
                    #print 'difference:',abs(self.x - self.followMe.x + self.offset[0])
                    if abs(self.x - self.followMe.x + self.offset[0]) > buffer or \
                    abs(self.y - self.followMe.y + self.offset[1]) > buffer or \
                    abs(self.z - self.followMe.z + self.offset[2]) > buffer:
                        # Convert to mavlink compatible units (degrees/meters)
                        lat = meters_to_lat(self.followMe.x + self.offset[0])
                        lon = meters_to_lon(self.followMe.y + self.offset[1])
                        alt = self.followMe.z + self.offset[2]
                        
                        #altitude safety check
                        if alt > 6:
                            print 'Unsafe altitude. Stopping follow'
                            self.followMe = None
                            return

                        # Get point that corresponds to goal
                        p = dronekit.LocationGlobalRelative(lon, lat, alt)

                        # Command Vehicle to Move
                        self.vehicle.simple_goto(p, groundspeed=5)
                        #print 'sending goto', self.followMe.x + self.offset[0], self.followMe.y + self.offset[1], self.followMe.z + self.offset[2]


                    targetX = self.followMe.x
                    targetY = self.followMe.y
                    targetZ = self.followMe.z
            
            time.sleep(.1)
            
        print 'ending follow'
    
    #REQUIRES:  list of positions in duples e.g. (x,y)
    #MODIFIES:  self.patrolList
    #EFFECTS:   sequentially patrols locations specified in positions
    def patrol(self, positions, v = 1):
        if len(positions) < 1:
            print 'Invalid patrol path.'
            return
            
        self.returnControl()
        
        with self.path_lock:
            self.patrolList = positions
            
        #start thread to follow patrol path
        t = threading.Thread(target=self._patrol,args=(v,)) #yes, the comma is important
        t.start()
        print 'started patrol thread'
        
    def _patrol(self, v):
        buffer = .2     #acceptable error for patrolling
        idx = 0         #index of current patrol location
        
        #send first patrol location
        targetX = self.patrolList[idx][0]
        targetY = self.patrolList[idx][1]
        targetZ = self.z
        
        #send first goto
        lat = meters_to_lat(targetX)
        lon = meters_to_lon(targetY)
        alt = targetZ
        #altitude safety check
        if alt > 6:
            print 'Unsafe altitude. Stopping patrol'
            self.patrolList = []
            return
        # Get point that corresponds to goal
        p = dronekit.LocationGlobalRelative(lon, lat, alt)
        # Command Vehicle to Move
        self.vehicle.simple_goto(p, groundspeed=v)
        
        while len(self.patrolList) > 0:
            with self.path_lock:
                #checks if the current patrol location has been reached
                if abs(self.x - targetX) <= buffer and \
                abs(self.y - targetY) <= buffer and \
                abs(self.z - targetZ) <= buffer:
                    idx = (idx + 1) % len(self.patrolList)
                    targetX = self.patrolList[idx][0]
                    targetY = self.patrolList[idx][1]
                
                    # Convert to mavlink compatible units (degrees/meters)
                    lat = meters_to_lat(targetX)
                    lon = meters_to_lon(targetY)
                    alt = targetZ
                    
                    #altitude safety check
                    if alt > 6:
                        print 'Unsafe altitude. Stopping patrol'
                        self.patrolList = []
                        return

                    # Get point that corresponds to goal
                    p = dronekit.LocationGlobalRelative(lon, lat, alt)

                    # Command Vehicle to Move
                    self.vehicle.simple_goto(p, groundspeed=v)
                    #print 'sending goto', self.followMe.x + self.offset[0], self.followMe.y + self.offset[1], self.followMe.z + self.offset[2]
            
            time.sleep(.1)
            
        print 'ending patrol'
        
    
    #REQUIRES:  list of waypoints
    #MODIFIES:  self.path
    #EFFECTS:   Sets the current waypoint path to 'waypoints'
    #           Starts a thread of _followPath if necessary
    def setPath(self, waypoints):
        #check if waypoints is empty
        if not waypoints:
            print 'Waypoints list is empty'
            return
            
        #clear existing waypoints
        with self.path_lock:
            #clear path deque
            self.path.clear()
            
        for w in waypoints:
            self.path.append(w)
            
        #spawn an instance of _followPath if it is not already running
        if self.following == False:
            t = threading.Thread(target=self._followPath,args=())
            t.start()
    
    #REQUIRES:  list of waypoints
    #MODIFIES:  self.path
    #EFFECTS:   Adds the waypoints in 'waypoints' to the end of self.path
    def addPath(self, waypoints):
        #check if waypoints is empty
        if not waypoints:
            print 'Waypoints list is empty'
            return
            
        #go through and add each waypoint in 'waypoints' to self.path
        for w in waypoints:
            self.path.append(w)
    
        #spawn an instance of _followPath if it is not already running
        if self.following == False:
            t = threading.Thread(target=self._followPath,args=())
            t.start()

    def _followPath(self):
        
        self.following = True
        next = self.path.popLeft()  #next waypoint to goto
        self.gotoWaypoint(next)
        timeout = 5                 #timeout between waypoints
        while True and timeout > 0:
            with self.path_lock:
                if self.path.empty():   #checks if another command has cleared the queue
                            self.following = False
                            return      #should return from here if following interrupted
                if self.closeTo(next):  #copter has "reached" waypoint
                    next = self.path.popLeft()
                    self.gotoWaypoint(next)
                    if self.path.empty():
                            self.following = False
                            return      #should return from here if following is completed
            
            
            timeout -= 1
            time.sleep(1)
        
        
        #self.following = False
    
    def closeTo(self, waypoint):
        return True
    
    def gotoWaypoint (self, waypoint, v = None):
        self.goto(waypoint.x, waypoint.y, waypoint.z, v)
        self.rotate(waypoint.heading)
        
    def goto(self, x=0.0, y=0.0, z=2.0, v=None):
        """
            Spawns a thread that makes the copter go to position (x,y,z) with flight
            velocity v.

            Inputs: x - number of meters to move along x axis in global field
                        (+ = right)
                    y - number of meters to move along y axis in global field
                        (+ = forwards)
                    z - number of meters to move along z axis in global field
                        (+ = up)
                    v - velocity in m/s to move at

        """
        t = threading.Thread(target=self._goto,args=(x,y,z,v))
        t.start()
        
    def _goto(self, x, y, z, v):
        """
            Commands the copter go to position (x,y,z) with flight
            velocity v.

            Inputs: x - number of meters to move along x axis in global coordinate system
                        (+ = right)
                    y - number of meters to move along y axis in global coordinate system
                        (+ = forwards)
                    z - number of meters to move along z axis in global coordinate system
                        (+ = up)
                    v - velocity in m/s to move at

        """
        self.returnControl()
        
        self.destination = Point(x,y,z)
            
        with self.command_lock:
            # Convert to mavlink compatible units (degrees/meters)
            lat = meters_to_lat(x)
            lon = meters_to_lon(y)
            alt = z

            # Get point that corresponds to goal
            p = dronekit.LocationGlobalRelative(lon, lat, alt)

            # Command Vehicle to Move
            self.vehicle.simple_goto(p, groundspeed=v)
            
    def reachedGoto(self, buffer = .2):
        #buffer = .25
        if self.destination == None:
            return True
        if abs(self.x - self.destination.x) > buffer or \
        abs(self.y - self.destination.y) > buffer or \
        abs(self.z - self.destination.z) > buffer:
            return False
        
        
        return True

    def condition_yaw(self, heading, clockwise=True, relative=False):
        """
            Commands the copter to adjust its yaw

            Inputs:
                heading -   the direction the quad to face in degrees
                clockwise - True if we rotate clockwise, False otherwise
                relative -  False if heading is in global coordinate system
                            True if heading is relative to current quad direction
        """
        #self.returnControl()
        
        if relative:
            is_relative = 1 #yaw relative to direction of travel
        else:
            is_relative = 0 #yaw is an absolute angle
        if clockwise:
            direction = 1
        else:
            direction = -1
        # create the CONDITION_YAW command using command_long_encode()
        msg = self.vehicle.message_factory.command_long_encode(
            0, 0,    # target system, target component
            pymavlink.mavutil.mavlink.MAV_CMD_CONDITION_YAW, #command
            0, #confirmation
            heading,    # param 1, yaw in degrees
            0,          # param 2, yaw speed deg/s
            direction,          # param 3, direction -1 ccw, 1 cw
            is_relative, # param 4, relative offset 1, absolute angle 0
            0, 0, 0)    # param 5 ~ 7 not used
        # send command to vehicle
        self.vehicle.send_mavlink(msg)

    def send_ned_velocity(self, velocity_x, velocity_y, velocity_z, duration=1):
        """
        Move vehicle in direction based on specified velocity vectors.
        """
        msg = self.vehicle.message_factory.set_position_target_local_ned_encode(
            0,       # time_boot_ms (not used)
            0, 0,    # target system, target component
            pymavlink.mavutil.mavlink.MAV_FRAME_LOCAL_NED, # frame
            0b0000111111000111, # type_mask (only speeds enabled)
            0, 0, 0, # x, y, z positions (not used)
            velocity_x, velocity_y, velocity_z, # x, y, z velocity in m/s
            0, 0, 0, # x, y, z acceleration (not supported yet, ignored in GCS_Mavlink)
            0, 0)    # yaw, yaw_rate (not supported yet, ignored in GCS_Mavlink)


        # send command to vehicle on 1 Hz cycle
        for x in range(0,duration):
            self.vehicle.send_mavlink(msg)
            time.sleep(1)
 
    def emergency_kill(self):
        """
            Sends a signal to the copter to immediately turn off
            WARNING: Will cause the copter to fall out of the sky!!!
        """
        self.returnControl()
        
        msg = self.vehicle.message_factory.command_long_encode(
            0, 0,    # target system, target component
            pymavlink.mavutil.mavlink.MAV_CMD_DO_FLIGHTTERMINATION, #command
            0, #confirmation,
            1, #terminate if param 1 >0.5
            0, 0, 0, 0, 0, 0)    # param 2 ~ 7 not used
        # send command to vehicle
        self.vehicle.send_mavlink(msg)
        print "EMERGENCY STOP!!!"
        
    def flip(self):
        """
            Sets the copter to flip mode
        """
        self.returnControl()
        msg = self.vehicle.message_factory.command_long_encode(
            0, 0,    # target system, target component
            pymavlink.mavutil.mavlink.MAV_CMD_DO_SET_MODE, #command
            0, #confirmation,
            1, #mode, this is ignored by the APM. set to 1 for MAV_MODE_FLAG_CUSTOM_MODE_ENABLED
            14, #custom mode, 14 is flip
            0, 0, 0, 0, 0)    # param 3 ~ 7 not used
        # send command to vehicle
        self.vehicle.send_mavlink(msg)
        print "Flipping!"

    def setLights(self, val):   #1000 for solid (no possession) or 2000 for blinking (possession)
        msg = self.vehicle.message_factory.command_long_encode(
            0, 0,    # target system, target component
            pymavlink.mavutil.mavlink.MAV_CMD_DO_SET_SERVO, #command
            0, #confirmation,
            9, #serial number
            val, #PWM
            0, 0, 0, 0, 0)    # param 3 ~ 7 not used
        # send command to vehicle
        self.vehicle.send_mavlink(msg)
        print 'setting lights to ',val
    
        
    def close(self):
        """
            Turns off connection to vehicle
        """
        self.returnControl()
        if self.vehicle is not None:
            self.vehicle.close()
        if self.sitl is not None:
            self.sitl.stop()
            
    def close_sitl(self):
        """
            Stops SITL instance
        """
        if self.sitl is not None:
            self.sitl.stop()
 
    def __del__(self):
        """
            Stops SITL instance
        """
        if self.sitl is not None:
            self.sitl.stop()


#######################################################################

# Copter Control Interface

    def printGoal(self, x, y, z):
        """Prints the goal location of the copter
            Inputs:
                x - x location of goal
                y - y location of goal
                z - z location of goal
        """    
        print "Goal Status"
        print "-----------"
        print "x(m) = ", x
        print "y(m) = ", y
        print "z(m) = ", z
        print "-----------"
        print "\n"
        #print "position increment(m) = ", self.positionIncrement

    def currentStatus(self):
        """
            Checks if a copter is selected and prints current copter status
        """
        print "Current Status"
        print "--------------"
        print "x(m): ", self.location.x
        print "y(m): ", self.location.y
        print "z(m): ", self.location.z
        print "heading: ", self.vehicle.heading
        #print "position increment(m) = ", self.positionIncrement
        print "battery: ", str(self.vehicle.battery)
        print "mode: ", str(self.vehicle.mode)
        print "\n"

    def enableADSB(self):
        """
            Enables ADSB on the Copter
        """
        self.adsb_enable = 1
        self.vehicle.ADSB_ENABLE = 1

    def disableADSB(self):
        """
            Disables ADSB on the copter
        """
        self.adsb_enable = 0
        self.vehicle.ADSB_ENABLE = 0


    def holdPosition(self):
        t = threading.Thread(target=self._holdPosition,args=())
        t.start()
    
    def _holdPosition(self):
        """
            Stops the Copter at its current position
        """    
        #x=self.location.x
        #y=self.location.y
        #zMeters=self.location.z #special for altitude

        # Stop Waypointing
        self.returnControl()

        print "manual control: stop"

        # set x,y,z, velocity to 0, with message frequency of 1
        self.send_ned_velocity(0,0,0, 1)


        # #Tell vehicle to go to same place
        #currentHeading = self.vehicle.heading
        #self.goto(x,y,zMeters)
        #self.condition_yaw(currentHeading)

        # # Sending Global ADSB Stop
        # msg = self.vehicle.message_factory.set_position_target_global_int_encode(
        #     0,       # time_boot_ms (not used)
        #     0, 0,    # target system, target component
        #     pymavlink.mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT_INT, # frame
        #     0b0000111111000111, # type_mask (only speeds enabled)
        #     0, # lat_int - X Position in WGS84 frame in 1e7 * meters
        #     0, # lon_int - Y Position in WGS84 frame in 1e7 * meters
        #     0, # alt - Altitude in meters in AMSL altitude(not WGS84 if absolute or relative)
        #     # altitude above terrain if GLOBAL_TERRAIN_ALT_INT
        #     0, # X velocity in NED frame in m/s
        #     0, # Y velocity in NED frame in m/s
        #     0, # Z velocity in NED frame in m/s
        #     0, 0, 0, # afx, afy, afz acceleration (not supported yet, ignored in GCS_Mavlink)
        #     0, 0)    # yaw, yaw_rate (not supported yet, ignored in GCS_Mavlink)
            
        # self.vehicle.send_mavlink(msg)

        # # Mode Switching Stop
        # timeout = 1
        # self.vehicle.mode = dronekit.VehicleMode("LOITER")
        # while self.vehicle.mode != dronekit.VehicleMode("LOITER") and timeout > 0:
        #     timeout -= .1
        #     time.sleep(.1)
        # self.vehicle.mode = dronekit.VehicleMode("GUIDED")
        

    def move(self, xstep, ystep, zstep):
        """
            Moves the copter xstep, ystep, and ztep
            Inputs:
                xstep - distance to move in meters to the right
                ystep - distance to move in meters to the forward
                zstep - distance to move in meters up
            Note: Negative values will cause the copter to move left, back and down respectively
        """
        self.returnControl()
        
        self.currentStatus()

        x = self.location.x + xstep
        y = self.location.y + ystep
        z = self.location.z + zstep #special for altitude

        print "moving copter by x:%f y:%f z:%f (meters)" % (xstep, ystep, zstep)
        self.goto(x, y, z)
        self.printGoal(x, y, z)


    def rotate(self, goal):
        """
            Rotates the Copter to heading

            Input: goal - the goal heading in degress
        """
        self.currentStatus()
  
        currentHeading = self.vehicle.heading

        # Calculate whether it is more efficient to rotate clockwise or counterclockwise
        rotateClockwise = False;
        if currentHeading < 180:
            if currentHeading <= goal <= (currentHeading+180):
                rotateClockwise = True
        else:
            if not ((currentHeading-180) <= goal <= currentHeading):
                rotateClockwise = True

        self.condition_yaw(goal, rotateClockwise, relative=False)
  
    def rotateRight(self, deg):
        """
            Rotates the copter deg to the right

            Inputs: 
                deg - degrees to rotate right

            Note: if deg is negative, copter rotates left
            North is 0 degrees. Degrees increase as we rotate right
        """
        self.currentStatus()    

        currentHeading = self.vehicle.heading

        if deg > 0:
            print "manual control: rotate right"
            #do clockwise rotation
            self.condition_yaw((currentHeading + deg) % 360, True) 
        else:
            print "manual control: rotate left"
            #do counterclockwise rotation
            self.condition_yaw((currentHeading + deg) % 360, False)

        print "goal heading: ", (currentHeading + deg) % 360
        
    def rotateLeft(self, deg):
        """
            Rotates the Copter deg to the left, uses rotateRight()

            Inputs:
                deg - degrees to rotate left

            Note: if deg is negative, copter rotates right 
        """
        self.rotateRight(-1*deg)
        

#######################################################################
