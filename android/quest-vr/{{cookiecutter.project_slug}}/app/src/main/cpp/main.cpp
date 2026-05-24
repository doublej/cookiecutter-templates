// Native entry point for {{ cookiecutter.project_name }}.
// GameActivity invokes android_main on its own thread; we hand off to run_app.

#include <game-activity/native_app_glue/android_native_app_glue.h>

#include "openxr_app.h"

extern "C" void android_main(android_app* app) {
    {{ cookiecutter.module_name.lower() }}::run_app(app);
}
