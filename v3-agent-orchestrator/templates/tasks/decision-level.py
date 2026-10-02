#!/usr/bin/env python3
# GENERERT av /setup fra loop.config.yaml — IKKE rediger her.
# Endre loop.config.yaml og kjør /setup på nytt.
"""tasks/decision-level.py — klassifiserer koordinator-hendelser til nivå A
(spør mennesket, loopen stopper) eller nivå B (koordinatoren bestemmer selv,
logger, mennesket kan vetoe) — TODO 246.

Leser IKKE loop.config.yaml ved kjøring. `CAP` og regeltabellene
under er FROSSET tekst, ikke substituert av /setup (i motsetning til
review-lens-select.py/review-severity-floor.py) — men fila følger samme
GENERERT-kontrakt som resten av kit-et: rediger templaten
(`v3-agent-orchestrator/templates/tasks/decision-level.py`), ikke denne fila,
og kjør /setup på nytt. `{{PROD_ENV_ID}}`/`{{PROD_BRANCH}}`/`{{DEV_ENV_ID}}`/
`{{RELEASE_COMMAND}}` i trigger-tekstene under ER ekte substitusjonstokens —
disse fire gjør V12 (idempotens) og V13 (V-DRY) substitusjons-BEVISSTE, ikke
trivielt sanne (lesson 2026-09-02, tasks/lessons/workflow-process/).

Regeltabellen (A1-A8 + B1-B7) og konvergensvakten under er én kilde i KODE.
Den andre kilden er PROSA i `docs/superpowers/loop/coordinator-runbook.md`
§ Pausepunkter og § Konvergensregel — de to holdes i paritet av
`--dump-rules` + Del D2 i hver helsesjekk.

Kjøres av koordinatoren OG av implementeren (samme mønster som
review-severity-floor.py/review-lens-select.py) — ALDRI av kode-revieweren,
som er read-only uten python3 i Bash-allowlisten (M10, TODO 246 plan §3.4).

Bruk:
    python3 tasks/decision-level.py --event <navn> [--context k=v]...
    python3 tasks/decision-level.py --dump-rules
    python3 tasks/decision-level.py --self-test
    python3 tasks/decision-level.py --agreement [--log <sti>]
    python3 tasks/decision-level.py --recent-b [--hours 24] [--log <sti>]

`--event`/`--context` skriver JSON på stdout:
    {"level": "A"|"B", "rule": "B1", "trigger": "...", "obligations": [...], "violations": [...]}

`rule` er `"A0"` når klassifiseringen feiler høyt (ukjent hendelse, manglende
påkrevd kontekst, manglende konvergens eller kostnadsbrems) — DA er `level` alltid `"A"`,
`trigger` er `None`, og exit-koden er != 0. Et ikke-klassifiserbart valg blir
ALDRI stilltiende et B-valg (fail-closed). For alle andre resultater
(inkludert legitime A1-A8-treff, som bare betyr «spør mennesket», ikke et
kontraktbrudd) er exit-koden 0.

`--dump-rules` skriver TSV (`id<TAB>level<TAB>trigger`) for alle 15 radene
(A1-A8, B1-B7) i den rekkefølgen de er definert under — brukt av V7/Del D2 for
å avstemme mot runbook-prosaen.

`--self-test` kjører fixturene og skriver `<N>/<total>` + PASS/FEIL per
fixture til stderr, JSON-sammendrag til stdout, og deretter logg-parser-testen
(`logg-parser: PASS|FEIL`). Exit 0 kun hvis begge besto.

`--agreement` skriver TSV `type n fulgt avvek forslag` over nivå A-entries med
`Eierens svar:` i decision-log (TODO 455). `--recent-b` skriver JSON-objekt
`{"entries": [...], "unparsed": N}`: `entries` er nivå B-entries fra de siste `--hours`
timene; `unparsed` teller `### `-linjer under markøren som ikke følger
`### YYYY-MM-DD HH:MM — …` og hvis første dato er innenfor samme vindu (linjer uten
dato telles alltid) — de er usynlige for begge kommandoene. Begge: exit 2 hvis loggen ikke
kan leses eller markøren mangler.
"""
import argparse
import json
import re
import sys
from datetime import datetime, timedelta

