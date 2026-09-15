import pytest

from {{ cookiecutter.project_slug.replace('-', '_') }} import i18n

CATALOGS = {
    "en": {
        "inbox": {
            "greeting": "Hello, {name}!",
            "unread": {
                "one": "{count} new message",
                "other": "{count} new messages",
            },
            "empty": "Nothing here yet",
        }
    },
    "nl": {
        "inbox": {
            "greeting": "Hoi, {name}!",
            "unread": {
                "one": "{count} nieuw bericht",
                "other": "{count} nieuwe berichten",
            },
        }
    },
}


@pytest.fixture
def catalogs(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(i18n, "_CATALOGS", CATALOGS)


def test_bundles_base_and_dutch() -> None:
    assert {"en", "nl"} <= set(i18n.LOCALES)


@pytest.mark.parametrize(
    ("tag", "expected"),
    [
        ("nl_NL.UTF-8", "nl"),
        ("nl-BE", "nl"),
        ("NL", "nl"),
        ("en_US.UTF-8", "en"),
        ("C", "en"),
        ("POSIX", "en"),
        ("xx_XX.UTF-8", "en"),
        (None, "en"),
    ],
)
def test_normalize(tag: str | None, expected: str) -> None:
    assert i18n.normalize(tag) == expected


def test_locale_from_env_prefers_lc_all_then_lc_messages_then_lang(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for name in ("LC_ALL", "LC_MESSAGES", "LANG"):
        monkeypatch.delenv(name, raising=False)
    assert i18n.locale_from_env() == "en"
    monkeypatch.setenv("LANG", "nl_NL.UTF-8")
    assert i18n.locale_from_env() == "nl"
    monkeypatch.setenv("LC_MESSAGES", "C")
    assert i18n.locale_from_env() == "en"
    monkeypatch.setenv("LC_ALL", "nl_BE.UTF-8")
    assert i18n.locale_from_env() == "nl"


@pytest.mark.parametrize(
    ("header", "expected"),
    [
        ("nl-NL,nl;q=0.9,en;q=0.8", "nl"),
        ("en;q=0.5, nl;q=0.8", "nl"),
        ("xx, nl;q=0.2", "nl"),
        ("nl;q=0", "en"),
        ("*", "en"),
        (None, "en"),
    ],
)
def test_negotiate_honours_q_values(header: str | None, expected: str) -> None:
    assert i18n.negotiate(header) == expected


@pytest.mark.usefixtures("catalogs")
def test_t_substitutes_placeholders() -> None:
    assert i18n.t("inbox.greeting", "nl", name="Sam") == "Hoi, Sam!"


@pytest.mark.usefixtures("catalogs")
def test_t_picks_plural_form_by_count() -> None:
    assert i18n.t("inbox.unread", "nl", count=1) == "1 nieuw bericht"
    assert i18n.t("inbox.unread", "nl", count=0) == "0 nieuwe berichten"
    assert i18n.t("inbox.unread", "en", count=3) == "3 new messages"


@pytest.mark.usefixtures("catalogs")
def test_t_falls_back_to_base_for_missing_locale_or_key() -> None:
    assert i18n.t("inbox.greeting", "xx", name="Sam") == "Hello, Sam!"
    assert i18n.t("inbox.empty", "nl") == "Nothing here yet"


@pytest.mark.usefixtures("catalogs")
def test_t_falls_back_to_the_key_when_no_locale_has_it() -> None:
    assert i18n.t("inbox.missing", "nl") == "inbox.missing"
