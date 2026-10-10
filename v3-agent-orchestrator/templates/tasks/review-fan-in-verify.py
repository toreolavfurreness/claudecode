#!/usr/bin/env python3
# GENERERT av /setup fra loop.config.yaml — IKKE rediger her.
# Endre loop.config.yaml og kjør /setup på nytt.
"""review-fan-in-verify.py — mekanisk kontrakt-vakt for kode-reviewerens
`fan_in`-rapport. Speiler selektor-stegets tre
mengde-sammenligninger og legger seks nye (attestasjon-form, ukjent agent,
stale SHA, manglende attestasjon) pluss en betinget bindende liveness-regel.

**Dette er en LOGG uten `--strict`, og en GATE med `--strict`.** Uten
`--strict` exit'er analysemodus `0` for ethvert antall funn (250A-
invarianten, ubrutt). Med `--strict` exit'er den `3` når minst én kode i
`BINDING_CODES` fyrer. Det leser IKKE `loop.config.yaml` ved kjøring —
`SEVERITY_FLOORS` under er substituert inn av /setup på SETUP-TID, samme
kontrakt som `review-severity-floor.py`, og KUN nøklene (agentnavnene)
brukes her, som `KNOWN_AGENTS`.

**Kontrast til `review-severity-floor.py` (bærende, les før du endrer exit-
håndtering):** det skriptet exit'er != 0 NÅR rapporten er avvist (kontraktbrudd
= usignert). DETTE skriptet exit'er 0 i analysemodus UTEN `--strict`, uansett
utfall — en exit != 0 herfra betyr da at SKRIPTET selv feilet (krasj/bruksfeil),
ALDRI at `fan_in`-rapporten ble avvist. MED `--strict` betyr exit 3 derimot en
FAKTISK avvisning (`verdict: "rejected"`). Utfallet leses fra JSON-en
(`violations[]`, `verdict` og `signals.attest`), og fra exit-koden KUN i
`--strict`-modus.

`--self-test` har en ANNEN, MOTSATT kontrakt (samme som søsknenes
`decision-level.py`): den exit'er `1` hvis ÉN av de frosne fixturene avviker
fra forventet `violations`/`attest`/`verdict`/`mode` ELLER dekningsassertionen
feiler, og skriver `<bestått>/<total>` til stderr (JSON-sammendrag til stdout
ETTER, samme rekkefølge som `decision-level.py:299`/`:300`). Exit-0-
invarianten over gjelder KUN `--fan-in`-modus uten `--strict`.

Opphavet til `fan_in`s felter (`returned`, `attestations`, …) er delvis
verifisert her (R12): en koordinator-etablert `--live-key`-fil kan
si at en `returned`-oppføring ikke matcher noe registrert signal
(`premature-return`). Skriptet leser ALDRI rapportens egen `evidence` for
dette formålet — nøkkelfila kommer alltid fra en ANNEN kilde enn `--fan-in`
(koordinatorens egne worktree-/ledger-snapshots), ellers ville en fabrikert
rapport kunne bevise sin egen ærlighet.

Bruk:
    python3 tasks/review-fan-in-verify.py --fan-in <fil|->  [--pr-head-sha <sha>] [--strict] [--require-attestations] [--live-key <fil>]     # analysemodus
    python3 tasks/review-fan-in-verify.py --self-test
    python3 tasks/review-fan-in-verify.py --dump-rules

Analysemodus skriver JSON på stdout:
    {"mode": "<observe|strict>", "verdict": "<observed|rejected>", "violations": [...],
     "signals": {"attest": "...", "skipped": [...], "known_agents": N, "live": "<none|unavailable|ledger|worktree>"}}

`mode` speiler `--strict`, `verdict` speiler exit-koden (`3` ⇔ `"rejected"`).

Regler (tretten i bruk — R1–R12 og R14; R13 er reservert og utelatt — flat
nummerering, én brudd-kode hver — 1:1 med `coordinator-runbook.md`s
utfallstabell):

    R1  --fan-in lesbar og gyldig JSON-objekt                         input-unreadable
    R2  De fire påkrevde nøklene finnes (triggered/dispatched/         contract-missing-key
        returned/expected_by_selector)
    R3  Hver påkrevd nøkkel er en array av strenger                    contract-bad-type
    R4  Finnes attestations: hver entry har agent (streng);            attestation-malformed
        toplevel/reviewed_sha er streng eller null
    R5  Finnes attestations: {a.agent} == set(returned)                attestation-mismatch
    R6  set(returned) ⊆ set(dispatched)                                returned-not-dispatched
    R7  set(dispatched) \\ set(returned) == ∅                          silent-node
    R8  set(dispatched) ⊆ KNOWN_AGENTS                                 unknown-agent
    R9  set(expected_by_selector) ⊆ set(dispatched)                    under-dispatch
    R10 --pr-head-sha oppgitt ⇒ hver normaliserbar reviewed_sha == den  stale-lens-sha
    R11 --require-attestations ∧ returned ≠ ∅ ∧ attestations mangler   attestations-missing
    R12 --live-key lastet ⇒ returned/worktree-signalet er FRISKT        premature-return
        (betinget bindende — KUN når --live-key sin mode == "ledger")
    R14 --live-key gitt, men uleselig/ugyldig                           live-key-unreadable

R6 ∧ R7 er nøyaktig `returned == dispatched`, splittet i to koder fordi
de to retningene betyr helt ulike ting: `returned ⊄ dispatched` er et navn
som aldri ble dispatchet (fabrikasjons-signal), `dispatched \\ returned ≠ ∅`
er en «stille node». R6/R7/R8/R9 forblir `logg`.

**R13 `ledger-orphan` er RESERVERT og ubrukt** (nummeret brukes ALDRI her,
slik at ingen renummerering trengs når regelen bygges):
den krever en ikke-tom ledger for å
kunne fyre i det hele tatt, og ledgeren er målt tom i denne harnessen.

Kontrollflyt: kun R1 kortslutter (uleselig input gjør resten meningsløst).
R2/R3 kortslutter ikke selv, men en regel som avhenger av en manglende eller
feiltypet nøkkel HOPPES og føres i `signals.skipped[]`. R4–R11 og R12/R14 har
ingen tidlig `return` — alle avvik samles.

`signals.attest` (frossen presedens, i denne rekkefølgen — kjøres MED
`--strict` prefikses verdien med `strict:`; uten `--strict` er
verdien byte-identisk med den uarmerte formen):
    1. violations ikke-tom          ⇒ de kommaseparerte kodene (sortert, dedup)
    2. ellers dispatched == []      ⇒ "none"
    3. ellers attestations mangler  ⇒ "legacy"
    4. ellers                       ⇒ "ok"

`script-error` produseres ALDRI av dette skriptet — det er koordinatorens
egen etikett når skriptet krasjet, og prefikses ALDRI med `strict:`.

`--dump-rules` skriver TSV (`<id><TAB><brudd-kode><TAB><utfall>`) for R1–R12
og R14 (R13 utelatt) til stdout, paritets-orakelet mot runbookens
utfallstabell (V6). `<utfall>` er `stopp` for R2–R5, R10 og R11, `betinget`
for R12 (bindende KUN når `--live-key` sin `mode == "ledger"`), og
`logg` for R1 (koordinatorens egen inndata-fil), R6–R9
og R14 (måler koordinatorens EGEN nøkkelfil, aldri bindende).

`--self-test` kjører de frosne fixturene og skriver PASS/FEIL per fixture
+ `<bestått>/<total>` til stderr, JSON-sammendrag til stdout, exit 0 kun når
alle er grønne OG dekningsassertionen passerer (hver kode i `--dump-rules`
har minst én fixture som forventer den).
"""
import argparse
import json
import os
import re
import sys
import tempfile

