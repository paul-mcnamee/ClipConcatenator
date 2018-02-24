import shutil
import glob
import base64
import json
import os
import datetime
import requests as re
import re as regex
import logging
import time
import configparser


config = configparser.ConfigParser()
config.read('config.ini')
output_directory = config.get('paths', 'output_dir')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# create a file handler
handler = logging.FileHandler(datetime.date.today().strftime('%Y-%m-%d') + '_downloads' + '.log')
handler.setLevel(logging.INFO)

# create a logging format
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)

# add the handlers to the logger
logger.addHandler(handler)

start_time = datetime.datetime.now()
num_downloaded_clips = 0
with open('twitch_headers.json') as json_data:
    headers = json.load(json_data)
    headers = headers[0]


def increase_downloaded_clip_count():
    global num_downloaded_clips
    num_downloaded_clips = num_downloaded_clips + 1


def parse_twitch_clip_url_response(content):
    """
    parse the initial url that we get from the twitch API to get the mp4 download links
    the first link is the highest or source quality
    :param content: text response from the get request to parse through and find the clip download links
    :return: url containing the mp4 download link
    """
    # Examples:
    # https://clips-media-assets.twitch.tv/vod-184480263-offset-8468.mp4
    # https://clips-media-assets.twitch.tv/26560534848-offset-21472.mp4
    # https://clips-media-assets.twitch.tv/26560534848.mp4
    match = regex.findall(r'https\:\/\/clips-media-assets.twitch.tv\/\w*\-*\d+\-*\w*\-*\d*\.mp4', content)
    if match.__len__() > 0:
        # NOTE: the first one is always the highest quality
        logger.info("found clip url: %s", match[0])
        return match[0]
    else:
        return ""


def download(url, file_name):
    """
    download the clip to a local folder
    :param url: url which contains a clip download link (mp4 in most cases)
    :param file_name: file name to generate and output content of the url to
    :return: none
    """
    os.makedirs(os.path.dirname(file_name), exist_ok=True)
    logger.info("downloading %s from %s", file_name, url)
    with open(file_name, "wb") as file:
        response = re.get(url)
        file.write(response.content)


def add_optional_query_params(url, channel, cursor, game_name, language, limit, period, trending):
    """
    Not all of the parameters are required, and the behavior is different if some are omitted.
    This whole thing is probably not necessary, but it's ok because it works right? Ship it.
    :param url:
    :param channel:
    :param cursor:
    :param game_name:
    :param language:
    :param limit:
    :param period:
    :param trending:
    :return:
    """
    new_url = url + "?"
    if channel != "":
        new_url = new_url + "channel=" + channel + "&"
    if cursor != "":
        new_url = new_url + "cursor=" + cursor + "&"
    if game_name != "":
        new_url = new_url + "game=" + game_name + "&"
    if language != "":
        new_url = new_url + "language=" + language + "&"
    if limit != "":
        new_url = new_url + "limit=" + limit + "&"
    if period != "":
        new_url = new_url + "period=" + period + "&"
    if trending != "":
        new_url = new_url + "trending=" + trending + "&"
    return new_url


def delete_clips_from_list(clips, indices_to_delete):
    for index in sorted(indices_to_delete, reverse=True):
        del clips[index]
    return clips


