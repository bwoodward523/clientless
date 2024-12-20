import json
import math
import xml.etree.ElementTree as ET


class WorldPosData:

	"""
	A data structure representing a 2D location.
	"""

	def __init__(self):
		self.x = 0
		self.y = 0

	def parseCoords(self, reader):
		self.x = reader.ReadFloat()
		self.y = reader.ReadFloat()

	def write(self, writer):
		writer.WriteFloat(self.x)
		writer.WriteFloat(self.y)

	def PrintString(self):
		print("x:", self.x, "y:", self.y)

class GroundTileData:
	
	"""
	x : x coordinate of the tile
	y : y coordinate of the tile
	type : tile type found in GroundCXML
	"""

	def __init__(self):
		self.x = 0
		self.y = 0
		self.type = 0

	def parseFromInput(self, reader):
		self.x = reader.ReadShort()
		self.y = reader.ReadShort()
		self.type = reader.ReadUnsignedShort()

	def write(self, writer):
		writer.WriteShort(self.x)
		writer.WriteShort(self.y)
		writer.WriteUnsignedShort(self.type)

	def PrintString(self):
		print("x", self.x, "y", self.y, "type", self.type)

class ObjectData:

	"""
	Adds objectType to ObjectStatusData
	"""

	def __init__(self):
		self.objectType = 0
		self.objectStatusData = ObjectStatusData()

	def parseFromInput(self, reader):
		self.objectType = reader.ReadUnsignedShort()
		self.objectStatusData.parse(reader)

	def write(self, writer):
		writer.WriteUnsignedShort(self.objectType)
		self.objectStatusData.write(writer)

	def PrintString(self):
		print("objectType", self.objectType)
		self.objectStatusData.PrintString()

class MarketOffer:

	"""
	Data representing an offer to be put on the market.
	"""

	def __init__(self):
		self.price = 0
		self.slotObject = SlotObjectData()

	def parseFromInput(self, reader):
		self.price = reader.ReadInt()
		self.slotObject.parseFromInput(reader)

	def write(self, writer):
		writer.WriteInt(self.price)
		self.slotObject.write(writer)

	def PrintString(self):
		self.slotObject.PrintString()
		print("price", self.price)

class SlotObjectData:

	"""
	Identifying data for a slot.
	objectID: id of the individual this particular slot belongs to
	slotID: the slot ID for this slot
	itemData: a custom Valor serialized json that represents information about the object
	"""

	def __init__(self):
		self.objectID = 0
		self.slotID = 0
		self.itemData = ""

	def parseFromInput(self, reader):
		self.objectID = reader.ReadInt()
		self.slotID = reader.ReadByte()
		self.itemData = reader.ReadString()

	def write(self, writer):
		writer.WriteInt(self.objectID)
		writer.WriteByte(self.slotID)
		writer.WriteString(self.itemData)

	def PrintString(self):
		print("objectID:", self.objectID, "slotID:", self.slotID, "itemData:", self.itemData)

class StatData:

	"""
	Data structure that contains information about attributes.
	Examples include health, mana, total gold, items in inventory, account ID, name, etc..
	"""

	def __init__(self):
		self.statType = 0 #byte
		self.statValue = 0 #int
		self.strStatValue = ""

	def isStringStat(self, x):
		if x == 31 or x == 62 or x == 38 or x == 54 or x == 127 or (8 <= x <= 19) or (71 <= x <= 78) or x == 34 or x == 25:
			return True

	def parse(self, reader):
		self.statType = reader.ReadByte()
		# condition effect
		if not self.isStringStat(self.statType):
			self.statValue = reader.ReadInt()
		else:
			self.strStatValue = reader.ReadString()

	def write(self, writer):
		writer.WriteByte(self.statType)
		if not self.isStringStat(self.statType):
			writer.WriteInt(self.statValue)
		else:
			writer.WriteString(self.strStatValue)

	def PrintString(self):
		print("statType", self.statType, "statValue", self.statValue, "strStatValue", self.strStatValue)