{{TECH_REVIEW_SEVERITY_FLOORS}}

# KUN nøklene (agentnavnene) brukes her, som KNOWN_AGENTS. Tom mengde er en
# LOVLIG konfigurasjon — et kit uten registrerte
# tech-review-lenser er gyldig, og R8 blir da vakuøs (se evaluate()). Skulle
# SEVERITY_FLOORS-substitusjonstokenet stå igjen uerstattet (en /setup-feil),
# krasjer modulen ALLEREDE her med NameError — et eksplisitt fail-fast-kall
# ville aldri blitt nådd i det tilfellet, og er derfor ikke duplisert.
KNOWN_AGENTS = frozenset(SEVERITY_FLOORS)

REQUIRED_KEYS = ["triggered", "dispatched", "returned", "expected_by_selector"]

RULES = [
    ("R1", "input-unreadable"),
    ("R2", "contract-missing-key"),
    ("R3", "contract-bad-type"),
    ("R4", "attestation-malformed"),
    ("R5", "attestation-mismatch"),
    ("R6", "returned-not-dispatched"),
    ("R7", "silent-node"),
    ("R8", "unknown-agent"),
    ("R9", "under-dispatch"),
    ("R10", "stale-lens-sha"),
    ("R11", "attestations-missing"),
    ("R12", "premature-return"),
    ("R14", "live-key-unreadable"),
]

# --- BINDING_CODES (D1.3) ----------------------------------------
# `input-unreadable` (R1) er BEVISST UTENFOR: den måler koordinatorens EGEN
# --fan-in-scratch-fil, ikke et felt revieweren fylte, og skal derfor aldri
# kunne gi A0-eskalering (r3 VIKTIG-2).
BINDING_CODES = frozenset({
    "contract-missing-key",
    "contract-bad-type",
    "attestation-malformed",
    "attestation-mismatch",
    "stale-lens-sha",
    "attestations-missing",
})

# --- LIVE_BINDING_CODES (D1.5) -----------------------------------
# `premature-return` (R12) er BETINGET bindende: den teller KUN mot
# compute_binding når live_mode == "ledger" (positiv kontroll oppfylt denne
# runden). En EGEN mengde, ikke en utvidelse av BINDING_CODES over — R12 skal
# aldri bli bindende ved et uhell fordi noen legger den i den frosne (§ 6 R-12).
LIVE_BINDING_CODES = frozenset({"premature-return"})

_HEX_RE = re.compile(r"^[0-9a-f]+$")


def _skip_key(r):
    """Sorteringsnøkkel for signals.skipped[] — håndterer BÅDE enkle ("R10")
    og kvalifiserte ("R10:unnormalizable:<agent>") former: begge sorteres på
    regel-NUMMERET (numerisk, ikke leksikografisk — "R10" < "R4" som streng),
    sekundært på hele strengen."""
    return (int(r[1:].split(":", 1)[0]), r)


def _normalize_sha(value):
    """Normaliser en reviewed_sha for R10 (D1.4).
    Returnerer lowercase hex-streng hvis den normaliserer til >= 7 hex-tegn,
    ellers None (unnormaliserbar — null-semantikk, aldri attestation-malformed)."""
    if not isinstance(value, str):
        return None
    v = value.lower()
    if len(v) < 7 or not _HEX_RE.match(v):
        return None
    return v


def _is_str_array(v):
    return isinstance(v, list) and all(isinstance(x, str) for x in v)


def load_fan_in(path):
    """Les og parse --fan-in. Returnerer (data, error) — error er en
    (brudd-kode, melding)-tuppel eller None. Feiler ALDRI med en Python-
    exception ut av denne funksjonen (R1 fanger alt)."""
    try:
        if path == "-":
            raw = sys.stdin.read()
        else:
            with open(path, "r", encoding="utf-8") as f:
                raw = f.read()
    except OSError as e:
        return None, ("input-unreadable", f"kan ikke lese --fan-in {path!r}: {e}")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        return None, ("input-unreadable", f"--fan-in er ikke gyldig JSON: {e}")
    if not isinstance(data, dict):
        return None, ("input-unreadable", "--fan-in er ikke et JSON-objekt")
    return data, None


