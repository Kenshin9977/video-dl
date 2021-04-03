@echo off

cd ..\resources
for /f %%i in ('..\resources\detect_hardware.bat') do set hw=%%i
cd ..\scripts
set /p whole_video=<..\config\config.ini
set whole_video="%whole_video%"

:start
set url=
set /p url="Enter Video's URL : "
set url="%url%"
IF [%url%]==[""] echo "No URL was specified." & pause & exit
set start=0:0& set end=99:0:0

IF [%whole_video%] NEQ ["whole_video=true"] echo Enter start and end time in the format HH:mm:ss (leave blank for the whole video)
IF [%whole_video%] NEQ ["whole_video=true"] set /p start="Start : " & set /p end="End : "
IF [%start%]==[] set start=0:0
IF [%end%]==[] set end=99:0:0

IF [%hw%]==[NVENC] set encoder=h264_nvenc
IF [%hw%]==[VCE] set encoder=h264_amf
IF [%hw%]==[QSV] set encoder=h264_qsv
IF [%hw%]==[x264] set encoder=h264

"%~dp0\..\bin\youtube-dl.exe" --ffmpeg-location "%~dp0\..\bin\ffmpeg.exe" --recode-video mp4 --no-playlist --postprocessor-args "-ss %start% -to %end% -c:v %encoder% -b:v 12M -c:a copy" -f "bestvideo[height<=?1080]+bestaudio[ext=m4a]/[height<=?1080]+bestaudio/best" --merge-output-format mkv %url% -o "%~dp0\..\downloads\%%(title)s - %%(uploader)s.%%(ext)s"

echo Download and conversion are finished
goto :start
