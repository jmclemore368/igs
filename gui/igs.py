import dronekit
import dronekit_sitl
import pymavlink
import socket 
import exceptions 
import argparse  
import time
import threading
from collections import deque
from math import floor, log10
# don't ask

######
import sys
from PySide.QtGui import *
from PySide.QtCore import *
####

from qt.igs_gui import Ui_MainWindow

#imports waypoint class
import os
import inspect
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
os.sys.path.insert(0,parentdir)
from controller.waypoints.waypoints import WayPoints
from platoon.platoon import Platoon



		   
class MainWindow(QMainWindow, Ui_MainWindow):
	def __init__(self, width=35.0, length=35.0):
		# Assign variables
		self.click = (None, None)       # location of last click
		self.patrolClicks = []           # list of patrol clicks currently selected
		self.selected_copter = 10       # number of the selected copter
		self.arena_width = width        # width of arena
		self.arena_length = length      # length of arena
		self.arena_height = 8           # height of arena
		self.draw_time = 0.0            # stores the last time the field was drawn
		self.draw_delay = .1            # time delay between draws, in seconds
		self.takeoff_alt = 2            # takeoff to 2 meters
		self.vehicleDict = {}           # Dictionary of friendly vehicles
		self.unconnectedDict = {}       # Dictionary of unconnected vehicles
		self.enemyDict = {}             # Dictionary of enemy vehicles
		self.platoon = Platoon()        # Platoon of friendly vehicles

		self.waypointDict = {}          # Dictionary of Waypoints
		self.dropPtDict = {}            # Dictionary of Drop Points
		self.blockPtDict = {}           # Dictionary of Block Points
		self.flipPtDict = {}            # Dictionary of Flip Points
		self.etcPtDict = {}             # Dictionary of Other Points
		self.currentPtDict = None       # Currently selected dictionary
		self.killArmed = False          # Keep track of if kill button is armed
		self.disconnectArmed = False    # Keep track of if disconnect button is armed
		self.hasBall = None             # String of object (dispenser or copter) that has the quaffle
		self.selected_waypoint = None   # String of selected waypoint, i.e. key to selected waypoint in waypointDict
		self.useWaypoint = False        # Determines whether to use waypoint or click position
		self.copterParams = {}          # Dictionary of Copter Params to be set on copter instantiation
		self.copterPaths = {}           # Dictionary of Queues representing Copter waypoint queues
		self.settingFollow = False      # Bool for whether follow is being set
		self.settingPlatoon = False     # Bool for whether platoon is being set
		self.settingWall = False        # Bool for whether wall is being set
		self.settingPatrol = False      # Bool for whether patrol is being set
		

		self.voltageYellow = 3.6 * 4    # Threshold voltage for battery bars to turn yellow
		self.voltageRed = 3.4 * 4       # Threshold voltage for battery bars to turn red
		
		self.scaleObjects = False       # Bool to toggle scaling of vehicles to field size
		self.visualScalar = 1           # Used to scale the size of the objects on the field
		self.click_diameter = 10        # Diameter of click circle

		self.ADSB = True                # Bool to toggle ADSB messages

		self.platoon = Platoon()        # Platoon to hold copters

		# Invoke master
		super(MainWindow, self).__init__()
		self.setupUi(self)
		self.assignWidgets()

		# GUI INSTRUCTIONS
		self.Instructions.setText(
"""Bindings for Keyboard Controls

1~6:    select copter
7:      select platoon
c:      connect
a:      arm and takeoff
F5:     land
+:      disconnect
s:      stop
g:      goto clicked point
shift+g: fast goto
j:      left
l:      right
i:      forward
k:      back
u:      rotate left
o:      rotate right
y:      increase altitude
h:      decrease altitude
m:      increase increment
n:      decrease increment
p:      print status
[:      disable ADSB
]:      enable ADSB
Backspace:      flip
\:      lob
~:      Emergency Kill
Alt-F4: Close Ground Station
Shift+i/j/k/l: Lock Heading N,W,S,E
F9:     Follow Mode Engaged
In Follow Mode:
1~6:    Follow Friendly Copter
F1~F6:  Follow Enemy Copter
""")

		# Color Dictionary
		self.color = {}
		self.color["red"] = QColor(255, 0, 0)
		self.color["blue"] = QColor(0, 0, 255)
		self.color["teal"] = QColor(0, 200, 200)
		self.color["purple"] = QColor(128, 0, 255)
		self.color["orange"] = QColor(255, 128, 0)
		self.color["brown"] = QColor(128, 64, 0)
		self.color["white"] = QColor(255, 255, 255)
		self.color["yellow"] = QColor(255, 255, 0)
		self.color["green"] = QColor(0, 255, 0)
		self.color["gray"] = QColor(127, 127, 127)
		self.color["light-gray"] = QColor(200, 200, 200)
		self.color["dark-gray"] = QColor(60, 60, 60)
		self.color["black"] = QColor(0, 0, 0)

		### STYLE SHEETS ###
		self.copterLabelStyle = """QPushButton { color: rgb(255,255,255); background-color: rgb(0,0,255); font-size: 30pt; font-family: Verdana; font-weight: bold; font-style: italic;}"""
		self.platoonLeaderStyle = """QPushButton { color: rgb(255,0,0); background-color: rgb(0,255,0); font-size: 30pt; font-family: Verdana; font-weight: bold; font-style: italic;}"""
		self.selectedCopterStyle = """QPushButton { background-color: rgb(0,255,0); font-size: 30pt; font-family: Verdana; font-weight: bold; font-style: italic;}"""
		self.notInitializedCopterStyle = """QPushButton { background-color: rgb(64,64,64); font-size: 30pt; font-family: Verdana; font-weight: bold; font-style: italic;}"""
		self.notInitializedSelectedCopterStyle = """QPushButton { background-color: rgb(64,150,64); font-size: 30pt; font-family: Verdana; font-weight: bold; font-style: italic;}"""
		self.noHeartBeatCopterStyle = """QPushButton { background-color: rgb(255,0,0); font-size: 30pt; font-family: Verdana; font-weight: bold; font-style: italic;}"""
		self.connectingCopterStyle = """QPushButton { background-color: rgb(210,80,225); font-size: 30pt; font-family: Verdana; font-weight: bold; font-style: italic;}"""
		self.noCopterStyle = """QPushButton { color: rgb(0,0,0); background-color: rgb(0,0,0);}"""
		self.killArmedStyle = """QPushButton { background-color: rgb(255,0,0)}"""
		self.warningStyle = """QLabel { color: rgb(255,0,0)}"""
		self.batteryYellowStyle = """QProgressBar::chunk { background-color: yellow; }"""
		self.batteryRedStyle = """QProgressBar::chunk { background-color: red; }"""
		###

		### FONT ###
		self.copterNumFont = QFont();
		self.copterNumFont.setPointSize(22);
		self.copterNumFont.setWeight(80);
		self.copterNumFont.setFamily("Calibri");

		self.copterSideFont = QFont();
		self.copterSideFont.setPointSize(14);
		self.copterSideFont.setWeight(70);
		self.copterSideFont.setFamily("Calibri");
		###

		for copterIndex in range(1,7):
			if copterIndex in self.unconnectedDict:
				eval("self.copterColor%d"%copterIndex).setStyleSheet(self.notInitializedCopterStyle)
			else:
				eval("self.copterColor%d"%copterIndex).setStyleSheet(self.noCopterStyle)
				eval("self.groupCopter_%d" %copterIndex).setEnabled(False)

		# Enable mouse tracking and install event filter
		self.viewArenaXY.setMouseTracking(True)
		self.viewArenaXY.installEventFilter(self)
		self.viewArenaXZ.installEventFilter(self)
		self.viewArenaXY.setScene(QGraphicsScene())
		self.viewArenaXZ.setScene(QGraphicsScene())
		self.positionIncrement  = .5
		self.headingIncrement   = 1.0
		self.headingLock = None
		
		#update label
		self.labelIncrementSpeedVALUE.setText(str(self.positionIncrement))

		# Stored coordinates initialization
		self.xc = None #self.get_x_from_w(0)  # Stored coordinates from mouse event (pixels)
		self.yc = self.get_h_from_y(0)
		self.zc = self.get_h_from_z(self.takeoff_alt)


		# Initialize copter and click marker ellipses
		# TODO: Put code here

		# Very last step: Show the window
		self.show()

	def paintEvent(self, event):
		# SHOULD CONTAIN ONLY POSITION OR STATUS (COLOR) UPDATES

		if time.clock() - self.draw_time < self.draw_delay:
			return

		self.viewArenaXY.scene().clear()
		self.viewArenaXZ.scene().clear()
		self.drawFieldXY()
		self.drawFieldXZ()

		sceneXY = self.viewArenaXY.scene()
		sceneXZ = self.viewArenaXZ.scene()

		# get view width and height
		w = self.viewArenaXY.width() #Scroll bars have been disabled so offsets are unnecessary now
		l = self.viewArenaXY.height()
		z = self.viewArenaXZ.height()
		
