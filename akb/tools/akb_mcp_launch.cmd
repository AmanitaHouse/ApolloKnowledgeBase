@echo off
setlocal EnableExtensions
REM Cursor stdio entry on Windows. cmd.exe resolves the Python app-execution
REM alias; a direct CreateProcess of WindowsApps\python.exe often breaks pipes.
set "SCRIPT=%~dp0akb_mcp_server.py"
if not "%AKB_PYTHON%"=="" (
  "%AKB_PYTHON%" -u "%SCRIPT%"
  exit /b %ERRORLEVEL%
)
python -u "%SCRIPT%"
exit /b %ERRORLEVEL%
