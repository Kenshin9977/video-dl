@ECHO OFF
SETLOCAL EnableDelayedExpansion

:: System Settings
SET "cfgRenderer=DX11" REM DX9, DX9Ex, DX11, OpenGL, OpenCL, Host, OpenCLDX9, OpenCLDX11, OpenGLDX9, OpenGLDX11, OpenCLOpenGLDX9, OpenCLOpenGLDX11, HostDX9, HostDX11, DX11DX9,
SET "cfgAdapterId=0"

:: Static Properties
SET "cfgUsage=TRANSCODING"
SET "cfgProfile=High"
SET "cfgProfileLevel=52"
SET "cfgFullRange=false"
SET "cfgFramerate=60,1"

:: Rate Control Properties
SET "cfgRateControlMethod=CBR"
SET "cfgRateControlPreAnalysis=DISABLED" REM DISABLED, ENABLED, ENABLED2, ENABLED4
SET "cfgRateControlSkipFrame=false"
SET "cfgMinQP=18"
SET "cfgMaxQP=51"
SET "cfgTargetBitrate=3500000" REM 3500kbit for Twitch highest
SET "cfgPeakBitrate=%cfgTargetBitrate%"
SET "cfgQPI=22"
SET "cfgQPP=22"
SET "cfgQPB=22"

:: Flags
SET "cfgDeblockingFilter=true"
SET "cfgFillerDataEnable=false"
SET "cfgEnableVBAQ=false"
SET "cfgEnforceHRD=false"

:: Picture Control
SET "cfgIDRPeriod=120"

:: Variable Bitrate Verifier Buffer
SET "cfgVBVBufferSize=%cfgTargetBitrate%"
SET "cfgVBVBufferInitialFullness=64"

:: Motion Estimation Properties
SET "cfgHalfPixelME=true"
SET "cfgQuarterPixelME=true"

:: Experimental
SET "cfgMaximumReferenceFrames=4"

:: System
SET sysFrames=300
SET sysThreadCount=1
SET "sysOutputDir=ResultsH264"

:: --------------------------------------------------------------------------------
:: - Test Settings                                                                -
:: --------------------------------------------------------------------------------
call Resolutions.bat

IF NOT EXIST "%sysOutputDir%" MKDIR %sysOutputDir%

PUSHD "32-Bit"
"CapabilityManager.exe" > ..\%sysOutputDir%\Caps.txt

SET "tmpEncoderParams="
SET "tmpEncoderParams=%tmpEncoderParams% -RENDER %cfgRenderer%"
SET "tmpEncoderParams=%tmpEncoderParams% -ADAPTERID %cfgAdapterId%"
SET "tmpEncoderParams=%tmpEncoderParams% -FRAMES %sysFrames%"
SET "tmpEncoderParams=%tmpEncoderParams% -CODEC AVC"
SET "tmpEncoderParams=%tmpEncoderParams% -Usage %cfgUsage%"
SET "tmpEncoderParams=%tmpEncoderParams% -Profile %cfgProfile%"
SET "tmpEncoderParams=%tmpEncoderParams% -ProfileLevel %cfgProfileLevel%"
::SET "tmpEncoderParams=%tmpEncoderParams% -HevcTier %cfgTier%"
SET "tmpEncoderParams=%tmpEncoderParams% -FullRangeColor %cfgFullRange%"
SET "tmpEncoderParams=%tmpEncoderParams% -Framerate %cfgFramerate%"
SET "tmpEncoderParams=%tmpEncoderParams% -RateControlMethod %cfgRateControlMethod%"
SET "tmpEncoderParams=%tmpEncoderParams% -RateControlPreAnalysisEnable %cfgRateControlPreAnalysis%"
SET "tmpEncoderParams=%tmpEncoderParams% -RateControlSkipFrameEnable %cfgRateControlSkipFrame%"
SET "tmpEncoderParams=%tmpEncoderParams% -MinQP %cfgMinQP%"
SET "tmpEncoderParams=%tmpEncoderParams% -MaxQP %cfgMaxQP%"
::SET "tmpEncoderParams=%tmpEncoderParams% -HevcMinQP_P %cfgMinQPP%"
::SET "tmpEncoderParams=%tmpEncoderParams% -HevcMaxQP_P %cfgMaxQPP%"
SET "tmpEncoderParams=%tmpEncoderParams% -TargetBitrate %cfgTargetBitrate%"
SET "tmpEncoderParams=%tmpEncoderParams% -PeakBitrate %cfgPeakBitrate%"
SET "tmpEncoderParams=%tmpEncoderParams% -QP_I %cfgQPI%"
SET "tmpEncoderParams=%tmpEncoderParams% -QP_P %cfgQPP%"
SET "tmpEncoderParams=%tmpEncoderParams% -QP_B %cfgQPB%"
SET "tmpEncoderParams=%tmpEncoderParams% -DeBlockingFilter %cfgDeblockingFilter%"
SET "tmpEncoderParams=%tmpEncoderParams% -FillerDataEnable %cfgFillerDataEnable%"
SET "tmpEncoderParams=%tmpEncoderParams% -EnableVBAQ %cfgEnableVBAQ%"
SET "tmpEncoderParams=%tmpEncoderParams% -EnforceHRD %cfgEnforceHRD%"
SET "tmpEncoderParams=%tmpEncoderParams% -VBVBufferSize %cfgVBVBufferSize%"
SET "tmpEncoderParams=%tmpEncoderParams% -InitialVBVBufferFullness %cfgVBVBufferInitialFullness%"
SET "tmpEncoderParams=%tmpEncoderParams% -HalfPixel %cfgHalfPixelME%"
SET "tmpEncoderParams=%tmpEncoderParams% -QuarterPixel %cfgQuarterPixelME%"
SET "tmpEncoderParams=%tmpEncoderParams% -MaxNumRefFrames %cfgMaximumReferenceFrames%"
::SET "tmpEncoderParams=%tmpEncoderParams% -GOPType %cfgGOPType%"
::SET "tmpEncoderParams=%tmpEncoderParams% -HevcGOPSize %cfgGOPSize%"
::SET "tmpEncoderParams=%tmpEncoderParams% -GOPSizeMin %cfgGOPSizeMin%"
::SET "tmpEncoderParams=%tmpEncoderParams% -GOPSizeMax %cfgGOPSizeMax%"
::SET "tmpEncoderParams=%tmpEncoderParams% -HevcGOPSPerIDR %cfgGOPSPerIDR%"
::SET "tmpEncoderParams=%tmpEncoderParams% -HevcInputQueueSize %cfgInputQueueSize%"
SET "tmpEncoderParams=%tmpEncoderParams% -BPicturesPattern 0"