# CAP markerer første runde som har en forrige runde å sammenligne med
# (konvergensdata kreves fra runde 2), og terskelen for decision_logged.
# Fast rundetak (fjernet i TODO 455): antall runder begrenses nå av at
# gate-funnene må gå ned for hver runde, pluss kostnadsbremsen.
CAP = 2

# --- Regeltabellen (frossen prosa, én kilde i kode) -------------------------
# Trigger-tekstene er ORDRETT identiske med tabellene i runbook-templatens
# § Pausepunkter (TODO 246 plan §3.1) — V7/Del D2 avstemmer de to. IKKE
# reformuler den ene uten den andre.
A_RULES = [
    ("A1", "Skriving mot prod-miljøet (`{{PROD_ENV_ID}}`) eller kjøring av `{{RELEASE_COMMAND}}`"),
    ("A2", "Env-variabler, secrets eller vault"),
    ("A3", "Native/EAS-bygg, TestFlight-distribusjon eller iOS-Modal-endring"),
    ("A4", "Push eller merge til `{{PROD_BRANCH}}`"),
    ("A5", "Destruktiv eller irreversibel operasjon (datasletting, force-push, drop)"),
    ("A6", "Avvik fra `CLAUDE.md` eller `docs/naming-conventions.md` som krever menneskets bekreftelse"),
    ("A7", "Apply av migrasjon eller RLS-endring mot dev (`{{DEV_ENV_ID}}`)"),
    ("A8", "Edge Function-deploy (dev eller prod)"),
]
B_RULES = [
    ("B1", "§5b revise-gate: ny fix-runde (fra runde 2 kun ved konvergens) vs. merge m/carry-forwards vs. stopp — alle runder under kostnadstaket"),
    ("B2", "Splitt av en todo i del-todos"),
    ("B3", "Valg eller hopp av neste todo innenfor mennesket-godkjent rekkefølge (§1)"),
    ("B4", "Pipelining: valg eller drop av B-sporet (§5c)"),
    ("B5", "Godkjenning av `technical_risk` fra **plan-rapporten** når `kind ∈ {docs_selfmod, hook_selfmod}` **og** `executable_gate = true`"),
    ("B6", "Retro-triage: hvilke retro-observasjoner som promoteres eller lukkes (§8b)"),
    ("B7", "§4 plan-review: ny revisjonsrunde (fra runde 2 kun ved konvergens) vs. drop/`open` — alle runder under kostnadstaket"),
]
TRIGGER_BY_ID = dict(A_RULES + B_RULES)

# Rundebetingelsene i B1/B7-teksten er PROSA. Konvergens og kostnadsbrems
# bor UTELUKKENDE i vakt 1 (_convergence), ikke i B1/B7-matchingen.

# --- Påkrevd kontekst per hendelsesklasse -----------------------------------
# `technical_risk` med `source == "planner"` krever i TILLEGG `kind` og
# `executable_gate` — håndtert som spesialtilfelle i classify(), ikke her,
# fordi kravet er BETINGET på en annen kontekstverdi.
REQUIRED_CONTEXT = {
    "revise_gate_choice": ["code_review_rounds", "action"],
    "plan_review_choice": ["plan_review_rounds", "action"],
    "technical_risk": ["source"],
    "migration_apply": ["env"],
}

TRUE_STRINGS = {"yes", "true", "1"}


def truthy(v):
    return isinstance(v, str) and v.lower() in TRUE_STRINGS


def obligations_for(rule_id):
    """De fire logg-pliktene (§3.2) for et B-valg, eller menneske-spørring for A."""
    if rule_id.startswith("B"):
        return [
            "Decision-log-entry i frosset format (docs/superpowers/loop/decision-log.md § Format).",
            "auto_decided=<rad-eier>:<antall> i run-log.md felt 11, ved siden av selector=/floor=/pipelined_from=.",
            f"Én linje i sluttmeldingen: '{rule_id} — <kort valg> (reversibel til <punkt>; veto: svar i chatten)'.",
            "Regel-IDen er hentet fra DETTE skriptet (--event/--context), ikke fra hukommelsen.",
        ]
    return [
        "Spør mennesket eksplisitt og vent på et uttrykkelig go/no-go.",
        "Release claim (den CLAIMEDE todoens claim — aldri en pipelinet, u-claimet B, se §5c).",
    ]


