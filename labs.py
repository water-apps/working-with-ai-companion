#!/usr/bin/env python3
"""Reader companion for "Working With AI: A Practical Guide to Getting More Done".

Local, deterministic exercises. Standard library only. Python 3.10 or later.
Nothing here connects to a work system, calls an AI model, schedules itself or
sends a message. All data is fictional.

Commands
  costs                      Practice 2: monthly cost change from data/costs.csv
  state [--file F]           Practice 3: missing-link comparison, no files written
  coverage [--fixed]         Practice 5: expected items vs completion ledger
  report [--work DIR]        Chapter 15: weekly report with a run ledger
  search --user U [--on D] Q Chapter 16: permission-filtered document retrieval
  roi                        Chapter 17: measured-value worksheet from data/roi.csv

Exit codes: 0 pass or created; 2 a check failed or the run stopped for review.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import os
import re
import sqlite3
import sys
from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"


# ----------------------------------------------------------------------------
# Practice 2: costs
# ----------------------------------------------------------------------------
def load_costs(path: Path = DATA / "costs.csv") -> list[dict]:
    with path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        r["cost_usd"] = Decimal(r["cost_usd"])
    return rows


def cost_summary(rows: list[dict]) -> dict:
    """Aggregate first, then compare. Never join individual rows by service name."""
    by = defaultdict(lambda: defaultdict(Decimal))
    for r in rows:
        by[r["month"]][r["service"]] += r["cost_usd"]
    months = sorted(by)
    if len(months) != 2:
        raise ValueError(f"expected exactly two months, found {months}")
    m0, m1 = months
    services = sorted(set(by[m0]) | set(by[m1]))
    lines = []
    for s in services:
        a, b = by[m0].get(s, Decimal(0)), by[m1].get(s, Decimal(0))
        lines.append({"service": s, m0: a, m1: b, "change": b - a})
    t0, t1 = sum(by[m0].values()), sum(by[m1].values())
    pct = (t1 - t0) / t0 * 100 if t0 else None
    return {"months": (m0, m1), "rows_read": len(rows), "services": lines,
            "total": {m0: t0, m1: t1, "change": t1 - t0, "pct": pct}}


def cmd_costs(args) -> int:
    s = cost_summary(load_costs())
    m0, m1 = s["months"]
    print(f"rows read: {s['rows_read']}")
    print(f"{'service':<10}{m0:>10}{m1:>10}{'change':>10}")
    for r in s["services"]:
        print(f"{r['service']:<10}{r[m0]:>10}{r[m1]:>10}{r['change']:>+10}")
    t = s["total"]
    pct = t["pct"].quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    print(f"{'total':<10}{t[m0]:>10}{t[m1]:>10}{t['change']:>+10}")
    print(f"percentage change: {pct}%")
    print("These totals do not establish the cause of the change.")
    return 0


# ----------------------------------------------------------------------------
# Practice 3: state
# ----------------------------------------------------------------------------
def state_plan(fixture: dict) -> dict:
    """Compare inventory, tracked mapping and expected mapping.

    Returns a plan of link_existing actions, or a stop when a tracked address
    points at a resource other than the expected one. Reads only; writes nothing.
    """
    inventory = set(fixture["inventory"])
    tracked = fixture["tracked_mapping"]
    expected = fixture["expected_mapping"]
    conflicts, actions, missing_resources = [], [], []
    for address, resource in expected.items():
        if address in tracked:
            if tracked[address] != resource:
                conflicts.append({"address": address, "tracked": tracked[address], "expected": resource})
            continue
        if resource in inventory:
            actions.append({"action": "link_existing", "address": address, "resource": resource})
        else:
            missing_resources.append({"address": address, "resource": resource})
    status = "stop_for_review" if conflicts else "plan"
    return {"status": status, "actions": actions, "conflicts": conflicts,
            "missing_resources": missing_resources, "cloud_changes": 0}


def cmd_state(args) -> int:
    fixture = json.loads(Path(args.file).read_text(encoding="utf-8"))
    plan = state_plan(fixture)
    print(json.dumps(plan, indent=2))
    if plan["status"] == "stop_for_review":
        print("STOP: a tracked address points at a different resource than expected. Review before changing anything.")
        return 2
    return 0


# ----------------------------------------------------------------------------
# Practice 5: coverage
# ----------------------------------------------------------------------------
def coverage_check(expected: list[str], ledger: list[dict]) -> dict:
    seen = defaultdict(list)
    for e in ledger:
        seen[e["item"]].append(e)
    duplicates = sorted(k for k, v in seen.items() if len(v) > 1)
    unexpected = sorted(k for k in seen if k not in expected)
    missing = [i for i in expected if i not in seen]
    failed = sorted(k for k, v in seen.items() if any(e.get("status") == "failed" for e in v))
    skipped_without_reason = sorted(k for k, v in seen.items()
                                    if any(e.get("status") == "skipped" and not e.get("reason") for e in v))
    ok = not (missing or duplicates or unexpected or failed or skipped_without_reason)
    return {"expected": len(expected), "recorded": len(ledger), "missing": missing, "failed": failed,
            "duplicates": duplicates, "unexpected": unexpected,
            "skipped_without_reason": skipped_without_reason, "pass": ok}


def cmd_coverage(args) -> int:
    expected = json.loads((DATA / "coverage_expected.json").read_text(encoding="utf-8"))
    name = "coverage_ledger_fixed.json" if args.fixed else "coverage_ledger_incomplete.json"
    ledger = json.loads((DATA / name).read_text(encoding="utf-8"))
    result = coverage_check(expected, ledger)
    print(json.dumps(result, indent=2))
    if not result["pass"]:
        print("FAIL: incomplete coverage")
        return 2
    print("PASS: every expected item is accounted for. This does not mean every copy succeeded.")
    return 0


# ----------------------------------------------------------------------------
# Chapter 15: report
# ----------------------------------------------------------------------------
def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_report(manifest: dict, tickets: list[dict]) -> str:
    start = dt.date.fromisoformat(manifest["period_start"])
    end = dt.date.fromisoformat(manifest["period_end_exclusive"])
    src = manifest["source"]
    completed = [t for t in tickets if t["status"] == "completed" and t["completed_on"]
                 and start <= dt.date.fromisoformat(t["completed_on"]) < end]
    open_now = [t for t in tickets if t["status"] == "open"]
    lines = [f"# Weekly report, team {manifest['team']}, {start} to {end} (end exclusive, {manifest['timezone']})",
             "", "DRAFT. Generated locally from a fictional fixture. A person reviews and posts this.", "",
             f"## Completed this period: {len(completed)}"]
    for t in completed:
        lines.append(f"- {t['ticket_id']}: {t['title']} (completed {t['completed_on']}; source {src})")
    lines += ["", f"## Currently open: {len(open_now)}"]
    for t in open_now:
        lines.append(f"- {t['ticket_id']}: {t['title']} (last updated {t['updated_on']}; source {src})")
    lines += ["", f"Source: {src}, {len(tickets)} rows read. Export complete flag: {manifest['export_complete']}."]
    return "\n".join(lines) + "\n"


def run_report(work: Path, manifest_path: Path = DATA / "manifest.json",
               tickets_path: Path = DATA / "tickets.csv", interrupt_after_draft: bool = False) -> dict:
    """One run of the weekly report with a durable ledger.

    States in the ledger: reserved -> drafted -> success. A rerun that finds a
    reservation without success stops instead of guessing.
    """
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not manifest.get("export_complete"):
        return {"status": "stopped_incomplete_input", "reason": "manifest says the export is not complete"}
    with tickets_path.open(newline="", encoding="utf-8") as f:
        tickets = list(csv.DictReader(f))
    work.mkdir(parents=True, exist_ok=True)
    out = work / f"report-{manifest['period_start']}.md"
    db = sqlite3.connect(work / "ledger.sqlite", timeout=5)
    db.execute("""CREATE TABLE IF NOT EXISTS runs (
        team TEXT NOT NULL, period_start TEXT NOT NULL, status TEXT NOT NULL,
        checksum TEXT, path TEXT, created_at TEXT, PRIMARY KEY (team, period_start))""")
    key = (manifest["team"], manifest["period_start"])
    row = db.execute("SELECT status, checksum FROM runs WHERE team=? AND period_start=?", key).fetchone()
    if row:
        status, checksum = row
        if status == "success":
            if out.exists() and sha256(out) != checksum:
                return {"status": "stopped_checksum_mismatch", "path": str(out),
                        "reason": "the draft was edited after it was recorded; review it, do not overwrite"}
            return {"status": "already_created", "path": str(out)}
        return {"status": "stopped_interrupted", "path": str(out),
                "reason": f"a previous run reached '{status}' and never recorded success; check the draft before retrying"}
    try:
        db.execute("INSERT INTO runs VALUES (?,?,?,?,?,?)",
                   (*key, "reserved", None, str(out), dt.datetime.now(dt.timezone.utc).isoformat()))
        db.commit()
    except sqlite3.IntegrityError:
        return {"status": "already_created", "path": str(out), "reason": "another run holds the reservation"}
    out.write_text(build_report(manifest, tickets), encoding="utf-8")
    db.execute("UPDATE runs SET status='drafted' WHERE team=? AND period_start=?", key)
    db.commit()
    if interrupt_after_draft:
        db.close()
        return {"status": "interrupted_for_test", "path": str(out)}
    db.execute("UPDATE runs SET status='success', checksum=? WHERE team=? AND period_start=?", (sha256(out), *key))
    db.commit()
    db.close()
    return {"status": "created", "path": str(out)}


def cmd_report(args) -> int:
    result = run_report(Path(args.work))
    print(json.dumps(result, indent=2))
    return 0 if result["status"] in ("created", "already_created") else 2


# ----------------------------------------------------------------------------
# Chapter 16: search
# ----------------------------------------------------------------------------
STOPWORDS = {"the", "a", "an", "is", "what", "who", "of", "for", "to", "in", "on", "and", "as"}


def _words(text: str) -> list[str]:
    return [w for w in re.findall(r"[a-z0-9]+", text.lower()) if w not in STOPWORDS]


def _effective(entry: dict, on: dt.date) -> bool:
    start = dt.date.fromisoformat(entry["effective_from"])
    end = entry["effective_to"]
    return start <= on and (end is None or on <= dt.date.fromisoformat(end))


def search(query: str, user: str, on: dt.date, catalog: list[dict], users: dict, data: Path = DATA) -> dict:
    """Filter by the user's groups first, then by approval and effective date, then match words."""
    groups = set(users.get(user, []))
    permitted = [e for e in catalog if groups & set(e["groups"])]
    authoritative = [e for e in permitted if e["approved"] and _effective(e, on)]
    qwords = set(_words(query))
    hits = []
    for e in authoritative:
        text = (data / e["file"]).read_text(encoding="utf-8")
        best, best_line = 0, None
        for line in text.splitlines():
            score = len(qwords & set(_words(line)))
            if score > best:
                best, best_line = score, line.strip()
        if best * 2 > len(qwords):  # a majority of the query words must appear on one line
            hits.append({"id": e["id"], "family": e["family"], "version": e["version"], "owner": e["owner"],
                         "score": best, "quote": best_line})
    hits.sort(key=lambda h: -h["score"])
    if not hits:
        return {"status": "no_supported_answer", "as_of": on.isoformat(), "user": user, "sources": []}
    top_family = hits[0]["family"]
    family_hits = [h for h in hits if h["family"] == top_family and h["score"] == hits[0]["score"]]
    if len(family_hits) > 1:
        return {"status": "conflict", "as_of": on.isoformat(), "user": user, "sources": family_hits,
                "message": f"Two approved sources in the '{top_family}' family are both in force and disagree. "
                           f"Ask the owners ({', '.join(sorted({h['owner'] for h in family_hits}))}) to resolve it."}
    return {"status": "answer", "as_of": on.isoformat(), "user": user, "sources": [hits[0]]}


