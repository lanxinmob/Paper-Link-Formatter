@echo off
setlocal

echo Automatically searching for the Python path...
for /f "delims=" %%p in ('where python') do (
    set "PYTHON_EXE_PATH=%%p"
    goto :PythonFound
)

:PythonNotFound
echo  python.exe was not found in the system. 
echo  Please ensure that Python is installed and added to the system's PATH environment variable.
pause
exit /b

:PythonFound
set "PYTHONW_EXE_PATH=%PYTHON_EXE_PATH:python.exe=pythonw.exe%"
echo Python has been found: %PYTHON_EXE_PATH%
echo.

>nul 2>&1 "%SYSTEMROOT%\system32\cacls.exe" "%SYSTEMROOT%\system32\config\system"
if '%errorlevel%' NEQ '0' (
    echo Requesting administrator privileges...
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)
echo Administrator privileges have been obtained.
echo.

cd /d "%~dp0"
echo The current working directory has been set to: %cd%
set "PROJECT_DIR=%cd%"
echo The project directory has been automatically set to: %PROJECT_DIR%
echo.

echo Checking and installing Python dependencies (from requirements.txt)...
if exist "requirements.txt" (
    "%PYTHON_EXE_PATH%" -m pip install -r requirements.txt --upgrade
    echo Dependencies installation completed.
) else (
    echo The requirements.txt file was not found.
    echo The dependency installation is skipped.
)
echo.

set "TEMP_FILE=%TEMP%\selected_path.txt"

echo.
echo Selecting Markdown Directory...
powershell -ExecutionPolicy Bypass -File ".\get-folder.ps1" -Title "Select Markdown Directory" -OutputFile "%TEMP_FILE%"

if exist "%TEMP_FILE%" (
    set /p REPO_PATH=<"%TEMP_FILE%"
    del "%TEMP_FILE%"
)
echo.
echo =================================
echo  Folders Selected:
echo =================================
echo Project Directory: [%PROJECT_DIR%]
echo Markdown Directory: [%REPO_PATH%]
echo.

rem pause

if not defined REPO_PATH (
  echo No repository directory was selected. Exiting.
  pause
  exit /b
)

echo Generating run_watcher.bat...
echo @echo off > "%PROJECT_DIR%\run_watcher.bat"
echo rem --- Auto-generated script, do not modify manually --- >> "%PROJECT_DIR%\run_watcher.bat"
echo echo --- Run at %%date%% %%time%% --- ^>^> "%PROJECT_DIR%\watcher_log.txt" >> "%PROJECT_DIR%\run_watcher.bat"
echo cd /d "%PROJECT_DIR%" >> "%PROJECT_DIR%\run_watcher.bat"
echo start "MarkdownWatcherService" "%PYTHONW_EXE_PATH%" "%PROJECT_DIR%\watcher.py" --repo "%REPO_PATH%" >> "%PROJECT_DIR%\run_watcher.bat"
echo echo --- End Run --- ^>^> "%PROJECT_DIR%\watcher_log.txt" >> "%PROJECT_DIR%\run_watcher.bat"
echo echo. ^>^> "%PROJECT_DIR%\watcher_log.txt" >> "%PROJECT_DIR%\run_watcher.bat"

echo run_watcher.bat has been successfully created.
echo.

schtasks /Create ^
  /TN "MarkdownWatcher" ^
  /TR "\"%PROJECT_DIR%\run_watcher.bat\"" ^
  /SC ONLOGON ^
  /RL HIGHEST ^
  /F

if %ERRORLEVEL% equ 0 (
    echo The startup task has been successfully created and will be executed immediately for the first time.
    call  "%PROJECT_DIR%\run_watcher.bat"
) else (
    echo The task schedule creation failed, error code:%ERRORLEVEL%
)
rem pause