def _hit(rule_id):
    level = "A" if rule_id.startswith("A") else "B"
    return level, rule_id, TRIGGER_BY_ID[rule_id], obligations_for(rule_id), []


def _a0(violations):
    return "A", "A0", None, [], violations


def _convergence(ctx, n):
    """Konvergensregelen (TODO 455). Ikke-tom liste ⇒ A0."""
    v = []
    if ctx.get("cost_over") != "no":
        v.append(f"cost_brake: cost_over={ctx.get('cost_over')!r}")
    if n >= CAP:
        try:
            prev, now = int(ctx["blocking_prev"]), int(ctx["blocking_now"])
        except (KeyError, TypeError, ValueError):
            v.append("konvergensdata mangler/ugyldig: blocking_prev/blocking_now")
        else:
            if now >= prev:
                v.append(f"no_convergence: blocking {prev}->{now}")
        if ctx.get("new_class") != "no":
            v.append(f"no_convergence: new_class={ctx.get('new_class')!r}")
        if ctx.get("content") != "no":
            v.append(f"no_convergence: content={ctx.get('content')!r}")
    return v


def classify(event, ctx):
    """Returnerer (level, rule, trigger, obligations, violations).

    Evalueringsrekkefølge (§3.1, ufravikelig): konvergensvakt →
    påkrevd-kontekst-vakt → A1..A8 → B1..B7 → A0 (fail-closed). Første treff
    vinner. Konvergensvakten kjøres FØR alt annet, uavhengig av `event` — det
    er nøyaktig det som lukker event-navn-lekkasjen (F14: `next_todo_select`
    med `code_review_rounds=3` og uten `decision_logged` er A0, selv om
    `next_todo_select` i seg selv ikke har noen rundebetingelse).
    """
    violations = []

    # --- 1. Konvergensvakt ---------------------------------------------------
    if "code_review_rounds" in ctx:
        try:
            n = int(ctx["code_review_rounds"])
        except (TypeError, ValueError):
            return _a0([f"code_review_rounds er ikke et heltall: {ctx['code_review_rounds']!r}"])
        # (i) decision_logged er NAVN-UAVHENGIG — gjelder enhver hendelse som
        # bærer code_review_rounds >= CAP, ikke bare revise_gate_choice.
        if n >= CAP and ctx.get("decision_logged") != "yes":
            violations.append(f"decision_logged mangler ved code_review_rounds={n}")
        # (ii) Konvergens + kostnadsbrems for en NY fix-runde.
        if event == "revise_gate_choice" and ctx.get("action") == "fix_round":
            violations += _convergence(ctx, n)

    if event == "plan_review_choice" and "plan_review_rounds" in ctx:
        try:
            prr = int(ctx["plan_review_rounds"])
        except (TypeError, ValueError):
            return _a0([f"plan_review_rounds er ikke et heltall: {ctx['plan_review_rounds']!r}"])
        if ctx.get("action") == "revise":
            violations += _convergence(ctx, prr)

    if violations:
        return _a0(violations)

    # --- 2. Påkrevd-kontekst-vakt --------------------------------------------
    missing = [k for k in REQUIRED_CONTEXT.get(event, []) if k not in ctx]
    if event == "technical_risk" and ctx.get("source") == "planner":
        missing += [k for k in ("kind", "executable_gate") if k not in ctx]
    if missing:
        return _a0([f"påkrevd kontekst mangler for {event!r}: {', '.join(missing)}"])

    # --- 3. A1..A8 ------------------------------------------------------------
    if event == "migration_apply" and ctx.get("env") == "prod":
        return _hit("A1")
    if event == "technical_risk" and ctx.get("source") == "planner" and ctx.get("kind") == "prod_push":
        return _hit("A1")
    if event == "secrets_change":
        return _hit("A2")
    if event == "technical_risk" and ctx.get("source") == "planner" and ctx.get("kind") == "secrets":
        return _hit("A2")
    if event == "native_build":
        return _hit("A3")
    if event == "main_push":
        return _hit("A4")
    if event == "destructive_op":
        return _hit("A5")
    if event == "naming_deviation":
        return _hit("A6")
    if event == "migration_apply" and ctx.get("env") == "dev":
        return _hit("A7")
    if event == "technical_risk" and ctx.get("source") == "planner" and ctx.get("kind") in ("migration", "rls"):
        return _hit("A7")
    if event == "edge_function_deploy":
        return _hit("A8")

    # --- 4. B1..B7 ------------------------------------------------------------
    if event == "revise_gate_choice" and ctx.get("action") in ("fix_round", "merge_carry", "stop"):
        return _hit("B1")
    if event == "todo_split":
        return _hit("B2")
    if event == "next_todo_select":
        return _hit("B3")
    if event == "pipeline_b_select":
        return _hit("B4")
    if (
        event == "technical_risk"
        and ctx.get("source") == "planner"
        and ctx.get("kind") in ("docs_selfmod", "hook_selfmod")
        and truthy(ctx.get("executable_gate"))
    ):
        return _hit("B5")
    if event == "retro_triage":
        return _hit("B6")
    if event == "plan_review_choice" and ctx.get("action") in ("revise", "drop"):
        return _hit("B7")

    # --- 5. A0 — fail-closed ----------------------------------------------
    return _a0([f"ukjent hendelse eller ingen regel treffer: event={event!r} context={ctx!r}"])


