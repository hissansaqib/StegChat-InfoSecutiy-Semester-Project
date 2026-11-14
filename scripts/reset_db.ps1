$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Split-Path -Parent $ScriptDir
Set-Location $RepoRoot

$DataDir = Join-Path $RepoRoot "data"
if (-not (Test-Path $DataDir)) {
    New-Item -ItemType Directory -Path $DataDir -Force | Out-Null
}

$DbPath = Join-Path $DataDir "stegchat.db"
if (Test-Path $DbPath) {
    Write-Host "Backing up existing database to stegchat.db.bak..."
    Copy-Item $DbPath "$DbPath.bak" -Force
    Remove-Item $DbPath -Force
}

Write-Host "Running alembic upgrade head to build clean database schema..."
py -3.14-64 -m alembic upgrade head

Write-Host "Database reset complete: $DbPath"

