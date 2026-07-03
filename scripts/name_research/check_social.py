#!/usr/bin/env python3
"""Check social handle availability for top name candidates."""

from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.request
from pathlib import Path

REQUEST_DELAY = 0.5
USER_AGENT = "Mozilla/5.0 (compatible; IndieArtistNamingResearch/1.0)"


def fetch_status(url: str) -> tuple[int, str]:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=12) as resp:
            body = resp.read(8000).decode("utf-8", errors="replace")
            return resp.status, body
    except urllib.error.HTTPError as exc:
        body = exc.read(8000).decode("utf-8", errors="replace") if exc.fp else ""
        return exc.code, body
    except Exception as exc:  # noqa: BLE001
        return 0, str(exc)


def check_instagram(handle: str) -> str:
    code, body = fetch_status(f"https://www.instagram.com/{handle}/")
    if code == 404:
        return "available"
    if "Sorry, this page isn't available" in body or '"username":"' not in body.lower():
        return "likely_available"
    if code == 200:
        return "taken"
    return "unknown"


def check_x(handle: str) -> str:
    code, body = fetch_status(f"https://x.com/{handle}")
    if code == 404:
        return "available"
    if "this account doesn't exist" in body.lower() or "account suspended" in body.lower():
        return "likely_available"
    if code == 200 and ("profile" in body.lower() or "@" in body):
        return "taken"
    return "unknown"


def check_tiktok(handle: str) -> str:
    code, body = fetch_status(f"https://www.tiktok.com/@{handle}")
    if code == 404:
        return "available"
    if "couldn't find this account" in body.lower():
        return "likely_available"
    if code == 200 and "uniqueId" in body:
        return "taken"
    return "unknown"


def score_social(result: dict) -> float:
    statuses = [result["instagram"], result["x"], result["tiktok"]]
    avail = sum(1 for s in statuses if s in ("available", "likely_available"))
    if avail == 3:
        return 5.0
    if avail == 2:
        return 4.0
    if avail == 1:
        return 2.5
    return 1.0


CURATED_SOCIAL = [
    "ownlynk", "sparklynk", "launchlynk", "rallylynk", "bloomlynk", "thrivelynk",
    "ignitelynk", "elevlynk", "flourlynk", "signallynk", "unitylynk", "livelynk",
    "harborlynk", "scenelynk", "venuelynk",
    "creatorlynk", "staglynk", "giglynk", "creatlynk", "createlynk",
    "stagenect", "fanmesh", "creatnect", "lynkstage",
    "catalynk", "amplynk",
]


def load_top_names(base: Path, limit: int = 30) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()
    for name in CURATED_SOCIAL:
        if name not in seen:
            seen.add(name)
            ordered.append(name)
    scored = json.loads((base / "scored_names.json").read_text(encoding="utf-8"))
    for r in scored["top_available"]:
        n = r["name"]
        if n not in seen and r.get("available"):
            seen.add(n)
            ordered.append(n)
        if len(ordered) >= limit + 5:
            break
    return ordered[: limit + 5]


def main() -> None:
    base = Path(__file__).resolve().parent
    names = load_top_names(base, limit=30)
    results = []

    for i, name in enumerate(names, 1):
        handle = re.sub(r"[^a-z0-9_]", "", name.lower())[:30]
        print(f"[{i}/{len(names)}] Social check @{handle}...")
        ig = check_instagram(handle)
        time.sleep(REQUEST_DELAY)
        x = check_x(handle)
        time.sleep(REQUEST_DELAY)
        tt = check_tiktok(handle)
        time.sleep(REQUEST_DELAY)

        row = {
            "name": name,
            "handle": handle,
            "instagram": ig,
            "x": x,
            "tiktok": tt,
            "social_score": score_social({"instagram": ig, "x": x, "tiktok": tt}),
        }
        results.append(row)
        print(f"  IG={ig} X={x} TikTok={tt} score={row['social_score']}")

    out_path = base / "social_handles.json"
    out_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
