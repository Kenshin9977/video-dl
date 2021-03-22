# video-dl script

The purpose of this script is to simplify the usage of [youtube-dl](https://github.com/ytdl-org/youtube-dl).
## Features

* Works with every website youtube-dl [supports](https://ytdl-org.github.io/youtube-dl/supportedsites.html)
* Get videos in 1080p or less if this resolution isn't available.
* Let you choose the start and end time of the video you want to download.
* Force video recode in order to ensure compatibility with every editing software.
* Detects if a GPU capable of h264 encoding is visible by the system and if there is, use it to encode the downloaded video rather than the CPU which is slower.
## Downloads

Binaries for Windows are available in the [releases](https://github.com/Kenshin9977/VGCAT/releases) section.
## Installation

Extract the archive anywhere you want.
Go to script/ and launch install-update.bat which will download and place the latest versions of youtube-dl and ffmpeg in the bin folder. This script can also be used to update those binaries. This ensure to get the latest version when you use the script.
## Usage

Launch script/video-dl.bat, enter the URL of a video, select start and end time then close the window when finished or enter another URL. The files are downloaded in the downloads/ folder.
You can skip the start and end time part by changing the value in config/config.ini from false to true. It's useful if you always want to get the whole video.
## Software used

* [youtube-dl](https://github.com/ytdl-org/youtube-dl)
* [ffmpeg](https://github.com/FFmpeg/FFmpeg)
* [7zip](https://www.7-zip.org/download.html)
* [detect_hardware](https://github.com/Kenshin9977/Detect_hardware)
