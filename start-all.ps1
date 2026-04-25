#Requires -Version 5.1
<#
.SYNOPSIS
    Start all Zetheta platform services in separate terminal windows.
.DESCRIPTION
    Opens 5 PowerShell windows — one for each service — so you can debug
    each independently. Press Ctrl+C in any window to stop that service.
    Run this script from the project root.
#>

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Definition
if (-not $projectRoot) { $projectRoot = Get-Location }

$services = @(
    @{
        Name = "AUTH"
        Title = "Auth Service (3001)"
        Color = "Blue"
        Command = "cd '$projectRoot'; `$env:PYTHONPATH = 'services'; python -m uvicorn auth-service.main:app --host 0.0.0.0 --port 3001"
    },
    @{
        Name = "GATEWAY"
        Title = "API Gateway (3000)"
        Color = "Green"
        Command = "cd '$projectRoot'; `$env:PYTHONPATH = 'services'; python -m uvicorn api-gateway.main:app --host 0.0.0.0 --port 3000"
    },
    @{
        Name = "CANDIDATE"
        Title = "Candidate Portal (4000)"
        Color = "Yellow"
        Command = "cd '$projectRoot\apps\candidate-portal'; npm run dev"
    },
    @{
        Name = "ASSESSMENT"
        Title = "Assessment Engine (4001)"
        Color = "Magenta"
        Command = "cd '$projectRoot\apps\assessment-engine'; npm run dev"
    },
    @{
        Name = "EMPLOYER"
        Title = "Employer Dashboard (4002)"
        Color = "Cyan"
        Command = "cd '$projectRoot\apps\employer-dashboard'; npm run dev"
    }
)

Write-Host "============================================" -ForegroundColor White
Write-Host "  Zetheta Platform — Starting all services  " -ForegroundColor White
Write-Host "============================================" -ForegroundColor White

foreach ($svc in $services) {
    Write-Host "Starting $($svc.Name) on port $($svc.Title.Split('(')[1].Replace(')',''))..." -ForegroundColor $svc.Color
    Start-Process powershell -ArgumentList "-NoExit", "-Command", $svc.Command -WindowStyle Normal
    Start-Sleep -Milliseconds 800
}

Write-Host ""
Write-Host "All services launched in separate windows." -ForegroundColor Green
Write-Host "Close each window individually to stop a service." -ForegroundColor Gray
