import os
import os.path
import stat
import string
import re
import time
import agent
import zsubst
from volpagelist import *

basedir = './lib'
desturi = './output'

basesrcdir = os.path.join(basedir, 'src')

fl = open(os.path.join(basedir, 'template.zml'))
templatetext = fl.read()
fl.close()

fl = open(os.path.join(basedir, 'event-template.zml'))
eventtemplatetext = fl.read()
fl.close()

fl = open(os.path.join(basedir, 'topbody.zml'))
topbodytext = fl.read()
fl.close()

fl = open(os.path.join(basedir, 'aboutbody.zml'))
aboutbodytext = fl.read()
fl.close()

fl = open(os.path.join(basedir, 'changesbody.zml'))
changesbodytext = fl.read()
fl.close()

fl = open(os.path.join(basedir, 'pagenote.zml'))
pagenotetemplatetext = fl.read()
fl.close()

fl = open(os.path.join(basedir, 'topic.zml'))
topictemplatetext = fl.read()
fl.close()

fl = open(os.path.join(basedir, 'chapterarrow.zml'))
chapterarrowtemplatetext = fl.read()
fl.close()

fl = open(os.path.join(basedir, 'topicarrow.zml'))
topicarrowtemplatetext = fl.read()
fl.close()

template = zsubst.parsestring(templatetext)
eventtemplate = zsubst.parsestring(eventtemplatetext)
topbody = zsubst.parsestring(topbodytext)
aboutbody = zsubst.parsestring(aboutbodytext)
changesbody = zsubst.parsestring(changesbodytext)
pagenotetemplate = zsubst.parsestring(pagenotetemplatetext, template)
chapterarrowtemplate = zsubst.parsestring(chapterarrowtemplatetext, template)
topictemplate = zsubst.parsestring(topictemplatetext, template)
topicarrowtemplate = zsubst.parsestring(topicarrowtemplatetext, template)

pagenotepattern = re.compile('p\\d+')
pagerefpattern = re.compile('[pc]?\\d+')

volume = None
framenames = {}
entities = {}
topics = {}
topiclist = []
pagenotes = {}
pagenotelist = []
refsubsets = []
trytopics = []
chapterdates = {}
updateobj = None

def readframes(fl):
	while (True):
		ln = fl.readline()
		if (not ln):
			break
		ln = ln.strip()
		pos = ln.find(':')
		if (pos >= 0):
			key = ln[:pos].strip()
			val = ln[pos+1:].strip()
			framenames[key] = val

class TopicBreak:
	index = {}
	def __init__(self, letter, nextletter):
		self.letter = letter
		self.nextletter = nextletter
		self.endletter = chr(ord(nextletter)-1)
		self.downlabel = self.letter + '-' + self.endletter
		self.uplabel = self.downlabel.upper()
		TopicBreak.index[letter] = self
		self.topiclist = []
			
def readtopicbreaks(fl):
	global topicbreaks
	ls = []
	while (True):
		ln = fl.readline()
		if (not ln):
			break
		ln = ln.strip()
		if (ln):
			ls.append(ln)
	ls.sort()
	
	ls.append(chr(ord('z')+1))
	topicbreaks = []
	for ix in range(len(ls)-1):
		topicbreaks.append(TopicBreak(ls[ix], ls[ix+1]))
	
def readchapters(fl):
	global volume
	arr = []
	while (True):
		ln = fl.readline()
		if (not ln):
			break
		ln = ln.strip()
		pos = ln.find(':')
		if (pos >= 0):
			chapname = ln[:pos].strip()
			chapstart = ln[pos+1:].strip()
			fullname = None
			pos = chapstart.find(':')
			if (pos >= 0):
				fullname = chapstart[pos+1:].strip()
				chapstart = chapstart[:pos].strip()
			if (fullname):
				pos = fullname.find(':')
				if (pos >= 0):
					chapterdates[chapname] = fullname[pos+1:].strip()
					fullname = fullname[:pos].strip()
			arr.append( (chapname, int(chapstart), fullname) )
		else:
			arr.append(ln)
	volume = Volume(arr)