def delete_clips_with_close_times(current_clip, clips_to_check):
    """
    Delete the duplicate clips for any given channel if the times are close
    Multiple clips might be generated of the same content but they both may show up if they are popular
    If there is a duplicate then we will keep the longest duration clip, and delete the shorter one
    :param current_clip: clip that we are comparing
    :param clips_to_check: list of clips that we will compare against
    :return: list of clips without duplicates
    """
    tolerance = 30
    need_to_delete = False
    index_to_delete = clips_to_check.index(current_clip)
    indices_to_delete = set()
    for index, clip_to_check in enumerate(clips_to_check):
        if current_clip['slug'] == clip_to_check['slug']:
            continue
        if clip_to_check['vod'] is None:
            indices_to_delete.add(index)
            logger.info("clip_to_check['vod'] is none for %s", clip_to_check)
            continue
        if current_clip['vod'] is None:
            logger.info("current_clip['vod'] is none for %s", current_clip)
            indices_to_delete.add(index)
            continue
        current_clip_offset = current_clip['vod']['offset']
        clip_to_check_offset = clip_to_check['vod']['offset']
        min_offset = current_clip_offset - tolerance
        max_offset = current_clip_offset + tolerance
        if (min_offset <= clip_to_check_offset <= max_offset) \
                and (clip_to_check['broadcaster']['display_name'] == current_clip['broadcaster']['display_name']):
            logger.info("Similar clip offsets found, clip_to_check_offset=%s current_clip_offset=%s",
                        clip_to_check_offset, current_clip_offset)
            if current_clip['views'] > clip_to_check['views']:
                logger.info("current_clip['views']=%s clip_to_check['views']=%s deleting %s"
                            , current_clip['views'], clip_to_check['views'], clip_to_check)
                index_to_delete = index
            else:
                logger.info("current_clip['views']=%s clip_to_check['views']=%s deleting %s"
                            , current_clip['views'], clip_to_check['views'], current_clip)
                index_to_delete = clips_to_check.index(current_clip)
            if index_to_delete not in indices_to_delete:
                indices_to_delete.add(index_to_delete)
    logger.info("indices_to_delete=%s", str(indices_to_delete))
    return delete_clips_from_list(clips_to_check, indices_to_delete)


def delete_clips_with_low_views(clips_to_check, min_number_of_views):
    """
    There are too many clips to encode, so we only want the really popular ones
    therefore, we are removing the clips if the views are under a certain threshold.
    :param min_number_of_views: minimum number of views required for clips to be downloaded
    :param clips_to_check: clip array to look at to remove clips with low views
    :return:
    """
    indices_to_delete = set()
    for index, clip_to_check in enumerate(clips_to_check):
        if clip_to_check['views'] < min_number_of_views:
            indices_to_delete.add(index)
    return delete_clips_from_list(clips_to_check, indices_to_delete)


def delete_excess_clips(clips):
    """
    We want to remove additional clips to minimize the amount of clips we need to download
    Check the total length of clips that we will combine
    Remove clips with the least number of views until the length is suitable
    :param clips: list of clips to evaluate
    :return:
    """
    indices_to_delete = set()
    combined_clip_time_seconds = 0
    logger.info("finding excess clips to delete")
    # sort clips in order of views
    clips = sorted(clips, key=lambda k: k['views'], reverse=True)

    # iterate through the list until the max length is reached (10 minutes)
    for index, clip in enumerate(clips):
        if combined_clip_time_seconds >= 600:
            indices_to_delete.add(index)
            continue
        combined_clip_time_seconds = combined_clip_time_seconds + int(clip['duration'])
    logger.info("combined_clip_time_seconds=%s", combined_clip_time_seconds)
    logger.info("excess clip indices to delete=%s", str(indices_to_delete))
    if combined_clip_time_seconds < 60:
        logger.info("Not enough time in clips, returning nothing, combined_clip_time_seconds=%s"
                    , combined_clip_time_seconds)
        clips = []
    return delete_clips_from_list(clips, indices_to_delete)


def copy_existing_clip(clip, base_directory, path_to_copy_file, copy_clip_info=True, look_for_encoded_clip=False):
    """
    Check if we already downloaded the same clip
    Copy the clip to the new location
    :param clip:
    :param base_directory:
    :param path_to_copy_file:
    :param copy_clip_info:
    :param look_for_encoded_clip:
    :return:
    """
    clip_exists = False

    res = [f for f in glob.iglob(base_directory + "/**/*.mp4", recursive=True)
           if str(clip['slug'] + ("_encoded" if look_for_encoded_clip else "")) in f]
    if res.__len__() > 0:
        # clip found as a duplicate already downloaded elsewhere
        logger.info("Clip %s already exists at %s", str(clip['slug']), str(res[0]))
        clip_exists = True
        res2 = [f for f in glob.iglob(os.path.dirname(path_to_copy_file) + "/**/*.mp4", recursive=True) if
                str(clip['slug'] + ("_encoded" if look_for_encoded_clip else "")) in f]
        if not res2.__len__() > 0:
            # clip is not copied to the current folder, copy the clip
            logger.info("Found already downloaded file at %s copying file to %s", res[0], path_to_copy_file)
            shutil.copy2(res[0], path_to_copy_file)

            # also copy clip info
            if copy_clip_info:
                res3 = [f for f in glob.iglob(os.path.dirname(base_directory) + "/**/*.txt", recursive=True) if
                        str(clip['slug']) in f and 'clipInfo' in f]
                if res3.__len__() > 0:
                    shutil.copy2(res3[0], os.path.dirname(path_to_copy_file))
    return clip_exists


