class Agent:
	def __init__(self):
		self._namelist = []
	def register(self, name):
		self._namelist.append(name)
	def execute(self, ex, name):
		uri = self.geturi(ex, name)
		ex.seturi(uri)
		self.generate(ex, name)
		ex.conclude()

class Execution:
	def __init__(self):
		self.outfl = None
	def seturi(self, uri):
		self.outfl = open(uri, 'w')
	def write(self, val):
		self.outfl.write(val)
	def conclude(self):
		self.outfl.close()
		self.outfl = None
