# {{ cookiecutter.project_name }}

> {{ cookiecutter.description }}

## Stack

- Native C++17 Android app (NDK), OpenXR via Khronos loader
- Graphics API: {{ cookiecutter.graphics_api }}
- AGP 8.13.2 / Gradle 8.14.3 (wrapper checked in) + CMake + GameActivity
- Target: Quest 2 / Quest 3 / Quest 3S (arm64-v8a)

## Commands

Use `just` as the task runner:

- `just check` — run all checks (just-fmt-check + loc-check + dir-check + lint + test + build)
- `just install` — download the Gradle distribution (first run only)
- `just lint` — Android lint
- `just test` — run JVM unit tests
- `just build` — assembleDebug APK
- `just build-release` — assembleRelease APK
- `just install-device` — deploy to connected Quest via adb
- `just log` — tail filtered logcat
- `just uninstall` — remove from device
- `just loc-check` — check file lengths (thresholds in `.quality.json`)
- `just dir-check` — check files per directory (thresholds in `.quality.json`)
- `just just-fmt-check` — verify Justfile formatting
- `just clean` — remove Gradle/build outputs
- `just update-scaffold` — pull updates from the cookiecutter template

## Project Structure

```
app/
├── build.gradle.kts
└── src/main/
    ├── AndroidManifest.xml
    └── cpp/
        ├── CMakeLists.txt
        ├── main.cpp
        ├── openxr_app.h
        └── openxr_app.cpp
build.gradle.kts
settings.gradle.kts
Justfile
```

## Conventions

- C++17 everywhere, one module per file
- Keep functions small (5–10 lines target, 20 max)
- Check every OpenXR return code, log and bail on failure
- Allocate at session start, NEVER in the frame loop
- Pose queries must use `predictedDisplayTime` from `xrWaitFrame`
- Use multiview + FFR — do not submit multi-pass stereo

## Agent

### Verify Loop

Run after every change: `just check`

Runs: just-fmt-check + loc-check + dir-check + lint + test + build.

Step-by-step alternative:

1. `just lint` — Android lint must pass
2. `just test` — JVM unit tests
3. `just build` — must compile
4. If manifest or build.gradle changed: also `just install-device` on a connected Quest

### Delegating verification

Don't block on `just check` while a feature is still in progress — hand it to the
`verify-runner` subagent and keep building. It applies safe auto-fixes itself and writes
anything it can't safely resolve to `.claude/tickets/` instead of stopping you. Read
`.claude/tickets/` before treating a feature as done, and delete a ticket once you've
confirmed its issue is fixed.

### Auto-fixable

- Clang-format (if `.clang-format` exists): `clang-format -i app/src/main/cpp/**/*.cpp`
- Gradle caches: `just clean` if build goes weird after dependency changes

### Common Tasks

- Add a C++ module: create `foo.h` + `foo.cpp` under `app/src/main/cpp/`, add both to `CMakeLists.txt` `add_library` source list
- Enable an OpenXR extension: add to `extensions[]` in `create_instance()`, guard with `#if defined(...)` if optional, check for support via `xrEnumerateInstanceExtensionProperties`
- Add a Gradle dependency: edit `app/build.gradle.kts`, then `just clean && just build`
- Lower CPU/GPU level: use `XR_EXT_performance_settings` — do not pin to `BOOST`
- Increase render detail: raise the swapchain size toward `recommendedImageRectWidth/Height` only

### Testing

- Unit tests: `just test` (JVM tests only — C++ is tested on-device)
- On-device smoke: `just install-device && just log` and look for session state transitions
- Profiling: OVR Metrics Tool / RenderDoc-Quest / Meta Performance HUD (`adb shell setprop debug.oculus.openxr.hud 1`)

### Boundaries

- Do not bump `compileSdk`, `minSdk`, or the NDK version without asking
- Do not publish, upload to the Horizon Store, or sign release builds
- Do not add `BOOST` performance level as a sustained setting
- Do not check in `gradle-wrapper.jar` edits or generated `.cxx/` outputs
- Do not skip `xrWaitFrame` — frame pacing contract is non-negotiable
