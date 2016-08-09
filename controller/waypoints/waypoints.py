class WayPoints():
    def __init__(self, node = None):
        if node != None:
            self.id = None if node.get("id") is None else node.get("id")
            self.type = None if node.find("type") is None else node.find("type").text
            self.x = None if node.find("x") is None else float(node.find("x").text)
            self.y = None if node.find("y") is None else float(node.find("y").text)
            self.z = None if node.find("z") is None else float(node.find("z").text)
            self.heading = None if node.find("heading") is None else float(node.find("heading").text)
        else:
            self.id = None
            self.type = None
            self.x = None
            self.y = None
            self.z = None
            self.heading = None
  
    def setProperties(self, id, type, x, y, z, h):
        self.id = id
        self.type = type
        self.x = x
        self.y = y
        self.z = z
        self.heading = h