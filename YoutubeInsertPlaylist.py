#!/usr/bin/python


from googleapiclient.errors import HttpError
from oauth2client.tools import argparser

import YoutubeBase


def insert_playlist(youtube, title, description, privacy_status):
    playlist_insert_response = youtube.playlists().insert(
      part="snippet,status",
      body=dict(
        snippet=dict(
          title=title,
          description=description
        ),
        status=dict(
          privacyStatus=privacy_status
        )
      )
    ).execute()

    print("New playlist id: %s" % playlist_insert_response["id"])


# Remove keyword arguments that are not set
def remove_empty_kwargs(**kwargs):
    good_kwargs = {}
    if kwargs is not None:
        for key, value in kwargs.iteritems():
            if value:
                good_kwargs[key] = value
    return good_kwargs


def playlist_list_items(youtube, **kwargs):
    response = youtube.playlists().list(
        **kwargs
    ).execute()
    print(response)

def main():

    youtube = YoutubeBase.get_authenticated_service()
    try:
        playlist_list_items(youtube,
                            part='snippet,contentDetails',
                            )
        # insert_playlist(youtube, "test title", "test description", "private")
    except HttpError as e:
        print("An HTTP error %d occurred:\n%s" % (e.resp.status, e.content))


if __name__ == "__main__":
    main()