def load_live_key(path):
    """Les og parse --live-key (D1.2). Ren funksjon, SAMME
    kontrakt som load_fan_in: returnerer (live, error), kaster ALDRI ut.
    `error` er ("live-key-unreadable", <melding>) når fila ikke kan leses,
    ikke er gyldig JSON, ikke er et objekt, eller `mode` mangler / ikke er i
    enumet {"ledger","worktree","unavailable"}. Ukjent calibration/
    lens_isolation degraderes til "none"/"unknown" (fail-open) — en ukjent
    kalibrering skal hoppe R12, ikke produsere et brudd. Returverdien
    konsumeres ALDRI direkte av evaluate() — den går gjennom live_state()
    (D1.0 i), som er det eneste stedet (live, error)-paret oversettes til
    normalisert live-tilstand."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = f.read()
    except OSError as e:
        return None, ("live-key-unreadable", f"kan ikke lese --live-key {path!r}: {e}")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        return None, ("live-key-unreadable", f"--live-key er ikke gyldig JSON: {e}")
    if not isinstance(data, dict):
        return None, ("live-key-unreadable", "--live-key er ikke et JSON-objekt")
    mode = data.get("mode")
    if mode not in ("ledger", "worktree", "unavailable"):
        return None, ("live-key-unreadable", f"--live-key har ukjent eller manglende mode: {mode!r}")
    calibration = data.get("calibration")
    if calibration not in ("autoremove", "persistent", "none"):
        calibration = "none"
    lens_isolation = data.get("lens_isolation")
    if lens_isolation not in ("own", "inherited", "unknown"):
        lens_isolation = "unknown"
    ledger = data.get("ledger")
    residual = data.get("residual_worktrees")
    live = {
        "mode": mode,
        "calibration": calibration,
        "lens_isolation": lens_isolation,
        "mid_snapshot": bool(data.get("mid_snapshot", False)),
        "ledger": ledger if _is_str_array(ledger) else [],
        "residual_worktrees": residual if _is_str_array(residual) else [],
    }
    return live, None


def live_state(live, err):
    """Normaliser (live, error)-paret fra load_live_key til ÉN av tre
    live-tilstander (D1.0 i). TOTAL funksjon — kalles av BEGGE
    kallstedene (run_analysis og run_self_test), slik at normaliseringen
    gjøres ÉN gang og ikke kan drive fra hverandre:

        (None, None)                                     -> None
        (_, ("live-key-unreadable", <melding>))           -> {"mode": "unreadable", "detail": <melding>}
        (<dict med lovlig mode>, None)                    -> samme dict, uendret

    R14 fyrer hvis og bare hvis live_state(...) gir en dict med
    mode == "unreadable"."""
    if err is not None:
        _, detail = err
        return {"mode": "unreadable", "detail": detail}
    return live


def live_token(live):
    """Total funksjon: normalisert live-tilstand -> signals.live-verdien
    (D1.6). Definert for alle tre live-tilstandene i live_state(),
    og derfor kallbar i BEGGE grenene av run_analysis (også R1-feilgrenen)."""
    if live is None:
        return "none"
    if live["mode"] == "unreadable":
        return "unavailable"
    return live["mode"]


def evaluate(data, pr_head_sha, require_attestations=False, known_agents=None, live=None):
    """Kjør R2..R12/R14 mot et allerede parset fan_in-objekt (R1 er kjørt av
    load_fan_in). `live` er NORMALISERT live-tilstand fra live_state() —
    ALDRI en filsti og ALDRI rapportens `evidence` (D1.0 i).
    Returnerer (violations, skipped, signals_extra)."""
    known_agents = KNOWN_AGENTS if known_agents is None else known_agents
    violations = []
    skipped = []

    # --- R2: påkrevde nøkler finnes -----------------------------------------
    missing = [k for k in REQUIRED_KEYS if k not in data]
    if missing:
        violations.append({"rule": "R2", "code": "contract-missing-key", "detail": f"mangler: {', '.join(missing)}"})

    # --- R3: hver PÅKREVD nøkkel som FINNES er en array av strenger --------
    bad_type = [k for k in REQUIRED_KEYS if k in data and not _is_str_array(data[k])]
    if bad_type:
        violations.append({"rule": "R3", "code": "contract-bad-type", "detail": f"ikke array av strenger: {', '.join(bad_type)}"})

    have_required = not missing and not bad_type
    if not have_required:
        # D1.4: R10 er IKKE med her lenger — R10 sjekkes ubetinget
        # under attestations-grenen og skal aldri kunne rapporteres som
        # BÅDE brudd og hoppet i samme output.
        skipped.extend(["R5", "R6", "R7", "R8", "R9"])
        # attestations kan fortsatt vurderes isolert (R4), men R5 (som
        # sammenligner mot returned) gir ikke mening uten et gyldig returned.
        dispatched = returned = expected = frozenset()
    else:
        dispatched = set(data["dispatched"])
        returned = set(data["returned"])
        expected = set(data["expected_by_selector"])

    # --- attestations (PÅKREVD når --require-attestations og returned != tom) --
    attestations = data.get("attestations")
    attestations_present = "attestations" in data
    attest_agents = None

    if attestations_present:
        if not isinstance(attestations, list):
            violations.append({"rule": "R4", "code": "attestation-malformed", "detail": "attestations er ikke en array"})
            attestations = []
        malformed = False
        agents = []
        for entry in attestations:
            if not isinstance(entry, dict) or not isinstance(entry.get("agent"), str):
                malformed = True
                continue
            for key in ("toplevel", "reviewed_sha"):
                if key in entry and entry[key] is not None and not isinstance(entry[key], str):
                    malformed = True
            agents.append(entry.get("agent"))
        if malformed:
            violations.append({"rule": "R4", "code": "attestation-malformed", "detail": "en eller flere entries mangler gyldig agent, eller toplevel/reviewed_sha er verken streng eller null"})
        attest_agents = set(agents)

        # --- R5: attestasjonssettet matcher returned ------------------------
        if have_required:
            if attest_agents != returned:
                violations.append({"rule": "R5", "code": "attestation-mismatch", "detail": f"attestations-agenter {sorted(attest_agents)} != returned {sorted(returned)}"})
        else:
            skipped.append("R5")

        # --- R10: stale-lens-sha (normalisert) ---------
        if pr_head_sha is not None:
            stale = []
            unnormalizable = []
            pr_sha_n = _normalize_sha(pr_head_sha) or pr_head_sha.lower()
            for entry in attestations:
                if not isinstance(entry, dict):
                    continue
                rs = entry.get("reviewed_sha")
                if rs is None:
                    continue
                rs_n = _normalize_sha(rs)
                if rs_n is None:
                    # Unnormaliserbar (for kort / ikke-hex): NULL-SEMANTIKK.
                    # Hoppes, rutes ALDRI til attestation-malformed (R4).
                    unnormalizable.append(entry.get("agent"))
                    continue
                n = min(len(rs_n), len(pr_sha_n))
                if rs_n[:n] != pr_sha_n[:n]:
                    stale.append(entry.get("agent"))
            if stale:
                violations.append({"rule": "R10", "code": "stale-lens-sha", "detail": f"reviewed_sha avviker fra --pr-head-sha for: {sorted(a for a in stale if a)}"})
            for ag in unnormalizable:
                skipped.append(f"R10:unnormalizable:{ag}")
        else:
            skipped.append("R10")
    else:
        # R4 gir ikke mening uten en attestations-nøkkel å validere formen på —
        # ført som skipped for symmetri med R5/R10, som av samme grunn (ingen
        # attestations å sammenligne/tidsstemple mot) også hoppes her.
        skipped.append("R4")
        skipped.append("R5")
        skipped.append("R10")

    # --- R11: attestations-missing (--require-attestations) -----
    # `returned`-leddet er IKKE pynt: uten det fyrer R11 på hver eneste runde
    # uten lens-trigger (selector=none, flertallet av rundene).
    if require_attestations and returned and not attestations_present:
        violations.append({"rule": "R11", "code": "attestations-missing", "detail": "attestations mangler mens --require-attestations er gitt og returned er ikke-tom"})

    if have_required:
        # --- R6: returned ⊆ dispatched -------------------------------------
        fabricated = returned - dispatched
        if fabricated:
            violations.append({"rule": "R6", "code": "returned-not-dispatched", "detail": f"i returned, ikke i dispatched: {sorted(fabricated)}"})

        # --- R7: dispatched \ returned == ∅ (stille node) -------------------
        silent = dispatched - returned
        if silent:
            violations.append({"rule": "R7", "code": "silent-node", "detail": f"dispatchet men ikke returnert: {sorted(silent)}"})

        # --- R8: dispatched ⊆ known_agents (VAKUØS når known_agents er tom,
        # et kit uten registrerte lenser er en gyldig konfigurasjon,
        # og skal ikke flagge ALLE dispatchede navn som "ukjente") ------------
        if known_agents:
            unknown = dispatched - known_agents
            if unknown:
                violations.append({"rule": "R8", "code": "unknown-agent", "detail": f"ukjent(e) agent(er) i dispatched: {sorted(unknown)}"})
        else:
            skipped.append("R8")

        # --- R9: expected_by_selector ⊆ dispatched --------------------------
        under = expected - dispatched
        if under:
            violations.append({"rule": "R9", "code": "under-dispatch", "detail": f"forventet av selector, ikke dispatchet: {sorted(under)}"})

    # --- R12/R14: liveness (D1.3/D1.4). Første treff vinner ------
    # (uttømmende tabell, D1.3): rad 0 (ingen nøkkel), 0b (R14 fyrte), 1
    # (have_required usann), 2-5 (mode=unavailable/ledger), 6-10
    # (mode=worktree), 11 (ellers — evaluert, rent, ingen oppføring).
    if live is None:
        # rad 0 — ingen --live-key: R12 OG R14 BEGGE i BAR form
        skipped.append("R12")
        skipped.append("R14")
    elif live["mode"] == "unreadable":
        # rad 0b — R14 er et brudd; R12 hoppes med kvalifisert grunn
        violations.append({"rule": "R14", "code": "live-key-unreadable", "detail": live.get("detail", "")})
        skipped.append("R12:live-key-unreadable")
    elif not have_required:
        # rad 1 — R2/R3 fyrte, ingenting meningsfullt å evaluere R12 mot
        skipped.append("R12:no-required-keys")
    elif live["mode"] == "unavailable":
        # rad 2 — den målte normaltilstanden (§ 0.1)
        skipped.append("R12:unavailable")
    elif live["mode"] == "ledger":
        ledger = set(live.get("ledger") or [])
        if not returned:
            # rad 3 — vakuøs: tom returned kan aldri gi et rødt utfall
            skipped.append("R12:vacuous")
        elif not ledger:
            # rad 4 — tom ledger kan aldri gi et FABRIKERT rødt utfall
            skipped.append("R12:empty-ledger")
        elif not returned <= ledger:
            # rad 5 — BRUDD: returnerte navn uten registrert signal i ledgeren
            violations.append({"rule": "R12", "code": "premature-return", "detail": f"returned ikke i ledger: {sorted(returned - ledger)}"})
        # else: rad 11 — evaluert, rent. Ingen oppføring (verken brudd eller hopp).
    else:
        # live["mode"] == "worktree"
        calibration = live.get("calibration")
        lens_isolation = live.get("lens_isolation")
        residual = set(live.get("residual_worktrees") or [])
        if calibration == "none":
            # rad 6 — fail-open: ukjent/uoppgitt kalibrering hopper, aldri brudd
            skipped.append("R12:calibration-none")
        elif lens_isolation != "own":
            # rad 7 — N3-falsifiseringen støpt i kode: lensen deler worktree
            # med koordinatoren/revieweren, og signalet kan da ikke skille dem
            skipped.append("R12:lens-not-isolated")
        elif calibration == "autoremove":
            if not live.get("mid_snapshot"):
                # rad 8 — uten mid-snapshot er "rad 2" ikke oppnåelig
                skipped.append("R12:no-mid-snapshot")
            elif residual:
                # rad 9 — BRUDD: worktree(r) sto igjen etter autoremove
                violations.append({"rule": "R12", "code": "premature-return", "detail": f"residual worktrees etter autoremove: {sorted(residual)}"})
            # else: rad 11
        elif calibration == "persistent":
            if not residual and dispatched:
                # rad 10 — BRUDD: ingen residual, men koordinatoren dispatchet
                violations.append({"rule": "R12", "code": "premature-return", "detail": "ingen residual worktrees, men dispatched er ikke tom (persistent)"})
            # else: rad 11

    signals_extra = {
        "dispatched_empty": have_required and len(dispatched) == 0,
        "attestations_present": attestations_present,
    }
    # Dedupliser: flere av grenene over kan legge til samme regel-ID i
    # overlappende scenarioer — signals.skipped er maskinlesbar JSON og skal
    # ikke rapportere samme hoppede regel to ganger. Sorteringsnøkkelen
    # håndterer BÅDE enkle ("R10") og kvalifiserte ("R10:unnormalizable:<agent>")
    # former — begge sorteres på regel-NUMMERET, sekundært på hele strengen.
    skipped = sorted(set(skipped), key=_skip_key)
    return violations, skipped, signals_extra


def compute_binding(violations, live_mode=None):
    """Mengden av fyrte koder som ligger i BINDING_CODES, ELLER i
    LIVE_BINDING_CODES når `live_mode == "ledger"` (D1.5).
    `premature-return` er dermed bindende KUN i mode=ledger — i mode=worktree
    kan den fyre som brudd, men teller ALDRI mot verdikt/eskalering."""
    codes = {v["code"] for v in violations if v["code"] in BINDING_CODES}
    if live_mode == "ledger":
        codes |= {v["code"] for v in violations if v["code"] in LIVE_BINDING_CODES}
    return codes


def compute_verdict(violations, strict, live_mode=None):
    """"rejected" når strict OG minst én bindende kode fyrte, ellers "observed"."""
    if strict and compute_binding(violations, live_mode=live_mode):
        return "rejected"
    return "observed"


def compute_mode(strict):
    """"strict" med --strict, "observe" uten (D1.2c)."""
    return "strict" if strict else "observe"


def compute_attest(violations, signals_extra, strict):
    """250A-verdien, prefikset med strict: når strict (D1.2b)."""
    if violations:
        codes = sorted({v["code"] for v in violations})
        base = ",".join(codes)
    elif signals_extra["dispatched_empty"]:
        base = "none"
    elif not signals_extra["attestations_present"]:
        base = "legacy"
    else:
        base = "ok"
    return f"strict:{base}" if strict else base


def run_analysis(path, pr_head_sha, strict=False, require_attestations=False, live_key_path=None):
    # Nøkkelfila lastes ØVERST, FØR load_fan_in, slik at `live` er i scope for
    # den ÉNE delte result["signals"]-dicten under — også R1-feilgrenen
    # (D1.0 iv). Skriptet leser ALDRI rapportens `evidence` her.
    live = live_state(*load_live_key(live_key_path)) if live_key_path is not None else None
    live_mode = None if live is None else live["mode"]
    data, err = load_fan_in(path)
    if err is not None:
        code, detail = err
        violations = [{"rule": "R1", "code": code, "detail": detail}]
        # R14 er UAVHENGIG av R1: `live` ble lastet FØR `load_fan_in` (se
        # kommentaren over) og skal ikke tapes bak R1-kortslutningen når
        # BEGGE filene er uleselige samtidig (samme
        # rad-0b-utfall som evaluate() ville gitt).
        if live is not None and live["mode"] == "unreadable":
            violations.append({"rule": "R14", "code": "live-key-unreadable", "detail": live.get("detail", "")})
            skipped = [rid for rid, _ in RULES if rid not in ("R1", "R12", "R14")]
            skipped.append("R12:live-key-unreadable")
        else:
            skipped = [rid for rid, _ in RULES if rid != "R1"]
        skipped = sorted(skipped, key=_skip_key)
        signals_extra = {"dispatched_empty": False, "attestations_present": False}
    else:
        violations, skipped, signals_extra = evaluate(data, pr_head_sha, require_attestations=require_attestations, live=live)

    verdict = compute_verdict(violations, strict, live_mode=live_mode)
    mode = compute_mode(strict)
    attest = compute_attest(violations, signals_extra, strict)
    result = {
        "mode": mode,
        "verdict": verdict,
        "violations": violations,
        "signals": {"attest": attest, "skipped": skipped, "known_agents": len(KNOWN_AGENTS), "live": live_token(live)},
    }
    print(f"[review-fan-in-verify] {mode} — attest={attest}, avvik: {len(violations)}, hoppet: {len(skipped)}", file=sys.stderr)
    print(json.dumps(result))
    return 3 if verdict == "rejected" else 0


# --- Frosne fixtures (13 + 11 nye, F24 realisert
# som TO poster ⇒ 25 poster i praksis; 13 nye, F25-F37,
# for R12/R14 ⇒ 38 poster; fix-runde 1 legger til 3 nye, F38-F40, for to
# udekkede D1.3-hoppgrener + R1-kortslutningens R14-tap ⇒ 41 poster totalt,
# D1.8) ------------------------------------------------------------------
def _fixture(name, payload, pr_head_sha=None, strict=False, require_attestations=False,
             expected_codes=(), expected_attest=None, expected_verdict="observed",
             expected_binding=(), expected_mode=None, expected_skipped=None,
             known_agents=None, live_key=None, live_key_path=None):
    # `live_key` (dict, skrives til en temp-fil og lastes) og `live_key_path`
    # (streng, sendes rett til load_live_key) er gjensidig utelukkende INPUT
    # (D1.0 ii) — begge satt samtidig er en FIXTURE-DEFEKT, ikke
    # en stille prioritering.
    if live_key is not None and live_key_path is not None:
        raise ValueError(f"{name}: live_key og live_key_path kan ikke begge være satt")
    return {
        "name": name,
        "payload": payload,
        "pr_head_sha": pr_head_sha,
        "strict": strict,
        "require_attestations": require_attestations,
        "expected_codes": sorted(expected_codes),
        "expected_attest": expected_attest,
        "expected_verdict": expected_verdict,
        "expected_binding": sorted(expected_binding),
        "expected_mode": expected_mode if expected_mode is not None else ("strict" if strict else "observe"),
        "expected_skipped": None if expected_skipped is None else sorted(expected_skipped, key=_skip_key),
        "known_agents": known_agents,
        "live_key": live_key,
        "live_key_path": live_key_path,
    }


def _fixtures():
    agents = sorted(KNOWN_AGENTS)
    a = agents[0] if agents else "rls-migration-reviewer"
    # `b` er KUN til bruk der et navn utenfor dispatched/KNOWN_AGENTS er selve
    # poenget (F6: en fabrikert returned-oppføring). Fallback er en åpenbart
    # syntetisk streng, aldri et prosjektspesifikt agentnavn — F8 bruker
    # samme mønster med "bogus-reviewer" literal.
    b = agents[1] if len(agents) > 1 else "bogus-reviewer"

    pr_sha_match = "aaaaaaa" + "0" * 33  # 40 tegn, prefiks "aaaaaaa"
    pr_sha_miss = "1111111" + "1" * 33  # 40 tegn, prefiks "1111111"

    return [
        # --- 13 arvet fra 250A (F1 ENDRET — r3 VIKTIG-2 + r4 VIKTIG-3) ------
        _fixture(
            "F1", {"path": "__MISSING__"}, strict=True, require_attestations=True,
            expected_codes=["input-unreadable"], expected_attest="strict:input-unreadable",
            expected_verdict="observed", expected_binding=[], expected_mode="strict",
        ),
        _fixture("F2", {"fan_in": {"triggered": [], "dispatched": [], "returned": []}},
                  expected_codes=["contract-missing-key"], expected_attest="contract-missing-key",
                  expected_binding=["contract-missing-key"]),
        _fixture("F3", {"fan_in": {"triggered": [], "dispatched": "not-an-array", "returned": [], "expected_by_selector": []}},
                  expected_codes=["contract-bad-type"], expected_attest="contract-bad-type",
                  expected_binding=["contract-bad-type"]),
        _fixture("F4", {"fan_in": {"triggered": [], "dispatched": [], "returned": [], "expected_by_selector": [], "attestations": [{"toplevel": "/x"}]}},
                  expected_codes=["attestation-malformed"], expected_attest="attestation-malformed",
                  expected_binding=["attestation-malformed"]),
        _fixture("F5", {"fan_in": {"triggered": [], "dispatched": [a], "returned": [a], "expected_by_selector": [], "attestations": []}},
                  expected_codes=["attestation-mismatch"], expected_attest="attestation-mismatch",
                  expected_binding=["attestation-mismatch"]),
        _fixture("F6", {"fan_in": {"triggered": [], "dispatched": [a], "returned": [a, b], "expected_by_selector": []}},
                  expected_codes=["returned-not-dispatched"], expected_attest="returned-not-dispatched",
                  expected_binding=[]),
        _fixture("F7", {"fan_in": {"triggered": [], "dispatched": [a], "returned": [], "expected_by_selector": []}},
                  expected_codes=["silent-node"], expected_attest="silent-node", expected_binding=[]),
        _fixture("F8", {"fan_in": {"triggered": [], "dispatched": ["bogus-reviewer"], "returned": ["bogus-reviewer"], "expected_by_selector": []}},
                  expected_codes=["unknown-agent"], expected_attest="unknown-agent", expected_binding=[]),
        _fixture("F9", {"fan_in": {"triggered": [], "dispatched": [], "returned": [], "expected_by_selector": [a]}},
                  expected_codes=["under-dispatch"], expected_attest="under-dispatch", expected_binding=[]),
        _fixture("F10", {"fan_in": {"triggered": [], "dispatched": [a], "returned": [a], "expected_by_selector": [], "attestations": [{"agent": a, "reviewed_sha": "bbbbbbb"}]}},
                  pr_head_sha="aaaaaaa", expected_codes=["stale-lens-sha"], expected_attest="stale-lens-sha",
                  expected_binding=["stale-lens-sha"]),
        _fixture("F11", {"fan_in": {"triggered": [], "dispatched": [a], "returned": [a], "expected_by_selector": []}},
                  expected_codes=[], expected_attest="legacy", expected_binding=[]),
        _fixture("F12", {"fan_in": {"triggered": [], "dispatched": [a], "returned": [a], "expected_by_selector": [], "attestations": [{"agent": a, "reviewed_sha": "aaaaaaa"}]}},
                  pr_head_sha="aaaaaaa", expected_codes=[], expected_attest="ok", expected_binding=[]),
        _fixture("F13", {"fan_in": {"triggered": [], "dispatched": [], "returned": [], "expected_by_selector": []}},
                  expected_codes=[], expected_attest="none", expected_binding=[]),

        # --- 11 nye (D1.5) ----------------------------------------
        _fixture(  # F14: R10 ikke både brudd og hoppet
            "F14", {"fan_in": {"triggered": [], "dispatched": [a], "returned": [a], "attestations": [{"agent": a, "reviewed_sha": "bbbbbbb"}]}},
            pr_head_sha=pr_sha_match,
            expected_codes=["contract-missing-key", "stale-lens-sha"],
            expected_attest="contract-missing-key,stale-lens-sha",
            expected_binding=["contract-missing-key", "stale-lens-sha"],
            expected_skipped=["R5", "R6", "R7", "R8", "R9", "R12", "R14"],
        ),
        _fixture(  # F15: over-attestasjon (fabrikasjonsretningen)
            "F15", {"fan_in": {"triggered": [], "dispatched": [a], "returned": [a], "expected_by_selector": [],
                                "attestations": [{"agent": a, "reviewed_sha": "aaaaaaa"}, {"agent": b, "reviewed_sha": "aaaaaaa"}]}},
            pr_head_sha="aaaaaaa",
            expected_codes=["attestation-mismatch"], expected_attest="attestation-mismatch",
            expected_binding=["attestation-mismatch"],
        ),
        _fixture(  # F16: 7-tegns prefiks som MATCHER 40-tegns
            "F16", {"fan_in": {"triggered": [], "dispatched": [a], "returned": [a], "expected_by_selector": [],
                                "attestations": [{"agent": a, "reviewed_sha": "aaaaaaa"}]}},
            pr_head_sha=pr_sha_match, expected_codes=[], expected_attest="ok", expected_binding=[],
        ),
        _fixture(  # F17: 7-tegns prefiks som IKKE matcher
            "F17", {"fan_in": {"triggered": [], "dispatched": [a], "returned": [a], "expected_by_selector": [],
                                "attestations": [{"agent": a, "reviewed_sha": "bbbbbbb"}]}},
            pr_head_sha=pr_sha_match, expected_codes=["stale-lens-sha"], expected_attest="stale-lens-sha",
            expected_binding=["stale-lens-sha"],
        ),
        _fixture(  # F18: for kort/ikke-hex ⇒ INGEN violation, R10:unnormalizable i skipped
            "F18", {"fan_in": {"triggered": [], "dispatched": [a], "returned": [a], "expected_by_selector": [],
                                "attestations": [{"agent": a, "reviewed_sha": "abcdef"}]}},
            pr_head_sha=pr_sha_miss, expected_codes=[], expected_attest="ok", expected_binding=[],
            expected_skipped=[f"R10:unnormalizable:{a}", "R12", "R14"],
        ),
        _fixture(  # F19 — R11 PÅ: strict + require_attestations + returned≠∅ + manglende nøkkel
            "F19", {"fan_in": {"triggered": [], "dispatched": [a], "returned": [a], "expected_by_selector": []}},
            strict=True, require_attestations=True,
            expected_codes=["attestations-missing"], expected_attest="strict:attestations-missing",
            expected_verdict="rejected", expected_binding=["attestations-missing"], expected_mode="strict",
        ),
        _fixture(  # F20 — R11 negativ: require_attestations + returned == [] ⇒ INGEN violation
            "F20", {"fan_in": {"triggered": [], "dispatched": [], "returned": [], "expected_by_selector": []}},
            strict=True, require_attestations=True,
            expected_codes=[], expected_attest="strict:none", expected_verdict="observed",
            expected_binding=[], expected_mode="strict",
        ),
        _fixture(  # F21: tom agent-mengde SOM PARAMETER ⇒ R8 vakuøs, attest=none
            "F21", {"fan_in": {"triggered": [], "dispatched": [], "returned": [], "expected_by_selector": []}},
            known_agents=frozenset(),
            expected_codes=[], expected_attest="none", expected_binding=[],
            expected_skipped=["R4", "R5", "R8", "R10", "R12", "R14"],
        ),
        _fixture(  # F22 — --strict på fixture som KUN gir R6-R9 ⇒ observed, exit 0
            "F22", {"fan_in": {"triggered": [], "dispatched": [a], "returned": [a, b], "expected_by_selector": []}},
            strict=True,
            expected_codes=["returned-not-dispatched"], expected_attest="strict:returned-not-dispatched",
            expected_verdict="observed", expected_binding=[], expected_mode="strict",
        ),
        _fixture(  # F23 — r2 VIKTIG-5: reviewed_sha: null + --pr-head-sha gitt ⇒ INGEN violation (escapen)
            "F23", {"fan_in": {"triggered": [], "dispatched": [a], "returned": [a], "expected_by_selector": [],
                                "attestations": [{"agent": a, "reviewed_sha": None}]}},
            pr_head_sha=pr_sha_match, expected_codes=[], expected_attest="ok", expected_binding=[],
        ),
        _fixture(  # F24a — strict: true ⇒ signals.attest bærer strict:-prefikset
            "F24a", {"fan_in": {"triggered": [], "dispatched": [a], "returned": [a], "expected_by_selector": []}},
            strict=True,
            expected_codes=[], expected_attest="strict:legacy", expected_verdict="observed",
            expected_binding=[], expected_mode="strict",
        ),
        _fixture(  # F24b — SAMME payload, strict: false ⇒ ingen prefiks
            "F24b", {"fan_in": {"triggered": [], "dispatched": [a], "returned": [a], "expected_by_selector": []}},
            strict=False,
            expected_codes=[], expected_attest="legacy", expected_verdict="observed",
            expected_binding=[], expected_mode="observe",
        ),

        # --- 13 nye (D1.8) — R12 premature-return / R14 -----------
        # live-key-unreadable. `a`/`b` er de samme to KNOWN_AGENTS-navnene som
        # over. Ingen av disse payloadene bærer `attestations`, så alle arver
        # R4/R5/R10 i skipped fra "ingen attestations"-grenen (D1.0), med
        # mindre annet er dokumentert under.
        _fixture(  # F25 — rad 4: tom ledger kan aldri gi et FABRIKERT rødt utfall (B1-fiksen)
            "F25", {"fan_in": {"triggered": [], "dispatched": [a], "returned": [a], "expected_by_selector": []}},
            live_key={"mode": "ledger", "ledger": []},
            expected_codes=[], expected_attest="legacy", expected_binding=[],
            expected_skipped=["R4", "R5", "R10", "R12:empty-ledger"],
        ),
        _fixture(  # F26 — rad 11: returned ⊆ ledger ⇒ evaluert, rent, INGEN oppføring
            "F26", {"fan_in": {"triggered": [], "dispatched": [a], "returned": [a], "expected_by_selector": []}},
            live_key={"mode": "ledger", "ledger": [a]},
            expected_codes=[], expected_attest="legacy", expected_binding=[],
            expected_skipped=["R4", "R5", "R10"],
        ),
        _fixture(  # F27 — rad 5: BRUDD, --strict + mode=ledger ⇒ bindende
            "F27", {"fan_in": {"triggered": [], "dispatched": [a, b], "returned": [a, b], "expected_by_selector": []}},
            live_key={"mode": "ledger", "ledger": [a]}, strict=True,
            expected_codes=["premature-return"], expected_attest="strict:premature-return",
            expected_verdict="rejected", expected_binding=["premature-return"], expected_mode="strict",
            expected_skipped=["R4", "R5", "R10"],
        ),
        _fixture(  # F28 — SAMME payload/nøkkel som F27, uten --strict ⇒ samme kode fyrer,
            # men verdikt forblir observed (strict er alltid ANDret inn i compute_verdict).
            # compute_binding avhenger KUN av live_mode (D1.5/D1.0 iii, ikke av --strict) —
            # koden telles derfor fortsatt som "binding-kandidat" her; det er --strict som
            # avgjør om den FAKTISK fører til avvisning.
            "F28", {"fan_in": {"triggered": [], "dispatched": [a, b], "returned": [a, b], "expected_by_selector": []}},
            live_key={"mode": "ledger", "ledger": [a]}, strict=False,
            expected_codes=["premature-return"], expected_attest="premature-return",
            expected_verdict="observed", expected_binding=["premature-return"], expected_mode="observe",
            expected_skipped=["R4", "R5", "R10"],
        ),
        _fixture(  # F29 — rad 2: mode=unavailable ⇒ hopp, uansett --strict (den målte normaltilstanden)
            "F29", {"fan_in": {"triggered": [], "dispatched": [], "returned": [], "expected_by_selector": []}},
            live_key={"mode": "unavailable"}, strict=True,
            expected_codes=[], expected_attest="strict:none", expected_binding=[], expected_mode="strict",
            expected_skipped=["R4", "R5", "R10", "R12:unavailable"],
        ),
        _fixture(  # F30 — rad 7: N3-falsifiseringen støpt i kode (lensen deler worktree)
            "F30", {"fan_in": {"triggered": [], "dispatched": [a], "returned": [a], "expected_by_selector": []}},
            live_key={"mode": "worktree", "calibration": "persistent", "lens_isolation": "inherited",
                       "residual_worktrees": [], "mid_snapshot": False},
            expected_codes=[], expected_attest="legacy", expected_binding=[],
            expected_skipped=["R4", "R5", "R10", "R12:lens-not-isolated"],
        ),
        _fixture(  # F31 — rad 10: BRUDD (persistent, egen worktree, ingen residual, dispatched≠∅).
            # mode=worktree ⇒ ALDRI bindende (compute_binding krever live_mode=="ledger"),
            # så verdikt forblir observed selv om koden fyrer.
            "F31", {"fan_in": {"triggered": [], "dispatched": [a], "returned": [a], "expected_by_selector": []}},
            live_key={"mode": "worktree", "calibration": "persistent", "lens_isolation": "own",
                       "residual_worktrees": [], "mid_snapshot": False},
            expected_codes=["premature-return"], expected_attest="premature-return",
            expected_verdict="observed", expected_binding=[],
            expected_skipped=["R4", "R5", "R10"],
        ),
        _fixture(  # F32 — rad 8: autoremove uten mid-snapshot ⇒ hopp ("rad 2" uoppnåelig uten den)
            "F32", {"fan_in": {"triggered": [], "dispatched": [a], "returned": [a], "expected_by_selector": []}},
            live_key={"mode": "worktree", "calibration": "autoremove", "lens_isolation": "own",
                       "mid_snapshot": False, "residual_worktrees": []},
            expected_codes=[], expected_attest="legacy", expected_binding=[],
            expected_skipped=["R4", "R5", "R10", "R12:no-mid-snapshot"],
        ),
        _fixture(  # F33 — rad 9: BRUDD (autoremove, mid-snapshot fantes, residual likevel ikke-tom)
            "F33", {"fan_in": {"triggered": [], "dispatched": [a], "returned": [a], "expected_by_selector": []}},
            live_key={"mode": "worktree", "calibration": "autoremove", "lens_isolation": "own",
                       "mid_snapshot": True, "residual_worktrees": ["/x"]},
            expected_codes=["premature-return"], expected_attest="premature-return",
            expected_verdict="observed", expected_binding=[],
            expected_skipped=["R4", "R5", "R10"],
        ),
        _fixture(  # F34 — rad 6: calibration=none ⇒ fail-open, hopp
            "F34", {"fan_in": {"triggered": [], "dispatched": [a], "returned": [a], "expected_by_selector": []}},
            live_key={"mode": "worktree", "calibration": "none", "lens_isolation": "own"},
            expected_codes=[], expected_attest="legacy", expected_binding=[],
            expected_skipped=["R4", "R5", "R10", "R12:calibration-none"],
        ),
        _fixture(  # F35 — R14: --live-key peker på ikke-eksisterende fil. Aldri bindende
            # (live-key-unreadable er IKKE i BINDING_CODES) ⇒ observed selv med --strict.
            "F35", {"fan_in": {"triggered": [], "dispatched": [a], "returned": [a], "expected_by_selector": []}},
            live_key_path="__MISSING_LIVE_KEY__", strict=True,
            expected_codes=["live-key-unreadable"], expected_attest="strict:live-key-unreadable",
            expected_verdict="observed", expected_binding=[], expected_mode="strict",
            expected_skipped=["R4", "R5", "R10", "R12:live-key-unreadable"],
        ),
        _fixture(  # F36 — R14, enum-grenen: mode utenfor {"ledger","worktree","unavailable"}
            "F36", {"fan_in": {"triggered": [], "dispatched": [a], "returned": [a], "expected_by_selector": []}},
            live_key={"mode": "hokus"},
            expected_codes=["live-key-unreadable"], expected_attest="live-key-unreadable",
            expected_verdict="observed", expected_binding=[],
            expected_skipped=["R4", "R5", "R10", "R12:live-key-unreadable"],
        ),
        _fixture(  # F37 — rad 0: ingen --live-key ⇒ R12 OG R14 BEGGE i BAR form
            "F37", {"fan_in": {"triggered": [], "dispatched": [a], "returned": [a], "expected_by_selector": []}},
            strict=True,
            expected_codes=[], expected_attest="strict:legacy", expected_binding=[], expected_mode="strict",
            expected_skipped=["R4", "R5", "R10", "R12", "R14"],
        ),

        # --- 3 nye (to udekkede D1.3-
        # hoppgrener + R1-kortslutningens tap av R14) -------------------------
        _fixture(  # F38 — rad 1: manglende påkrevd nøkkel MED en gyldig --live-key
            # til stede ⇒ "not have_required" avgjøres FØR mode-sjekkene,
            # uavhengig av hvilken gyldig mode nøkkelen bærer.
            "F38", {"fan_in": {"dispatched": [], "returned": [], "expected_by_selector": []}},
            live_key={"mode": "unavailable"},
            expected_codes=["contract-missing-key"], expected_attest="contract-missing-key",
            expected_binding=["contract-missing-key"],
            expected_skipped=["R4", "R5", "R6", "R7", "R8", "R9", "R10", "R12:no-required-keys"],
        ),
        _fixture(  # F39 — rad 3: mode=ledger, tom `returned` ⇒ vakuøs (kan aldri gi et
            # rødt utfall), skilt fra F25s tomme LEDGER (rad 4).
            "F39", {"fan_in": {"triggered": [], "dispatched": [], "returned": [], "expected_by_selector": []}},
            live_key={"mode": "ledger", "ledger": [a]},
            expected_codes=[], expected_attest="none", expected_binding=[],
            expected_skipped=["R4", "R5", "R10", "R12:vacuous"],
        ),
        _fixture(  # F40 — R1-kortslutningen (run_analysis/--self-test) skal IKKE tape
            # R14 når BEGGE `--fan-in` og `--live-key` er uleselige samtidig.
            "F40", {"path": "__MISSING__"}, live_key_path="__MISSING_LIVE_KEY__", strict=True,
            expected_codes=["input-unreadable", "live-key-unreadable"],
            expected_attest="strict:input-unreadable,live-key-unreadable",
            expected_verdict="observed", expected_binding=[], expected_mode="strict",
            expected_skipped=["R2", "R3", "R4", "R5", "R6", "R7", "R8", "R9", "R10", "R11", "R12:live-key-unreadable"],
        ),
    ]


def run_self_test():
    fixtures = _fixtures()
    total = len(fixtures)
    passed = 0
    results = []
    covered_codes = set()

    for fx in fixtures:
        payload = fx["payload"]
        covered_codes.update(fx["expected_codes"])
        if "path" in payload:
            path = payload["path"]
        else:
            fd, path = tempfile.mkstemp(prefix="fan-in-verify-selftest-")
            with os.fdopen(fd, "w") as f:
                json.dump(payload["fan_in"], f)

        # --- live-nøkkel (D1.0 iii) — dict skrives til en EGEN
        # temp-fil (samme mekanisme som payload["fan_in"] over); streng sendes
        # rett til load_live_key (samme mekanisme som payload["path"] for R1).
        # Begge None ⇒ live = None (ingen --live-key). live_tmp_path ryddes i
        # en EGEN, ubetinget opprydding under — ALDRI i samme betingede blokk
        # som fan-in-temp-fila, som kun rydder "path" ikke er i payload.
        live_tmp_path = None
        if fx["live_key"] is not None:
            live_fd, live_tmp_path = tempfile.mkstemp(prefix="fan-in-verify-selftest-live-")
            with os.fdopen(live_fd, "w") as f:
                json.dump(fx["live_key"], f)
            live_obj, live_err = load_live_key(live_tmp_path)
        elif fx["live_key_path"] is not None:
            live_obj, live_err = load_live_key(fx["live_key_path"])
        else:
            live_obj, live_err = None, None
        live = live_state(live_obj, live_err)
        live_mode = None if live is None else live["mode"]

        data, err = load_fan_in(path)
        if err is not None:
            code, detail = err
            violations = [{"rule": "R1", "code": code, "detail": detail}]
            # Samme rad-0b-bevaring som run_analysis (over) — R14 skal ikke
            # tapes bak R1-kortslutningen når begge filene er uleselige samtidig
            # (MINDRE-funn).
            if live is not None and live["mode"] == "unreadable":
                violations.append({"rule": "R14", "code": "live-key-unreadable", "detail": live.get("detail", "")})
                skipped = [rid for rid, _ in RULES if rid not in ("R1", "R12", "R14")]
                skipped.append("R12:live-key-unreadable")
            else:
                skipped = [rid for rid, _ in RULES if rid != "R1"]
            skipped = sorted(skipped, key=_skip_key)
            signals_extra = {"dispatched_empty": False, "attestations_present": False}
        else:
            violations, skipped, signals_extra = evaluate(
                data, fx["pr_head_sha"],
                require_attestations=fx["require_attestations"],
                known_agents=fx["known_agents"],
                live=live,
            )

        if "path" not in payload:
            os.unlink(path)
        if live_tmp_path is not None:
            os.unlink(live_tmp_path)

        strict = fx["strict"]
        actual_codes = sorted({v["code"] for v in violations})
        actual_binding = sorted(compute_binding(violations, live_mode=live_mode))
        actual_verdict = compute_verdict(violations, strict, live_mode=live_mode)
        actual_mode = compute_mode(strict)
        actual_attest = compute_attest(violations, signals_extra, strict)

        ok = (
            fx["expected_codes"] == actual_codes
            and (fx["expected_attest"] is None or fx["expected_attest"] == actual_attest)
            and fx["expected_verdict"] == actual_verdict
            and fx["expected_binding"] == actual_binding
            and fx["expected_mode"] == actual_mode
            and (fx["expected_skipped"] is None or fx["expected_skipped"] == skipped)
        )
        results.append({
            "name": fx["name"],
            "expected": {"codes": fx["expected_codes"], "attest": fx["expected_attest"], "verdict": fx["expected_verdict"], "binding": fx["expected_binding"], "mode": fx["expected_mode"]},
            "actual": {"codes": actual_codes, "attest": actual_attest, "verdict": actual_verdict, "binding": actual_binding, "mode": actual_mode, "skipped": skipped},
            "pass": ok,
        })
        status = "PASS" if ok else "FEIL"
        print(f"[review-fan-in-verify --self-test] {fx['name']}: {status} (forventet {fx['expected_codes']}/{fx['expected_attest']}/{fx['expected_verdict']}/{fx['expected_mode']}, fikk {actual_codes}/{actual_attest}/{actual_verdict}/{actual_mode})", file=sys.stderr)
        if ok:
            passed += 1

    # --- Dekningsassertion (V-COV) — manglende dekning ⇒ exit 1 uansett -----
    all_codes = {code for _, code in RULES}
    missing_cov = sorted(all_codes - covered_codes)
    cov_ok = not missing_cov
    if not cov_ok:
        print(f"[review-fan-in-verify --self-test] DEKNINGSASSERTION FEILET — koder uten fixture: {missing_cov}", file=sys.stderr)

    print(f"[review-fan-in-verify --self-test] {passed}/{total}", file=sys.stderr)
    print(json.dumps({"passed": passed, "total": total, "coverage_ok": cov_ok, "missing_coverage": missing_cov, "results": results}))
    return (passed == total) and cov_ok


def run_dump_rules():
    for rule_id, code in RULES:
        if code in BINDING_CODES:
            klass = "stopp"
        elif code in LIVE_BINDING_CODES:
            klass = "betinget"
        else:
            klass = "logg"
        print(f"{rule_id}\t{code}\t{klass}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--fan-in", help="Fil med fan_in-JSON-objekt, eller '-' for stdin.")
    ap.add_argument("--pr-head-sha", default=None, help="PR-ens HEAD-SHA, for stale-lens-sha-sjekken (R10).")
    ap.add_argument("--strict", action="store_true", help="Arm kontrakt-vakten: exit 3 + verdict=rejected når minst én kode i BINDING_CODES fyrer.")
    ap.add_argument("--require-attestations", action="store_true", help="Aktiver R11 (attestations-missing) sammen med --strict.")
    ap.add_argument("--live-key", default=None, help="Fil med koordinatorens live-nøkkel-JSON (mode/calibration/lens_isolation/mid_snapshot/ledger/residual_worktrees), for R12 premature-return. Skrives av koordinatoren fra EGNE worktree-/ledger-snapshots — ALDRI avledet fra --fan-in sin egen evidence.")
    ap.add_argument("--self-test", action="store_true", help="Kjør de frosne fixturene.")
    ap.add_argument("--dump-rules", action="store_true", help="Skriv TSV av alle tretten reglene (R13 utelatt).")
    args = ap.parse_args()

    if args.dump_rules:
        run_dump_rules()
        return

    if args.self_test:
        ok = run_self_test()
        sys.exit(0 if ok else 1)

    if not args.fan_in:
        sys.exit("FEIL: --fan-in er påkrevd (eller bruk --dump-rules / --self-test).")

    sys.exit(run_analysis(args.fan_in, args.pr_head_sha, strict=args.strict, require_attestations=args.require_attestations, live_key_path=args.live_key))


if __name__ == "__main__":
    main()