def readtrytopics(fl):
	global trytopics
	while (True):
		ln = fl.readline()
		if (not ln):
			break
		ln = ln.strip()
		if (ln.startswith('#')):
			continue
		pos = ln.find(':')
		if (pos < 0):
			key = ln
			val = None
		else:
			key = ln[:pos].strip()
			val = ln[pos+1:].strip()
		trytopics.append( (key, val) )

def readfile(fl, key):
	headline = fl.readline()
	if (not headline):
		return

	altlabel = None
	pos = headline.find('{')
	if (pos >= 0):
		pos2 = headline.rfind('}')
		if (pos2 >= 0):
			altlabel = headline[pos+1 : pos2]
			headline = headline[ : pos] + headline[pos2+1 : ]

	props = {}
	while (True):
		pos = headline.find('<')
		if (pos < 0):
			break
		pos2 = headline.find('>')
		if (pos2 >= 0):
			val = headline[pos+1 : pos2]
			headline = headline[ : pos] + headline[pos2+1 : ]
			pos = val.find(':')
			if (pos < 0):
				props[val.strip()] = 'true'
			else:
				props[val[:pos].strip()] = val[pos+1:].strip()
	
	headline = headline.strip()
	if (not headline):
		return
		
	if (pagenotepattern.match(headline)):
		ent = PageNote(key, headline)
		pagenotes[key] = ent
	else:
		ent = Topic(key, headline)
		topics[key] = ent
	entities[key] = ent

	lines = []

	while (1):
		ln = fl.readline()
		if (not ln):
			lines.append('')
			break
		ln = ln.strip()
		if (ln.startswith('::')):
			ln = ln[2:]
			ls = [ el.strip() for el in ln.split(',') ]
			ent.rawrefs.extend(ls)
			continue
		if (ln == ''):
			lines.append('')
		lines.append(ln)

	ent.body = linestohtml(lines, key, ent)
	ent.altlabel = altlabel
	if (props):
		ent.properties.update(props)
		
def readupdates(fl):
	global updateobj
	updateobj = Update()
	
	lines = []

	while (1):
		ln = fl.readline()
		if (not ln):
			lines.append('')
			break
		ln = ln.strip()
		if (ln == ''):
			lines.append('')
		lines.append(ln)

	lines.append('*')
	lastpos = -1
	lasthead = None
	for ix in range(len(lines)):
		ln = lines[ix]
		if (ln.startswith('*')):
			if (lastpos >= 0):
				sublines = lines[ lastpos : ix ]
				key = lasthead[1:].strip()
				date = time.strptime(key, '%m-%d-%Y')
				datestr = time.strftime('%b %d, %Y (%A)', date)
				datestr = datestr.replace(' 0', ' ')
				sect = linestohtml(sublines, updateobj.key, updateobj)
				updateobj.rawdays.append( (key, datestr, sect) )
			lastpos = ix+1
			lasthead = ln

	if (updateobj.rawdays):
		val = updateobj.rawdays[0][1]
		pos = val.find('(')
		if (pos >= 0):
			val = val[:pos].strip()
		updateobj.lastchange = val

