import svg.path
from svg.path import Point
import sys
from bs4 import BeautifulSoup
import random

distanceTolerance = 0.1 	# Our granularity, stops the bezier-to-point calculation at this line length
lineScale = 1 				# Global line scale, multiple for converting SVG dimensions to EAGLE dimensions
strokeScale = 1 			# Multiple for converting SVG path pixel widths to EAGLE mm widths

globalLayer = 16 			# Place all wires and polygons into this EAGLE layer
globalSig = "bird" 			# If this variable exists, all EAGLE signals will be named this (connects all lines/polys as one signal)
signalLayers = [1, 16]		# Signal layers, shouldn't need to change unless you have a custom EAGLE board stackup

				# Global 

# Default path style for lines that don't have an SVG style specified
defaultStyle = {u'opacity': u'1', u'stroke-linejoin': u'miter', u'stroke-opacity': u'1', u'stroke': u'#000000', u'stroke-linecap': u'butt', u'stroke-width': u'1px', u'fill': u'none'}

def recursiveBezier(start, cp1, cp2, end):
	""" Recursively plot the points on a cubic bezier curve 
	down to our distance tolerance
	"""

	# Calculate points on the curve
	x12 = (start.x + cp1.x) / 2
	y12 = (start.y + cp1.y) / 2
	x23 = (cp1.x + cp2.x) / 2
	y23 = (cp1.y + cp2.y) / 2
	x34 = (cp2.x + end.x) / 2
	y34 = (cp2.y + end.y) / 2
	x123 = (x12 + x23) / 2
	y123 = (y12 + y23) / 2
	x234 = (x23 + x34) / 2
	y234 = (y23 + y34) / 2
	x1234 = (x123 + x234) / 2
	y1234 = (y123 + y234) / 2

	dx = end.x - start.x
	dy = end.y - start.y

	d2 = abs(((cp1.x - end.x) * dy - (cp1.y - end.y) * dx))
	d3 = abs(((cp2.x - end.x) * dy - (cp2.y - end.y) * dx))

	# If we're below our distance tolerance (granularity) add the point and break
	if ((d2 + d3) * (d2 + d3) < distanceTolerance * (dx * dx + dy * dy)):
		global points
		point = Point(x=x1234, y=y1234)
		points.append(point)
	else: # We have to go deeper!
		recursiveBezier(start, Point(x=x12, y=y12), Point(x=x123, y=y123), Point(x=x1234, y=y1234))
		recursiveBezier(Point(x=x1234, y=y1234), Point(x=x234, y=y234), Point(x=x34, y=y34), end)

def bezier(start, cp1, cp2, end):
	"""Add the start and end points of a bezier curve
	use recursiveBezier to find all the intermediate points
	bases on the control points
	"""

	global points
	points.append(start)
	recursiveBezier(start, cp1, cp2, end)
	points.append(end)

def parseXMLToLayers(filename):
	"""Parse an SVG file into layers and paths"""

	# Open the SVG file and read it into Beautiful Soup
	with open(filename, 'r') as infile:

		soup = BeautifulSoup(infile.read())

		# Find all layers ('g' tags)
		layers = soup.find_all('g')
		
		# What if the SVG doesn't have any layers? Spit out one layer with the path data.
		if len(layers) == 0:
			try:
				path = svg.path.parse_path(soup.path.attrs['d'])
				parsedPaths.append((path, defaultStyle))
				yield [paths]
			except KeyError, e:
				print "Error: Could not find layers or paths in this SVG file"
				return

		# We have a layered file, yield the layers
		for layer in layers:

			outLayer = {}

			if 'id' in layer.attrs:
				outLayer['id'] = layer.attrs['id']
			if 'style' in layer.attrs:
				outLayer['style'] = layer.attrs['style']

			# Find the path tags
			foundPaths = layer.find_all('path')
			parsedPaths = []

			if len(foundPaths) == 0:
				continue
			
			# Parse the layer paths and styles
			for pathTag in foundPaths:
	
				path = {'path':svg.path.parse_path(pathTag.attrs['d'])}
				if 'id' in pathTag.attrs:
					path['id'] = pathTag.attrs['id']
				style = defaultStyle
				if 'style' in pathTag.attrs:
					style = parse_style(pathTag.attrs['style'])
				path['style'] = style
				parsedPaths.append(path)

			outLayer['paths'] = parsedPaths

			yield outLayer
		return

def parse_style(style):
	"""Parse SVG style into a python dict"""
	
	outstyle = dict(item.split(":") for item in style.split(";"))
	return outstyle

