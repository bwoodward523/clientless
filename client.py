import re
import rsa
import base64
import socket
import select
import struct
import requests
import time
import json
import pickle
import traceback
import threading
import numpy as np

from valorlib.Packets.Packet import *	
from valorlib.Packets.DataStructures import *	
from valorlib.RC4 import RC4
from queue import Queue
from Notifier import *
from AFK import *

class ObjectInfo:

	def __init__(self):
		self.pos = WorldPosData()
		self.pos.x = 100.0 + random.randint(-10, 10)
		self.pos.y = 133.0 + random.randint(-10, 10)
		self.objectType = 0
		self.moveRecords = MoveRecords()
		self.tickId = 0
		self.lastTickId = -1

	def clearMoveRecord(self):
		self.moveRecord = []

	def PrintString(self):
		self.pos.PrintString()
		print("objectType", self.objectType)

class Client:

	def __init__(self, names: dict):

		# static stuff

		self.publicKey = rsa.PublicKey.load_pkcs1_openssl_pem(b"-----BEGIN PUBLIC KEY-----\nMIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQDTa2VXtjKzQ8HO2hCRuXZPhezl0HcWdO0QxUhz1b+N5xJIXjvPGYpawLnJHgVgjcTI4dqDW9sthI3hEActKdKV6Zm/dpPMuCvgEXq1ajOcr8WEX+pDji5kr9ELH0iZjjlvgfzUiOBI6q4ba3SRYiAJFgOoe1TCC1sDk+rDZEPcMwIDAQAB\n-----END PUBLIC KEY-----")
		self.remoteHostAddr = "127.0.0.1"
		self.remoteHostPort = 2050
		# use this key to decrypt packets from the server
		self.clientReceiveKey = RC4(bytearray.fromhex("c91d9eec420160730d825604e0"))
		# use this key to send packets to the server
		self.serverRecieveKey = RC4(bytearray.fromhex("5a4d2016bc16dc64883194ffd9"))
		self.headers = {
			'User-Agent': "Mozilla/5.0 (Windows; U; en-US) AppleWebKit/533.19.4 (KHTML, like Gecko) AdobeAIR/32.0",
			'Referer' : 'app:/Valor.swf',
			'x-flash-version' : '32,0,0,170'
		}
		self.email = None
		self.password = None
		self.buildVersion = "3.0.0"
		self.loginToken = b""
		self.serverSocket = None
		self.lastPacketTime = time.time()
		
		# modules + internal variables
		self.moduleName = "none"
		self.module = None
		self.enemyName = names
		self.reconnecting = False
		self.connected = False
		self.blockLoad = False
		self.helloTime = 0
		self.messageQueue = Queue()

		# state consistency
		self.gameIDs = {
			1 : "Realm",
			-2 : "Nexus",
			-2 : "Nexus",
			-5 : "Vault",
			-15 : "Marketplace",
			-16 : "Ascension Enclave",
			-17 : "Aspect Hall"
		}
		self.currentMap = None
		self.charID = None
		self.objectID = None
		self.newObjects = {}
		self.oryx = False
		self.nextGameID = -1
		self.nextKeyTime = 0
		self.nextKey = []
		self.latestQuest = None
		self.questSwitch = False

		# this is in milliseconds
		self.clientStartTime = int(time.time() * 1000)
		self.ignoreIn = []
		"""
		self.ignoreIn = [
			PacketTypes.ShowEffect, PacketTypes.Ping, PacketTypes.Goto, 
			PacketTypes.Update, PacketTypes.NewTick, PacketTypes.EnemyShoot
			]
		"""
		self.objInfo = ObjectInfo()

		#Client Stats
		self.minSpeed = 0.004
		self.maxSpeed = 0.0096
		self.speed = 1
		self.speedMult = 1.0
		self.velocity = Vector2(1, 0)
		self.funnyAngle = 0.0  + random.randint(0, 360)

		#Player
		self.player = Player()

	# returns how long the client has been active
	def time(self):
		return int(time.time() * 1000 - self.clientStartTime)

	"""
	connect remote host -> send hello packet
	"""
	def connect(self):
		self.serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.serverSocket.connect((self.remoteHostAddr, self.remoteHostPort))
		self.connected = True

	def fireMovePacket(self, tickId, vel):
		#update the player's position by the velocity
		self.calcualteVelocity()

		self.objInfo.pos.x += vel.x
		self.objInfo.pos.y += vel.y

		#Build the move packet
		move = Move()
		move.tickID = tickId
		move.time = self.time()
		move.newPosition.x = self.objInfo.pos.x
		move.newPosition.y = self.objInfo.pos.y

		last_move = self.objInfo.moveRecords.last_clear_time
		move.records = []
		if last_move >= 0 and move.time - last_move > 125:
			len_records = min(10, len(self.objInfo.moveRecords.records))
			for i in range(len_records):
				if self.objInfo.moveRecords.records[i].time >= move.time - 25:
					break
				move.records.append(self.objInfo.moveRecords.records[i])

		self.objInfo.moveRecords.clear(move.time)
		#move.PrintString()

		#TEMPORARY PACKET SPAM FIX
		#if random.randint(0, 100) < 10:
		self.SendPacketToServer(CreatePacket(move))

	#Calculate the velocity of the player the way the flash Client does
	def calcualteVelocity(self):

		self.velocity = Vector2.rotate(Vector2(1,0),self.funnyAngle) * self.getMoveSpeed()
		self.funnyAngle += 1
		if self.funnyAngle >= 360:
			self.funnyAngle = 0
		print(self.speed)

	#Calculate the speed of the player the way the flash Client does
	def getMoveSpeed(self):
		moveSpeed = self.minSpeed + (self.speed / 75 * (self.maxSpeed - self.minSpeed))
		moveSpeed = self.speed * self.speedMult
		return moveSpeed
	# send hello packet
	def fireHelloPacket(self, useReconnect):
		p = Hello()
		if not useReconnect:
			p.buildVersion = self.buildVersion
			p.gameID = -2
			p.guid = self.encryptString(self.email)
			p.password = self.encryptString(self.password)
			p.keyTime = -1
			p.key = []
			p.mapJSON = ""
			self.currentMap = 'Nexus'
		else:
			p.buildVersion = self.buildVersion
			p.gameID = self.nextGameID
			self.currentMap = self.gameIDs[p.gameID]
			p.guid = self.encryptString(self.email)
			p.password = self.encryptString(self.password)
			p.keyTime = self.nextKeyTime
			p.key = self.nextKey
			p.mapJSON = ""

		p.PrintString()

		# after sending hello, reset states (since keys have expired)
		self.nextGameID = -1
		self.nextKeyTime = 0
		self.nextKey = []

		self.helloTime = time.time()


		self.SendPacketToServer(CreatePacket(p))

	def fireLoadPacket(self):
		p = Load()
		# should only trigger on startup
		if self.charID is None:
			self.charID = self.getRandomCharID()
		p.charID = self.charID
		p.isFromArena = False
		self.SendPacketToServer(CreatePacket(p))
	def firePlayerTextPacket(self):
		p = PlayerText()
		p.text = "Hello World" + str(random.randint(0, 1000))
		self.SendPacketToServer(CreatePacket(p))

	# listen for incoming packets and deal with them
	def listenToServer(self):

		header = self.serverSocket.recv(5)

		if len(header) == 0:
			print("server sent 0")
			self.reset()
		
		# if the server sent nothing, keep trying until we recieve 5 bytes
		while len(header) != 5:
			header += self.serverSocket.recv(5 - len(header))

		packetID = header[4]
		expectedPacketLength = struct.unpack("!i", header[:4])[0]
		# read the packet, subtract 5 cuz you already read header
		leftToRead = expectedPacketLength - 5
		data = bytearray()
		
		while (leftToRead > 0):
			buf = bytearray(self.serverSocket.recv(leftToRead))
			data += buf
			leftToRead -= len(buf)

		packet = Packet(header, data, packetID)
		send = True


		# # for debugging
		try:
			if packet.ID not in self.ignoreIn:
				print("Server sent:", PacketTypes.reverseDict[packet.ID])
		except:
			print("Got unknown packet from server, id", packet.ID)

		if packet.ID == PacketTypes.CreateSuccess:
			# capture our object ID, necessary to send many types of packets like invswap or buy
			self.onCreateSuccess(packet)

		elif packet.ID == PacketTypes.Goto:
			p = GotoAck()
			p.time = self.time()
			self.SendPacketToServer(CreatePacket(p))

		# keep-alive functions
		elif packet.ID == PacketTypes.Ping:
			p = Ping()
			p.read(packet.data)
			reply = Pong()
			reply.serial = p.serial
			reply.time = self.time()
			self.SendPacketToServer(CreatePacket(reply))

		elif packet.ID == PacketTypes.Update:

			p = UpdateAck()
			self.SendPacketToServer(CreatePacket(p))

			p = Update()
			p.read(packet.data)
			for i in p.newObjects:
				obj = ObjectInfo()
				obj.pos = i.objectStatusData.pos
				obj.objectType = i.objectType
				self.newObjects.update({i.objectStatusData.objectID : obj})

		# elif packet.ID == PacketTypes.Text:
		# 	p = Text()
		# 	p.read(packet.data)
		# 	if p.name == '#Sidon the Dark Elder' and 'CLOSED THIS' in p.text:
		# 		self.oryx = True

		elif packet.ID == PacketTypes.NewTick:
			p = NewTick()
			p.read(packet.data)
			#p.PrintString()

			#Handle the incoming object status data
			for i in p.statuses:
				#if isinstance(i, ObjectStatusData):
				#print("helloObj: id == ", i.objectID, i.PrintString())
				#print(i.PrintString())
				if i.objectID == self.objectID:
					print("Player's stats")
					#Now we process the player's stats
					self.objInfo.pos = i.pos
					#i.PrintString()
			self.objInfo.tickId += 1

			self.fireMovePacket(self.objInfo.tickId, self.velocity)
			self.objInfo.lastTickId = self.objInfo.tickId

			#print(self.objInfo.lastTickId, "<- tickID")

		#p.PrintString()

		elif packet.ID == PacketTypes.QueuePing:
			p = QueuePing()
			p.read(packet.data)
			reply = QueuePong()
			reply.serial = p.serial
			reply.time = self.time()
			self.SendPacketToServer(CreatePacket(reply))

		# you need to ack the update packets
		elif packet.ID == PacketTypes.Update:
			p = UpdateAck()
			self.SendPacketToServer(CreatePacket(p))

		# server expects a Load from the client after AccountList
		elif packet.ID == PacketTypes.AccountList:
			# then, fire Load packet
			self.fireLoadPacket()

		elif packet.ID == PacketTypes.QuestObjId:
			p = QuestObjId()
			p.read(packet.data)
			self.questSwitch = True
			self.latestQuest = p.objectID

		elif packet.ID == PacketTypes.Reconnect:
			# update map name.
			p = Reconnect()
			p.read(packet.data)
			
			self.nextGameID = p.gameID
			self.nextKeyTime = p.keyTime
			self.nextKey = p.key
			p.PrintString()
			self.reconnecting = True

		elif packet.ID == PacketTypes.Failure:
			p = Failure()
			p.read(packet.data)
			p.PrintString()
			raise Exception("Got failure from server. Aborting")


	# create a wizzy
	def Create(self):
		p = Create()
		p.classType = 782
		p.skinType = 0
		self.SendPacketToServer(CreatePacket(p))


	def reset(self):
		self.resetStates()
		self.clientReceiveKey.reset()
		self.serverRecieveKey.reset()
		self.serverSocket = None
		self.gameSocket = None
		
		# first, connect to remote
		self.connect()
		
		# then, fire the hello packet, connect to new map
		self.fireHelloPacket(True)		
		self.clientStartTime = int(time.time() * 1000)

	def resetStates(self):
		self.connected = False
		self.helloTime = 0
		self.clientReceiveKey.reset()
		self.serverRecieveKey.reset()
		self.objectID = None
		self.newObjects = {}
		self.oryx = False
		self.latestQuest = None
		self.clientStartTime = int(time.time() * 1000)


	def onReconnect(self):
		self.Disconnect()
		self.resetStates()
		self.connect()
		self.fireHelloPacket(True)


		# load or create:
		if self.charID is None:
			self.charID = self.getRandomCharID()

		if self.charID == -1:
			self.blockLoad = True
			self.Create()

	def Disconnect(self):
		self.connected = False
		if self.serverSocket:
			self.serverSocket.shutdown(socket.SHUT_RD)
			self.serverSocket.close()
		self.gameSocket = None

	# main loop!
	def mainLoop(self):

		# post to acc/verify
		self.accountVerify()

		# first, connect to remote
		self.connect()
		# then, fire the hello packet, connect to nexus.
		self.fireHelloPacket(False)


		# load or create:
		if self.charID is None:
			self.charID = self.getRandomCharID()

		# if no character exists
		if self.charID == -1:
			self.blockLoad = True
			self.Create()

		print("Connected to server!")
		helloworldt = 0
		# listen to packets
		while True:
			helloworldt += random.randint(0, 1000)
			if helloworldt % 1000 == 0:
				#print("????")
				self.firePlayerTextPacket()
			try:
				if time.time() - self.lastPacketTime > 30:
					print("Connection was hanging")
					self.reset()
				
				# take care of reconnect first
				if self.reconnecting:

					# flush
					ready = select.select([self.serverSocket], [], [])[0]
					if self.serverSocket in ready:
						self.serverSocket.recv(20000)

					self.onReconnect()
					self.reconnecting = False

				# check if there is data ready from the server
				ready = select.select([self.serverSocket], [], [])[0]
				if self.serverSocket in ready:
					self.lastPacketTime = time.time()
					self.listenToServer()

				# finally, run a custom module
				self.module.main(self)

			except ConnectionAbortedError as e:
				print("Connection was aborted:", e)
				self.reset()

			except ConnectionResetError as e:
				print("Connection was reset")
				traceback.print_exc()
				self.reset()

			except Exception as e:
				print("Ran into exception:", e)
