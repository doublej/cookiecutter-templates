# {{ cookiecutter.project_name }}

> {{ cookiecutter.description }}

## What this is

A native C++17 Android app targeting Meta Quest 2 / 3 / 3S via OpenXR. No Java or Kotlin source — `GameActivity` is the only Android-side entry point; everything else is C++ linked through the Khronos OpenXR loader. Graphics API: `{{ cookiecutter.graphics_api }}` (OpenGL ES 3 or Vulkan). `minSdk` `{{ cookiecutter.min_sdk_version }}`, `targetSdk` `{{ cookiecutter.target_sdk_version }}`, arm64-v8a only.

## Mental model

```
app/
├── build.gradle.kts        # AGP, NDK/CMake wiring, OpenXR AAR
└── src/main/
    ├── AndroidManifest.xml # VR intent category, supported devices
    └── cpp/
        ├── CMakeLists.txt  # links openxr_loader + game-activity
        ├── main.cpp        # android_main entry
        ├── openxr_app.h
        └── openxr_app.cpp  # instance / session / event loop / render stub
build.gradle.kts            # root (plugin versions)
settings.gradle.kts         # project name, include :app
gradle.properties           # prefab=true, AndroidX flags
```

The runtime path is `Android boot → GameActivity → android_main (main.cpp) → OpenXrApp::run() → instance / session / frame loop`. `openxr_app.cpp` owns the OpenXR lifecycle; rendering hooks attach inside the frame loop.

## Invariants

- C++17, one responsibility per file, no single-letter names.
- Functions stay small (5–10 lines target, 20 max).
- Every OpenXR call is result-checked — log and bail on `XR_FAILED`. Silent failures lock up the headset.
- No allocations in the frame loop — preallocate swapchains, command buffers, and pose arrays at session start.
- Pose queries use `predictedDisplayTime` from `xrWaitFrame` — never a cached or stale timestamp.
- Stereo rendering uses multiview (texture array, `arraySize=2`).
- Fixed foveated rendering (`XR_FB_foveation`) is enabled by default with dynamic level.
- Quest devices only — `minSdk` and `targetSdk` track Meta's supported range.

## Common change patterns

- **Add a render call** → inside the frame loop in `openxr_app.cpp`, between `xrBeginFrame` and `xrEndFrame`.
- **Add an OpenXR extension** → request it at instance creation in `openxr_app.cpp`, guard usage with `xrEnumerateInstanceExtensionProperties`.
- **Switch / extend graphics API** → change `cookiecutter.graphics_api` semantics: update `CMakeLists.txt` link targets, swapchain creation, and shader path.
- **Add a dependency** → AGP module deps in `app/build.gradle.kts`; native deps via prefab packages or CMake `find_package`.

## Verification

Run `just check` after every change. It composes:

`just-fmt-check` + `loc-check` + `dir-check` + `lint` + `test` + `build`

Recipe reference:

- `just install` — install the Gradle wrapper (first run only)
- `just lint` — Android lint on the debug variant
- `just test` — unit tests
- `just build` — assemble debug APK
- `just build-release` — assemble release APK (unsigned)
- `just install-device` — `adb install` debug APK to connected Quest
- `just log` — `adb logcat` filtered to this app
- `just uninstall` — remove from device
- `just loc-check` / `just dir-check` — file-size and per-directory thresholds from `.quality.json`
- `just just-fmt-check` — verify Justfile formatting
- `just clean` — remove Gradle / build outputs
- `just update-scaffold` — pull updates from the cookiecutter template

## Related context

- [agent.md](agent.md) — verify loop, auto-fix commands, common tasks, boundaries
- `.claude/` — Claude Code settings, scaffold-update hook, library-freshness hook, diagnostic logging
- `.quality.json` — loc / dir thresholds (single source of truth)
- As this project grows, add nested `CLAUDE.md` files in high-value subfolders (`app/src/main/cpp/render/`, `app/src/main/cpp/input/`, extension wrappers, shader sources) following the `claude-md-tree` skill's context-packet pattern.
