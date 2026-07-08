@echo off
title GetAiLab - Boot Chimera
cd /d "%~dp0"
echo.
echo  GetAiLab - Igniting Chimera
echo  Keep this window open while the Commander Console runs.
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0Boot-GetAiLab-Windows.ps1" %*
exit /b %ERRORLEVEL%