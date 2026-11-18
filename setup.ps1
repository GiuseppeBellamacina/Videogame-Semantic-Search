param([switch]$Force)  # -Force: rigenera l'ontologia anche se esiste già

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

foreach ($cmd in "uv", "bun") {
    if (-not (Get-Command $cmd -ErrorAction SilentlyContinue)) {
        Write-Host "[ERROR] $cmd non trovato. Installalo e riprova." -ForegroundColor Red
        exit 1
    }
}

Write-Host "[1/3] Dipendenze Python (uv sync)..."
uv sync

Write-Host "[2/3] Dipendenze frontend (bun install)..."
Push-Location frontend
bun install
Pop-Location

Write-Host "[3/3] Ontologia (fetch + reasoning + scrittura; salta se già presente)..."
$extra = if ($Force) { @("--force") } else { @() }
uv run python ontology/build_ontology.py @extra

Write-Host ""
Write-Host "Setup completato. Crea il file .env (vedi .env.example) e avvia con ./start.ps1"