# --- Fixtures (39 stk.: F1..F36 + F1b/F1c/F25b) -----------------------------
_CONV = {"blocking_prev": "3", "blocking_now": "1", "new_class": "no", "content": "no", "cost_over": "no"}
_F28 = {"code_review_rounds": "2", "action": "fix_round", "decision_logged": "yes", **_CONV}
_F34 = {"plan_review_rounds": "2", "action": "revise", **_CONV, "blocking_prev": "2"}
FIXTURES = [
    ("F1", "revise_gate_choice", {"code_review_rounds": "2", "action": "fix_round", "decision_logged": "yes", **_CONV}, "B", "B1"),
    ("F1b", "revise_gate_choice", {"code_review_rounds": "3", "action": "fix_round", "decision_logged": "yes", **_CONV, "blocking_prev": "2", "blocking_now": "2"}, "A", "A0"),
    ("F1c", "revise_gate_choice", {"code_review_rounds": "3", "action": "merge_carry", "decision_logged": "yes"}, "B", "B1"),
    ("F2", "technical_risk", {"source": "planner", "kind": "hook_selfmod", "executable_gate": "yes"}, "B", "B5"),
    ("F3", "todo_split", {}, "B", "B2"),
    ("F4", "migration_apply", {"env": "dev"}, "A", "A7"),
    ("F5", "naming_deviation", {}, "A", "A6"),
    ("F6", "technical_risk", {"source": "planner", "kind": "migration", "executable_gate": "yes"}, "A", "A7"),
    ("F7", "technical_risk", {"source": "planner", "kind": "hook_selfmod", "executable_gate": "no"}, "A", "A0"),
    ("F8", "technical_risk", {"source": "planner", "kind": "hook_selfmod"}, "A", "A0"),
    ("F9", "hokus_pokus", {}, "A", "A0"),
    ("F10", "migration_apply", {"env": "prod"}, "A", "A1"),
    ("F11", "plan_review_choice", {"plan_review_rounds": "2", "action": "revise"}, "A", "A0"),
    ("F12", "next_todo_select", {}, "B", "B3"),
    ("F13", "edge_function_deploy", {}, "A", "A8"),
    ("F14", "next_todo_select", {"code_review_rounds": "3"}, "A", "A0"),
    ("F15", "plan_review_choice", {"plan_review_rounds": "1", "action": "revise", "cost_over": "no"}, "B", "B7"),
    ("F16", "revise_gate_choice", {"code_review_rounds": "1", "action": "fix_round", "cost_over": "no"}, "B", "B1"),
    ("F17", "technical_risk", {"source": "reviewer", "kind": "hook_selfmod", "executable_gate": "yes"}, "A", "A0"),
    ("F18", "retro_triage", {}, "B", "B6"),
    ("F19", "pipeline_b_select", {}, "B", "B4"),
    ("F20", "secrets_change", {}, "A", "A2"),
    ("F21", "native_build", {}, "A", "A3"),
    ("F22", "main_push", {}, "A", "A4"),
    ("F23", "destructive_op", {}, "A", "A5"),
    ("F24", "revise_gate_choice", {"action": "fix_round"}, "A", "A0"),
    # F25/F25b: lukking (merge_carry) er alltid B1; et NYTT fix_round-forsøk
    # uten konvergensdata (F25b) er A0.
    ("F25", "revise_gate_choice", {"code_review_rounds": "4", "action": "merge_carry", "decision_logged": "yes"}, "B", "B1"),
    ("F25b", "revise_gate_choice", {"code_review_rounds": "4", "action": "fix_round", "decision_logged": "yes"}, "A", "A0"),
    ("F26", "revise_gate_choice", {"code_review_rounds": "2", "action": "merge_carry", "decision_logged": "yes"}, "B", "B1"),
    # F27: plan-review r2 VIKTIG-funn 3 — et ikke-gate-B-valg (todo_split) som
    # ÆRLIG bærer code_review_rounds-kontekst skal IKKE fanges av
    # konvergensvakten (den er scopet til revise_gate_choice alene).
    # decision_logged=yes er likevel PÅKREVD her (navn-uavhengig, VIKTIG-funn
    # 3 punkt (i)) — uten den ville F27 vært A0 på manglende loggplikt, ikke
    # på konvergensvakten.
    ("F27", "todo_split", {"code_review_rounds": "4", "decision_logged": "yes"}, "B", "B2"),
    # F28-F36 (TODO 455): hver A0-fixture skiller seg fra F28/F34 i ÉN nøkkel.
    ("F28", "revise_gate_choice", _F28, "B", "B1"),
    ("F29", "revise_gate_choice", {**_F28, "blocking_now": "3"}, "A", "A0"),
    ("F30", "revise_gate_choice", {**_F28, "new_class": "yes"}, "A", "A0"),
    ("F31", "revise_gate_choice", {**_F28, "content": "yes"}, "A", "A0"),
    ("F32", "revise_gate_choice", {**_F28, "cost_over": "yes"}, "A", "A0"),
    ("F33", "revise_gate_choice", {"code_review_rounds": "1", "action": "fix_round", "cost_over": "yes"}, "A", "A0"),
    ("F34", "plan_review_choice", _F34, "B", "B7"),
    ("F35", "plan_review_choice", {**_F34, "blocking_prev": "1"}, "A", "A0"),
    ("F36", "revise_gate_choice", {**_F28, "code_review_rounds": "6", "blocking_prev": "2"}, "B", "B1"),
]


