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
        }
        .padding()
    }
}
