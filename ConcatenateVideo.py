from glob import glob
import os
import json
import subprocess
import datetime
import logging

# TODO: AFTER THIS IS FULLY WORKING: we should look for the "combined" clip name to potentially skip so we can pick up where we previously left off if the process failed or add something to flag the directory and remove it from the list to process
# TODO: combine the files with transitions (not sure about transitions or not) (1, 2, 3, etc.) for top 5 or top 10 videos

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# create a file handler
handler = logging.FileHandler(datetime.date.today().strftime('%Y-%m-%d') + '_concat' + '.log')
handler.setLevel(logging.INFO)

# create a logging format
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)

# add the handlers to the logger
logger.addHandler(handler)

# start_dir needs to be the output directory from the DownloadTwitchClips.py results
start_dir = 'C:/temp/' + str(datetime.date.today().strftime('%Y-%m-%d'))
outro_clip_path = 'C:/clips/intro.mp4' # TODO: Create this
intro_clip_path = 'C:/clips/intro.mp4'
watermark_image_path = 'C:/clips/watermark.png' # TODO: Create this
ffmpeg_path = 'C:/ffmpeg/bin/ffmpeg.exe'
output_dir = 'C:/combined_clips/'


def generate_description_text(clips):
    """
    Create the description for the clips, this is mainly to give credit to the people who own the clips
    :param clips:
    :return:
    """
    description = 'Clip Sources: \n'
    logger.info('Generating description for combined clips.')
    for index, clip in enumerate(clips):
        description += "#" + str(index + 1) + " " + clip["broadcaster"] + " " \
                       + clip["broadcaster_url"] + "\n"
    logger.info('Description: %s', description)
    return description


def generate_clip_list(directory):
    """
    find all of the actual clips to combine for the current directory
    :param directory:
    :return:
    """
    clips = []
    combined_files = glob(directory + '\combined.mp4')
    if combined_files.__len__() > 0:
        return clips
    files = glob(directory + '\clipInfo_*.txt')
    logger.info('Generating clip list')
    if files.__len__() > 0:
        for file in files:
            with open(file, encoding='utf-8') as data_file:
                data = json.load(data_file)
                file = file.replace('\\', '/')
                file_name = os.path.dirname(file) + "/" + str(data["views"]) + "_" + data["slug"] + ".mp4"
                file_name = os.path.normpath(file_name)
                slug = data["slug"]
                clip_info_file_name = "clipInfo_" + slug + ".txt"
                views = data["views"]
                broadcaster = data["broadcaster"]["display_name"]
                broadcaster_url = data["broadcaster"]["channel_url"]

                clips.append({'slug': slug,
                              'views': views,
                              'broadcaster': broadcaster,
                              'broadcaster_url': broadcaster_url,
                              'file_name': file_name,
                              'clip_info_file_name': clip_info_file_name
                              })
    return clips


def sort_clips(clips):
    """
    Sort the clips in order of views and move the 2nd most popular clip to the end of the video so the user
    ends on a good note and starts on a good note.
    :param clips:
    :return:
    """
    if clips.__len__() < 3:
        return clips
    logger.info('Sorting clips in order of views.')
    # sort clips in order of views
    clips = sorted(clips, key=lambda k: k['views'], reverse=True)
    tmp = clips

    # move the 2nd most popular clip to the end of the list to give them something good at the end of the video
    tmp.append(clips[1])
    tmp.pop(1)
    clips = tmp
    return clips


def encode_clip(clip, output_clip_path):
    """
    Encodes a clip using ffmpeg for a given clip and outputs it to the specified path
    :param clip:
    :param output_clip_path:
    :return:
    """
    # TODO: probably better to just not use a file for this since it's a single clip each time...
    # Delete the file of clips to encode
    try:
        os.remove("clips_to_encode.txt")
    except OSError:
        pass

    name, ext = os.path.splitext(output_clip_path)
    output_clip_path = "{name}_encoded{ext}".format(name=name, ext=ext)

    # Check if the encoded clip already exists
    if os.path.exists(output_clip_path):
        logger.info('Encoded clip already exists! %s', clip["file_name"])
        return True, output_clip_path

    logger.info('Encoding clip %s', clip["file_name"])
    # write the clip path to the file to encode
    with open("clips_to_encode.txt", 'w', encoding='utf-8') as outfile:
        clip_file_name = os.path.normpath(clip["file_name"]).replace('\\', '/').replace('\'', '\\\'')
        outfile.write("file " + clip_file_name + "\n")
        outfile.close()

    # encode the file
    args = ["-y", "-f", "concat", "-safe", "0", "-i", "clips_to_encode.txt", "-c:a", "aac",
            "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-pix_fmt", "yuv420p",
            "-s", "1920x1080", "-r", "60", "-vbr", "5", "-ac", "2", "-ar", "44100", "-vsync", "0",
            output_clip_path]
    run_ffmpeg(args)
    success = os.path.isfile(output_clip_path)
    return success, output_clip_path


