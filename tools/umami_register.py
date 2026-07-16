#!/usr/bin/env python3
"""Register a website in Umami and print its website id.

Usage:
    python tools/umami_register.py <name> <domain> [--json]

Connection resolves without any priming:
    1. environment: UMAMI_URL + UMAMI_API_KEY or UMAMI_USERNAME/UMAMI_PASSWORD
    2. onenv fallback: `onenv export umami --reveal` fills any missing key

Auth: UMAMI_API_KEY is sent as the x-umami-api-key header (Umami Cloud).
Otherwise UMAMI_USERNAME/UMAMI_PASSWORD log in via POST /api/auth/login and
the returned token is sent as a bearer (self-hosted Umami).

On success the created website id is printed to stdout (with --json a single
line {"websiteId": ..., "umamiUrl": ...} instead), so the caller can capture
it with `$(...)`. On failure a message is written to stderr and the process
exits non-zero — it never raises a traceback at the caller.
"""
import json
import os
import shutil
import subprocess
import sys
import urllib.error
import urllib.request

ONENV_NAMESPACE = "umami"
KEYS = ("UMAMI_URL", "UMAMI_API_KEY", "UMAMI_USERNAME", "UMAMI_PASSWORD")


def _onenv_vars() -> dict:
    """Best-effort {KEY: value} from `onenv export umami --reveal`."""
    if not shutil.which("onenv"):
        return {}
    try:
        r = subprocess.run(
            ["onenv", "export", ONENV_NAMESPACE, "--reveal", "--json"],
            capture_output=True, text=True, timeout=30,
        )
        if r.returncode != 0:
            return {}
        data = json.loads(r.stdout)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def resolve_config() -> dict:
    """Env first; any missing key is filled from the onenv `umami` namespace."""
    cfg = {k: os.environ.get(k, "") for k in KEYS}
    has_auth = cfg["UMAMI_API_KEY"] or (cfg["UMAMI_USERNAME"] and cfg["UMAMI_PASSWORD"])
    if not cfg["UMAMI_URL"] or not has_auth:
        fallback = _onenv_vars()
        for k in KEYS:
            cfg[k] = cfg[k] or fallback.get(k, "")
    cfg["UMAMI_URL"] = cfg["UMAMI_URL"].rstrip("/")
    return cfg


def _post_json(url: str, payload: dict, headers: dict) -> dict:
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        method="POST",
        headers={"Content-Type": "application/json", "Accept": "application/json", **headers},
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode())


def _auth_headers(cfg: dict) -> dict:
    if cfg["UMAMI_API_KEY"]:
        return {"x-umami-api-key": cfg["UMAMI_API_KEY"]}
    body = _post_json(
        f"{cfg['UMAMI_URL']}/api/auth/login",
        {"username": cfg["UMAMI_USERNAME"], "password": cfg["UMAMI_PASSWORD"]},
        {},
    )
    token = body.get("token")
    if not token:
        raise ValueError(f"login returned no token: {list(body)}")
    return {"Authorization": f"Bearer {token}"}


def register(cfg: dict, name: str, domain: str) -> str:
    headers = _auth_headers(cfg)
    body = _post_json(f"{cfg['UMAMI_URL']}/api/websites", {"name": name, "domain": domain}, headers)
    website_id = body.get("id") or body.get("websiteId")
    if not website_id:
        raise ValueError(f"no website id in response: {body}")
    return website_id


def main():
    args = [a for a in sys.argv[1:] if a != "--json"]
    as_json = "--json" in sys.argv[1:]
    if len(args) != 2:
        print(f"Usage: {sys.argv[0]} <name> <domain> [--json]", file=sys.stderr)
        sys.exit(2)

    cfg = resolve_config()
    if not cfg["UMAMI_URL"]:
        print("ERROR: UMAMI_URL not set and not found in onenv namespace 'umami'", file=sys.stderr)
        sys.exit(1)
    if not cfg["UMAMI_API_KEY"] and not (cfg["UMAMI_USERNAME"] and cfg["UMAMI_PASSWORD"]):
        print(
            "ERROR: no Umami credentials — set UMAMI_API_KEY or UMAMI_USERNAME/UMAMI_PASSWORD "
            "(env or onenv namespace 'umami')",
            file=sys.stderr,
        )
        sys.exit(1)

    name, domain = args
    try:
        website_id = register(cfg, name, domain)
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")[:300]
        print(f"ERROR: Umami returned HTTP {e.code}: {detail}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: register failed: {type(e).__name__}: {e}", file=sys.stderr)
        sys.exit(1)

    if as_json:
        print(json.dumps({"websiteId": website_id, "umamiUrl": cfg["UMAMI_URL"]}))
    else:
        print(website_id)


if __name__ == "__main__":
    main()
