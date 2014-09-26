from EagleLayout import Layout
from EagleSchematic import Schematic
import xml.etree.ElementTree as ET
import sys

boardList = []
boardFileList = []
schematicFileList = []

#Does not support holes??

if __name__ == "__main__":

	# Assemble the board list from the arguments
	for item in sys.argv[1:-1]:
		boardList.append(item)

	for item in boardList:
		boardFileList.append(open("%s.brd" % item, 'r'))
		schematicFileList.append(open("%s.sch" % item, 'r'))


	outfile = sys.argv[-1]

	outBrd = open("%s.brd" % outfile, 'w')
	outSch = open("%s.sch" % outfile, 'w')

	# First board in the list is our master board

	print "Master Board:"
	masterBoard = Layout(boardFileList[0])

	print "Master Schematic:"
	masterSchematic = Schematic(schematicFileList[0])

	print "The Rest:"

	for boardNum in range(1, len(boardList)):

		subBoard = Layout(boardFileList[boardNum])
		subSch = Schematic(schematicFileList[boardNum])

		subSch.renameAllElements(boardNum)
		subBoard.renameAllElements(boardNum)

		bounds = masterBoard.getOuterBounds()
		if bounds is not None:
			subBoard.transpose((bounds[0] + 10, 0))

		masterBoard.append(subBoard)
		masterSchematic.appendNewSheet(subSch)
		masterSchematic.mergeLibraries(subSch)



	# Write out the master board
	masterBoard.getXMLElement().write(outBrd)
	masterSchematic.getXMLElement().write(outSch)


	# Close the open files
	for item in boardFileList:
		item.close()
	for item in schematicFileList:
		item.close()
	outBrd.close()
	outSch.close()
