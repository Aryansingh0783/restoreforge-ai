@echo off
setlocal EnableExtensions
title RestoreForge AI
cd /d "%~dp0"

rem ===========================================================================
rem  RestoreForge AI - double-click this file to open the app.
rem  KEEP WINDOWS (CRLF) LINE ENDINGS - cmd.exe finds labels by byte offset,
rem  and in an LF-only file a GOTO can fail and close the window with no
rem  message at all.
rem ===========================================================================

rem The GUI runs on the SYSTEM Python because it must work before the venv
rem exists (it is what installs it). Only tkinter is required.
set "SYSPY="
for %%P in ("py -3.11" "py -3" "python") do (
    if not defined SYSPY (
        %%~P -c "import tkinter" >nul 2>&1 && set "SYSPY=%%~P"
    )
)

if not defined SYSPY goto NOPYTHON

%SYSPY% "%~dp0gui.py"
if errorlevel 1 goto CRASHED
exit /b 0

:NOPYTHON
echo.
echo   ############################################################
echo   RestoreForge AI needs Python 3.11 with tkinter.
echo.
echo   Install it, then double-click this file again:
echo       winget install Python.Python.3.11
echo.
echo   During installation make sure "tcl/tk and IDLE" stays ticked.
echo   ############################################################
echo.
pause
exit /b 1

:CRASHED
echo.
echo   ############################################################
echo   The app closed unexpectedly. The error is printed above.
echo   ############################################################
echo.
pause
exit /b 1
