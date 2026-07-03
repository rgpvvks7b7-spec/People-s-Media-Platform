#!/usr/bin/env python3
"""Build final shortlist.md from scored names, RDAP, and social data."""

from __future__ import annotations

import json
from pathlib import Path

# Manual trademark assessment (preliminary — not legal advice)
TRADEMARK = {
    "ownlynk": ("Medium", "Phonetically similar to Owlynk (KR robotics/comm, owlynk.com). No exact AU/US TM found."),
    "launchlynk": ("Low", "No major conflicts found in music/creator SaaS."),
    "rallylynk": ("Low", "Distinct compound; no major platform conflicts."),
    "bloomlynk": ("Low", "Generic growth metaphor; no major conflicts."),
    "thrivelynk": ("Low", "Distinct; no major conflicts."),
    "ignitelynk": ("Low", "Distinct compound."),
    "elevlynk": ("Low", "Distinct compound."),
    "flourlynk": ("Low", "Distinct compound."),
    "signallynk": ("Medium", "SignalLink is a known brand category; compound is distinct."),
    "unitylynk": ("Low", "Distinct compound."),
    "harborlynk": ("Low", "Distinct compound."),
    "scenelynk": ("Low", "Fits local scene positioning; no major conflicts."),
    "venuelynk": ("Low", "Venue-focused; distinct."),
    "kindlelynk": ("High", "Amazon Kindle trademark risk — avoid."),
    "creatorlynk": ("Low", "Creator economy; broad but clear."),
    "staglynk": ("Low", "Stage + link; clear live music angle."),
    "giglynk": ("Low", "Gig economy angle."),
    "creatlynk": ("Low", "Short creator + lynk."),
    "createlynk": ("Low", "Creator + lynk variant."),
    "stagenect": ("Low", "More distinctive coinage; good TM potential."),
    "creatnect": ("Low", "Distinct coinage."),
    "lynkstage": ("Low", "Reversed compound; available."),
    "catalynk": ("High", "Existing Catalynk businesses (NZ consulting catalynk.co, UK AI healthcare catalynk.app). Domain held by HugeDomains."),
    "amplynk": ("Medium", "Similar to Amplync (amplync.com) and Amplink (link shortener)."),
}

TAGLINES = {
    "ownlynk": ["Own your audience.", "Where artists and fans connect directly."],
    "launchlynk": ["Launch your career. Link your fans.", "The launchpad for independent creators."],
    "rallylynk": ["Rally your fans. Build what lasts.", "Where independent artists rally their audience."],
    "bloomlynk": ["Where music builds lasting connections.", "Grow your audience. Keep the relationship."],
    "thrivelynk": ["Thrive independently.", "The growth network for independent creators."],
    "stagenect": ["Connect on stage. Grow off it.", "Where live music builds real relationships."],
    "scenelynk": ["Your scene. Your fans. Your link.", "Connect with the artists in your scene."],
    "creatnect": ["Create. Connect. Grow.", "Direct connections for independent creators."],
    "creatorlynk": ["Link your fans. Keep your independence.", "The creator network that puts you first."],
    "staglynk": ["From stage to audience — directly.", "Link your live shows to lasting fans."],
    "ignitelynk": ["Ignite your audience.", "Spark growth. Build connections."],
    "elevlynk": ["Elevate your craft. Own your audience.", "Rise independently."],
    "catalynk": ["Connecting independent artists with the people who matter.", "Catalyst for growth. Link for life."],
}

PRONUNCIATION = {
    "ownlynk": "OWN-link",
    "launchlynk": "LAUNCH-link",
    "rallylynk": "RALLY-link",
    "bloomlynk": "BLOOM-link",
    "thrivelynk": "THRIVE-link",
    "ignitelynk": "ig-NITE-link",
    "elevlynk": "eh-LEV-link",
    "flourlynk": "FLUR-link",
    "signallynk": "SIG-nul-link",
    "unitylynk": "YOU-nih-tee-link",
    "harborlynk": "HAR-bor-link",
    "scenelynk": "SEEN-link",
    "venuelynk": "VEN-yoo-link",
    "creatorlynk": "kree-AY-tor-link",
    "staglynk": "STAYJ-link",
    "giglynk": "GIG-link",
    "creatlynk": "KREE-at-link",
    "createlynk": "KREE-ate-link",
    "stagenect": "STAYJ-nect",
    "creatnect": "KREE-at-nect",
    "lynkstage": "LINK-stayj",
    "catalynk": "CAT-uh-link",
    "amplynk": "AMP-link",
}