### DRAWS FOR XY PLANE ###
		# draw vehicles - dimensions from QI Simulator guide
		if self.scaleObjects == True:
			self.copter_diameterX = self.visualScalar * (w / self.arena_width) * 0.785876  # 30.94" proper scale
			self.copter_diameterY = self.visualScalar * (l / self.arena_length) * 0.785876  # 30.94" proper scale
			self.copter_diameterZ = self.visualScalar * (z / self.arena_height) * 0.2032  # 8" proper scale
		else:
			self.copter_diameterX = 30
			self.copter_diameterY = 30
			self.copter_diameterZ = 20

		#draw enemy vehicles
		# print "Enemy: ", str(self.enemyDict)
		for key in self.enemyDict.keys():
			v = self.enemyDict[key]
			if v.x != None and v.y != None:
				x = self.get_w_from_x(v.x)
				y = self.get_h_from_y(v.y)
				x = x - (self.copter_diameterX/2)
				y = y - (self.copter_diameterY/2)
				sceneXY.addEllipse(x, y, self.copter_diameterX, self.copter_diameterY, QPen(v.color), QBrush(v.color))
				#paint possession
				if self.hasBall == v.name:
					p = QPen(self.color['orange'])
					p.setWidth(5)
					sceneXY.addEllipse(x, y, self.copter_diameterX + 5, self.copter_diameterY + 5, p, QBrush(QColor(0,0,0,0)))
				#paint heading
				self.paintHeading(key, v)
				#add number text
				text = sceneXY.addSimpleText(str(v.id - 10), self.copterNumFont)
				text.setPos(x + 9,y - 5)    #manual offsets depending on font
				text.setBrush(QBrush(self.color['white']))

		#draw friendly unselected vehicles
		for key in self.vehicleDict.keys():
			if (key in self.platoon.copterDict.keys() and self.selected_copter == 7):
				continue
			v = self.vehicleDict[key]
			if v.location.x != None and key != self.selected_copter:
				x = self.get_w_from_x(v.location.x)
				y = self.get_h_from_y(v.location.y)
				x = x - (self.copter_diameterX/2)
				y = y - (self.copter_diameterY/2)
				#print indicator for current goto
				if v.reachedGoto() == False:
					destX = self.get_w_from_x(v.destination.x) - self.click_diameter/2
					destY = self.get_h_from_y(v.destination.y) - self.click_diameter/2
					sceneXY.addEllipse(destX, destY, self.click_diameter, self.click_diameter, QPen(self.color['teal']), QBrush(self.color['teal']))
					p = QPen(self.color['teal'])
					p.setWidth(3)
					sceneXY.addLine(destX + (self.click_diameter/2), destY + (self.click_diameter/2), x + (self.copter_diameterX/2), y + (self.copter_diameterY/2), p)
				#draw circle for copter
				sceneXY.addEllipse(x, y, self.copter_diameterX, self.copter_diameterY, QPen(v.color), QBrush(v.color))
				#paint possession
				if self.hasBall == v.id:
					p = QPen(self.color['orange'])
					p.setWidth(5)
					sceneXY.addEllipse(x, y, self.copter_diameterX + 5, self.copter_diameterY + 5, p, QBrush(QColor(0,0,0,0)))
				#paint heading
				self.paintHeading(key)
				#add number text
				text = sceneXY.addSimpleText(str(key), self.copterNumFont)
				text.setPos(x + 9,y - 5)    #manual offsets depending on font
				text.setBrush(QBrush(self.color['white']))
				#update battery bar color
				self.batteryCheck(key)
				#draw patrol path
				lastc = None
				if len(v.patrolList) > 0:
					x = self.get_w_from_x(v.patrolList[-1][0])
					y = self.get_h_from_y(v.patrolList[-1][1])
					lastc = (x,y)
				for c in v.patrolList:
					x = self.get_w_from_x(c[0])
					y = self.get_h_from_y(c[1])
					p = QPen(self.color['teal'])
					p.setWidth(1)
					sceneXY.addEllipse(x - self.click_diameter/4, y - self.click_diameter/4, self.click_diameter/2, self.click_diameter/2, QPen(self.color['teal']), QBrush(self.color['teal']))
					sceneXY.addLine(x, y, lastc[0], lastc[1], p)
					lastc = (x,y)
				
				

		#draw selected copter in different color
		if self.selected_copter in self.vehicleDict.keys():
			v = self.vehicleDict[self.selected_copter]
			if v.location.x != None:
				x = self.get_w_from_x(v.location.x)
				y = self.get_h_from_y(v.location.y)
				x = x - (self.copter_diameterX/2)
				y = y - (self.copter_diameterY/2)
				#print indicator for current goto
				if v.reachedGoto() == False:
					destX = self.get_w_from_x(v.destination.x) - self.click_diameter/2
					destY = self.get_h_from_y(v.destination.y) - self.click_diameter/2
					sceneXY.addEllipse(destX, destY, self.click_diameter, self.click_diameter, QPen(self.color['teal']), QBrush(self.color['teal']))
					p = QPen(self.color['teal'])
					p.setWidth(3)
					sceneXY.addLine(destX + (self.click_diameter/2), destY + (self.click_diameter/2), x + (self.copter_diameterX/2), y + (self.copter_diameterY/2), p)
				#draw circle for copter
				sceneXY.addEllipse(x, y, self.copter_diameterX, self.copter_diameterY, QPen(self.color['green']), QBrush(self.color['green']))
				#paint possession
				if self.hasBall == v.id:
					p = QPen(self.color['orange'])
					p.setWidth(5)
					sceneXY.addEllipse(x, y, self.copter_diameterX + 5, self.copter_diameterY + 5, p, QBrush(QColor(0,0,0,0)))
				#paint heading
				self.paintHeading(self.selected_copter)
				#add number text
				text = sceneXY.addSimpleText(str(self.selected_copter), self.copterNumFont)
				text.setPos(x + 9,y - 5)    #manual offsets depending on font
				text.setBrush(QBrush(self.color['black']))
				#update battery bar color
				self.batteryCheck(self.selected_copter)
				#draw patrol path
				lastc = None
				if len(v.patrolList) > 0:
					x = self.get_w_from_x(v.patrolList[-1][0])
					y = self.get_h_from_y(v.patrolList[-1][1])
					lastc = (x,y)
				for c in v.patrolList:
					x = self.get_w_from_x(c[0])
					y = self.get_h_from_y(c[1])
					p = QPen(self.color['teal'])
					p.setWidth(1)
					sceneXY.addEllipse(x - self.click_diameter/4, y - self.click_diameter/4, self.click_diameter/2, self.click_diameter/2, QPen(self.color['teal']), QBrush(self.color['teal']))
					sceneXY.addLine(x, y, lastc[0], lastc[1], p)
					lastc = (x,y)

		#draw platoon
		self.paintPlatoonXY()
					
		#draw ball drops
		w = self.viewArenaXY.width()
		l = self.viewArenaXY.height()
		dropYloc_1 = 12.5 / 50.0 * l
		dropYloc_2 = 25 / 50.0 * l
		dropYloc_3 = 37.5 / 50.0 * l
		dropXloc = self.get_w_from_x(0)
		dropRadius = 15
		dropPen = QPen(QColor(255, 255, 255, 125))
		dropPen.setWidth(5)
		for dropYloc in [dropYloc_1, dropYloc_2, dropYloc_3]:
			self.centerObjectOnCoordinate(sceneXY.addEllipse(0, 0, dropRadius, dropRadius, dropPen, QBrush(QColor(0,0,0,0))),dropXloc, dropYloc)

		#draw currently selected patrol path
		lastc = None
		if len(self.patrolClicks) > 0:
			x = self.get_w_from_x(self.patrolClicks[-1][0])
			y = self.get_h_from_y(self.patrolClicks[-1][1])
			lastc = (x,y)
		for c in self.patrolClicks:
			x = self.get_w_from_x(c[0])
			y = self.get_h_from_y(c[1])
			p = QPen(self.color['yellow'])
			p.setWidth(3)
			sceneXY.addEllipse(x - self.click_diameter/2, y - self.click_diameter/2, self.click_diameter, self.click_diameter, QPen(self.color['yellow']), QBrush(self.color['yellow']))
			sceneXY.addLine(x, y, lastc[0], lastc[1], p)
			lastc = (x,y)
			
			
		#draw mouse click positions
		if(self.xc != None):
			w = self.viewArenaXY.width()
			l = self.viewArenaXY.height()
			h = self.viewArenaXZ.height()

			xc, yc = self.click #TODO: To deprecate
			#change positions to accurately draw circle
			xc = self.xc - (self.click_diameter/2)
			yc = self.yc - (self.click_diameter/2)
			zc = self.zc - (self.click_diameter/2)
			#prevent circles from going outside viewArenaXY
			# notes: removed the "x/y/z - 2"
			if(xc < 0):
				xc = 0
			if(xc + self.click_diameter > w):
				xc = w - self.click_diameter
			if(yc < 0):
				yc = 0
			if(yc + self.click_diameter > l):
				yc = l - self.click_diameter
			if (zc < 0):
				zc = 0
			if (zc + self.click_diameter > z):
				zc = h - self.click_diameter
			#point is ok, can paint
			if self.useWaypoint == False:
				#click
				sceneXY.addEllipse(xc, yc, self.click_diameter, self.click_diameter, QPen(self.color['yellow']), QBrush(self.color['yellow']))
			else:
				#waypoint
				sceneXY.addEllipse(xc, yc, self.click_diameter, self.click_diameter, QPen(self.color['purple']), QBrush(self.color['purple']))
### END XY PLANE ###

