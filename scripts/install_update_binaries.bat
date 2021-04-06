@echo off
set NLM=^


set NL=^^^%NLM%%NLM%^%NLM%%NLM%
cd /d %~dp0
if not exist "..\bin\" mkdir "..\bin\"
echo Downloading the latest version of youtube-dl.exe.
curl -L --url https://yt-dl.org/latest/youtube-dl.exe --output "..\bin\youtube-dl.exe"
echo %NL%Downloading the latest version of ffmpeg.exe by gyan.dev.
curl -L --url https://www.gyan.dev/ffmpeg/builds/ffmpeg-git-essentials.7z --output ".\ffmpeg-essentials_build.7z"
if exist ".\ffmpeg-essentials_build.7z" (
	..\ressources\7za.exe e ".\ffmpeg-essentials_build.7z" "ffmpeg.exe" -aoa -o"..\bin\" -r
	..\ressources\7za.exe e ".\ffmpeg-essentials_build.7z" "ffprobe.exe" -aoa -o"..\bin\" -r
	del ".\ffmpeg-essentials_build.7z"
	exit /b		
)
