#!/usr/bin/env pwsh
# Start the Videogame Semantic Search system (backend + frontend)

Write-Host "================================" -ForegroundColor Cyan
Write-Host "  Videogame Semantic Search" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan
Write-Host ""

# Save the root directory path
$ROOT_DIR = $PSScriptRoot
if ([string]::IsNullOrEmpty($ROOT_DIR)) {
    $ROOT_DIR = $PWD.Path
}

# Capture current PATH so child processes inherit it
$currentPath = $env:PATH

# Start Backend
Write-Host "🚀 Starting Backend Server..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "`$env:PATH = '$currentPath'; cd '$ROOT_DIR'; Write-Host 'Backend server starting on http://localhost:8000' -ForegroundColor Cyan; uv run uvicorn backend.main:app --reload --port 8000"
$backendStarted = $?

if ($backendStarted) {
    Write-Host "✅ Backend process launched successfully" -ForegroundColor Green
} else {
    Write-Host "❌ Failed to launch backend process" -ForegroundColor Red
}

Write-Host ""

# Wait for backend to initialize
Write-Host "⏳ Waiting for backend to initialize..." -ForegroundColor Yellow
Start-Sleep -Seconds 5

Write-Host ""

# Start Frontend
Write-Host "🌐 Starting Frontend Development Server..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "`$env:PATH = '$currentPath'; cd '$ROOT_DIR\frontend'; Write-Host 'Frontend starting on http://localhost:5173' -ForegroundColor Cyan; bun run dev"
$frontendStarted = $?

if ($frontendStarted) {
    Write-Host "✅ Frontend process launched successfully" -ForegroundColor Green
} else {
    Write-Host "❌ Failed to launch frontend process" -ForegroundColor Red
}

Write-Host ""
Write-Host "================================" -ForegroundColor Cyan
Write-Host "  System is starting up!" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Backend:  http://localhost:8000" -ForegroundColor White
Write-Host "  Frontend: http://localhost:5173" -ForegroundColor White
Write-Host "  API Docs: http://localhost:8000/docs" -ForegroundColor White
Write-Host ""
Write-Host "Startup completed" -ForegroundColor Green
