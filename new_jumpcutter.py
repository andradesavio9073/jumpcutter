import argparse
import misc_func
import playlist_list
import threading
import multiprocessing
import neverland
from pytube import Playlist
from tqdm import tqdm
from time import sleep
import os
import gc

gc.enable()

parser = argparse.ArgumentParser(description='Modifies a video file to play at different speeds when there is sound vs. silence.')
parser.add_argument('-i', type=str,  help='the video file you want modified')
parser.add_argument('-u', type=str, help='A youtube url to download and process')
parser.add_argument('-t', type=int, default=int(multiprocessing.cpu_count()/4), help='Number of threads to use')
parser.add_argument('-o', type=str, default="", help="the output file. (optional. if not included, it'll use the input name)")
parser.add_argument('-dd', type=str, help="The directory to save the output to")
parser.add_argument('-p', type=str, help="A youtube playlist url to download and process")
parser.add_argument('--use_playlist_list', type=bool, choices=[True, False], default=False, help="Use Playlist List file")
parser.add_argument('--silent_threshold', type=float, default=0.03, help="the volume amount that frames' audio needs to surpass to be consider \"sounded\". It ranges from 0 (silence) to 1 (max volume)")
parser.add_argument('-sos', type=float, default=2, help="the speed that sounded (spoken) frames should be played at. Typically 1.")
parser.add_argument('-sis', type=float, default=20, help="the speed that silent frames should be played at. 999999 for jumpcutting.")
parser.add_argument('--frame_margin', type=float, default=5, help="some silent frames adjacent to sounded frames are included to provide context. How many frames on either the side of speech should be included? That's this variable.")
parser.add_argument('--sample_rate', type=float, default=44100, help="sample rate of the input and output videos")
parser.add_argument('--frame_rate', type=float, default=30, help="frame rate of the input and output videos. optional... I try to find it out myself, but it doesn't always work.")
parser.add_argument('--frame_quality', type=int, default=1, help="quality of frames to be extracted from input video. 1 is highest, 31 is lowest, 1 is the default.")
parser.add_argument('--playlist_init', type=int, default=0, help="If using a list of playlists. Define the initial point. In the case of code erroring out. Default is 0. Obviously. This isn't MATLAB you plebs.")
args = parser.parse_args()

#Globals
frameRate = args.frame_rate
SAMPLE_RATE = args.sample_rate
SILENT_THRESHOLD = args.silent_threshold
FRAME_SPREADAGE = args.frame_margin
NEW_SPEED = [args.sis, args.sos]
FRAME_QUALITY = args.frame_quality

playlist_itterator = args.playlist_init
threads = args.t
processCount = 0
global processLock

if not (False):
    playlist_list = [[args.dd, args.p]]
else:
    playlist_list = playlist_list.playlist_list


pid_itterator = 0
def jumpcutter(pid, INPUT_FILE, DestiD):
    global processCount
    global processLock
    OUTPUT_FILE = DestiD+"/"+misc_func.fix_input(INPUT_FILE)
    neverland.process(pid, threads, INPUT_FILE, OUTPUT_FILE, frameRate, SAMPLE_RATE, SILENT_THRESHOLD, FRAME_SPREADAGE, NEW_SPEED, FRAME_QUALITY)
    os.remove(INPUT_FILE)

    processLock.acquire()
    processCount -= 1        #Locks prevent race condition when modifying global var
    processLock.release()




if __name__ == '__main__':
    global processCount
    global processLock

    processLock = threading.Lock()

    for ddplaylist in playlist_list[playlist_itterator:]:
        playlist = Playlist(ddplaylist[1])
        playlist.populate_video_urls()
        dd = ddplaylist[0]
        misc_func.createPath(dd)
        for video in tqdm(playlist.video_urls):
            while processCount >= threads:    #Limits Number Of Active threads, only start new thread after old one is finished
                sleep(1)

            try:
                INPUT_FILE = misc_func.downloadFile(video)
            except:
                sleep(5)
                INPUT_FILE=misc_func.downloadFile(video)

            processLock.acquire()
            processCount += 1       #Locks prevent race condition when modifying global var
            processLock.release()

            P = threading.Thread(target=jumpcutter, args=(pid_itterator, INPUT_FILE, dd))       #Using threading instead of multiprocessing, allows global var modification
            P.start()

            pid_itterator=pid_itterator+1