class ObjectStatusData:

	"""
	Data structure that contains a list of StatData objects for a certain objectID.
	"""

	def __init__(self):
		self.objectID = 0
		self.pos = WorldPosData()
		self.stats = [] # statdata objects

	def parse(self, reader): 
		self.objectID = reader.ReadInt()
		self.pos.parseCoords(reader)
		length = reader.ReadShort()
		for _ in range(length):
			s = StatData()
			s.parse(reader)
			self.stats.append(s)

	def write(self, writer):
		writer.WriteInt(self.objectID)
		self.pos.write(writer)
		writer.WriteShort(len(self.stats))
		for s in self.stats:
			s.write(writer)
		
	def PrintString(self):
		print("objid", self.objectID, "pos", self.pos.x, self.pos.y, "stats: ", self.stats)

class PlayerShopItem:

	""" data structure that contains information about one single item in the market """

	def __init__(self):
		self.ID = 0
		self.itemID = 0
		self.price = 0
		self.insertTime = 0
		self.count = 0
		self.isLast = False

	def parseFromInput(self, reader):
		self.ID = reader.ReadUnsignedInt()
		self.itemID = reader.ReadUnsignedShort()
		self.price = reader.ReadInt()
		self.insertTime = reader.ReadInt()
		self.count = reader.ReadInt()
		self.isLast = reader.ReadBoolean()

	def PrintString(self):
		print(
			"ID", self.ID, "itemID", self.itemID, "price", self.price,
			"insertTime", self.insertTime, "count", self.count, "isLast", self.isLast
		)

# class MoveRecord:
#
# 	"""move pos @ time"""
#
# 	def __init__(self):
# 		self.time = 0
# 		self.x = 0
# 		self.y = 0
#
# 	def parseFromInput(self, reader):
# 		self.time = reader.ReadInt()
# 		self.x = reader.ReadFloat()
# 		self.y = reader.ReadFloat()
#
# 	def write(self, writer):
# 		writer.WriteInt(self.time)
# 		writer.WriteFloat(self.x)
# 		writer.WriteFloat(self.y)
class MoveRecord:
	def __init__(self, time, x, y):
		self.time = time
		self.x = x
		self.y = y
	def PrintString(self):
		print("time:", self.time, "x:", self.x, "y:", self.y)

class MoveRecords:
	def __init__(self):
		self.last_clear_time = -1
		self.records = []

	def add_record(self, time, x, y):
		if self.last_clear_time < 0:
			return
		record_id = self.get_id(time)
		if record_id < 1 or record_id > 10:
			return
		if len(self.records) == 0:
			self.records.append(MoveRecord(time, x, y))
			return
		curr_record = self.records[-1]
		curr_id = self.get_id(curr_record.time)
		if record_id != curr_id:
			self.records.append(MoveRecord(time, x, y))
			return
		score = self.get_score(record_id, time)
		curr_score = self.get_score(curr_id, curr_record.time)
		if score < curr_score:
			curr_record.time = time
			curr_record.x = x
			curr_record.y = y

	def get_id(self, time):
		return (time - self.last_clear_time + 50) // 100

	def get_score(self, record_id, time):
		return abs(time - self.last_clear_time - record_id * 100)

	def clear(self, time):
		self.records = []
		self.last_clear_time = time


class Vector2:
	def __init__(self, x=0.0, y=0.0):
		self.x = x
		self.y = y

	def __repr__(self):
		return f"Vector2(x={self.x}, y={self.y})"

	def __add__(self, other):
		return Vector2(self.x + other.x, self.y + other.y)

	def __sub__(self, other):
		return Vector2(self.x - other.x, self.y - other.y)

	def __mul__(self, scalar):
		return Vector2(self.x * scalar, self.y * scalar)

	def __truediv__(self, scalar):
		return Vector2(self.x / scalar, self.y / scalar)

	def dot(self, other):
		return self.x * other.x + self.y * other.y

	def magnitude(self):
		return (self.x**2 + self.y**2)**0.5

	def normalize(self):
		mag = self.magnitude()
		if mag == 0:
			return Vector2()
		return Vector2(self.x / mag, self.y / mag)

	def distance_to(self, other):
		return ((self.x - other.x)**2 + (self.y - other.y)**2)**0.5

	def to_tuple(self):
		return (self.x, self.y)
	def rotate(self, angle):
		x = self.x * math.cos(angle) - self.y * math.sin(angle)
		y = self.x * math.sin(angle) + self.y * math.cos(angle)
		self.x = x
		self.y = y
		return self


