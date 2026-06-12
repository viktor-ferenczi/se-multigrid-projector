@echo off
setlocal enabledelayedexpansion

REM Check if the required parameters are passed (NAME and SOURCE)
if "%~2" == "" (
    echo ERROR: Missing required parameters
    exit /b 1
)

REM Extract parameters and remove quotes
set NAME=%~1
set SOURCE=%~2

REM Resolve source file:
REM - If "%SOURCE%\%NAME%" exists, use that
REM - Else if "%SOURCE%" exists and is a file, use it
REM - Else fail
set "SRCFILE="
if exist "%SOURCE%\%NAME%" (
    set "SRCFILE=%SOURCE%\%NAME%"
) else if exist "%SOURCE%" (
    set "SRCFILE=%SOURCE%"
) else (
    echo ERROR: Source not found: %SOURCE% or %SOURCE%\%NAME%
    exit /b 1
)

REM Remove trailing backslash if applicable
if "%NAME:~-1%"=="\" set NAME=%NAME:~0,-1%
if "%SOURCE:~-1%"=="\" set SOURCE=%SOURCE:~0,-1%

REM Verify Magnetar deployment
set MAGNETAR_DIR=%AppData%\Magnetar\Legacy
if not exist "%MAGNETAR_DIR%" (
    echo "Missing Magnetar folder: %MAGNETAR_DIR%"
    echo "Magnetar not installed?"
    exit /b 2
)

REM Deploy into both the Local and Interim plugin folders
call :DEPLOY "%MAGNETAR_DIR%\Local" || exit /b 1
call :DEPLOY "%MAGNETAR_DIR%\Interim" || exit /b 1
exit /b 0

:DEPLOY
set "PLUGIN_DIR=%~1"
if not exist "%PLUGIN_DIR%" mkdir "%PLUGIN_DIR%" >NUL 2>&1

echo Copying "%SRCFILE%" to "%PLUGIN_DIR%\"
for /l %%i in (1, 1, 10) do (
    copy /y "%SRCFILE%" "%PLUGIN_DIR%\"

    if !ERRORLEVEL! NEQ 0 (
        REM "timeout" requires input redirection which is not supported,
        REM so we use ping as a way to delay the script between retries.
        ping -n 2 127.0.0.1 >NUL 2>&1
    ) else (
        exit /b 0
    )
)

REM This part will only be reached if the loop has been exhausted
echo ERROR: Could not copy "%NAME%".
exit /b 1
