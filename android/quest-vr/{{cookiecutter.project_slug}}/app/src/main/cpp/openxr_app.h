#pragma once

#include <game-activity/native_app_glue/android_native_app_glue.h>

namespace {{ cookiecutter.module_name.lower() }} {

// Run the OpenXR app until the native app loop signals destruction.
void run_app(android_app* app);

}  // namespace {{ cookiecutter.module_name.lower() }}
