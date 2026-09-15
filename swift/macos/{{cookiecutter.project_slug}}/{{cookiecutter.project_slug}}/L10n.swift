import Foundation

/// `Bundle.module` narrowed to the user's preferred language.
///
/// A bare SwiftPM executable has no Info.plist (no `CFBundleLocalizations`), so Foundation
/// localizes every bundle to the development language and ignores `nl` in the user's
/// language list. Picking the `.lproj` sub-bundle ourselves restores normal selection.
/// Look strings up through `L10n.bundle`, never through `.module` directly.
enum L10n {
    static let bundle: Bundle = {
        let language = Bundle.preferredLocalizations(
            from: Bundle.module.localizations, forPreferences: Locale.preferredLanguages
        ).first ?? "en"
        return Bundle.module.path(forResource: language, ofType: "lproj").flatMap(Bundle.init(path:)) ?? .module
    }()
}
