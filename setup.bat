@echo off
echo ============================================
echo   Videogame Semantic Search - Setup
echo ============================================
echo.

REM Check uv
uv --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] uv non trovato. Installa uv (https://docs.astral.sh/uv/) e riprova.
    exit /b 1
)

REM Check Node
node --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Node.js non trovato. Installa Node.js 18+ e riprova.
    exit /b 1
)

echo [1/4] Installazione dipendenze Python con uv...
uv sync

echo.
echo [2/4] Installazione dipendenze frontend...
cd frontend
call bun install
cd ..

echo.
echo [3/3] Popolazione ontologia da Wikidata...
echo        (questo puo' richiedere alcuni minuti)
cd ontology
uv run python populate_wikidata.py
cd ..

echo.
echo ============================================
echo   Setup completato!
echo ============================================
echo.
echo Per avviare il progetto (dalla ROOT del progetto):
echo   1. Crea un file .env con OPENAI_API_KEY=sk-...
echo   2. Backend:  uv run uvicorn backend.main:app --reload --port 8000
echo   3. Frontend: cd frontend ^& bun run dev
echo   4. Apri http://localhost:5173
echo.
