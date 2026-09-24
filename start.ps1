$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$labEnv = if ($env:AUDIO_LAB_ENV) { $env:AUDIO_LAB_ENV } else { Join-Path $env:LOCALAPPDATA 'AudioRepairLab\qwen-venv' }
$python = Join-Path $labEnv 'Scripts\python.exe'
if (-not (Test-Path $python)) { throw 'Run install.ps1 first' }
& $python -m scripts.run
exit $LASTEXITCODE
