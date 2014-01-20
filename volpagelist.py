import sets
import operator

class Volume:
	def __init__(self, arr=None):
		self.extralist = []
		self.chapterlist = []
		self.chapters = {}
		if (arr):
			chaps = [ tup for tup in arr if type(tup) == tuple ]
			for ix in range(len(chaps)-1):
				cname = chaps[ix][0]
				start = chaps[ix][1]
				end = chaps[ix+1][1]-1
				chap = Chapter(cname, start, end)
				chap.fullname = chaps[ix][2]
				self.chapters[cname] = chap
				self.chapterlist.append(cname)
			for val in arr[:-1]:
				if (type(val) == tuple):
					chap = self.chapters.get(val[0])
					self.extralist.append(chap)
				else:
					self.extralist.append(val)

	def __str__(self):
		arr = [ (cname + ' ' + str(self.chapters[cname].range))
			for cname in self.chapterlist ]
		return '[' + ('; '.join(arr)) + ']'
	
	def pagelist(self, *args):
		return Pagelist(volume=self, *args)

	def find(self, val):
		for cname in self.chapterlist:
			(start, end) = self.chapters[cname].range
			if (val >= start and val <= end):
				return cname
		return None

	def labelof(self, cname):
		chap = self.chapters.get(cname)
		if (not chap):
			return None
		return chap.label

	def nameof(self, cname):
		chap = self.chapters.get(cname)
		if (not chap):
			return None
		if (chap.fullname):
			return chap.fullname
		return chap.label

class Chapter:
	def __init__(self, key, start, end):
		self.key = key
		self.range = (start, end)
		self.fullname = None
		self.label = None
		
		val = key
		try:
			val = 'ch' + str(int(key))
		except:
			pass
		self.label = val

	def __repr__(self):
		return '<Chapter \'' + self.key + '\'>'
		
class Pagelist:
	def __init__(self, *args, **dic):
		self.pages = sets.Set()
		self.subpos = {}
		self.volume = dic.get('volume')
		self.frozen = False
		self.displayname = None
		self.firstpage = None
		self.add(*args)

	def add(self, *args):
		self.frozen = False

		if (len(args) == 1 and type(args[0]) == list):
			args = args[0]

		if (len(args) == 1 and isinstance(args[0], Pagelist)):
			self.init_page(args[0])
		elif (len(args) == 1 and type(args[0]) in [str, unicode]):
			self.init_str(args[0])
		elif (reduce(operator.and_, 
			[(type(val) in [int, long, float]) for val in args], 
			True)):
			self.init_list(args)
		else:
			raise ValueError('Pagelist must be created with a string, or a sequence of numbers')

	def init_str(self, st):
		for grp in st.split(','):
			grp = grp.strip()
			startpager = None
			
			if (grp.startswith('c')):
				grp = grp[1:]
				(startpage, endpage) = self.volume.chapters[grp].range
			else:
				if (grp.startswith('p')):
					grp = grp[1:]
				dashpos = grp.find('-', 1)
				endval = None
				if (dashpos >= 0):
					endval = grp[ dashpos+1 : ]
					grp = grp[ : dashpos ]
				startval = grp
	
				if ('.' in startval):
					startpager = float(startval)
					startpage = int(startpager)
				else:
					startpage = int(startval)
	
				if (endval != None):
					if ('.' in endval):
						val = float(endval)
						endpage = int(val)
					else:
						endpage = int(endval)
				else:
					endpage = None

			self.add_el(startpage, startpager)
			if (endpage != None):
				for val in range(startpage+1, endpage+1):
					self.add_el(val)
				
	def init_list(self, args):
		for val in args:
			if (type(val) == float):
				rval = val
				val = int(val)
				self.add_el(val, rval)
			else:
				self.add_el(val)

	def init_page(self, pag):
		for val in pag.pages:
			rval = pag.subpos.get(val)
			self.add_el(val, rval)

	def add_el(self, val, rval=None):
		if (not (val in self.pages)):
			self.pages.add(val)
			if (rval != None):
				self.subpos[val] = rval
		else:
			selfrval = self.subpos.get(val)
			if (rval == None and selfrval != None):
				self.subpos.pop(val)
			elif (rval != None and selfrval != None and rval < selfrval):
				self.subpos[val] = rval

	def __repr__(self):
		ls = list(self.pages)
		ls.sort()
		return '<Pagelist ' + str(ls) + '>'

	def __str__(self):
		if (not self.frozen):
			self.freeze()
		return self.displayname

	def __cmp__(self, other):
		if (type(other) in [int, long, float, str, unicode]):
			other = Pagelist(other, volume=self.volume)
		if ((not self.pages) and (not other.pages)):
			return 0
		if (not self.pages):
			return -1
		if (not other.pages):
			return 1
		selfbeg = self.getstart()
		otherbeg = other.getstart()
		selfrbeg = self.subpos.get(selfbeg, selfbeg)
		otherrbeg = other.subpos.get(otherbeg, otherbeg)
		if (selfrbeg != otherrbeg):
			return cmp(selfrbeg, otherrbeg)
		selfls = list(self.pages)
		selfls.sort()
		otherls = list(other.pages)
		otherls.sort()
		for (selfval, otherval) in zip(selfls, otherls):
			selfrval = self.subpos.get(selfval, selfval)
			otherrval = other.subpos.get(otherval, otherval)
			if (selfrval != otherrval):
				return cmp(selfrval, otherrval)
		return cmp(len(self.pages), len(other.pages))

	def __len__(self):
		return len(self.pages)

	def freeze(self):
		ls = list(self.pages)
		if (not ls):
			self.firstpage = None
			self.displayname = '(none)'
		else:
			ls.sort()
			self.firstpage = ls[0]
			self.lastpage = ls[-1]

			name = 'p'
			rangestart = None
			rangeend = None
			ls.append('#')
			for val in ls:
				if (rangeend != None and val == rangeend+1):
					rangeend = val
					continue
				if (rangestart != None):
					if (name != 'p'):
						name += ', '
					if (rangestart == rangeend):
						name += str(rangestart)
					else:
						name += str(rangestart) + '-' + str(rangeend)
					rangestart = None
					rangeend = None
				rangestart = val
				rangeend = val
			self.displayname = name
			self.chapterlabel = None
			if (self.volume):
				chstart = self.volume.find(self.firstpage)
				chend = self.volume.find(self.lastpage)
				if (chstart or chend):
					if (chstart == chend or (chend == None)):
						self.chapterlabel = ' (' + self.volume.labelof(chstart) + ')'
					else:
						self.chapterlabel = ' (' + self.volume.labelof(chstart) + '-' + chend + ')'
				
		self.frozen = True

	def getstart(self):
		if (not self.frozen):
			self.freeze()
		return self.firstpage
