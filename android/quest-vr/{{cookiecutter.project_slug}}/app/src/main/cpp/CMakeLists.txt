cmake_minimum_required(VERSION 3.22.1)
project({{ cookiecutter.project_slug.replace('-', '_') }} LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

if(NOT DEFINED GRAPHICS_API)
    set(GRAPHICS_API "{{ cookiecutter.graphics_api }}")
endif()

find_package(OpenXR REQUIRED CONFIG)
find_package(game-activity REQUIRED CONFIG)

add_library(${CMAKE_PROJECT_NAME} SHARED
    main.cpp
    openxr_app.cpp
)

target_include_directories(${CMAKE_PROJECT_NAME} PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}
)

target_compile_definitions(${CMAKE_PROJECT_NAME} PRIVATE
    XR_USE_PLATFORM_ANDROID=1
)

if(GRAPHICS_API STREQUAL "vulkan")
    target_compile_definitions(${CMAKE_PROJECT_NAME} PRIVATE
        XR_USE_GRAPHICS_API_VULKAN=1
    )
    target_link_libraries(${CMAKE_PROJECT_NAME} PRIVATE vulkan)
else()
    target_compile_definitions(${CMAKE_PROJECT_NAME} PRIVATE
        XR_USE_GRAPHICS_API_OPENGL_ES=1
    )
    target_link_libraries(${CMAKE_PROJECT_NAME} PRIVATE GLESv3 EGL)
endif()

target_link_libraries(${CMAKE_PROJECT_NAME} PRIVATE
    OpenXR::openxr_loader
    game-activity::game-activity_static
    android
    log
)
