// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "{{ cookiecutter.module_name }}",
    platforms: [
        .macOS(.v{{ cookiecutter.deployment_target.split('.')[0] }})
    ],
    targets: [
        .executableTarget(
            name: "{{ cookiecutter.module_name }}",
            path: "{{ cookiecutter.project_slug }}"
        )
    ]
)
