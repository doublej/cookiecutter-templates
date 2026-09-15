//! User-facing text: `t(locale, key, params)` over the JSON files in `locales/`.

use std::collections::HashMap;
use std::sync::LazyLock;

use serde_json::Value;

/// Every supported language: adding one is a `locales/<code>.json` file plus one line here.
const FILES: &[(&str, &str)] = &[
    ("en", include_str!("../locales/en.json")),
    ("nl", include_str!("../locales/nl.json")),
];
const FALLBACK: &str = "en";
const LOCALE_VARS: [&str; 3] = ["LC_ALL", "LC_MESSAGES", "LANG"];

static CATALOGS: LazyLock<HashMap<&str, Value>> = LazyLock::new(|| {
    FILES
        .iter()
        .map(|&(code, json)| {
            (
                code,
                serde_json::from_str(json).expect("locale file is valid JSON"),
            )
        })
        .collect()
});

pub fn supported() -> impl Iterator<Item = &'static str> {
    FILES.iter().map(|&(code, _)| code)
}

/// `nl_NL.UTF-8` → `nl`; `C`, `POSIX` and unsupported locales → `en`.
pub fn normalize(raw: &str) -> &'static str {
    let language = raw
        .split(['_', '-', '.', '@'])
        .next()
        .unwrap_or_default()
        .to_lowercase();
    supported()
        .find(|code| *code == language)
        .unwrap_or(FALLBACK)
}

/// Locale from `LC_ALL`, then `LC_MESSAGES`, then `LANG`; `en` when none is set.
pub fn locale_from_env() -> &'static str {
    locale_from(|var| std::env::var(var).ok())
}

fn locale_from(read_var: impl Fn(&str) -> Option<String>) -> &'static str {
    let raw = LOCALE_VARS
        .iter()
        .find_map(|var| read_var(var).filter(|value| !value.is_empty()));
    raw.map_or(FALLBACK, |value| normalize(&value))
}

/// Text for `key` (dotted path) in `locale`, falling back to `en`, then to the key itself.
/// `{name}` placeholders are filled from `params`; plural keys pick a form from the `count` param.
pub fn t(locale: &str, key: &str, params: &[(&str, &str)]) -> String {
    let text = lookup(locale, key, params)
        .or_else(|| lookup(FALLBACK, key, params))
        .unwrap_or(key);
    params
        .iter()
        .fold(text.to_string(), |text, &(name, value)| {
            text.replace(&["{", name, "}"].concat(), value)
        })
}

fn lookup(locale: &str, key: &str, params: &[(&str, &str)]) -> Option<&'static str> {
    let node = CATALOGS
        .get(locale)?
        .pointer(&format!("/{}", key.replace('.', "/")))?;
    let node = if node.is_object() {
        &node[plural_form(params)]
    } else {
        node
    };
    node.as_str()
}

// ponytail: one/other only (count == 1) — correct for en and nl; add CLDR plural rules with the
// first language that needs more
fn plural_form(params: &[(&str, &str)]) -> &'static str {
    if params.contains(&("count", "1")) {
        "one"
    } else {
        "other"
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn resolve(vars: &[(&str, &str)]) -> &'static str {
        locale_from(|var| {
            vars.iter()
                .find(|(name, _)| *name == var)
                .map(|(_, value)| value.to_string())
        })
    }

    #[test]
    fn normalize_maps_system_locales_to_supported_codes() {
        assert_eq!(normalize("nl_NL.UTF-8"), "nl");
        assert_eq!(normalize("NL-be"), "nl");
        assert_eq!(normalize("C"), "en");
        assert_eq!(normalize("POSIX"), "en");
        assert_eq!(normalize("de_DE.UTF-8"), "en");
    }

    #[test]
    fn locale_from_reads_lc_all_then_lc_messages_then_lang() {
        assert_eq!(
            resolve(&[("LC_ALL", "nl_NL.UTF-8"), ("LANG", "en_US.UTF-8")]),
            "nl"
        );
        assert_eq!(
            resolve(&[("LC_ALL", ""), ("LC_MESSAGES", "nl_NL"), ("LANG", "en_US")]),
            "nl"
        );
        assert_eq!(
            resolve(&[("LC_MESSAGES", "C"), ("LANG", "nl_NL.UTF-8")]),
            "en"
        );
        assert_eq!(resolve(&[("LANG", "nl_NL.UTF-8")]), "nl");
        assert_eq!(resolve(&[]), "en");
    }

    #[test]
    fn t_falls_back_to_en_then_to_the_key() {
        assert_eq!(
            t("xx", "output.no_input", &[]),
            t("en", "output.no_input", &[])
        );
        assert_eq!(t("nl", "missing.key", &[]), "missing.key");
    }

    #[test]
    fn t_fills_placeholders() {
        assert_eq!(
            t("en", "output.processing", &[("input", "demo")]),
            "Processing: demo"
        );
    }

    #[test]
    fn t_picks_one_or_other_from_count() {
        assert_eq!(
            t("en", "output.characters", &[("count", "1")]),
            "1 character"
        );
        assert_eq!(t("nl", "output.characters", &[("count", "4")]), "4 tekens");
    }
}