def get_clips_from_twitch(channel, cursor, game_name, language, limit, period, trending, category, game=''):
    """
    Gets the clips from the twitch api for the given parameters
            https://dev.twitch.tv/docs/v5/reference/clips#get-top-clips
    :param channel: string  	Channel name. If this is specified, top clips for only this channel are returned; otherwise, top clips for all channels are returned. If both channel and game are specified, game is ignored.
    :param cursor: string 	    Tells the server where to start fetching the next set of results, in a multi-page response.
    :param game_name: string  	Game name. (Game names can be retrieved with the Search Games endpoint.) If this is specified, top clips for only this game are returned; otherwise, top clips for all games are returned. If both channel and game are specified, game is ignored.
    :param language: string  	Comma-separated list of languages, which constrains the languages of videos returned. Examples: es, en,es,th. If no language is specified, all languages are returned. Default: "". Maximum: 28 languages.
    :param limit: long 	    Maximum number of most-recent objects to return. Default: 10. Maximum: 100.
    :param period: string 	    The window of time to search for clips. Valid values: day, week, month, all. Default: week.
    :param trending: boolean 	If true, the clips returned are ordered by popularity; otherwise, by viewcount. Default: false.
    :param category: the type of clips we are getting combining together for the end video -- channel, game, etc.
    :return:
    """
    url = ''
    try:
        base_url = "https://api.twitch.tv/kraken/clips/top"
        url = add_optional_query_params(base_url, channel, cursor, game_name, language, limit, period, trending)
        response = re.get(url, headers=headers)
        game_info_was_saved = False
        if response.status_code == 200:
            clips = response.json()['clips']
            for index, clip in enumerate(clips):
                logger.info("Attempting to remove duplicate clips from the retrieved list.")
                clips = delete_clips_with_close_times(clip, clips)
            clips = delete_clips_with_low_views(clips, 200)
            clips = delete_excess_clips(clips)
            for clip in clips:
                clip_response_page = re.get(clip['url']).text
                download_url = parse_twitch_clip_url_response(clip_response_page)
                if download_url.__len__() > 0:
                    broadcaster_name = clip['broadcaster']['display_name']
                    if channel == '' and game_name == '':
                        broadcaster_name = "all_top_twitch"
                    elif channel == '' and game_name != '':
                        # some games have unsafe characters (CS:GO) so we have to do the encoding for names
                        # https://stackoverflow.com/questions/295135/turn-a-string-into-a-valid-filename
                        broadcaster_name = base64.urlsafe_b64encode(game_name.encode('ascii'))
                    output_path = output_directory + datetime.date.today().strftime('%Y-%m-%d') \
                                  + "/" + category + "/" + str(broadcaster_name) + "/"
                    os.makedirs(os.path.dirname(output_path), exist_ok=True)
                    if not game_info_was_saved and game != '':
                        logger.info("Saving game info for %s", game)
                        with open(output_path + 'game_info.txt', 'w', encoding='utf-8') as outfile:
                            json.dump(game, outfile)
                        game_info_was_saved = True
                    clip_file_name = output_path + str(clip['views']) + "_" + clip['slug'] + ".mp4"
                    if not copy_existing_clip(clip, output_directory, clip_file_name):
                        logger.info("Starting a clip download for %s", str(broadcaster_name))
                        download(download_url, clip_file_name)
                        increase_downloaded_clip_count()
                        logger.info("Dumping clip info for %s", str(broadcaster_name))
                        with open(output_path + "clipInfo_" + clip['slug'] + '.txt', 'w', encoding='utf-8') as outfile:
                            json.dump(clip, outfile)
                    logger.info("Waiting some time before attempting to download the next clip")
                    time.sleep(2)
                else:
                    logger.info("Download url was empty for clip=%s", clip)
        else:
            logger.warning("Failed to get a valid response when attempting to retrieve clips"
                           ", response=%s for url=%s", response, url)
    except:
        logger.warning("Failed to download a clip for url=%s", url)


