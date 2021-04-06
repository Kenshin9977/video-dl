@echo off

cd ..\ressources
FOR /f %%i in ('..\ressources\detect_hardware.bat') do set hw=%%i
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

"..\bin\youtube-dl.exe" --ffmpeg-location "..\bin\ffmpeg.exe" --no-playlist -f "bestvideo[vcodec*=avc1,height<=?1080]+bestaudio[acodec*=mp4a]/[height<=?1080]+bestaudio/best" --merge-output-format mkv %url% -o "..\downloads\%%(title)s - %%(uploader)s.%%(ext)s"

FOR %%i in (..\downloads\*.mkv) do set mkv_file=%%~ni
FOR /f %%i in ('..\bin\ffprobe.exe -v error -select_streams v:0 -show_entries stream^=codec_name -of default^=noprint_wrappers^=1:nokey^=1 "..\downloads\%mkv_file%.mkv"') do set mkv_codec=%%i
IF [%mkv_codec%]==[h264] (..\bin\ffmpeg.exe -hide_banner -loglevel warning -i "..\downloads\%mkv_file%.mkv" -ss %start% -to %end% -c copy -y "..\downloads\%mkv_file%.mp4" & echo Download and remuxing are finished) ELSE (..\bin\ffmpeg.exe -hide_banner -loglevel warning -i "..\downloads\%mkv_file%.mkv" -ss %start% -to %end% -c:v %encoder% -b:v 12M -c:a copy -y "..\downloads\%mkv_file%.mp4" & echo Download and conversion are finished)
DEL "..\downloads\%mkv_file%.mkv"

goto :start
