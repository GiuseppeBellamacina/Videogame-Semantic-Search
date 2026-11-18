@echo off
REM Usa "setup.bat -Force" per rigenerare l'ontologia anche se esiste già
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup.ps1" %*