def get_popular_games_list(number_of_games):
    """
    Generate the list of games from twitch
    :return: list of games
    """
    url = "https://api.twitch.tv/kraken/games/top?limit=" + str(number_of_games)
    response = re.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()['top']
    else:
        logger.warning("failed to retrieve top games list with url=%s", url)
        return ['']


def get_popular_channel_list():
    #     https://socialblade.com/twitch/top/100/followers
    # TODO: we could use some api call to populate this, though I don't think it would really change all that much...
    # would be good to get this list from a text file so we don't have to update this array
    # return ['lirik']
    # removed: 'riotgames', 'mlg_live', 'mlg', 'dreamhackcs', 'sgdq', 'gamesdonequick', 'faceittv', 'Faceit', 'eleaguetv', 'thenadeshot', 'twitch', 'e3', 'nalcs1', 'starladder5', 'pgl', 'bobross',
    return ['syndicate', 'summit1g', 'nightblue3', 'imaqtpie', 'lirik', 'sodapoppin',
            'meclipse', 'shroud', 'tsm_bjergsen', 'joshog', 'dyrus', 'gosu', 'castro_1021', 'timthetatman',
            'captainsparklez', 'goldglove', 'boxbox', 'speeddemosarchivesda',
            'drdisrespectlive', 'nl_kripp', 'trick2g', 'swiftor', 'c9sneaky', 'doublelift',
            'sivhd', 'iijeriichoii', 'Voyboy', 'faker', 'izakooo',
            'tsm_theoddone', 'pewdiepie', 'cohhcarnage', 'pashabiceps', 'amazhs', 'anomalyxd', 'ungespielt',
            'loltyler1', 'trumpsc', 'kinggothalion', 'omgitsfirefoxx',
            'nadeshot', 'kittyplays', 'stonedyooda', 'yoda', 'Gronkh', 'GiantWaffle', 'nick28t',
            'monstercat', 'gassymexican', 'montanablack88', 'cryaotic', 'reckful', 'a_seagull', 'm0e_tv',
            'forsenlol', 'kaypealol', 'sovietwomble', 'ProfessorBroman', 'nickbunyun',
            'dansgaming', 'yogscast', 'zeeoon', 'rewinside', 'legendarylea', 'ninja',
            'markiplier', 'pokimane', 'froggen', 'aphromoo', 'olofmeister', 'followgrubby']


def main():
    logger.info("Starting Downloader Process.")
    cursor = ""
    game_name = ""
    language = "en"
    limit = "30"
    period = "day"
    trending = ""

    # TODO: add these back once we figure out how to encode videos faster, right now it's taking way too long...
    #
    # logger.info("Getting the top clips from the top channels.")
    # channels = get_popular_channel_list()
    # for channel in channels:
    #     get_clips_from_twitch(channel, cursor, game_name, language, limit, period, trending, category='channels')

    logger.info("Getting the top clips from the top games.")
    channel = ""
    games = get_popular_games_list(15)
    category = 'games'
    for game in games:
        get_clips_from_twitch(channel, cursor, game['game']['name'], language, limit, period, trending, category, game)

    logger.info("Getting the top clips from all of twitch.")
    channel = ""
    period = "day"
    limit = "30"
    category = 'twitch'
    get_clips_from_twitch(channel, cursor, game_name, language, limit, period, trending, category)

    end_time = datetime.datetime.now()
    total_processing_time_sec = (end_time - start_time).total_seconds()
    logger.info("Downloaded %s clips in %s seconds", num_downloaded_clips, total_processing_time_sec)
    logger.info("FINISHED!!!")


if __name__ == "__main__":
    main()

