#!/usr/bin/python

import struct

"""An adapter that allows the client to write directly into the WAV data chunk, adding
the necessary WAV headers."""
class WAVWriter:
	def __init__(self, file, AudioFormat=1, NumChannels=1, SampleRate=44100, BitsPerSample=16):
		self.file = file
		self.dataChunkSize = 0
		BlockAlign=NumChannels*BitsPerSample/8
		ByteRate=SampleRate*BitsPerSample/8
		file.write("RIFF")
		file.write("????") # DataChunkSize+36, fill this in later
		file.write("WAVE")
		file.write("fmt ")
		file.write(struct.pack("<IHHIIHH", 16,
			AudioFormat,
			NumChannels,
			SampleRate,
			ByteRate,
			BlockAlign,
			BitsPerSample))
		file.write("data")
		file.write("????") # DataChunkSize, fill this in later
	
	def write(self, buf):
		self.file.write(buf)
		self.dataChunkSize += len(buf)

	def close(self):
		self.file.seek(4, 0)
		self.file.write(struct.pack("<I", self.dataChunkSize+36))
		self.file.seek(40, 0)
		self.file.write(struct.pack("<I", self.dataChunkSize))
		self.file.close()
