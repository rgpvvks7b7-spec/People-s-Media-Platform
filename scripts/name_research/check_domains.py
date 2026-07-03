#!/usr/bin/env python3
"""Check .com domain availability via DNS NS lookup (parallel)."""

from __future__ import annotations

import csv
import json
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

PARKING_NS_MARKERS = (
    "afternic",
    "hugedomains",
    "namebright",
    "sedo",
    "dan.com",
    "above.com",
    "bodis",
    "domaincontrol.com/for-sale",
    "squadhelp",
    "atom.com",
    "namefind",
)


def dig_ns(domain: str) -> tuple[str, str, bool]:
    """Return (dns_status, ns_or_registrar_hint, parking_detected)."""
    try:
        result = subprocess.run(
            ["dig", "+short", "NS", domain],
            capture_output=True,
            text=True,
            timeout=8,
        )
        ns_records = [line.strip().lower() for line in result.stdout.splitlines() if line.strip()]
        if not ns_records:
            # Also check A record for parked domains without NS yet
            a_result = subprocess.run(
                ["dig", "+short", "A", domain],
                capture_output=True,
                text=True,
                timeout=8,
            )
            a_records = [line.strip() for line in a_result.stdout.splitlines() if line.strip()]
            if a_records:
                return "parked_or_active_no_ns", a_records[0], True
            return "likely_available", "", False

        ns_joined = " ".join(ns_records)
        parking = any(marker in ns_joined for marker in PARKING_NS_MARKERS)
        status = "taken_parked" if parking else "taken"
        return status, ns_records[0], parking
    except subprocess.TimeoutExpired:
        return "timeout", "", False
    except Exception as exc:  # noqa: BLE001
        return "error", str(exc), False


def load_candidates(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return data["candidates"]


def main() -> None:
    base = Path(__file__).resolve().parent
    candidates_path = base / "candidates.json"
    if not candidates_path.exists():
        raise SystemExit("Run generate_names.py first")

    candidates = load_candidates(candidates_path)
    domains = [c["domain"] for c in candidates]
    name_by_domain = {c["domain"]: c["name"] for c in candidates}

    results: dict[str, dict] = {}
    workers = min(40, max(8, len(domains) // 20))

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(dig_ns, d): d for d in domains}
        done = 0
        for fut in as_completed(futures):
            domain = futures[fut]
            dns_status, hint, parking = fut.result()
            results[domain] = {
                "name": name_by_domain[domain],
                "domain": domain,
                "dns_status": dns_status,
                "registrar_hint": hint,
                "parking_detected": parking,
                "whois_status": "pending",
            }
            done += 1
            if done % 100 == 0:
                print(f"Checked {done}/{len(domains)}...")

    available = [r for r in results.values() if r["dns_status"] == "likely_available"]
    taken = [r for r in results.values() if r["dns_status"].startswith("taken")]
    print(f"\nTotal: {len(results)} | Available: {len(available)} | Taken: {len(taken)}")

    csv_path = base / "availability_report.csv"
    fieldnames = ["name", "domain", "dns_status", "whois_status", "parking_detected", "registrar_hint"]
    with csv_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in sorted(results.values(), key=lambda r: (r["dns_status"], r["name"])):
            writer.writerow({k: row[k] for k in fieldnames})

    summary_path = base / "availability_summary.json"
    summary_path.write_text(
        json.dumps(
            {
                "total": len(results),
                "available_count": len(available),
                "taken_count": len(taken),
                "available": sorted([r["name"] for r in available]),
                "taken_parked": sorted(
                    [r["name"] for r in results.values() if r["dns_status"] == "taken_parked"]
                ),
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"Wrote {csv_path}")
    print(f"Wrote {summary_path}")


if __name__ == "__main__":
    main()
