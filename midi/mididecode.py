#!/usr/bin/python

import struct, sys

file=open(sys.argv[1], "r")

def readFully(file, size):
	ret = ""
	remain = size
	while remain > 0:
		str = file.read(remain)
		bytesRead = len(str)
		if bytesRead == 0:
			raise EOFError
		remain -= bytesRead
		ret += str
	return ret

def FindRiffChunks(file):
	chunks=dict()
	file.seek(0, 2)
	fileLength = file.tell()
	file.seek(0)
	offset = 0;
	while offset < fileLength:
		(type, length) = struct.unpack(">4sL", readFully(file, 8))
		offset += 8
		if type not in chunks:
			chunks[type] = []
		chunks[type].append({"offset":offset, "length":length})
		offset += length
		file.seek(length, 1)
	return chunks

def DecodeHeader(file, chunkIdx):
	if len(chunkIdx["MThd"]) != 1 or chunkIdx["MThd"][0]["offset"] != 8 or chunkIdx["MThd"][0]["length"] != 6:
		raise ValueError("not a MIDI header")
	file.seek(8)
	(formatType, numTracks, timeDivision) = struct.unpack(">HHH", readFully(file, 6))
	if timeDivision & 0xA000:
		timeDivision &= 0x7FFF
		divisionType = "FRAMES_PER_SECOND"
	else:
		divisionType = "TICKS_PER_BEAT"
	return {"formatType":formatType, "numTracks":numTracks, "timeDivision":timeDivision, "divisionType":divisionType}

def ReadVariableLengthNumber(file, appendTo=None):
	ret = 0
	for i in xrange(0,4):
		ret <<= 7
		byte = readFully(file, 1)
		if appendTo != None:
			appendTo += byte
		(x,) = struct.unpack("B", byte)
		ret |= x & 0x7F
		if x & 0x80 == 0:
			return (ret, appendTo)
	raise ValueError("largest permitted value is 0xffffffff")

midiEventTypeNames={
	0x08:"Note Off",
	0x09:"Note On ",
	0x0A:"Note Aftertouch",
	0x0B:"Controller",
	0x0C:"Program Change",
	0x0D:"Channel Aftertouch",
	0x0E:"Pitch Bend",
}
asciiMetaEventTypes=set(xrange(1,8))
metaEventTypeNames={
	0x01:"text",
	0x02:"Copyright Notice",
	0x03:"Sequence/Track Name",
	0x04:"Instrument Name",
	0x05:"Lyrics",
	0x06:"Marker",
	0x07:"Cue Point",
	0x21:"Port Prefix",
	0x2F:"End Of Track",
	0x51:"Set Tempo",
	0x54:"SMPTE Offset",
	0x58:"Time Signature",
	0x59:"Key Signature",
	0x7F:"Sequencer Specific",
}

class MIDIEvent:
	META_EVENT = 0xff
	SYSEX_EVENT = 0xf0
	
	def __init__(self):
		self.messageData = ""

	def Type(self):
		(type,) = struct.unpack("B", self.messageData[0])
		if type == MIDIEvent.META_EVENT or type == MIDIEvent.SYSEX_EVENT:
			return type
		else:
			return type >> 4
		
	def TypeName(self):
		return midiEventTypeNames[self.Type()]
	
	def MetaEventType(self):
		assert self.Type() == MIDIEvent.META_EVENT
		(metaEventType,) = struct.unpack("B", self.messageData[1])
		return metaEventType
	
	def MetaEventTypeName(self):
		return metaEventTypeNames[self.MetaEventType()]

	def MetaEventString(self):
		assert self.Type() == MIDIEvent.META_EVENT
		if self.MetaEventType() in asciiMetaEventTypes:
			length = self.MetaDataLength()
			return self.messageData[-length:]
		else:
			return None
	
	def MetaDataLength(self):
		assert self.Type() == MIDIEvent.META_EVENT
		return MIDIEvent._decodeVariableLength(self.messageData[2:])
	
	def SysExLength(self):
		assert self.Type() == MIDIEvent.SYSEX_EVENT
		return MIDIEvent._decodeVariableLength(self.messageData[1:])

	@staticmethod
	def _decodeVariableLength(data):
		result = 0
		for x in data:
			x = ord(x)
			result <<= 7
			result |= x & 0x7f
			if x & 0x80 == 0:
				return result
	
	def Channel(self):
		type = self.Type()
		assert type >= 0x8 and type <= 0xe
		return ord(self.messageData[0]) & 0xf

	def Param1(self):
		type = self.Type()
		assert type >= 0x8 and type <= 0xe
		return ord(self.messageData[1])
	
	def Param2(self):
		type = self.Type()
		assert type >= 0x8 and type <= 0xe
		if type == 0xc or type == 0xd:
			return None
		else:
			return ord(self.messageData[2])

