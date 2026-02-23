$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Path $PSScriptRoot -Parent
$pythonExe = Join-Path $projectRoot "venv\Scripts\python.exe"
$dashboardScript = Join-Path $projectRoot "src\dashboard.py"

if (-not (Test-Path $pythonExe)) {
    throw "Python executable not found: $pythonExe"
}
if (-not (Test-Path $dashboardScript)) {
    throw "Dashboard script not found: $dashboardScript"
}

& $pythonExe -m streamlit run $dashboardScript --server.port 8501
