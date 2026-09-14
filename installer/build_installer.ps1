param(
    [string]$PythonExecutable = "",
    [string]$IsccExecutable = ""
)

$ErrorActionPreference = "Stop"
$installerRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$repositoryRoot = Split-Path -Parent $installerRoot
$validator = Join-Path $installerRoot "validate_installer_inputs.py"
$iss = Join-Path $installerRoot "FitRouteAIClient.iss"
$output = Join-Path $repositoryRoot "installer_output\FitRoute-AI-Client-Setup-0.1.0.exe"
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

& $PythonExecutable $validator --write-manifest
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

if ($IsccExecutable) {
    if (-not (Test-Path -LiteralPath $IsccExecutable -PathType Leaf)) {
        throw "ISCC.exe was not found at the supplied path: $IsccExecutable"
    }
    $IsccExecutable = (Resolve-Path -LiteralPath $IsccExecutable).Path
} else {
    $isccCommand = Get-Command ISCC.exe -ErrorAction SilentlyContinue
    $isccCandidates = @()
    if ($isccCommand) {
        $isccCandidates += $isccCommand.Source
    }
    $isccCandidates += @(
        "C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
        "C:\Program Files\Inno Setup 6\ISCC.exe"
    )
    foreach ($registryPath in @(
        "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\Inno Setup 6_is1",
        "HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\Inno Setup 6_is1",
        "HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\Inno Setup 6_is1"
    )) {
        $item = Get-ItemProperty -LiteralPath $registryPath -ErrorAction SilentlyContinue
        if ($item.InstallLocation) {
            $isccCandidates += (Join-Path $item.InstallLocation "ISCC.exe")
        }
    }
    $IsccExecutable = $isccCandidates |
        Where-Object { $_ -and (Test-Path -LiteralPath $_ -PathType Leaf) } |
        Select-Object -First 1
}

if (-not $IsccExecutable) {
    Write-Output "INSTALLER SCRIPT READY"
    Write-Output "INNO SETUP COMPILER NOT FOUND"
    exit 2
}

$IsccExecutable = (Resolve-Path -LiteralPath $IsccExecutable).Path
$isccVersion = (Get-Item -LiteralPath $IsccExecutable).VersionInfo.ProductVersion
Write-Output "ISCC: $IsccExecutable"
Write-Output "Inno Setup version: $isccVersion"

& $IsccExecutable $iss
if ($LASTEXITCODE -ne 0) {
    throw "Inno Setup compile failed with exit code $LASTEXITCODE."
}
if (-not (Test-Path -LiteralPath $output -PathType Leaf)) {
    throw "Expected single-file installer output was not created: $output"
}

& $PythonExecutable $validator
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
