# video-dl script

The purpose of this script is to simplify the usage of [yt-dlp](https://github.com/yt-dlp/yt-dlp).
<p align="center">
<img src="https://i.imgur.com/HP9yvMm.png">
</p>


## Requirements

### Windows
All the requirements are embedded within the installer.

### Linux
* You need to install both `ffmpeg` and `ffprobe` manually. Most Linux distributions have these in their package manager.
* In order to use QSV, you must have the `intel-mediasdk` (apt) or `intel-media-sdk` (pacman) package installed.

### OSX
* For macOS users, Homebrew has the `ffmpeg` package which includes `ffprobe`. If python 3 was installed with Homebrew, you will also need the `python-tk` package.

## Downloads
The installer for Windows is available in the [releases](https://github.com/Kenshin9977/video-dl-script/releases) section.
The program isn't signed yet, so your browser will probably warn you when downloading it.


## Installation

### Windows
Simply run the installer. The program isn't signed yet, so you'll have a window popping up telling you the program isn't safe.

### UNIX
I plan to compile binaries for both OSX and Linux. In the meantime you can compile from the sources.

## Features

* Works with every website yt-dlp [supports](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md).
* Allows you to choose the max framerate and resolutions in which you want the videos in the selected resolution. It will try to find it but will get a lower value if this resolution/framerate isn't available.
* Allows you to only download the audio of a video, automatically converts the audio to MP3 320 kbps to ensure compatibility.
* Let you choose the start and end time of the video you want to download. It only downloads the part you selected but the download is slower since it's handled by ffmpeg and not av2conv.
* Allows you to get cookies from your browser in order to access restricted videos on Youtube only accessible if you log in.
* Saves videos with the name of the video followed by the author's name.
* Only remuxes videos if it is encoded in h264 (faster than recode and lossless) in order to ensure compatibility with every NLE software.
* Recodes the video in h264 if it is encoded with something else in order to ensure compatibility.
* Detects if a GPU capable of h264/h265 encoding is visible by the system and if there is, use it to encode the video rather than the CPU which is slower.
* Can download subtitles

## Usage

Launch Video-dl, enter a valid URL of a supported website, select the options you want then click "Download".

## Compile from sources

You need to install:
* Python >= 3.8
* The requirements listed in requirements.txt
* ffmpeg
* ffprobe

You can use pyinstaller to create a binary file. On Windows I'm using the following command line: 
`pyinstaller -wF --icon=icon.ico --name=Video-dl.exe video-dl/gui.py`

## Software used

* [yt-dlp](https://github.com/yt-dlp/yt-dlp)
* [ffmpeg](https://github.com/FFmpeg/FFmpeg)
* [PySimpleGUI](https://pysimplegui.readthedocs.io/en/latest/)
