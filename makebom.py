from EagleSchematic import Schematic
import xml.etree.ElementTree as ET
import sys
import sqlite3

def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

parts = {}

with sqlite3.connect('../control-surface/pcb/database.db') as conn:
	conn.row_factory = dict_factory
	cur = conn.cursor()

	with open(sys.argv[1], 'r') as schFile:
		schematic = Schematic(schFile)

		for part in schematic.drawing.schematic.partsList:

			if len(part.xml._children) > 0:
				for child in part.xml._children:
					if child.attrib['name'] == 'PARTNO':

						mfgPartNo = child.attrib['value']

						if mfgPartNo in parts:
							parts[mfgPartNo]['refs'].append(part.getName())
							# parts[mfgPartNo]['value'] = part.getValue()
						else:
							parts[mfgPartNo] = {}
							parts[mfgPartNo]['refs'] = [part.getName()]
							parts[mfgPartNo]['value'] = part.getValue()


		for part in parts:

			sql = "select pkg_code, mfg_name, vendor, sku, description from parts where mfg_part_num = '%s'" % part
			cur.execute(sql)
			results = cur.fetchone()
			package = results['pkg_code']
			mfg_name = results['mfg_name']
			vendor = results['vendor']
			sku = results['sku']
			desc = results['description']

			print len(parts[part]), parts[part], package, part, mfg_name, vendor, sku, desc