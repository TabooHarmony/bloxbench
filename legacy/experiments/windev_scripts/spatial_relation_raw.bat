@echo off
REM Raw control arm for the matched spatial-relation pilot.
cd /d C:\Users\Admin\bloxbench

taskkill /f /im StudioMCP.exe >nul 2>&1
taskkill /f /im RobloxStudioBeta.exe >nul 2>&1
taskkill /f /im RobloxCrashHandler.exe >nul 2>&1
ping -n 4 127.0.0.1 >nul

set "STUDIO_EXE="
for /f "delims=" %%i in ('dir /b /ad /o-n "%LOCALAPPDATA%\Roblox\Versions\version-*"') do if not defined STUDIO_EXE if exist "%LOCALAPPDATA%\Roblox\Versions\%%i\RobloxStudioBeta.exe" set "STUDIO_EXE=%LOCALAPPDATA%\Roblox\Versions\%%i\RobloxStudioBeta.exe"
if not defined STUDIO_EXE exit /b 1
set "MCP_BAT=%USERPROFILE%\studio-mcp.bat"
if not exist "%MCP_BAT%" exit /b 2

python harness.py ^
  --evals-dir Evals\Building ^
  --places-dir Places ^
  --studio-exe "%STUDIO_EXE%" ^
  --mcp-bat "%MCP_BAT%" ^
  --model-name "cline-pass/deepseek-v4-flash" ^
  --output-dir results ^
  --screenshots ^
  --existing-scene ^
  --eval-filter "VB_REPAIR_001_watchtower|VB_REPAIR_003_roof_and_flag" ^
  --startup-wait 45 --eval-timeout 600 ^
  --max-rounds 12 ^
  --max-tokens-per-eval 250000
set "RUN_RC=%ERRORLEVEL%"

taskkill /f /im StudioMCP.exe >nul 2>&1
taskkill /f /im RobloxStudioBeta.exe >nul 2>&1
taskkill /f /im RobloxCrashHandler.exe >nul 2>&1
exit /b %RUN_RC%