ECHO Parameters: %tmpEncoderParams%
FOR /L %%i IN (1,1,%RES_NUM%) DO (
	SET "tmpOutputName=../%sysOutputDir%/H264_!RES_W[%%i]!x!RES_H[%%i]!"
	ECHO Testing Resolution: !RES_W[%%i]!x!RES_H[%%i]!

	IF EXIST "!tmpOutputName!.txt" DEL "!tmpOutputName!.txt"
	ECHO - Speed ------------------------------------------------------------------------>> !tmpOutputName!.txt
	ECHO "VCEEncoderD3D.exe" -WIDTH !RES_W[%%i]! -HEIGHT !RES_H[%%i]! -OUTPUT !tmpOutputName!_Speed.h264 -QualityPreset Speed
	"VCEEncoderD3D.exe" -WIDTH !RES_W[%%i]! -HEIGHT !RES_H[%%i]! %tmpEncoderParams% -OUTPUT !tmpOutputName!_Speed.h264 -QualityPreset Speed >> !tmpOutputName!.txt 2>&1
	TIMEOUT /T 1 /NOBREAK > nul
	REM ECHO - Balanced --------------------------------------------------------------------->> !tmpOutputName!.txt
	REM ECHO "VCEEncoderD3D.exe" -WIDTH !RES_W[%%i]! -HEIGHT !RES_H[%%i]! -OUTPUT !tmpOutputName!_Balanced.h264 -QualityPreset Balanced
	REM "VCEEncoderD3D.exe" -WIDTH !RES_W[%%i]! -HEIGHT !RES_H[%%i]! %tmpEncoderParams% -OUTPUT !tmpOutputName!_Balanced.h264 -QualityPreset Balanced >> !tmpOutputName!.txt 2>&1
	REM TIMEOUT /T 1 /NOBREAK > nul
	REM ECHO - Quality ---------------------------------------------------------------------->> !tmpOutputName!.txt
	REM ECHO "VCEEncoderD3D.exe" -WIDTH !RES_W[%%i]! -HEIGHT !RES_H[%%i]! -OUTPUT !tmpOutputName!_Quality.h264 -QualityPreset Quality
	REM "VCEEncoderD3D.exe" -WIDTH !RES_W[%%i]! -HEIGHT !RES_H[%%i]! %tmpEncoderParams% -OUTPUT !tmpOutputName!_Quality.h264 -QualityPreset Quality >> !tmpOutputName!.txt 2>&1
	REM TIMEOUT /T 1 /NOBREAK > nul
)
POPD

ENDLOCAL
