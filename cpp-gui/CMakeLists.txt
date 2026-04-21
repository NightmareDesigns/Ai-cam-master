cmake_minimum_required(VERSION 3.20)
project(AICamGUI VERSION 1.0.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_AUTOMOC ON)
set(CMAKE_AUTORCC ON)
set(CMAKE_AUTOUIC ON)

# Find Qt6 components
find_package(Qt6 REQUIRED COMPONENTS
    Core
    Gui
    Widgets
    Network
    WebSockets
    Multimedia
    MultimediaWidgets
)

# Find Python (for embedding)
find_package(Python3 REQUIRED COMPONENTS Interpreter Development)

# Source files
set(SOURCES
    src/main.cpp
    src/MainWindow.cpp
    src/CameraGridWidget.cpp
    src/LiveVideoWidget.cpp
    src/ApiClient.cpp
    src/PythonBackend.cpp
    src/StreamDecoder.cpp
    src/CameraDialog.cpp
    src/EventsTableWidget.cpp
    src/SettingsDialog.cpp
)

set(HEADERS
    include/MainWindow.h
    include/CameraGridWidget.h
    include/LiveVideoWidget.h
    include/ApiClient.h
    include/PythonBackend.h
    include/StreamDecoder.h
    include/CameraDialog.h
    include/EventsTableWidget.h
    include/SettingsDialog.h
)

set(UI_FILES
    ui/mainwindow.ui
    ui/cameradialog.ui
    ui/settingsdialog.ui
)

# Resources
set(RESOURCES
    resources/resources.qrc
)

# Include directories
include_directories(
    ${CMAKE_CURRENT_SOURCE_DIR}/include
    ${Python3_INCLUDE_DIRS}
)

# Create executable
add_executable(ai-cam-gui WIN32 MACOSX_BUNDLE
    ${SOURCES}
    ${HEADERS}
    ${UI_FILES}
    ${RESOURCES}
)

# Link libraries
target_link_libraries(ai-cam-gui PRIVATE
    Qt6::Core
    Qt6::Gui
    Qt6::Widgets
    Qt6::Network
    Qt6::WebSockets
    Qt6::Multimedia
    Qt6::MultimediaWidgets
    ${Python3_LIBRARIES}
)

# Platform-specific settings
if(WIN32)
    set_target_properties(ai-cam-gui PROPERTIES
        WIN32_EXECUTABLE TRUE
        OUTPUT_NAME "AI-Cam"
    )
    # Embed Python runtime on Windows
    target_compile_definitions(ai-cam-gui PRIVATE WINDOWS_EMBED_PYTHON)
elseif(APPLE)
    set_target_properties(ai-cam-gui PROPERTIES
        MACOSX_BUNDLE TRUE
        MACOSX_BUNDLE_INFO_PLIST ${CMAKE_CURRENT_SOURCE_DIR}/resources/Info.plist
        OUTPUT_NAME "AI-Cam"
    )
else()
    set_target_properties(ai-cam-gui PROPERTIES
        OUTPUT_NAME "ai-cam-gui"
    )
endif()

# Install target
install(TARGETS ai-cam-gui
    BUNDLE DESTINATION .
    RUNTIME DESTINATION bin
)

# Install Python backend
install(FILES ${CMAKE_CURRENT_SOURCE_DIR}/../dist/aicam-backend
    DESTINATION bin
    PERMISSIONS OWNER_EXECUTE OWNER_WRITE OWNER_READ
)

# Install resources
install(DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}/../src/static
    DESTINATION share/aicam
)
