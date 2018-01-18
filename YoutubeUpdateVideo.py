#!/usr/bin/python

import sys

from googleapiclient.errors import HttpError
from oauth2client.tools import argparser

import YoutubeBase


def update_video(youtube, options):
    # Call the API's videos.list method to retrieve the video resource.
    videos_list_response = youtube.videos().list(
        id=options.video_id,
        part='snippet'
    ).execute()

    # If the response does not contain an array of "items" then the video was
    # not found.
    if not videos_list_response["items"]:
        print("Video '%s' was not found." % options.video_id)
        sys.exit(1)

    # Since the request specified a video ID, the response only contains one
    # video resource. This code extracts the snippet from that resource.
    videos_list_snippet = videos_list_response["items"][0]["snippet"]

    # Preserve any tags already associated with the video. If the video does
    # not have any tags, create a new array. Append the provided tag to the
    # list of tags associated with the video.
    if "tags" not in videos_list_snippet:
        videos_list_snippet["tags"] = []
    videos_list_snippet["tags"].append(options.tag)

    # Update the video resource by calling the videos.update() method.
    videos_update_response = youtube.videos().update(
        part='snippet',
        body=dict(
            snippet=videos_list_snippet,
            id=options.video_id
        )).execute()


def main():
    argparser.add_argument("--video-id", help="ID of video to update.",
                           required=True)
    argparser.add_argument("--tag", default="youtube",
                           help="Additional tag to add to video.")
    args = argparser.parse_args()

    youtube = YoutubeBase.get_authenticated_service()
    try:
        update_video(youtube, args)
    except HttpError as e:
        print("An HTTP error %d occurred:\n%s" % (e.resp.status, e.content))

    else:
        print("Tag '%s' was added to video id '%s'." % (args.tag, args.video_id))


if __name__ == "__main__":
    main()
