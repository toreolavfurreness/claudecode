#!/usr/bin/env python3
# GENERERT av /setup fra loop.config.yaml — IKKE rediger her.
# Endre loop.config.yaml og kjør /setup på nytt.
"""tasks/decision-level.py — klassifiserer koordinator-hendelser til nivå A
(spør mennesket, loopen stopper) eller nivå B (koordinatoren bestemmer selv,
logger, mennesket kan vetoe).

Leser IKKE loop.config.yaml ved kjøring. `CAP` og regeltabellene
under er FROSSET tekst, ikke substituert av /setup (i motsetning til
review-lens-select.py/review-severity-floor.py) — men fila følger samme
GENERERT-kontrakt som resten av kit-et: rediger templaten
(`v3-agent-orchestrator/templates/tasks/decision-level.py`), ikke denne fila,
og kjør /setup på nytt. `{{PROD_ENV_ID}}`/`{{PROD_BRANCH}}`/`{{DEV_ENV_ID}}`/
`{{RELEASE_COMMAND}}` i trigger-tekstene under ER ekte substitusjonstokens —
disse fire gjør V12 (idempotens) og V13 (V-DRY) substitusjons-BEVISSTE, ikke
trivielt sanne.

Regeltabellen (A1-A8 + B1-B8) og konvergensvakten under er én kilde i KODE.
Den andre kilden er PROSA i `docs/superpowers/loop/coordinator-runbook.md`
§ Pausepunkter og § Konvergensregel — de to holdes i paritet av
`--dump-rules` + Del D2 i hver helsesjekk.

Kjøres av koordinatoren OG av implementeren (samme mønster som
review-severity-floor.py/review-lens-select.py) — ALDRI av kode-revieweren,
som er read-only uten python3 i Bash-allowlisten (M10).

Bruk:
    python3 tasks/decision-level.py --event <navn> [--context k=v]... [--todo <nr>] [--title <tekst>]
    python3 tasks/decision-level.py --dump-rules
    python3 tasks/decision-level.py --self-test
    python3 tasks/decision-level.py --agreement [--log <sti>]
    python3 tasks/decision-level.py --recent-b [--hours 24] [--log <sti>]
    python3 tasks/decision-level.py --auto-decided <nr> [--log <sti>] [--run-log <sti>]
    python3 tasks/decision-level.py --reconcile [--since YYYY-MM-DDTHH:MM] [--log <sti>] [--run-log <sti>]

`--event`/`--context` skriver JSON på stdout:
    {"level": "A"|"B", "rule": "B1", "trigger": "...", "obligations": [...], "violations": [...],
     "header": "### <tid> — TODO <nr> [B1]: <tittel>", "warnings": [...]}

`header` er overskriftslinja for decision-log-oppføringen, med maskinens klokke. Den limes inn
ordrett. `warnings` sier fra når `--title` peker på en annen todo enn `--todo`.

`--auto-decided <nr>` skriver run-log-tokenet `auto_decided=<nr>:<n>`. `--reconcile` sammenligner
hver run-log-rad etter `--since` (standard: siste `health`-rad) med oppføringene som hører til
raden. Begge bruker `attribute()`: en `[B<siffer>]`-oppføring eies av første `TODO <nr>` i
overskriften og telles på eierens første rad med radtid >= oppføringstid. Exit 1 ved avvik,
manglende token eller oppføring etter en `merged`-rad, 2 når en fil ikke kan leses.

`rule` er `"A0"` når klassifiseringen feiler høyt (ukjent hendelse, manglende
påkrevd kontekst, ugyldig verdi, kostnadsbrems, manglende konvergensdata, innholdsfunn eller rundestopp i §5b) — DA er `level` alltid `"A"`,
`trigger` er `None`, og exit-koden er != 0. Et ikke-klassifiserbart valg blir
ALDRI stilltiende et B-valg (fail-closed). For alle andre resultater
(inkludert legitime A1-A8-treff, som bare betyr «spør mennesket», ikke et
kontraktbrudd) er exit-koden 0.

`--dump-rules` skriver TSV (`id<TAB>level<TAB>trigger`) for alle 16 radene
(A1-A8, B1-B8) i den rekkefølgen de er definert under — brukt av V7/Del D2 for
å avstemme mot runbook-prosaen.

`--self-test` kjører fixturene og skriver `<N>/<total>` + PASS/FEIL per
fixture til stderr, JSON-sammendrag til stdout, og deretter logg-parser-testen
(`logg-parser: PASS|FEIL`) og avstemmingstesten (`avstemming: PASS|FEIL`). Exit 0 kun hvis alle
tre besto.

`--agreement` skriver TSV `type n fulgt avvek forslag` over nivå A-entries med
`Eierens svar:` i decision-log. `flytt-til-B` foreslås bare når leddet foran kolon står i
`SLAG`, og i slaget `eiervalg` bare for kort-navnet `mekanisk`. `--recent-b` skriver JSON-objekt
`{"entries": [...], "unparsed": N}`: `entries` er nivå B-entries fra de siste `--hours`
timene; `unparsed` teller `### `-linjer under markøren som ikke følger
`### YYYY-MM-DD HH:MM …` og hvis første dato er innenfor samme vindu (linjer uten
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
# Intet fast rundetak: i §4 og §5b begrenser bare kostnadsbremsen og innholdsregelen antall runder.
# Unntak: i §5b er en ny fix-runde fra runde ROUND_STOP alltid A0.
CAP = 2
ROUND_STOP = 4

# --- Regeltabellen (frossen prosa, én kilde i kode) -------------------------
# Trigger-tekstene er ORDRETT identiske med tabellene i runbook-templatens
# § Pausepunkter — V7/Del D2 avstemmer de to. IKKE
# reformuler den ene uten den andre.
A_RULES = [
    ("A1", "Skriving mot prod-miljøet (`{{PROD_ENV_ID}}`) eller kjøring av `{{RELEASE_COMMAND}}`"),
    ("A2", "Env-variabler, secrets eller vault"),
    ("A3", "Native/EAS-bygg, TestFlight-distribusjon, eller native iOS-arbeid med ny native avhengighet eller ny tillatelse"),
    ("A4", "Push eller merge til `{{PROD_BRANCH}}`"),
    ("A5", "Destruktiv eller irreversibel operasjon (datasletting, force-push, drop)"),
    ("A6", "Avvik fra `CLAUDE.md` eller `docs/naming-conventions.md` som krever menneskets bekreftelse"),
    ("A7", "Apply av migrasjon eller RLS-endring mot dev (`{{DEV_ENV_ID}}`)"),
    ("A8", "Edge Function-deploy (dev eller prod)"),
]
B_RULES = [
    ("B1", "§5b revise-gate: ny fix-runde (fra runde 2 kun uten innholdsfunn, fra runde 4 aldri) vs. merge m/carry-forwards vs. stopp — alle runder under kostnadstaket"),
    ("B2", "Splitt av en todo i del-todos"),
    ("B3", "Valg eller hopp av neste todo innenfor mennesket-godkjent rekkefølge (§1)"),
    ("B4", "Pipelining: valg eller drop av B-sporet (§5c)"),
    ("B5", "Godkjenning av `technical_risk` fra **plan-rapporten** når `kind ∈ {docs_selfmod, hook_selfmod}` **og** `executable_gate = true`"),
    ("B6", "Retro-triage: hvilke retro-observasjoner som promoteres eller lukkes (§8b)"),
    ("B7", "§4 plan-review: ny revisjonsrunde (fra runde 2 kun uten innholdsfunn) vs. drop/`open` — alle runder under kostnadstaket"),
    ("B8", "Godkjenning av `technical_risk` fra **plan-rapporten** når `kind = native` uten ny native avhengighet og uten ny tillatelse"),
]
TRIGGER_BY_ID = dict(A_RULES + B_RULES)

# Rundebetingelsene i B1/B7-teksten er PROSA. Konvergens, innholdsregel og
# kostnadsbrems bor UTELUKKENDE i vakt 1 (_convergence), ikke i B1/B7-matchingen.
# Rundestoppet i §5b (ROUND_STOP) ligger i classify, ikke i _convergence (som deles med §4).

# --- Påkrevd kontekst per hendelsesklasse -----------------------------------
# `technical_risk` med `source == "planner"` krever i TILLEGG `kind` og
# `executable_gate` (for `kind=native`: NATIVE_KEYS i stedet) — håndtert som spesialtilfelle i classify(), ikke her,
# fordi kravet er BETINGET på en annen kontekstverdi.
REQUIRED_CONTEXT = {
    "revise_gate_choice": ["code_review_rounds", "action"],
    "plan_review_choice": ["plan_review_rounds", "action"],
    "technical_risk": ["source"],
    "migration_apply": ["env"],
}

TRUE_STRINGS = {"yes", "true", "1"}
NATIVE_KEYS = ("native_dep", "native_permission")


def truthy(v):
    return isinstance(v, str) and v.lower() in TRUE_STRINGS


def obligations_for(rule_id):
    """De fire logg-pliktene (§3.2) for et B-valg, eller menneske-spørring for A."""
    if rule_id.startswith("B"):
        return [
            "Decision-log-entry i frosset format (docs/superpowers/loop/decision-log.md § Format). "
            "Overskriften limes inn ordrett fra header-feltet i dette svaret.",
            "auto_decided=<rad-eier>:<antall> i run-log.md felt 11, limt inn ordrett fra "
            "`--auto-decided <rad-eier>`. Tallet er [B<siffer>]-oppføringene der rad-eieren står først "
            "i overskriften. `— loop`-valg uten todo står ikke på noen rad.",
            f"Én linje i sluttmeldingen: '{rule_id} — <kort valg> (reversibel til <punkt>; veto: svar i chatten)'.",
            "Regel-IDen er hentet fra DETTE skriptet (--event/--context), ikke fra hukommelsen.",
        ]
    return [
        "Spør mennesket eksplisitt, med anbefaling og konsekvens i vanlig språk, og vent på et uttrykkelig go/no-go.",
        "Release claim (den CLAIMEDE todoens claim — aldri en pipelinet, u-claimet B, se §5c).",
    ]


def _hit(rule_id):
    level = "A" if rule_id.startswith("A") else "B"
    return level, rule_id, TRIGGER_BY_ID[rule_id], obligations_for(rule_id), []


def _a0(violations):
    return "A", "A0", None, [], violations


def _convergence(ctx, n):
    """Konvergensregelen. Ikke-tom liste ⇒ A0.

    Begge gater leses likt (§5b og §4): at gate-funnene ikke går ned, og en ny feilklasse, er B1/B7. Innholdsfunn,
    manglende data og kostnadsbremsen er A0. `cost_over=few` (bremsen mangler utvalg)
    er A0 fra runde 2 og teller som `no` i runde 1.
    """
    v = []
    if ctx.get("cost_over") not in (("no",) if n >= CAP else ("no", "few")):
        v.append(f"cost_brake: cost_over={ctx.get('cost_over')!r}")
    if n >= CAP:
        try:
            int(ctx["blocking_prev"]), int(ctx["blocking_now"])
        except (KeyError, TypeError, ValueError):
            v.append("konvergensdata mangler/ugyldig: blocking_prev/blocking_now")
        if ctx.get("new_class") not in ("yes", "no"):
            v.append(f"konvergensdata mangler/ugyldig: new_class={ctx.get('new_class')!r}")
        if ctx.get("content") != "no":
            v.append(f"no_convergence: content={ctx.get('content')!r}")
    return v


def classify(event, ctx):
    """Returnerer (level, rule, trigger, obligations, violations).

    Evalueringsrekkefølge (§3.1, ufravikelig): konvergensvakt →
    påkrevd-kontekst-vakt → A1..A8 → B1..B8 → A0 (fail-closed). Første treff
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
        # (ii) Kostnadsbrems, konvergensdata og innholdsregel for en NY fix-runde (smal lesning).
        if event == "revise_gate_choice" and ctx.get("action") == "fix_round":
            violations += _convergence(ctx, n)
            if n >= ROUND_STOP:
                violations.append(f"round_stop: code_review_rounds={n}")

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
    native = event == "technical_risk" and ctx.get("source") == "planner" and ctx.get("kind") == "native"
    if event == "technical_risk" and ctx.get("source") == "planner":
        missing += [k for k in ("kind",) + (NATIVE_KEYS if native else ("executable_gate",)) if k not in ctx]
    if missing:
        return _a0([f"påkrevd kontekst mangler for {event!r}: {', '.join(missing)}"])
    # `true`/`false` fra skjemaet skal oversettes til yes/no av koordinatoren. Alt annet er en feil.
    bad = [f"ugyldig verdi: {k}={ctx[k]!r}" for k in NATIVE_KEYS if native and ctx[k] not in ("yes", "no")]
    if bad:
        return _a0(bad)

    # --- 3. A1..A8 ------------------------------------------------------------
    if event == "migration_apply" and ctx.get("env") == "prod":
        return _hit("A1")
    if event == "technical_risk" and ctx.get("source") == "planner" and ctx.get("kind") == "prod_push":
        return _hit("A1")
    if event == "secrets_change":
        return _hit("A2")
    if event == "technical_risk" and ctx.get("source") == "planner" and ctx.get("kind") == "secrets":
        return _hit("A2")
    if event == "native_build" or (native and [ctx[k] for k in NATIVE_KEYS] != ["no", "no"]):
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

    # --- 4. B1..B8 ------------------------------------------------------------
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
    if native:
        return _hit("B8")

    # --- 5. A0 — fail-closed ----------------------------------------------
    return _a0([f"ukjent hendelse eller ingen regel treffer: event={event!r} context={ctx!r}"])


