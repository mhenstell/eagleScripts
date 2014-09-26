import xml.etree.ElementTree as ET
import re

partNamingPattern = re.compile("([A-Z$]*)([0-9]*)")

class Schematic:

	def __init__(self, schematicfile):

		self.schematicfile = schematicfile
		self.name = schematicfile.name

		print "\tParsing Schematic %s" % self.name

		tree = ET.parse(schematicfile)
		root = tree.getroot()
		self.xml = root

		for child in root._children:
			if child.tag == 'drawing':
				self.drawing = Drawing(child)

	def getXMLElement(self):
		return ET.ElementTree(self.xml)

	def renameAllElements(self, postfix):

		print "renaming elements for %s with %s" % (self.name, postfix)

		remapping = {}

		for part in self.drawing.schematic.partsList:
			oldName = part.getName()
			part.setName(part.getName() + "-%s" % postfix)
			remapping[oldName] = part.getName()

		for net in self.drawing.schematic.netList:
			net.setName(net.getName() + "-%s" % postfix)
			net.updatePinRefs(remapping)

		for instance in self.drawing.schematic.instanceList:
			instance.setName(remapping[instance.getName()])

	def appendNewSheet(self, newBoard):

		newSheet = ET.Element("sheet")
		ET.SubElement(newSheet, "plain")

		instances = ET.SubElement(newSheet, "instances")
		nets = ET.SubElement(newSheet, "nets")

		for part in newBoard.drawing.schematic.parts:
			self.drawing.schematic.parts._children.append(part)

		for instance in newBoard.drawing.schematic.instanceList:
			instances._children.append(instance.xml)

		for net in newBoard.drawing.schematic.netList:
			nets._children.append(net.xml)

		for buss in newBoard.drawing.schematic.bussList:
			newSheet._children.append(buss.xml)

		self.drawing.schematic.sheets.append(newSheet)

	def appendLibrary(self, library):
		self.drawing.schematic.libraries._children.append(library)

	def mergeLibraryType(self, newLibrary, libraryType):

		# print "\t\tMerging type %s for library %s" % (libraryType.tag, newLibrary.attrib['name'])

		mainLibrary = [lib for lib in self.drawing.schematic.libraries if lib.attrib['name'] == newLibrary.attrib['name']][0]
		mainLibraryType = [libType for libType in mainLibrary._children if libType.tag == libraryType.tag][0]

		for child in libraryType._children:
			if child.tag != 'deviceset':

				# print "\t\t\tMerging %s %s" % (libraryType.tag, child.attrib['name'])

				# check if the symbol or package is in the main library, if not, append it
				if child.attrib['name'] not in [unit.attrib['name'] for unit in mainLibraryType._children]:
					mainLibraryType._children.append(child)

			else:
				# handle merging of devicesets
				# print "\t\t\tMerging deviceset %s in %s" % (child.attrib['name'], newLibrary.attrib['name'])

				# check if the entire deviceset is missing, if so, append it
				if child.attrib['name'] not in [ds.attrib['name'] for ds in mainLibraryType._children]:
					mainLibraryType._children.append(child)

				else: # the deviceset exists, but we need to make sure it has all the right gate and device entries

					mainLibraryDeviceset = [ds for ds in mainLibraryType._children if ds.attrib['name'] == child.attrib['name']][0]

					for devicesetType in child._children:

						# merge the deviceset gates
						if devicesetType.tag == 'gates':

							gateInsertPoint = [gates for gates in mainLibraryDeviceset if gates.tag == 'gates'][0]
							for gate in devicesetType._children:
								if gate.attrib['symbol'] not in [gate.attrib['symbol'] for gate in gateInsertPoint._children]:
									gateInsertPoint._children.append(gate)
						
						# merge the deviceset devices by name AND package
						elif devicesetType.tag == 'devices':

							devicesInsertPoint = [devices for devices in mainLibraryDeviceset if devices.tag == 'devices'][0]
							for device in devicesetType._children:
								if device.attrib['name'] not in [dv.attrib['name'] for dv in devicesInsertPoint]:
									devicesInsertPoint._children.append(device)
								elif 'package' in device.attrib and device.attrib['package'] not in [dv.attrib['package'] for dv in devicesInsertPoint]:
									devicesInsertPoint._children.append(device)

	def mergeLibraries(self, newBoard):

		# for each library, append the whole library (if it doesn't exist yet in main), or merge each library subtype to make sure we got everything
		for newLibrary in newBoard.drawing.schematic.libraries:

			if newLibrary.attrib['name'] not in [lib.attrib['name'] for lib in self.drawing.schematic.libraries]:
				self.appendLibrary(newLibrary)
			else:

				for libraryType in newLibrary._children:
					self.mergeLibraryType(newLibrary, libraryType)

