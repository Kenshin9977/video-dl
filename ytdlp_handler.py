import yt_dlp
import mimetypes

from ffmpeg_handler import *
from quantiphy import Quantity
from yt_dlp.YoutubeDL import sanitize_path, sanitize_filename

CANCELED = False


def video_dl(values):
    global CANCELED
    CANCELED = False
    trim_start = f"{values['sH']}:{values['sM']}:{values['sS']}"
    trim_end = f"{values['eH']}:{values['eM']}:{values['eS']}"
    ydl_opts = gen_query(values['MaxHeight'], values['Browser'], values['AudioOnly'], values['path'], trim_start, trim_end)
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        infos_ydl = ydl.extract_info(values["url"])
    ext = infos_ydl['audio_ext'] if (values['AudioOnly'] and infos_ydl['audio_ext'] != 'none') else infos_ydl['ext']
    filename = f"{sanitize_filename(infos_ydl['title'][:100])} - {infos_ydl['uploader']}.{ext}"
    full_path = sanitize_path(os.path.join(values['path'], filename))
    post_process_dl(full_path, values, infos_ydl)
    # os.remove(full_path)


def gen_query(h, browser, audio_only, path, start, end):
    options = {'noplaylist': True, 'progress_hooks': [download_progress_bar], 'trim_file_name': 250,
               'outtmpl': os.path.join(path, "%(title).100s - %(uploader)s.%(ext)s")}
    video_format = ""
    for acodec in ["aac", "mp3", "mp4a"]:
        video_format += f'bestvideo[vcodec*=avc1][height<=?{h}]+bestaudio[acodec*={acodec}]/'
    video_format += f'bestvideo[vcodec*=avc1][height<=?{h}]+bestaudio/'
    for acodec in ["aac", "mp3", "mp4a"]:
        video_format += f'/bestvideo[height<=?{h}]bestaudio[acodec={acodec}]/'
    video_format += f'bestvideo[height<=?{h}]bestaudio/best'
    audio_format = 'bestaudio[acodec*=mp4a]/bestaudio[acodec*=mp3]/bestaudio[acodec*=aac]/bestaudio/best'
    options['format'] = audio_format if audio_only else video_format
    if audio_only:
        options['extract_audio'] = True
    if start != "00:00:00" or end != "99:59:59":
        options['external_downloader'] = 'ffmpeg'
        options['external_downloader_args'] = {'ffmpeg_i': ['-ss', start, '-to', end]}
    else:
        options["merge-output-format"] = "mp4"
    if browser != "None":
        options['cookiesfrombrowser'] = [browser.lower()]
    return options


def download_progress_bar(d):
    global CANCELED
    media_type = mimetypes.guess_type(d['filename'])[0].split('/')[0]
    if d['status'] == 'finished':
        file_tuple = os.path.split(os.path.abspath(d['filename']))
        print("Done downloading {}".format(file_tuple[1]))
    if d['status'] == 'downloading':
        downloaded = Quantity(d['downloaded_bytes'], 'B')
        total = Quantity(d['total_bytes'], 'B') if 'total_bytes' in d.keys() else Quantity(d['total_bytes_estimate'], 'B')
        progress = Sg.OneLineProgressMeter('Downloading', downloaded, total, f'Downloading {media_type}', orientation='h',
                                no_titlebar=True, grab_anywhere=True)
        if CANCELED or (not progress and downloaded < total):
            CANCELED = True
            raise ValueError