#				self.reset()

			except KeyboardInterrupt:
				print("Quitting.")
				return

	# rsa encrypt + base 64
	def encryptString(self, s):
		return base64.b64encode(rsa.encrypt(s, self.publicKey))

	# send a packet to the server
	def SendPacketToServer(self, packet):
		self.serverSocket.sendall(packet.format())
		#print(f"Packet sent to server: {self.serverSocket}")

	def moveRight(self, worldPos):
		pass
	# get loginToken
	def accountVerify(self):

		x = requests.post(
			"http://127.0.0.1:8080/account/verify?g={}".format(self.email),
			#headers = self.headers,
			data = {
				"guid" : self.email,
				"password" : self.password,
				"pin": "",
				"ignore" : 0,
				"gameClientVersion" : self.buildVersion
			}
		).content.decode("utf-8")
		#print(x)
		#self.loginToken = bytes(re.findall("<LoginToken>(.+?)</LoginToken>", x, flags = re.I)[0], 'utf-8')

	def getRandomCharID(self):
		print("getting random char ID")
		x = requests.post(
			"http://127.0.0.1:8080//char/list?g={}".format(self.email),
			headers = self.headers,
			 data = {
			 	"guid" : self.email,
			 	"password" : self.password}
			# 	"do_login" : "true",
			# 	"ignore" : 0,
			# 	"gameClientVersion" : self.buildVersion
			# }
		).content.decode("utf-8")
		print(x)
		try:
			charID = int(re.findall("<char id=\"([0-9]+)\">", x, flags = re.I)[0])
			print(charID)

			#Now lets parse the stat data and information from our player into the client from this XML


			return charID
		except IndexError:
			return -1

	def onCreateSuccess(self, packet):
		p = CreateSuccess()
		p.read(packet.data)
		self.connected = True
		self.objectID = p.objectID
		self.charID = p.charID
		print("Connected to {}!".format(self.currentMap))#, "objectID:", self.objectID, "charID:", self.charID)

	#########
	# hooks #
	#########

	def initializeAccountDetails(self, email, password, moduleName):
		try:
			self.email = email.encode("utf-8")
			self.password = password.encode("utf-8")
			self.moduleName = moduleName

			if self.email == b"" or self.password == b"":
				raise Exception("You left your credentials blank!")

		except Exception as e:
			print(e)
			print("Make sure you are entering your account details correctly; do not forget the comma after the email value.")
			return False

		return True

	def loadModules(self):
		if self.moduleName == "notifier":
			self.module = Notifier()
		elif self.moduleName == "afk":
			self.module = AFK()
		print(self.moduleName)
		#elif self.moduleName == "WZYBFIPQLMOH":
		#	self.module = WZYBFIPQLMOH()

		if self.module == None:
			return False

		return True

if __name__ == "__main__":

	with open("NameDictionary.pkl", "rb") as f:
		nameDictionary = pickle.load(f)

	c = Client(nameDictionary)
	if not c.initializeAccountDetails():
		print("Encountered exception in initializing account details. Quitting.")
	if not c.loadModules():
		print("No module was loaded. Quitting.")
	else:
		c.mainLoop()