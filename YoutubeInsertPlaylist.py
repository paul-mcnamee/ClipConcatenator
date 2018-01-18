#!/usr/bin/python

from googleapiclient.errors import HttpError

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


def playlist_list_items(youtube, **kwargs):
    response = youtube.playlists().list(
        **kwargs
    ).execute()
    print(response)


def channels(youtube, **kwargs):
    response = youtube.channels().list(
        **kwargs
    ).execute()
    print(response)
    return response


def main():
    youtube = YoutubeBase.get_authenticated_service()
    try:
        # https://developers.google.com/youtube/v3/docs/playlists/update
        playlist_list_items(youtube,
                            part='snippet, contentDetails',
                            channelId="UCvBAYfx-Cl540j2IYXGWqnA",
                            maxResults=25
                            )
        # insert_playlist(youtube, "test title", "test description", "private")
    except HttpError as e:
        print("An HTTP error %d occurred:\n%s" % (e.resp.status, e.content))


if __name__ == "__main__":
    main()

