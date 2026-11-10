"""Steps 2.4 and 2.8 - Deterministic quality check of the scenarios (no AI involved).

Checks every scenario in scenarios/*.yaml against the gap catalogue, the action vocabulary, the role
sheets, the mandate table and the precedent table, plus the hackathon requirements on information
(progressive, incomplete, uneven). Exit code 1 if any error.

Usage:  python -m alerte.scenario.validate
"""
from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
SCN = ROOT / "scenarios"
KNOW = ROOT / "knowledge"

CORE = {"G1", "G2", "G3", "G6", "G7", "G8", "G9"}
OUTCOMES = {"gap", "partial", "covered", "not_assessable"}
STRONG = {"power", "duty"}
EVENT_KEYS = {"id", "act", "t", "source", "to", "content", "tests_action", "expected", "good_behaviour", "inspired_by"}
# personal data and real persons: honorifics followed by a capitalised name, e-mails, phone numbers
PERSON = re.compile(r"\b(M\.|Mme|Mr\.?|Mrs\.?|Dr\.?|Sheikh|Cheikh|Monsieur|Madame)\s+[A-Z][a-z]+")
CONTACT = re.compile(r"[\w.]+@[\w.]+\.\w+|\+?\d[\d \-]{8,}\d")
REAL_OPERATORS = {"CM": re.compile(r"\b(MTN|Orange|Camtel|Nexttel)\b"),
                  "AE": re.compile(r"\b(Etisalat|e&|du)(?=\W)")}


def load_yaml(p: Path):
    return yaml.safe_load(p.read_text(encoding="utf-8"))


def minutes(t: str) -> int:
    m = re.fullmatch(r"D(\d+) (\d\d):(\d\d)", t)
    if not m:
        raise ValueError(t)
    d, h, mi = map(int, m.groups())
    return (d - 1) * 1440 + h * 60 + mi


def check(scn: dict, ctx: dict, errors: list, warnings: list) -> dict:
    sid, cc = scn["id"], scn["country"]
    E = lambda msg: errors.append(f"{sid}: {msg}")
    roles = set(ctx["roles"][cc]["roles"])
    if not scn.get("fictional") or not scn.get("banner"):
        E("missing fictional flag or banner")
    if scn.get("reviewed_by", "pending") == "pending":
        warnings.append(f"{sid}: not yet reviewed by a second team member (step 2.8)")
    last, received, tested = -1, {r: 0 for r in roles}, {}
    ids = {e["id"] for e in scn["events"]}
    hs = ctx["hydrosense"]["validity_condition"]
    for e in scn["events"]:
        eid = e.get("id", "?")
        missing = EVENT_KEYS - e.keys()
        if missing:
            E(f"{eid} missing fields {sorted(missing)}")
            continue
        t = minutes(e["t"])
        if t <= last:
            E(f"{eid} time {e['t']} not after previous event")
        last = t
        bad = set(e["to"]) - roles
        if bad:
            E(f"{eid} unknown recipients {sorted(bad)}")
        for r in set(e["to"]) & roles:
            received[r] += 1
        act = e["tests_action"]
        if act not in ctx["actions"]:
            E(f"{eid} unknown action {act}")
        if e["inspired_by"] != "fictional" and e["inspired_by"] not in ctx["manifest"]:
            E(f"{eid} inspired_by {e['inspired_by']} not in manifest")
        if "contradicts" in e and e["contradicts"] not in ids:
            E(f"{eid} contradicts unknown event {e['contradicts']}")
        text = " ".join(str(e[k]) for k in ("content", "good_behaviour"))
        if PERSON.search(text) or CONTACT.search(text):
            E(f"{eid} looks like a real person or personal data")
        if REAL_OPERATORS[cc].search(text):
            E(f"{eid} names a real operator (operators must be fictional)")
        if "hydrosense" in e:
            h = e["hydrosense"]
            valid = h["sensors_active"] >= hs["min_sensors_active"] and h["data_age_min"] <= hs["max_data_age_min"]
            if valid != h["validity_met"]:
                E(f"{eid} validity_met={h['validity_met']} but the card's condition gives {valid}")
            if not valid and not any(x["gap"] == "G8" for x in e["expected"]):
                E(f"{eid} HydroSense outside validity but G8 not expected")
        for x in e["expected"]:
            g, out = x["gap"], x["outcome"]
            if g not in ctx["gaps"]:
                E(f"{eid} unknown gap {g}")
                continue
            if out not in OUTCOMES:
                E(f"{eid} {g} bad outcome {out}")
            gap_actions = set(ctx["gaps"][g]["actions"])
            xact = x.get("action", act)  # a secondary gap names the action it concerns
            if xact not in ctx["actions"]:
                E(f"{eid} {g} unknown action {xact}")
            if xact not in gap_actions and g != "G8":
                E(f"{eid} {g} does not concern the action {xact}")
            refs = []
            for m in x["law_refs"]:
                row = ctx["mandates"].get(m)
                if row is None:
                    E(f"{eid} {g} unknown mandate row {m}")
                elif row["country"] != cc:
                    E(f"{eid} {g} mandate row {m} is for {row['country']}")
                else:
                    refs.append(row)
            for p in x["precedents"]:
                pr = ctx["precedents"].get(p)
                if pr is None:
                    E(f"{eid} {g} unknown precedent {p}")
                elif pr["gap"] != g:
                    warnings.append(f"{sid}: {eid} {g} cites precedent {p} filed under {pr['gap']}")
            strong = [r for r in refs if r["action"] in gap_actions and r["kind"] in STRONG and r["evidence"] == "documented"]
            if out == "gap" and strong:
                E(f"{eid} {g} outcome gap but {strong[0]['id']} is a documented {strong[0]['kind']}")
            if out == "covered" and not strong:
                E(f"{eid} {g} outcome covered with no documented power or duty")
            if out == "not_assessable" and not any(re.search(r"not (found|accessible|obtained)", r["note"]) for r in refs):
                E(f"{eid} {g} not_assessable but no cited row records a missing text")
            if out == "partial" and not any(r["kind"] in ("partial", "prohibition", "power", "duty") for r in refs):
                E(f"{eid} {g} outcome partial with no partial, prohibition or power row")
            if not e.get("optional"):
                tested.setdefault(g, []).append((eid, out))
    core = [e for e in scn["events"] if not e.get("optional")]
    if len(core) != 12:
        E(f"{len(core)} core events, 12 expected")
    if {e["act"] for e in core} != {1, 2}:
        E("core events must cover acts 1 and 2")
    full = [r for r, n in received.items() if n == len(scn["events"])]
    if full:
        E(f"role(s) {full} receive every event: information must be uneven")
    silent = [r for r, n in received.items() if n == 0]
    if silent:
        E(f"role(s) {silent} receive no event")
    if not any("contradicts" in e for e in scn["events"]):
        E("no contradictory information")
    missing_core = CORE - tested.keys()
    if missing_core:
        E(f"core gaps not tested: {sorted(missing_core)}")
    return {"id": sid, "country": cc, "received": received, "tested": tested,
            "signature": [(e["id"], e["act"], e["tests_action"]) for e in scn["events"]]}