### DRAWS FOR XZ PLANE ###
		#draw altitude indicator
		altPen = QPen()
		if self.useWaypoint == False:
			altPen.setColor(self.color['yellow'])
		else:
			altPen.setColor(self.color['purple'])
		altPen.setWidth(3)
		if self.xc != None:
			if self.zc > self.viewArenaXZ.height() - (self.copter_diameterZ/2):
				sceneXZ.addLine(1, self.viewArenaXZ.height() - (self.copter_diameterZ/2), sceneXZ.width(), self.viewArenaXZ.height() - (self.copter_diameterZ/2), altPen)
			else:
				sceneXZ.addLine(1, self.zc, sceneXZ.width(), self.zc, altPen)

		#draw enemy vehicles
		# print "Enemy: ", str(self.enemyDict)
		for key in self.enemyDict.keys():
			v = self.enemyDict[key]
			if v.x != None and v.z != None:
				x = self.get_w_from_x(v.location.x)
				z = self.get_h_from_z(v.location.z)
				x = x - (self.copter_diameterX/2)
				z = z - (self.copter_diameterZ/2)
				if z > self.viewArenaXZ.height() - self.copter_diameterZ:
					z = self.viewArenaXZ.height() - self.copter_diameterZ
				sceneXZ.addRect(x, z, self.copter_diameterX, self.copter_diameterZ, QPen(v.color), QBrush(v.color))
				#add number text
				text = sceneXZ.addSimpleText(str(v.id - 10), self.copterSideFont)
				text.setPos(x + 10,z - 2)    #manual offsets depending on font
				text.setBrush(QBrush(self.color['white']))

		#draw friendly unselected vehicles
		for key in self.vehicleDict.keys():
			if (key in self.platoon.copterDict.keys() and self.selected_copter == 7):
				continue
			v = self.vehicleDict[key]
			if v.location.x != None and key != self.selected_copter:
				x = self.get_w_from_x(v.location.x)
				z = self.get_h_from_z(v.location.z)
				x = x - (self.copter_diameterX/2)
				z = z - (self.copter_diameterZ/2)
				if z > self.viewArenaXZ.height() - self.copter_diameterZ:
					z = self.viewArenaXZ.height() - self.copter_diameterZ
				sceneXZ.addRect(x, z, self.copter_diameterX, self.copter_diameterZ, QPen(v.color), QBrush(v.color))
				#add number text
				text = sceneXZ.addSimpleText(str(key), self.copterSideFont)
				text.setPos(x + 10,z - 2)    #manual offsets depending on font
				text.setBrush(QBrush(self.color['white']))

		#draw selected copter in different color
		if self.selected_copter in self.vehicleDict.keys():
			v = self.vehicleDict[self.selected_copter]
			if v.location.x != None:
				x = self.get_w_from_x(v.location.x)
				z = self.get_h_from_z(v.location.z)
				x = x - (self.copter_diameterX/2)
				z = z - (self.copter_diameterZ/2)
				if z > self.viewArenaXZ.height() - self.copter_diameterZ:
					z = self.viewArenaXZ.height() - self.copter_diameterZ
				sceneXZ.addRect(x, z, self.copter_diameterX, self.copter_diameterZ, QPen(self.color['green']), QBrush(self.color['green']))
				#add number text
				text = sceneXZ.addSimpleText(str(self.selected_copter), self.copterSideFont)
				text.setPos(x + 10,z - 2)    #manual offsets depending on font
				text.setBrush(QBrush(self.color['black']))
				
		self.paintPlatoonXZ()