def cmd_search(args) -> int:
    catalog = json.loads((DATA / "catalog.json").read_text(encoding="utf-8"))
    users = {k: v for k, v in json.loads((DATA / "demo_users.json").read_text(encoding="utf-8")).items() if k != "note"}
    on = dt.date.fromisoformat(args.on) if args.on else dt.date.today()
    if args.user not in users:
        print(f"unknown demo user {args.user!r}; known: {', '.join(users)}")
        return 2
    result = search(" ".join(args.query), args.user, on, catalog, users)
    print(json.dumps(result, indent=2))
    if result["status"] == "no_supported_answer":
        print("No supported answer found in the sources you may access.")
    return 0


# ----------------------------------------------------------------------------
# Chapter 17: roi
# ----------------------------------------------------------------------------
def roi_rows(path: Path = DATA / "roi.csv") -> list[dict]:
    with path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    out = []
    for r in rows:
        d = {k: Decimal(v) for k, v in r.items() if k != "task"}
        minutes_saved = (d["manual_minutes_per_run"] - d["human_minutes_with_ai_per_run"]) * d["runs_per_month"] \
            - d["maintenance_minutes_per_month"]
        hours_saved = minutes_saved / 60
        net = hours_saved * d["hourly_value"] - d["tool_cost_per_month"]
        out.append({"task": r["task"], "minutes_saved": minutes_saved, "hours_saved": hours_saved, "net_value": net})
    return out


def cmd_roi(args) -> int:
    q = lambda x: x.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    print(f"{'task':<20}{'min saved':>12}{'hours saved':>13}{'net value $':>13}")
    for r in roi_rows():
        print(f"{r['task']:<20}{r['minutes_saved']:>12}{q(r['hours_saved']):>13}{q(r['net_value']):>13}")
    print("A negative row is a result, not an error: that task got slower with AI.")
    return 0


# ----------------------------------------------------------------------------
def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("costs").set_defaults(fn=cmd_costs)
    s = sub.add_parser("state"); s.add_argument("--file", default=str(DATA / "state_simulation.json")); s.set_defaults(fn=cmd_state)
    s = sub.add_parser("coverage"); s.add_argument("--fixed", action="store_true"); s.set_defaults(fn=cmd_coverage)
    s = sub.add_parser("report"); s.add_argument("--work", default="work"); s.set_defaults(fn=cmd_report)
    s = sub.add_parser("search"); s.add_argument("--user", required=True); s.add_argument("--on")
    s.add_argument("query", nargs="+"); s.set_defaults(fn=cmd_search)
    sub.add_parser("roi").set_defaults(fn=cmd_roi)
    args = p.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
