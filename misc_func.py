from pytube import YouTube
from time import sleep
import os
import numpy as np
from shutil import copyfile, rmtree, move
import platform

def getMaxVolume(s):
    maxv = float(np.max(s))
    minv = float(np.min(s))
    return max(maxv,-minv)

def downloadFile(url):
    sleep(10)
    name = YouTube(url).streams.first().download()
    return name

def copyFrame(inputFrame,outputFrame, TEMP_FOLDER):
    src = TEMP_FOLDER+"/frame{:06d}".format(inputFrame+1)+".jpg"
    dst = TEMP_FOLDER+"/newFrame{:06d}".format(outputFrame+1)+".jpg"
    if not os.path.isfile(src):
        return False
    copyfile(src, dst)
    return True

def createPath(s):
    try:
        os.mkdir(s)
    except OSError:
        assert False, "Creation of the directory {} failed. (The folder may already exist. Delete or rename it, and try again.)".format(s)

def deletePath(s): # Dangerous! Watch out!
    try:
        rmtree(s,ignore_errors=False)
    except OSError:
        print ("Deletion of the directory %s failed" % s)
        print(OSError)
def fix_input(input):
    if platform.system() == 'Linux':
        input = input.split("/")
    else:
        input = input.split("\\")
    return input[-1]
