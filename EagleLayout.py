import xml.etree.ElementTree as ET
import re

elementNamingPattern = re.compile("([A-Z$_-]*)([0-9]*)")

class Layout:

	def __init__(self, boardfile):

		self.boardfile = boardfile
		self.name = boardfile.name

		print "\tParsing board %s" % self.name


		tree = ET.parse(boardfile)
		root = tree.getroot()
		self.xml = root

		for child in root._children:
			if child.tag == 'drawing':
				self.drawing = Drawing(child)

	def getXMLElement(self):
		return ET.ElementTree(self.xml)

	def renameAllElements(self, postfix):

		mapping = {}

		for element in self.drawing.board.elementList:
			oldName = element.getName()
			element.setName(element.getName() + "-%s" % postfix)
			mapping[oldName] = element.getName()

		for signal in self.drawing.board.signalList:
			# print "Remapping signal %s to %s" % (signal.getName(), signal.getName() + "-%s" % postfix)
			signal.setName(signal.getName() + "-%s" % postfix)
			signal.remapContactRefs(mapping)


	def append(self, newBoard):
		print "\tAppending %s" % newBoard.name

		# TODO layers, settings, grid, variantdefs, classes, designrules, autorouter are not merged

		# Append elements
		for element in newBoard.drawing.board.elements:
			self.drawing.board.elements._children.append(element)

		# Append signals
		for signal in newBoard.drawing.board.signals:
			self.drawing.board.signals._children.append(signal)

		# Append dimension layer
		for entry in newBoard.drawing.board.plain:
			self.drawing.board.plain._children.append(entry)

		# Reconcile the libraries/packages
		libraryList = {}
		for library in self.drawing.board.libraries:
			entry = []

			for child in library._children:
				if child.tag == 'description': entry.append("description")
				elif child.tag == 'packages':
					for package in child._children:
						entry.append(package.attrib['name'])

			libraryList[library.attrib['name']] = entry

		for library in newBoard.drawing.board.libraries:

			if library.attrib['name'] not in libraryList:
				# print "\tWARNING: Library %s does not exist in masterBoard" % library.attrib['name']
				self.drawing.board.libraries._children.append(library)

			else:
				for child in library._children:
					if child.tag == 'packages':
						for package in child._children:
							if package.attrib['name'] not in libraryList[library.attrib['name']]:
								# print "\tWARNING: Package %s does not exist in masterBoard library %s" % (package.attrib['name'], library.attrib['name'])
								for mainLib in self.drawing.board.libraries:
									if mainLib.attrib['name'] == library.attrib['name']:
										for child in mainLib._children:
											if child.tag == 'packages':
												child._children.append(package)
								
	def transpose(self, (x, y)):
		print "\tTransposing %s by (%s, %s)" % (self.name, x, y)
		self.drawing.board.transpose((x, y))

	def getOuterBounds(self):
		# self.drawing.board.generatePlainList() #Necessary?
		return self.drawing.board.getDimensions()

class Drawing(Layout):

	def __init__(self, drawing):
		self.xml = drawing
		for child in drawing._children:
			if child.tag == 'settings':
				# self.settings = Settings(child)
				self.settings = child
			elif child.tag == 'grid':
				# self.grid == Grid(child)
				self.grid = child
			elif child.tag == 'layers':
				# self.layers = Layers(child)
				self.layers = child
			elif child.tag == 'board':
				self.board = Board(child)

	def getUnits(self):
		return self.grid.attrib['unit']

	def getXMLElement(self):
		
		drawingElement = Element("drawing")
		settingsElement = ET.SubElement(drawingElement, settings.xml)
		gridElement = ET.SubElement(drawingElement, grid.xml)
		layersElement = ET.SubElement(drawingElement, layers.xml)
		boardElement = ET.SubElement(drawingElement, board.xml)

		return drawingElement

