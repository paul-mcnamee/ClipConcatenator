import configparser
import shutil
import time


config = configparser.ConfigParser()
config.read('config.ini')
directory_to_remove = config.get('paths', 'output_dir')
keep_clips = config.getboolean('settings', 'keep_clips')

if not keep_clips:
    # wait 15 minutes to ensure the last clip was uploaded...
    time.sleep(900)
    shutil.rmtree(directory_to_remove, ignore_errors=True)