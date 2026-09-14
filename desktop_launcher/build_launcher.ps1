param(
    [string]$PythonExecutable = "",
    [string]$ProjectRoot = ""
)

$ErrorActionPreference = "Stop"
$launcherRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not $ProjectRoot) {
    $ProjectRoot = (Resolve-Path (Join-Path $launcherRoot "..")).Path
}
if (-not $PythonExecutable) {
    $PythonExecutable = (Get-Command python -ErrorAction Stop).Source
}

$PythonExecutable = (Resolve-Path -LiteralPath $PythonExecutable -ErrorAction Stop).Path
$ProjectRoot = (Resolve-Path -LiteralPath $ProjectRoot -ErrorAction Stop).Path
$entryScript = Join-Path $ProjectRoot "src\main.py"
if (-not (Test-Path -LiteralPath $entryScript -PathType Leaf)) {
    throw "FitRoute AI entry script was not found: $entryScript"
}

& $PythonExecutable -c "import PyInstaller" 2>$null
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller is not installed in the selected Python environment. Install it explicitly, then rerun this script."
}

& $PythonExecutable -m PyInstaller `
    --noconfirm `
    --clean `
    --onefile `
    --noconsole `
    --name FitRouteLauncher `
    --distpath (Join-Path $launcherRoot "dist") `
    --workpath (Join-Path $launcherRoot "build") `
    --specpath $launcherRoot `
    (Join-Path $launcherRoot "launcher.py")
if ($LASTEXITCODE -ne 0) {
    throw "FitRouteLauncher.exe build failed."
}

$config = [ordered]@{
    python_executable = $PythonExecutable
    project_root = $ProjectRoot
    entry_script = "src/main.py"
}
$config | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $launcherRoot "dist\config.json") -Encoding UTF8
Write-Output "Launcher: $(Join-Path $launcherRoot 'dist\FitRouteLauncher.exe')"
Write-Output "Config:   $(Join-Path $launcherRoot 'dist\config.json')"
