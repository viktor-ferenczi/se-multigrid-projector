@echo off

del /s /f /q ClientPlugin\bin >NUL 2>&1
del /s /f /q ClientPlugin\obj >NUL 2>&1

del /s /f /q DedicatedPlugin\bin >NUL 2>&1
del /s /f /q DedicatedPlugin\obj >NUL 2>&1

del /s /f /q TorchPlugin\bin >NUL 2>&1
del /s /f /q TorchPlugin\obj >NUL 2>&1