def run_self_test():
    total = len(FIXTURES)
    passed = 0
    results = []
    for name, event, ctx, exp_level, exp_rule in FIXTURES:
        level, rule, trigger, obligations, violations = classify(event, ctx)
        ok = (level == exp_level and rule == exp_rule)
        results.append({
            "name": name, "event": event, "context": ctx,
            "expected": {"level": exp_level, "rule": exp_rule},
            "actual": {"level": level, "rule": rule},
            "pass": ok,
        })
        status = "PASS" if ok else "FEIL"
        print(f"[decision-level --self-test] {name}: {status} (forventet {exp_level}/{exp_rule}, fikk {level}/{rule})", file=sys.stderr)
        if ok:
            passed += 1
    print(f"[decision-level --self-test] {passed}/{total}", file=sys.stderr)
    print(json.dumps({"passed": passed, "total": total, "results": results}))
    return passed == total


# --- Logg-parser (TODO 455) -------------------------------------------------
LOG_PATH = "docs/superpowers/loop/decision-log.md"
_HEADER = re.compile(r"^### (\d{4}-\d{2}-\d{2} \d{2}:\d{2}) — (.*)$")
_FIELD = re.compile(r"\*\*([^*:]+):\*\*\s*(.*)")


def parse_log(text):
    """Entries under `<!-- FORMAT-V2`-markøren. None hvis markøren mangler."""
    lines = text.splitlines()
    start = next((i for i, l in enumerate(lines) if l.startswith("<!-- FORMAT-V2")), None)
    if start is None:
        return None
    entries, cur = [], None
    for line in lines[start + 1:]:
        if line.startswith("### "):
            m = _HEADER.match(line)
            cur = {"ts": m.group(1), "header": m.group(2), "fields": {}} if m else None
            if cur:
                entries.append(cur)
            continue
        if cur is None:
            continue
        f = _FIELD.search(line.lstrip("- "))
        if f and line.lstrip("- ").startswith("**"):
            cur["fields"].setdefault(f.group(1).strip(), f.group(2).strip())
    return entries


