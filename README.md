# video-dl script

The purpose of this script is to simplify the usage of [youtube-dl](https://github.com/ytdl-org/youtube-dl).

## Windows

### Requirements

* This script uses cURL which ships with Windows 10 1803 or later. You can also install it separately.

### Installation

Extract the archive anywhere you want.
Go to `scripts/` and launch `install_update_binaries.bat` which will download and place the latest versions of `youtube-dl` and `ffmpeg` in the bin folder. This script can also be used to update those binaries. This ensures to get the latest version when you use the script.

## UNIX

### Requirements

* You need to install both `youtube-dl` and `ffmpeg` manually. Most Linux distributions have these in their package manager. 
* In order to use QSV, you must have the `intel-mediasdk` (apt) or `intel-media-sdk` (pacman) package installed.
* For macOS users, Homebrew has the `youtube-dl` and `ffmpeg` packages. Videotoolbox API is used for hardware encoding.

### Installation

* Download and extract a copy of the repository.
* Go to the `scripts/` folder and run `video_dl.sh`, if both `youtube-dl` and `ffmpeg` are found and you are prompted to enter a URL, you are good to go.

## Features

* Works with every website youtube-dl [supports](https://ytdl-org.github.io/youtube-dl/supportedsites.html).
* Get videos in 1080p or less if this resolution isn't available.
* Let you choose the start and end time of the video you want to download.
* Force video recode in order to ensure compatibility with every editing software.
* Detects if a GPU capable of h264 encoding is visible by the system and if there is, use it to encode the downloaded video rather than the CPU which is slower.

## Downloads

The .zip for Windows is available in the [releases](https://github.com/Kenshin9977/video-dl-script/releases) section.

## Usage

Launch `scripts/video_dl.bat` (Windows) or `scripts/video_dl.sh` (Linux/Mac), enter the URL of a video, select start and end time then close the window when finished or enter another URL. The files are downloaded in the `downloads/` folder.
You can skip the start and end time part by changing the value in config/config.ini from false to true. It's useful if you always want to get the whole video.

## Software used

* [youtube-dl](https://github.com/ytdl-org/youtube-dl)
* [ffmpeg](https://github.com/FFmpeg/FFmpeg)
* [7zip](https://www.7-zip.org/download.html)
* [detect_hardware](https://github.com/Kenshin9977/Detect_hardware)
