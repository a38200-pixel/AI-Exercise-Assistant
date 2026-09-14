param(
    [string]$PythonExecutable = "",
    [string]$AiClientExecutable = "",
    [string]$ApiBaseUrl = "https://fitroute-api.onrender.com",
    [string]$SupabaseUrl = "",
    [string]$SupabaseAnonKey = ""
)

$ErrorActionPreference = "Stop"
$launcherRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not $PythonExecutable) {
    $PythonExecutable = (Get-Command python -ErrorAction Stop).Source
}

$PythonExecutable = (Resolve-Path -LiteralPath $PythonExecutable -ErrorAction Stop).Path
$launcherDist = Join-Path $launcherRoot "dist"
if (-not $AiClientExecutable) {
    $AiClientExecutable = "..\..\dist\FitRouteAIClient\FitRouteAIClient.exe"
}
$aiClientPath = $AiClientExecutable
if (-not [System.IO.Path]::IsPathRooted($aiClientPath)) {
    $aiClientPath = Join-Path $launcherDist $aiClientPath
}
$aiClientPath = [System.IO.Path]::GetFullPath($aiClientPath)
if (-not (Test-Path -LiteralPath $aiClientPath -PathType Leaf)) {
    throw "FitRoute AI Client executable was not found: $aiClientPath"
}
if (-not $SupabaseUrl -or -not $SupabaseAnonKey) {
    throw "SupabaseUrl and SupabaseAnonKey (publishable key only) are required for Desktop login."
}

& $PythonExecutable -c "import supabase, supabase_auth, tkinter"
if ($LASTEXITCODE -ne 0) {
    throw "Desktop dependencies are missing. Install desktop_launcher/requirements.txt in the selected environment."
}

& $PythonExecutable -c "import PyInstaller" 2>$null
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller is not installed in the selected Python environment. Install it explicitly, then rerun this script."
}

$environmentRoot = Split-Path -Parent $PythonExecutable
$condaLibraryBin = Join-Path $environmentRoot "Library\bin"
$runtimeDllPaths = @(
    foreach ($dllName in @(
        "ffi-7.dll",
        "ffi-8.dll",
        "ffi.dll",
        "libexpat.dll",
        "liblzma.dll",
        "LIBBZ2.dll",
        "sqlite3.dll",
        "libzmq-mt-4_3_5.dll",
        "tk86t.dll",
        "tcl86t.dll"
    )) {
        $dllPath = Join-Path $condaLibraryBin $dllName
        if (Test-Path -LiteralPath $dllPath -PathType Leaf) {
            (Resolve-Path -LiteralPath $dllPath).Path
        }
    }
)

$pyInstallerArguments = @(
    "-m", "PyInstaller",
    "--noconfirm",
    "--clean",
    "--onefile",
    "--noconsole",
    "--hidden-import", "supabase_auth",
    "--exclude-module", "PyQt5",
    "--exclude-module", "PyQt6",
    "--exclude-module", "matplotlib",
    "--name", "FitRouteLauncher",
    "--distpath", (Join-Path $launcherRoot "dist"),
    "--workpath", (Join-Path $launcherRoot "build"),
    "--specpath", $launcherRoot
)
foreach ($dllPath in $runtimeDllPaths) {
    $pyInstallerArguments += @("--add-binary", "$dllPath;.")
}
$pyInstallerArguments += (Join-Path $launcherRoot "launcher.py")

& $PythonExecutable @pyInstallerArguments
if ($LASTEXITCODE -ne 0) {
    throw "FitRouteLauncher.exe build failed."
}

$config = [ordered]@{
    ai_client_executable = $AiClientExecutable
    api_base_url = $ApiBaseUrl.TrimEnd("/")
    supabase_url = $SupabaseUrl.TrimEnd("/")
    supabase_anon_key = $SupabaseAnonKey
}
$config | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $launcherRoot "dist\config.json") -Encoding UTF8
Write-Output "Launcher: $(Join-Path $launcherRoot 'dist\FitRouteLauncher.exe')"
Write-Output "Config:   $(Join-Path $launcherRoot 'dist\config.json')"