def unparsed_headers(text, hours, now):
    """`### `-linjer under markøren som _HEADER ikke matcher, innenfor vinduet."""
    lines = text.splitlines()
    start = next((i for i, l in enumerate(lines) if l.startswith("<!-- FORMAT-V2")), len(lines))
    cutoff = (now - timedelta(hours=hours)).strftime("%Y-%m-%d")
    n = 0
    for line in lines[start + 1:]:
        if line.startswith("### ") and not _HEADER.match(line):
            d = re.search(r"\d{4}-\d{2}-\d{2}", line)
            n += d is None or d.group(0) >= cutoff
    return n


def _bracket(header):
    i = header.find("[")
    return header[i + 1:] if i >= 0 else ""


def agreement(entries):
    rows = {}
    for e in sorted(entries, key=lambda e: e["ts"]):
        svar = e["fields"].get("Eierens svar")
        if svar is None or svar.lower().startswith("venter"):
            continue
        typ = e["fields"].get("Type") or re.split(r"[,\]]", _bracket(e["header"]))[0].strip()
        rows.setdefault(typ, []).append(svar.lower().startswith("fulgt"))
    out = []
    for typ in sorted(rows):
        r = rows[typ]
        forslag = "flytt-til-B" if len(r) >= 10 and all(r[-10:]) else "-"
        out.append(f"{typ}\t{len(r)}\t{sum(r)}\t{len(r) - sum(r)}\t{forslag}")
    return out


def recent_b(entries, hours, now):
    cutoff = (now - timedelta(hours=hours)).strftime("%Y-%m-%d %H:%M")
    hits = [
        {"ts": e["ts"], "header": e["header"], "reversibel": e["fields"].get("Reversibel til", "–")}
        for e in entries
        if _bracket(e["header"]).startswith("B") and e["ts"] >= cutoff
    ]
    return sorted(hits, key=lambda h: h["ts"], reverse=True)


def _mini_log():
    def entry(ts, tag, **f):
        body = "".join(f"- **{k.replace('_', ' ')}:** {v}\n" for k, v in f.items())
        return f"### {ts} — TODO 9 [{tag}]: test\n{body}\n"
    out = "# mini\n" + entry("2026-10-02 11:30", "B1", Type="X", Eierens_svar="fulgt", Reversibel_til="x")
    out += "<!-- FORMAT-V2 (test) -->\n"
    for d in range(20, 30):
        out += entry(f"2026-09-{d} 10:00", "A0", Type="X", Eierens_svar="fulgt")
    for d in range(1, 10):
        out += entry(f"2026-09-0{d} 10:00", "A0", Type="Z", Eierens_svar="fulgt")
    out += entry("2026-09-10 10:00", "A0", Type="Y", Eierens_svar="fulgt")
    out += entry("2026-09-11 10:00", "A0", Type="Y", Eierens_svar="avvek: kutt")
    out += entry("2026-10-01 10:00", "A0", Type="X", Eierens_svar="venter")
    out += entry("2026-09-12 10:00", "A, eier", Eierens_svar="Fulgt («ja»)")
    out += entry("2026-10-02 09:00", "B1", Reversibel_til="merge")
    out += entry("2026-10-01 11:00", "B", Reversibel_til="y")
    out += entry("2026-10-02 10:00", "VETO av B1", Reversibel_til="z")
    return out


