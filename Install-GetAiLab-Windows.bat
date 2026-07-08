@echo off
title GetAiLab - Windows Setup
cd /d "%~dp0"
echo.
echo  GetAiLab Windows Setup
echo  If Windows asks about permissions, choose Allow.
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0Install-GetAiLab-Windows.ps1" %*
exit /b %ERRORLEVEL%