def main() -> int:
    ctx = {
        "gaps": load_yaml(SCN / "gaps.yaml"),
        "actions": load_yaml(KNOW / "actions.yaml"),
        "hydrosense": load_yaml(SCN / "hydrosense.yaml"),
        "roles": {p.stem: load_yaml(p) for p in (SCN / "roles").glob("*.yaml")},
        "mandates": {r["id"]: r for r in csv.DictReader(open(KNOW / "mandates.csv", encoding="utf-8"))},
        "precedents": {r["id"]: r for r in csv.DictReader(open(KNOW / "precedents.csv", encoding="utf-8"))},
        "manifest": {r["id"] for r in csv.DictReader(open(KNOW / "manifest.csv", encoding="utf-8"))},
    }
    errors, warnings, results = [], [], []
    for cc, rs in ctx["roles"].items():  # role sheets: every mandate cited must exist and match
        for name, r in rs["roles"].items():
            for a in r["actions"]:
                row = ctx["mandates"].get(a["mandate"])
                if row is None or row["country"] != cc or row["action"] != a["action"] or row["kind"] != a["kind"]:
                    errors.append(f"roles/{cc}: {name} {a['mandate']} does not match the mandate table")
    for p in sorted(SCN.glob("[A-Z][A-Z]-*.yaml")):
        results.append(check(load_yaml(p), ctx, errors, warnings))
    if len(results) >= 2:  # same structure in every country (step 2.3)
        sigs = {r["id"]: r["signature"] for r in results}
        first = next(iter(sigs.values()))
        for sid, s in sigs.items():
            if s != first:
                errors.append(f"{sid}: structure differs from the other scenario (ids, acts or actions)")
    for r in results:
        print(f"{r['id']} ({r['country']}): {len(r['signature'])} events")
        print("  events received per role: " + ", ".join(f"{k} {v}" for k, v in sorted(r["received"].items())))
        for g in sorted(r["tested"], key=lambda g: int(g[1:])):
            outs = sorted({o for _, o in r["tested"][g]})
            print(f"  {g}: tested by {', '.join(e for e, _ in r['tested'][g])} -> {'/'.join(outs)}")
    for w in warnings:
        print("WARNING", w)
    for e in errors:
        print("ERROR", e)
    print(f"{len(errors)} error(s), {len(warnings)} warning(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
