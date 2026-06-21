@echo off
setlocal enabledelayedexpansion

REM Parameters: NAME SOURCE [TFM]
if "%~2" == "" (
    echo ERROR: Missing required parameters
    exit /b 1
)

REM Extract parameters and remove quotes
set "NAME=%~1"
set "SOURCE=%~2"
set "TFM=%~3"

REM Remove trailing backslash from SOURCE if applicable
if "%SOURCE:~-1%"=="\" set "SOURCE=%SOURCE:~0,-1%"

REM Resolve the built assembly
set "SRCFILE=%SOURCE%\%NAME%"
if not exist "%SRCFILE%" (
    echo ERROR: Source not found: %SRCFILE%
    exit /b 1
)

REM Route by target framework:
REM   net4x  (.NET Framework) -> Magnetar\Legacy\Local
REM   others (.NET 5+)        -> Magnetar\Interim\Local (only if Magnetar\Interim exists)
set "MAGNETAR=%AppData%\Magnetar"
set "EDITION=Interim"
echo(%TFM% | findstr /b /i "net4" >nul && set "EDITION=Legacy"
if "%TFM%"=="" set "EDITION=Legacy"

if /i "%EDITION%"=="Interim" (
    REM Only deploy the .NET build when the Interim Magnetar edition is installed
    if not exist "%MAGNETAR%\Interim" (
        echo Magnetar Interim not installed, skipping %TFM% deploy: %MAGNETAR%\Interim
        exit /b 0
    )
    set "PLUGIN_DIR=%MAGNETAR%\Interim\Local"
    if not exist "!PLUGIN_DIR!" mkdir "!PLUGIN_DIR!"
) else (
    set "PLUGIN_DIR=%MAGNETAR%\Legacy\Local"
    if not exist "!PLUGIN_DIR!" (
        echo Missing Local plugin folder: !PLUGIN_DIR!
        echo Magnetar not installed?
        exit /b 2
    )
)

REM Copy the plugin into the plugin directory, retrying if it is locked by a running server
echo Copying "%SRCFILE%" to "!PLUGIN_DIR!\"

for /l %%i in (1, 1, 10) do (
    copy /y "%SRCFILE%" "!PLUGIN_DIR!\"

    if !ERRORLEVEL! NEQ 0 (
        REM "timeout" requires input redirection which is not supported,
        REM so we use ping as a way to delay the script between retries.
        ping -n 2 127.0.0.1 >NUL 2>&1
    ) else (
        goto BREAK_LOOP
    )
)

REM This part will only be reached if the loop has been exhausted
REM Any success would skip to the BREAK_LOOP label below
echo ERROR: Could not copy "%NAME%".
exit /b 1

:BREAK_LOOP
exit /b 0
