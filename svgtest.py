import svg.path
from svg.path import parse_path, Path, Line, QuadraticBezier, Point
import sys
from bs4 import BeautifulSoup

# pathStrings = ['M34.719,25.91l5.844,0.268c0,0-5.404,0.68-6.056,0.875c-1.239,3.31-4.899,2.469-6.085,4.057 c-1.866,2.501-5.296,3.35-10.641,1.895c-0.541,0.785-5.931,4.926-7.466,5.426s3.175-3.199,3.175-3.199s-2.259,1.568-3.789,1.974 c-1.528,0.403,4.119-3.855,4.119-3.855s-2.454,1.022-3.782,1.106c-1.33,0.084,2.567-2.4,2.567-2.4s-1.201,0.092-1.656,0.092 s-0.655-0.371,0.973-1.107c1.627-0.736,5.069-2.426,8.245-3.033c0.214-1.105-5.533-9.709-5.212-10.422 c0.321-0.715,3.248-0.465,7.425,4.354c0.393-0.713-0.789-11.315,0.141-10.352c0.929,0.965,4.893,8.889,5.32,14.957 c0.679,0.143,1.94-0.931,3.319-1.571C33.64,23.82,34.719,25.91,34.719,25.91z']

distanceTolerance = 0.25
scale = 1

paths = []
points = []

def recursiveBezier(start, cp1, cp2, end):
	global points
	
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

	if ((d2 + d3) * (d2 + d3) < distanceTolerance * (dx * dx + dy * dy)):
		# print "\tPoint %s" % str(Point(x=x1234, y=y1234))
		point = Point(x=x1234, y=y1234)
		points.append(point)
		# print "Appending %s" % str(Point(x=x1234, y=y1234))
	else:
		recursiveBezier(start, Point(x=x12, y=y12), Point(x=x123, y=y123), Point(x=x1234, y=y1234))
		recursiveBezier(Point(x=x1234, y=y1234), Point(x=x234, y=y234), Point(x=x34, y=y34), end)

def bezier(start, cp1, cp2, end):
	global points
	points.append(start)
	recursiveBezier(start, cp1, cp2, end)
	points.append(end)
	# print start, cp1, cp2, end


#<wire x1="13.97" y1="73.66" x2="31.75" y2="73.66" width="0.4064" layer="29"/>
#<wire x1="31.75" y1="73.66" x2="31.75" y2="55.88" width="0.4064" layer="29"/>

def parse_style(style):
	
	outstyle = dict(item.split(":") for item in style.split(";"))
	return outstyle

def parseXML(filename):

	with open(filename, 'r') as infile:

		xml = infile.read()
		soup = BeautifulSoup(xml)

		paths = []

		layers = soup.find_all('g')
		if len(layers) == 0:
			try:
				path = parse_path(soup.path.attrs['d'])
				paths.append((path, ))
				return paths
			except KeyError, e:
				print "Error: Could not find layers or paths in this SVG file"
				return

		for layer in layers:
			if layer.path and 'd' in layer.path.attrs:
				path = parse_path(layer.path.attrs['d'])

				style = None
				if 'style' in layer.path.attrs:
					style = parse_style(layer.path.attrs['style'])
				paths.append((path, style))

		return paths
		
def generateWires(path, style):
	paths = []
	wires = []

	for item in path:
		if type(item) == svg.path.path.CubicBezier:

			bezier(item.start, item.control1, item.control2, item.end)
			paths.append(points)
			points = []
		elif type(item) == svg.path.path.Line:
			linePoints = [item.start, item.end]
			paths.append(linePoints)
		else:
			print item

	maxX = 0
	maxY = 0

	for path in paths:
		for point in path:
			maxX = max(point.x, maxX)
			maxY = max(point.y, maxY)

	for path in paths:
		for _ in range(0, len(path)-1):

			point = path.pop(0)
			wires.append("""<wire x1="%s" y1="%s" x2="%s" y2="%s" width="0.4064" layer="29"/>\n""" % ((point.x * scale), ((maxY - point.y) * scale), (path[0].x * scale), ((maxY - path[0].y) * scale)))

	return wires

if __name__ == "__main__":

	print "Starting"

	filename = sys.argv[1]
	paths = parseXML(filename)

	out = ""

	for pathPair in paths:
		
		path, style = pathPair

		if style and style['fill'] != 'none':
			generateWires(path, style)
		elif style and style['fill'] != 'none':
			generatePolygon(path, style)
		else:
			print "No style!"
			sys.exit(-1)

		

	


	
			# out += """<wire x1="%s" y1="%s" x2="%s" y2="%s" width="0.4064" layer="29"/>\n""" % (points[1].x, points[1].y, points[2].x, points[2].y)


	with open("outfile.txt", 'w') as f:
		f.write(out)
