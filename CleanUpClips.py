import configparser
import shutil


config = configparser.ConfigParser()
config.read('config.ini')
directory_to_remove = config.get('paths', 'output_dir')
keep_clips = config.getboolean('settings', 'keep_clips')

if not keep_clips:
    shutil.rmtree(directory_to_remove, ignore_errors=True)