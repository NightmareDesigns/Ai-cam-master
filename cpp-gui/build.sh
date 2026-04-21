#!/bin/bash
# Quick build script for C++ GUI

set -e

echo "=== Building AI-Cam C++ GUI ==="

# Check for Qt6
if ! command -v qmake6 &> /dev/null && ! command -v qmake &> /dev/null; then
    echo "Error: Qt6 not found. Please install Qt6."
    exit 1
fi

# Create build directory
mkdir -p build
cd build

# Configure
echo "Configuring CMake..."
cmake .. -DCMAKE_BUILD_TYPE=Release

# Build
echo "Building..."
cmake --build . --config Release -j$(nproc 2>/dev/null || echo 4)

echo ""
echo "=== Build Complete ==="
echo "Executable location:"
if [ "$(uname)" == "Darwin" ]; then
    echo "  ./AI-Cam.app"
    echo ""
    echo "Run with: open ./AI-Cam.app"
else
    echo "  ./ai-cam-gui"
    echo ""
    echo "Run with: ./ai-cam-gui"
fi
