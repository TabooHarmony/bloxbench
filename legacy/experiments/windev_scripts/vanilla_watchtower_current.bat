@echo off
REM Current same-cap vanilla control for compile-once watchtower.
cd /d C:\Users\Admin\bloxbench

taskkill /f /im StudioMCP.exe >nul 2>&1
taskkill /f /im RobloxStudioBeta.exe >nul 2>&1
taskkill /f /im RobloxCrashHandler.exe >nul 2>&1
ping -n 4 127.0.0.1 >nul
if exist "C:\Users\Admin\bloxbench\Places\baseplate.rbxl.lock" del /f /q "C:\Users\Admin\bloxbench\Places\baseplate.rbxl.lock" >nul 2>&1

set "STUDIO_EXE="
for /f "delims=" %%i in ('dir /b /ad /o-n "%LOCALAPPDATA%\Roblox\Versions\version-*"') do if not defined STUDIO_EXE if exist "%LOCALAPPDATA%\Roblox\Versions\%%i\RobloxStudioBeta.exe" set "STUDIO_EXE=%LOCALAPPDATA%\Roblox\Versions\%%i\RobloxStudioBeta.exe"
if not defined STUDIO_EXE (
  echo ERROR: RobloxStudioBeta.exe not found under %LOCALAPPDATA%\Roblox\Versions
  exit /b 1
)
set "MCP_BAT=%USERPROFILE%\studio-mcp.bat"
set "MODEL=cline-pass/deepseek-v4-flash"

python harness.py ^
  --evals-dir Evals\Building ^
  --places-dir Places ^
  --model-name "%MODEL%" ^
  --studio-exe "%STUDIO_EXE%" ^
  --mcp-bat "%MCP_BAT%" ^
  --existing-scene ^
  --eval-filter "VB_REPAIR_001_watchtower" ^
  --max-rounds 10 ^
  --max-tokens-per-eval 220000 ^
  --no-gate ^
  --screenshots ^
  --output-dir results