class ObjectLibrary:
	def __init__(self, xml_file):
		self.xml_file = xml_file
		try:
			self.xml_tree = ET.parse(xml_file)
			self.xml_root = self.xml_tree.getroot()
		except ET.ParseError as e:
			print(f"Error parsing XML file: {e}")
		except FileNotFoundError:
			print(f"File not found: {xml_file}")
		except Exception as e:
			print(f"An error occurred: {e}")

	def get_class_maxes(self, object_type):
		for obj in self.xml_root.findall('.//Object'):
			#if int(obj.get('type'), 16) == object_type:
			if self.xml_root.find('.//Object[@type="' +object_type + '"]') is not None:
				print("hiii")
				maxes = {
					'MaxHitPoints': int(obj.find('.//MaxHitPoints').get('max')),
					'MaxMagicPoints': int(obj.find('.//MaxMagicPoints').get('max')),
					'Attack': int(obj.find('.//Attack').get('max')),
					'Defense': int(obj.find('.//Defense').get('max')),
					'Speed': int(obj.find('.//Speed').get('max')),
					'Dexterity': int(obj.find('.//Dexterity').get('max')),
					'HpRegen': int(obj.find('.//HpRegen').get('max')),
					'MpRegen': int(obj.find('.//MpRegen').get('max'))
				}
				return maxes
		return None

class Player:
	def __init__(self, maxList):
		self.ip_ = None  # Placeholder for IntPoint equivalent
		self.HPMax = maxList['MaxHitPoints']
		self.MPMax = maxList['MaxMagicPoints']
		self.attackMax = maxList['Attack']
		self.defenseMax = maxList['Defense']
		self.speedMax = maxList['Speed']
		self.dexterityMax = maxList['Dexterity']
		self.vitalityMax = maxList['HpRegen']
		self.wisdomMax = maxList['MpRegen']

		# Current values
		self.name = ""
		self.level = 0
		self.exp = 0
		self.equipment = []
		self.equipData = []
		self.maxHP = 0
		self.hp = 0
		self.maxMP = 0
		self.mp = 0
		self.attack = 0
		self.defense = 0
		self.speed = 0
		self.dexterity = 0
		self.vitality = 0
		self.wisdom = 0
		#self.texturingCache_ = {}

	@staticmethod
	def fromPlayerXML(name, playerXML):
		root = ET.fromstring(playerXML)
		objectType = root.find('.//Char/ObjectType').text
		objectTypeHex = format(int(objectType), '#06x')

		objlib = ObjectLibrary('XMLs/ClassMaxes')

		max_list = objlib.get_class_maxes(objectTypeHex)

		player = Player(max_list)
		print(max_list)
		player.name = name
		player.level = int(root.find('.//Char/Level').text)
		player.exp = int(root.find('.//Char/Exp').text)
		player.equipment = [int(e) for e in root.find('.//Char/Equipment').text.split(',')]
		data = [json.loads(d) for d in root.find('.//Char/ItemDatas').text.split(';')]
		player.equipData = data
		player.maxHP = int(root.find('.//Char/MaxHitPoints').text)
		player.hp = int(root.find('.//Char/HitPoints').text)
		player.maxMP = int(root.find('.//Char/MaxMagicPoints').text)
		player.mp = int(root.find('.//Char/MagicPoints').text)
		player.attack = int(root.find('.//Char/Attack').text)
		player.defense = int(root.find('.//Char/Defense').text)
		player.speed = int(root.find('.//Char/Speed').text)
		player.dexterity = int(root.find('.//Char/Dexterity').text)
		player.vitality = int(root.find('.//Char/HpRegen').text)
		player.wisdom = int(root.find('.//Char/MpRegen').text)
		#player.tex1Id_ = int(root.find('.//Char/Tex1').text)
		#player.tex2Id_ = int(root.find('.//Char/Tex2').text)
		#player.hasBackpack_ = root.find('.//Char/HasBackpack').text == '1'
		return player
