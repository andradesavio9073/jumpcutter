from time import sleep
import os
import numpy as np
from shutil import copyfile, rmtree, move
import platform
import re
import subprocess
import youtube_dl
import os
import sys
import warnings

warnings.filterwarnings("ignore")

class MyLogger(object):
    def debug(self, msg):
        pass

    def warning(self, msg):
        pass

    def error(self, msg):
        print(msg)


def getMaxVolume(s):
    maxv = float(np.max(s))
    minv = float(np.min(s))
    return max(maxv,-minv)

def downloadFile(url):

    ydl = youtube_dl.YoutubeDL({'outtmpl': '%(id)s%(ext)s', 'logger':MyLogger(),})
    with ydl:
        result = ydl.extract_info(
            url,
            download=True
            )

    inputname = ''.join([result['id'], result['ext'], '.', result['ext']])
    alt_inputname = ''.join([result['id'], result['ext'], '.', 'mkv'])
    title = result['title']
    title = "".join([x if x not in "\/:*?<>|" else " " for x in title])
    exists = os.path.isfile(inputname)

    if exists:
        format = result['ext']
    else:
        inputname = alt_inputname
        format = 'mkv'
    return inputname, title, format

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
    except Exception as e:
        print(e)
        deletePath(s)
        os.mkdir(s)

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

def getFrameRate(path):
    process = subprocess.Popen(["ffmpeg", "-i", path], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    stdout, _ = process.communicate()
    output =  stdout.decode()
    match_dict = re.search(r"\s(?P<fps>[\d\.]+?)\stbr", output).groupdict()
    return float(match_dict["fps"])
