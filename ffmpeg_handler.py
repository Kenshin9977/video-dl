import os
import re
import subprocess
from typing import Dict, List

import ffmpeg
import PySimpleGUI as Sg

from gui import gpus_possible_encoders
from lang import GuiField, get_text


def post_process_dl(full_name: str) -> None:
    file_infos = ffmpeg.probe(full_name)['streams']
    audio_codec, video_codec = 'na', 'na'
    for i in range(0, min(2, len(file_infos))):
        if file_infos[i]['codec_type'] == 'audio':
            audio_codec = file_infos[i]['codec_tag_string']
        elif file_infos[i]['codec_type'] == 'video':
            video_codec = file_infos[i]['codec_tag_string']
    fps2compute = ffmpeg.probe(full_name)['streams'][0]['r_frame_rate'].split('/')
    fps = 10 if len(fps2compute) == 1 or int(fps2compute[1]) == 0 else int(fps2compute[0]) // int(fps2compute[1])
    acodecs_list = ["aac", "mp3", "mp4a"]
    acodec_supported = len([i for i in acodecs_list if re.match(f"{i}", audio_codec)]) > 0
    vcodec_supported = re.match("avc1", video_codec) is not None
    _ffmpeg_video(full_name, acodec_supported, vcodec_supported, fps)


def _ffmpeg_video(path: str, acodec_supported: bool, vcodec_supported: bool, fps: int) -> None:
    recode_acodec = "aac" if not acodec_supported else "copy"
    recode_vcodec = _best_encoder(path, fps) if not vcodec_supported else "copy"
    tmp_path = os.path.splitext(path)[0] + '.tmp' + ".mp4"
    ffmpegCommand = ['ffmpeg', '-hide_banner', '-i', path, '-c:a', recode_acodec, '-c:v', recode_vcodec, '-y', tmp_path]
    action = get_text(GuiField.ff_remux) if acodec_supported and vcodec_supported else get_text(
        GuiField.ff_reencode)
    _progress_ffmpeg(ffmpegCommand, action, path)
    os.replace(tmp_path, path)


def _progress_ffmpeg(cmd: List[str], action: str, filepath: str) -> None:
    result = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of",
                             "default=noprint_wrappers=1:nokey=1", filepath],
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    total_duration = int(float(result.stdout))
    layout = [[Sg.Text(action)],
              [Sg.ProgressBar(100, orientation='h', size=(20, 20), key='-PROG-')],
              [Sg.Text(get_text(GuiField.ff_starting), key='PROGINFOS1')],
              [Sg.Text("", key='PROGINFOS2')],
              [Sg.Cancel(button_text=get_text(GuiField.cancel_button))]]

    progress_window = Sg.Window(
        action, layout, no_titlebar=True, grab_anywhere=True)
    progress_pattern = re.compile(r'(frame|fps|size|time|bitrate|speed)\s*=\s*(\S+)')
    p = subprocess.Popen(cmd, stderr=subprocess.PIPE, universal_newlines=True, encoding="utf8")

    while p.poll() is None:
        output = p.stderr.readline().rstrip(os.linesep) if p.stderr is not None else ""
        items = {key: value for key, value in progress_pattern.findall(output)}
        if 'time' in items.keys() and 'speed' in items.keys():
            event, _ = progress_window.read(timeout=10)
            if event == 'Cancel' or event == Sg.WIN_CLOSED:
                progress_window.close()
                raise ValueError
            progress_percent = _get_progress_percent(items['time'], total_duration)
            progress_window['PROGINFOS1'].update(f"{progress_percent}%")
            progress_window['PROGINFOS2'].update(
                f"{get_text(GuiField.ff_speed)}: {items['speed']}")
            progress_window['-PROG-'].update(progress_percent)
    progress_window.close()


def _get_progress_percent(timestamp: str, total_duration: int) -> int:
    prog = re.split('[:.]', timestamp)
    progress_seconds = int(prog[0]) * 3600 + int(prog[1]) * \
        60 + int(prog[2]) + int(prog[0]) / 100
    return int(progress_seconds / total_duration * 100)


def _best_encoder(path: str, fps: int) -> str:
    file_name_ext = os.path.splitext(path)
    output_path = f"{file_name_ext[0]}.tmp.mp4"
    end = format(1 / fps, '.3f')
    for encoder in gpus_possible_encoders:
        try:
            ffmpeg.input(path, ss="00:00:00.00", to=end).output(output_path, vcodec=encoder).run(overwrite_output=True)
        except ffmpeg.Error:
            continue
        else:
            return encoder
        finally:
            if os.path.isfile(output_path):
                os.remove(path=output_path)
    return "libx264"
