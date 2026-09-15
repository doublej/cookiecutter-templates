import AppKit

/// Bringing this app to the front — the one macOS behaviour that bites every menubar app.
///
/// macOS 14 made activation *cooperative*: `NSApplication.activate()` only works if the
/// currently-active app yielded to us, and `NSApplication.h` says so outright — "no
/// guarantee that the app will be activated at all". Nothing yields to a background or
/// `.accessory` (`LSUIElement`) app, so `NSApp.activate()` is a silent no-op: the window is
/// created and ordered front *within your app*, your app stays behind, and the user sees
/// nothing happen until they hit Exposé and find the window buried.
///
/// Measured on macOS 26 (accessory app, another app frontmost, repeated runs):
///
/// | call                                                | fronts? |
/// |-----------------------------------------------------|---------|
/// | `makeKeyAndOrderFront` alone                         | no      |
/// | `NSApp.activate()`                                   | no      |
/// | `NSApp.activate(ignoringOtherApps: true)`            | yes     |
/// | `NSWorkspace.openApplication(self, activates: true)` | yes     |
///
/// So: take the fast path, then verify and escalate. `ignoringOtherApps:` is marked
/// `API_TO_BE_DEPRECATED`, which is why the LaunchServices path — the same request `open -a`
/// makes, and it reuses the running instance rather than spawning one — backs it up.
///
/// `.swiftlint.yml` carries a `bare_nsapp_activate` rule so the broken call cannot come back.
enum AppActivation {
    /// Make this app frontmost. Call it right after `openWindow(id:)`; `openWindow` already
    /// orders the window front *within* the app, so fronting the app is the missing half.
    static func front() {
        NSApp.activate(ignoringOtherApps: true)
        DispatchQueue.main.async {
            guard !isFrontmost else { return }
            let config = NSWorkspace.OpenConfiguration()
            config.activates = true
            NSWorkspace.shared.openApplication(at: Bundle.main.bundleURL, configuration: config)
        }
    }

    private static var isFrontmost: Bool {
        NSWorkspace.shared.frontmostApplication?.bundleIdentifier == Bundle.main.bundleIdentifier
    }
}