def linestohtml(lines, key, ent):
	pos = 0
	literals = []
	reflist = []
	
	while (pos < len(lines)):
		ln = lines[pos]
		if (ln == '<!-->'):
			lines[pos] = '<!--!>'
			lit = []
			pos = pos+1
			while (pos < len(lines)):
				ln = lines[pos]
				if (ln == '<--!>'):
					del lines[pos]
					break
				lit.append(ln)
				del lines[pos]
			lit = string.join(lit, '\n')
			literals.append(lit)
		else:
			pos = pos+1

	inlist = 0
	pos = 0
	while (pos < len(lines)):
		ln = lines[pos]
		if (ln == '---'):
			if (not inlist):
				inlist = 1
				depth = 1
				lines[pos] = '<ul>\n'
			else:
				inlist = 0
				lines[pos] = '</ul>\n'
			continue
		if (not inlist):
			pos = pos+1
			continue
		ix = 0
		while (ln[:2] == '- '):
			ix = ix+1
			ln = ln[2:]
		if (ix == 0):
			pos = pos+1
			continue
		lines[pos] = '<li>' + ln
		if (ix != depth):
			if (ix > depth):
				lines[pos:pos] = ['  <ul>\n']
			else:
				lines[pos:pos] = ['  </ul>\n']
			pos = pos+1
			depth = ix
		pos = pos+1

	pos = 0
	outstack = []
	while (pos < len(lines)):
		ln = lines[pos]
		if (ln.startswith('/--')):
			code = ln[1:].strip('-')
			code = code.strip()
			if (not code):
				inln = '<div class="Quote">\n<p>'
				outln = '</p>\n</div>\n'
			else:
				codename = framenames.get(code)
				if (codename is None):
					print key + ': unknown quote frame: ' + code
					codename = 'XXX'
				inln = '<div class="Frame">'
				inln += '<div class="Frame' + code.upper() + '">\n'
				if (codename):
					inln += '<div class="FrameLabel">' + codename + ':</div>'
				inln += '<p>'
				outln = '</p>\n</div></div>\n'
			lines[pos] = inln
			outstack.append(outln)
		if (ln.startswith('\\--')):
			lines[pos] = outstack.pop()
		pos = pos+1

	if (outstack):
		print key + ': unclosed quote frame'
		
	waspara = False
	pos = 0
	newlines = []
	for ln in lines:
		if (ln != ''):
			if (ln.startswith('<ul') or ln.startswith('<div')):
				if (waspara):
					newlines.append('</p>')
					newlines.append('')
			elif (ln.startswith('|--')):
				if (waspara):
					print 'marker in mid-paragraph:', ln
				else:
					code = ln[1:].strip('-')
					newlines.append('<p class="' + code + '">')
					ln = ''
			else:
				if (not waspara):
					newlines.append('<p>')
			waspara = True
			newlines.append(ln)
			if (ln.startswith('</ul') or ln.startswith('</p>\n</div')):
				waspara = False
		else:
			if (waspara):
				newlines.append('</p>')
				newlines.append('')
				waspara = False

	buf = string.join(newlines, '\n')

	while (1):
		pos = string.find(buf, '*')
		if (pos < 0):
			break
		pos2 = string.find(buf, '*', pos+1)
		if (pos2 < 0):
			break
		buf = buf[:pos] + '<em>' + buf[pos+1:pos2] + '</em>' + buf[pos2+1:]

	while (1):
		pos = string.find(buf, '_')
		if (pos < 0):
			break
		pos2 = string.find(buf, '_', pos+1)
		if (pos2 < 0):
			break
		buf = buf[:pos] + '<em>' + buf[pos+1:pos2] + '</em>' + buf[pos2+1:]

	startpos = 0
	while (1):
		pos = string.find(buf, '[', startpos)
		if (pos < 0):
			break
		pos2 = string.find(buf, ']', pos+1)
		if (pos2 < 0):
			break
		spec = buf[pos+1:pos2]
		if (spec == '('):
			outstr = '['
		elif (spec == ')'):
			outstr = ']'
		elif (spec == '...'):
			outstr = '[...]'
		elif (spec.startswith('|')):
			ext = ' target="_blank"'
			spec = spec[1:]
			if (spec.startswith('+')):
				spec = spec[1:]
				ext = ''
			pos3 = spec.find('|')
			if (pos3 >= 0):
				url = spec[:pos3].strip()
				urllabel = spec[pos3+1:].strip()
			else:
				url = spec.strip()
				urllabel = url
			outstr = '<a' + ext + ' href="' + url + '">' + urllabel + '</a>'
		else:
			link = ent.makelink(spec)
			outstr = '<$$' + link.key + '$$>'
		buf = buf[:pos] + outstr + buf[pos2+1:]
		startpos = pos + len(outstr)

	lit = 0
	while (1):
		pos = string.find(buf, '<!--!>')
		if (pos < 0):
			break
		buf = buf[:pos] + literals[lit] + buf[pos+6:]
		lit = lit+1

	return buf

