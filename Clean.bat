@echo off

del /s /f /q ClientPlugin\bin >NUL 2>&1
del /s /f /q ClientPlugin\obj >NUL 2>&1

del /s /f /q ServerPlugin\bin >NUL 2>&1
del /s /f /q ServerPlugin\obj >NUL 2>&1

del /s /f /q IngameApiTest\bin >NUL 2>&1
del /s /f /q IngameApiTest\obj >NUL 2>&1

del /s /f /q ModApiTest\bin >NUL 2>&1
del /s /f /q ModApiTest\obj >NUL 2>&1
