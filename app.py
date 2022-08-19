from gui import _video_dl_gui
from updater.updater import Updater

if __name__ == "__main__":
    Updater().update_app()
    _video_dl_gui()

# TODO: Write tests
# TODO: Sign updates
# TODO: Handle MacOS and Linux updater
# TODO: Autoinstall ffmpeg if missing os MacOS and Linux
# TODO: Investigate pyinstaller crosscompilation to generate new versions
