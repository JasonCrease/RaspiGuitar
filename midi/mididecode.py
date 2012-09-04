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

def ReadVariableLengthNumber(file):
	ret = 0
	for i in xrange(0,4):
		ret <<= 7
		(x,) = struct.unpack("B", readFully(file, 1))
		ret |= x & 0x7F
		if x & 0x80 == 0:
			return ret
	raise ValueError("largest permitted value is 0xffffffff")

channelEventTypes={
	0x08:"Note Off",
	0x09:"Note On ",
	0x0A:"Note Aftertouch",
	0x0B:"Controller",
	0x0C:"Program Change",
	0x0D:"Channel Aftertouch",
	0x0E:"Pitch Bend",
}
asciiMetaEventTypes={
	0x01:"text",
	0x02:"Copyright Notice",
	0x03:"Sequence/Track Name",
	0x04:"Instrument Name",
	0x05:"Lyrics",
	0x06:"Marker",
	0x07:"Cue Point",
}
otherMetaEventTypes={
	0x21:"Port Prefix",
	0x2F:"End Of Track",
	0x51:"Set Tempo",
	0x54:"SMPTE Offset",
	0x58:"Time Signature",
	0x59:"Key Signature",
	0x7F:"Sequencer Specific",
}
def DecodeTrack(file, chunkIdx, trackNum):
	print "Time\t% 18s  Channel  Param1  Param2" % "Event"
	time = 0
	where = chunkIdx["MTrk"][trackNum]
	file.seek(where["offset"])
	endOffset = where["offset"] + where["length"]
	while file.tell() < endOffset:
		deltaTime = ReadVariableLengthNumber(file)
		time += deltaTime
		(eventTypeAndChannel,) = struct.unpack("B", readFully(file, 1))
		if eventTypeAndChannel == 0xFF:
			(metaEventType,) = struct.unpack("B", readFully(file, 1))
			metaLength = ReadVariableLengthNumber(file)
			metaData = readFully(file, metaLength)
			if metaEventType in asciiMetaEventTypes:
				print "%d\t%s: %s" % (time, asciiMetaEventTypes[metaEventType], metaData)
			else:
				eventName = otherMetaEventTypes[metaEventType] if metaEventType in otherMetaEventTypes else "META %d" % metaEventType
				print "%d\t%s (%d bytes)" % (time, eventName, metaLength)
		elif eventTypeAndChannel == 0xF0:
			length = ReadVariableLengthNumber(file)
			file.seek(length, 1)
			print "%d\tSysEx (%d bytes)" % (time, length)
		else:
			if eventTypeAndChannel >= 0x80:
				(param1,) = struct.unpack("B", readFully(file, 1))
			else:
				# "running status" - the event type is the same as the last message
				# this is actually the first data byte of the new message
				param1 = eventTypeAndChannel
				eventTypeAndChannel = previousEventTypeAndChannel
			eventType = eventTypeAndChannel >> 4
			channel = eventTypeAndChannel & 0xF
			assert eventType >= 8 and eventType <= 0xe
			param2 = ""
			if eventType != 0x0C and eventType != 0x0D:
				# 0xC and 0xD have only one byte of data, others have 2
				(param2,) = struct.unpack("B", readFully(file, 1))
				param2 = "% 6d" % param2
			print "%d\t% 18s  % 7d  % 6d  %s" % (time, channelEventTypes[eventType], channel, param1, param2)
		previousEventTypeAndChannel = eventTypeAndChannel
	assert file.tell() == endOffset
	
chunkIdx = FindRiffChunks(file)
hdr = DecodeHeader(file, chunkIdx)
print hdr
if hdr["numTracks"] != len(chunkIdx["MTrk"]):
	raise ValueError("track count mismatch")
for trackNum in xrange(0, hdr["numTracks"]):
	print "TRACK %d" % trackNum
	DecodeTrack(file, chunkIdx, trackNum)

file.close()
