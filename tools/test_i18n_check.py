#!/usr/bin/env python3
"""Offline test for .claude/scripts/check_i18n.py.

Builds one throwaway project per fixture in a tempdir, runs the checker and asserts
the exit code and the problem it names: missing key, extra key, placeholder mismatch,
plural objects, an undeclared extra locale, Apple .strings (UTF-8 and UTF-16), Android
resources, Shopify's en.default base file, a missing required locale, the dormant
not-configured mode, and the phone-home diagnostic record.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "python/cli/{{cookiecutter.project_slug}}/.claude/scripts"

JSON_CFG = {"base": "en", "required": ["en", "nl"], "format": "json", "files": ["messages/{locale}.json"]}
STRINGS_CFG = {**JSON_CFG, "format": "strings", "files": ["App/Resources/{locale}.lproj/Localizable.strings"]}
ANDROID_CFG = {**JSON_CFG, "format": "android", "files": ["app/src/main/res/values-{locale}/strings.xml"]}
SHOPIFY_CFG = {**JSON_CFG, "base_file": "en.default", "files": ["locales/{locale}.json", "locales/{locale}.schema.json"]}

SCHEMA = "https://inlang.com/schema/inlang-message-format"
EN = {"$schema": SCHEMA, "home": {"title": "Welcome", "greeting": "Hello, {name}!"},
      "files": {"one": "1 file", "other": "{count} files"}}
NL = {"$schema": SCHEMA, "home": {"title": "Welkom", "greeting": "Hoi {name}!"},
      "files": {"one": "1 bestand", "other": "{count} bestanden"}}


def _with(base: dict, path: str, value: object) -> dict:
    """Deep copy of base with a dotted path set (value None deletes it)."""
    out = json.loads(json.dumps(base))
    *parents, leaf = path.split(".")
    node = out
    for key in parents:
        node = node.setdefault(key, {})
    if value is None:
        del node[leaf]
    else:
        node[leaf] = value
    return out


def _messages(en: dict, nl: dict | None) -> dict[str, str]:
    files = {"messages/en.json": json.dumps(en)}
    if nl is not None:
        files["messages/nl.json"] = json.dumps(nl)
    return files


EN_STRINGS = '/* Greeting on launch */\n"greeting" = "Hello, %@!";\n"welcome" = "Welcome";\n'
EN_ANDROID = ('<resources><string name="app_name">Quest</string>'
              '<string name="version" translatable="false">1.0</string>'
              '<string name="score">Score: %1$d</string></resources>')
NL_ANDROID = '<resources><string name="app_name">Quest</string><string name="score">Punten: %d</string></resources>'

# (name, i18n block, files, expected exit code, substrings stdout must contain, substrings it must not)
CASES: list[tuple[str, dict | None, dict, int, list[str], list[str]]] = [
    ("json ok, plural forms may drop a placeholder", JSON_CFG, _messages(EN, NL), 0, ["i18n: ok (en, nl;"], []),
    ("missing key", JSON_CFG, _messages(EN, _with(NL, "home.title", None)), 1,
     ["messages/nl.json: missing key home.title"], []),
    ("extra key", JSON_CFG, _messages(EN, _with(NL, "home.extra", "Extra")), 1,
     ["messages/nl.json: extra key home.extra"], []),
    ("placeholder mismatch", JSON_CFG, _messages(EN, _with(NL, "home.greeting", "Hoi {naam}!")), 1,
     ["placeholders differ for home.greeting: en {name} / nl {naam}"], []),
    ("plural placeholder mismatch", JSON_CFG, _messages(EN, _with(NL, "files.other", "{n} bestanden")), 1,
     ["placeholders differ for files: en {count} / nl {n}"], []),
    ("required locale missing", JSON_CFG, _messages(EN, None), 1, ["nl: missing messages/nl.json"], []),
    ("undeclared extra locale is checked too", JSON_CFG,
     {**_messages(EN, NL), "messages/de.json": json.dumps(_with(EN, "home.title", None))}, 1,
     ["messages/de.json: missing key home.title"], ["messages/nl.json"]),
    ("printf flags and width are the same placeholder (date formats reorder and unpad)", JSON_CFG,
     _messages(_with(EN, "date_formats.long", "%B %d, %Y"), _with(NL, "date_formats.long", "%-d %B %Y")),
     0, ["i18n: ok (en, nl;"], []),
    ("strings ok, nl in UTF-16", STRINGS_CFG,
     {"App/Resources/en.lproj/Localizable.strings": EN_STRINGS,
      "App/Resources/nl.lproj/Localizable.strings": '"greeting" = "Hoi %@!";\n"welcome" = "Welkom";\n'.encode("utf-16")},
     0, ["i18n: ok (en, nl;"], []),
    ("strings placeholder mismatch", STRINGS_CFG,
     {"App/Resources/en.lproj/Localizable.strings": EN_STRINGS,
      "App/Resources/nl.lproj/Localizable.strings": '"greeting" = "Hoi!";\n"welcome" = "Welkom";\n'},
     1, ["placeholders differ for greeting: en %@ / nl (none)"], []),
    ("android ok: positional args, translatable=false skipped", ANDROID_CFG,
     {"app/src/main/res/values/strings.xml": EN_ANDROID, "app/src/main/res/values-nl/strings.xml": NL_ANDROID},
     0, ["i18n: ok (en, nl;"], []),
    ("android missing key", ANDROID_CFG,
     {"app/src/main/res/values/strings.xml": EN_ANDROID,
      "app/src/main/res/values-nl/strings.xml": '<resources><string name="app_name">Quest</string></resources>'},
     1, ["app/src/main/res/values-nl/strings.xml: missing key score"], []),
    ("shopify en.default base, schema file checked separately", SHOPIFY_CFG,
     {"locales/en.default.json": json.dumps({"cart": {"count": {"one": "{{ count }} item", "other": "{{ count }} items"}}}),
      "locales/nl.json": json.dumps({"cart": {"count": {"one": "{{ count }} artikel", "other": "{{ count }} artikelen"}}}),
      "locales/en.default.schema.json": json.dumps({"sections": {"header": {"name": "Header"}}}),
      "locales/nl.schema.json": json.dumps({"sections": {"header": {}}})},
     1, ["locales/nl.schema.json: missing key sections.header.name"], ["locales/nl.json", "en.default.schema"]),
    ("not configured", None, {}, 0, ["i18n: not configured"], ["FAIL"]),
]


def _project(base: Path, index: int, i18n: dict | None, files: dict) -> Path:
    project = base / f"case{index}"
    (project / ".claude" / "scripts").mkdir(parents=True)
    for script in ("check_i18n.py", "_diag.py"):
        shutil.copy(SCRIPTS / script, project / ".claude" / "scripts" / script)
    quality: dict = {"loc": {"warn": 300, "error": 400}}
    if i18n is not None:
        quality["i18n"] = i18n
    (project / ".quality.json").write_text(json.dumps(quality))
    for rel, content in files.items():
        path = project / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, bytes):
            path.write_bytes(content)
        else:
            path.write_text(content, encoding="utf-8")
    return project


def _run(project: Path, diag: bool = False) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env.pop("NO_TEMPLATE_DIAG", None)
    if not diag:
        env["NO_TEMPLATE_DIAG"] = "1"
    return subprocess.run(
        [sys.executable, ".claude/scripts/check_i18n.py"],
        cwd=project, capture_output=True, text=True, encoding="utf-8", errors="replace", env=env,
    )


def main() -> None:
    failures: list[str] = []

    # The script ships through cookiecutter's Jinja render; delimiters in it break every render.
    source = (SCRIPTS / "check_i18n.py").read_text(encoding="utf-8")
    failures += [f"check_i18n.py contains Jinja delimiter {d!r}" for d in ("{" + "{", "{" + "%", "{" + "#") if d in source]

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        for index, (name, i18n, files, code, present, absent) in enumerate(CASES):
            r = _run(_project(tmp_path, index, i18n, files))
            if r.returncode != code:
                failures.append(f"{name}: expected exit {code}, got {r.returncode}: {r.stdout!r} {r.stderr[-500:]!r}")
            failures += [f"{name}: expected {s!r} in {r.stdout!r}" for s in present if s not in r.stdout]
            failures += [f"{name}: unexpected {s!r} in {r.stdout!r}" for s in absent if s in r.stdout]

        # No .quality.json at all -> dormant, exit 0.
        project = _project(tmp_path, len(CASES), None, {})
        (project / ".quality.json").unlink()
        r = _run(project)
        if r.returncode != 0 or "i18n: not configured" not in r.stdout:
            failures.append(f"no .quality.json: expected dormant exit 0, got {r.returncode} {r.stdout!r}")

        # Phone-home: one ok record with the problem count, written to the upstream repo.
        upstream = tmp_path / "upstream"
        project = _project(tmp_path, len(CASES) + 1, JSON_CFG, _messages(EN, NL))
        (project / ".template-meta.json").write_text(json.dumps({
            "template": "python/cli", "template_version": "1.0.0",
            "template_source": {"type": "local", "path": str(upstream)}, "context": {},
        }))
        _run(project, diag=True)
        records = [json.loads(line) for p in (upstream / "_diagnostics" / "python/cli").glob("*.jsonl")
                   for line in p.read_text().splitlines() if line.strip()]
        if len(records) != 1 or records[0].get("hook") != "check_i18n" or records[0].get("status") != "ok" \
                or records[0].get("meta", {}).get("problems") != 0:
            failures.append(f"diag: expected one ok check_i18n record with problems=0, got {records}")

    if failures:
        print("FAIL")
        for f in failures:
            print(f"  - {f}")
        sys.exit(1)
    print(f"OK ({len(CASES) + 2} cases)")


if __name__ == "__main__":
    main()
