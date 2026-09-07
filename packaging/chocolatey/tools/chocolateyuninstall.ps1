$ErrorActionPreference = 'Stop'

Get-Process -Name 'video-dl' -ErrorAction SilentlyContinue |
  Stop-Process -Force -ErrorAction SilentlyContinue

$shortcut = Join-Path ([Environment]::GetFolderPath('CommonPrograms')) 'video-dl.lnk'
if (Test-Path $shortcut) { Remove-Item $shortcut -Force -ErrorAction SilentlyContinue }

Write-Host 'Your settings remain in %AppData%\video-dl.'
