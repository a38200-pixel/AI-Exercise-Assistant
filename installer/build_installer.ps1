param(
    [string]$PythonExecutable = "",
    [string]$IsccExecutable = "",
    [ValidatePattern('^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?$')]
    [string]$Version = "0.1.0"
)

$ErrorActionPreference = "Stop"
$installerRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$repositoryRoot = Split-Path -Parent $installerRoot
$releaseHelpers = Join-Path $repositoryRoot "scripts\windows_release_common.ps1"
if (-not (Test-Path -LiteralPath $releaseHelpers -PathType Leaf)) {
    throw "Release helper was not found: $releaseHelpers"
}
. $releaseHelpers
$validator = Join-Path $installerRoot "validate_installer_inputs.py"
$iss = Join-Path $installerRoot "FitRouteAIClient.iss"
$output = Join-Path $repositoryRoot "installer_output\FitRoute-AI-Client-Setup-$Version.exe"
$launcher = Join-Path $repositoryRoot "desktop_launcher\dist\FitRouteLauncher.exe"
$aiRoot = Join-Path $repositoryRoot "dist_candidate_protoc\FitRouteAIClient"
$aiExe = Join-Path $aiRoot "FitRouteAIClient.exe"
$models = @(
    (Join-Path $aiRoot "models\detector\yolo26n.engine"),
    (Join-Path $aiRoot "models\pose\pose_landmarker_full.task"),
    (Join-Path $aiRoot "models\classifier\model_weights.xgb"),
    (Join-Path $aiRoot "models\classifier\classes.json")
)

if ((Resolve-Path -LiteralPath (Get-Location)).Path -ne (Resolve-Path -LiteralPath $repositoryRoot).Path) {
    Write-Output "Build can run from any directory; repository root resolved to: $repositoryRoot"
}

if (-not $PythonExecutable) {
    if ($env:CONDA_PREFIX -and (Test-Path -LiteralPath (Join-Path $env:CONDA_PREFIX "python.exe") -PathType Leaf)) {
        $PythonExecutable = Join-Path $env:CONDA_PREFIX "python.exe"
    } else {
        $pythonCommand = Get-Command python.exe -ErrorAction SilentlyContinue
        if ($pythonCommand) {
            $PythonExecutable = $pythonCommand.Source
        }
    }
}
if (-not $PythonExecutable -or -not (Test-Path -LiteralPath $PythonExecutable -PathType Leaf)) {
    throw "Python is required only to validate installer inputs. Pass -PythonExecutable with a valid path."
}
$PythonExecutable = (Resolve-Path -LiteralPath $PythonExecutable).Path

& $PythonExecutable $validator --version $Version
if ($LASTEXITCODE -ne 0) {
    throw "Installer input validation failed."
}

$protectedSources = @($launcher, $aiExe) + $models
$before = @{}
foreach ($path in $protectedSources) {
    $resolved = (Resolve-Path -LiteralPath $path).Path
    $before[$resolved] = (Get-FileHash -LiteralPath $resolved -Algorithm SHA256).Hash
}
$beforeCount = @(Get-ChildItem -LiteralPath $aiRoot -Recurse -File).Count
$beforeBytes = (Get-ChildItem -LiteralPath $aiRoot -Recurse -File | Measure-Object -Property Length -Sum).Sum

$IsccExecutable = Resolve-IsccPath -CandidatePath $IsccExecutable
$isccVersion = (Get-Item -LiteralPath $IsccExecutable).VersionInfo.ProductVersion
Write-Output "ISCC: $IsccExecutable"
Write-Output "Inno Setup version: $isccVersion"

& $IsccExecutable "/DMyAppVersion=$Version" $iss
if ($LASTEXITCODE -ne 0) {
    throw "Inno Setup compile failed with exit code $LASTEXITCODE."
}
if (-not (Test-Path -LiteralPath $output -PathType Leaf)) {
    throw "Expected single-file installer output was not created: $output"
}

& $PythonExecutable $validator --version $Version --write-manifest
if ($LASTEXITCODE -ne 0) {
    throw "Post-compile installer input validation failed."
}
$afterCount = @(Get-ChildItem -LiteralPath $aiRoot -Recurse -File).Count
$afterBytes = (Get-ChildItem -LiteralPath $aiRoot -Recurse -File | Measure-Object -Property Length -Sum).Sum
if ($beforeCount -ne $afterCount -or $beforeBytes -ne $afterBytes) {
    throw "AI baseline inventory changed during installer compilation."
}
foreach ($path in $protectedSources) {
    $resolved = (Resolve-Path -LiteralPath $path).Path
    $afterHash = (Get-FileHash -LiteralPath $resolved -Algorithm SHA256).Hash
    if ($before[$resolved] -ne $afterHash) {
        throw "Protected source changed during installer compilation: $resolved"
    }
}

$outputItem = Get-Item -LiteralPath $output
$outputHash = (Get-FileHash -LiteralPath $output -Algorithm SHA256).Hash
$ratio = $outputItem.Length / [double]$beforeBytes
Write-Output "INSTALLER BUILD PASS"
Write-Output "Output: $($outputItem.FullName)"
Write-Output "Bytes: $($outputItem.Length)"
Write-Output ("MiB: {0:N6}" -f ($outputItem.Length / 1MB))
Write-Output ("GiB: {0:N6}" -f ($outputItem.Length / 1GB))
Write-Output ("Output/baseline ratio: {0:P3}" -f $ratio)
Write-Output "SHA256: $outputHash"
Write-Output "Protected source hashes unchanged: YES"