class Board(Drawing):

	def __init__(self, board):
		self.xml = board
		self.elementList = []
		self.signalList = []
		self.plainList = []
		self.plain = None

		for child in board._children:
			if child.tag == 'plain':
				self.plain = child
			elif child.tag == 'libraries':
				self.libraries = child
			elif child.tag == 'attributes':
				self.attributes = child
			elif child.tag == 'variantdefs':
				self.variantdefs = child
			elif child.tag == 'classes':
				self.classes = child
			elif child.tag == 'designrules':
				self.designrules = child
			elif child.tag == 'autorouter':
				self.autorouter = child
			elif child.tag == 'elements':
				self.elements = child
			elif child.tag == 'signals':
				self.signals = child

		self.elementList = []
		for element in self.elements._children:
			el = Element(element)
			self.elementList.append(el)

		self.signalList = []
		for signal in self.signals._children:
			self.signalList.append(Signal(signal))

		if self.plain == None:
			plain = ET.Element("plain")
			self.plain = plain
			self.xml._children.append(self.plain)

	def transposeElementPositions(self, (x, y)):
		for element in self.elementList:
			element.transposePosition((x, y))

	def transposeSignalPositions(self, (x, y)):
		for signal in self.signalList:
			signal.transposePosition((x, y))

	def transposePlainPositions(self, (x, y)):
		for child in self.plain._children:
			self.plainList.append(Plain(child))

		for entry in self.plainList:
			entry.transposePosition((x, y))

	def transpose(self, (x, y)):
		self.transposeElementPositions((x, y))
		self.transposeSignalPositions((x, y))
		self.transposePlainPositions((x, y))

	def getDimensions(self):
		maxX = 0.0
		maxY = 0.0

		for child in self.plain._children:
			if child.tag == 'wire':
				if float(child.attrib['x1']) > maxX: maxX = float(child.attrib['x1'])
				if float(child.attrib['x2']) > maxX: maxX = float(child.attrib['x2'])
				if float(child.attrib['y1']) > maxY: maxY = float(child.attrib['y1'])
				if float(child.attrib['y2']) > maxY: maxY = float(child.attrib['y2'])

		if maxX == 0.0 and maxY == 0.0:
			return None
		return (maxX, maxY)

class Element(Board):

	def __init__(self, element):
		self.xml = element

	def getName(self):
		return self.xml.attrib['name']

	def setName(self, name):
		self.xml.attrib['name'] = name

	def getPosition(self):
		x = self.xml.attrib['x']
		y = self.xml.attrib['y']
		return (float(x), float(y))

	def transposePosition(self, (x, y)):
		self.xml.attrib['x'] = str(float(self.xml.attrib['x']) + float(x))
		self.xml.attrib['y'] = str(float(self.xml.attrib['y']) + float(y))

		for child in self.xml._children:
			child.attrib['x'] = str(float(child.attrib['x']) + float(x))
			child.attrib['y'] = str(float(child.attrib['y']) + float(y))

class Signal(Board):

	def __init__(self, signal):
		self.xml = signal

	def getName(self):
		return self.xml.attrib['name']

	def setName(self, name):
		self.xml.attrib['name'] = name

	def transposePosition(self, (x, y)):

		wires = []
		vias = []
		polygons = []

		for child in self.xml._children:
			if child.tag == 'wire':
				wires.append(child)
			elif child.tag == 'via':
				vias.append(child)
			elif child.tag == 'polygon':
				polygons.append(child)

		for wire in wires:
			wire.attrib['x1'] = str(float(wire.attrib['x1']) + float(x))
			wire.attrib['x2'] = str(float(wire.attrib['x2']) + float(x))
			wire.attrib['y1'] = str(float(wire.attrib['y1']) + float(y))
			wire.attrib['y2'] = str(float(wire.attrib['y2']) + float(y))

		for via in vias:
			via.attrib['x'] = str(float(via.attrib['x']) + float(x))
			via.attrib['y'] = str(float(via.attrib['y']) + float(y))
			# print "\t" + wire.attrib['x1']

		for polygon in polygons:
			for vertex in polygon._children:
				vertex.attrib['x'] = str(float(vertex.attrib['x']) + float(x))
				vertex.attrib['y'] = str(float(vertex.attrib['y']) + float(y))

	def remapContactRefs(self, mapping):

		for child in self.xml._children:
			if child.tag == 'contactref':
				# print "renaming %s to %s" % (child.attrib['element'], mapping[child.attrib['element']])
				child.attrib['element'] = mapping[child.attrib['element']]

class Plain(Board):

	def __init__(self, entry):
		self.xml = entry

	def getType(self):
		return self.xml.tag 

	def transposePosition(self, (x, y)):
		if self.getType() == 'text' or self.getType() == 'circle':
			self.xml.attrib['x'] = str(float(self.xml.attrib['x']) + float(x))
			self.xml.attrib['y'] = str(float(self.xml.attrib['y']) + float(y))
		elif self.getType() == 'wire' or self.getType() == 'rectangle':
			self.xml.attrib['x1'] = str(float(self.xml.attrib['x1']) + float(x))
			self.xml.attrib['x2'] = str(float(self.xml.attrib['x2']) + float(x))
			self.xml.attrib['y1'] = str(float(self.xml.attrib['y1']) + float(y))
			self.xml.attrib['y2'] = str(float(self.xml.attrib['y2']) + float(y))