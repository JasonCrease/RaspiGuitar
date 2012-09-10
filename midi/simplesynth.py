#!/usr/bin/python

from mididecode import FindRiffChunks, DecodeHeader, MIDIEvent, DecodeTrack, GetTempoChangeEvents, FilterEventsByChannel
from wavwriter import WAVWriter

import math, sys

"""Output the waveform from the input iterator to the file as uint16 Little Endian."""
def LE16(waveform, out):
	for amplitude in waveform:
		if amplitude == 0:
			out.write("\0\0")
		elif amplitude == 1:
			out.write("\xff\x7f")
		elif amplitude == -1:
			out.write("\0\x80")
		else:
			raise AssertionError

"""Generates a square waveform based on the list of tuples of (fromTime, midiNote).
For silent regions, midiNote is None."""
def GenerateWaveform(timedNotes, sampleIntervalMillis):
	it = timedNotes.__iter__()
	T = 0
	Tosc = 0
	amplitude = 0
	halfWavelength = 0
	(tranTime, nextNote) = it.next()
	while True:
		while T >= tranTime:
			if nextNote != None:
				amplitude = 1
				halfWavelength = 500.0/MIDINoteFrequencyHz(nextNote)
				Tosc = 0
			else:
				amplitude = 0
			next = it.next()
			if next == None:
				return
			(tranTime, nextNote) = next
		Tosc += sampleIntervalMillis
		if Tosc >= halfWavelength:
			amplitude *= -1
			Tosc -= halfWavelength
		yield amplitude
		T += sampleIntervalMillis

"""Returns the frequency in Hertz for the given MIDI note (0-127)."""
def MIDINoteFrequencyHz(midiNote):
	assert midiNote >= 0 and midiNote < 128
	return 440.0 * math.pow(2, (midiNote-69)/12.0)

"""Converts the timestamps on the event list into milliseconds from the track time.
This is based on the Time Division in the header and the tempo, where the tempo can
change throughout the track."""
def TrackTimeToMillis(hdr, channelEvents, tempoChangeEvents):
	assert hdr["divisionType"]=="TICKS_PER_BEAT"
	ticksPerBeat = hdr["timeDivision"]
	channelEventIterator = channelEvents.__iter__()
	tempoEventIterator = tempoChangeEvents.__iter__()
	# StopIteration here is OK, if the input is empty then the output will be empty
	(nextChannelEventTime, nextChannelEvent) = channelEventIterator.next()
	try:
		(nextTempoEventTime, nextTempoMPQN) = tempoEventIterator.next()
	except StopIteration:
		# this is not OK, there should be tempo setting at the start
		raise AssertionError
	milliTime = 0
	milliTimeBase = 0
	eventTimeBase = 0
	millisPerEventTick = 0
	while True:
		if nextTempoEventTime == None or nextChannelEventTime < nextTempoEventTime:
			milliTime = milliTimeBase + (nextChannelEventTime - eventTimeBase) * millisPerEventTick
			yield (milliTime, nextChannelEvent)
			try:
				(nextChannelEventTime, nextChannelEvent) = channelEventIterator.next()
			except StopIteration:
				return
		else:
			milliTime = milliTimeBase + (nextTempoEventTime - eventTimeBase) * millisPerEventTick
			milliTimeBase = milliTime
			eventTimeBase = nextTempoEventTime
			millisPerEventTick = 0.001*nextTempoMPQN/ticksPerBeat
			try:
				(nextTempoEventTime, nextTempoMPQN) = tempoEventIterator.next()
			except StopIteration:
				nextTempoEventTime = None

"""Returns a list of (fromTime, noteNumber) from (time, MIDIEvent), consisting only of notes.
Where two or more notes are played in polyphone in the input stream, the later note replaces
the original note. In silent regions, noteNumber is None."""
def ExtractMonophonicNotes(trackEvents):
	for (time, event) in trackEvents:
		type = event.Type()
		if type == MIDIEvent.NOTE_OFF or (type == MIDIEvent.NOTE_ON and event.Param2() == 0):
			# Note on with velocity 0 also means note off
			note = event.Param1()
			if note == currentlyPlayingNote:
				currentlyPlayingNote = None
				yield (time, None)
		elif type == MIDIEvent.NOTE_ON:
			currentlyPlayingNote = event.Param1()
			yield (time, currentlyPlayingNote)
		elif type == MIDIEvent.META_EVENT and event.MetaEventType() == MIDIEvent.END_OF_TRACK:
			yield (time, None)
			return
	raise AssertionError("end of track expected")
			
midiFile=open(sys.argv[1], "r")
chunkIdx = FindRiffChunks(midiFile)
hdr = DecodeHeader(midiFile, chunkIdx)
track0 = DecodeTrack(midiFile, chunkIdx, 0)
tempoChangeEvents = GetTempoChangeEvents(track0)
SampleRate=44100
# Type 0 MIDI files are synthesised by separate channels
# Type 1 and 2 files are synthesised by track
if hdr["formatType"] == 0:
	eventsPerChannel = FilterEventsByChannel(track0)
	range = eventsPerChannel.keys()
else:
	range = xrange(1, hdr["numTracks"])
track0 = None
for i in range:
	if hdr["formatType"] == 0:
		filename = "channel%d.wav" % i
		channelEvents = eventsPerChannel[i]
	else:
		filename = "track%d.wav" % i
		channelEvents = DecodeTrack(midiFile, chunkIdx, i)
	print "writing %s" % filename
	wavFile = WAVWriter(open(filename, "wb"), SampleRate=SampleRate)
	LE16(GenerateWaveform(ExtractMonophonicNotes(TrackTimeToMillis(hdr, channelEvents, tempoChangeEvents)), 1000.0/SampleRate), wavFile)
	wavFile.close()
midiFile.close()
