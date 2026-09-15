[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [string]$Version,
    [string]$R2PublicBaseUrl = $env:FITROUTE_R2_PUBLIC_BASE_URL,
    [string]$RcloneRemote = 'r2',
    [string]$R2Bucket = 'fitroute-downloads',
    [string]$PythonExecutable = '',
    [string]$IsccExecutable = '',
    [switch]$DryRun
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
. (Join-Path $PSScriptRoot 'windows_release_common.ps1')

Assert-SemVer -Version $Version
if (-not $R2PublicBaseUrl) {
    throw 'Set FITROUTE_R2_PUBLIC_BASE_URL or pass -R2PublicBaseUrl.'
}
Assert-HttpsUrl -Value $R2PublicBaseUrl -Name 'R2PublicBaseUrl'

$repositoryRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$validator = Join-Path $repositoryRoot 'installer\validate_installer_inputs.py'
$buildScript = Join-Path $repositoryRoot 'installer\build_installer.ps1'
$installerManifestPath = Join-Path $repositoryRoot 'installer\installer_manifest.json'
$installerFileName = "FitRoute-AI-Client-Setup-$Version.exe"
$installerPath = Join-Path $repositoryRoot "installer_output\$installerFileName"
$metadataDirectory = Join-Path $repositoryRoot 'releases\windows'
$metadataPath = Join-Path $metadataDirectory "v$Version.json"
$r2ObjectKey = "releases/v$Version/$installerFileName"
$remoteObject = "$RcloneRemote`:$R2Bucket/$r2ObjectKey"
$downloadUrl = Get-PublicDownloadUrl -BaseUrl $R2PublicBaseUrl -ObjectKey $r2ObjectKey

Push-Location $repositoryRoot
try {
    $gitExecutable = Get-RequiredCommand -Name 'git'
    $workingTree = @(& $gitExecutable status --porcelain=v1 --untracked-files=all)
    if ($LASTEXITCODE -ne 0) {
        throw 'Unable to inspect the Git working tree.'
    }
    if ($workingTree.Count -gt 0) {
        if ($DryRun) {
            Write-Warning 'Git working tree is not clean. A real release would stop.'
        } else {
            throw 'Git working tree must be clean before preparing a release.'
        }
    } else {
        Write-Output 'Git working tree: CLEAN'
    }

    if (Test-Path -LiteralPath $metadataPath) {
        throw "Release metadata already exists; versions are immutable: $metadataPath"
    }
    if (Test-Path -LiteralPath $installerPath) {
        if ($DryRun) {
            Write-Warning "Local installer already exists. A real release would stop instead of overwriting it: $installerPath"
        } else {
            throw "Installer already exists; versions are immutable: $installerPath"
        }
    }

    if (-not $PythonExecutable) {
        if ($env:CONDA_PREFIX -and (Test-Path -LiteralPath (Join-Path $env:CONDA_PREFIX 'python.exe') -PathType Leaf)) {
            $PythonExecutable = Join-Path $env:CONDA_PREFIX 'python.exe'
        } else {
            $PythonExecutable = Get-RequiredCommand -Name 'python.exe'
        }
    }
    if (-not (Test-Path -LiteralPath $PythonExecutable -PathType Leaf)) {
        throw "Python executable was not found: $PythonExecutable"
    }
    $PythonExecutable = (Resolve-Path -LiteralPath $PythonExecutable).Path
    $rcloneExecutable = Resolve-RclonePath
    $IsccExecutable = Resolve-IsccPath -CandidatePath $IsccExecutable

    Write-Output "Version: $Version"
    Write-Output "Installer: $installerPath"
    Write-Output "R2 destination: $remoteObject"
    Write-Output "Download URL: $downloadUrl"
    Write-Output "[rclone] Found: $rcloneExecutable"
    Write-Output "[ISCC] Found: $IsccExecutable"

    & $PythonExecutable $validator --version $Version
    if ($LASTEXITCODE -ne 0) {
        throw 'Installer input validation failed; build and upload are blocked.'
    }

    $buildArguments = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', $buildScript, '-Version', $Version, '-PythonExecutable', $PythonExecutable)
    $buildArguments += @('-IsccExecutable', $IsccExecutable)

    if ($DryRun) {
        Write-PlannedCommand -Executable 'powershell.exe' -Arguments $buildArguments
        Write-PlannedCommand -Executable $rcloneExecutable -Arguments @('copyto', $installerPath, $remoteObject, '--immutable', '--s3-no-check-bucket', '--s3-upload-cutoff=100M', '--s3-chunk-size=100M', '--progress')
        Write-Output "PLAN: verify remote object size, then write $metadataPath"
        Write-Output 'DRY RUN COMPLETE: no installer build, upload, metadata write, Git change, or deployment was performed.'
        return
    }

    $existingObject = Get-R2ObjectInfo -RcloneExecutable $rcloneExecutable -RemoteObject $remoteObject
    if ($existingObject) {
        throw "R2 object already exists; refusing to overwrite immutable version: $remoteObject"
    }

    & powershell.exe @buildArguments
    if ($LASTEXITCODE -ne 0) {
        throw "Installer build failed with exit code $LASTEXITCODE; upload is blocked."
    }
    if (-not (Test-Path -LiteralPath $installerPath -PathType Leaf)) {
        throw "Expected installer was not created: $installerPath"
    }
    if (-not (Test-Path -LiteralPath $installerManifestPath -PathType Leaf)) {
        throw 'Installer build manifest was not created; upload is blocked.'
    }
    $installerManifest = Get-Content -LiteralPath $installerManifestPath -Raw -Encoding utf8 | ConvertFrom-Json
    if ($installerManifest.installer.version -ne $Version) {
        throw "Installer manifest version does not match requested release: $($installerManifest.installer.version) != $Version"
    }

    $installer = Get-Item -LiteralPath $installerPath
    $sha256 = (Get-FileHash -LiteralPath $installerPath -Algorithm SHA256).Hash.ToUpperInvariant()
    Write-Output "Bytes: $($installer.Length)"
    Write-Output ("MiB: {0:N6}" -f ($installer.Length / 1MB))
    Write-Output ("GiB: {0:N6}" -f ($installer.Length / 1GB))
    Write-Output "SHA256: $sha256"

    & $rcloneExecutable copyto $installerPath $remoteObject --immutable --s3-no-check-bucket --s3-upload-cutoff=100M --s3-chunk-size=100M --progress
    if ($LASTEXITCODE -ne 0) {
        throw "R2 upload failed with exit code $LASTEXITCODE; metadata was not written."
    }

    $remoteInfo = Get-R2ObjectInfo -RcloneExecutable $rcloneExecutable -RemoteObject $remoteObject
    if (-not $remoteInfo) {
        throw 'R2 verification failed: uploaded object was not found; metadata was not written.'
    }
    if ([int64]$remoteInfo.Size -ne [int64]$installer.Length) {
        throw "R2 verification failed: remote size $($remoteInfo.Size) does not match local size $($installer.Length)."
    }

    $metadata = [ordered]@{
        version = $Version
        filename = $installerFileName
        size_bytes = [int64]$installer.Length
        sha256 = $sha256
        r2_object_key = $r2ObjectKey
        download_url = $downloadUrl
        built_at = [DateTime]::UtcNow.ToString('o')
    }
    New-Item -ItemType Directory -Path $metadataDirectory -Force | Out-Null
    $metadata | ConvertTo-Json | Set-Content -LiteralPath $metadataPath -Encoding utf8

    Write-Output 'PREPARE RELEASE COMPLETE'
    Write-Output "Metadata: $metadataPath"
    Write-Output 'NEXT: verify web download -> install -> launch -> workout save on a separate Windows PC.'
    Write-Output "Optional manual tag after review: git tag v$Version"
    Write-Output "Optional manual tag push: git push origin v$Version"
} finally {
    Pop-Location
}
