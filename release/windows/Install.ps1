[CmdletBinding()]
param(
    [ValidateSet('auto', 'official', 'tsinghua', 'aliyun')]
    [string]$PyPI = 'auto',
    [switch]$SkipPlugin
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Write-Step([string]$Message) {
    Write-Host "`n==> $Message" -ForegroundColor Cyan
}

function Test-IsAdministrator {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($identity)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Resolve-CompatiblePython {
    $candidates = @(
        @{ Exe = 'py'; Args = @('-3.12') },
        @{ Exe = 'py'; Args = @('-3') },
        @{ Exe = 'python'; Args = @() },
        @{ Exe = 'python3'; Args = @() }
    )

    foreach ($candidate in $candidates) {
        if (-not (Get-Command $candidate.Exe -ErrorAction SilentlyContinue)) { continue }
        try {
            $prefix = @($candidate.Args)
            $path = & $candidate.Exe @prefix -c "import sys; print(sys.executable if sys.version_info >= (3,10) else '')" 2>$null
            if ($LASTEXITCODE -eq 0 -and $path) {
                return ($path | Select-Object -First 1).Trim()
            }
        } catch {}
    }

    $fallbacks = @(
        "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python313\python.exe"
    )
    foreach ($path in $fallbacks) {
        if (Test-Path $path) { return $path }
    }
    return $null
}

function Install-PythonIfNeeded {
    $python = Resolve-CompatiblePython
    if ($python) { return $python }

    Write-Step 'Compatible Python not found'
    if (Get-Command winget -ErrorAction SilentlyContinue) {
        Write-Host 'Installing Python 3.12 with winget...'
        & winget install -e --id Python.Python.3.12 --scope user --accept-package-agreements --accept-source-agreements
        if ($LASTEXITCODE -ne 0) {
            throw 'winget could not install Python 3.12. See INSTALL.zh-CN.md / INSTALL.en.md for manual Python installation.'
        }
        Start-Sleep -Seconds 2
        $python = Resolve-CompatiblePython
        if ($python) { return $python }
    }

    throw 'Python 3.10+ is required and could not be installed automatically. Install Python 3.12, then run Install.cmd again.'
}

function Get-PyPIIndexes([string]$Mode) {
    switch ($Mode) {
        'official'  { return @('https://pypi.org/simple') }
        'tsinghua'  { return @('https://pypi.tuna.tsinghua.edu.cn/simple') }
        'aliyun'    { return @('https://mirrors.aliyun.com/pypi/simple/') }
        default     { return @(
            'https://pypi.org/simple',
            'https://pypi.tuna.tsinghua.edu.cn/simple',
            'https://mirrors.aliyun.com/pypi/simple/'
        ) }
    }
}

$PackageRoot = Split-Path -Parent $PSCommandPath
$PluginSource = Join-Path $PackageRoot 'AI Audio Analyzer.vst3'
$McpSource = Join-Path $PackageRoot 'mcp'
$SkillSource = Join-Path $PackageRoot 'skill'
$InstallRoot = Join-Path $env:LOCALAPPDATA 'AI Audio Analyzer'
$VenvRoot = Join-Path $InstallRoot 'venv'

if (-not $SkipPlugin -and -not (Test-IsAdministrator)) {
    Write-Host 'VST3 installation needs Administrator permission. Requesting UAC...'
    $arguments = @(
        '-NoProfile',
        '-ExecutionPolicy', 'Bypass',
        '-File', ('"{0}"' -f $PSCommandPath),
        '-PyPI', $PyPI
    )
    Start-Process -FilePath 'powershell.exe' -Verb RunAs -ArgumentList $arguments -Wait
    exit $LASTEXITCODE
}

Write-Host 'AI Audio Analyzer automatic installer'
Write-Host "Package: $PackageRoot"

if (-not $SkipPlugin) {
    Write-Step 'Installing VST3'
    if (-not (Test-Path $PluginSource)) {
        throw "Plugin bundle not found: $PluginSource"
    }
    $Vst3Root = Join-Path ${env:ProgramFiles} 'Common Files\VST3'
    New-Item -ItemType Directory -Path $Vst3Root -Force | Out-Null
    $PluginDestination = Join-Path $Vst3Root 'AI Audio Analyzer.vst3'
    if (Test-Path $PluginDestination) {
        Remove-Item $PluginDestination -Recurse -Force
    }
    Copy-Item $PluginSource $PluginDestination -Recurse -Force
    Write-Host "Installed: $PluginDestination"
}

Write-Step 'Preparing Analyzer MCP and Skill'
New-Item -ItemType Directory -Path $InstallRoot -Force | Out-Null

foreach ($name in @('mcp', 'skill')) {
    $source = Join-Path $PackageRoot $name
    $destination = Join-Path $InstallRoot $name
    if (-not (Test-Path $source)) { throw "Missing package folder: $source" }
    if (Test-Path $destination) { Remove-Item $destination -Recurse -Force }
    Copy-Item $source $destination -Recurse -Force
}

foreach ($doc in @('START-HERE.md', 'INSTALL.en.md', 'INSTALL.zh-CN.md')) {
    $source = Join-Path $PackageRoot $doc
    if (Test-Path $source) { Copy-Item $source $InstallRoot -Force }
}

Write-Step 'Checking Python'
$Python = Install-PythonIfNeeded
Write-Host "Python: $Python"
& $Python -c "import sys; print('Python', sys.version)"
if ($LASTEXITCODE -ne 0) { throw 'Selected Python interpreter could not start.' }

Write-Step 'Creating isolated MCP virtual environment'
if (Test-Path $VenvRoot) { Remove-Item $VenvRoot -Recurse -Force }
& $Python -m venv $VenvRoot
if ($LASTEXITCODE -ne 0) { throw 'Could not create Python virtual environment.' }

$VenvPython = Join-Path $VenvRoot 'Scripts\python.exe'
if (-not (Test-Path $VenvPython)) { throw "Virtual environment Python not found: $VenvPython" }

& $VenvPython -m pip install --upgrade pip --disable-pip-version-check
if ($LASTEXITCODE -ne 0) { Write-Warning 'pip upgrade failed; continuing with the bundled pip.' }

Write-Step 'Installing MCP dependencies'
$Requirements = Join-Path $InstallRoot 'mcp\requirements.txt'
$installed = $false
foreach ($index in (Get-PyPIIndexes $PyPI)) {
    Write-Host "Trying PyPI index: $index"
    & $VenvPython -m pip install --disable-pip-version-check --timeout 30 --retries 2 -i $index -r $Requirements
    if ($LASTEXITCODE -eq 0) {
        $installed = $true
        Write-Host "Dependencies installed from: $index" -ForegroundColor Green
        break
    }
    Write-Warning "Dependency installation failed from $index"
}
if (-not $installed) {
    throw 'Could not install MCP dependencies from any configured PyPI index. See INSTALL.zh-CN.md / INSTALL.en.md.'
}

Write-Step 'Validating MCP runtime'
$ServerPath = Join-Path $InstallRoot 'mcp\server.py'
& $VenvPython -m py_compile $ServerPath
if ($LASTEXITCODE -ne 0) { throw 'server.py syntax validation failed.' }
& $VenvPython -c "from mcp.server import MCPServer; import pythonosc; print('MCP v2 runtime OK')"
if ($LASTEXITCODE -ne 0) { throw 'MCP runtime import validation failed.' }

Write-Step 'Generating Cherry Studio MCP configuration'
$ConfigPath = Join-Path $InstallRoot 'cherry-studio-mcp.json'
$config = @{
    mcpServers = @{
        'ai-audio-analyzer' = @{
            command = $VenvPython
            args = @($ServerPath)
            env = @{
                AI_ANALYZER_OSC_HOST = '127.0.0.1'
                AI_ANALYZER_OSC_PORT = '9855'
            }
        }
    }
}
$config | ConvertTo-Json -Depth 8 | Set-Content -Path $ConfigPath -Encoding UTF8

Write-Host ''
Write-Host 'Installation completed.' -ForegroundColor Green
Write-Host "MCP config: $ConfigPath"
Write-Host "Skill folder: $(Join-Path $InstallRoot 'skill')"
Write-Host ''
Write-Host 'Next:'
Write-Host '1. Fully restart FL Studio and rescan VST3 plugins.'
Write-Host '2. Add the generated MCP config to Cherry Studio.'
Write-Host '3. Import the Skill folder into Cherry Studio.'
Write-Host '4. For DAW control, also install https://github.com/rosasynthesiz/flstudio-mcp'
