from pathlib import Path
import time
import subprocess
import os
import math
from multiprocessing import Pool
import sys

import configparser
config_ini = configparser.ConfigParser()
config_ini.read('config.ini', encoding='utf-8')
setting = config_ini['DEFAULT']
FFMPEG_BIN = setting['FFMPEG_BIN']

GEN_THUMB = [FFMPEG_BIN+"/ffmpeg.exe", "-y", "-skip_frame", "nokey"]
GEN_THUMB_AFTER = ["-vsync", "vfr", "-q:v", "10"]
GET_FRAMES = [FFMPEG_BIN+"/ffprobe.exe", "-v", "error", "-select_streams", "v:0",
              "-count_packets", "-show_entries", "stream=nb_read_packets", "-of", "csv=p=0"]
GET_DURATION = [FFMPEG_BIN+"/ffprobe.exe", "-v", "error",
                "-show_entries", "format=duration", "-of", "csv=p=0"]


class PreviewThumbnailGenerator:
    cancel = False

    def __init__(self, path):
        self.target = path.replace(os.sep, '/')
        self.pool = Pool(1)

    def start(self):
        self.scan(Path(self.target))
        self.pool.close()
        self.pool.join()

    def stop(self, error):
        print(error)
        self.cancel = True

    def scan(self, path):
        if(self.cancel):
            return

        if(path.is_file()):
            try:
                self.gen(path)
            except Exception as e:
                print(e)
            return
        for file in path.glob('*[!.jpg]'):
            if(self.cancel):
                return
            self.scan(file)

    def gen(self, file):
        if(file.with_suffix('.jpg').exists()):
            return

        ret = subprocess.run(
            GET_DURATION + [PreviewThumbnailGenerator.getAbsolutePathString(file)], stdout=subprocess.PIPE,        encoding="utf-8")
        duration = PreviewThumbnailGenerator.tryParseInt(ret.stdout)
        if(duration == False):
            print("error on ffprobe. file: "+str(file))
            return

        self.pool.apply_async(PreviewThumbnailGenerator.genThumb,
                              args=(file, math.floor(duration/12),), error_callback=self.stop)

    @staticmethod
    def genThumb(file, interval):
        thumbFilename = PreviewThumbnailGenerator.getAbsolutePathString(
            file.with_suffix('.jpg'))

        subprocess.run(
            GEN_THUMB + ["-i", PreviewThumbnailGenerator.getAbsolutePathString(file)] + GEN_THUMB_AFTER + ["-vf", f'fps=fps=1/{interval}:round=down,scale=320:240,tile=4x3', thumbFilename], stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)

    @staticmethod
    def getAbsolutePathString(path):
        return str(path.resolve())

    @staticmethod
    def tryParseInt(str):
        try:
            return int(float(str))
        except ValueError:
            return False


if __name__ == "__main__":
    target = setting['DEFAULT_TARGET']
    args = sys.argv
    if(len(args) == 2):
        target = args[1]
    elif(not target):
        print("no arg")
        exit()

    start = time.time()
    generator = PreviewThumbnailGenerator(target)
    try:
        generator.start()
    except KeyboardInterrupt:
        generator.stop()
    print('{} seconds.'.format((time.time() - start)))
