class Platoon:
    def __init__(self):
        self.copterDict = {}    # dictionary of all copters (key is slot #, entry is copter)
        self.offsetDict = {}    # dictionary of all offsets (key is slot #, entry is offset)
        self.leader = None

    def addCopter(self, copter):
        """
            Adds a copter to the Platoon
        """
        # If no copters are in the platoon, make the first the leader
        if len(self.copterDict) == 0 or self.leader == None: 
            self.leader = copter
            
        self.copterDict[copter.slot] = copter       
        
        self.offsetDict[copter.slot] = copter.location - self.leader.location
        
    #REQUIRES:  slot of copter to be removed
    #MODIFIES:  self.copterDict, self.leader
    #EFFECTS:   removed the copter in selected slot from the platoon. assigns a random leader if the removed copter was the leader
    def removeCopter(self, slot):
        if slot in self.copterDict.keys():
            del self.copterDict[slot]
        else:
            print 'Invalid copter, cannot be deleted from platoon'
            return
        
        if self.leader.slot == slot:
            #assign new leader
            self.leader = None
            for key in self.copterDict.keys():
                self.leader = self.copterDict[key]
                break
            #assign new offsets
            self.offsetDict.clear()
            for key in self.copterDict.keys():
                self.offsetDict[key] = self.copterDict[key].location - self.leader.location
            
            
    #REQUIRES:  slot of copter to be checked
    #MODIFIES:  N/A
    #EFFECTS:   returns true if the platoon has the copter with slot 'slot', false otherwise
    def hasCopter(self, slot):
        if slot in self.copterDict.keys():
            return True
        return False
    
    #REQUIRES:  N/A
    #MODIFIES:  N/A
    #EFFECTS:   returns the size of the platoon
    def size(self):
        return len(self.copterDict)
    
    #REQUIRES:  N/A
    #MODIFIES:  self.copterDict, self.offsetDict, self.leader
    #EFFECTS:   clears the platoon
    def clear(self):
        self.copterDict.clear()
        self.offsetDict.clear()
        self.leader = None

    def move(self, dx, dy, dz, v=None):
        """
            Moves all copters by dx, dy and dz with velocity v
        """
        inc_x = self.leader.location.x + dx
        inc_y = self.leader.location.y + dy
        inc_z = self.leader.location.z + dz

        for copterSlot in self.copterDict:
            copter = self.copterDict[copterSlot]
            offsetPt = self.offsetDict[copterSlot]
            x = offsetPt.x + inc_x
            y = offsetPt.y + inc_y
            z = offsetPt.z + inc_z
            copter.goto(x, y, z, v)

    def goto(self, goal_x, goal_y, goal_z, v=None):
        """
            Sends leader to goal_x, goal_y, and goal_z with velocity, v
            All other copters maintain the same relative position to the leader
        """
        for copterSlot in self.copterDict:
            copter = self.copterDict[copterSlot]
            offsetPt = self.offsetDict[copterSlot]
            x = offsetPt.x + goal_x
            y = offsetPt.y + goal_y
            z = offsetPt.z + goal_z
            copter.goto(x, y, z, v)
            
    def gotoWaypoint (self, waypoint, v = None):
        goal_x = waypoint.x
        goal_y = waypoint.y
        goal_z = waypoint.z
        goal_h = waypoint.heading
        
        for copterSlot in self.copterDict:
            copter = self.copterDict[copterSlot]
            offsetPt = self.offsetDict[copterSlot]
            x = offsetPt.x + goal_x
            y = offsetPt.y + goal_y
            z = offsetPt.z + goal_z
            copter.goto(x, y, z, v)
            copter.rotate(goal_h)

    def rotateRight(self, deg):
        """
            Rotates all copters Right by deg 
        """
        for copterSlot in self.copterDict:
            copter = self.copterDict[copterSlot]
            copter.rotateRight(deg)

    def rotateLeft(self, deg):
        """
            Rotates all copters left by deg 
        """
        for copterSlot in self.copterDict:
            copter = self.copterDict[copterSlot]
            copter.rotateLeft(deg)

    def rotate(self, deg):
        """
            Rotates all copters to face heading, deg.
        """
        for copterSlot in self.copterDict:
            copter = self.copterDict[copterSlot]
            copter.rotate(deg)

    def stop(self):
        """
            Stops all copters in formation
        """
        for copterSlot in self.copterDict:
            copter = self.copterDict[copterSlot]
            copter.holdPosition()

    '''
    def move(self):
        """
            
        """
    '''