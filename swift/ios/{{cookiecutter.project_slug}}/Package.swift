// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "{{ cookiecutter.project_slug }}",
    platforms: [
        .iOS(.v{{ cookiecutter.deployment_target.split('.')[0] }})
    ],
    targets: [
        .executableTarget(
            name: "{{ cookiecutter.project_slug }}",
            path: "{{ cookiecutter.project_slug }}"
        )
    ]
)
