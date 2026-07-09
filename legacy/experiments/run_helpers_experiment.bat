@echo off
REM BloxBench — Helpers v2 experiment: vanilla vs helpers on loose Building set
REM Both runs use --no-gate (human is the judge).
REM Run from C:\Users\Admin\bloxbench

cd /d C:\Users\Admin\bloxbench

REM === PRE-RUN STUDIO CLEANUP ===
echo ============================================
echo PRE-RUN: killing any stale Roblox/Studio processes
echo ============================================
taskkill /f /im StudioMCP.exe >nul 2>&1
taskkill /f /im RobloxStudioBeta.exe >nul 2>&1
taskkill /f /im RobloxCrashHandler.exe >nul 2>&1
taskkill /f /im RobloxStudioInstaller.exe >nul 2>&1

set _waited=0
:waitloop
tasklist /fi "imagename eq RobloxStudioBeta.exe" 2>nul | find /i "RobloxStudioBeta.exe" >nul
if errorlevel 1 goto cleaned
if %_waited% geq 15 goto cleaned
timeout /t 1 >nul
set /a _waited+=1
goto waitloop
:cleaned

if exist "C:\Users\Admin\bloxbench\Places\baseplate.rbxl.lock" del /f /q "C:\Users\Admin\bloxbench\Places\baseplate.rbxl.lock" >nul 2>&1
echo PRE-RUN cleanup done.

set STUDIO_EXE=C:\Program Files (x86)\Roblox\Versions\version-8b44d8f2067642d8\RobloxStudioBeta.exe
set MCP_BAT=C:\Users\Admin\studio-mcp.bat
set MODEL=cline-pass/deepseek-v4-flash

echo ============================================
echo RUN 1/2: VANILLA (no gate, no helpers)
echo ============================================
python harness.py ^
  --evals-dir Evals\Building ^
  --places-dir Places ^
  --studio-exe "%STUDIO_EXE%" ^
  --mcp-bat "%MCP_BAT%" ^
  --model-name "%MODEL%" ^
  --output-dir results ^
  --screenshots ^
  --no-gate ^
  --startup-wait 45 --eval-timeout 600 ^
  --max-rounds 25

echo ============================================
echo RUN 2/2: HELPERS v2 (no gate, spatial helpers)
echo ============================================
python harness.py ^
  --evals-dir Evals\Building ^
  --places-dir Places ^
  --studio-exe "%STUDIO_EXE%" ^
  --mcp-bat "%MCP_BAT%" ^
  --model-name "%MODEL%" ^
  --output-dir results ^
  --screenshots ^
  --no-gate ^
  --helpers ^
  --startup-wait 45 --eval-timeout 600 ^
  --max-rounds 25

echo ============================================
echo HELPERS v2 EXPERIMENT COMPLETE
echo ============================================
dir /b results\
