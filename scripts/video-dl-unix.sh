#!/bin/bash

check_dependencies() {

    if ! type ffmpeg; then
        echo "FFMPEG could not be found in your PATH, please install it using Homebrew (macOS) or your package manager."
        exit
    fi

    if ! type youtube-dl; then
        echo "youtube-dl could not be found in your PATH, please install it using Homebrew (macOS) or your package manager."
        exit
    fi

    echo "All dependencies have been found."
    return
}

load_encoder() {
    
    pushd ../ressources > /dev/null
    encoder=$(./detect_hardware_unix.sh)
    popd > /dev/null

    qp="-qp 30"

    if [[ $encoder = "NVENC" ]]; then
        encoder="h264_nvenc"
    elif [[ $encoder = "QSV" ]]; then
        encoder="h264_qsv"
    elif [[ $encoder = "VCE" ]]; then
        encoder="h264"
    elif [[ $encoder = "VTL" ]]; then
        encoder="h264_videotoolbox"
        qp="-b:v 12M" # VTL doesn't support CRF
        # 12Mbps is the recommended bitrate for
        # 1080p60 by Youtube.
    elif [[ $encoder = "x264" ]]; then
        encoder="h264"
    fi

    echo "The following encoder has been selected: $encoder"
    return
}

load_config() {
    whole_vid=$(head -n 1 ../config/config.ini)
    echo "Config has successfully been loaded."
    return
}

get_url() {
    read -p "Enter Video's URL: " url
    if [ "$url" == "" ]; then
        echo "No URL was specified."
        exit
    fi

    return
}

get_video_times() {

    if [ "$whole_vid" != "whole_video=true" ]; then
        echo "Enter start and end time in the format HH:mm:ss (leave blank for the whole video)"
        read -p "Start: " start
        read -p "End: " end
    fi

    if [ "$start" == "" ]; then
        start="0:0"
    fi
    if [ "$end" == "" ]; then
        end="99:0:0"
    fi

    return
}

download_video() {
    youtube-dl --ffmpeg-location $(which ffmpeg) --recode-video mp4 --no-playlist --postprocessor-args "-ss $start -to $end -c:v $encoder $qp -c:a copy" -f "bestvideo[height<=?1080]+bestaudio[ext=m4a]/[height<=?1080]+bestaudio/best" --merge-output-format mkv $url -o "../downloads/%(title)s - %(uploader)s.%(ext)s"
    return
}

check_dependencies

load_encoder
load_config

while true
do
    get_url
    get_video_times

    download_video
done
