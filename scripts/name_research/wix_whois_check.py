#!/usr/bin/env python3
"""Verify domain availability via Verisign RDAP (replaces Wix WHOIS API)."""

from __future__ import annotations

import csv
import json
import time
import urllib.error
import urllib.request
from pathlib import Path

RDAP_URL = "https://rdap.verisign.com/com/v1/domain/{domain}"
REQUEST_DELAY = 0.25

CURATED_VERIFY = [
    "ownlynk", "sparklynk", "launchlynk", "rallylynk", "bloomlynk", "thrivelynk",
    "ignitelynk", "elevlynk", "flourlynk", "signallynk", "unitylynk", "livelynk",
    "harborlynk", "scenelynk", "venuelynk", "kindlelynk",
    "creatorlynk", "staglynk", "giglynk", "audiolynk", "creatlynk", "createlynk",
    "stagenect", "fanmesh", "creatnect", "fannecta", "artnecta", "creatnecta",
    "stagnecta", "venuenecta", "lynkstage", "supportlynk", "nectlynk",
    "catalynk", "amplynk",
]


def rdap_lookup(domain: str) -> dict:
    url = RDAP_URL.format(domain=domain.upper())
    req = urllib.request.Request(
        url,
        headers={"Accept": "application/rdap+json", "User-Agent": "NamingResearch/1.0"},
    )
    try:
        with urllib.request.urlopen(req, timeout=12) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return {"registered": True, "data": data}
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return {"registered": False, "data": {}}
        return {"registered": None, "error": f"HTTP {exc.code}"}
    except Exception as exc:  # noqa: BLE001
        return {"registered": None, "error": str(exc)}


def registrar_from_rdap(data: dict) -> str:
    for entity in data.get("entities", []):
        roles = entity.get("roles", [])
        if "registrar" in roles:
            vcard = entity.get("vcardArray", [[], []])
            if len(vcard) > 1:
                for item in vcard[1]:
                    if item[0] == "fn":
                        return str(item[3])
    return ""


def load_top_available(base: Path, limit: int = 100) -> list[str]:
    scored_path = base / "scored_names.json"
    algo: list[str] = []
    if scored_path.exists():
        data = json.loads(scored_path.read_text(encoding="utf-8"))
        algo = [r["name"] for r in data.get("top_available", [])[:limit]]

    ordered: list[str] = []
    seen: set[str] = set()
    for name in CURATED_VERIFY + algo:
        if name not in seen:
            seen.add(name)
            ordered.append(name)
    return ordered[:limit]


def load_rows(base: Path) -> list[dict]:
    with (base / "availability_report.csv").open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def main() -> None:
    base = Path(__file__).resolve().parent
    names = load_top_available(base, limit=100)
    rows_by_name = {r["name"]: r for r in load_rows(base)}

    results = []
    for i, name in enumerate(names, 1):
        domain = f"{name}.com"
        print(f"[{i}/{len(names)}] RDAP {domain}...")
        resp = rdap_lookup(domain)
        if resp["registered"] is True:
            status = "registered"
            registrar = registrar_from_rdap(resp.get("data", {}))
        elif resp["registered"] is False:
            status = "available"
            registrar = ""
        else:
            status = "error"
            registrar = resp.get("error", "")

        row = rows_by_name.get(name, {})
        results.append(
            {
                "name": name,
                "domain": domain,
                "dns_status": row.get("dns_status", ""),
                "whois_status": status,
                "registrar": registrar,
                "rdap_confirmed": resp["registered"] is not False if resp["registered"] is not None else None,
            }
        )
        time.sleep(REQUEST_DELAY)

    out_path = base / "wix_whois_results.json"
    out_path.write_text(json.dumps(results, indent=2), encoding="utf-8")

    rdap_by_name = {r["name"]: r for r in results}
    all_rows = load_rows(base)
    for row in all_rows:
        if row["name"] in rdap_by_name:
            row["whois_status"] = rdap_by_name[row["name"]]["whois_status"]

    csv_path = base / "availability_report.csv"
    fieldnames = ["name", "domain", "dns_status", "whois_status", "parking_detected", "registrar_hint"]
    with csv_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in all_rows:
            writer.writerow({k: row.get(k, "") for k in fieldnames})

    available = sum(1 for r in results if r["whois_status"] == "available")
    registered = sum(1 for r in results if r["whois_status"] == "registered")
    print(f"\nRDAP confirmed available: {available}/{len(results)}")
    print(f"RDAP confirmed registered: {registered}/{len(results)}")
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