dehtmldict = {
	'&Eacute;':'&#0201;',
	'&Oacute;':'&#0211;',
	'&aacute;':'&#0225;',
	'&eacute;':'&#0233;',
	'&acirc;':'&#0226;',
	'&ocirc;':'&#0244;',
	'&auml;':'&#0228;',
	'&euml;':'&#0235;',
	'&ouml;':'&#0246;',
	'&uuml;':'&#0252;',
}
def dehtmlentities(val):
	if ('&' in val):
		for key in dehtmldict:
			val = val.replace(key, dehtmldict[key])
	return val

summarizetagpattern = re.compile('<[^>]*>')

def summarize(val):
	val = summarizetagpattern.sub('', val)
	ls = val.split()
	if (len(ls) > 20):
		ls = ls[:20]
		ls.append('...')
	val = ' '.join(ls)
	return val

class Entity:
	def __init__(self, key):
		self.key = key
		self.altlabel = None
		self.rawrefs = []
		self.pagerefs = volume.pagelist()
		self.seealsos = []
		self.linkcount = 0
		self.links = {}
		self.properties = {}

	def makelink(self, spec):
		link = Link(self.linkcount, spec)
		self.linkcount += 1
		self.links[link.key] = link
		return link

	def resolvelinks(self, backlink):
		for linkkey in self.links.keys():
			link = self.links[linkkey]
			target = entities.get(link.destkey)
			if (not target):
				print key + ': link to nonexistent item: ' + link.destkey
				continue
			if (backlink):
				if (link.inserting):
					if (self.istopic()):
						target.seealsos.append(self)
					else:
						target.seealsos.append(self)
						target.pagerefs.add(self.pagelist)
				if (link.imbibe):
					refsubsets.append( (link.imbibe, self, target, link.imbibelinks) )
			label = link.label
			if (not label):
				label = str(target)
			elif (label == '+'):
				label = str(target)
				if (target.altlabel):
					label = label + ' (' + target.altlabel + ')'
			url = target.geturl()
			val = '<a href="' + url + '">' + label + '</a>'
			link.replacement = val

class PageNote(Entity):
	def __init__(self, key, pagestr):
		Entity.__init__(self, key)
		self.pagelist = volume.pagelist(pagestr)
		self.chapter = None

	def __repr__(self):
		return '<PageNote ' + self.key + ': ' + str(self.pagelist) + '>'

	def __str__(self):
		val = self.properties.get('pagenumname')
		if (val):
			return val
		return str(self.pagelist)
		
	def __cmp__(self, other):
		if (isinstance(other, Topic)):
			return 1
		return cmp(self.pagelist, other.pagelist)

	def istopic(self):
		return False
		
	def geturl(self):
		return 'chapter-' + str(self.chapter) + '.html#' + self.key
	
class Topic(Entity):
	def __init__(self, key, title):
		Entity.__init__(self, key)
		self.title = title
		self.lowertitle = title.lower()
		self.topicbreak = None
		
	def __repr__(self):
		return '<Topic ' + self.key + ': "' + self.title + '">'

	def __str__(self):
		return self.title
	
	def __cmp__(self, other):
		if (isinstance(other, PageNote)):
			return -1
		return cmp(self.lowertitle, other.lowertitle)

	def istopic(self):
		return True

	def geturl(self):
		return 'topics-' + self.topicbreak.downlabel + '.html#' + self.key
		
class Update(Entity):
	def __init__(self):
		Entity.__init__(self, '(update)')
		self.rawdays = []
		self.days = []
		self.lastchange = '(no updates)'

