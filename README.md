# video-dl (a yt-dlp GUI)

The purpose of this script is to simplify the usage of [yt-dlp](https://github.com/yt-dlp/yt-dlp).
<p align="center">
<img src="https://i.imgur.com/Ji0CuT2.png" width=400>
</p>


## Requirements

### Windows
All the requirements are embedded within the installer. FFmpeg is automatically downloaded on first launch if missing.

### Linux
* You need to install both `ffmpeg` and `ffprobe` manually. Most Linux distributions have these in their package manager.
* In order to use QSV, you must have the `intel-mediasdk` (apt) or `intel-media-sdk` (pacman) package installed.

### macOS
* Homebrew has the `ffmpeg` package which includes `ffprobe`: `brew install ffmpeg`

## Downloads

| Windows | macOS | Linux |
|:-------:|:-----:|:-----:|
| [video-dl-windows.exe](https://github.com/Kenshin9977/video-dl/releases/latest/download/video-dl-windows.exe) | [video-dl-macos.dmg](https://github.com/Kenshin9977/video-dl/releases/latest/download/video-dl-macos.dmg) | [video-dl-linux](https://github.com/Kenshin9977/video-dl/releases/latest/download/video-dl-linux) |

Or browse all releases [here](https://github.com/Kenshin9977/video-dl/releases).

## Usage

Simply run the binary.

Launch video-dl, enter a valid URL of a supported website, select the options you want then click "Download".
Each option should be self explanatory. If it isn't, don't hesitate to create an issue so that I can fix that.

## Features

* Works with every website yt-dlp [supports](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md).
* Allows you to choose the max framerate and resolution. It will try to find it but will get a lower value if this resolution/framerate isn't available.
* Allows you to only download the audio of a video.
* Allows you to choose among the most common audio codecs if you only want the audio.
* Let you choose the start and end time of the video you want to download.
* Allows you to get cookies from your browser in order to access restricted videos only accessible if you log in.
* Saves videos with the name of the video followed by the author's name.
* Remuxes videos if the downloaded file's codec matches the targeted video codec (faster than recode and lossless) to ensure compatibility with every NLE software.
* Recodes the video in the targeted codec if it is encoded with something else.
* Detects hardware encoders (h264/h265/ProRes/AV1) and uses them instead of the CPU when available.
* Can download subtitles.

## Build from sources

### Prerequisites

* Python >= 3.12
* ffmpeg and ffprobe

```bash
git clone https://github.com/Kenshin9977/video-dl.git
cd video-dl
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -e ".[dev]"
```

Add [this plugin](https://github.com/seproDev/yt-dlp-ChromeCookieUnlock?tab=readme-ov-file) in your venv so that cookie extraction works with Chromium-based browsers.

### Run

```bash
python main.py          # normal
python main.py --debug  # debug mode
```

### Package

#### Windows
```bash
pyinstaller specs/Windows-video-dl.spec
```

#### macOS
```bash
pyinstaller specs/macOS-video-dl.spec
```

#### Linux
```bash
pyinstaller specs/Linux-video-dl.spec
```

## Code signing policy

Free code signing provided by [SignPath.io](https://signpath.io), certificate by [SignPath Foundation](https://signpath.org).

- Committers and reviewers: [Kenshin9977](https://github.com/Kenshin9977)
- Approvers: [Kenshin9977](https://github.com/Kenshin9977)

## Privacy policy

This program will not transfer any information to other networked systems unless specifically requested by the user (e.g. downloading a video from a URL provided by the user).

## Software used

* [yt-dlp](https://github.com/yt-dlp/yt-dlp)
* [FFmpeg](https://github.com/yt-dlp/FFmpeg-Builds)
* [Flet](https://flet.dev/)
