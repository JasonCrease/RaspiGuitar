// FFTCWin32.cpp : Defines the entry point for the console application.
//

#include "stdafx.h"
#include "portaudio.h"
#include "recorder.h"

typedef struct
{
	float left_phase;
	float right_phase;
}   
paTestData;

#define SAMPLE_RATE 44100
/* This routine will be called by the PortAudio engine when audio is needed.
It may called at interrupt level on some machines so don't do anything
that could mess up the system like calling malloc() or free().
*/ 
static int patestCallback( const void *inputBuffer, void *outputBuffer,
	unsigned long framesPerBuffer,
	const PaStreamCallbackTimeInfo* timeInfo,
	PaStreamCallbackFlags statusFlags,
	void *userData )
{
	/* Cast data passed through stream to our structure. */
	paTestData *data = (paTestData*)userData; 
	float *out = (float*)outputBuffer;
	unsigned int i;
	(void) inputBuffer; /* Prevent unused variable warning. */

	for( i=0; i<framesPerBuffer; i++ )
	{
		*out++ = data->left_phase;  /* left */
		*out++ = data->right_phase;  /* right */

		/* Generate simple sawtooth phaser that ranges between -1.0 and 1.0. */
		data->left_phase += 0.01f;
		/* When signal reaches top, drop back down. */
		if( data->left_phase >= 0.5f ) data->left_phase -= 1.0f;
		/* higher pitch so we can distinguish left and right. */
		data->right_phase += 0.0075f;
		if( data->right_phase >= 0.3f ) data->right_phase -= 0.6f;

		//data->left_phase = 0;
		//data->right_phase = 0;
	}
	return 0;
}

int _tmain(int argc, _TCHAR* argv[])
{
	int err = 0;
	Recorder recorder;

	paTestData data;
	data.left_phase =0; data.right_phase=0;

	/* Initialize */

	err = Pa_Initialize();
		if( err != paNoError ) goto error;

	PaStream *stream;
    PaError paerr;

	/* Setup the Recorder */
	int x = recorder.GetDeviceNumberWithName("Line 1/2 (Digidesign Mbox 2 Mini Audio)");
	recorder.SetupInputAndOutput();
	printf("%d", x);

    /* Open an audio I/O stream. */
    paerr = Pa_OpenDefaultStream( &stream,
                                0,          /* no input channels */
                                2,          /* stereo output */
                                paFloat32,  /* 32 bit floating point output */
                                SAMPLE_RATE,
                                paFramesPerBufferUnspecified,        /* frames per buffer, i.e. the number
                                                   of sample frames that PortAudio will
                                                   request from the callback. Many apps
                                                   may want to use
                                                   paFramesPerBufferUnspecified, which
                                                   tells PortAudio to pick the best,
                                                   possibly changing, buffer size.*/
                                patestCallback, /* this is your callback function */
                                &data ); /*This is a pointer that will be passed to
                                                   your callback*/
    if(paerr != paNoError ) goto error;

	/* Start the stream */

	err = Pa_StartStream( stream );
    if( err != paNoError ) goto error;

	/* Sleep a bit */

	Pa_Sleep(4 * 1000);

	/* Stop stream */
	err = Pa_StopStream( stream );
    if( err != paNoError ) goto error;
	
	/* Close stream */

	err = Pa_CloseStream( stream );
    if( err != paNoError ) goto error;

    /* Shutdown */
	
	err = Pa_Terminate();
		if( err != paNoError ) goto error; 
	//getchar();

	return 0;

	/* Errors */

error: 
	printf(  "PortAudio error: %s\n", Pa_GetErrorText( err ) );
	getchar();
	return -1;
}