### END XZ PLANE ###


		#update the unconnected copter states
		for key in self.unconnectedDict.keys():
			eval("self.groupCopter_%d" %key).setEnabled(True)
			if key == self.selected_copter:
				eval("self.copterColor%d"%key).setStyleSheet(self.notInitializedSelectedCopterStyle)
			elif self.unconnectedDict[key].connecting == True:
				eval("self.copterColor%d"%key).setStyleSheet(self.connectingCopterStyle)
			else:
				eval("self.copterColor%d"%key).setStyleSheet(self.notInitializedCopterStyle)

		#update the connected copter states
		for key in self.vehicleDict.keys():
			#check to see if platoon is selected
			if (key in self.platoon.copterDict.keys() and self.selected_copter == 7):
				continue
			# Copter will always exist now that we are using a dictionary
			# if copterIndex <= len(self.vehicles):
			#     #vehicle exists
			eval("self.groupCopter_%d" %key).setEnabled(True)
			v = self.vehicleDict[key]
			heartbeat_time = v.vehicle.last_heartbeat
			if int(heartbeat_time) % 6 == 5:
				#it's been 5 seconds since our last heart beat
				eval("self.copterColor%d"%key).setStyleSheet(self.noHeartBeatCopterStyle)
			elif key == self.selected_copter:
				#copter is selected
				eval("self.copterColor%d"%key).setStyleSheet(self.selectedCopterStyle)
			else:
				#copter is active, but not selected
				eval("self.copterColor%d"%key).setStyleSheet(self.copterLabelStyle)
			# else:
			#     #copter doesnt exist
			#     eval("self.copterColor%d"%copterIndex).setStyleSheet(self.notInitializedCopterStyle)
			
		#update platoon labels if platoon is selected
		if self.selected_copter == 7:
			for key in self.platoon.copterDict.keys():
				eval("self.groupCopter_%d" %key).setEnabled(True)
				v = self.platoon.copterDict[key]
				heartbeat_time = v.vehicle.last_heartbeat
				if int(heartbeat_time) % 6 == 5:
					#it's been 5 seconds since our last heart beat
					eval("self.copterColor%d"%key).setStyleSheet(self.noHeartBeatCopterStyle)
				elif key == self.platoon.leader.slot:
					#copter is leader
					eval("self.copterColor%d"%key).setStyleSheet(self.platoonLeaderStyle)
				else:
					#copter is in platoon but not leader
					eval("self.copterColor%d"%key).setStyleSheet(self.selectedCopterStyle)
					
		#draw the vehicle locations
		self.update_vehicle_status()

		#update the draw time
		self.draw_time = time.clock()

	#REQUIES:   key of vehicle
	#MODIFIES:  stylesheet of corresponding battery bar
	#EFFECTS:   turns battery bar red if voltage is below a certain threshold
	def batteryCheck(self, key):
		#set battery bar styles
		if self.vehicleDict[key].vehicle.battery.voltage < self.voltageRed:
			s = 'self.copterBatteryIndicator_'+str(key)+'.setStyleSheet(self.batteryRedStyle)'
			eval(s)
		elif self.vehicleDict[key].vehicle.battery.voltage < self.voltageYellow:
			s = 'self.copterBatteryIndicator_'+str(key)+'.setStyleSheet(self.batteryYellowStyle)'
			eval(s)
		else:
			s = 'self.copterBatteryIndicator_'+str(key)+'.setStyleSheet("")'
			eval(s)

	def paintVehiclesXY(self):
		pass
		
	def paintVehiclesXZ(self):
		pass
	
	def paintPlatoonXY(self):
		if self.selected_copter != 7:
			return
		sceneXY = self.viewArenaXY.scene()
		sceneXZ = self.viewArenaXZ.scene()
		# get view width and height
		w = self.viewArenaXY.width() #Scroll bars have been disabled so offsets are unnecessary now
		l = self.viewArenaXY.height()
		z = self.viewArenaXZ.height()
		# draw vehicles - dimensions from QI Simulator guide
		if self.scaleObjects == True:
			self.copter_diameterX = self.visualScalar * (w / self.arena_width) * 0.785876  # 30.94" proper scale
			self.copter_diameterY = self.visualScalar * (l / self.arena_length) * 0.785876  # 30.94" proper scale
			self.copter_diameterZ = self.visualScalar * (z / self.arena_height) * 0.2032  # 8" proper scale
		else:
			self.copter_diameterX = 30
			self.copter_diameterY = 30
			self.copter_diameterZ = 20
			
		for key in self.platoon.copterDict.keys():
			v = self.platoon.copterDict[key]
			if v.location.x != None and key != self.selected_copter:
				x = self.get_w_from_x(v.location.x)
				y = self.get_h_from_y(v.location.y)
				x = x - (self.copter_diameterX/2)
				y = y - (self.copter_diameterY/2)
				#print indicator for current goto
				if v.reachedGoto() == False:
					destX = self.get_w_from_x(v.destination.x) - self.click_diameter/2
					destY = self.get_h_from_y(v.destination.y) - self.click_diameter/2
					sceneXY.addEllipse(destX, destY, self.click_diameter, self.click_diameter, QPen(self.color['teal']), QBrush(self.color['teal']))
					p = QPen(self.color['teal'])
					p.setWidth(3)
					sceneXY.addLine(destX + (self.click_diameter/2), destY + (self.click_diameter/2), x + (self.copter_diameterX/2), y + (self.copter_diameterY/2), p)
				#draw circle for copter
				sceneXY.addEllipse(x, y, self.copter_diameterX, self.copter_diameterY, QPen(self.color['green']), QBrush(self.color['green']))
				#paint possession
				if self.hasBall == v.id:
					p = QPen(self.color['orange'])
					p.setWidth(5)
					sceneXY.addEllipse(x, y, self.copter_diameterX + 5, self.copter_diameterY + 5, p, QBrush(QColor(0,0,0,0)))
				#paint heading
				self.paintHeading(key)
				#add number text
				text = sceneXY.addSimpleText(str(key), self.copterNumFont)
				text.setPos(x + 9,y - 5)    #manual offsets depending on font
				if key == self.platoon.leader.slot:
					text.setBrush(QBrush(self.color['red']))
				else:
					text.setBrush(QBrush(self.color['black']))
				#update battery bar color
				self.batteryCheck(key)
	
	def paintPlatoonXZ(self):
		if self.selected_copter != 7:
			return
		sceneXY = self.viewArenaXY.scene()
		sceneXZ = self.viewArenaXZ.scene()
		# get view width and height
		w = self.viewArenaXY.width() #Scroll bars have been disabled so offsets are unnecessary now
		l = self.viewArenaXY.height()
		z = self.viewArenaXZ.height()
		# draw vehicles - dimensions from QI Simulator guide
		if self.scaleObjects == True:
			self.copter_diameterX = self.visualScalar * (w / self.arena_width) * 0.785876  # 30.94" proper scale
			self.copter_diameterY = self.visualScalar * (l / self.arena_length) * 0.785876  # 30.94" proper scale
			self.copter_diameterZ = self.visualScalar * (z / self.arena_height) * 0.2032  # 8" proper scale
		else:
			self.copter_diameterX = 30
			self.copter_diameterY = 30
			self.copter_diameterZ = 20
			
		for key in self.platoon.copterDict.keys():
			v = self.platoon.copterDict[key]
			if v.location.x != None:
				x = self.get_w_from_x(v.location.x)
				z = self.get_h_from_z(v.location.z)
				x = x - (self.copter_diameterX/2)
				z = z - (self.copter_diameterZ/2)
				if z > self.viewArenaXZ.height() - self.copter_diameterZ:
					z = self.viewArenaXZ.height() - self.copter_diameterZ
				sceneXZ.addRect(x, z, self.copter_diameterX, self.copter_diameterZ, QPen(self.color['green']), QBrush(self.color['green']))
				#add number text
				text = sceneXZ.addSimpleText(str(key), self.copterSideFont)
				text.setPos(x + 10,z - 2)    #manual offsets depending on font       
				if key == self.platoon.leader.slot:
					text.setBrush(QBrush(self.color['red']))
				else:
					text.setBrush(QBrush(self.color['black']))
			
	#REQUIRES:  key of vehicle
	#MODIFIES:  N/A
	#EFFECTS:   paints the heading of the vehicle. should be called from paintevent for each copter
	def paintHeading(self, key = -1, vehicle = None):
		if vehicle == None:
			v = self.vehicleDict[key]
		else:
			v = vehicle

		p1 = QPoint(0, -32)
		p2 = QPoint(-5, -20)
		p3 = QPoint(5, -20)

		points = [p1, p2, p3, p1]

		triangle = QPolygon(points)


		matrix = QMatrix()
		matrix.rotate(v.heading)
		triangle = matrix.map(triangle)

		copterX = self.get_w_from_x(v.location.x)
		copterY = self.get_h_from_y(v.location.y)
		triangle.translate(copterX,copterY)

		if key == self.selected_copter or (key in self.platoon.copterDict.keys() and self.selected_copter == 7):
			self.viewArenaXY.scene().addPolygon(triangle, QPen(self.color['green']), QBrush(self.color['green']))
		else:
			self.viewArenaXY.scene().addPolygon(triangle, QPen(v.color), QBrush(v.color))

	def add_vehicle(self, v):
		"""
			Add v to the dictionary of unconnected vehicle
			Inputs: v - an Soar1ngVehicle type object to be added to the field
		"""

		print "Assigning vehicle to Slot %i\n\n" % v.slot
		self.unconnectedDict[v.slot] = v
		v.color = self.color['blue']

	def connectVehicle(self):
		"""
			Connects the currently selected copter and adds it to the field
			DO NOT Call by itself. use thread wrapper function connectPushed() instead
		"""
		currentSlot = self.selected_copter

		if currentSlot in self.vehicleDict.keys():
			print "Copter is already connected"
			return

		currentCopter = self.unconnectedDict[currentSlot]

		if currentCopter.connecting == True:
			print "Copter is already trying to connect"
			return

		connected = currentCopter.connect(currentCopter.connection)

		del self.unconnectedDict[currentSlot]

		if connected:
			s = 'QObject.connect(self, SIGNAL("batteryUpdated_'+str(currentSlot)+'(int)"), self.copterBatteryIndicator_'+str(currentSlot)+', SLOT("setValue(int)"))'
			eval(s)
			currentCopter.vehicle.add_attribute_listener('battery', self.battery_callback)
			currentCopter.setParams(self.copterParams)
			self.vehicleDict[currentSlot] = currentCopter
			self.update()
			#set lights
			currentCopter.setLights(1000)   #solid lights, i.e. no possession

		else:
			self.unconnectedDict[currentSlot] = currentCopter
			print "Failed to Connect, Please try again."

	def disconnectVehicle(self):
		"""
			Disconnects the currently selected copter and removes it from the field
			DO NOT Call by itself. use thread wrapper function disconnectPushed() instead
		"""
		currentSlot = self.selected_copter

		if currentSlot not in self.vehicleDict.keys():
			print "Copter is not connected"
			return False

		currentCopter = self.vehicleDict[currentSlot]

		if currentCopter.connecting == True:
			print "Copter is trying to connect. Wait until connection is established before disconnecting."
			return False

		currentCopter.close()

		del self.vehicleDict[currentSlot]

		self.unconnectedDict[currentSlot] = currentCopter

		print "Selected copter disconnected"
		s = 'self.emit(SIGNAL("batteryUpdated_'+str(self.selected_copter)+'(int)"), int(130))'
		eval(s)
		return True

	def update_vehicle_status(self):
		for key in self.vehicleDict.keys():
			v = self.vehicleDict[key]
			#for all the vehicles we currently are tracking
			if v.location.x != None and v.vehicle.gps_0.fix_type == 3:
				#if the vehicle has reported a position
				eval("self.copterX_%d" % key).setText(str(round(v.location.x,2)))
				eval("self.copterY_%d" % key).setText(str(round(v.location.y,2)))
				eval("self.copterZ_%d" % key).setText(str(round(v.vehicle.location.global_relative_frame.alt,2)))
				eval("self.copterH_%d" % key).setText(str(round(v.vehicle.heading,2)))
				eval("self.copterX_%d" % key).setStyleSheet('')
				eval("self.copterY_%d" % key).setStyleSheet('')
				eval("self.copterZ_%d" % key).setStyleSheet('')
				eval("self.copterH_%d" % key).setStyleSheet('')
			else:
				eval("self.copterX_%d" % key).setText('---')
				eval("self.copterY_%d" % key).setText('NO')
				eval("self.copterZ_%d" % key).setText('GPS')
				eval("self.copterH_%d" % key).setText('---')
				eval("self.copterX_%d" % key).setStyleSheet(self.warningStyle)
				eval("self.copterY_%d" % key).setStyleSheet(self.warningStyle)
				eval("self.copterZ_%d" % key).setStyleSheet(self.warningStyle)
				eval("self.copterH_%d" % key).setStyleSheet(self.warningStyle)

			#update the mode
			eval("self.copterMode_%d" % key).setText(v.vehicle.mode.name)

			#update battery status
			if v.vehicle.battery.voltage:
				eval("self.copterVolts_%d" % key).setText(str(round(v.vehicle.battery.voltage,2)))
			if v.vehicle.battery.current:
				eval("self.copterAmps_%d" % key).setText(str(round(v.vehicle.battery.current,2)))

	def sendADSBtoAll(self):
		"""
			Sends ADSB information of our/enemy copters to our copters
		"""
		# rkey = key of receiving copter
		self.ADSB = True
		while (self.ADSB):
			for rkey in self.vehicleDict:
				#print "sending ADSB to copter: ", rkey

				# rCopter = copter receiving the message
				rCopter = self.vehicleDict[rkey]

				# send information of our copters
				# skey = key of copter whose information is sent
				for skey in self.vehicleDict:

					#sCopter = copter whose information is sent
					sCopter = self.vehicleDict[skey]

					#send only other copter's messages
					if rCopter.slot != sCopter.slot:
						try:
							id = sCopter.slot   #let our copter's slot be the id
							lat = sCopter.adsb_lat
							lon = sCopter.adsb_long
							altitude = sCopter.adsb_altitude
							heading = sCopter.adsb_heading
							hor_vel = sCopter.adsb_hor_vel
							ver_vel = sCopter.adsb_ver_vel

							msg = self.sendADSBtoCopter(rCopter, id, lat, lon, altitude, heading, hor_vel, ver_vel)
							# print "receiving vehicle:", rCopter.slot
							# print "sending vehicle information:", sCopter.slot
							# print "adsb msg:", msg
						except Exception as e:
							print "ADSB Message was invalid: ", e
							print "id: ", id
							print "lat: ", lat
							print "lon: ", lon
							print "alt: ", altitude
							print "head: ", heading
							print "h_vel: ", hor_vel
							print "v_vel: ", ver_vel
							pass
						#print "copter ", skey, " information sent to copter ", rkey
						# print "copter ", skey, " information sent to copter ", rkey


				#Send information of enemy copters
				for skey in self.enemyDict:
					try:
						#sCopter = copter whose information is sent
						sCopter = self.enemyDict[skey]
						id = sCopter.id
						lat = sCopter.adsb_lat
						lon = sCopter.adsb_lon
						altitude = sCopter.adsb_altitude
						heading = sCopter.adsb_heading
						hor_vel = sCopter.adsb_hor_vel
						ver_vel = sCopter.adsb_ver_vel
						msg = self.sendADSBtoCopter(rCopter, id, lat, lon, altitude, heading, hor_vel, ver_vel)
					except Exception:
						print "ADSB Message was invalid: "
						pass
					# print "copter ", skey, " information sent to copter ", rkey

			# print "ADSB sleep 1 seconds..."
			time.sleep(1)

	def stopADSB(self):
		self.ADSB = False

	def sendADSBtoCopter(self, copter, icao, lat, lon, altitude, heading, hor_vel, ver_vel):
		"""
			Sends an ADSB message to copter
			Source: https://pixhawk.ethz.ch/mavlink/#ADSB_VEHICLE
		"""
		msg = copter.vehicle.message_factory.adsb_vehicle_encode(
			icao,           #ICAO_address
			lat,            #lat
			lon,            #lon
			1,              #altitude_type: 0 if QNH (relative to sea level?), 1 if GNSS (from GPS?)
			altitude,       #altitude (millimeters)
			heading,        #heading (centidegrees)
			hor_vel,             #horizontal velocity (cm/s)
			ver_vel,             #vertical velocity (cm/s)
			"",             #callsign,
			0,              #emitter_type, leaving unassigned for now, see webpage for vehicle classifications
			0,              #time since last communication in seconds
			0x3,            #flags (valid coords and altitude)
			0               #squawk
		)
		#print msg
		# print type(icao)
		# print type(lat)
		# print type(lon)
		# print type(altitude)
		# print type(heading)
		# print type(hor_vel)
		# print type(ver_vel)
		copter.vehicle.send_mavlink(msg)
		return msg



	#this is used to paint battery bars
	def battery_callback(self, source, attr, val):
		for key in self.vehicleDict.keys():
			v = self.vehicleDict[key]
			if v.vehicle.battery.voltage:
				#s = 'self.emit(SIGNAL("batteryUpdated_'+str(key)+'(int)"), int(168))'    #SITL only for lower voltage
				s = 'self.emit(SIGNAL("batteryUpdated_'+str(key)+'(int)"), int(v.vehicle.battery.voltage*10))'
				eval(s)

	### Event Handlers/Slots ###

	def eventFilter(self,object,event):
		# TODO: Implement hover text
		# self.hoverLocation.setText('(' + str(round(self.get_x_from_w(event.x()), 2)) + ', ' + str(round(self.get_y_from_h(event.y()), 2)) + ')')
		# print object # object will be the one that tells you the widget that the event occurred
		# print event.type()
		if event.type() == QEvent.MouseButtonPress:
			self.useWaypoint = False
			#print "Mouse clicked at " + str(event.x()) + ", " + str(event.y())
			self.click = (event.x(), event.y())
			self.update()
			if object == self.viewArenaXY:          
				self.xc = event.x()
				self.yc = event.y()
				if self.settingPatrol == True:
					self.patrolClicks.append((self.get_x_from_w(self.xc), self.get_y_from_h(self.yc)))
					return True
				if self.useWaypoint == True:
					self.zc = self.get_h_from_z(self.takeoff_alt)
				if event.button() == Qt.RightButton:
					if self.selected_copter == 7:
						if self.platoon.size() > 0:
							self.zc = self.get_h_from_z(self.platoon.leader.z)
						else:
							print 'Not enough copters for right click command'
							return
					else:
						self.zc = self.get_h_from_z(self.vehicleDict[self.selected_copter].z)
					self.gotoPushed()
			elif object == self.viewArenaXZ:
				self.zc = event.y()
				if self.useWaypoint == True or self.xc == None:
					self.xc = self.get_w_from_x(0)
					self.yc = self.get_h_from_y(0)
				if event.button() == Qt.RightButton:
					self.xc = self.get_w_from_x(self.vehicleDict[self.selected_copter].x)
					self.yc = self.get_h_from_y(self.vehicleDict[self.selected_copter].y)
					self.gotoPushed()
			else:
				print "Object neither viewArenaXY or viewArenaXZ"
			self.savedLocX.setText(str(round(self.get_x_from_w(self.xc), 2)))
			self.savedLocY.setText(str(round(self.get_y_from_h(self.yc), 2)))
			self.savedLocZ.setText(str(round(self.get_z_from_h(self.zc), 2)))
			#set useWaypoint to False since click is selected
			return True
		return False

	def selectCopterCheck(self):
		""" Checks if a copter has been selected """
		if self.selected_copter in self.vehicleDict.keys():
			return True
		print 'Invalid copter selected!'
		return False

	def connectPushed(self):
		t = threading.Thread(target=self.connectVehicle, args=())
		t.start()

	def disconnectConfirmPushed(self):
		if self.disconnectArmed == True and self.selectCopterCheck() == True:
			t = threading.Thread(target=self.disconnectVehicle, args=())
			t.start()
				
			self.disconnectArmed = False
			self.pbtnDISCONNECT_CONFIRM.setStyleSheet("")
			self.pbtnDISCONNECT.setText('DISCONNECT')
	
	def disconnectPushed(self):
		if self.disconnectArmed == False:
			self.disconnectArmed = True
			self.pbtnDISCONNECT_CONFIRM.setStyleSheet(self.killArmedStyle)
			self.pbtnDISCONNECT.setText('DISCONNECT ARMED')
			print '***WARNING: DISCONNECT ARMED***'
		elif self.disconnectArmed == True:
			self.disconnectArmed = False
			self.pbtnDISCONNECT_CONFIRM.setStyleSheet("")
			self.pbtnDISCONNECT.setText('DISCONNECT')
			print '***DISCONNECT DISARMED***'

	def armAndTakeOffPushed(self):
		#print 'Arm pushed!'
		if self.selectCopterCheck() == False:
			return
		self.vehicleDict[self.selected_copter].arm_and_takeoff(self.takeoff_alt)
		self.headingLock = 0

	def copterColorPushed(self):
		# TODO: You can typecast to int and then if-check (1 <= id <= 6)
		id = 0
		sender = self.sender()
		if sender.text() == '1':
			id = 1
		elif sender.text() == '2':
			id = 2
		elif sender.text() == '3':
			id = 3
		elif sender.text() == '4':
			id = 4
		elif sender.text() == '5':
			id = 5
		elif sender.text() == '6':
			id = 6
		else:
			print 'Invalid sender:'
			print sender.text()
			return

		self.selectCopter(id)
		if id in self.unconnectedDict:
			self.connectPushed()
		elif id in self.vehicleDict:
			#print "Copter is already connected"
			return
		else:
			print "No copter to connect to"
			return

	'''
	def takeoffPushed(self):
		#print 'Takeoff pushed!'
		if self.selectCopterCheck() == False:
			return
		#self.vehicleDict[self.selected_copter].takeoff()
	'''

	def isPointInsideRectangle(self, x, y):
		return (self.XYx1 <= x <= self.XYx2) and (self.XYy1 <= y <= self.XYy2)

	def gotoPushed(self):
		if self.selectCopterCheck() == False and self.selected_copter != 7:
			return
		#xc, yc = self.click
		if self.xc is None or self.yc is None or self.zc is None:
			print 'No point selected.'
			return
		v = 1
		if QApplication.keyboardModifiers() == Qt.ShiftModifier:
			v = 5
			print 'Shift applied, using velocity v =', str(v)
		if self.useWaypoint == False:
			x = self.get_x_from_w(self.xc)
			y = self.get_y_from_h(self.yc)
			z = self.get_z_from_h(self.zc)

			isAcceptablePoint = self.isPointInsideRectangle(self.xc,self.yc)
			# isAcceptablePoint = self.isPointInsideRectangle(self.xc,self.zc)
			if isAcceptablePoint:
				print("Copter {0} going to: {1},{2},{3} px == {4:.2f},{5:.2f},{6:.2f} m".format(self.selected_copter, self.xc, self.yc, self.zc, x, y, z))
				if self.selected_copter == 7:
					#platoon command
					currentCopter = self.platoon
					currentAlt = self.platoon.leader.z
				else:
					currentCopter = self.vehicleDict[self.selected_copter]
					currentAlt = currentCopter.location.z
				currentCopter.goto(x,y,z, v)
				if self.headingLock != None:
					currentCopter.rotate(self.headingLock)
			else:
				print "Clicked point is not within bounds."
		elif self.useWaypoint == True:
			x = self.waypointDict[self.selected_waypoint].x
			y = self.waypointDict[self.selected_waypoint].y
			z = self.waypointDict[self.selected_waypoint].z
			isAcceptablePoint = self.isPointInsideRectangle(self.xc,self.yc)
			 # isAcceptablePoint = self.isPointInsideRectangle(self.xc,self.zc)
			if isAcceptablePoint:
				print(
				"Copter {0} going to: {1},{2},{3} px == {4:.2f},{5:.2f},{6:.2f} m".format(self.selected_copter, self.xc, self.yc, self.zc, x, y, z))
				if self.selected_copter == 7:
					currentCopter = self.platoon
				else:
					currentCopter = self.vehicleDict[self.selected_copter]
				currentCopter.gotoWaypoint(self.waypointDict[self.selected_waypoint], v)
			else:
				print "That point is not in bounds."

	def landPushed(self):
		if self.selectCopterCheck() == False:
			return
		self.vehicleDict[self.selected_copter].vehicle.mode = dronekit.VehicleMode("LAND")

	def flipPushed(self):
		if self.selectCopterCheck() == False:
			return
		print "Flipping"
		if self.selectCopterCheck() == False:
			return
		self.vehicleDict[self.selected_copter].vehicle._master.set_mode(14)
		#currentCopter.flip()
		
	def lobPushed(self):
		if self.selectCopterCheck() == False:
			return
		print "Lobbing"
		if self.selectCopterCheck() == False:
			return
		self.vehicleDict[self.selected_copter].vehicle._master.set_mode(13)
		#currentCopter.flip()

		
	def followPushed(self, i = None):
		if i == None:
			self.settingFollow = True
			print 'Setting follow. Please select a copter or press q to quit.'
			return
			
		if i in self.vehicleDict.keys():
			print 'Following copter',i
			self.vehicleDict[self.selected_copter].follow(self.vehicleDict[int(i)])
			self.selectCopter(i)
			return True
		
		for key in self.enemyDict.keys():
			v = self.enemyDict[key]
			if v.id == i:
				print 'Following enemy copter',i - 10
				self.vehicleDict[self.selected_copter].follow(v)
				return True
		
		return False
		
	def patrolPushed(self):
		if self.selectCopterCheck() == False:
			return
		if self.settingPatrol == False:
			self.settingPatrol = True
			print 'Setting patrol. Click on XY to set patrol positions. Press q to quit or press PATROL again to confirm.'
		else:
			# send the list of patrol locations
			self.vehicleDict[self.selected_copter].rotate(self.headingLock)
			self.vehicleDict[self.selected_copter].patrol(self.patrolClicks)
			self.settingPatrol = False
			self.patrolClicks = []
			
	def platoonPushed(self):
		if self.selectCopterCheck() == False:
			return
		if self.platoon.hasCopter(self.selected_copter):
			print 'Removing copter in slot',self.selected_copter,'from platoon'
			self.platoon.removeCopter(self.selected_copter)
		else:
			print 'Adding copter in slot',self.selected_copter,'to platoon'
			self.platoon.addCopter(self.vehicleDict[self.selected_copter])

	def killPushed(self):
		if self.killArmed == False:
			self.killArmed = True
			self.pbtnKILL_CONFIRM.setStyleSheet(self.killArmedStyle)
			self.pbtnKILL.setText('KILL ARMED')
			print '***WARNING: KILL ARMED***'
		elif self.killArmed == True:
			self.killArmed = False
			self.pbtnKILL_CONFIRM.setStyleSheet("")
			self.pbtnKILL.setText('KILL')
			print '***KILL DISARMED***'

	def killConfirmPushed(self):
		if self.killArmed == True and self.selectCopterCheck() == True:
			self.vehicleDict[self.selected_copter].emergency_kill()
			self.killArmed = False
			self.pbtnKILL_CONFIRM.setStyleSheet("")
			self.pbtnKILL.setText('KILL')

	def setTakeoffAlt(self, alt):
		"""
			Sets the takeoff altitude for all copters in meters
		"""
		print "Takeoff altitude set to: ", alt, " meters"
		self.takeoff_alt = alt
		self.zc = self.get_h_from_z(self.takeoff_alt)

	def setWaypointDicts(self, wayPts, dropPts, blockPts, flipPts, etcPts):
		"""
			Add the waypoints in dictionary into our Waypoints Dictionary
		"""
		for key in wayPts:
			self.waypointDict[key] = wayPts[key]
		for key in dropPts:
			self.dropPtDict[key] = dropPts[key]
		for key in blockPts:
			self.blockPtDict[key] = blockPts[key]
		for key in flipPts:
			self.flipPtDict[key] = flipPts[key]
		for key in etcPts:
			self.etcPtDict[key] = etcPts[key]

		#setup waypoints

		#set focus policies
		self.markedLocationsList.setFocusPolicy(Qt.NoFocus) #no focus prevents waypoint selection from blocking keyboard commands

		#populate list
		self.markedLocationsList.setSortingEnabled(True)
		self.markedLocationsList.clear()
		for key in self.waypointDict.keys():
			w = self.waypointDict[key]
			self.markedLocationsList.addItem(w.id)
			
		self.currentPtDict = self.waypointDict

		#connect waypoint list signal to slot
		self.markedLocationsList.itemClicked.connect(self.waypointSelected)

	def setCopterParams(self, dictionary):
		"""
			Add parameters to the copter parameters Dictionary
		"""
		for key in dictionary:
			self.copterParams[key] = dictionary[key]

	def decreasePositionIncrement(self):
		"""
			Decreases the Increment value
		"""
		if self.positionIncrement - .05 <= .000000000001:    #arbitrary small number to prevent roundoff error
			print "Cannot decrease increment below 0."
			return
		self.positionIncrement -= 0.05
		print("descreased position increment to : %f" % self.positionIncrement)
		#update label
		self.labelIncrementSpeedVALUE.setText(str(self.positionIncrement))

	def increasePositionIncrement(self):
		"""
			Increases the Increment value
		"""
		self.positionIncrement += 0.05
		print("increased position increment to : %f" % self.positionIncrement)
		#update label
		self.labelIncrementSpeedVALUE.setText(str(self.positionIncrement))

	def selectCopter(self,copterNumber):
		if copterNumber in self.vehicleDict.keys():
			self.selected_copter = copterNumber
			v = self.vehicleDict[self.selected_copter]
			self.xc = self.get_w_from_x(v.x)
			self.yc = self.get_h_from_y(v.y)
			self.zc = self.get_h_from_z(v.z)
		elif (copterNumber in self.unconnectedDict.keys()):
			self.selected_copter = copterNumber
			print "Copter:", copterNumber, "is selected"
		elif copterNumber == 7:
			self.selected_copter = copterNumber
			print 'Platoon selected'
		else:
			print "Not a valid Copter"

	### Event Handlers ###
	
	def allwpPushed(self):
		self.markedLocationsList.clear()
		for key in self.waypointDict.keys():
			w = self.waypointDict[key]
			self.markedLocationsList.addItem(w.id)
		self.currentPtDict = self.waypointDict
		
	def dropwpPushed(self):
		self.markedLocationsList.clear()
		for key in self.dropPtDict.keys():
			w = self.dropPtDict[key]
			self.markedLocationsList.addItem(w.id)
		self.currentPtDict = self.dropPtDict
		
	def shootwpPushed(self):
		self.markedLocationsList.clear()
		for key in self.flipPtDict.keys():
			w = self.flipPtDict[key]
			self.markedLocationsList.addItem(w.id)
		self.currentPtDict = self.flipPtDict
	
	def blockwpPushed(self):
		self.markedLocationsList.clear()
		for key in self.blockPtDict.keys():
			w = self.blockPtDict[key]
			self.markedLocationsList.addItem(w.id)
		self.currentPtDict = self.blockPtDict
		
	def etcwpPushed(self):
		self.markedLocationsList.clear()
		for key in self.etcPtDict.keys():
			w = self.etcPtDict[key]
			self.markedLocationsList.addItem(w.id)
		self.currentPtDict = self.etcPtDict
		
	def addwpPushed(self):
		try:
			x = float(self.savedLocX.text())
			y = float(self.savedLocY.text())
			z = float(self.savedLocZ.text())
			h = float(self.savedLocH.text())
		except ValueError:
			print 'Invalid waypoint coordinates. Waypoint not added.'
			return
		type = 'custom'
		id = 'Custom '
		#get next available id
		i = 1
		while str(id + str(i)) in self.waypointDict.keys():
			i += 1
		id = str(id + str(i))
		
		w = WayPoints(None)
		w.setProperties(id, type, x, y, z, h)
		#add this waypoint to currently selected dict and all dict
		if self.currentPtDict == self.dropPtDict:
			self.dropPtDict[id] = w
		elif self.currentPtDict == self.flipPtDict:
			self.flipPtDict[id] = w
		elif self.currentPtDict == self.blockPtDict:
			self.blockPtDict[id] = w
		elif self.currentPtDict == self.etcPtDict:
			self.etcPtDict[id] = w
		
		self.waypointDict[id] = w
		
		#refresh the waypoint list
		self.markedLocationsList.clear()
		for key in self.currentPtDict.keys():
			w = self.currentPtDict[key]
			self.markedLocationsList.addItem(w.id)
		
	def removewpPushed(self):
		if self.selected_waypoint in self.waypointDict.keys():
			del self.waypointDict[self.selected_waypoint]
		if self.selected_waypoint in self.dropPtDict.keys():
			del self.dropPtDict[self.selected_waypoint]
		if self.selected_waypoint in self.flipPtDict.keys():
			del self.flipPtDict[self.selected_waypoint]
		if self.selected_waypoint in self.blockPtDict.keys():
			del self.blockPtDict[self.selected_waypoint]
		if self.selected_waypoint in self.etcPtDict.keys():
			del self.etcPtDict[self.selected_waypoint]
			
		#refresh the waypoint list
		self.markedLocationsList.clear()
		for key in self.currentPtDict.keys():
			w = self.currentPtDict[key]
			self.markedLocationsList.addItem(w.id)
			
	def centerPushed(self):
		"""
			Sends copter to the center of the map
		"""
		if self.selectCopterCheck():
			centerPoint = self.waypointDict["center"]
			currentCopter = self.vehicleDict[self.selected_copter]
			currentCopter.goto(centerPoint.x, centerPoint.y, centerPoint.z)
			currentCopter.rotate(centerPoint.heading)

	def waypointSelected(self, waypoint):
		self.selected_waypoint = waypoint.text()
		print 'Selected waypoint:',self.selected_waypoint

		w = self.waypointDict[self.selected_waypoint]
		self.xc = self.get_w_from_x(w.x) 
		self.yc = self.get_h_from_y(w.y)
		self.zc = self.get_h_from_z(w.z)
		self.useWaypoint = True
		
		x = str(round(w.x, 2))
		y = str(round(w.y, 2))
		z = str(round(w.z, 2))
		h = str(round(w.heading, 2))
		
		
		self.savedLocX.setText(x)
		self.savedLocY.setText(y)
		self.savedLocZ.setText(z)
		self.savedLocH.setText(h)



	def assignWidgets(self):
		"""
			Assign functions to Buttons in GUI
		"""
		#copter command buttons
		self.pbtnARM.clicked.connect(self.armAndTakeOffPushed)
		self.pbtnGOTO.clicked.connect(self.gotoPushed)
		self.pbtnLAND.clicked.connect(self.landPushed)
		self.pbtnKILL.clicked.connect(self.killPushed)
		self.pbtnKILL_CONFIRM.clicked.connect(self.killConfirmPushed)
		self.pbtnFLIP.clicked.connect(self.flipPushed)
		self.pbtnLOB.clicked.connect(self.lobPushed)
		self.pbtnFOLLOW.clicked.connect(self.followPushed)
		self.pbtnDISCONNECT.clicked.connect(self.disconnectPushed)
		self.pbtnDISCONNECT_CONFIRM.clicked.connect(self.disconnectConfirmPushed)
		self.pbtnPATROL.clicked.connect(self.patrolPushed)
		self.pbtnPLATOON.clicked.connect(self.platoonPushed)
		#copter buttons
		self.copterColor1.clicked.connect(self.copterColorPushed)
		self.copterColor2.clicked.connect(self.copterColorPushed)
		self.copterColor3.clicked.connect(self.copterColorPushed)
		self.copterColor4.clicked.connect(self.copterColorPushed)
		self.copterColor5.clicked.connect(self.copterColorPushed)
		self.copterColor6.clicked.connect(self.copterColorPushed)
		#waypoint buttons
		self.pbtnALLWP.clicked.connect(self.allwpPushed)
		self.pbtnDROPWP.clicked.connect(self.dropwpPushed)
		self.pbtnSHOOTWP.clicked.connect(self.shootwpPushed)
		self.pbtnBLOCKWP.clicked.connect(self.blockwpPushed)
		self.pbtnETCWP.clicked.connect(self.etcwpPushed)
		self.pbtnADDWP.clicked.connect(self.addwpPushed)
		self.pbtnREMOVEWP.clicked.connect(self.removewpPushed)
		


	def keyPressEvent(self, event):

		#catch modifiers
		if(event.key() == Qt.Key_Shift):
			return
			
		#setting patrol
		if(self.settingPatrol == True):
			#check for quit
			if(event.key() == Qt.Key_Q):
				self.settingPatrol = False
				self.patrolClicks = []
				return
			
		#setting follow
		if(self.settingFollow == True):
			i = 0
			
			#check for quit
			if(event.key() == Qt.Key_Q):
				self.settingFollow = False
				return
				
			if(event.key() == Qt.Key_1):
				i = 1

			elif(event.key() == Qt.Key_2):
				i = 2

			elif(event.key() == Qt.Key_3):
				i = 3

			elif(event.key() == Qt.Key_4):
				i = 4

			elif(event.key() == Qt.Key_5):
				i = 5

			elif(event.key() == Qt.Key_6):
				i = 6
				
			if(event.key() == Qt.Key_F1):
				i = 11

			elif(event.key() == Qt.Key_F2):
				i = 12

			elif(event.key() == Qt.Key_F3):
				i = 13

			elif(event.key() == Qt.Key_F4):
				i = 14

			elif(event.key() == Qt.Key_F5):
				i = 15

			elif(event.key() == Qt.Key_F6):
				i = 16
		
			if self.followPushed(i):
				self.settingFollow = False

			return

		if(event.key() == Qt.Key_1):
			self.selectCopter(1)

		elif(event.key() == Qt.Key_2):
			self.selectCopter(2)

		elif(event.key() == Qt.Key_3):
			self.selectCopter(3)

		elif(event.key() == Qt.Key_4):
			self.selectCopter(4)

		elif(event.key() == Qt.Key_5):
			self.selectCopter(5)

		elif(event.key() == Qt.Key_6):
			self.selectCopter(6)

		elif(event.key() == Qt.Key_7):
			self.selectCopter(7)

		elif(event.key() == Qt.Key_N):
			self.decreasePositionIncrement()

		elif(event.key() == Qt.Key_M):
			self.increasePositionIncrement()

		elif self.selected_copter == 7:
			#platoon commands
			
			#check copter size first
			if self.platoon.size() <= 0:
				print 'Not enough copters in platoon. Current size:',self.platoon.size()
				return
			else:
				currentCopter = self.platoon
				
			if(event.key() == Qt.Key_G):
				self.gotoPushed()
			elif QApplication.keyboardModifiers() == Qt.ShiftModifier:
				if (event.key() == Qt.Key_I):
					currentCopter.rotate(0)
					self.headingLock = 0

				elif(event.key() == Qt.Key_J):
					currentCopter.rotate(270)
					self.headingLock = 270

				elif(event.key() == Qt.Key_K):
					currentCopter.rotate(180)
					self.headingLock = 180

				elif(event.key() == Qt.Key_L):
					currentCopter.rotate(90)
					self.headingLock = 90
					
			elif(event.key() == Qt.Key_J):
				currentCopter.move(-self.positionIncrement,0.0,0.0)

			elif(event.key() == Qt.Key_K):
				currentCopter.move(0.0,-self.positionIncrement,0.0)

			elif(event.key() == Qt.Key_I):
				currentCopter.move(0.0,self.positionIncrement,0.0)

			elif(event.key() == Qt.Key_L):
				currentCopter.move(self.positionIncrement,0.0,0.0)

			elif(event.key() == Qt.Key_Y):
				currentCopter.move(0.0,0.0,self.positionIncrement)

			elif(event.key() == Qt.Key_H):
				currentCopter.move(0.0,0.0,-self.positionIncrement)

			elif(event.key() == Qt.Key_U):
				currentCopter.rotateLeft(45)
				
			elif(event.key() == Qt.Key_O):
				currentCopter.rotateRight(45)
				
			elif(event.key() == Qt.Key_Escape) or (event.key() == Qt.Key_S):
				currentCopter.stop()
			else:
				print 'Invalid platoon command.'
				return

		elif self.selected_copter in self.unconnectedDict.keys():
			if (event.key() == Qt.Key_C):
				self.connectPushed()

		elif self.selected_copter in self.vehicleDict.keys():
			currentCopter = self.vehicleDict[self.selected_copter]

			if QApplication.keyboardModifiers() == Qt.ShiftModifier:
				if (event.key() == Qt.Key_I):
					currentCopter.rotate(0)
					self.headingLock = 0

				elif(event.key() == Qt.Key_J):
					currentCopter.rotate(270)
					self.headingLock = 270

				elif(event.key() == Qt.Key_K):
					currentCopter.rotate(180)
					self.headingLock = 180

				elif(event.key() == Qt.Key_L):
					currentCopter.rotate(90)
					self.headingLock = 90
					
				elif(event.key() == Qt.Key_G):
					self.gotoPushed()

			elif(event.key() == Qt.Key_C):
				print "Copter ", self.selected_copter," is already connected"

			elif(event.key() == Qt.Key_A):
				self.armAndTakeOffPushed()

			elif(event.key() == Qt.Key_F5):
				self.landPushed()

			elif (event.key() == Qt.Key_Plus):
				self.disconnectPushed()

			elif(event.key() == Qt.Key_Escape) or (event.key() == Qt.Key_S):
				currentCopter.holdPosition()

			elif(event.key() == Qt.Key_G):
				self.gotoPushed()

			elif(event.key() == Qt.Key_J):
				if (self.vehicleDict[self.selected_copter].x >= -self.arena_width*.8/2):
					currentCopter.move(-self.positionIncrement,0.0,0.0)

			elif(event.key() == Qt.Key_K):
				if (self.vehicleDict[self.selected_copter].y >= -self.arena_height*.7/2):
					currentCopter.move(0.0,-self.positionIncrement,0.0)

			elif(event.key() == Qt.Key_I):
				if (self.vehicleDict[self.selected_copter].y <= self.arena_height*.7/2):
					currentCopter.move(0.0,self.positionIncrement,0.0)

			elif(event.key() == Qt.Key_L):
				if (self.vehicleDict[self.selected_copter].x <= self.arena_width*.8/2):
					currentCopter.move(self.positionIncrement,0.0,0.0)

			elif(event.key() == Qt.Key_Y):
				currentCopter.move(0.0,0.0,self.positionIncrement)

			elif(event.key() == Qt.Key_H):
				currentCopter.move(0.0,0.0,-self.positionIncrement)

			elif(event.key() == Qt.Key_U):
				self.headingLock = (self.vehicleDict[self.selected_copter].heading - 45) % 360
				currentCopter.rotateLeft(45)
				

			elif(event.key() == Qt.Key_O):
				self.headingLock = (self.vehicleDict[self.selected_copter].heading + 45) % 360
				currentCopter.rotateRight(45)
			
			elif(event.key() == Qt.Key_F9):
				self.followPushed()
				
			elif(event.key() == Qt.Key_F12):
				self.patrolPushed()

			elif(event.key() == Qt.Key_P):
				currentCopter.currentStatus()

			elif(event.key() == Qt.Key_Backspace):
				self.flipPushed()

			elif(event.key() == Qt.Key_Backslash):
				self.lobPushed()

			elif(event.key() == Qt.Key_BracketLeft):
				currentCopter.disableADSB()

			elif (event.key() == Qt.Key_BracketRight):
				currentCopter.enableADSB()

			elif(event.key() == Qt.Key_AsciiTilde): #~ tilde
				currentCopter.emergency_kill()

			else:
				print 'Invalid key!'
		else:
			print 'Invalid copter selected!'

	def close_sitls(self):
		#clean up sitls
		for key in self.vehicleDict.keys():
			v = self.vehicleDict[key]
			if v.connection == None:
				v.close_sitl()
				
	def closeThreads(self):
		print 'returning control'
		for key in self.vehicleDict.keys():
			v = self.vehicleDict[key]
			v.returnControl()
			

	#TODO: Owner to explain why '__del__' was commented out
	'''
	def __del__(self):
		#clean up sitls
		for key in self.vehicleDict.keys():
			v = self.vehicleDict[key]
			v.close_sitl()
	'''

	# Conversion from real life meters to pixels (m -> px)
	# Used to arrange clicked coordinates to be origin-center
	def get_w_from_x(self,x):
		w = float(self.viewArenaXY.width())
		return (self.arena_width/2 + x)/self.arena_width*w

	def get_h_from_y(self,y):
		h = float(self.viewArenaXY.height())
		return (self.arena_length/2 - y)/self.arena_length*h

	def get_h_from_z(self, z):
		return self.viewArenaXZ.height() - (z * self.viewArenaXZ.height() / self.arena_height)

	# Inverse of above two functions (px -> m)    
	def get_x_from_w(self,x):
		w = float(self.viewArenaXY.width())
		return (x/w - 1.0/2.0)*self.arena_width

	def get_y_from_h(self,y):
		h = float(self.viewArenaXY.height())
		return -1 * (y/h - 1.0/2.0)*self.arena_length
		
	#used for XZ plane   
	def get_h_from_z(self, z):
		return self.viewArenaXZ.height() - (z * self.viewArenaXZ.height() / self.arena_height)

	def get_z_from_h(self, h):
		return (self.viewArenaXZ.height() - h) * self.arena_height / float(self.viewArenaXZ.height())
		#return (h - self.viewArenaXZ.height())*self.arena_height/self.viewArenaXZ.height()

	def feetToMeters(self, feet):
		return 0.3048*feet

	def centerObjectOnCoordinate(self, qSceneObject, x0, y0):
		rect = qSceneObject.rect()
		w = rect.width()
		h = rect.height()
		qSceneObject.setPos(x0 - w/2, y0 - h/2)

	def drawFieldXY(self):
		scene = self.viewArenaXY.scene()

		# Get view width and height (GUI Screen)
		w = self.viewArenaXY.width() - 2 # -2 for offset to prevent scene shift in view
		h = self.viewArenaXY.height() - 2 # -2 for offset to prevent scene shift in view

		# Paint Field Zones
		self.fullFieldXY = QRectF(0, 0, w, h)

		# CONFIG: Configure buffer through use of a coefficient multiplier (meters)
		real_buff = 0.5
		real_w = self.arena_width
		real_h = self.arena_length
		w_buff = real_buff / real_w
		h_buff = real_buff / real_h
		self.playField = QRectF(w * w_buff, h * h_buff, w * (1 - 2 * w_buff), h * (1 - 2 * h_buff))

		# Acceptable playing field zone vertices
		self.XYx1, self.XYy1, self.XYx2, self.XYy2 = self.playField.getCoords()
		fXYx1, fXYy1, fXYx2, fXYy2 = self.fullFieldXY.getCoords()
		# self.get_v_from_x(feet)

		# keeperZoneOutter = self.get_w_from_x(self.feetToMeters(42)) #from center
		# keeperZoneInner = self.get_w_from_x(self.feetToMeters(27)) #from center

		# Draw field
		scene.addRect(self.fullFieldXY, QPen(self.color['black']), QBrush(self.color['black']))
		scene.addRect(self.playField, QPen(self.color['light-gray']), QBrush(self.color['black']))



		# Draw keeper zones
		keeperWidth = 10/94.0 * w
		keeperHeight = self.fullFieldXY.height() - 2
		keeperXLeft = 12.5 / 94.0 * w
		keeperXRight =  81.5/ 94.0 * w
		keeperY = self.get_h_from_y(0)
		keeperColor = QColor(255, 255, 255, 20)
		self.centerObjectOnCoordinate(scene.addRect(0, 0, keeperWidth, keeperHeight, QPen(), QBrush(keeperColor)), keeperXLeft, keeperY)
		self.centerObjectOnCoordinate(scene.addRect(0, 0, keeperWidth, keeperHeight, QPen(), QBrush(keeperColor)), keeperXRight, keeperY)

		# TODO: Draw guide lines (by meters)


		# Draw goals
		goalXloc_1 = 10 / 94.0 * w
		goalXloc_2 = 84 / 94.0 * w
		goalYloc = [15 / 50.0 * h,
					25 / 50.0 * h,
					35 / 50.0 * h]
		if self.scaleObjects == True:
			goalShapeH = self.visualScalar * (self.viewArenaXY.height() / self.arena_length) * 0.5842 #23"
			goalShapeW = self.visualScalar * (self.viewArenaXY.height() / self.arena_length) * 0.5842 / 5 # for oval
		else:
			goalShapeH = 40
			goalShapeW = 10
		colorList = [QColor(180, 180, 90), self.color['yellow'], QColor(110, 110, 80)]

		for goalXloc in [goalXloc_1, goalXloc_2]:
			for x in range(3):
				goalPen = QPen(colorList[x])
				goalPen.setWidth(3)
				self.centerObjectOnCoordinate(scene.addEllipse(0,0,goalShapeW, goalShapeH, goalPen, QBrush(QColor(0,0,0,0))), goalXloc, goalYloc[x])
			colorList = list(reversed(colorList))
		# Draw ball drop zone
		dropWidth = 10/94.0 * w # 5' feet from midline
		dropHeight = self.fullFieldXY.height() - 2
		dropX = 47 / 94.0 * w
		dropY = self.get_h_from_y(0)
		self.centerObjectOnCoordinate(scene.addRect(0, 0, dropWidth, dropHeight, QPen(), QBrush(keeperColor)), dropX, dropY)

	def drawFieldXZ(self):
		scene = self.viewArenaXZ.scene()

		# Get view width and height (GUI Screen)
		w = self.viewArenaXZ.width() - 2 # -2 for offset to prevent scene shift in view
		h = self.viewArenaXZ.height() - 2 # -2 for offset to prevent scene shift in view
		self.fullFieldXZ = QRectF(0, 0, w, h)
		scene.addRect(0,0, w, h, QPen(self.color['black']), QBrush(self.color['black']))

		# Draw zones
		keeperWidth = 10/94.0 * w
		keeperHeight = self.fullFieldXZ.height() - 2
		keeperXLeft = 12.5 / 94.0 * w
		keeperXRight =  81.5/ 94.0 * w
		keeperY = self.get_h_from_z(0)
		keeperColor = QColor(255, 255, 255, 20)
		self.centerObjectOnCoordinate(scene.addRect(0, 0, keeperWidth, keeperHeight, QPen(), QBrush(keeperColor)), keeperXLeft, keeperHeight/2)
		self.centerObjectOnCoordinate(scene.addRect(0, 0, keeperWidth, keeperHeight, QPen(), QBrush(keeperColor)), keeperXRight, keeperHeight/2)

		# Draw goals
		goalZloc = [h - (h / self.arena_height * self.feetToMeters(12)),
					h - (h / self.arena_height * self.feetToMeters(15)),
					h - (h / self.arena_height * self.feetToMeters(9))]
		goalXloc_1 = 10 / 94.0 * w
		goalXloc_2 = 84 / 94.0 * w

		if self.scaleObjects == True:
			goalShapeH = self.visualScalar * (self.viewArenaXY.height() / self.arena_length) * 0.5842  # 23"
			goalShapeW = self.visualScalar * (self.viewArenaXY.height() / self.arena_length) * 0.5842 / 5  # for oval
		else:
			goalShapeH = 40
			goalShapeW = 10
		colorList = [QColor(180, 180, 90), self.color['yellow'], QColor(110, 110, 80)]

		for goalXloc in [goalXloc_1, goalXloc_2]:
			for x in range(3):
				goalPen = QPen(colorList[x])
				goalPen.setWidth(3)
				self.centerObjectOnCoordinate(scene.addEllipse(0, 0, goalShapeW, goalShapeH, goalPen, QBrush(QColor(0, 0, 0, 0))), goalXloc, goalZloc[x])
				goalZloc = list(reversed(goalZloc))
				colorList = list(reversed(colorList))


		
		# Draw ball drop zone
		dropZoneWidth = 10/94.0 * w #5' from field midline
		dropZoneHeight = self.fullFieldXZ.height() - 2
		dispenserHeight = dropZoneHeight - self.get_h_from_z(self.feetToMeters(2)) #self.get_h_from_z(self.dispenser_height)
		dropX = 47/94.0 * w
		# TODO: Logic for setting ball drop color via modification of ballDropActive
		ballDropActive = False;
		ballDropColor = QColor(255,0,0,50) if ballDropActive is True else QColor(255,255,255,50)

		self.centerObjectOnCoordinate(scene.addRect(0, 0, dropZoneWidth, dropZoneHeight, QPen(), QBrush(keeperColor)), dropX, keeperHeight/2)
		scene.addRect(0, 0, dropZoneWidth/10, dispenserHeight, QPen(), QBrush(ballDropColor)).setPos((self.fullFieldXZ.width()-dropZoneWidth/10)/2,0) # Zoning out above airspace


		# Draw outer perimeter
		
		
		
		
	   
