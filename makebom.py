from EagleSchematic import Schematic
import xml.etree.ElementTree as ET
import sys
import sqlite3
import xlsxwriter
import json
from datetime import date

def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

parts = {}

class Part(object):

	def __init__(self, part):

		self.partno = None
		self.value = part.getValue()
		self.ref = part.getName()

		if len(part.xml._children) > 0:
			for child in part.xml._children:
				if child.attrib['name'] == 'PARTNO':
					self.partno = child.attrib['value']

class Bom(object):

	def __init__(self, filename, quantity):
		print "Creating BOM for %s" % filename
		self.schematicFilename = filename
		self.parts = {}
		self.dbParts = {}
		self.quantity = int(quantity)

		self.assemble()

	def assemble(self):
		self.gatherPartsFromSchematic()
		self.gatherPartsFromDatabase()
		# self.gatherPricingInfo()

	def gatherPartsFromSchematic(self):
		print "Assembling parts from schematic file"

		with open(self.schematicFilename, 'r') as schFile:
			schematic = Schematic(schFile)

			for schematicPart in schematic.drawing.schematic.partsList:

				part = Part(schematicPart)
				if part.partno is not None:
					if part.partno not in self.parts:
						self.parts[part.partno] = [part]
					else:
						self.parts[part.partno].append(part)
		
	def gatherPartsFromDatabase(self):
		print "Gathering part matches from the database"

		with sqlite3.connect('../control-surface/pcb/database.db') as conn:
			conn.row_factory = dict_factory
			cur = conn.cursor()

			for part in self.parts:
				sql = "select pkg_code, mfg_name, vendor, sku, description, pricing, fee, packaging from parts where mfg_part_num = '%s'" % part
				cur.execute(sql)
				results = cur.fetchall()
				self.dbParts[part] = []

				for result in results:
					self.dbParts[part].append(result)

	def getPricing(self, part, neededQty):
		output = []

		# print "\tGetting pricing for %s" % part['sku']

		if part['pricing'] is not None and 'USD' in part['pricing']:
				
			pricing = json.loads(part['pricing'])['USD']
			fee = part['fee']
			if fee is None: fee = 0


			levels = []
			for level in pricing:
				levels.append(level[0])

			for levelNum in range(0, len(levels) - 1):
				if levels[levelNum] <= neededQty <= levels[levelNum+1]:

					# Now at the minimum level
					unitPrice = float(pricing[levelNum][1])
					neededPrice = ((neededQty * unitPrice) + fee)
					
					nextQtyPrice = None
					nextLevelQty = None
					if levelNum < len(levels) - 1:
						nextLevelQty = pricing[levelNum + 1][0]
						nextLevelUnitPrice = float(pricing[levelNum + 1][1])
						nextQtyPrice = (nextLevelQty * nextLevelUnitPrice) + fee
					
					if part['packaging'] != "Tape & Reel":
						# print "Adding needed qty %s at level qty %s price %s" % (neededQty, pricing[levelNum][0], unitPrice)
						output.append((neededQty, neededPrice))

					if nextLevelQty:
						# print "Adding next level qty %s price %s" % (nextLevelQty, nextLevelUnitPrice)
						output.append((nextLevelQty, nextQtyPrice))

				elif levels[0] >= neededQty and len(output) == 0:
					levelQty = pricing[0][0]
					levelUnitPrice = float(pricing[0][1])
					levelPrice = (levelQty * levelUnitPrice) + fee
					output.append((levelQty, levelPrice))

			if len(output) == 0:
				levelQty = pricing[-1][0]
				levelUnitPrice = float(pricing[-1][1])
				if part['packaging'] == "Tape & Reel":
					levelPrice = ((levelQty * levelUnitPrice) + fee)
				else:
					levelPrice = ((neededQty * levelUnitPrice) + fee)

				output.append((neededQty, levelPrice))

		return output

	def addAssemblyToDatabase(self):

		with sqlite3.connect('../control-surface/pcb/database.db') as conn:
			conn.row_factory = dict_factory
			cur = conn.cursor()

			sql = "select max(num) from assemblies"
			cur.execute(sql)
			assembly_num = int(cur.fetchone()['max(num)']) + 1

			datestamp = format(date.today(), "%m/%d/%Y")
			sql = "insert into assemblies (num, name, version, date, assembly_units) values (%s, '%s', %s, '%s', %s)" % (assembly_num, self.schematicFilename, "NULL", datestamp, self.quantity)
			# cur.execute(sql)
			print sql

			print "Inserted data for Assembly # %s" % assembly_num
			return assembly_num

	def selectSKUs(self):

		print
		print "There are %s part numbers that need SKU selection" % len(self.parts)

		partChoices = {}

		for mfg_part in self.parts:

				neededQty = len(self.parts[mfg_part]) * self.quantity

				print
				print "Part %s is available in the following forms:" % mfg_part

				partNum = 0
				partOptions = []

				if len(self.dbParts[mfg_part]) == 0:
					print 
					print "Error: did not find any parts in the database for %s" % mfg_part
					print
				elif len(self.dbParts[mfg_part]) == 1:
					partChoices[mfg_part] = (neededQty, self.dbParts[mfg_part][0])
					continue

				for part in self.dbParts[mfg_part]:

					print "\t %s %s %s %s" % (neededQty, part['vendor'], part['sku'], part['packaging'])
					pricing = self.getPricing(part, neededQty)
					
					for level in pricing:
						qty = level[0]
						price = level[1]
						print "\t\t (%s) %s %s" % (partNum, qty, price)
						partOptions.append((qty, part))
						partNum += 1

				num = raw_input("\nSelect a line number: ")
				if num == 'q' or num == 'Q':
					return partChoices
				num = int(num)

				partChoices[mfg_part] = partOptions[num]
		
		return partChoices

	def getPartNumForSku(self, sku):
		with sqlite3.connect('../control-surface/pcb/database.db') as conn:
			cur = conn.cursor()
			print sku
			sql = "select part_num from parts where sku == '%s'" % sku
			cur.execute(sql)
			result = cur.fetchone()
			if result is not None:
				return result[0]

	def addSkusToDatabase(self, assemblyNum, partChoices):

		print
		print "Selected SKUs: "
		for partNo in skus:
			qty = skus[partNo][0]
			vendor = skus[partNo][1]['vendor']
			packaging = skus[partNo][1]['packaging']
			print "\t",qty, partNo, vendor, packaging

		for mfg_part in self.parts:

			sku = partChoices[mfg_part][1]['sku']
			part_num = self.getPartNumForSku(sku)

			for part in self.parts[mfg_part]:

				part_name = part.ref
				part_value = part.value
				if part_value is None: part_value = "NULL"
				dnp = 0

				sql = "insert into boms (assembly_num, part_num, part_name, part_value, dnp) values (%s, %s, '%s', '%s', %s)" % (assemblyNum, part_num, part_name, part_value, dnp)
				print sql
	# def gatherPricingInfo(self):
	# 	for part in self.dbParts:
	# 		print "Part %s is available from the following vendors:" % part

	# 		for dbPart in self.dbParts[part]:

	# 			price = None
	# 			neededQty = len(self.parts[part])

	# 			if dbPart['pricing'] is not None and 'USD' in dbPart['pricing']:
	# 				pricing = json.loads(dbPart['pricing'])['USD']
	# 				fee = dbPart['fee']
	# 				if fee is None: fee = 0

	# 				for level in range(0, len(pricing)):
	# 					if pricing[level][0] < neededQty: continue
	# 					qty = pricing[level][0]
	# 					price = (qty * float(pricing[level][1])) + fee

	# 					if part not in self.partOptions:
	# 						self.partOptions[part] = [{qty: price, 'vendor': dbPart['vendor']}]
	# 					else:
	# 						self.partOptions[part].append({qty: price, 'vendor': dbPart['vendor']})
	# 						break
	# 	print self.partOptions

				# print "\t%s %s %s (%s @ %s)" % (dbPart['vendor'], dbPart['sku'], dbPart['packaging'], price, qty)

newBom = Bom(sys.argv[1], sys.argv[2])

assemblyNum = newBom.addAssemblyToDatabase()
skus = newBom.selectSKUs()
newBom.addSkusToDatabase(assemblyNum, skus)


# workbook = xlsxwriter.Workbook('test.xlsx')
# worksheet = workbook.add_worksheet()

# row = 1
# for part in newBom.parts:

# 	for dbPart in newBom.dbParts[part]:

# 		worksheet.write(row, 0, len(newBom.parts[part]))
# 		worksheet.write(row, 1, ",".join([p.ref for p in newBom.parts[part]]))
# 		worksheet.write(row, 2, dbPart['pkg_code'])
# 		worksheet.write(row, 3, part)
# 		worksheet.write(row, 4, dbPart['mfg_name'])
# 		worksheet.write(row, 5, dbPart['vendor'])
# 		worksheet.write(row, 6, dbPart['sku'])
# 		worksheet.write(row, 7, dbPart['description'])

# 		row += 1
# 	row += 1

# workbook.close()