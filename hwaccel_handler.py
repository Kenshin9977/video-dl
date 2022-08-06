from GPUtil import getGPUs
from re import match


def _get_encoders_list() -> dict:
    encoders_dict = dict()
    encoders_dict.update(
        {
            "x264": list(),
            "x265": list(),
            "ProRes": ["prores_ks"],
            "AV1": ["libaom-av1"],
        }
    )
    tmp_list_x264 = list()
    tmp_list_x265 = list()
    gpus = getGPUs()
    for gpu in gpus:
        gpu_name = gpu.name
        if match("NVIDIA", gpu_name):
            tmp_list_x264.append("h264_nvenc")
            tmp_list_x265.append("hevc_nvenc")
        if match("AMD", gpu_name):
            tmp_list_x264.append("h264_amf")
            tmp_list_x265.append("hevc_amf")
        if match("Intel", gpu_name):
            tmp_list_x264.append("h264_qsv")
            tmp_list_x265.append("hevc_qsv")
    tmp_list_x264.append("libx264")
    tmp_list_x265.append("libx265")
    encoders_dict["x264"] = tmp_list_x264
    encoders_dict["x265"] = tmp_list_x265
    return encoders_dict
