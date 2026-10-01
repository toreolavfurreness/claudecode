#!/usr/bin/env python3
# GENERERT av /setup fra loop.config.yaml — IKKE rediger her.
# Endre loop.config.yaml og kjør /setup på nytt.
"""tasks/decision-level.py — klassifiserer koordinator-hendelser til nivå A
(spør mennesket, loopen stopper) eller nivå B (koordinatoren bestemmer selv,
logger, mennesket kan vetoe) — TODO 246.

Leser IKKE loop.config.yaml ved kjøring. `CAP`/`EXTRA_ALLOWED` og regeltabellene
under er FROSSET tekst, ikke substituert av /setup (i motsetning til
review-lens-select.py/review-severity-floor.py) — men fila følger samme
GENERERT-kontrakt som resten av kit-et: rediger templaten
(`v3-agent-orchestrator/templates/tasks/decision-level.py`), ikke denne fila,
og kjør /setup på nytt. `{{PROD_ENV_ID}}`/`{{PROD_BRANCH}}`/`{{DEV_ENV_ID}}`/
`{{RELEASE_COMMAND}}` i trigger-tekstene under ER ekte substitusjonstokens —
disse fire gjør V12 (idempotens) og V13 (V-DRY) substitusjons-BEVISSTE, ikke
trivielt sanne (lesson 2026-09-02, workflow-process-sep2026.md).

Regeltabellen (A1-A8 + B1-B7) og rundetak-vakten under er én kilde i KODE.
Den andre kilden er PROSA i `docs/superpowers/loop/coordinator-runbook.md`
§ Pausepunkter — de to holdes i paritet av `--dump-rules` + V7
(engangs i PR-en, STÅENDE som Del D2 i hver helsesjekk).

Kjøres av koordinatoren OG av implementeren (samme mønster som
review-severity-floor.py/review-lens-select.py) — ALDRI av kode-revieweren,
som er read-only uten python3 i Bash-allowlisten (M10, TODO 246 plan §3.4).

Bruk:
    python3 tasks/decision-level.py --event <navn> [--context k=v]...
    python3 tasks/decision-level.py --dump-rules
    python3 tasks/decision-level.py --self-test

`--event`/`--context` skriver JSON på stdout:
    {"level": "A"|"B", "rule": "B1", "trigger": "...", "obligations": [...], "violations": [...]}

`rule` er `"A0"` når klassifiseringen feiler høyt (ukjent hendelse, manglende
påkrevd kontekst, eller rundetak overskredet) — DA er `level` alltid `"A"`,
`trigger` er `None`, og exit-koden er != 0. Et ikke-klassifiserbart valg blir
ALDRI stilltiende et B-valg (fail-closed). For alle andre resultater
(inkludert legitime A1-A8-treff, som bare betyr «spør mennesket», ikke et
kontraktbrudd) er exit-koden 0.

`--dump-rules` skriver TSV (`id<TAB>level<TAB>trigger`) for alle 15 radene
(A1-A8, B1-B7) i den rekkefølgen de er definert under — brukt av V7/Del D2 for
å avstemme mot runbook-prosaen.

`--self-test` kjører de 30 frosne fixturene (§3.5 i planen) og skriver
`<N>/<total>` + PASS/FEIL per fixture til stderr, JSON-sammendrag til stdout.
Exit 0 kun hvis alle fixturer besto.
"""
import argparse
import json
import sys

# Rundetak: taket er 2, frosset fra runbook-templaten (§4: "Etter 2 runder
# uten go" / §5b: "Etter 2 runder uten at revise-gaten er tom"). EXTRA_ALLOWED
# er et FIX-RUNDE-BUDSJETT, ikke et globalt rundebudsjett — det gjelder KUN
# `action == "fix_round"` på `revise_gate_choice`-siden (se klassifiseringen
# under: en tidligere ubetinget "n > CAP + EXTRA_ALLOWED"-gren gjorde MERGE
# etter runde 4 til et menneske-spørsmål og over-fyrte på B-hendelser uten
# noe med kode-review-runder å gjøre — plan-review r2, VIKTIG-funn 3+4, rettet
# i r3). Veto-lever: å heve EXTRA_ALLOWED er en ett-tegns endring — se planens
# §0.4 for hvorfor 1 ble valgt og hvilke andre tall som må endres i tandem
# (F1b/F25b, V16c).
CAP = 2
EXTRA_ALLOWED = 1

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
    ("B1", "§5b revise-gate **etter 2/2**: én ekstra målrettet fix-runde (runde 3) vs. merge m/carry-forwards vs. stopp — og de samme valgene innenfor taket"),
    ("B2", "Splitt av en todo i del-todos"),
    ("B3", "Valg eller hopp av neste todo innenfor mennesket-godkjent rekkefølge (§1)"),
    ("B4", "Pipelining: valg eller drop av B-sporet (§5c)"),
    ("B5", "Godkjenning av `technical_risk` fra **plan-rapporten** når `kind ∈ {docs_selfmod, hook_selfmod}` **og** `executable_gate = true`"),
    ("B6", "Retro-triage: hvilke retro-observasjoner som promoteres eller lukkes (§8b)"),
    ("B7", "§4 plan-review: ny revisjonsrunde vs. drop/`open` — **kun når `plan_review_rounds < 2`**"),
]
TRIGGER_BY_ID = dict(A_RULES + B_RULES)

