@echo off
REM Relation context plus structured pre-edit commitment arm.
cd /d C:\Users\Admin\bloxbench
set "STUDIO_EXE="
for /d %%D in ("%LOCALAPPDATA%\Roblox\Versions\version-*") do if exist "%%D\RobloxStudioBeta.exe" set "STUDIO_EXE=%%D\RobloxStudioBeta.exe"
if "%STUDIO_EXE%"=="" (
    echo STUDIO_NOT_FOUND
    exit /b 2
)

set "MCP_BAT=%USERPROFILE%\studio-mcp.bat"
if not exist "%MCP_BAT%" (
    echo MCP_NOT_FOUND: %MCP_BAT%
    exit /b 2
)
set COMMON=--evals-dir Evals\Building --places-dir Places --mcp-bat "%MCP_BAT%" --studio-exe "%STUDIO_EXE%" --model-name cline-pass/deepseek-v4-flash --eval-filter "VB_REPAIR_001_watchtower|VB_REPAIR_003_roof_and_flag" --existing-scene --screenshots --max-rounds 12 --max-tokens-per-eval 250000 --startup-wait 45 --output-dir results

call python harness.py %COMMON% --relation-context-dir research\spatial_behavior\relation_contexts --relation-commitment-dir research\spatial_behavior\relation_commitments
set "RC=%ERRORLEVEL%"
taskkill /f /im StudioMCP.exe >nul 2>&1
taskkill /f /im RobloxStudioBeta.exe >nul 2>&1
taskkill /f /im RobloxCrashHandler.exe >nul 2>&1
exit /b %RC%
