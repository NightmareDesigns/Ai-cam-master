@echo off
REM Quick build script for C++ GUI on Windows

echo === Building AI-Cam C++ GUI ===

REM Check for CMake
where cmake >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo Error: CMake not found. Please install CMake.
    exit /b 1
)

REM Create build directory
if not exist build mkdir build
cd build

REM Configure
echo Configuring CMake...
cmake .. -G "Visual Studio 17 2022" -A x64

REM Build
echo Building...
cmake --build . --config Release

echo.
echo === Build Complete ===
echo Executable location:
echo   .\Release\AI-Cam.exe
echo.
echo Run with: .\Release\AI-Cam.exe