def combine_clips(clips):
    """
    Concatenate the clips together and add the intro and outro
    :param clips:
    :return:
    """
    logger.info('Starting the concatenation process.')
    success = False
    clip_description = "Included Twitch Clips:\n"
    combined_clip_name = "combined.mp4"
    combined_clip_path = os.path.dirname(clips[0]["file_name"]) + "\\" + combined_clip_name
    os.chdir(os.path.dirname(clips[0]["file_name"]))

    # re-encode each clip since the bitrate and fps may change with each clip
    with open("clips_to_combine.txt", 'w', encoding='utf-8') as outfile:
        outfile.write("file " + intro_clip_path + "\n")
        for index, clip in enumerate(clips):
            clip_to_find = clip["file_name"]
            slug_from_clip = os.path.basename(clip_to_find).split('_')[1].split('.')[0]
            clip_path = glob(os.path.dirname(clip_to_find) + '\\*_' + slug_from_clip + '.mp4', recursive=False)[0]
            success, encoded_clip_path = encode_clip(clip, clip_path)
            if success:
                clip_description = clip_description + "Clip #" + str(index + 1) + " " + clip["broadcaster"] + ": " + clip["broadcaster_url"] + "\n"
                outfile.write("file " + os.path.normpath(encoded_clip_path).replace('\\', '/').replace('\'', '\\\'') + "\n")
        outfile.write("file " + outro_clip_path + "\n")
        outfile.close()

    args = ["-y", "-f", "concat", "-safe", "0", "-i", "clips_to_combine.txt", "-c:a", "aac",
            "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-pix_fmt", "yuv420p",
            "-s", "1920x1080", "-r", "60", "-vbr", "5", "-ac", "2", "-ar", "44100", "-vsync", "0",
            combined_clip_path]
    run_ffmpeg(args)
    success = os.path.isfile(combined_clip_path)

    # save the description of the combined clips
    with open(os.path.dirname(combined_clip_path) + "\combined_description.txt", 'w', encoding='utf-8') as outfile:
        outfile.write(clip_description)
        outfile.close()

    return success, combined_clip_path, clip_description


def add_watermark(clip):
    """
    Add the watermark to the specified clip (normally this would be done at the end)
    NOTE: we could possibly just do this with youtube, they have a watermark feature for video uploads.
    :param clip:
    :return:
    """
    logger.info('Adding watermark to clip.')
    success = False
    watermarked_clip_name = "watermarked.mp4"
    watermarked_clip_path = os.path.dirname(clips[0]["file_name"]) + "\\" + watermarked_clip_name
    # ffmpeg -i input -i logo -filter_complex 'overlay=10:main_h-overlay_h-10' output
    args = ["-y", "-i", clip, "-i", watermark_image_path, "-filter_complex", "overlay=5:H-h-5:format=rgb,format=yuv420p", "-codec:a", "copy", watermarked_clip_path]
    run_ffmpeg(args)
    success = os.path.isfile(watermarked_clip_path)
    return success, watermarked_clip_path


def run_ffmpeg(args):
    """
    Invoke ffmpeg via command line with the arguments specified
    :param args:
    :return:
    """
    args.insert(0, ffmpeg_path)
    subprocess.call(args)


logger.info("Starting Concat Process.")
# start_dir = 'C:/temp/'
# start_dir = 'C:/temp/2017-11-21/games'
all_dirs = [directory_with_clips[0] for directory_with_clips in os.walk(start_dir)]

for current_dir in all_dirs:
    # we only want directories with clips in them
    clips_to_combine = []
    clips = generate_clip_list(current_dir)
    if clips.__len__() > 0:
        sort_clips(clips)
        for clip in clips:
            clips_to_combine.append(clip)

        # combine the clips with the intro and outro and add the watermark
        # description_text = generate_description_text(clips)
        success, clip_path, clip_description = combine_clips(clips_to_combine)
        # skip adding the watermark -- don't think it's necessary
        # success, clip_path = add_watermark(clip_path)
