@echo off

cd ..\resources
FOR /f %%i in ('..\resources\detect_hardware.bat') do set hw=%%i
cd ..\scripts
set /p whole_video=<..\config\config.ini
set whole_video="%whole_video%"

:Start
set url=
set downloaded_file=
set downloaded_file_fullname=
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

for /f "tokens=2 delims=:." %%x in ('chcp') do set cp=%%x
chcp 1252>nul

FOR /f "delims=" %%i in ('..\bin\youtube-dl.exe --skip-download --get-filename --no-warnings --no-playlist %url% -o "%%(title)s - %%(uploader)s"') do set downloaded_file=%%i
"..\bin\youtube-dl.exe" --no-playlist -f "bestvideo[vcodec*=avc1,width<=?1920]+bestaudio[acodec*=mp4a]/[height<=?1080]+bestaudio/best" --merge-output-format mp4 %url% -o "..\downloads\%%(title)s - %%(uploader)s.%%(ext)s"
IF ["%downloaded_file%"]==[""] ECHO Download or remuxing/encoding failed. & goto :start
FOR %%i in ("..\downloads\%downloaded_file%*") DO (
	SET downloaded_file_fullname=%%~nxi
)

chcp %cp%>nul

IF ["%downloaded_file_fullname%"]==[""] ECHO Download failed. & goto :start
FOR /f %%i in ('..\bin\ffprobe.exe -v error -select_streams v:0 -show_entries stream^=codec_name -of default^=noprint_wrappers^=1:nokey^=1 "..\downloads\%downloaded_file_fullname%"') do set files_codec=%%i
ECHO File's codec: %files_codec%.
SET flags=-hide_banner -loglevel warning
IF [%files_codec%]==[h264] (
	..\bin\ffmpeg.exe %flags% -i "..\downloads\%downloaded_file_fullname%" -ss %start% -to %end% -c copy -y "..\downloads\Processed_%downloaded_file%.mp4"
	ECHO Download and remuxing are finished
) ELSE (
	..\bin\ffmpeg.exe %flags% -i "..\downloads\%downloaded_file_fullname%" -ss %start% -to %end% -c:v %encoder% -b:v 12M -c:a copy -y "..\downloads\Processed_%downloaded_file%.mp4"
	ECHO Download and conversion are finished
)

DEL "..\downloads\%downloaded_file_fullname%"
REN "..\downloads\Processed_%downloaded_file%.mp4" "%downloaded_file%.mp4""

goto :Start