def pathToPointLists(path):
	"""Convert an SVG path to a nested list of cartesian points"""

	for item in path:

		# Only handles cubic bezier and lines for now
		if type(item) == svg.path.path.CubicBezier:
			global points
			bezier(item.start, item.control1, item.control2, item.end)
			outpoints = points
			points = []
			yield outpoints

		# Lines make our job easy
		elif type(item) == svg.path.path.Line:
			linePoints = [item.start, item.end]
			yield linePoints
		else:
			print "Warning: skipping unknown SVG command: %s" % item

	return
		
def generateWires(path):
	"""Generate EAGLE wires based on SVG paths
	Wire output should look like:
	<wire x1="13.97" y1="73.66" x2="31.75" y2="73.66" width="0.4064" layer="29"/>
	"""

	# Skip this path if the opacity is less than zero
	if 'opacity' in path['style'] and float(path['style']['opacity']) < 1:
		print "Skipping line %s with opacity < 1" % path['id']
		return []

	stroke = 0.5 #default mm
	if 'stroke-width' in path['style'] and 'px' in path['style']['stroke-width']:
		stroke = int(path['style']['stroke-width'].replace('px', ''))
	
	width = stroke * strokeScale # Convert SVG pixel line widths to EAGLE mm width

	wires = []
	if globalLayer in signalLayers:
		if globalSig:
			sig = globalSig
		else:
			sig = path['id']
		wires.append("""<signal name="%s">""" % sig)

	for pointList in pathToPointLists(path['path']):
		for _ in range(0, len(pointList)-1):
			point = pointList.pop(0)
			# SVG and EAGLE coordinate spaces are reversed on the Y axis
			# Reflect everything about Y 100 (arbitrary)
			wires.append("""<wire x1="%s" y1="%s" x2="%s" y2="%s" width="%s" layer="%s" id="%s"/>""" % ((point.x * lineScale), ((100 - point.y) * lineScale), (pointList[0].x * lineScale), ((100 - pointList[0].y) * lineScale), width, globalLayer, sig))

	if globalLayer in signalLayers:
		wires.append("""</signal>""")

	return wires

def generatePolygon(path):
	"""Generate EAGLE polygons based on SVG paths
	Output should look like:

	<signal name="TEST">
	<polygon width="0.4064" layer="16">
	<vertex x="8.89" y="82.55"/>
	<vertex x="30.48" y="82.55"/>
	<vertex x="30.48" y="54.61"/>
	<vertex x="8.89" y="54.61"/>
	</polygon>
	"""

	output = []
	width = path['style']['stroke-width']

	# Start the polygon with the SVG path ID as the signal name
	if globalLayer in signalLayers:
		if globalSig:
			sig = globalSig
		else:
			sig = path['id']
		output.append('<signal name="POLY-%s">' % sig)
	output.append('<polygon width="%s" layer="%s">' % (width, globalLayer))

	# Add all the points as EAGLE vertexes
	for pointList in pathToPointLists(path['path']):
		for _ in range(0, len(pointList)-1):
			point = pointList.pop(0)
			output.append("""<vertex x="%s" y="%s"/>""" % (point.x * lineScale, ((100 - point.y) * lineScale)))

	if globalLayer in signalLayers:
		output.append('</polygon></signal>')
	return output

if __name__ == "__main__":

	filename = sys.argv[1]
	print "Parsing %s" % filename

	wireSegments = []	# Holds EAGLE wire definitions
	polygons = []		# Holds EAGLE polygon definitions
	points = []			# Global for holding points for recursive point generation

	# Parse the layers out of our SVG file for processing
	for layer in parseXMLToLayers(filename):

		# Ignore if layer is set to display:none
		if 'style' in layer and layer['style'].split(':')[1] == 'none':
			print "Ignoring invisible layer %s" % layer['id']
			continue
		else:
			print "Processing layer %s" % layer['id']
		
		# Grab the paths in each layer and generate 
		# EAGLE wires or polygons depending on the path style
		for path in layer['paths']:

			# No fill, treat as wires
			if path['style']['fill'] == 'none':
				wireSegments.append(generateWires(path))

			# SVG has a fill, treat as a polygon/ground plane
			elif path['style']['fill'] != 'none':
				polygons.append(generatePolygon(path))

	print "Writing out %s wire segments and %s polygons" % (len(wireSegments), len(polygons))

	# Write out a text file with the EAGLE wires and polygons in separate sections
	# TODO: throw these directly into the EAGLE file without destroying anything
	with open("outfile.txt", 'w') as f:
		f.write("Wires:\n\n")
		
		for segment in wireSegments:
			for wire in segment:
				f.write(wire + "\n")

		f.write("\n\nPolygons:\n")
		
		for polygon in polygons:
			for line in polygon:
				f.write(line + "\n")


