REM This file is ran in a pre-build event when data from "Directory.Build.props" or
REM "Directory.Build.targets" is required.
REM It assumes "Directory.Build.props", "Directory.Build.targets" and "verify_props"
REM are all in the solution directory

@echo off
setlocal

set SOLUTION=%~dp0

REM Loop through each parameter provided
for %%a in (%*) do (
    
    REM Detect if the parameter is not a valid path
    if not exist "%%~a" (

        REM Raise an error for each bad path - this will prevent the build from completing.
        echo ERROR: Invalid path "%%~a" in "%SOLUTION%Directory.Build.props" or "%SOLUTION%Directory.Build.targets" 1>&2
    )
)

exit /b 0
