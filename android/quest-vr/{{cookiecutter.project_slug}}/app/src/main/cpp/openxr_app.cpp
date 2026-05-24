// Minimal OpenXR shell for Quest. Creates instance + system, runs the event
// loop, and cleans up on destroy. Rendering (swapchain, projection layers) is
// intentionally stubbed — extend render_frame() to draw your scene.

#include "openxr_app.h"

#include <android/log.h>
#include <openxr/openxr.h>
#include <openxr/openxr_platform.h>

#include <cstring>

#define LOG_TAG "{{ cookiecutter.project_slug }}"
#define LOGI(...) __android_log_print(ANDROID_LOG_INFO, LOG_TAG, __VA_ARGS__)
#define LOGE(...) __android_log_print(ANDROID_LOG_ERROR, LOG_TAG, __VA_ARGS__)

namespace {{ cookiecutter.module_name.lower() }} {

namespace {

struct AppState {
    XrInstance instance = XR_NULL_HANDLE;
    XrSystemId system = XR_NULL_SYSTEM_ID;
    XrSession session = XR_NULL_HANDLE;
    XrSessionState session_state = XR_SESSION_STATE_UNKNOWN;
    bool running = false;
};

bool init_loader(android_app* app) {
    PFN_xrInitializeLoaderKHR init_loader_fn = nullptr;
    XrResult res = xrGetInstanceProcAddr(
        XR_NULL_HANDLE,
        "xrInitializeLoaderKHR",
        reinterpret_cast<PFN_xrVoidFunction*>(&init_loader_fn));
    if (XR_FAILED(res) || !init_loader_fn) {
        LOGE("xrInitializeLoaderKHR not available");
        return false;
    }
    XrLoaderInitInfoAndroidKHR info = {XR_TYPE_LOADER_INIT_INFO_ANDROID_KHR};
    info.applicationVM = app->activity->vm;
    info.applicationContext = app->activity->javaGameActivity;
    return XR_SUCCEEDED(init_loader_fn(reinterpret_cast<XrLoaderInitInfoBaseHeaderKHR*>(&info)));
}

bool create_instance(AppState& state) {
    const char* extensions[] = {
        XR_KHR_ANDROID_CREATE_INSTANCE_EXTENSION_NAME,
#if defined(XR_USE_GRAPHICS_API_VULKAN)
        XR_KHR_VULKAN_ENABLE2_EXTENSION_NAME,
#else
        XR_KHR_OPENGL_ES_ENABLE_EXTENSION_NAME,
#endif
    };
    XrInstanceCreateInfo ci = {XR_TYPE_INSTANCE_CREATE_INFO};
    ci.enabledExtensionCount = sizeof(extensions) / sizeof(extensions[0]);
    ci.enabledExtensionNames = extensions;
    std::strcpy(ci.applicationInfo.applicationName, "{{ cookiecutter.project_name }}");
    ci.applicationInfo.applicationVersion = 1;
    std::strcpy(ci.applicationInfo.engineName, "{{ cookiecutter.module_name }}");
    ci.applicationInfo.engineVersion = 1;
    ci.applicationInfo.apiVersion = XR_CURRENT_API_VERSION;
    XrResult res = xrCreateInstance(&ci, &state.instance);
    if (XR_FAILED(res)) {
        LOGE("xrCreateInstance failed: %d", res);
        return false;
    }
    return true;
}

bool get_system(AppState& state) {
    XrSystemGetInfo info = {XR_TYPE_SYSTEM_GET_INFO};
    info.formFactor = XR_FORM_FACTOR_HEAD_MOUNTED_DISPLAY;
    XrResult res = xrGetSystem(state.instance, &info, &state.system);
    if (XR_FAILED(res)) {
        LOGE("xrGetSystem failed: %d", res);
        return false;
    }
    return true;
}

void poll_events(AppState& state) {
    XrEventDataBuffer event = {XR_TYPE_EVENT_DATA_BUFFER};
    while (xrPollEvent(state.instance, &event) == XR_SUCCESS) {
        if (event.type == XR_TYPE_EVENT_DATA_SESSION_STATE_CHANGED) {
            auto* e = reinterpret_cast<XrEventDataSessionStateChanged*>(&event);
            state.session_state = e->state;
            LOGI("session state: %d", e->state);
        }
        event.type = XR_TYPE_EVENT_DATA_BUFFER;
    }
}

void render_frame(AppState& /*state*/) {
    // TODO: xrWaitFrame -> xrBeginFrame -> acquire/wait/release swapchain
    // -> xrEndFrame. See references/quest-android-vr-client for the full
    // frame loop contract.
}

void shutdown(AppState& state) {
    if (state.session != XR_NULL_HANDLE) {
        xrDestroySession(state.session);
    }
    if (state.instance != XR_NULL_HANDLE) {
        xrDestroyInstance(state.instance);
    }
}

}  // namespace

void run_app(android_app* app) {
    LOGI("starting {{ cookiecutter.project_slug }}");

    if (!init_loader(app)) {
        return;
    }

    AppState state;
    if (!create_instance(state) || !get_system(state)) {
        shutdown(state);
        return;
    }

    state.running = true;
    while (state.running && !app->destroyRequested) {
        int events = 0;
        android_poll_source* source = nullptr;
        while (ALooper_pollAll(0, nullptr, &events, reinterpret_cast<void**>(&source)) >= 0) {
            if (source != nullptr) {
                source->process(app, source);
            }
        }
        poll_events(state);
        render_frame(state);
    }

    shutdown(state);
    LOGI("exiting {{ cookiecutter.project_slug }}");
}

}  // namespace {{ cookiecutter.module_name.lower() }}
