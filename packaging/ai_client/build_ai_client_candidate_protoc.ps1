$ErrorActionPreference = "Stop"

$ScriptDirectory = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepositoryRoot = (Resolve-Path (Join-Path $ScriptDirectory "..\..")).Path
$SpecPath = Join-Path $ScriptDirectory "FitRouteAIClient.optimized_protoc.spec"
$ValidatorPath = Join-Path $ScriptDirectory "validate_build_env.py"
$BaselineExecutable = Join-Path $RepositoryRoot "dist_candidate_polars\FitRouteAIClient\FitRouteAIClient.exe"
$CandidateWorkPath = Join-Path $RepositoryRoot "build_candidate_protoc"
$CandidateDistPath = Join-Path $RepositoryRoot "dist_candidate_protoc"
$ExpectedExecutable = Join-Path $CandidateDistPath "FitRouteAIClient\FitRouteAIClient.exe"

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
    throw "protoc candidate build requires fitroute_build; active environment is '$EnvironmentName' ($PythonExecutable)."
}

if (-not (Test-Path -LiteralPath $BaselineExecutable -PathType Leaf)) {
    throw "Validated Polars baseline executable is missing: $BaselineExecutable"
}

Write-Host "Python: $PythonExecutable"
Write-Host "Environment: $EnvironmentName"
Write-Host "Validated baseline preserved: $BaselineExecutable"
Write-Host "Candidate work path: $CandidateWorkPath"
Write-Host "Candidate dist path: $CandidateDistPath"

Push-Location $RepositoryRoot
try {
    $env:MPLCONFIGDIR = Join-Path $CandidateWorkPath "mpl-cache"
    $env:YOLO_AUTOINSTALL = "false"

    & $PythonExecutable $ValidatorPath
    if ($LASTEXITCODE -ne 0) {
        throw "Build environment validation failed."
    }

    & $PythonExecutable -m PyInstaller `
        --noconfirm `
        --clean `
        --workpath $CandidateWorkPath `
        --distpath $CandidateDistPath `
        $SpecPath
    if ($LASTEXITCODE -ne 0) {
        throw "protoc candidate PyInstaller build failed with exit code $LASTEXITCODE."
    }

    if (-not (Test-Path -LiteralPath $ExpectedExecutable -PathType Leaf)) {
        throw "Expected protoc candidate executable was not created: $ExpectedExecutable"
    }

    Write-Host "protoc candidate build complete: $ExpectedExecutable"
}
finally {
    Pop-Location
}