def run_parser_self_test():
    entries = parse_log(_mini_log())
    exp_agr = ["A\t1\t1\t0\t-", "X\t10\t10\t0\tflytt-til-B", "Y\t2\t1\t1\t-", "Z\t9\t9\t0\t-"]
    got_agr = agreement(entries)
    got_rb = [(h["ts"], h["reversibel"]) for h in recent_b(entries, 24, datetime(2026, 10, 2, 12, 0))]
    exp_rb = [("2026-10-02 09:00", "merge")]
    bad = "<!-- FORMAT-V2 -->\n### 2026-10-02 — [B4] uten klokke\n### 2026-09-01 — [B4] gammel\n### udatert\n"
    got_un = unparsed_headers(bad, 24, datetime(2026, 10, 2, 12, 0))
    ok = got_agr == exp_agr and got_rb == exp_rb and got_un == 2
    if got_un != 2:
        print(f"  forventet unparsed=2, faktisk {got_un}", file=sys.stderr)
    print(f"[decision-level --self-test] logg-parser: {'PASS' if ok else 'FEIL'}", file=sys.stderr)
    if not ok:
        print(f"  forventet agreement={exp_agr} recent_b={exp_rb}", file=sys.stderr)
        print(f"  faktisk   agreement={got_agr} recent_b={got_rb}", file=sys.stderr)
    return ok


def _load_entries(path):
    try:
        with open(path, encoding="utf-8") as fh:
            entries = parse_log(fh.read())
    except OSError as exc:
        print(f"FEIL: kan ikke lese {path}: {exc}", file=sys.stderr)
        sys.exit(2)
    if entries is None:
        print(f"FEIL: <!-- FORMAT-V2-markøren mangler i {path}", file=sys.stderr)
        sys.exit(2)
    return entries


def run_dump_rules():
    for rule_id, trigger in A_RULES + B_RULES:
        level = "A" if rule_id.startswith("A") else "B"
        print(f"{rule_id}\t{level}\t{trigger}")


def parse_context(pairs):
    ctx = {}
    for p in pairs or []:
        for part in p.split(","):
            if "=" not in part:
                sys.exit(f"FEIL: --context må være k=v (kommaseparert tillatt innenfor ett flagg), fikk {p!r}")
            k, v = part.split("=", 1)
            ctx[k] = v
    return ctx


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--event", help="Hendelsesnavn (f.eks. revise_gate_choice).")
    ap.add_argument("--context", action="append", help="k=v, kan gjentas (eller k1=v1,k2=v2 i ett flagg).")
    ap.add_argument("--dump-rules", action="store_true", help="Skriv TSV av alle 15 regler.")
    ap.add_argument("--self-test", action="store_true", help="Kjør fixturene og logg-parser-testen.")
    ap.add_argument("--agreement", action="store_true", help="Samsvar per type (TSV).")
    ap.add_argument("--recent-b", action="store_true", help="Nivå B-entries siste --hours timer (JSON).")
    ap.add_argument("--hours", type=float, default=24)
    ap.add_argument("--log", default=LOG_PATH)
    args = ap.parse_args()

    if args.agreement:
        print("\n".join(agreement(_load_entries(args.log))))
        return

    if args.recent_b:
        now = datetime.now()
        entries = _load_entries(args.log)  # exit 2 ved manglende fil/markør, før lesingen under
        with open(args.log, encoding="utf-8") as fh:
            unparsed = unparsed_headers(fh.read(), args.hours, now)
        print(json.dumps({"entries": recent_b(entries, args.hours, now), "unparsed": unparsed},
                         ensure_ascii=False))
        return

    if args.dump_rules:
        run_dump_rules()
        return

    if args.self_test:
        ok = run_self_test()
        ok = run_parser_self_test() and ok
        sys.exit(0 if ok else 1)

    if not args.event:
        sys.exit("FEIL: --event er påkrevd (eller bruk --dump-rules / --self-test).")

    ctx = parse_context(args.context)
    level, rule, trigger, obligations, violations = classify(args.event, ctx)
    print(json.dumps({
        "level": level,
        "rule": rule,
        "trigger": trigger,
        "obligations": obligations,
        "violations": violations,
    }))
    if rule == "A0":
        sys.exit(1)


if __name__ == "__main__":
    main()
