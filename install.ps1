# ==============================================================================
# Ace — One-Line Installer for Windows PowerShell
# Repo: https://github.com/jachinsamuel/Ace
# ==============================================================================

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "   ___        " -ForegroundColor Cyan
Write-Host "  / _ | ______ " -ForegroundColor Cyan
Write-Host " / __ |/ __/ -_)" -ForegroundColor Cyan
Write-Host "/_/ |_|\__/\__/ " -ForegroundColor Cyan
Write-Host "AI-Powered Git Copilot Installer (Windows)" -ForegroundColor Cyan
Write-Host ""

# 1. Find compatible Python (3.11+)
function Find-Python {
    $candidates = @("python", "py", "python3")
    foreach ($cmd in $candidates) {
        $exec = Get-Command $cmd -ErrorAction SilentlyContinue
        if ($exec) {
            try {
                $verStr = & $cmd -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>$null
                if ($verStr) {
                    $parts = $verStr.Trim().Split('.')
                    $major = [int]$parts[0]
                    $minor = [int]$parts[1]
                    if ($major -eq 3 -and $minor -ge 11) {
                        return $cmd
                    }
                }
            } catch {}
        }
    }
    return $null
}

$pyCmd = Find-Python

if (-not $pyCmd) {
    Write-Host "Error: Python 3.11 or newer is required to install Ace." -ForegroundColor Red
    Write-Host "Please download Python 3.11+ from https://www.python.org or run 'winget install Python.Python.3.12'" -ForegroundColor Yellow
    exit 1
}

$pyVer = & $pyCmd --version
Write-Host "✔ Found compatible Python: $pyVer" -ForegroundColor Green

# 2. Check for uv or pipx, else install into isolated folder
$uv = Get-Command uv -ErrorAction SilentlyContinue
$pipx = Get-Command pipx -ErrorAction SilentlyContinue

$installDir = "$env:LOCALAPPDATA\Programs\ace"
$binDir = "$installDir\bin"

if ($uv) {
    Write-Host "→ Installing via uv tool..." -ForegroundColor Cyan
    & uv tool install ace-git-copilot --force
} elseif ($pipx) {
    Write-Host "→ Installing via pipx..." -ForegroundColor Cyan
    & pipx install ace-git-copilot --force
} else {
    Write-Host "→ Creating isolated environment in $installDir..." -ForegroundColor Cyan
    New-Item -ItemType Directory -Force -Path $binDir | Out-Null
    
    & $pyCmd -m venv "$installDir\venv"
    & "$installDir\venv\Scripts\pip.exe" install --quiet --upgrade pip
    & "$installDir\venv\Scripts\pip.exe" install --quiet --upgrade ace-git-copilot
    
    # Create wrapper cmd in binDir
    $batContent = "@echo off`r`n`"$installDir\venv\Scripts\ace.exe`" %*"
    Set-Content -Path "$binDir\ace.cmd" -Value $batContent -Encoding ASCII
}

# 3. Check and update User PATH if not present
$userPath = [Environment]::GetEnvironmentVariable("Path", [EnvironmentVariableTarget]::User)
$needsPathUpdate = $false

if ($uv -or $pipx) {
    # uv / pipx manage their own paths
} else {
    if ($userPath -notlike "*$binDir*") {
        Write-Host "→ Adding $binDir to User PATH..." -ForegroundColor Cyan
        [Environment]::SetEnvironmentVariable("Path", "$userPath;$binDir", [EnvironmentVariableTarget]::User)
        $env:Path = "$env:Path;$binDir"
        $needsPathUpdate = $true
    }
}

Write-Host ""
Write-Host "✔ Ace Git Copilot installed successfully!" -ForegroundColor Green
Write-Host ""

if ($needsPathUpdate) {
    Write-Host "Notice: Environment path updated. You may need to restart your terminal for 'ace' to be globally available." -ForegroundColor Yellow
    Write-Host ""
}

Write-Host "Get started by running:" -ForegroundColor White
Write-Host "  ace setup   → Configure your preferred AI model" -ForegroundColor Cyan
Write-Host "  ace dash    → Open the interactive Git cockpit" -ForegroundColor Cyan
Write-Host ""
