# AI-Cam C++ GUI

This directory contains the C++ Qt-based desktop GUI for AI-Cam.

## Features

- **Cross-platform desktop application** (Windows, macOS, Linux)
- **Qt6-based modern UI** with dark theme
- **Live camera streaming** via WebSocket
- **Camera management** with auto-discovery
- **Event monitoring** with real-time updates
- **Embedded Python backend** for AI processing

## Building

### Requirements

- CMake 3.20+
- Qt 6.6+
- C++17 compiler (MSVC 2019+, GCC 9+, Clang 10+)
- Python 3.10+ (for backend)

### Build Instructions

#### Linux

```bash
# Install Qt6
sudo apt-get install qt6-base-dev qt6-multimedia-dev qt6-websockets-dev

# Build
cd cpp-gui
cmake -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build

# Run
./build/ai-cam-gui
```

#### Windows

```bash
# Install Qt6 from https://www.qt.io/download

# Build with Visual Studio
cd cpp-gui
cmake -B build -G "Visual Studio 17 2022" -A x64
cmake --build build --config Release

# Run
.\build\Release\AI-Cam.exe
```

#### macOS

```bash
# Install Qt6
brew install qt@6

# Build
cd cpp-gui
cmake -B build -DCMAKE_PREFIX_PATH=$(brew --prefix qt@6)
cmake --build build

# Run
open build/AI-Cam.app
```

## Architecture

The application consists of:

1. **C++ Qt GUI** - Native desktop interface
2. **Python Backend** - Embedded FastAPI server for AI processing
3. **WebSocket Streaming** - Real-time video frames
4. **REST API Client** - Communication with backend

### Components

- `MainWindow` - Main application window with camera grid and events
- `CameraGridWidget` - Dynamic grid layout for camera tiles
- `LiveVideoWidget` - Individual camera stream display with WebSocket
- `ApiClient` - REST API client for backend communication
- `PythonBackend` - Backend process manager
- `StreamDecoder` - JPEG/MJPEG frame decoder

## Packaging

The GitHub Actions workflow automatically builds executables for all platforms:

- **Windows**: `.exe` installer with NSIS
- **Linux**: AppImage
- **macOS**: `.dmg` disk image

See `.github/workflows/build-cpp-gui.yml` for build configuration.

## License

MIT License - See LICENSE file in repository root.