# **Pinnet (plan-review r2, VIKTIG-funn 5): `etter 2/2` (B1) og
# `plan_review_rounds < 2` (B7) i trigger-tekstene over er PROSA for
# menneskelesere og for V7-paritet — de er IKKE en betingelse i B1/B7-
# regel-matchingen under. Rundebetingelsene bor UTELUKKENDE i rundetak-vakten.
# Uten dette skillet blir mutant M-4 (fjern hele rundetak-vakten) vakuøs på
# F11: B7 ville da selv forkastet F11 via en innebygd `< 2`-sjekk, i stedet
# for å falle gjennom til B7 og bevise at vakten faktisk var det som hindret
# den.**

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


def classify(event, ctx):
    """Returnerer (level, rule, trigger, obligations, violations).

    Evalueringsrekkefølge (§3.1, ufravikelig): rundetak-vakt →
    påkrevd-kontekst-vakt → A1..A8 → B1..B7 → A0 (fail-closed). Første treff
    vinner. Rundetak-vakten kjøres FØR alt annet, uavhengig av `event` — det
    er nøyaktig det som lukker event-navn-lekkasjen (F14: `next_todo_select`
    med `code_review_rounds=3` og uten `decision_logged` er A0, selv om
    `next_todo_select` i seg selv ikke har noen rundebetingelse).
    """
    violations = []

    # --- 1. Rundetak-vakt ---------------------------------------------------
    if "code_review_rounds" in ctx:
        try:
            n = int(ctx["code_review_rounds"])
        except (TypeError, ValueError):
            return _a0([f"code_review_rounds er ikke et heltall: {ctx['code_review_rounds']!r}"])
        # (i) decision_logged er NAVN-UAVHENGIG — gjelder enhver hendelse som
        # bærer code_review_rounds >= CAP, ikke bare revise_gate_choice.
        if n >= CAP and ctx.get("decision_logged") != "yes":
            violations.append(f"decision_logged mangler ved code_review_rounds={n}")
        # (ii) Fix-runde-budsjettet — scopet til revise_gate_choice +
        # action=fix_round (IKKE et globalt rundetak, se modul-docstringen).
        if event == "revise_gate_choice" and ctx.get("action") == "fix_round" and n >= CAP + EXTRA_ALLOWED:
            violations.append(f"code_review_extra_spent: runde {n + 1} > {CAP + EXTRA_ALLOWED}")

    if event == "plan_review_choice" and "plan_review_rounds" in ctx:
        try:
            prr = int(ctx["plan_review_rounds"])
        except (TypeError, ValueError):
            return _a0([f"plan_review_rounds er ikke et heltall: {ctx['plan_review_rounds']!r}"])
        if prr >= CAP:
            violations.append(f"plan_review_cap: plan_review_rounds={prr} >= {CAP}")

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


# --- Frosne fixtures (§3.5 i planen — 30 stk., F1..F27 + F1b/F1c/F25b) ------
FIXTURES = [
    ("F1", "revise_gate_choice", {"code_review_rounds": "2", "action": "fix_round", "decision_logged": "yes"}, "B", "B1"),
    ("F1b", "revise_gate_choice", {"code_review_rounds": "3", "action": "fix_round", "decision_logged": "yes"}, "A", "A0"),
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
    ("F15", "plan_review_choice", {"plan_review_rounds": "1", "action": "revise"}, "B", "B7"),
    ("F16", "revise_gate_choice", {"code_review_rounds": "1", "action": "fix_round"}, "B", "B1"),
    ("F17", "technical_risk", {"source": "reviewer", "kind": "hook_selfmod", "executable_gate": "yes"}, "A", "A0"),
    ("F18", "retro_triage", {}, "B", "B6"),
    ("F19", "pipeline_b_select", {}, "B", "B4"),
    ("F20", "secrets_change", {}, "A", "A2"),
    ("F21", "native_build", {}, "A", "A3"),
    ("F22", "main_push", {}, "A", "A4"),
    ("F23", "destructive_op", {}, "A", "A5"),
    ("F24", "revise_gate_choice", {"action": "fix_round"}, "A", "A0"),
    # F25/F25b: plan-review r2 VIKTIG-funn 4 — extra_allowed er et
    # FIX-RUNDE-budsjett, ikke et globalt rundebudsjett. F25 (merge_carry ved
    # crr=4) er derfor B1 (lukking er alltid B, uansett rundetall); kun et
    # NYTT fix_round-forsøk utover budsjettet (F25b) er A0.
    ("F25", "revise_gate_choice", {"code_review_rounds": "4", "action": "merge_carry", "decision_logged": "yes"}, "B", "B1"),
    ("F25b", "revise_gate_choice", {"code_review_rounds": "4", "action": "fix_round", "decision_logged": "yes"}, "A", "A0"),
    ("F26", "revise_gate_choice", {"code_review_rounds": "2", "action": "merge_carry", "decision_logged": "yes"}, "B", "B1"),
    # F27: plan-review r2 VIKTIG-funn 3 — et ikke-gate-B-valg (todo_split) som
    # ÆRLIG bærer code_review_rounds-kontekst skal IKKE fanges av
    # fix-runde-taket (det taket er scopet til revise_gate_choice alene).
    # decision_logged=yes er likevel PÅKREVD her (navn-uavhengig, VIKTIG-funn
    # 3 punkt (i)) — uten den ville F27 vært A0 på manglende loggplikt, ikke
    # på det scopede taket.
    ("F27", "todo_split", {"code_review_rounds": "4", "decision_logged": "yes"}, "B", "B2"),
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
    ap.add_argument("--self-test", action="store_true", help="Kjør de 30 frosne fixturene.")
    args = ap.parse_args()

    if args.dump_rules:
        run_dump_rules()
        return

    if args.self_test:
        ok = run_self_test()
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
