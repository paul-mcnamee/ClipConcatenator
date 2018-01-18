#!/usr/bin/python

import httplib2
import sys

from googleapiclient.discovery import build
from google.oauth2 import service_account

from oauth2client.client import flow_from_clientsecrets
from oauth2client.tools import run_flow
from oauth2client.file import Storage
from oauth2client.contrib import gce


# The CLIENT_SECRETS_FILE variable specifies the name of a file that contains
# the OAuth 2.0 information for this application, including its client_id and
# client_secret.
CLIENT_SECRETS_FILE = "youtube_api_client_secrets.json"

# This OAuth 2.0 access scope allows for full read/write access to the
# authenticated user's account.
SCOPES = ['https://www.googleapis.com/auth/youtube']
YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"


def get_authenticated_service():
    credentials = service_account.Credentials.from_service_account_file(CLIENT_SECRETS_FILE, scopes=SCOPES)
    return build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION, credentials=credentials)


def main():
    pass


if __name__ == "__main__":
    main()
