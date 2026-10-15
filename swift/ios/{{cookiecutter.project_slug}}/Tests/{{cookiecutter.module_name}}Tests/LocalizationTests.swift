import Foundation
import Testing

/// Reads the `.strings` files from source, so the test needs no import of the executable target.
private func strings(_ language: String) throws -> [String: String] {
    let url = URL(filePath: #filePath)
        .deletingLastPathComponent().deletingLastPathComponent().deletingLastPathComponent()
        .appending(path: "{{ cookiecutter.project_slug }}/Resources/\(language).lproj/Localizable.strings")
    let plist = try PropertyListSerialization.propertyList(from: Data(contentsOf: url), format: nil)
    return try #require(plist as? [String: String])
}

@Test func dutchHasEnglishKeys() throws {
    let english = try strings("en")
    #expect(!english.isEmpty)
    #expect(Set(try strings("nl").keys) == Set(english.keys))
}
