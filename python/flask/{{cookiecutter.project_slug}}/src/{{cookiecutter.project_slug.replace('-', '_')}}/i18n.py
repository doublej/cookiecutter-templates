"""User-facing text, looked up by key in the bundled `locales/<locale>.json` files."""

import json
import os
import re
from importlib import resources
from typing import Any

BASE_LOCALE = "en"

_CATALOGS: dict[str, dict[str, Any]] = {
    file.name.removesuffix(".json"): json.loads(file.read_text(encoding="utf-8"))
    for file in resources.files(__package__).joinpath("locales").iterdir()
    if file.name.endswith(".json")
}
LOCALES = tuple(sorted(_CATALOGS))

_Q_VALUE = re.compile(r"\bq=([01](?:\.\d{0,3})?)")


def normalize(tag: str | None) -> str:
    """Map a locale tag (`nl_NL.UTF-8`, `nl-NL`, `C`) to a supported locale, else the base."""
    language = _language(tag or "")
    return language if language in LOCALES else BASE_LOCALE


def locale_from_env() -> str:
    """Resolve the locale from LC_ALL, then LC_MESSAGES, then LANG; the first one set wins."""
    env = os.environ
    return normalize(env.get("LC_ALL") or env.get("LC_MESSAGES") or env.get("LANG"))


def negotiate(accept_language: str | None) -> str:
    """Pick the supported locale an Accept-Language header ranks highest, by q-value."""
    weighted = [_weigh(part) for part in (accept_language or "").split(",")]
    supported = [(q, lang) for q, lang in weighted if q > 0 and lang in LOCALES]
    return max(supported, key=lambda pair: pair[0], default=(0.0, BASE_LOCALE))[1]


def t(key: str, locale: str, **params: object) -> str:
    """Translate a dotted key: the locale's text, else the base locale's, else the key."""
    text = _lookup(locale, key)
    if text is None:
        text = _lookup(BASE_LOCALE, key)
    if text is None:
        return key
    if isinstance(text, dict):
        # ponytail: one/other only — correct for en and nl; add CLDR plural rules with the first language that needs more
        text = text["one" if params.get("count") == 1 else "other"]
    return str(text).format(**params)


def _language(tag: str) -> str:
    return re.split(r"[-_.@]", tag.strip(), maxsplit=1)[0].lower()


def _weigh(part: str) -> tuple[float, str]:
    tag, _, params = part.partition(";")
    q_value = _Q_VALUE.search(params)
    return (float(q_value.group(1)) if q_value else 1.0), _language(tag)


def _lookup(locale: str, key: str) -> Any:
    node: Any = _CATALOGS.get(locale, {})
    for part in key.split("."):
        if not isinstance(node, dict) or part not in node:
            return None
        node = node[part]
    return node