class Link:
	def __init__(self, num, spec):
		self.key = str(num)
		self.inserting = False
		self.imbibe = 0
		self.imbibelinks = False
		self.label = None
		if (spec.startswith('::')):
			self.inserting = True
			spec = spec[2:]
		while (spec.startswith('+')):
			self.imbibe += 1
			spec = spec[1:]
		if (spec.startswith('!')):
			self.imbibelinks = True
			spec = spec[1:]
		pos = spec.find('/')
		if (pos >= 0):
			self.label = spec[pos+1:].strip()
			if (not self.label):
				self.label = spec[:pos].strip()
			spec = spec[:pos]
		self.destkey = spec.strip().lower()
		self.replacement = '$$$[' + self.destkey + ']$$$'
	def __repr__(self):
		res = '<Link to \'' + self.destkey + '\''
		if (self.label):
			res += ' "' + self.label + '"'
		res += '>'
		return res

def process():
	global topiclist, pagenotelist
	
	for key in entities.keys():
		ent = entities[key]
		if (ent.istopic()):
			pass
		else:
			ent.chapter = volume.find(ent.pagelist.getstart())
			if (not ent.chapter):
				print key + ': not in chapter: ' + ent.pagelist

	topiclist = topics.values()
	topiclist.sort()
	pagenotelist = pagenotes.values()
	pagenotelist.sort()

	for tbreak in topicbreaks:
		ls = []
		for ent in topiclist:
			val = ent.lowertitle
			if (val >= tbreak.letter and val < tbreak.nextletter):
				ls.append(ent)
		tbreak.topiclist = ls
		for ent in ls:
			ent.topicbreak = tbreak
		
	for key in entities.keys():
		ent = entities[key]
		for val in ent.rawrefs:
			imbibe = 0
			imbibelinks = False
			while (val.startswith('+')):
				imbibe += 1
				val = val[1:]
			if (val.startswith('!')):
				imbibelinks = True
				val = val[1:]
			if (pagerefpattern.match(val)):
				ent.pagerefs.add(val)
			else:
				target = entities.get(val)
				if (not target):
					print key + ': reference does not exist: ' + val
					continue
				if (target.istopic()):
					ent.seealsos.append(target)
				else:
					ent.seealsos.append(target)
					ent.pagerefs.add(target.pagelist)
				if (imbibe):
					refsubsets.append( (imbibe, target, ent, imbibelinks) )

	linkpattern = re.compile('<\\$\\$(\\d+)\\$\\$>')
	
	for key in entities.keys():
		ent = entities[key]
		ent.resolvelinks(True)
		def linkfunc(match):
			linkkey = match.group(1)
			link = ent.links[linkkey]
			return link.replacement
		ent.body = linkpattern.sub(linkfunc, ent.body)

	updateobj.resolvelinks(False)
	def linkfunc(match):
		linkkey = match.group(1)
		link = updateobj.links[linkkey]
		return link.replacement
	for (key, datestr, body) in updateobj.rawdays:
		body = linkpattern.sub(linkfunc, body)
		updateobj.days.append( (key, datestr, body) )

	refsubsets.sort()
	for (val, subent, grpent, imbibelinks) in refsubsets:
		grpent.pagerefs.add(subent.pagerefs)
		if (imbibelinks):
			grpent.seealsos.extend(subent.seealsos)

	for key in entities.keys():
		ent = entities[key]
		dic = dict([ (subent.key, subent) for subent in ent.seealsos ])
		ls = dic.values()
		ls.sort()
		ent.seealsos = ls

def topbreaklist(zsub, write, parentenv):
	entrytemplate = zsub.getkey(parentenv, 'topicline')
	parentbreak = zsub.getkey(parentenv, 'topicbreak')
	for tbreak in topicbreaks:
		env = {}
		env['breakkey'] = tbreak.downlabel
		env['breaklabel'] = tbreak.uplabel
		ix = topicbreaks.index(tbreak)
		if (ix > 0):
			env['breakprev'] = topicbreaks[ix-1]
		if (ix+1 < len(topicbreaks)):
			env['breaknext'] = topicbreaks[ix+1]
		if (tbreak == parentbreak):
			env['matchparent'] = parentbreak
		entrytemplate.out(write, env)
		
