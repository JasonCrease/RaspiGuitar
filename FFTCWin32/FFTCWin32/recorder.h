#pragma once
class Recorder
{
public:
	Recorder(void);
	~Recorder(void);
	void StartRecording(void);
	int GetDeviceNumberWithName(const char* name);
	int SetupInputAndOutput(void);
};

