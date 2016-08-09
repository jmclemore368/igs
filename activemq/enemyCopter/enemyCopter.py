from PySide.QtGui import *
from PySide.QtCore import *

from math import *

class Point:
    def __init__(self,x,y,z):
        self.x = x
        self.y = y
        self.z = z 

class EnemyCopter():
    def __init__(self, name, id, x, y, z, heading, vx, vy, vz, yaw, pitch, roll):
        self.name = name
        self.id = 11 + id #Offset the Enemy Copter ID by 11 to avoid conflicts with our copter's id
        self.x = x
        self.y = y
        self.z = z
        self.location = Point(x, y, z)
        self.heading = degrees(float(heading))
        self.vx = vx
        self.vy = vy
        self.vz = vz
        self.yaw = yaw
        self.pitch = pitch
        self.roll = roll
        self.color = QColor(255, 0, 0)
        self.marker = None

        # For ADSB message creation
        self.adsb_lat = None
        self.adsb_lon = None
        self.adsb_altitude = None
        self.adsb_heading = None
        self.adsb_hor_vel = None
        self.adsb_ver_vel = None

    def __repr__(self):
        return "name = " + str(self.name) \
         + "\nid = " + str(self.id) \
         + "\nheading = " + str(self.heading) \
         + "\nx = " + str(self.x) \
         + "\ny = " + str(self.y) \
         + "\nz = "+ str(self.z) \
         + "\nvx = "+ str(self.vx) \
         + "\nvy = "+ str(self.vy) \
         + "\nvz = "+ str(self.vz) \
         + "\nYaw = "+ str(self.yaw) \
         + "\nPitch = "+ str(self.pitch) \
         + "\nRoll = "+ str(self.roll) \
         + "\n"

    def update(self, x, y, z, heading, vx, vy, vz, yaw, pitch, roll):
        self.x = x
        self.y = y
        self.z = z
        self.location = Point(x, y, z)
        self.heading = degrees(float(heading))
        self.vx = vx
        self.vy = vy
        self.vz = vz
        self.yaw = yaw
        self.pitch = pitch
        self.roll = roll

        # Set ADSB parameters
        self.adsb_lat = self.meters_to_lat(x) * 1e7             # assuming self.x is in meters, convert to lat*1e7
        self.adsb_lon = self.meters_to_lon(y) * 1e7            # assuming self.x is in meters, convert to long*1e7
        self.adsb_altitude = self.z * 1000                      # convert from meters to millimeters
        self.adsb_heading = self.heading * 100         # convert from radians to degrees to centidegrees
        self.adsb_vx = self.vx * 100                            # convert from m/s to cm/s
        self.adsb_vy = self.vy * 100                            # convert from m/s to cm/s
        self.adsb_hor_vel = sqrt(self.vx**2 + self.vy**2) * 100 # convert from m/s to cm/s
        self.adsb_ver_vel = self.vz * 100                       # convert from m/s to cm/s
        
    def meters_to_lat(self, meter):
        """
            Converts meters to latitude

            At 0 deg lat, 1 m approx 9.04371732957e-6 deg
            (source: https://en.wikipedia.org/wiki/Latitude#Length_of_a_degree_of_latitude)
        """
        return meter * 9.04371732957e-6 #1/110574.0

    def meters_to_lon(self, meter):
        """
            Converts meters to longitude

            At 0 deg long, 1 m approx 9.04371732957e-6
            (source: https://en.wikipedia.org/wiki/Latitude#Length_of_a_degree_of_latitude)
        """
        return meter * 8.983111749911e-6 #1/111320.0



