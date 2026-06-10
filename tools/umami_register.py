#!/usr/bin/env python3
"""Register a website in Umami and print its website id.

Usage:
    python tools/umami_register.py <name> <domain>

Connection is read from the environment (prime via `onenv prime`):
    UMAMI_URL       base url of the Umami instance, e.g. https://umami.example.com
    UMAMI_API_KEY   sent as the x-umami-api-key header

On success the created website id is printed to stdout (and nothing else), so the
caller can capture it with `$(...)`. On failure a message is written to stderr and
the process exits non-zero — it never raises a traceback at the caller.
"""
import json
import os
import sys
import urllib.error
import urllib.request


def register(base_url: str, api_key: str, name: str, domain: str) -> str:
    url = f"{base_url.rstrip('/')}/api/websites"
    payload = json.dumps({"name": name, "domain": domain}).encode()
    req = urllib.request.Request(
        url,
        data=payload,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "x-umami-api-key": api_key,
        },
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        body = json.loads(resp.read().decode())
    website_id = body.get("id") or body.get("websiteId")
    if not website_id:
        raise ValueError(f"no website id in response: {body}")
    return website_id


def main():
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <name> <domain>", file=sys.stderr)
        sys.exit(2)

    base_url = os.environ.get("UMAMI_URL")
    api_key = os.environ.get("UMAMI_API_KEY")
    if not base_url or not api_key:
        print(
            "ERROR: UMAMI_URL and UMAMI_API_KEY must be set (run `onenv prime`)",
            file=sys.stderr,
        )
        sys.exit(1)

    name, domain = sys.argv[1], sys.argv[2]
    try:
        website_id = register(base_url, api_key, name, domain)
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")[:300]
        print(f"ERROR: Umami returned HTTP {e.code}: {detail}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: register failed: {type(e).__name__}: {e}", file=sys.stderr)
        sys.exit(1)

    print(website_id)


if __name__ == "__main__":
    main()