def topchapterlist(zsub, write, parentenv):
	entrytemplate = zsub.getkey(parentenv, 'chapterline')
	parttemplate = zsub.getkey(parentenv, 'partline')
	for val in volume.extralist:
		if (isinstance(val, Chapter)):
			ch = val.key
			env = {}
			env['chapterkey'] = ch
			env['chaptername'] = volume.nameof(ch)
			(env['chapterstart'], env['chapterend']) = volume.chapters.get(ch).range
			if (env['chapterstart']):
				env['nonintro'] = True
			entrytemplate.out(write, env)
		else:
			env = {}
			env['partname'] = val
			parttemplate.out(write, env)

def toptrylist(*args):
	toptopiclist(trytopics, ',', *args)

def toptopiclist(ls, separator, zsub, write, parentenv):
	entrytemplate = zsub.getkey(parentenv, 'bookmarkline')
	sep = ''
	for (val, label) in ls:
		ent = entities.get(val)
		env = {}
		env['key'] = ent.key
		env['url'] = ent.geturl()
		if (not label):
			label = ent.title.lower()
		env['label'] = label
		env['separator'] = sep
		sep = separator
		entrytemplate.out(write, env)

def chapternotelist(zsub, write, parentenv):
	chap = parentenv['chapterobj']
	ls = [ ent for ent in pagenotelist if (ent.chapter == chap.key) ]
	for ent in ls:
		env = {}
		env['key'] = ent.key
		env['page'] = str(ent)
		env['entrybody'] = ent.body
		if (len(ent.pagerefs)):
			env['refpages'] = str(ent.pagerefs)
		if (len(ent.seealsos)):
			env['topiclist'] = ent.seealsos
			env['reftopics'] = topicreflist
		pagenotetemplate.out(write, env)

def topicpagelist(zsub, write, parentenv):
	tbreak = parentenv['topicbreak']
	for ent in tbreak.topiclist:
		env = {}
		env['key'] = ent.key
		env['title'] = ent.title
		env['entrybody'] = ent.body
		if (len(ent.pagerefs)):
			env['refpages'] = str(ent.pagerefs)
		if (len(ent.seealsos)):
			env['topiclist'] = ent.seealsos
			env['reftopics'] = topicreflist
		if (ent.properties.get('seenoalso')):
			env['seenoalso'] = True
		topictemplate.out(write, env)

def topicreflist(zsub, write, parentenv):
	ls = parentenv['topiclist']
	first = True
	for ent in ls:
		if (first):
			first = False
		else:
			write(',\n')
		write('<a href="')
		write(ent.geturl())
		write('">')
		if (ent.istopic()):
			write(ent.title)
		else:
			write(str(ent.pagelist))
		if (ent.altlabel):
			write(' (')
			write(ent.altlabel)
			write(')')
		write('</a>')

def evententrylist(zsub, write, parentenv):
	entrytemplate = zsub.getkey(parentenv, 'entryline')
	for ent in pagenotelist:
		plot = ent.properties.get('plot')
		if (not plot):
			continue
		env = {}
		env['key'] = ent.key
		env['page'] = ent.pagelist.getstart()
		if (ent.altlabel):
			label = ent.altlabel
		else:
			label = str(ent)
		if (plot != 'true'):
			label = plot
		label = dehtmlentities(label)
		env['label'] = label
		env['url'] = ent.geturl()
		body = summarize(ent.body)
		env['body'] = dehtmlentities(body)
		entrytemplate.out(write, env)
		
def changeslist(zsub, write, parentenv):
	entrytemplate = zsub.getkey(parentenv, 'day')
	for (key, datestr, body) in updateobj.days:
		env = {}
		env['date'] = datestr
		env['body'] = body
		entrytemplate.out(write, env)

