$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) { throw 'Please install uv first: https://docs.astral.sh/uv/getting-started/installation/' }
$labEnv = if ($env:AUDIO_LAB_ENV) { $env:AUDIO_LAB_ENV } else { Join-Path $env:LOCALAPPDATA 'AudioRepairLab\qwen-venv' }
$python = Join-Path $labEnv 'Scripts\python.exe'
if (-not (Test-Path $python)) { & uv venv --python 3.12 $labEnv; if ($LASTEXITCODE -ne 0) { throw 'Python setup failed' } }
& uv pip install --python $python -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw 'Package installation failed' }
& $python -m scripts.download_models
if ($LASTEXITCODE -ne 0) { throw 'Model setup failed; rerun install.ps1 to retry' }
Write-Host 'Setup complete. Double click start.cmd to open the local web UI.'
