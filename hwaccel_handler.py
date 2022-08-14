import os

import ffmpeg

ENCODERS = {
    "x264": {
        "QuickSync": "h264_qsv",
        "NVENC": "h264_nvenc",
        "AMF": "h264_amf",
        "Apple": "h264_videotoolbox",
        "Raspberry": "h264_v4l2m2m",
        "CPU": "libx264",
    },
    "x265": {
        "QuickSync": "hevc_qsv",
        "NVENC": "hevc_nvenc",
        "AMF": "hevc_amf",
        "Apple": "hevc_videotoolbox",
        "Raspberry": "hevc_v4l2m2m",
        "CPU": "libx265",
    },
    "ProRes": {
        "QuickSync": None,
        "NVENC": None,
        "AMF": None,
        "Apple": "prores_videotoolbox",
        "Raspberry": None,
        "CPU": "prores_ks",
    },
    "AV1": {
        "QuickSync": None,
        "NVENC": None,
        "AMF": None,
        "Apple": None,
        "CPU": "liboam-av1",
    },
}


def fastest_encoder(path: str, target_vcodec: str) -> str:
    """
    Determine the fastest encoder by trying to encode 1 frame with each
    possible encoder for the targeted video codec. As soon as one works it is
    considered the fastest as it's pretty rare to have multiple hardware
    encoders and the difference in speed/quality is often negligible.
    The CPU is the fallback option as it's a universal solution altough the
    slowest.

    Args:
        path (str): path to the file used to test the codecs
        target_vcodec (str): Video codec to encode to

    Raises:
        ffmpeg.Error: If no compatible codec was found

    Returns:
        str: Fastest compatible codec
    """
    file_name_ext = os.path.splitext(path)
    new_ext = ".mp4" if target_vcodec != "ProRes" else ".mov"
    output_path = f"{file_name_ext[0]}.tmp{new_ext}"
    vcodecs = ENCODERS[target_vcodec].values()
    for vcodec in vcodecs:
        if not vcodec:
            continue
        try:
            ffmpeg.input(path).output(
                output_path, vframes=1, vcodec=vcodec
            ).run(overwrite_output=True)
        except ffmpeg.Error:
            continue
        else:
            return vcodec
        finally:
            if os.path.isfile(output_path):
                os.remove(path=output_path)
    raise ffmpeg.Error
