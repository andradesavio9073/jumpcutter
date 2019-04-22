import misc_func
import subprocess
from audiotsm import phasevocoder
from audiotsm.io.wav import WavReader, WavWriter
from scipy.io import wavfile
import numpy as np
import re
import math
from contextlib import closing
import os

def process(pid, threads, INPUT_FILE, OUTPUT_FILE, frameRate, SAMPLE_RATE, SILENT_THRESHOLD, FRAME_SPREADAGE, NEW_SPEED, FRAME_QUALITY):
    try:
        TEMP_FOLDER = "TEMP_"+str(pid)
        AUDIO_FADE_ENVELOPE_SIZE = 400 # smooth out transitiion's audio by quickly fading in/out (arbitrary magic number whatever)
        misc_func.createPath(TEMP_FOLDER)

        #image extraction
        command = 'ffmpeg -v quiet -threads '+str(threads)+' -thread_queue_size 512 -i "'+INPUT_FILE+'" -qscale:v '+str(FRAME_QUALITY)+' '+TEMP_FOLDER+'/frame%06d.jpg -hide_banner'
        subprocess.call(command, shell=True)

        #audio extraction
        command = 'ffmpeg -v quiet -threads '+str(threads)+' -thread_queue_size 512 -i "'+INPUT_FILE+'" -ab 160k -ac 2 -ar '+str(SAMPLE_RATE)+" -vn "+TEMP_FOLDER+"/audio.wav > NUL"
        subprocess.call(command, shell=True)

        #original parameter extraction
        command = 'ffmpeg -i "'+INPUT_FILE+'" 2>&1'
        f = open(TEMP_FOLDER+"/params.txt", "w")
        subprocess.call(command, shell=True, stdout=f)
        f.close()

        sampleRate, audioData = wavfile.read(TEMP_FOLDER+"/audio.wav")
        audioSampleCount = audioData.shape[0]
        maxAudioVolume = misc_func.getMaxVolume(audioData)

        f = open(TEMP_FOLDER+"/params.txt", 'r+')
        pre_params = f.read()
        f.close()
        params = pre_params.split('\n')
        for line in params:
            m = re.search('Stream #.*Video.* ([0-9]*) fps',line)
            if m is not None:
                frameRate = float(m.group(1))

        samplesPerFrame = sampleRate/frameRate

        audioFrameCount = int(math.ceil(audioSampleCount/samplesPerFrame))

        hasLoudAudio = np.zeros((audioFrameCount))

        for i in range(audioFrameCount):
            start = int(i*samplesPerFrame)
            end = min(int((i+1)*samplesPerFrame),audioSampleCount)
            audiochunks = audioData[start:end]
            maxchunksVolume = float(misc_func.getMaxVolume(audiochunks))/maxAudioVolume
            if maxchunksVolume >= SILENT_THRESHOLD:
                hasLoudAudio[i] = 1

        chunks = [[0,0,0]]
        shouldIncludeFrame = np.zeros((audioFrameCount))
        for i in range(audioFrameCount):
            start = int(max(0,i-FRAME_SPREADAGE))
            end = int(min(audioFrameCount,i+1+FRAME_SPREADAGE))
            shouldIncludeFrame[i] = np.max(hasLoudAudio[start:end])
            if (i >= 1 and shouldIncludeFrame[i] != shouldIncludeFrame[i-1]): # Did we flip?
                chunks.append([chunks[-1][1],i,shouldIncludeFrame[i-1]])

        chunks.append([chunks[-1][1],audioFrameCount,shouldIncludeFrame[i-1]])
        chunks = chunks[1:]

        outputAudioData = np.zeros((0,audioData.shape[1]))
        outputPointer = 0

        lastExistingFrame = None
        for chunk in chunks:
            audioChunk = audioData[int(chunk[0]*samplesPerFrame):int(chunk[1]*samplesPerFrame)]

            sFile = TEMP_FOLDER+"/tempStart.wav"
            eFile = TEMP_FOLDER+"/tempEnd.wav"
            wavfile.write(sFile,SAMPLE_RATE,audioChunk)
            with WavReader(sFile) as reader:
                with WavWriter(eFile, reader.channels, reader.samplerate) as writer:
                    tsm = phasevocoder(reader.channels, speed=NEW_SPEED[int(chunk[2])])
                    tsm.run(reader, writer)
            _, alteredAudioData = wavfile.read(eFile)
            leng = alteredAudioData.shape[0]
            endPointer = outputPointer+leng
            outputAudioData = np.concatenate((outputAudioData,alteredAudioData/maxAudioVolume))

            # smooth out transitiion's audio by quickly fading in/out

            if leng < AUDIO_FADE_ENVELOPE_SIZE:
                outputAudioData[outputPointer:endPointer] = 0 # audio is less than 0.01 sec, let's just remove it.
            else:
                premask = np.arange(AUDIO_FADE_ENVELOPE_SIZE)/AUDIO_FADE_ENVELOPE_SIZE
                mask = np.repeat(premask[:, np.newaxis],2,axis=1) # make the fade-envelope mask stereo
                outputAudioData[outputPointer:outputPointer+AUDIO_FADE_ENVELOPE_SIZE] *= mask
                outputAudioData[endPointer-AUDIO_FADE_ENVELOPE_SIZE:endPointer] *= 1-mask

            startOutputFrame = int(math.ceil(outputPointer/samplesPerFrame))
            endOutputFrame = int(math.ceil(endPointer/samplesPerFrame))
            for outputFrame in range(startOutputFrame, endOutputFrame):
                inputFrame = int(chunk[0]+NEW_SPEED[int(chunk[2])]*(outputFrame-startOutputFrame))
                didItWork = misc_func.copyFrame(inputFrame,outputFrame, TEMP_FOLDER)
                if didItWork:
                    lastExistingFrame = inputFrame
                else:
                    misc_func.copyFrame(lastExistingFrame,outputFrame, TEMP_FOLDER)

            outputPointer = endPointer

        wavfile.write(TEMP_FOLDER+"/audioNew.wav",SAMPLE_RATE,outputAudioData)

        command = 'ffmpeg -v quiet -threads '+str(threads)+' -thread_queue_size 1024 -framerate '+str(frameRate)+' -i '+TEMP_FOLDER+'/newFrame%06d.jpg -i '+TEMP_FOLDER+'/audioNew.wav -strict -2 "'+OUTPUT_FILE+'"'
        subprocess.call(command, shell=True)
        misc_func.deletePath(TEMP_FOLDER)


    except Exception as e:
        print(e)
