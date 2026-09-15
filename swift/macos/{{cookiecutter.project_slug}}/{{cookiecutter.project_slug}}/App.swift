import SwiftUI

@main
struct {{ cookiecutter.module_name }}App: App {
    var body: some Scene {
        WindowGroup {
            ContentView()
        }
    }
}

struct ContentView: View {
    var body: some View {
        VStack {
            Text("{{ cookiecutter.project_name }}")
                .font(.largeTitle)
            Text("{{ cookiecutter.description }}")
                .foregroundStyle(.secondary)
            Text(String(localized: "welcome", bundle: L10n.bundle))
            Text(String(format: String(localized: "edit_hint", bundle: L10n.bundle), "App.swift"))
        }
        .padding()
    }
}