# --- Fixtures (61 stk.: F1..F49 + F52..F60 + F1b/F1c/F25b) -----------------------------
_CONV = {"blocking_prev": "3", "blocking_now": "1", "new_class": "no", "content": "no", "cost_over": "no"}
_F28 = {"code_review_rounds": "2", "action": "fix_round", "decision_logged": "yes", **_CONV}
_F34 = {"plan_review_rounds": "2", "action": "revise", **_CONV, "blocking_prev": "2"}
_NAT = {"source": "planner", "kind": "native"}
FIXTURES = [
    ("F1", "revise_gate_choice", {"code_review_rounds": "2", "action": "fix_round", "decision_logged": "yes", **_CONV}, "B", "B1"),
    ("F1b", "revise_gate_choice", {"code_review_rounds": "3", "action": "fix_round", "decision_logged": "yes", **_CONV, "blocking_prev": "2", "blocking_now": "2"}, "B", "B1"),
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
    # F25/F25b: lukking (merge_carry) er alltid B1; fix_round uten cost_over er A0 (bremsen er
    # fail-closed). F25b mangler også konvergensdata.
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
    # F28-F40: hver fixture skiller seg fra F28/F34 i ÉN nøkkel. §5b leses smalt:
    # F29 (funnene går ikke ned) og F30 (ny feilklasse) er B1. §4 leses likt: F35 og F37 er B7, F38 er A0.
    ("F28", "revise_gate_choice", _F28, "B", "B1"),
    ("F29", "revise_gate_choice", {**_F28, "blocking_now": "3"}, "B", "B1"),
    ("F30", "revise_gate_choice", {**_F28, "new_class": "yes"}, "B", "B1"),
    ("F31", "revise_gate_choice", {**_F28, "content": "yes"}, "A", "A0"),
    ("F32", "revise_gate_choice", {**_F28, "cost_over": "yes"}, "A", "A0"),
    ("F33", "revise_gate_choice", {"code_review_rounds": "1", "action": "fix_round", "cost_over": "yes"}, "A", "A0"),
    ("F34", "plan_review_choice", _F34, "B", "B7"),
    ("F35", "plan_review_choice", {**_F34, "blocking_prev": "1"}, "B", "B7"),
    ("F36", "revise_gate_choice", {**_F28, "code_review_rounds": "6", "blocking_prev": "2"}, "A", "A0"),
    ("F37", "plan_review_choice", {**_F34, "new_class": "yes"}, "B", "B7"),
    ("F38", "plan_review_choice", {**_F34, "content": "yes"}, "A", "A0"),
    ("F39", "revise_gate_choice", {k: v for k, v in _F28.items() if k != "blocking_now"}, "A", "A0"),
    ("F40", "revise_gate_choice", {k: v for k, v in _F28.items() if k != "new_class"}, "A", "A0"),
    # F41-F49: `few` stopper begge gater fra runde 2 (F41, F43, F45). F46-F48 fester at `unknown` stopper
    # også i §4 og i §5b runde 1, F49 at manglende `cost_over` stopper i §5b runde 1.
    ("F41", "revise_gate_choice", {**_F28, "cost_over": "few"}, "A", "A0"),
    ("F42", "revise_gate_choice", {"code_review_rounds": "1", "action": "fix_round", "cost_over": "few"}, "B", "B1"),
    ("F43", "plan_review_choice", {**_F34, "cost_over": "few"}, "A", "A0"),
    ("F44", "plan_review_choice", {"plan_review_rounds": "1", "action": "revise", "cost_over": "few"}, "B", "B7"),
    ("F45", "revise_gate_choice", {**_F28, "code_review_rounds": "3", "cost_over": "few"}, "A", "A0"),
    ("F46", "plan_review_choice", {"plan_review_rounds": "1", "action": "revise", "cost_over": "unknown"}, "A", "A0"),
    ("F47", "revise_gate_choice", {"code_review_rounds": "1", "action": "fix_round", "cost_over": "unknown"}, "A", "A0"),
    ("F48", "plan_review_choice", {**_F34, "cost_over": "unknown"}, "A", "A0"),
    ("F49", "revise_gate_choice", {"code_review_rounds": "1", "action": "fix_round"}, "A", "A0"),
    # F52-F58 (F50/F51 er reservert): native kodearbeid
    # er B8 bare når begge feltene er `no`. Manglende felt, `false` og source=reviewer er A0.
    ("F52", "technical_risk", {**_NAT, "native_dep": "no", "native_permission": "no"}, "B", "B8"),
    ("F53", "technical_risk", {**_NAT, "native_dep": "yes", "native_permission": "no"}, "A", "A3"),
    ("F54", "technical_risk", {**_NAT, "native_dep": "no", "native_permission": "yes"}, "A", "A3"),
    ("F55", "technical_risk", {**_NAT, "native_dep": "no"}, "A", "A0"),
    ("F56", "technical_risk", {**_NAT, "source": "reviewer", "native_dep": "no", "native_permission": "no"}, "A", "A0"),
    ("F57", "technical_risk", {**_NAT, "native_dep": "false", "native_permission": "no"}, "A", "A0"),
    ("F58", "plan_review_choice", {k: v for k, v in _F34.items() if k != "new_class"}, "A", "A0"),
    # F59/F60: rundestoppet gjelder en ny fix-runde i §5b fra runde 4 (også F36), ikke §4.
    ("F59", "revise_gate_choice", {**_F28, "code_review_rounds": "4"}, "A", "A0"),
    ("F60", "plan_review_choice", {**_F34, "plan_review_rounds": "4"}, "B", "B7"),
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


# --- Logg-parser -------------------------------------------------
LOG_PATH = "docs/superpowers/loop/decision-log.md"
RUN_LOG_PATH = "docs/superpowers/loop/run-log.md"
_HEADER = re.compile(r"^### (\d{4}-\d{2}-\d{2} \d{2}:\d{2})(?: —)? (.*)$")
_TODO = re.compile(r"TODO (\d+[A-Za-z0-9]*)")
_BTAG = re.compile(r"\[B\d+\]")
_TOKEN = re.compile(r"auto_decided=([^ |;:]*):(\d+)")
_FIELD = re.compile(r"\*\*([^*:]+):\*\*\s*(.*)")
# `se <tid>` peker til svaroppføringen. Annen tekst som starter med «se» er et vanlig svar.
_SE = re.compile(r"se \d{4}-\d{2}-\d{2} \d{2}:\d{2}", re.I)
# Leddet foran kolon i `Type` -> slag. Eneste vokabular: leses av [A0]-vakten i reconcile() og av retro-numbers.py.
SLAG = {ledd: slag for slag, ledd_ in {
    "runder": "revise_gate_choice revise_gate plan_review_choice plan_invalid runder",
    "eiervalg": "eiervalg scope_change calibration naming_deviation todo_split next_todo_select "
                "pipeline_b_select retro_triage worker_blocked release_scope",
    "risiko": "risiko technical_risk migration_apply edge_function_deploy secrets_change native_build "
              "main_push destructive_op",
    "kvittering": "kvittering health_red",
    "måling": "måling",
}.items() for ledd in ledd_.split()}


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
        # `se <tid>` peker til svaroppføringen, og en uoppfordret ordre er ikke et svar på en anbefaling.
        if svar is None or svar.lower().startswith("venter") or _SE.match(svar) or "(uoppfordret)" in svar.lower():
            continue
        typ = e["fields"].get("Type") or re.split(r"[,\]]", _bracket(e["header"]))[0].strip()
        rows.setdefault(typ, []).append(svar.lower().startswith("fulgt"))
    # En type med en [B, calibration]-oppføring er alt flyttet og foreslås ikke på nytt.
    moved = {e["fields"].get("Type") for e in entries if _bracket(e["header"]).startswith("B, calibration")}
    out = []
    for typ in sorted(rows):
        r = rows[typ]
        # Tillatelsesliste: leddet må stå i SLAG, og et eiervalg må ha klassen `mekanisk`.
        ledd, _, navn = typ.partition(":")
        slag = SLAG.get(ledd.strip())
        tillatt = slag is not None and (slag != "eiervalg" or navn.strip() == "mekanisk")
        forslag = "flytt-til-B" if tillatt and len(r) >= 10 and all(r[-10:]) and typ not in moved else "-"
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
    out = "# mini\n" + entry("2026-10-02 11:30", "B1", Type="plan_review_choice", Eierens_svar="fulgt", Reversibel_til="x")
    out += "<!-- FORMAT-V2 (test) -->\n"
    for d in range(20, 30):
        out += entry(f"2026-09-{d} 10:00", "A0", Type="plan_review_choice", Eierens_svar="fulgt")
    for d in range(1, 10):
        out += entry(f"2026-09-0{d} 10:00", "A0", Type="runder", Eierens_svar="fulgt")
    out += entry("2026-09-10 10:00", "A0", Type="Y", Eierens_svar="fulgt")
    out += entry("2026-09-11 10:00", "A0", Type="Y", Eierens_svar="avvek: kutt")
    out += entry("2026-10-01 10:00", "A0", Type="plan_review_choice", Eierens_svar="venter")
    out += entry("2026-09-13 10:00", "A0", Type="Y", Eierens_svar="se 2026-09-10 10:00")
    out += entry("2026-09-14 10:00", "A0", Type="Y", Eierens_svar="ordre: x (uoppfordret)")
    out += entry("2026-09-15 10:00", "A0", Type="V", Eierens_svar="se over, kutt X")   # ingen peker: et avvik
    out += entry("2026-09-12 10:00", "A, eier", Eierens_svar="Fulgt («ja»)")
    out += entry("2026-10-02 09:00", "B1", Reversibel_til="merge")
    out += entry("2026-10-01 11:00", "B", Reversibel_til="y")
    out += entry("2026-10-02 10:00", "VETO av B1", Reversibel_til="z")
    for d in range(10, 20):
        out += entry(f"2026-08-{d} 10:00", "A0", Type="revise_gate_choice", Eierens_svar="fulgt")
    out += entry("2026-08-20 10:00", "B, calibration", Type="revise_gate_choice", Reversibel_til="første VETO")
    # i eiervalg-slaget foreslås bare kort-navnet `mekanisk`. `technical_risk` ender på et avvik.
    for typ in ("eiervalg", "eiervalg:produkt", "Eiervalg:produkt", "eiervalg:mekanisk", "eiervalg:mekanisk:x",
                "release_scope", "release_scope:mekanisk", "technical_risk"):
        for d in range(10, 20):
            svar = "avvek: x" if (typ, d) == ("technical_risk", 19) else "fulgt"
            out += entry(f"2026-07-{d} 10:00", "A0", Type=typ, Eierens_svar=svar)
    return out


def run_parser_self_test():
    entries = parse_log(_mini_log())
    exp_agr = ["A\t1\t1\t0\t-", "Eiervalg:produkt\t10\t10\t0\t-", "V\t1\t0\t1\t-", "Y\t2\t1\t1\t-",
               "eiervalg\t10\t10\t0\t-", "eiervalg:mekanisk\t10\t10\t0\tflytt-til-B", "eiervalg:mekanisk:x\t10\t10\t0\t-",
               "eiervalg:produkt\t10\t10\t0\t-", "plan_review_choice\t10\t10\t0\tflytt-til-B",
               "release_scope\t10\t10\t0\t-", "release_scope:mekanisk\t10\t10\t0\tflytt-til-B",
               "revise_gate_choice\t10\t10\t0\t-", "runder\t9\t9\t0\t-", "technical_risk\t10\t9\t1\t-"]
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


# --- Avstemming mot run-loggen -----------------------------------
def attribute(entries, run_text):
    """Hvilken run-log-rad bærer hver [B<siffer>]-oppføring. Ingen filsystemkall.

    Eier = første `TODO <nr>` i overskriften. Oppføringen telles på eierens første rad med
    radtid >= oppføringstid. Returnerer (rader, ventende, eierløse): rader i filrekkefølge med
    `token` (tallet raden fører, None når det mangler) og `n` (tallet loggen gir), ventende som
    (tid, todo, siste radutfall eller None) og eierløse som tid.
    Rader med `-` i todo-feltet hoppes over og avstemmes ikke.
    """
    rows, by_todo = [], {}
    for line in run_text.splitlines():
        f = [x.strip() for x in line.split("|")]
        if not re.match(r"20\d\d-", line) or len(f) < 4 or f[3] == "health" or f[1] == "-":
            continue
        m = _TOKEN.search(line)
        row = {"ts": f[0][:16].replace("T", " "), "todo": f[1], "outcome": f[3],
               "token": int(m.group(2)) if m else None, "key": m and m.group(1), "n": 0}
        rows.append(row)
        by_todo.setdefault(f[1], []).append(row)
    for rs in by_todo.values():
        rs.sort(key=lambda r: r["ts"])
    waiting, ownerless = [], []
    for e in entries:
        if not _BTAG.search(e["header"]):
            continue
        m = _TODO.search(e["header"])
        if not m:
            ownerless.append(e["ts"])
            continue
        rs = by_todo.get(m.group(1), [])
        # ponytail: minuttoppløsning. En oppføring skrevet etter raden i samme minutt telles
        # på raden og gir AVVIK ved neste helsesjekk. Sekunder i begge logger hvis det plager.
        row = next((r for r in rs if r["ts"] >= e["ts"]), None)
        if row:
            row["n"] += 1
        else:
            waiting.append((e["ts"], m.group(1), rs[-1]["outcome"] if rs else None))
    return rows, waiting, ownerless


def auto_decided(entries, run_text, nr):
    waiting = attribute(entries, run_text)[1]
    return f"auto_decided={nr}:{sum(1 for _, todo, _ in waiting if todo == nr)}"


def last_health(run_text):
    ts = [l[:16] for l in run_text.splitlines() if re.match(r"20\d\d-.*\| health \|", l)]
    return ts[-1] if ts else ""


def reconcile(entries, run_text, since):
    """(linjer, exit-kode) for vinduet etter `since` (YYYY-MM-DDTHH:MM)."""
    since = since.replace("T", " ")
    rows, waiting, ownerless = attribute(entries, run_text)
    out, n_rows, bad, missing = [], 0, 0, 0
    for r in rows:
        if r["ts"] <= since:
            continue
        n_rows += 1
        ts = r["ts"].replace(" ", "T")
        if r["token"] is None:
            missing += 1
            out.append(f"{ts} {r['todo']} rad=- logg={r['n']} MANGLER_TOKEN")
        else:
            status = "AVVIK" if r["token"] != r["n"] else "FEIL_FORM" if r["key"] != r["todo"] else "OK"
            bad += status != "OK"
            out.append(f"{ts} {r['todo']} rad={r['token']} logg={r['n']} {status}")
    # [A0]-vakten gjelder fra 516s egen merged-rad (kit-porten bytter nummeret). Uten raden håndheves ingenting.
    limit = next((r["ts"] for r in rows if r["todo"] == "516" and r["outcome"] == "merged"), None)
    n = 0
    for e in entries if limit else []:
        if not re.search(r"\[A0[\],]", e["header"]) or e["ts"] <= since or e["ts"] <= limit:
            continue
        typ = e["fields"].get("Type")
        ledd = typ and typ.split(":")[0].strip()
        if not ledd or ledd not in SLAG:
            n += 1
            out.append(f"{e['ts'].replace(' ', 'T')} A0 " + (f"UKJENT_TYPE {ledd}" if ledd else "MANGLER_TYPE"))
    after, wait = {}, {}
    for ts, todo, outcome in waiting:
        if ts > since:
            d = after if outcome == "merged" else wait
            d[todo] = d.get(todo, 0) + 1

    def fmt(d):
        return " ".join(f"{k}:{v}" for k, v in d.items()) or "-"

    n_after = sum(after.values())
    out.append(f"etter merged-rad: {fmt(after)}")
    out.append(f"venter på merge: {fmt(wait)}")
    out.append(f"uten todo: {sum(1 for ts in ownerless if ts > since)}")
    out.append(f"rader={n_rows} avvik={bad} mangler_token={missing} etter_merged={n_after} a0_feil={n}")
    return out, 1 if bad + missing + n_after + n else 0


def build_header(rule, todo, title, now):
    who = f"TODO {todo}" if todo else "loop"
    return f"### {now:%Y-%m-%d %H:%M} — {who} [{rule}]: {title or '<kort valg>'}"


def header_warnings(todo, title):
    other = [n for n in _TODO.findall(title or "") if n != todo]
    if not other:
        return []
    nums = ", ".join(other)
    if todo:
        return [f"tittelen nevner TODO {nums}, men --todo er {todo}: oppføringen telles på {todo}"]
    return [f"--todo mangler, og tittelen nevner TODO {nums}: oppføringen telles på {other[0]}"]


def run_reconcile_self_test():
    t = "2026-01-01"
    log = "<!-- FORMAT-V2 (test) -->\n" + "".join(f"### {t} {h}\n" for h in [
        "09:01 [B1] TODO 11 nivået foran",
        "09:02 — TODO 11 [B7]: nivået etter nummeret",
        "09:03 — TODO 11: nivået sist [B1]",
        "10:05 — TODO 11 [B]: uten siffer",
        "10:06 — TODO 11 [B, calibration]: flytting",
        "10:07 — TODO 11 [VETO av B1]: veto",
        "10:08 — TODO 11 [A0]: spørsmål",
        "10:30 — TODO 12 [B1]: før pausen",
        "11:30 — TODO 15 [B3]: før helseraden",
        "12:10 — TODO 12 [B1]: etter pausen",
        "12:20 — TODO 12 [B1]: etter pausen igjen",
        "12:30 — TODO 15 [B7]: etter helseraden",
        "13:10 — TODO 13 go, TODO 14 no-go [B7]",
        "13:15 — 352 og 315 go [B7]",
        "14:05 — TODO 16 [B1]: etter merge",
    ])

    def row(hhmm, todo, outcome, tok):
        return f"{t}T{hhmm} | {todo} | slug | {outcome} | - | #1 | 1 | 1 | m | - | - | selector=none; {tok}ci=green\n"

    row11 = row("10:00", "11", "merged", "auto_decided=koordinator:3; ")
    run = "# test\n" + row11 + row("11:00", "12", "paused", "auto_decided=12:1; ")
    run += f"{t}T12:00 | - | loop-health-check | health | helsesjekk-grønn | - | 0 | 0 | m | sha=x\n"
    run += row("13:00", "12", "merged", "auto_decided=12:2; ") + row("13:30", "13", "merged", "auto_decided=13:1; ")
    run += row("13:40", "14", "merged", "auto_decided=14:0; ") + row("14:00", "16", "merged", "auto_decided=16:0; ")
    run += row("14:10", "17", "merged", "")
    entries = parse_log(log)
    n = {(r["todo"], r["outcome"]): r["n"] for r in attribute(entries, run)[0]}
    lines, code = reconcile(entries, run, last_health(run))
    plus, _ = reconcile(entries, run.replace(row11, row11.replace(":3;", ":4;")), "")
    tok15 = auto_decided(entries, run, "15")
    run_rt = run + row("15:00", "15", "merged", tok15 + "; ")
    rt, _ = reconcile(entries, run_rt, last_health(run))
    with_header = parse_log(log + build_header("B3", "15", "prøve", datetime(2026, 1, 1, 12, 40)) + "\n")
    ff, ff_code = reconcile(entries, "# test\n" + row11, "")
    run516 = run + row("14:20", "516", "merged", "auto_decided=516:0; ")
    a0_log = log + f"### {t} 14:19 — loop [A0]: før grensen\n### {t} 14:23 — loop [A0]: kjent\n- **Type:** eiervalg:farge\n"

    def a0(extra, since):
        ls, c = reconcile(parse_log(a0_log + extra), run516, since)
        return [l for l in ls if " A0 " in l], ls[-1], c

    a0_sum = "rader=1 avvik=0 mangler_token=0 etter_merged=0 a0_feil="
    a0_bad = f"### {t} 14:21 — loop [A0]: uten type\n### {t} 14:22 — loop [A0]: ukjent\n- **Type:** hokus\n"
    checks = [
        ("varianter", 3, n[("11", "merged")]),
        ("flerrad", (1, 2), (n[("12", "paused")], n[("12", "merged")])),
        ("to-todoer", (1, 0), (n[("13", "merged")], n[("14", "merged")])),
        ("uten-todo", True, "uten todo: 1" in lines),
        ("b-uten-siffer", "auto_decided=11:0", auto_decided(entries, run, "11")),
        ("venter", ("venter på merge: 15:1", "auto_decided=15:2"), (lines[-3], tok15)),
        ("etter-merged", ("etter merged-rad: 16:1", "rader=5 avvik=0 mangler_token=1 etter_merged=1 a0_feil=0", 1),
         (lines[-4], lines[-1], code)),
        ("mangler-token", True, f"{t}T14:10 17 rad=- logg=0 MANGLER_TOKEN" in lines),
        ("pluss-en", [f"{t}T10:00 11 rad=4 logg=3 AVVIK"], [l for l in plus if l.endswith("AVVIK")]),
        ("rundtur", (True, "auto_decided=15:0"),
         (f"{t}T15:00 15 rad=2 logg=2 OK" in rt, auto_decided(entries, run_rt, "15"))),
        ("header", "auto_decided=15:3", auto_decided(with_header, run, "15")),
        ("feil-form", (f"{t}T10:00 11 rad=3 logg=3 FEIL_FORM", "rader=1 avvik=1 mangler_token=0 etter_merged=0 a0_feil=0", 1),
         (ff[0], ff[-1], ff_code)),
        ("a0-type", ([f"{t}T14:21 A0 MANGLER_TYPE", f"{t}T14:22 A0 UKJENT_TYPE hokus"], a0_sum + "2", 1),
         a0(a0_bad, f"{t}T14:15")),
        ("a0-type", ([], a0_sum + "0", 0), a0("", f"{t}T14:15")),
        ("a0-type", ([], "rader=0 avvik=0 mangler_token=0 etter_merged=0 a0_feil=0", 0), a0(a0_bad, f"{t}T14:22")),
    ]
    ok = True
    for name, exp, got in checks:
        if exp != got:
            ok = False
            print(f"  avstemming {name}: forventet {exp!r}, faktisk {got!r}", file=sys.stderr)
    print(f"[decision-level --self-test] avstemming: {'PASS' if ok else 'FEIL'}", file=sys.stderr)
    return ok


def _read(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return fh.read()
    except OSError as exc:
        print(f"FEIL: kan ikke lese {path}: {exc}", file=sys.stderr)
        sys.exit(2)


def _load_entries(path):
    entries = parse_log(_read(path))
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
    ap.add_argument("--dump-rules", action="store_true", help="Skriv TSV av alle 16 regler.")
    ap.add_argument("--self-test", action="store_true", help="Kjør fixturene og logg-parser-testen.")
    ap.add_argument("--agreement", action="store_true", help="Samsvar per type (TSV).")
    ap.add_argument("--recent-b", action="store_true", help="Nivå B-entries siste --hours timer (JSON).")
    ap.add_argument("--hours", type=float, default=24)
    ap.add_argument("--log", default=LOG_PATH)
    ap.add_argument("--run-log", default=RUN_LOG_PATH)
    ap.add_argument("--auto-decided", metavar="NR", help="Skriv auto_decided=<nr>:<n> for run-log-raden.")
    ap.add_argument("--reconcile", action="store_true", help="Avstem run-log-rader mot decision-log (D4).")
    ap.add_argument("--since", help="YYYY-MM-DDTHH:MM (standard: siste health-rad).")
    ap.add_argument("--todo", help="Todo-nummeret oppføringen eies av (til header-feltet).")
    ap.add_argument("--title", help="Kort valg (til header-feltet).")
    args = ap.parse_args()

    if args.auto_decided:
        print(auto_decided(_load_entries(args.log), _read(args.run_log), args.auto_decided))
        return

    if args.reconcile:
        entries, run_text = _load_entries(args.log), _read(args.run_log)
        lines, code = reconcile(entries, run_text, args.since or last_health(run_text))
        print("\n".join(lines))
        sys.exit(code)

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
        ok = run_reconcile_self_test() and ok
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
        "header": build_header(rule, args.todo, args.title, datetime.now()),
        "warnings": header_warnings(args.todo, args.title),
    }, ensure_ascii=False))
    if rule == "A0":
        sys.exit(1)


if __name__ == "__main__":
    main()
