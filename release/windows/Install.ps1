[CmdletBinding()]
param(
    [switch]$SkipPlugin,
    [switch]$PluginOnly
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

$PackageRoot = Split-Path -Parent $PSCommandPath
$PluginSource = Join-Path $PackageRoot 'AI Audio Analyzer.vst3'
$InstallRoot = Join-Path $env:LOCALAPPDATA 'AI Audio Analyzer'

function Install-Vst3 {
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

if ($PluginOnly) {
    if (-not (Test-IsAdministrator)) {
        throw 'PluginOnly mode requires Administrator permission.'
    }
    Write-Step 'Installing VST3'
    Install-Vst3
    exit 0
}

Write-Host 'AI Audio Analyzer installer'
Write-Host 'No programming tools are required.' -ForegroundColor Green

if (-not $SkipPlugin) {
    if (Test-IsAdministrator) {
        Write-Step 'Installing VST3'
        Install-Vst3
    } else {
        Write-Host 'Windows will ask for Administrator permission to copy the VST3.'
        $arguments = @(
            '-NoProfile',
            '-ExecutionPolicy', 'Bypass',
            '-File', ('"{0}"' -f $PSCommandPath),
            '-PluginOnly'
        )
        $process = Start-Process -FilePath 'powershell.exe' -Verb RunAs -ArgumentList $arguments -Wait -PassThru
        if ($process.ExitCode -ne 0) {
            throw "VST3 installation failed with exit code $($process.ExitCode)."
        }
    }
}

Write-Step 'Installing Analyzer connection and Cherry Studio Skill'
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

$McpExe = Join-Path $InstallRoot 'mcp\ai-audio-analyzer-mcp.exe'
if (-not (Test-Path $McpExe)) {
    throw "Analyzer MCP executable not found: $McpExe"
}

Write-Step 'Checking Analyzer connection service'
$oldSelfTest = $env:AI_ANALYZER_SELF_TEST
try {
    $env:AI_ANALYZER_SELF_TEST = '1'
    & $McpExe
    if ($LASTEXITCODE -ne 0) {
        throw "Analyzer MCP self-test failed with exit code $LASTEXITCODE."
    }
} finally {
    if ($null -eq $oldSelfTest) {
        Remove-Item Env:AI_ANALYZER_SELF_TEST -ErrorAction SilentlyContinue
    } else {
        $env:AI_ANALYZER_SELF_TEST = $oldSelfTest
    }
}

Write-Step 'Creating Cherry Studio configuration'
$ConfigPath = Join-Path $InstallRoot 'cherry-studio-mcp.json'
$config = @{
    mcpServers = @{
        'ai-audio-analyzer' = @{
            command = $McpExe
            args = @()
            env = @{
                AI_ANALYZER_OSC_HOST = '127.0.0.1'
                AI_ANALYZER_OSC_PORT = '9855'
            }
        }
    }
}
$config | ConvertTo-Json -Depth 8 | Set-Content -Path $ConfigPath -Encoding UTF8

Write-Host ''
Write-Host 'Installation completed successfully.' -ForegroundColor Green
Write-Host ''
Write-Host 'Next steps:'
Write-Host '1. Restart FL Studio and rescan VST3 plugins.'
Write-Host '2. In Cherry Studio, add the generated MCP configuration:'
Write-Host "   $ConfigPath"
Write-Host '3. Import the installed Skill folder:'
Write-Host "   $(Join-Path $InstallRoot 'skill')"
Write-Host ''
Write-Host 'You do not need Python, pip, a terminal, or any programming setup.' -ForegroundColor Green