class Drawing(Schematic):

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
			elif child.tag == 'schematic':
				self.schematic = SchematicBoard(child)

	def getUnits(self):
		return self.grid.attrib['unit']

	def getXMLElement(self):
		
		drawingElement = Element("drawing")
		settingsElement = ET.SubElement(drawingElement, settings.xml)
		gridElement = ET.SubElement(drawingElement, grid.xml)
		layersElement = ET.SubElement(drawingElement, layers.xml)
		boardElement = ET.SubElement(drawingElement, board.xml)

		return drawingElement

class SchematicBoard(Drawing):

	def __init__ (self, schematic):

		self.libraries = ET.Element("libraries")

		for child in schematic._children:

			if child.tag == 'libraries':
				self.libraries = child
			elif child.tag == 'attributes':
				self.attributes = child
			elif child.tag == 'variantdefs':
				self.variantdefs = child
			elif child.tag == 'classes':
				self.classes = child
			elif child.tag == 'parts':
				self.parts = child
			elif child.tag == 'sheets':
				self.sheets = child

		self.partsList = []
		for part in self.parts._children:
			p = Part(part)
			self.partsList.append(p)

		self.netList = []
		for sheet in self.sheets._children:
			for child in sheet._children:
				if child.tag == 'nets':
					for net in child._children:
						self.netList.append(Net(net))

		self.instanceList = []
		for sheet in self.sheets:
			for child in sheet._children:
				if child.tag == 'instances':
					for instance in child._children:
						self.instanceList.append(Instance(instance))

		self.bussList = []
		for sheet in self.sheets._children:
			for child in sheet._children:
				if child.tag == 'busses':
					for buss in child._children:
						self.bussList.append(Buss(buss))


		self.libraryList = []
		self.libraryMap = {}
		for library in self.libraries:
			self.libraryList.append(library)
			self.libraryMap[library.attrib['name']] = library

class Part(SchematicBoard):

	def __init__(self, part):
		self.xml = part

	def getName(self):
		return self.xml.attrib['name']

	def setName(self, name):
		self.xml.attrib['name'] = name

class Instance(SchematicBoard):

	def __init__(self, instance):
		self.xml = instance

	def getName(self):
		return self.xml.attrib['part']

	def setName(self, name):
		self.xml.attrib['part'] = name

class Net(SchematicBoard):

	def __init__(self, net):
		self.xml = net
		self.oldName = self.getName()

	def getName(self):
		return self.xml.attrib['name']

	def setName(self, name):
		self.xml.attrib['name'] = name

	def updatePinRefs(self, mapping):
		for segment in self.xml._children:
			for child in segment._children:
				if child.tag == 'pinref':
					if child.attrib['part'] in mapping:
						child.attrib['part'] = mapping[child.attrib['part']]

class Buss(SchematicBoard):

	def __init__(self, buss):
		self.xml = net

	def getName(self):
		return self.xml.attrib['name']

	def setName(self, name):
		self.xml.attrib['name'] = name
