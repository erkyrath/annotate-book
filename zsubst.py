import string
import re
import types
import sys

TOKGEN = 0
TOKEND = 1
TOKDEF = 2
TOKELSE = 3
TOKCOND = 4

token_regexp = re.compile('[a-zA-Z][a-zA-Z0-9_]*')

def parsestring(str, parent=None):
	z = ZSubst(parent)
	z.initialize(str)
	return z

def parsefile(filename, parent=None):
	file = open(filename, 'r')
	buf = file.read()
	file.close()
	z = ZSubst(parent)
	z.initialize(buf)
	return z

def parsereadable(file, parent=None):
	buf = file.read()
	z = ZSubst(parent)
	z.initialize(buf)
	return z

class ZSubst:
	def __init__(self, parent=None):
		self.dict = {'<$':'<$', '$>':'$>'}
		self.body = []
		self.parent = parent

	def initialize(self, buf):
		arr = self.parse(buf)
		self.build(arr, [0], self.body, 0)
		for ent in self.body:
			if (type(ent) != types.StringType and ent[0]==TOKDEF):
				tokname = ent[1]
				tokval = ent[2]
				newsub = ZSubst(self)
				newsub.body = tokval
				self.dict[tokname] = newsub

	def parse(dummy, buf):
		res = []
		pos = 0
		buflen = len(buf)
		
		while (pos < buflen):
			brace = string.find(buf, '<$', pos)
			if (brace < 0 or brace == buflen-2):
				res.append(buf[pos:])
				pos = buflen
				continue
			if (brace > pos):
				res.append(buf[pos:brace])
			pos = brace+2
			toktype = TOKGEN
			if (buf[pos] == '/'):
				toktype = TOKEND
				pos = pos+1
			elif (buf[pos] == ':'):
				toktype = TOKELSE
				pos = pos+1
			elif (buf[pos] == '#'):
				toktype = TOKDEF
				pos = pos+1
			elif (buf[pos] == '?'):
				toktype = TOKCOND
				pos = pos+1
			elif (buf[pos:pos+3] == '<$>'):
				pos = pos+3
				pair = (TOKGEN, '<$')
				res.append(pair)
				continue
			elif (buf[pos:pos+3] == '>$>'):
				pos = pos+3
				pair = (TOKGEN, '$>')
				res.append(pair)
				continue
			tok = token_regexp.match(buf, pos)
			if (tok == None):
				if (toktype == TOKGEN):
					res.append('<$')
					continue
				tokname = ''
			else:
				tokname = tok.group()
				pos = tok.end()
			pair = (toktype, tokname)
			res.append(pair)
			brace2 = string.find(buf, '$>', pos)
			if (brace2 < 0):
				pos = buflen
				continue
			pos = brace2+2
			
		killnewline = 0
		for ix in range(len(res)):
			ent = res[ix]
			if (type(ent) == types.StringType):
				if (killnewline and ent[0] == '\n'):
					res[ix] = ent[1:]
				killnewline = 0
			else:
				toktype = ent[0]
				if (toktype == TOKGEN):
					killnewline = 0
				else:
					killnewline = 1
		return res

	def build(self, arr, pos, sofar, depth):
		while (pos[0] < len(arr)):
			ent = arr[pos[0]]
			pos[0] = pos[0]+1
			if (type(ent) == types.StringType):
				sofar.append(ent)
				continue
			(toktype, tokname) = ent
			if (toktype == TOKGEN):
				sofar.append(ent)
				continue
			elif (toktype == TOKEND):
				if (depth > 0):
					return TOKEND
				continue
			elif (toktype == TOKELSE):
				if (depth > 0):
					return TOKELSE
				continue
			elif (toktype == TOKDEF):
				subarr = []
				self.build(arr, pos, subarr, depth+1)
				tup = (TOKDEF, tokname, subarr)
				sofar.append(tup)
				continue
			elif (toktype == TOKCOND):
				subarr1 = []
				subarr2 = []
				res = self.build(arr, pos, subarr1, depth+1)
				if (res == TOKELSE):
					self.build(arr, pos, subarr2, depth+1)
				tup = (TOKCOND, tokname, subarr1, subarr2)
				sofar.append(tup)
				continue
			else:
				continue
		return TOKEND

	def getkey(self, env, key):
		while (env != None):
			res = env.get(key)
			if (res != None):
				return res
			env = env.get('__next__')
		zsub = self
		while (zsub != None):
			res = zsub.dict.get(key)
			if (res != None):
				return res
			zsub = zsub.parent
		return None

	def outsequence(self, write, env, arr):
		for ent in arr:
			if (type(ent) == types.StringType):
				write(ent)
				continue
			toktype = ent[0]
			if (toktype == TOKDEF):
				continue
			elif (toktype == TOKGEN):
				tokname = ent[1]
				self.outkey(write, env, tokname)
			elif (toktype == TOKCOND):
				tokname = ent[1]
				if (self.getkey(env, tokname) != None):
					self.outsequence(write, env, ent[2])
				else:
					self.outsequence(write, env, ent[3])

	def outkey(self, write=None, env=None, key=None):
		val = self.getkey(env, key)
		if (val == None):
			write('<$unknown name: ' + key + '$>')
		else:
			if (type(val) == types.StringType
				or type(val) == types.UnicodeType):
				write(val)
			elif (type(val) == types.IntType 
				or type(val) == types.FloatType 
				or type(val) == types.LongType):
				write(str(val))
			elif (isinstance(val, ZSubst)):
				val.out(write, env)
			elif (callable(val)):
				val(self, write, env)
			else:
				write('<$' + repr(val) + '$>')

	def out(self, write=None, env=None):
		if (write == None):
			write = sys.stdout.write
		self.outsequence(write, env, self.body)

