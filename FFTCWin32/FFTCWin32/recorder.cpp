#include "StdAfx.h"
#include "recorder.h"
#include "portaudio.h"
#include <cstring>

Recorder::Recorder(void)
{
}

Recorder::~Recorder(void)
{
}

int Recorder::SetupInputAndOutput(void)
{
	PaStreamParameters inputParameters, outputParameters;
	int err;

    inputParameters.device = Pa_GetDefaultInputDevice(); /* default input device */
    inputParameters.channelCount = 1;
	inputParameters.sampleFormat = paInt16;
    inputParameters.suggestedLatency = Pa_GetDeviceInfo( inputParameters.device )->defaultHighInputLatency ;
    inputParameters.hostApiSpecificStreamInfo = NULL;
	
	PaStream *stream;

	/* -- setup stream -- */
    err = Pa_OpenStream(
              &stream,
              &inputParameters,
              NULL,
              44100,
              paFramesPerBufferUnspecified,
              paClipOff,     /* we won't output out of range samples so don't bother clipping them */
              NULL,			 /* no callback, use blocking API */
              NULL );		 /* no callback, so no callback userData */
    if( err != paNoError ) goto error;

		return 0;

	error:
		return -1;
}

int Recorder::GetDeviceNumberWithName(const char* desiredName)
{
	int numDevices;
	int err;

    numDevices = Pa_GetDeviceCount();
    if( numDevices < 0 )
    {
        printf( "ERROR: Pa_CountDevices returned 0x%x\n", numDevices );
        err = numDevices;
        goto error;
    }

	const   PaDeviceInfo *deviceInfo;

    for(int i=0; i<numDevices; i++ )
    {
        deviceInfo = Pa_GetDeviceInfo( i );
		if(!strcmp(deviceInfo->name, desiredName)    //has correct name
			&& deviceInfo->maxInputChannels == 0     //has recording channels
			&& deviceInfo->maxOutputChannels == 2    //has no output channels
		) return i;
    }

	error:
	return -1;
}


void Recorder::StartRecording(void)
{

}