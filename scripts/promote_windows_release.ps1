[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [string]$Version,
    [string]$RcloneRemote = 'r2',
    [string]$R2Bucket = 'fitroute-downloads',
    [string]$CurrentDownloadUrl = '',
    [string]$FrontendProductionUrl = 'https://fitroute-ivory.vercel.app/',
    [switch]$ApproveProductionChange,
    [switch]$DryRun
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
. (Join-Path $PSScriptRoot 'windows_release_common.ps1')

Assert-SemVer -Version $Version
Assert-HttpsUrl -Value $FrontendProductionUrl -Name 'FrontendProductionUrl'

$repositoryRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$frontendDirectory = Join-Path $repositoryRoot 'frontend'
$metadataPath = Join-Path $repositoryRoot "releases\windows\v$Version.json"
$productionStatePath = Join-Path $repositoryRoot 'releases\windows\production.json'

if (-not (Test-Path -LiteralPath $metadataPath -PathType Leaf)) {
    throw "Release metadata was not found: $metadataPath"
}
$metadata = Get-Content -LiteralPath $metadataPath -Raw -Encoding utf8 | ConvertFrom-Json
$requiredFields = @('version', 'filename', 'size_bytes', 'sha256', 'r2_object_key', 'download_url', 'built_at')
foreach ($field in $requiredFields) {
    if ($field -notin $metadata.PSObject.Properties.Name) {
        throw "Release metadata is missing required field: $field"
    }
}

$expectedFilename = "FitRoute-AI-Client-Setup-$Version.exe"
$expectedObjectKey = "releases/v$Version/$expectedFilename"
if ($metadata.version -ne $Version) { throw 'Metadata version does not match requested version.' }
if ($metadata.filename -ne $expectedFilename) { throw 'Metadata filename does not match requested version.' }
if ($metadata.r2_object_key -ne $expectedObjectKey) { throw 'Metadata R2 object key is not canonical.' }
if ([int64]$metadata.size_bytes -le 0) { throw 'Metadata size_bytes must be positive.' }
if ($metadata.sha256 -notmatch '^[A-Fa-f0-9]{64}$') { throw 'Metadata SHA-256 is missing or invalid.' }
Assert-HttpsUrl -Value $metadata.download_url -Name 'metadata.download_url'

if (-not $CurrentDownloadUrl -and (Test-Path -LiteralPath $productionStatePath -PathType Leaf)) {
    $productionState = Get-Content -LiteralPath $productionStatePath -Raw -Encoding utf8 | ConvertFrom-Json
    $CurrentDownloadUrl = [string]$productionState.download_url
}
if (-not $CurrentDownloadUrl) {
    if ($DryRun) {
        $CurrentDownloadUrl = '<not recorded; supply -CurrentDownloadUrl for the first promotion>'
    } else {
        throw 'Current production URL is not recorded. Pass -CurrentDownloadUrl for the first promotion.'
    }
}

$remoteObject = "$RcloneRemote`:$R2Bucket/$($metadata.r2_object_key)"
$rcloneExecutable = Resolve-RclonePath
$vercelExecutable = Resolve-VercelPath
Write-Output "[rclone] Found: $rcloneExecutable"
Write-Output "[Vercel] Found: $vercelExecutable"
Assert-VercelAuthentication -VercelExecutable $vercelExecutable -WorkingDirectory $frontendDirectory
Write-Output '[Vercel] Authentication: CONFIRMED'

Write-Output 'Production change'
Write-Output "  Current: $CurrentDownloadUrl"
Write-Output "  New:     $($metadata.download_url)"
Write-Output "  Version: v$Version"
Write-Output "  SHA256:  $($metadata.sha256)"

if ($DryRun) {
    Write-PlannedCommand -Executable $rcloneExecutable -Arguments @('lsjson', $remoteObject, '--stat', '--files-only', '--no-mimetype', '--no-modtime', '--s3-no-check-bucket')
    Write-PlannedCommand -Executable $vercelExecutable -Arguments @('env', 'add', 'VITE_DESKTOP_CLIENT_DOWNLOAD_URL', 'production', '--force', '--cwd', $frontendDirectory)
    Write-PlannedCommand -Executable $vercelExecutable -Arguments @('deploy', '--prod', '--yes', '--cwd', $frontendDirectory)
    Write-Output "PLAN: verify HTTP status at $FrontendProductionUrl"
    Write-Output 'DRY RUN COMPLETE: no R2 mutation, Vercel change, deployment, state write, or Git change was performed.'
    return
}

if (-not $ApproveProductionChange) {
    throw 'Production promotion requires explicit -ApproveProductionChange approval.'
}

$gitExecutable = Get-RequiredCommand -Name 'git'
Push-Location $repositoryRoot
try {
    $workingTree = @(& $gitExecutable status --porcelain=v1 --untracked-files=all)
    if ($LASTEXITCODE -ne 0) { throw 'Unable to inspect the Git working tree.' }
    if ($workingTree.Count -gt 0) { throw 'Git working tree must be clean before Production promotion.' }

    $remoteInfo = Get-R2ObjectInfo -RcloneExecutable $rcloneExecutable -RemoteObject $remoteObject
    if (-not $remoteInfo) { throw "R2 release object was not found: $remoteObject" }
    if ([int64]$remoteInfo.Size -ne [int64]$metadata.size_bytes) {
        throw "R2 object size does not match release metadata: $($remoteInfo.Size) != $($metadata.size_bytes)"
    }

    $projectLink = Join-Path $frontendDirectory '.vercel\project.json'
    if (-not (Test-Path -LiteralPath $projectLink -PathType Leaf)) {
        throw "Vercel project is not linked. Run 'vercel link --cwd frontend' interactively first."
    }
    $metadata.download_url | & $vercelExecutable env add VITE_DESKTOP_CLIENT_DOWNLOAD_URL production --force --cwd $frontendDirectory --no-color
    if ($LASTEXITCODE -ne 0) { throw 'Vercel Production environment update failed; deployment was not started.' }

    $deployOutput = @(& $vercelExecutable deploy --prod --yes --cwd $frontendDirectory --no-color 2>&1)
    if ($LASTEXITCODE -ne 0) {
        throw "Vercel Production deploy failed. Restore the previous release with this script. Output: $($deployOutput -join ' ')"
    }
    $deploymentUrl = $deployOutput | Where-Object { $_ -match '^https://' } | Select-Object -Last 1
    if (-not $deploymentUrl) { throw 'Vercel deploy completed without returning a deployment URL.' }

    $response = Invoke-WebRequest -UseBasicParsing -Uri $FrontendProductionUrl -TimeoutSec 60
    if ($response.StatusCode -lt 200 -or $response.StatusCode -ge 400) {
        throw "Frontend Production health check failed with HTTP $($response.StatusCode)."
    }

    $state = [ordered]@{
        version = $Version
        download_url = [string]$metadata.download_url
        sha256 = [string]$metadata.sha256
        deployment_url = [string]$deploymentUrl
        production_url = $FrontendProductionUrl
        promoted_at = [DateTime]::UtcNow.ToString('o')
    }
    $state | ConvertTo-Json | Set-Content -LiteralPath $productionStatePath -Encoding utf8

    Write-Output 'WINDOWS RELEASE PROMOTION COMPLETE'
    Write-Output "Deployment: $deploymentUrl"
    Write-Output "Production: $FrontendProductionUrl (HTTP $($response.StatusCode))"
    Write-Output "State: $productionStatePath"
} finally {
    Pop-Location
}
