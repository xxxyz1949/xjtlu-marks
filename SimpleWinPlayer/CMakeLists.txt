cmake_minimum_required(VERSION 3.26)
project(SimpleWinPlayer LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# Use vcpkg toolchain externally via -DCMAKE_TOOLCHAIN_FILE
# Require static where possible

find_package(Qt6 6.7 REQUIRED COMPONENTS Gui Quick Qml QuickControls2)
find_package(unofficial-ffmpeg CONFIG REQUIRED)

# D3D11
set(D3D_LIBS d3d11 dxgi dxguid d3dcompiler)

qt_standard_project_setup()

qt_add_qml_module(simplewinplayer
    URI SimpleWinPlayer
    VERSION 1.0
    QML_FILES
        ui/main.qml
        ui/Controls.qml
        ui/SettingsPanel.qml
)

add_executable(SimpleWinPlayer
    src/main.cpp
    src/Core/VideoPlayer.cpp
    src/Core/VideoPlayer.h
    src/Render/D3D11Renderer.cpp
    src/Render/D3D11Renderer.h
    shaders/PixelShader.hlsl
)

target_include_directories(SimpleWinPlayer PRIVATE src)

target_link_libraries(SimpleWinPlayer PRIVATE
    Qt6::Gui
    Qt6::Quick
    Qt6::Qml
    Qt6::QuickControls2
    unofficial::ffmpeg::avcodec
    unofficial::ffmpeg::avformat
    unofficial::ffmpeg::avutil
    unofficial::ffmpeg::swresample
    unofficial::ffmpeg::swscale
    ${D3D_LIBS}
)

if(MSVC)
    target_compile_definitions(SimpleWinPlayer PRIVATE _CRT_SECURE_NO_WARNINGS NOMINMAX)
endif()

# Embed shader path for runtime
configure_file(${CMAKE_CURRENT_SOURCE_DIR}/shaders/PixelShader.hlsl
               ${CMAKE_CURRENT_BINARY_DIR}/PixelShader.hlsl COPYONLY)
