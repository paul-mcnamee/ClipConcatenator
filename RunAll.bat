@echo off
cmd /k "cd /d C:\Envs\VideoConcatenator\Scripts & activate & cd /d D:\VideoConcatenator & python DownloadTwitchClips.py & python ConcatenateVideo.py & python UploadClipsToYoutube.py"