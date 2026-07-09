@echo off
REM Targeted PartPrimitives smoke: cottage exercises wall/roof/windows;
REM dragon exercises limb/chain composition. Human reviews screenshots.
cd /d C:\Users\Admin\bloxbench

REM Use the persistent Studio/MCP setup. Only kill stale processes when needed.
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
set MCP_BAT=%USERPROFILE%\studio-mcp.bat
set MODEL=cline-pass/deepseek-v4-flash

echo ============================================
echo SMOKE TEST: PartPrimitives, 2 targeted evals
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
  --primitives ^
  --eval-filter "VB_BUILD_001_cozy_cottage|VB_BUILD_010_dragon_statue" ^
  --startup-wait 45 --eval-timeout 600 ^
  --max-rounds 25 ^
  --max-tokens-per-eval 500000

echo ============================================
echo SMOKE TEST DONE
echo ============================================
