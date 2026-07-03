#!/usr/bin/env python3
"""Generate company name candidates for Growth+Link branding direction."""

from __future__ import annotations

import json
from pathlib import Path

GROWTH = [
    "spark",
    "ignite",
    "bloom",
    "thrive",
    "flour",
    "elev",
    "rise",
    "launch",
    "rally",
    "grow",
    "boost",
    "cataly",
    "soar",
    "lift",
    "scale",
    "build",
    "forge",
    "seed",
    "root",
    "nest",
    "harbor",
    "beacon",
    "orbit",
    "anchor",
    "kindle",
    "fuel",
    "drive",
    "push",
    "dash",
    "pulse",
    "glow",
    "shine",
    "flame",
    "prime",
    "peak",
    "apex",
    "surge",
    "swift",
    "rapid",
    "fresh",
    "nova",
    "vivid",
    "bright",
    "clear",
    "true",
    "pure",
    "bold",
    "brave",
    "free",
    "open",
]

CONNECTION = [
    "lynk",
    "link",
    "nect",
    "mesh",
    "bridge",
    "bond",
    "sync",
    "tie",
    "join",
    "hub",
    "loop",
    "relay",
    "signal",
    "echo",
    "wave",
    "flow",
    "grid",
    "net",
    "web",
    "path",
    "lane",
    "line",
    "wire",
    "port",
    "dock",
    "spot",
    "base",
    "core",
    "node",
    "ring",
    "chain",
    "route",
    "trail",
    "meet",
    "gather",
    "circle",
    "union",
    "align",
    "fuse",
    "blend",
    "merge",
    "weave",
    "knit",
    "mesh",
    "nest",
]

AUDIENCE = [
    "fan",
    "artist",
    "creator",
    "stage",
    "gig",
    "scene",
    "venue",
    "crowd",
    "tribe",
    "own",
    "direct",
    "indie",
    "live",
    "support",
    "collect",
]

# Blended coinages (catalyst+lynk style)
BLENDS = [
    "catalynk",
    "amplynk",
    "soundlynk",
    "stagelyn k",
    "fanlynk",
    "creatlynk",
    "giglynk",
    "launchlynk",
    "rallylynk",
    "audiolynk",
    "musiclynk",
    "creatorlynk",
    "crowdlynk",
    "venuelyn k",
    "directlynk",
    "nexlynk",
    "pulselynk",
    "forgelyn k",
    "bridgelyn k",
    "unitylynk",
    "tribelyn k",
    "signallynk",
    "echolynk",
    "beatlynk",
    "wavelyn k",
    "tracklynk",
    "growlynk",
    "riselyn k",
    "elevalynk",
    "ownlynk",
    "homelyn k",
    "baselyn k",
    "livelynk",
    "showlynk",
    "indielynk",
    "scenelyn k",
    "supportlynk",
    "meshlynk",
    "nectlynk",
    "sparklynk",
    "ignitelynk",
    "bloomlynk",
    "thrivelynk",
    "flourlynk",
    "kindlelynk",
    "elevlynk",
    "harborlynk",
    "beaconlynk",
    "anchorlynk",
    "orbitlynk",
    "havenlynk",
    "seedlynk",
    "rootlynk",
    "nestlynk",
    "craftlynk",
    "buildlynk",
    "stagelynk",
    "venuelynk",
    "createlynk",
    "fannect",
    "artnect",
    "creatnect",
    "stagenect",
    "venuenect",
    "fanmesh",
    "artistmesh",
    "creatormesh",
    "stagemesh",
    "fannecta",
    "artnecta",
    "creatnecta",
    "stagnecta",
    "venuenecta",
    "lynkstage",
    "lynkbase",
    "lynkcore",
    "lynkforge",
    "lynkfan",
    "lynkartist",
    "lynkcreator",
    "lynkvenue",
    "lynkgig",
    "lynkshow",
    "lynklive",
    "lynkdirect",
    "lynkgrow",
    "lynklaunch",
    "lynkamplify",
    "lynkunity",
    "lynktribe",
    "lynkecho",
    "lynksignal",
    "lynktrack",
    "lynkorigin",
    "lynkhome",
    "lynkown",
    "lynkfirst",
    "lynkone",
    "lynkhq",
    "lynkos",
    "lynkcollective",
    "lynknetwork",
    "lynkhub",
]

MUSIC_LOCKED_PREFIXES = {"music", "beat", "audio", "sound", "sonic", "tune", "melod", "rhythm"}
TRADEMARK_RISK_STEMS = {"kindle", "amplify", "amazon", "apple", "google", "meta", "spotify", "bandcamp"}


def _clean(name: str) -> str:
    return name.replace(" ", "").lower()


def _valid(name: str) -> bool:
    if not name.isalpha():
        return False
    if not (6 <= len(name) <= 12):
        return False
    for stem in TRADEMARK_RISK_STEMS:
        if stem in name:
            return False
    return True


def generate() -> list[dict]:
    seen: set[str] = set()
    results: list[dict] = []

    def add(name: str, category: str, growth_link: bool = False) -> None:
        name = _clean(name)
        if name in seen or not _valid(name):
            return
        seen.add(name)
        music_locked = any(name.startswith(p) for p in MUSIC_LOCKED_PREFIXES)
        results.append(
            {
                "name": name,
                "domain": f"{name}.com",
                "category": category,
                "growth_link": growth_link,
                "music_locked": music_locked,
            }
        )

    # Growth + Connection (primary direction)
    for g in GROWTH:
        for c in CONNECTION:
            add(g + c, "growth_connection", growth_link=True)

    # Audience + Connection
    for a in AUDIENCE:
        for c in CONNECTION:
            add(a + c, "audience_connection", growth_link="lynk" in c or "link" in c)

    # Audience + Growth suffix patterns
    for a in AUDIENCE:
        for g in GROWTH:
            if len(a + g) <= 12:
                add(a + g, "audience_growth", growth_link=False)

    # Blended coinages
    for b in BLENDS:
        cleaned = _clean(b)
        gl = "lynk" in cleaned or "link" in cleaned
        add(cleaned, "blend", growth_link=gl)

    # Growth + lynk only (explicit priority list expansion)
    for g in GROWTH:
        add(g + "lynk", "growth_lynk", growth_link=True)

    return sorted(results, key=lambda x: x["name"])


def main() -> None:
    out_dir = Path(__file__).resolve().parent
    candidates = generate()
    payload = {
        "total": len(candidates),
        "growth_link_count": sum(1 for c in candidates if c["growth_link"]),
        "candidates": candidates,
    }
    out_path = out_dir / "candidates.json"
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Generated {payload['total']} candidates ({payload['growth_link_count']} growth+link)")
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
