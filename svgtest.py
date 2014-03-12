import svg.path
from svg.path import parse_path, Path, Line, QuadraticBezier, Point

path1 = parse_path("m38,57c0,-1 2,-1 7,-1c24,0 34,0 65,0c17,0 32.111298,-0.354958 39,2c5.095642,1.741985 7.486252,3.82375 8,6c0.459503,1.946495 1,7 1,13c0,3 0,14 0,25l0,12l0,10")


distanceTolerance = 0.5

def recursiveBezier(start, cp1, cp2, end):

	print "Recursive Bezier!"

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
		print "\tPoint %s" % str(Point(x=x1234, y=y1234))
	else:
		recursiveBezier(start, Point(x=x12, y=y12), Point(x=x123, y=y123), Point(x=x1234, y=y1234))
		recursiveBezier(Point(x=x1234, y=y1234), Point(x=x234, y=y234), Point(x=x34, y=y34), end)


for item in path1:
	if type(item) == svg.path.path.CubicBezier:
		print "New item: %s" % item
		recursiveBezier(item.start, item.control1, item.control2, item.end)