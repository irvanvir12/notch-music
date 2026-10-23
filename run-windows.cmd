@echo off
setlocal
set "NOTCH_GDK_BACKEND=win32"
set "GDK_BACKEND=win32"
if not defined MSYS2_UCRT64 set "MSYS2_UCRT64=C:\msys64\ucrt64"
if not exist "%MSYS2_UCRT64%\bin\python.exe" (
    echo Install MSYS2 UCRT64 dependencies from README.md first.
    echo Or use the portable ZIP after its Windows build has passed.
    pause
    exit /b 1
)
set "PATH=%MSYS2_UCRT64%\bin;%PATH%"
"%MSYS2_UCRT64%\bin\python.exe" "%~dp0notch_music.py" %*
