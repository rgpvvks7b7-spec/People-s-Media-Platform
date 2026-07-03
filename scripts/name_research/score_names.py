#!/usr/bin/env python3
"""Score name candidates using weighted rubric."""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path

WEIGHTS = {
    "pronounce": 0.15,
    "spell": 0.15,
    "premium": 0.10,
    "not_music_locked": 0.15,
    "com_available": 0.20,
    "memorable": 0.10,
    "trademark_low_risk": 0.10,
    "social": 0.05,
}

GROWTH_LINK_BONUS = 0.10  # +10% to final score

PREMIUM_NAMES = {
    "ownlynk",
    "sparklynk",
    "launchlynk",
    "rallylynk",
    "bloomlynk",
    "thrivelynk",
    "ignitelynk",
    "elevlynk",
    "flourlynk",
    "signallynk",
    "unitylynk",
    "livelynk",
    "harborlynk",
    "scenelynk",
    "stagenect",
    "fanmesh",
    "creatnect",
    "creatorlynk",
    "staglynk",
    "catalynk",
    "amplynk",
}

MEMORABLE_NAMES = PREMIUM_NAMES | {
    "venuelynk",
    "createlynk",
    "giglynk",
    "audiolynk",
    "creatlynk",
    "nectlynk",
    "supportlynk",
    "lynkstage",
}

TRADEMARK_RISK = {
    "kindlelynk": 2,
    "amplifyhq": 2,
    "lynkamplify": 2,
    "bandlynk": 2,
    "patreon": 1,
}

VOWELS = set("aeiou")


def count_syllables(word: str) -> int:
    word = word.lower()
    groups = re.findall(r"[aeiouy]+", word)
    return max(1, len(groups))


def score_pronounce(name: str) -> float:
    syl = count_syllables(name)
    if 2 <= syl <= 4:
        return 5.0
    if syl == 1 or syl == 5:
        return 3.5
    return 2.5


def score_spell(name: str) -> float:
    score = 5.0
    if "lynk" in name:
        score -= 0.5
    if "nect" in name:
        score -= 0.3
    if len(name) > 10:
        score -= 0.5
    weird = sum(1 for a, b in zip(name, name[1:]) if a == b and a not in VOWELS)
    score -= weird * 0.3
    return max(1.0, min(5.0, score))


def score_premium(name: str) -> float:
    if name in PREMIUM_NAMES:
        return 5.0
    if name.endswith("lynk") and len(name) <= 10:
        return 4.0
    if name.endswith(("nect", "mesh")):
        return 4.2
    if name.endswith("link") and len(name) <= 9:
        return 3.5
    return 3.0


def score_not_music_locked(music_locked: bool, name: str) -> float:
    if music_locked:
        return 2.0
    music_stems = ("music", "beat", "audio", "sound", "sonic", "tune")
    if any(name.startswith(s) for s in music_stems):
        return 2.5
    return 5.0


def score_memorable(name: str) -> float:
    if name in MEMORABLE_NAMES:
        return 5.0
    if len(name) <= 9 and ("lynk" in name or "nect" in name):
        return 4.0
    return 3.2


def score_trademark(name: str) -> float:
    risk = TRADEMARK_RISK.get(name, 0)
    if risk >= 2:
        return 2.0
    if risk == 1:
        return 3.5
    # Generic lynk/link compounds are medium-low
    if name.endswith("lynk") or name.endswith("link"):
        return 4.0
    return 4.5


def score_social_placeholder() -> float:
    """Filled in later by social check script; default neutral."""
    return 3.5


def load_availability(base: Path) -> dict[str, dict]:
    csv_path = base / "availability_report.csv"
    rows: dict[str, dict] = {}
    with csv_path.open(encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            rows[row["name"]] = row
    return rows


def load_candidates(base: Path) -> list[dict]:
    data = json.loads((base / "candidates.json").read_text(encoding="utf-8"))
    return data["candidates"]


def compute_score(candidate: dict, avail: dict | None) -> dict:
    name = candidate["name"]
    available = avail is not None and avail.get("dns_status") == "likely_available"

    scores = {
        "pronounce": score_pronounce(name),
        "spell": score_spell(name),
        "premium": score_premium(name),
        "not_music_locked": score_not_music_locked(candidate.get("music_locked", False), name),
        "com_available": 5.0 if available else 1.0,
        "memorable": score_memorable(name),
        "trademark_low_risk": score_trademark(name),
        "social": score_social_placeholder(),
    }

    weighted = sum(scores[k] * WEIGHTS[k] for k in WEIGHTS)
    if candidate.get("growth_link"):
        weighted = min(5.0, weighted * (1 + GROWTH_LINK_BONUS))

    return {
        "name": name,
        "domain": candidate["domain"],
        "category": candidate.get("category", ""),
        "growth_link": candidate.get("growth_link", False),
        "dns_status": avail.get("dns_status", "unknown") if avail else "unknown",
        "parking_detected": avail.get("parking_detected", "") if avail else "",
        "scores": scores,
        "weighted_score": round(weighted, 3),
        "available": available,
    }


def main() -> None:
    base = Path(__file__).resolve().parent
    candidates = load_candidates(base)
    availability = load_availability(base)

    scored = [compute_score(c, availability.get(c["name"])) for c in candidates]
    scored.sort(key=lambda x: x["weighted_score"], reverse=True)

    # Include high-scoring taken names for acquisition research
    top_all = scored[:50]
    available_only = [s for s in scored if s["available"]]
    top_available = available_only[:100]

    out = {
        "top_available": top_available,
        "top_all_including_taken": top_all,
        "available_count": len(available_only),
    }
    out_path = base / "scored_names.json"
    out_path.write_text(json.dumps(out, indent=2), encoding="utf-8")

    csv_path = base / "scored_names.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=["name", "weighted_score", "available", "dns_status", "growth_link", "category"],
        )
        writer.writeheader()
        for row in scored:
            writer.writerow(
                {
                    "name": row["name"],
                    "weighted_score": row["weighted_score"],
                    "available": row["available"],
                    "dns_status": row["dns_status"],
                    "growth_link": row["growth_link"],
                    "category": row["category"],
                }
            )

    print(f"Scored {len(scored)} names; {len(available_only)} available")
    print(f"Top available: {', '.join(r['name'] for r in top_available[:10])}")
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
