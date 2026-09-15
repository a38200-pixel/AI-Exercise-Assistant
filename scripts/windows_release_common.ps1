Set-StrictMode -Version Latest

$script:SemVerPattern = '^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?$'

function Assert-SemVer {
    param([Parameter(Mandatory)][string]$Version)

    if ($Version -notmatch $script:SemVerPattern) {
        throw "Version must be valid SemVer (for example 0.1.1): $Version"
    }
}

function Assert-HttpsUrl {
    param(
        [Parameter(Mandatory)][string]$Value,
        [Parameter(Mandatory)][string]$Name
    )

    $uri = $null
    if (-not [Uri]::TryCreate($Value, [UriKind]::Absolute, [ref]$uri) -or $uri.Scheme -ne 'https') {
        throw "$Name must be an absolute HTTPS URL."
    }
}

function Get-RequiredCommand {
    param([Parameter(Mandatory)][string]$Name)

    $command = Get-Command $Name -ErrorAction SilentlyContinue
    if (-not $command) {
        throw "Required command was not found: $Name"
    }
    return $command.Source
}

function Resolve-ExecutableCandidate {
    param([Parameter(Mandatory)][string[]]$Candidates)

    foreach ($candidate in $Candidates) {
        if ($candidate -and (Test-Path -LiteralPath $candidate -PathType Leaf)) {
            return (Resolve-Path -LiteralPath $candidate).Path
        }
    }
    return $null
}

function Resolve-RclonePath {
    $command = Get-Command rclone.exe -ErrorAction SilentlyContinue
    if (-not $command) {
        $command = Get-Command rclone -ErrorAction SilentlyContinue
    }
    if ($command -and $command.Source) {
        return (Resolve-Path -LiteralPath $command.Source).Path
    }

    $winGetPath = if ($env:LOCALAPPDATA) {
        Join-Path $env:LOCALAPPDATA 'Microsoft\WinGet\Links\rclone.exe'
    } else {
        $null
    }
    $resolved = Resolve-ExecutableCandidate -Candidates @($winGetPath)
    if ($resolved) {
        return $resolved
    }
    throw 'rclone was not found. Install rclone or make it available through PATH / WinGet Links.'
}

function Resolve-IsccPath {
    param([string]$CandidatePath = '')

    if ($CandidatePath) {
        $resolved = Resolve-ExecutableCandidate -Candidates @($CandidatePath)
        if (-not $resolved) {
            throw "ISCC.exe was not found at the supplied path: $CandidatePath"
        }
        return $resolved
    }

    $command = Get-Command ISCC.exe -ErrorAction SilentlyContinue
    if ($command -and $command.Source) {
        return (Resolve-Path -LiteralPath $command.Source).Path
    }

    $candidates = @()
    if ($env:LOCALAPPDATA) {
        $candidates += Join-Path $env:LOCALAPPDATA 'Programs\Inno Setup 6\ISCC.exe'
    }
    $programFilesX86 = [Environment]::GetEnvironmentVariable('ProgramFiles(x86)')
    if ($programFilesX86) {
        $candidates += Join-Path $programFilesX86 'Inno Setup 6\ISCC.exe'
    }
    if ($env:ProgramFiles) {
        $candidates += Join-Path $env:ProgramFiles 'Inno Setup 6\ISCC.exe'
    }

    $resolved = Resolve-ExecutableCandidate -Candidates $candidates
    if ($resolved) {
        return $resolved
    }
    throw 'ISCC.exe was not found. Install Inno Setup 6 or pass -IsccExecutable with its full path.'
}

function Resolve-VercelPath {
    foreach ($name in @('vercel.cmd', 'vercel')) {
        $command = Get-Command $name -ErrorAction SilentlyContinue
        if ($command -and $command.Source) {
            return (Resolve-Path -LiteralPath $command.Source).Path
        }
    }

    $candidates = @()
    if ($env:APPDATA) {
        $candidates += Join-Path $env:APPDATA 'npm\vercel.cmd'
    }

    $npmCommand = Get-Command npm.cmd -ErrorAction SilentlyContinue
    if ($npmCommand) {
        $npmPrefix = (& $npmCommand.Source config get prefix 2>$null | Select-Object -First 1)
        if ($LASTEXITCODE -eq 0 -and $npmPrefix) {
            $candidates += Join-Path ([string]$npmPrefix).Trim() 'vercel.cmd'
        }
    }

    $resolved = Resolve-ExecutableCandidate -Candidates $candidates
    if ($resolved) {
        return $resolved
    }
    throw "Vercel CLI was not found. Install it manually with: npm install -g vercel"
}

function ConvertTo-NativeProcessArgument {
    param([Parameter(Mandatory)][AllowEmptyString()][string]$Value)

    if ($Value -match '["\r\n]') {
        throw 'Native process arguments must not contain quotes or line breaks.'
    }
    return '"' + $Value + '"'
}

