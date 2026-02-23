$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Path $PSScriptRoot -Parent
$pythonExe = Join-Path $projectRoot "venv\Scripts\python.exe"
$producerScript = Join-Path $projectRoot "src\api_producer.py"

if (-not (Test-Path $pythonExe)) {
    throw "Python executable not found: $pythonExe"
}

& $pythonExe $producerScript
