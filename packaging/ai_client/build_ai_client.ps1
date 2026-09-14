$ErrorActionPreference = "Stop"

$ScriptDirectory = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepositoryRoot = (Resolve-Path (Join-Path $ScriptDirectory "..\..")).Path
$SpecPath = Join-Path $ScriptDirectory "FitRouteAIClient.spec"
$ValidatorPath = Join-Path $ScriptDirectory "validate_build_env.py"
$ExpectedExecutable = Join-Path $RepositoryRoot "dist\FitRouteAIClient\FitRouteAIClient.exe"

$PythonExecutable = (& python -c "import sys; print(sys.executable)").Trim()
if ($LASTEXITCODE -ne 0) {
    throw "Unable to resolve the active Python executable."
}

$PythonPrefix = (& python -c "import sys; print(sys.prefix)").Trim()
if ($LASTEXITCODE -ne 0) {
    throw "Unable to resolve the active Python environment."
}

$EnvironmentName = Split-Path -Leaf $PythonPrefix
if ($EnvironmentName -ne "fitroute_build") {
    throw "Build requires fitroute_build; active environment is '$EnvironmentName' ($PythonExecutable)."
}

Write-Host "Python: $PythonExecutable"
Write-Host "Environment: $EnvironmentName"

Push-Location $RepositoryRoot
try {
    $env:MPLCONFIGDIR = Join-Path $RepositoryRoot "build\mpl-cache"
    # PyInstaller analysis imports optional Ultralytics tracker modules. Never
    # allow that analysis to mutate the clean build environment.
    $env:YOLO_AUTOINSTALL = "false"

    & $PythonExecutable $ValidatorPath
    if ($LASTEXITCODE -ne 0) {
        throw "Build environment validation failed."
    }

    & $PythonExecutable -m PyInstaller --noconfirm --clean $SpecPath
    if ($LASTEXITCODE -ne 0) {
        throw "PyInstaller build failed with exit code $LASTEXITCODE."
    }

    if (-not (Test-Path -LiteralPath $ExpectedExecutable -PathType Leaf)) {
        throw "Expected executable was not created: $ExpectedExecutable"
    }

    Write-Host "Build complete: $ExpectedExecutable"
}
finally {
    Pop-Location
}