function Invoke-NativeProcess {
    param(
        [Parameter(Mandatory)][string]$ExecutablePath,
        [Parameter(Mandatory)][string[]]$ArgumentList,
        [string]$WorkingDirectory = '',
        [AllowEmptyString()][string]$StandardInput
    )

    $resolvedExecutable = (Resolve-Path -LiteralPath $ExecutablePath).Path
    $startInfo = New-Object System.Diagnostics.ProcessStartInfo
    $startInfo.FileName = $resolvedExecutable
    $startInfo.Arguments = (($ArgumentList | ForEach-Object {
        ConvertTo-NativeProcessArgument -Value ([string]$_)
    }) -join ' ')
    $startInfo.UseShellExecute = $false
    $startInfo.CreateNoWindow = $true
    if ($WorkingDirectory) {
        $resolvedWorkingDirectory = (Resolve-Path -LiteralPath $WorkingDirectory).Path
        if (-not (Test-Path -LiteralPath $resolvedWorkingDirectory -PathType Container)) {
            throw "Native process working directory was not found: $WorkingDirectory"
        }
        $startInfo.WorkingDirectory = $resolvedWorkingDirectory
    }
    $startInfo.RedirectStandardOutput = $true
    $startInfo.RedirectStandardError = $true
    $hasStandardInput = $PSBoundParameters.ContainsKey('StandardInput')
    $startInfo.RedirectStandardInput = $hasStandardInput

    $process = New-Object System.Diagnostics.Process
    $process.StartInfo = $startInfo
    try {
        if (-not $process.Start()) {
            throw "Native process could not be started: $resolvedExecutable"
        }
        $stdoutTask = $process.StandardOutput.ReadToEndAsync()
        $stderrTask = $process.StandardError.ReadToEndAsync()
        if ($hasStandardInput) {
            $process.StandardInput.WriteLine($StandardInput)
            $process.StandardInput.Close()
        }
        $process.WaitForExit()
        return [PSCustomObject]@{
            ExitCode = $process.ExitCode
            StdOut = $stdoutTask.Result
            StdErr = $stderrTask.Result
        }
    } finally {
        $process.Dispose()
    }
}

function Get-SafeNativeProcessOutput {
    param([Parameter(Mandatory)]$Result)

    $lines = @($Result.StdOut, $Result.StdErr) -join [Environment]::NewLine
    $safeLines = $lines -split '\r?\n' | ForEach-Object {
        if ($_ -match '(?i)(VERCEL_OIDC_TOKEN|authorization|access.?key|secret|password|eyJ[A-Za-z0-9_-]{20,})') {
            '[REDACTED SENSITIVE OUTPUT]'
        } else {
            $_
        }
    }
    $text = ($safeLines -join [Environment]::NewLine).Trim()
    if ($text.Length -gt 6000) {
        return $text.Substring(0, 6000) + [Environment]::NewLine + '[OUTPUT TRUNCATED]'
    }
    return $text
}

function Assert-VercelAuthentication {
    param(
        [Parameter(Mandatory)][string]$VercelExecutable,
        [Parameter(Mandatory)][string]$WorkingDirectory
    )

    $result = Invoke-NativeProcess -ExecutablePath $VercelExecutable -ArgumentList @(
        'whoami', '--cwd', $WorkingDirectory, '--no-color'
    )
    if ($result.ExitCode -ne 0) {
        throw "Vercel CLI is installed but no authenticated session was confirmed. Run 'vercel login' and retry."
    }
}

function Assert-VercelProjectAccess {
    param(
        [Parameter(Mandatory)][string]$VercelExecutable,
        [Parameter(Mandatory)][string]$WorkingDirectory,
        [Parameter(Mandatory)][string]$ProjectName,
        [Parameter(Mandatory)][string]$Scope
    )

    $result = Invoke-NativeProcess -ExecutablePath $VercelExecutable -ArgumentList @(
        'project', 'inspect', $ProjectName, '--scope', $Scope,
        '--format', 'json', '--cwd', $WorkingDirectory, '--no-color'
    )
    if ($result.ExitCode -ne 0) {
        throw "Vercel project '$ProjectName' is not accessible in scope '$Scope'. Verify access without creating or linking a new project."
    }
}

function Get-R2ObjectInfo {
    param(
        [Parameter(Mandatory)][string]$RcloneExecutable,
        [Parameter(Mandatory)][string]$RemoteObject
    )

    $output = & $RcloneExecutable lsjson $RemoteObject --stat --files-only --no-mimetype --no-modtime --s3-no-check-bucket 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "R2 object lookup failed for $RemoteObject. rclone exit code: $LASTEXITCODE"
    }

    $text = ($output | Out-String).Trim()
    if (-not $text) {
        return $null
    }
    try {
        $item = $text | ConvertFrom-Json
    } catch {
        throw "R2 object lookup returned invalid JSON for $RemoteObject."
    }
    if ($item -is [Array]) {
        $item = $item | Select-Object -First 1
    }
    if (-not $item -or $item.IsDir -eq $true -or $null -eq $item.Size) {
        return $null
    }
    return $item
}

function Get-PublicDownloadUrl {
    param(
        [Parameter(Mandatory)][string]$BaseUrl,
        [Parameter(Mandatory)][string]$ObjectKey
    )

    return "$($BaseUrl.TrimEnd('/'))/$ObjectKey"
}

function Write-PlannedCommand {
    param(
        [Parameter(Mandatory)][string]$Executable,
        [Parameter(Mandatory)][string[]]$Arguments
    )

    $rendered = $Arguments | ForEach-Object {
        if ($_ -match '\s') { '"' + $_.Replace('"', '\"') + '"' } else { $_ }
    }
    Write-Output ("PLAN: {0} {1}" -f $Executable, ($rendered -join ' '))
}
