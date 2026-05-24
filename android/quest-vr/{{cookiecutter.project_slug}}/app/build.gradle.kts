plugins {
    id("com.android.application")
}

android {
    namespace = "{{ cookiecutter.package_id }}"
    compileSdk = 34
    ndkVersion = "26.1.10909125"

    defaultConfig {
        applicationId = "{{ cookiecutter.package_id }}"
        minSdk = {{ cookiecutter.min_sdk_version }}
        targetSdk = {{ cookiecutter.target_sdk_version }}
        versionCode = 1
        versionName = "0.1.0"

        ndk {
            abiFilters += "arm64-v8a"
        }

        externalNativeBuild {
            cmake {
                arguments += listOf(
                    "-DANDROID_STL=c++_shared",
                    "-DANDROID_PLATFORM=android-{{ cookiecutter.min_sdk_version }}",
                    "-DGRAPHICS_API={{ cookiecutter.graphics_api }}"
                )
                cppFlags += "-std=c++17"
            }
        }
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            proguardFiles(getDefaultProguardFile("proguard-android-optimize.txt"), "proguard-rules.pro")
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    externalNativeBuild {
        cmake {
            path = file("src/main/cpp/CMakeLists.txt")
            version = "3.22.1"
        }
    }

    buildFeatures {
        prefab = true
    }
}

dependencies {
    implementation("org.khronos.openxr:openxr_loader_for_android:1.1.36")
    implementation("androidx.games:games-activity:3.0.4")
}
