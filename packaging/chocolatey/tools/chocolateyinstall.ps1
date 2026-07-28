$ErrorActionPreference = 'Stop'

$packageName = 'video-dl'
$toolsDir    = Split-Path -Parent $MyInvocation.MyCommand.Definition

# Injected at pack time by the release workflow from the artifact it just built
# and signed. Left as placeholders in the repo so a stray copy of this file can
# never point at a stale download.
$url64      = '$url64$'
$checksum64 = '$checksum64$'

# The portable exe, not the Inno installer, and the reason is the same one that
# shapes the WinGet manifest differently: video-dl.iss sets
# PrivilegesRequired=lowest and installs into {localappdata}. Chocolatey runs
# elevated, so the installer would land in the administrator's profile and be
# invisible to whoever typed the command. A single portable exe in the
# Chocolatey library is machine-wide and has no such opinion.
$exe = Join-Path $toolsDir 'video-dl.exe'

Get-ChocolateyWebFile `
  -PackageName   $packageName `
  -FileFullPath  $exe `
  -Url64bit      $url64 `
  -Checksum64    $checksum64 `
  -ChecksumType64 'sha256'

# Marks the shim as a GUI app. Without it the shim waits for the window to
# close, so `video-dl` from a terminal blocks that terminal until you quit.
New-Item "$exe.gui" -ItemType File -Force | Out-Null

Install-ChocolateyShortcut `
  -ShortcutFilePath (Join-Path ([Environment]::GetFolderPath('CommonPrograms')) 'video-dl.lnk') `
  -TargetPath $exe `
  -Description 'A GUI for yt-dlp'

Write-Host 'Installed as the portable build, so it updates through Chocolatey rather than on its own.'
