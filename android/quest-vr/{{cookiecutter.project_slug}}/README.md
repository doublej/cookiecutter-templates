# {{ cookiecutter.project_name }}

{{ cookiecutter.description }}

Author: {{ cookiecutter.author }}

## Requirements

- Android SDK with platform {{ cookiecutter.target_sdk_version }}
- Android NDK 28.2+ (28.2.13676358 recommended)
- CMake 3.22.1+
- Gradle 8.14.3 (wrapper is checked in; `just install` warms it up)
- JDK 17
- A Quest 2, Quest 3, or Quest 3S in developer mode

## Getting Started

```bash
just install        # download the gradle distribution (first run only)
just build          # assembleDebug APK
just install-device # adb install to connected Quest
just log            # tail logcat for this app
```

## Stack

- Native C++17 via NDK (no Java/Kotlin source)
- OpenXR via Khronos loader (prefab AAR)
- Graphics API: **{{ cookiecutter.graphics_api }}** (OpenGL ES 3 or Vulkan)
- GameActivity native entry point

## Common Commands

| Command | Description |
|---------|-------------|
| `just build` | assembleDebug APK |
| `just build-release` | assembleRelease APK (unsigned) |
| `just install-device` | Deploy debug build to connected Quest |
| `just log` | Filtered `adb logcat` |
| `just uninstall` | Remove from device |
| `just clean` | Remove Gradle / CMake outputs |
| `just check` | loc + dir + lint + build |

## Project Structure

```
app/
├── build.gradle.kts
└── src/main/
    ├── AndroidManifest.xml
    └── cpp/
        ├── CMakeLists.txt
        ├── main.cpp         # android_main entry
        ├── openxr_app.h
        └── openxr_app.cpp   # OpenXR instance/session + event loop
build.gradle.kts             # root plugin versions
settings.gradle.kts
gradle/wrapper/              # checked-in Gradle 8.14.3 wrapper
```

## Next Steps

The generated scaffold initializes an OpenXR instance and runs the lifecycle
event loop. To render something visible, extend `render_frame()` in
`app/src/main/cpp/openxr_app.cpp` to:

1. Create a graphics binding (GL ES or Vulkan) and pass it to `xrCreateSession`
2. Enumerate view configurations and create a stereo swapchain (`arraySize = 2`)
3. Implement the frame loop: `xrWaitFrame` → `xrBeginFrame` → draw → `xrEndFrame`
4. Submit an `XrCompositionLayerProjection` for the two eyes