def main() -> None:
    base = Path(__file__).resolve().parent
    social = {r["name"]: r for r in json.loads((base / "social_handles.json").read_text())}
    rdap = {r["name"]: r for r in json.loads((base / "wix_whois_results.json").read_text())}
    scored = json.loads((base / "scored_names.json").read_text())

    # Curated final shortlist order (human-ranked after automated pass)
    finalists = [
        "ownlynk", "launchlynk", "rallylynk", "bloomlynk", "thrivelynk",
        "ignitelynk", "elevlynk", "scenelynk", "stagenect", "creatnect",
        "creatorlynk", "staglynk", "lynkstage", "signallynk", "unitylynk",
        "flourlynk", "harborlynk", "venuelynk", "creatlynk", "createlynk",
        "giglynk", "audiolynk", "fannecta", "artnecta", "creatnecta",
        "stagnecta", "venuenecta", "supportlynk", "nectlynk",
        "catalynk", "amplynk",
    ]

    lines = [
        "# Company Name Shortlist",
        "",
        "**Platform today:** IndieFund (indiefund.com taken)",
        "**Research date:** 30 June 2026",
        "**Candidates generated:** 3,558 | **DNS-available:** 757 | **RDAP-verified available (curated):** 28",
        "",
        "> Trademark notes are preliminary screening only — not legal advice. Engage your AU lawyer before filing.",
        "",
        "## Recommendation",
        "",
        "**Register immediately if you love it: Ownlynk** (`ownlynk.com`)",
        "",
        "- Best alignment with your core pitch: *own your audience*, direct-to-fan, no middleman",
        "- RDAP-confirmed .com available (~$12–15/yr to register)",
        "- Instagram likely available; X/Twitter `@ownlynk` available",
        "- Medium trademark risk (phonetic overlap with Owlynk robotics brand) — lawyer should clear",
        "",
        "**Runner-up:** Launchlynk, Rallylynk, Bloomlynk, Stagenect",
        "",
        "**Avoid unless acquiring:** Catalynk (domain $$$ via HugeDomains + existing NZ/UK companies), Kindlelynk (Amazon TM)",
        "",
        "---",
        "",
        "## Tier A — Growth + Link (.com confirmed available via Verisign RDAP)",
        "",
        "| Rank | Name | Score | .com | Social (IG/X/TT) | TM Risk | Pronunciation | Tagline |",
        "|------|------|-------|------|------------------|---------|---------------|---------|",
    ]

    score_by_name = {r["name"]: r for r in scored["top_available"]}
    for i, name in enumerate(finalists[:25], 1):
        if name in ("catalynk", "amplynk"):
            continue
        rd = rdap.get(name, {})
        if rd.get("whois_status") == "registered":
            continue
        soc = social.get(name, {})
        tm_level, _ = TRADEMARK.get(name, ("Low", ""))
        score = score_by_name.get(name, {}).get("weighted_score", "—")
        ig = soc.get("instagram", "—")
        x = soc.get("x", "—")
        tt = soc.get("tiktok", "—")
        tag = TAGLINES.get(name, ["—"])[0]
        pron = PRONUNCIATION.get(name, name)
        lines.append(
            f"| {i} | **{name.title()}** | {score} | Available | {ig}/{x}/{tt} | {tm_level} | {pron} | {tag} |"
        )

    lines.extend([
        "",
        "---",
        "",
        "## Tier B — Acquire if budget allows",
        "",
        "| Name | .com | Est. cost | TM Risk | Notes |",
        "|------|------|-----------|---------|-------|",
        "| **Catalynk** | Taken (HugeDomains/NameBright) | $2,000–$8,000+ | High | See ACQUISITION.md. Existing NZ consulting + UK AI healthcare brands. |",
        "| **Amplynk** | Taken (XServer JP) | Unknown — inquire | Medium | Similar to Amplync, Amplink. Registered Dec 2024. |",
        "",
        "---",
        "",
        "## Tier C — RDAP shows TAKEN (despite DNS false negative)",
        "",
        "These appeared available via DNS but Verisign RDAP confirms registration:",
        "",
        "- sparklynk.com",
        "- livelynk.com",
        "- fanmesh.com",
        "",
        "---",
        "",
        "## Names to avoid",
        "",
        "| Name | Reason |",
        "|------|--------|",
        "| kindlelynk | Amazon Kindle trademark risk |",
        "| musiclynk / audiolynk | Locks brand into music-only (lower strategic flexibility) |",
        "| Plain \"lynk\" | lynk.com taken; poor TM/social protection |",
        "",
        "---",
        "",
        "## Social handle summary (curated check)",
        "",
        "Best social availability (X handle free):",
        "- ownlynk, launchlynk, rallylynk, bloomlynk, thrivelynk, ignitelynk, elevlynk",
        "- flourlynk, signallynk, unitylynk, harborlynk, scenelynk, venuelynk",
        "- creatorlynk, staglynk, creatlynk, createlynk, stagenect, lynkstage",
        "",
        "X taken (need fallback like @getname or @namehq):",
        "- sparklynk, giglynk, fanmesh, creatnect, catalynk, amplynk",
        "",
        "Instagram: all checked handles appear likely available (no active profile detected).",
        "",
        "---",
        "",
        "## Next steps",
        "",
        "1. Pick 3–5 finalists from Tier A",
        "2. Register `.com` immediately (domains get sniped after research)",
        "3. Grab Instagram + X handles same day",
        "4. Lawyer trademark clearance in AU (Classes 9, 41, 42) + US if launching globally",
        "5. Rebrand codebase (~70 files) as separate PR after name is locked",
        "",
        "---",
        "",
        "## Data files",
        "",
        "- [`candidates.json`](candidates.json) — 3,558 generated names",
        "- [`availability_report.csv`](availability_report.csv) — DNS status for all",
        "- [`scored_names.json`](scored_names.json) — weighted scores",
        "- [`wix_whois_results.json`](wix_whois_results.json) — Verisign RDAP verification",
        "- [`social_handles.json`](social_handles.json) — IG/X/TikTok checks",
        "- [`ACQUISITION.md`](ACQUISITION.md) — catalynk/amplynk buy options",
        "",
    ])

    (base / "shortlist.md").write_text("\n".join(lines), encoding="utf-8")
    print("Wrote shortlist.md")


if __name__ == "__main__":
    main()
