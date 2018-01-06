import json
import datetime
import subprocess
import glob
import os
import base64
import logging
from datetime import timedelta


# needs to be the output directory from the DownloadTwitchClips.py results
youtube_uploader_dir = 'D:/VideoConcatenator/'
clips_dir = 'C:/temp/' + str((datetime.date.today() - timedelta(days=1)).strftime('%Y-%m-%d'))
# clips_dir = 'C:/temp/2017-12-26'

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# create a file handler
handler = logging.FileHandler(datetime.date.today().strftime('%Y-%m-%d') + '_uploader' + '.log')
handler.setLevel(logging.INFO)

# create a logging format
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)

# add the handlers to the logger
logger.addHandler(handler)

def upload_to_youtube(category_id, file_location, description, tags, title, privacy):
    # https://github.com/porjo/youtubeuploader
    base_call = './youtubeuploader.exe'
    logger.info('Attempting to upload clip from %s with description %s', file_location, description)
    args = [base_call, '-categoryId', category_id, '-description', description, '-filename', file_location, '-tags', tags, '-title', title, '-privacy', privacy]
    try:
        command_line_process = subprocess.Popen(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )

        process_output, _ = command_line_process.communicate()
        process_output = str(process_output)
        logging.info(process_output)
        if 'Upload successful' in process_output:
            # TODO: we can probably do something with this later if we want to modify the uploads or check if it's on YT
            logger.info('Upload was successful!')
            video_id = process_output.split('Video ID: ')[1]
            video_id = video_id.split('\\n')[0]
    except OSError as exception:
        logging.info('Exception occured: ' + str(exception))
        logging.info('Subprocess failed')
        return False
    else:
        # no exception was raised
        logging.info('Subprocess finished')


# find combined_description.txt and associated combined.mp4
def find_clips_to_upload(directory):
    clips = []
    files = [f for f in glob.glob(directory + "\combined_description.txt")]
    if files.__len__() > 0:
        for file in files:
            with open(file, encoding='utf-8') as data_file:
                description = data_file.read()
                clip_path = os.path.dirname(file) + '\combined.mp4'
                clips.append([description, clip_path])
    return clips


def generate_title_for_clip(clip):
    clip_dir = os.path.dirname(clip)
    title = 'Top Twitch Clips Recap - '
    additional_tags = ""
    if 'games' in clip_dir:
        # TODO: maybe we should use regex to get the byte string instead of splitting with '
        game_name = base64.urlsafe_b64decode(bytes(clip_dir.split('\'')[1], 'ascii')).decode('utf-8')
        title = title + game_name
        additional_tags = ", " + game_name
    else:
        subdir_parts = os.path.split(clip_dir)
        subdir = subdir_parts[subdir_parts.__len__() - 1]
        title = title + subdir
        additional_tags = ", " + str(subdir)
    return str(title + " - " + datetime.date.today().strftime('%Y-%m-%d')), additional_tags


def add_tag_if_not_added(tags, tag):
    if tag not in tags:
        # tags string has a max length of 500 characters
        # https://developers.google.com/youtube/v3/docs/videos
        if (tags.__len__() + tag.__len__()) < 500:
            tags = tags + ", " + tag
    return tags


def tags_from_clip_info(clip, tags):
    # get the directory of the clip
    directory = os.path.dirname(clip)

    # get the clipInfo files
    files = glob.glob(directory + '\clipInfo_*.txt')
    logger.info('Generating tags from clip list')
    if files.__len__() > 0:
        for file in files:
            with open(file, encoding='utf-8') as data_file:
                data = json.load(data_file)

                # add the tags if they don't exist already
                tags = add_tag_if_not_added(tags, data["broadcaster"]["display_name"])
                # TODO: use a list of alias names for the game, and add the game alias names
                # tags = add_tag_if_not_added(tags, data["game"])
                # tags = add_tag_if_not_added(tags, data["title"])
    return tags


def generate_tags_for_clip(clip, additional_tags):
    tags = "twitch, tv, clip, clips, fail, fails, compilation, perfect, timing, girl, girls, highlight, highlights, " \
           "donation, donations, moment, moments, crazy, best, top"
    tags = tags + additional_tags # currently just the game name generated from the folder
    tags = tags_from_clip_info(clip, tags)
    return tags


def clean_tags(tags):
    # remove all non-alpha numeric characters
    tags = ''.join(c for c in tags if (c.isalnum() or c == '-' or c == '_' or c == ' '))
    tags = tags.replace(' ', ', ')
    return tags


logger.info("Starting Uploader Process.")
all_dirs = [directory_with_clips[0] for directory_with_clips in os.walk(clips_dir)]
for current_dir in all_dirs:
    logger.info('Finding clips to upload to youtube.')
    clips = find_clips_to_upload(current_dir)
    logger.info('Found %s clips to upload in %s', str(clips.__len__()), current_dir)
    for clip in clips:
        logger.info('Generating title and tags for clip.')
        clip_title, additional_tags = generate_title_for_clip(clip[1])
        # TODO: check youtube for clip name if it exists already
        tags = generate_tags_for_clip(clip[1], additional_tags)
        tags = clean_tags(tags)
        logging.info(tags)
        category_id = "20"  # gaming
        logger.info('Starting upload for clip.')
        upload_to_youtube(category_id, clip[1], clip[0], tags, clip_title, "public")
        # TODO: delete or move the uploaded clips ?? currently just manually moving to the 4TB drive
