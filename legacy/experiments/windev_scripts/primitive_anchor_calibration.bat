@echo off
REM Zero-token PartPrimitives origin-face calibration.
REM Cleanup commands are separate so absent processes cannot abort the run.
cd /d C:\Users\Admin\bloxbench

taskkill /f /im StudioMCP.exe >nul 2>&1
taskkill /f /im RobloxStudioBeta.exe >nul 2>&1
taskkill /f /im RobloxCrashHandler.exe >nul 2>&1
ping -n 4 127.0.0.1 >nul
if exist "C:\Users\Admin\bloxbench\Places\baseplate.rbxl.lock" del /f /q "C:\Users\Admin\bloxbench\Places\baseplate.rbxl.lock" >nul 2>&1

python scripts\windev\primitive_anchor_calibration.py