class ThisAgent(agent.Agent):

	def startup(self):
		self.register('index')
		self.register('about')
		self.register('changes')
		self.register('css')
		
		filename = os.path.join(basedir, 'chapters')
		fl = open(filename, 'r')
		readchapters(fl)
		fl.close()

		for ch in volume.chapterlist:
			self.register('ch-'+ch)
		
		filename = os.path.join(basedir, 'frames')
		fl = open(filename, 'r')
		readframes(fl)
		fl.close()
				
		filename = os.path.join(basedir, 'topics')
		fl = open(filename, 'r')
		readtopicbreaks(fl)
		fl.close()

		filename = os.path.join(basedir, 'trytopics')
		fl = open(filename, 'r')
		readtrytopics(fl)
		fl.close()

		for tbreak in topicbreaks:
			self.register('topics-'+tbreak.letter)
		
		srclist = os.listdir(basesrcdir)
		for key in srclist:
			if (key[-1] == '~'):
				continue
			filename = os.path.join(basesrcdir, key)
			fl = open(filename, 'r')
			readfile(fl, key)
			fl.close()

		filename = os.path.join(basedir, 'updates')
		fl = open(filename, 'r')
		readupdates(fl)
		fl.close()

		process()

	def geturi(self, ex, name):
		if (name == 'index'):
			return os.path.join(desturi, 'index.html')
		if (name == 'about'):
			return os.path.join(desturi, 'about.html')
		if (name == 'changes'):
			return os.path.join(desturi, 'changes.html')
		if (name == 'css'):
			return os.path.join(desturi, 'all.css')
		if (name.startswith('topics-')):
			ch = name[7:]
			tbreak = TopicBreak.index[ch]
			return os.path.join(desturi, 'topics-'+tbreak.downlabel+'.html')
		if (name.startswith('ch-')):
			ch = name[3:]
			return os.path.join(desturi, 'chapter-'+ch+'.html')
	
	def generate(self, ex, name):
		if (name == 'index'):
			env = {}
			env['docid'] = name
			env['body'] = topbody
			env['chapterlist'] = topchapterlist
			env['topicbreaklist'] = topbreaklist
			env['trytopics'] = toptrylist
			env['lastchange'] = updateobj.lastchange
			template.out(ex.write, env)
		if (name == 'about'):
			env = {}
			env['docid'] = name
			env['body'] = aboutbody
			env['pagetitle'] = 'About This Work'
			template.out(ex.write, env)
		if (name == 'changes'):
			env = {}
			env['docid'] = name
			env['body'] = changesbody
			env['pagetitle'] = 'Recent Updates'
			env['changes'] = changeslist
			template.out(ex.write, env)
		if (name == 'css'):
			fl = open(os.path.join(basedir, 'all.css'))
			dat = fl.read()
			fl.close()
			ex.write(dat)
		if (name.startswith('topics-')):
			ch = name[7:]
			tbreak = TopicBreak.index[ch]
			env = {}
			env['docid'] = name
			env['body'] = topicpagelist
			env['pagetitle'] = 'Index (' + tbreak.uplabel + ')'
			env['topicbreak'] = tbreak
			env['topicline'] = topicarrowtemplate
			env['headfoot'] = topbreaklist
			template.out(ex.write, env)
		if (name.startswith('ch-')):
			ch = name[3:]
			chap = volume.chapters.get(ch)
			env = {}
			env['docid'] = name
			env['subject'] = volume.nameof(ch)
			val = chapterdates.get(chap.key)
			if (val):
				env['subsubject'] = '[' + val + ']'
			env['pagetitle'] = volume.nameof(ch)
			env['body'] = chapternotelist
			env['chapterobj'] = chap
			ix = volume.chapterlist.index(ch)
			if (ix > 0):
				env['chapterprev'] = volume.chapterlist[ix-1]
			if (ix+1 < len(volume.chapterlist)):
				env['chapternext'] = volume.chapterlist[ix+1]
			env['headfoot'] = chapterarrowtemplate
			template.out(ex.write, env)
	
ag = ThisAgent()

if __name__ == "__main__":
		ag.startup()
		for name in ag._namelist:
				print 'zont: generating', name
				ex = agent.Execution()
				ag.execute(ex, name)