def PrintTrack(eventList):
	print "Time\t% 18s  Channel  Param1  Param2" % "Event"
	time = 0
	for (deltaTime, event) in eventList:
		time += deltaTime
		type = event.Type()
		if type == MIDIEvent.META_EVENT:
			metaStr = event.MetaEventString()
			if metaStr != None:
				print "%d\t%s: %s" % (time, event.MetaEventTypeName(), metaStr)
			else:
				print "%d\t%s (%d bytes)" % (time, event.MetaEventTypeName(), event.MetaDataLength())
		elif type == MIDIEvent.SYSEX_EVENT:
			print "%d\tSysEx (%d bytes)" % (time, event.SysExLength())
		else:
			param2 = event.Param2()
			if param2 != None:
				param2 = "% 6d" % param2
			else:
				param2 = ""
			print "%d\t% 18s  % 7d  % 6d  %s" % (time, event.TypeName(), event.Channel(), event.Param1(), param2)

def DecodeTrack(file, chunkIdx, trackNum):
	where = chunkIdx["MTrk"][trackNum]
	file.seek(where["offset"])
	endOffset = where["offset"] + where["length"]
	events = []
	while file.tell() < endOffset:
		event = MIDIEvent()
		(deltaTime,discard) = ReadVariableLengthNumber(file, None)
		etcByte = readFully(file, 1)
		(eventTypeAndChannel,) = struct.unpack("B", etcByte)
		if eventTypeAndChannel == 0xFF:
			event.messageData += etcByte
			byte = readFully(file, 1) # meta event type
			event.messageData += byte
			(metaLength, event.messageData) = ReadVariableLengthNumber(file, event.messageData)
			metaData = readFully(file, metaLength)
			event.messageData += metaData
		elif eventTypeAndChannel == 0xF0:
			# SysEx event
			event.messageData += etcByte
			(length, event.messageData) = ReadVariableLengthNumber(file, event.messageData)
			event.messageData += readFully(file, length)
		else:
			if eventTypeAndChannel >= 0x80:
				event.messageData += etcByte
				byte = readFully(file, 1)
				event.messageData += byte
			else:
				# "running status" - the event type is the same as the last message
				# this is actually the first data byte of the new message
				event.messageData += previousEtcByte + etcByte
				etcByte = previousEtcByte
				(eventTypeAndChannel,) = struct.unpack("B", etcByte)
			eventType = eventTypeAndChannel >> 4
			assert eventType >= 8 and eventType <= 0xe
			if eventType != 0x0C and eventType != 0x0D:
				# 0xC and 0xD have only one byte of data, others have 2
				byte = readFully(file, 1)
				event.messageData += byte
		previousEtcByte = etcByte
		events.append((deltaTime, event))
	assert file.tell() == endOffset
	return events
	
chunkIdx = FindRiffChunks(file)
hdr = DecodeHeader(file, chunkIdx)
print hdr
if hdr["numTracks"] != len(chunkIdx["MTrk"]):
	raise ValueError("track count mismatch")
for trackNum in xrange(0, hdr["numTracks"]):
	print "TRACK %d" % trackNum
	PrintTrack(DecodeTrack(file, chunkIdx, trackNum))

file.close()
