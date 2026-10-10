# /setup — kompiler loop.config.yaml inn i kit-et

> **Installasjon:** kopier denne fila til prosjektets `.claude/commands/setup.md`
> så den blir kjørbar som `/setup`. Den er bevisst IKKE tokenisert — den er
> bootstrapperen som *gjør* tokeniseringen, ikke en del av det genererte kit-et.
> Denne fila holdes byte-identisk med `.claude/commands/setup.md` (`diff -q` MÅ gi exit 0) —
> endrer du den ene, kopier til den andre i samme PR.

Du kjører `/setup` i et prosjekt som har lagt v3-mappen
(`v3-agent-orchestrator/`) i roten og fylt ut `loop.config.yaml`. Kommandoen
leser config-en og **kompilerer** templates inn i prosjektets faktiske stier.

## Prinsipper (ufravikelige)

1. **Deterministisk substitusjon for sikkerhetsverdier.** Miljø-IDer,
   branch-navn og verifiserings-kommandoer erstattes av skriptet under — ikke
   av at du «redigerer inn» verdier med skjønn. Null sjanse for et hallusinert
   prosjekt-ID i et charter. Du driver skriptet; du skriver ikke verdiene selv.
2. **Validerings-gate — feil høyt.** Skriptet stopper hardt hvis (a) en påkrevd
   config-nøkkel mangler, eller (b) det gjenstår `{{...}}`-tokens etter
   substitusjon. En charter med `{{DEV_ENV_ID}}` igjen skal ALDRI genereres.
3. **Idempotent + «GENERERT»-merking.** Re-kjøring overskriver de genererte
   filene rent. Hver generert fil bærer en header som sier «ikke rediger her».
4. **Kilde vs. generert adskilt.** Templates (med tokens) blir liggende i
   `v3-agent-orchestrator/templates/`. Skriptet skriver generert output til
   prosjektets `.claude/`, `docs/`, `tasks/`. Du kan alltid diffe de to.
5. **Prosjekt-eide filer seedes, aldri overskrives.** `CLAUDE.md`, lessons-katalogen,
   lessons-tema-mappene, agent-minnet, doc-skjelettene, `tasks/queue-config.py` og
   `docs/superpowers/loop/artifacts.md` skrives kun hvis de mangler.
   Kit-eide regler ligger i den genererte `docs/loop-rules.md`, som `CLAUDE.md` importerer.
6. **Eksisterende prosjektfiler merges minimalt og idempotent.** `.claude/settings.json` får
   kun kit-ets egne hook-oppføringer (nøkkel = kommandostrengen), `CLAUDE.md` får én
   `@docs/loop-rules.md`-linje hvis den mangler, `.gitignore` får runtime-filene. Alt annet i
   filene bevares. `/setup` sletter aldri — en avslått hook rapporteres, fjernes ikke.
7. **Avslutt med restart + probe.** Agent-registeret lastes ved sesjonsstart.
   Etter `/setup`: start en FERSK sesjon og kjør agent-proben fra
   `run-loop.md` for å bekrefte at `<project>-*`-agentene er registrert.

## Steg

1. Bekreft at `v3-agent-orchestrator/loop.config.yaml` finnes og er fylt
   (ikke `loop.config.example.yaml` — kopier og fyll den først).
2. Kjør substitusjons-skriptet under fra prosjektroten. Det validerer, renamer
   agentene til `<project_name>-*`, substituerer alle tokens, prepender
   GENERERT-headeren, og skriver til prosjektets stier.
3. Les skriptets sluttrapport. Gjenværende-token-feil eller manglende-nøkkel-feil
   → fiks config / templates og kjør på nytt. Aldri fortsett med en delvis
   generert kit.
4. **Tech-review-agenter:** kopier prosjektets egne domene-reviewere inn i
   `.claude/agents/` (se `v3-agent-orchestrator/examples/` for maler). Disse
   er pluggbare — code-revieweren dispatcher dem etter `tech_review_agents` i
   config, og read-only-kontrakten (`.claude/hooks/reviewer-readonly.contract`)
   genereres fra samme liste. Hver av dem MÅ ha `disallowedTools: Write, Edit`
   (hook-harnessens D5 sjekker det). Har prosjektet ingen → `tech_review_agents: []`.
5. **Stillas:** hvis prosjektet ikke allerede har det, kopier scaffolding
   (`githooks/` → `.githooks/` med `pre-push` + `pre-commit`, CI-workflow med
   `todo-nr-guard`) og sett `git config core.hooksPath .githooks` — se README steg 8.
6. **Kjør vakt-harnessene** (de ble generert sammen med hookene):
   `bash .claude/hooks/test-guard-main-merge.sh` og
   `bash .claude/hooks/test-guard-reviewer-readonly.sh` — begge skal gi `AVVIK: 0`.
7. Commit de genererte filene. Start fersk sesjon (hooks og agenter lastes ved
   sesjonsstart). Kjør `/run-loop once`.

## Token-tabell (kanonisk vokabular)

Hver `{{TOKEN}}` i `templates/` mapper til én config-nøkkel. Skriptet er
autoritativt; tabellen er for mennesker.

| Token | Config-nøkkel |
|---|---|
| `{{PROJECT_NAME}}` | `project_name` (også agent-filnavn) |
| `{{GITHUB_REPO}}` | `github_repo` |
| `{{LANGUAGE}}` | `language` |
| `{{DEV_SERVER_PORT}}` | `dev_server_port` |
| `{{DEV_SERVER_PROCESS}}` | `dev_server_process` |
| `{{MODEL_PLANNER}}` / `{{EFFORT_PLANNER}}` | `models.planner` / `models.planner_effort` |
| `{{MODEL_REVIEWER}}` / `{{EFFORT_REVIEWER}}` | `models.reviewer` / `models.reviewer_effort` |
| `{{MODEL_IMPLEMENTER}}` / `{{EFFORT_IMPLEMENTER}}` | `models.implementer` / `models.implementer_effort` |
| `{{MODEL_CODE_REVIEWER}}` / `{{EFFORT_CODE_REVIEWER}}` | `models.code_reviewer` / `models.code_reviewer_effort` |
| `{{MODELS_DISPLAY}}` | utledes fra `models.planner/reviewer/implementer/code_reviewer` (`claude-opus-5-5` → `Opus5.5`); valgfri override `models.display` |
| `{{MODEL_SCOUT}}` / `{{EFFORT_SCOUT}}` | `models.scout` / `models.scout_effort` — påkrevd iff `scout.enabled` |
| `{{SCOUT_MAX_FINDINGS}}` | `scout.max_findings` — påkrevd iff `scout.enabled` |
| `{{SCOUT_AGENT_TOOL}}` | rendret `, Agent(<project>-scout)`-ledd for planner-/implementer-`tools:`-linja (tom streng når scout er av) |
| `{{SCOUT_DELEGATION_BLOCK}}` | rendret delegerings-seksjon i planner-/implementer-charteret (tom streng når scout er av) |
| `{{SCOUT_PROBE_BULLET}}` | rendret probe-punkt i `run-loop.md`s preflight (tom streng når scout er av) |
| `{{SCOUT_MODEL_ROW}}` | rendret rad i Modeller-tabellen i `docs/orchestration-loop.md` (tom streng når scout er av) |
| `{{SCOUT_USAGE_LINE}}` | rendret `scout_usage`-linje i plan-/ferdig-rapport-eksemplene i `report-schema.md` (tom streng når scout er av) |
| `{{DEV_ENV_ID}}` / `{{PROD_ENV_ID}}` | `environments.dev_id` / `environments.prod_id` |
| `{{BASE_BRANCH}}` / `{{RELEASE_BRANCH}}` / `{{PROD_BRANCH}}` | `branch_strategy.*` |
| `{{CMD_BUILD}}` / `{{CMD_TYPE_CHECK}}` / `{{CMD_TYPE_CHECK_SCRIPT}}` / `{{CMD_LINT}}` / `{{CMD_FORMAT_CHECK}}` / `{{CMD_TEST}}` / `{{CMD_E2E}}` / `{{CMD_WEB_SMOKE}}` / `{{CMD_E2E_PROBE}}` | `verification_commands.*` |
| `{{TIER1_INVARIANTS}}` | `tier1_invariants` (blokk) |
| `{{TECH_REVIEW_AGENTS_DISPATCH}}` | `tech_review_agents` (rendret blokk, inkl. `trigger_globs` per agent — B2a) |
| `{{TECH_REVIEW_AGENT_NAMES}}` | `tech_review_agents[].name` (rendret `Agent(...)`-ledd for `tools:`-linja, tom streng hvis ingen konfigurert) |
| `{{TECH_REVIEW_TRIGGER_GLOBS}}` | `tech_review_agents[].trigger_globs` (rendret Python-dict-literal `{navn: [glob, …]}`, brukt av `tasks/review-lens-select.py` — TODO 180A) |
| `{{TECH_REVIEW_SEVERITY_FLOORS}}` | `tech_review_agents[].severity_floor` (rendret Python-dict-literal `{navn: gulv-eller-None}`, brukt av `tasks/review-severity-floor.py` OG `tasks/review-fan-in-verify.py` — TODO 180B; CF-250-6) |
| `{{TECH_REVIEW_FLOOR_EXEMPTIONS}}` | `tech_review_agents[].floor_exempt` (valgfri; rendret Python-dict-literal `{navn: [klasse, …]}`, `[]` for agenter uten nøkkelen, brukt av `tasks/review-severity-floor.py` — TODO 321) |
| `{{CANARY_FILE}}` | `canary_source` |
| `{{PAUSE_TRIGGERS}}` | `pause_triggers` |
| `{{RELEASE_COMMAND}}` | `release.command` |
| `{{HEALTH_CHECK_INTERVAL}}` | `release.health_check_merge_interval` |
| `{{PIPELINE_MAX_IN_FLIGHT}}` | `pipelining.max_in_flight` — valgfri nøkkel, default `0` |
| `{{PARALLEL_IMPLEMENTERS_MAX}}` | `parallel_implementers.max` — valgfri nøkkel, default `1` (TODO 233, §5d) |
| `{{MEMORY_PLANNER}}` | `agent_memory.scope` + `agent_memory.enabled_roles` (planner) — valgfri nøkkel |
| `{{MEMORY_REVIEWER}}` | `agent_memory.scope` + `agent_memory.enabled_roles` (reviewer) — valgfri nøkkel |
| `{{MEMORY_IMPLEMENTER}}` | `agent_memory.scope` + `agent_memory.enabled_roles` (implementer) — valgfri nøkkel |
| `{{MEMORY_CODE_REVIEWER}}` | `agent_memory.scope` + `agent_memory.enabled_roles` (code_reviewer) — valgfri nøkkel |
| `{{MEMORY_SCOUT}}` | `agent_memory.scope` + `agent_memory.enabled_roles` (scout) — valgfri nøkkel |
| `{{SCOUT_DELEGATION_BLOCK_IMPLEMENTER}}` | som `{{SCOUT_DELEGATION_BLOCK}}` + implementerens rapporteringsplikt for `dispatches: 0` (tom streng når scout er av) |
| `{{LESSONS_TOPICS_BULLETS}}` / `{{LESSONS_INDEX_ENTRIES}}` | `lessons_topics` (rendret liste i `docs/loop-rules.md` / seedet `tasks/lessons.md`). Hvert tema blir en mappe `tasks/lessons/<tema>/`; `open-followups` i lista ignoreres (oppfølginger ligger i `tasks/followups/`) |
| `{{IMPLEMENTER_MODEL_ALIAS}}` / `{{DEEP_MODEL_ALIAS}}` | modellfamilien i `models.implementer` / `models.code_reviewer` (`claude-opus-5-5` → `opus`) — `model`-verdien i implementer-dispatchen (§5/§5b) |
| `{{IMPLEMENTER_DISPATCH_ALLOWED}}` / `{{DEEP_DISPATCH_ALLOWED}}` | `case`-mønster med familien og alle dypere (`haiku` < `sonnet` < `opus` < `fable`), brukt av `guard-fix-round-model.sh` |
| `{{BELOW_IMPLEMENTER_ALIAS}}` / `{{FIXR3_IMPL_EXPECT}}` | testdata for `test-guard-fix-round-model.sh` (familien under implementer-klassen; forventet exit for implementer-modellen i fix-runde 3+) |
| `{{AGENT_MEMORY_ROLES}}` | `agent_memory.enabled_roles` (rendret agentnavn-liste i `docs/loop-rules.md`) |
| `{{READONLY_CONTRACT}}` | rendret `.claude/hooks/reviewer-readonly.contract`: reviewer, code-reviewer (Agent-felt = `tech_review_agents[].name`), hver tech-agent (ekstra verktøy = `readonly_extra_tools`), scout iff `scout.enabled` |
| `{{READONLY_PROBE_ROLE}}` | `<project>-scout` hvis scout er på, ellers `<project>-reviewer` — rollen K18/K19 i readonly-harnessen prober |
| `{{TYPECHECK_ON_EDIT_CASE}}` | `hooks.typecheck_on_edit_extensions` (rendret `case`-mønster, f.eks. `*.ts\|*.tsx`) |
| `{{BOOTSTRAP_INSTALL_CMD}}` / `{{BOOTSTRAP_LOCKFILE}}` / `{{BOOTSTRAP_INSTALL_MARKER}}` | `worktree_bootstrap.install_cmd` / `.lockfile` / `.install_marker` — valgfri seksjon, tom = hopp over |
| `{{BOOTSTRAP_ENV_FILES}}` / `{{BOOTSTRAP_ENV_ALLOWED_KEYS}}` / `{{BOOTSTRAP_ENV_DENY_REGEX}}` | `worktree_bootstrap.env_files` / `.env_allowed_keys` / `.env_denied_prefixes` |
| `{{GENERATED_HEADER}}` | fast tekst (se skript) |

**Uten token, styrt av config:** `hooks.*` avgjør hvilke hook-filer som genereres
(`SKIP_WHEN_OFF`) og hvilke som registreres i `.claude/settings.json`. Default: de tre
vaktene (`main_merge_guard`, `reviewer_readonly_guard`, `implementer_model_guard`) PÅ,
`session_start_lint`, `typecheck_on_edit_extensions` og `compaction_checkpoint` AV.
`compaction_checkpoint` styrer også om `docs/superpowers/loop/steps/0c-sjekkpunkt.md` genereres.

## Substitusjons-skript

Krever `python3` med `pyyaml`. Mangler `pyyaml` → skriptet sier fra (feil
høyt) — installer med `pip install pyyaml`. Kjør fra prosjektroten:

```bash
python3 - <<'PY'
import sys, os, re, shutil
try:
    import yaml
except ImportError:
    sys.exit("FEIL: pyyaml mangler. Installer: pip install pyyaml")

ROOT = os.getcwd()
KIT  = os.path.join(ROOT, "v3-agent-orchestrator")
TPL  = os.path.join(KIT, "templates")
CFG  = os.path.join(KIT, "loop.config.yaml")

if not os.path.exists(CFG):
    sys.exit(f"FEIL: {CFG} finnes ikke. Kopier loop.config.example.yaml → loop.config.yaml og fyll den.")

with open(CFG) as f:
    c = yaml.safe_load(f)

# --- Valider påkrevde nøkler (feil høyt) ---------------------------------
REQUIRED = [
    "project_name","github_repo","language","dev_server_port","dev_server_process",
    "models.planner","models.planner_effort","models.reviewer","models.reviewer_effort",
    "models.implementer","models.implementer_effort","models.code_reviewer",
    "models.code_reviewer_effort",
    "environments.dev_id","environments.prod_id",
    "branch_strategy.base_branch","branch_strategy.release_branch","branch_strategy.prod_branch",
    "verification_commands.build","verification_commands.type_check",
    "verification_commands.type_check_script","verification_commands.lint",
    "verification_commands.format_check",
    "verification_commands.test","verification_commands.e2e","verification_commands.web_smoke",
    "verification_commands.e2e_probe",
    "tier1_invariants","canary_source","lessons_topics","pause_triggers",
    "release.command","release.health_check_merge_interval",
]
def get(path):
    cur = c
    for k in path.split("."):
        if not isinstance(cur, dict) or k not in cur: return None
        cur = cur[k]
    return cur
missing = [p for p in REQUIRED if get(p) is None]
# tech_review_agents kan være [] men nøkkelen MÅ finnes
if "tech_review_agents" not in c: missing.append("tech_review_agents")
if missing:
    sys.exit("FEIL: manglende config-nøkler:\n  - " + "\n  - ".join(missing))

# --- Valider trigger_globs per tech-review-agent (fail høyt, TODO 180A) ----
# trigger_globs er et GULV (se loop.config.yaml-kommentaren) for koordinatorens
# tasks/review-lens-select.py — MÅ finnes og være en ikke-tom liste av strenger
# for HVER konfigurert agent. En tom tech_review_agents: [] er fortsatt lovlig
# (prosjekter uten tech-reviewere) — denne sjekken kjører kun over agentene som
# faktisk finnes, aldri over en tom liste.
_glob_errors = []
for _a in (c.get("tech_review_agents") or []):
    _name = _a.get("name", "<uten navn>")
    _globs = _a.get("trigger_globs")
    if not isinstance(_globs, list) or not _globs or not all(isinstance(g, str) and g for g in _globs):
        _glob_errors.append(_name)
if _glob_errors:
    sys.exit("FEIL: trigger_globs mangler eller er tom liste for: " + ", ".join(_glob_errors))

# --- Valider severity_floor per tech-review-agent (fail høyt, TODO 180B) ---
# MEMBERSHIP-test, ikke .get(): en manglende nøkkel er en ANNEN feil enn et
# bevisst null-gulv, og .get() ville gjort dem identiske — fail-open på
# nøyaktig den feilen valideringen finnes for.
VALID_FLOORS = {"BLOKKERENDE", "VIKTIG", "MINDRE", "PAUSEPUNKT", None}
_floor_errors = []
for _a in (c.get("tech_review_agents") or []):
    _name = _a.get("name", "<uten navn>")
    if "severity_floor" not in _a:
        _floor_errors.append(f"{_name} (nøkkelen severity_floor mangler)")
    elif _a["severity_floor"] not in VALID_FLOORS:
        _floor_errors.append(f"{_name} (ugyldig severity_floor: {_a['severity_floor']!r})")
if _floor_errors:
    sys.exit("FEIL: severity_floor mangler eller er ugyldig for: " + ", ".join(_floor_errors))

# --- Valider floor_exempt per tech-review-agent (valgfri, fail høyt, TODO 321) ---
# MEMBERSHIP-test: nøkkelen er valgfri, men finnes den, må verdien være en liste av
# kjente klasser. null er IKKE «ingen unntak» — da skal nøkkelen utelates.
VALID_FLOOR_EXEMPT_CLASSES = {"comment_doc_wording"}
_exempt_errors = []
for _a in (c.get("tech_review_agents") or []):
    if "floor_exempt" not in _a:
        continue
    _name = _a.get("name", "<uten navn>")
    _v = _a["floor_exempt"]
    if not isinstance(_v, list) or not all(isinstance(_x, str) for _x in _v):
        _exempt_errors.append(f"{_name} (ikke en liste av strenger: {_v!r})")
    elif any(_x not in VALID_FLOOR_EXEMPT_CLASSES for _x in _v):
        _exempt_errors.append(f"{_name} (ukjent klasse: {_v!r})")
    elif len(set(_v)) != len(_v):
        _exempt_errors.append(f"{_name} (duplikat: {_v!r})")
    elif _v and _a.get("severity_floor") not in ("BLOKKERENDE", "VIKTIG", "MINDRE"):
        _exempt_errors.append(f"{_name} (krever severity_floor BLOKKERENDE, VIKTIG eller MINDRE)")
if _exempt_errors:
    sys.exit("FEIL: floor_exempt er ugyldig for: " + ", ".join(_exempt_errors))

# --- Kryssjekk: CLI-basert e2e krever en probe (fail-closed, se TODO 181) --
# Preflightens §1 (run-loop.md) faller tilbake til "tilgjengelig" for en tom
# CLI-probe (et tomt skall avslutter med exit 0) — uten denne sjekken kunne et
# feilkonfigurert prosjekt generere et kit som rapporterer bevisløs "E2E:
# tilgjengelig" for hver eneste runde.
_e2e   = (get("verification_commands.e2e") or "").strip()
_probe = (get("verification_commands.e2e_probe") or "").strip()
if _e2e and "mcp__" not in _e2e and not _probe:
    sys.exit(
        "FEIL: verification_commands.e2e er CLI-basert (" + _e2e + ") men e2e_probe er tom.\n"
        "  Preflightens §1 ville rapportert «E2E: tilgjengelig» uten bevis (tomt skall = exit 0).\n"
        "  Sett verification_commands.e2e_probe, eller gjør e2e MCP-basert."
    )

# --- Valider agent_memory (valgfri nøkkel — fravær = minne AV for alle roller) --
# Skrur på Claude Codes `memory:`-frontmatter (agent-minne) for én eller flere
# worker-roller. Ugyldig scope/rollenavn feiler høyt, samme prinsipp som resten
# av skriptet (prinsipp 2) — en stille no-op ville latt en typo passere som «av».
VALID_MEMORY_SCOPES = {"user", "project", "local"}
VALID_MEMORY_ROLES = {"planner", "reviewer", "implementer", "code_reviewer", "scout"}
_am = c.get("agent_memory") or {}
_am_scope = _am.get("scope", "project")
_am_roles = _am.get("enabled_roles") or []
if _am_scope not in VALID_MEMORY_SCOPES:
    sys.exit(
        f"FEIL: agent_memory.scope er ugyldig ({_am_scope!r}).\n"
        f"  Gyldige verdier: {sorted(VALID_MEMORY_SCOPES)}."
    )
_bad_roles = [r for r in _am_roles if r not in VALID_MEMORY_ROLES]
if _bad_roles:
    sys.exit(
        f"FEIL: agent_memory.enabled_roles inneholder ugyldig(e) rolle(r): {_bad_roles}.\n"
        f"  Gyldige verdier: {sorted(VALID_MEMORY_ROLES)}."
    )

# --- Valider pipelining (valgfri nøkkel — fravær = pipelining AV) ---------
# Taket for hvor mange todos som kan ligge i pipeline (plan uten claim) mens en
# annen implementeres — koordinator-runbook §5c. Fravær ⇒ 0 ⇒ dagens
# sekvensielle atferd. Ugyldig verdi feiler høyt (samme prinsipp som
# agent_memory): en stille no-op ville latt en typo passere som «av».
_pl = c.get("pipelining") or {}
_pmif = _pl.get("max_in_flight", 0)
if isinstance(_pmif, bool) or not isinstance(_pmif, int) or _pmif < 0:
    sys.exit(
        f"FEIL: pipelining.max_in_flight må være et heltall >= 0 "
        f"(0 = pipelining av), fikk {_pmif!r}."
    )

# --- Valider parallel_implementers (valgfri nøkkel — fravær = 1, dagens atferd) ---
# Taket for hvor mange samtidig skrive-kapable implementere (koordinator-runbook
# §5d, TODO 233). Default MÅ være 1, ALDRI 0 — 0 implementere ville betydd «ingen
# implementering» (R7), ikke «av», til forskjell fra pipelining der 0 er den
# korrekte «av»-verdien. Ugyldig verdi feiler høyt, samme prinsipp som over.
_pim = c.get("parallel_implementers") or {}
_pimax = _pim.get("max", 1)
if isinstance(_pimax, bool) or not isinstance(_pimax, int) or _pimax < 1:
    sys.exit(
        f"FEIL: parallel_implementers.max må være et heltall >= 1 "
        f"(1 = dagens sekvensielle atferd), fikk {_pimax!r}."
    )

# --- Valider scout (valgfri nøkkel — fravær = scout AV) -------------------
# Lokaliserings-workeren (§3/§5). Fravær ⇒ enabled = False ⇒ charteret genereres
# ikke, og planner/implementer får verken Agent(...)-leddet eller delegerings-
# seksjonen — dagens atferd, uendret. Er den PÅ, er modell + effort + tak
# påkrevd: en scout uten modell ville arvet hovedmodellen og gjort hele rollen
# (en billigere modell for lokalisering) til en ren kostnad.
_sc = c.get("scout") or {}
if not isinstance(_sc, dict):
    sys.exit(
        f"FEIL: scout må være et objekt med enabled/max_findings (evt. utelatt helt), "
        f"fikk {_sc!r}."
    )
_sc_enabled = _sc.get("enabled", False)
if not isinstance(_sc_enabled, bool):
    sys.exit(f"FEIL: scout.enabled må være true/false, fikk {_sc_enabled!r}.")
if _sc_enabled:
    # Sannhetstest, ikke `is None`: models.scout: "" passerte `is None` og genererte et
    # charter med en tom `model:`-linje — nøyaktig utfallet kommentaren over sier sjekken
    # finnes for å hindre. (REQUIRED-lista har samme svakhet for de øvrige modellene; egen todo.)
    _sc_missing = [k for k in ("models.scout", "models.scout_effort")
                   if not str(get(k) or "").strip()]
    if _sc_missing:
        sys.exit("FEIL: scout.enabled er true, men disse mangler:\n  - " + "\n  - ".join(_sc_missing))
    _sc_max = _sc.get("max_findings")
    if isinstance(_sc_max, bool) or not isinstance(_sc_max, int) or _sc_max < 1:
        sys.exit(
            f"FEIL: scout.max_findings må være et heltall >= 1 når scout.enabled er true, "
            f"fikk {_sc_max!r}."
        )

# --- Valider hooks (valgfri nøkkel — fravær = de to vaktene PÅ, komfort-hookene AV) ----
# Vaktene (guard-main-merge, guard-reviewer-readonly) håndhever nivå-A-invarianter og er PÅ
# med mindre de slås av eksplisitt. Komfort-hookene er stack-avhengige og AV som default.
_hk = c.get("hooks") or {}
if not isinstance(_hk, dict):
    sys.exit(f"FEIL: hooks må være et objekt, fikk {_hk!r}.")
_HOOK_BOOLS = {"main_merge_guard": True, "reviewer_readonly_guard": True, "implementer_model_guard": True,
               "session_start_lint": False, "compaction_checkpoint": False}
_hooks_on = {}
for _k, _default in _HOOK_BOOLS.items():
    _v = _hk.get(_k, _default)
    if not isinstance(_v, bool):
        sys.exit(f"FEIL: hooks.{_k} må være true/false, fikk {_v!r}.")
    _hooks_on[_k] = _v
_tc_ext = _hk.get("typecheck_on_edit_extensions", [])
if not isinstance(_tc_ext, list) or not all(isinstance(x, str) and re.fullmatch(r"\.[A-Za-z0-9]+", x) for x in _tc_ext):
    sys.exit(f"FEIL: hooks.typecheck_on_edit_extensions må være en liste som [\".ts\", \".tsx\"], fikk {_tc_ext!r}.")
_hooks_on["typecheck_on_edit"] = bool(_tc_ext)
_unknown_hk = set(_hk) - set(_HOOK_BOOLS) - {"typecheck_on_edit_extensions"}
if _unknown_hk:
    sys.exit(f"FEIL: ukjente nøkler under hooks: {sorted(_unknown_hk)}.")
if _hooks_on["session_start_lint"] and not (get("verification_commands.type_check") or get("verification_commands.lint")):
    sys.exit("FEIL: hooks.session_start_lint er på, men både type_check og lint er tomme.")
if _hooks_on["typecheck_on_edit"] and not get("verification_commands.type_check"):
    sys.exit("FEIL: hooks.typecheck_on_edit_extensions er satt, men verification_commands.type_check er tom.")

# --- Valider worktree_bootstrap (valgfri nøkkel — fravær = ingen installasjon/env-kopi) ----
# Verdiene rendres inn i et bash-skript. Alt som havner mellom doble anførselstegn valideres
# mot tegn som ville brutt ut av strengen; install_cmd går via sitert heredoc og er fri.
_wb = c.get("worktree_bootstrap") or {}
if not isinstance(_wb, dict):
    sys.exit(f"FEIL: worktree_bootstrap må være et objekt, fikk {_wb!r}.")
_unknown_wb = set(_wb) - {"install_cmd", "lockfile", "install_marker", "env_files", "env_allowed_keys", "env_denied_prefixes"}
if _unknown_wb:
    sys.exit(f"FEIL: ukjente nøkler under worktree_bootstrap: {sorted(_unknown_wb)}.")
_SAFE_PATH = re.compile(r"[A-Za-z0-9._/+-]*")
_ENV_KEY = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
for _k in ("lockfile", "install_marker"):
    if not _SAFE_PATH.fullmatch(str(_wb.get(_k, "") or "")):
        sys.exit(f"FEIL: worktree_bootstrap.{_k} har ugyldige tegn: {_wb.get(_k)!r}.")
for _k, _rx in (("env_files", _SAFE_PATH), ("env_allowed_keys", _ENV_KEY), ("env_denied_prefixes", _ENV_KEY)):
    _v = _wb.get(_k, []) or []
    if not isinstance(_v, list) or not all(isinstance(x, str) and x and _rx.fullmatch(x) for x in _v):
        sys.exit(f"FEIL: worktree_bootstrap.{_k} må være en liste av gyldige navn, fikk {_v!r}.")

# --- Valider readonly_extra_tools per tech-review-agent (valgfri, TODO 365) ------------
# Ekstra verktøy en read-only rolle får i kontraktfila (f.eks. WebFetch). Skrive-verktøy
# kan aldri grantes — hooken avviser dem uansett (WRITE_DENYLIST_EXACT), men en slik
# config er en misforståelse og feiler her i stedet for å se ut som den virker.
_WRITE_TOOLS = {"Write", "Edit", "MultiEdit", "NotebookEdit", "SlashCommand", "Skill", "Monitor", "SendMessage"}
for _a in (c.get("tech_review_agents") or []):
    _v = _a.get("readonly_extra_tools", [])
    if not isinstance(_v, list) or not all(isinstance(x, str) and re.fullmatch(r"[A-Za-z0-9_]+", x) for x in _v):
        sys.exit(f"FEIL: readonly_extra_tools for {_a.get('name')} må være en liste av verktøynavn, fikk {_v!r}.")
    _bad = [x for x in _v if x in _WRITE_TOOLS or x.startswith("mcp__")]
    if _bad:
        sys.exit(f"FEIL: readonly_extra_tools for {_a.get('name')} inneholder skrive-verktøy {_bad} — en read-only rolle kan aldri få dem.")

def memory_line(role):
    """Render `memory: <scope>`-frontmatterlinja for en rolle, eller en
    selvdokumenterende kommentarlinje hvis rollen ikke er skrudd på. Begge er
    gyldig YAML i frontmatteren."""
    if role in _am_roles:
        return f"memory: {_am_scope}"
    return "# memory: av (sett agent_memory.enabled_roles i loop.config.yaml)"

# --- Render block-tokens --------------------------------------------------
PROJ_NAME = c["project_name"]
tras = c.get("tech_review_agents") or []
if tras:
    lines = []
    for a in tras:
        if a["severity_floor"] is not None:
            _floor_sent = (f"Severity-gulv: {a['severity_floor']} (synthesizeren setter severity på "
                           f"alle funn og kan HEVE til gulvet, aldri senke under det).")
        else:
            _floor_sent = "Severity-gulv: ingen — funnene er fullt underlagt synthesizerens skjønn."
        _exempt = a.get("floor_exempt") or []
        _exempt_sent = (" Gulvunntak: " + ", ".join(f"`{x}`" for x in _exempt) + " (se «Synthesizerens plikter» punkt 5).") if _exempt else ""
        lines.append(f"   - Hvis diffen berører {a['trigger']} → dispatcher `{a['name']}`-agenten "
                     f"som frisk sub-agent (egen kontekst, ser kun diffen). {_floor_sent}{_exempt_sent}")
        _globs_str = ", ".join(f"`{g}`" for g in a["trigger_globs"])
        lines.append(f"     trigger_globs (gulv koordinatoren regner ut selv — ikke fasit, kun mekanisk "
                     f"sikret delmengde; fnmatch: `*` krysser `/`): {_globs_str}.")
    tech_block = "\n".join(lines)
else:
    tech_block = "   - (Ingen tech-review-agenter konfigurert — hopp over sikkerhets-/domene-armen.)"

# {{TECH_REVIEW_TRIGGER_GLOBS}}: Python-dict-literal {navn: [glob, …]} rendret
# inn i tasks/review-lens-select.py (TODO 180A). Globene substitueres på
# SETUP-TID, ikke lest av skriptet ved kjøring — samme kontrakt som resten av
# kit-et (loop.config.yaml:2-4). Config-rekkefølgen bevares (dict-er er
# ordnet i Python ≥3.7) — selektorens `triggered`-output skal følge
# config-rekkefølge, ikke set-iterasjon.
if tras:
    _glob_lines = [f"    {a['name']!r}: [" + ", ".join(repr(g) for g in a["trigger_globs"]) + "]," for a in tras]
    tech_review_trigger_globs = "TRIGGER_GLOBS = {\n" + "\n".join(_glob_lines) + "\n}"
else:
    tech_review_trigger_globs = "TRIGGER_GLOBS = {}"

# {{TECH_REVIEW_SEVERITY_FLOORS}}: Python-dict-literal {navn: gulv-eller-None}
# rendret inn i tasks/review-severity-floor.py OG tasks/review-fan-in-verify.py
# (TODO 180B; CF-250-6 — begge konsumerer samme token). Samme kontrakt og
# struktur som {{TECH_REVIEW_TRIGGER_GLOBS}} over — substituert på SETUP-TID,
# aldri lest fra loop.config.yaml ved kjøretid.
if tras:
    _floor_lines = [f"    {a['name']!r}: {a['severity_floor']!r}," for a in tras]
    tech_review_severity_floors = "SEVERITY_FLOORS = {\n" + "\n".join(_floor_lines) + "\n}"
else:
    tech_review_severity_floors = "SEVERITY_FLOORS = {}"

# {{TECH_REVIEW_FLOOR_EXEMPTIONS}}: Python-dict-literal {navn: [klasse, …]} rendret
# inn i tasks/review-severity-floor.py (TODO 321). [] for agenter uten nøkkelen.
# Substituert på SETUP-TID, aldri lest fra loop.config.yaml ved kjøretid.
if tras:
    _exempt_lines = [f"    {a['name']!r}: {list(a.get('floor_exempt') or [])!r}," for a in tras]
    tech_review_floor_exemptions = "FLOOR_EXEMPTIONS = {\n" + "\n".join(_exempt_lines) + "\n}"
else:
    tech_review_floor_exemptions = "FLOOR_EXEMPTIONS = {}"

# {{TECH_REVIEW_AGENT_NAMES}}: rendret Agent(...)-ledd for code-reviewerens
# tools:-linje. Utledet fra samme tras-liste som tech_block over — aldri
# hardkod agentnavn i en template igjen (jf. TODO 173 PR1-kode-review-funn:
# hardkodede navn i tools: driftet fra tech_review_agents og feilet dispatch
# med «Agent type not found» når en ny lens-agent ble lagt i config men ikke
# i allowlisten). Tom streng når tras er tom — IKKE render et tomt Agent().
if tras:
    tech_review_agent_names = ", Agent(" + ", ".join(a["name"] for a in tras) + ")"
else:
    tech_review_agent_names = ""

# {{SCOUT_AGENT_TOOL}} / {{SCOUT_DELEGATION_BLOCK}}: begge er TOMME når scout er av,
# slik at planner-/implementer-charterne genereres byte-identisk med dagens (samme
# «tom streng, ikke tomt ledd»-regel som {{TECH_REVIEW_AGENT_NAMES}}). Blokken rendres
# her og ikke i templaten fordi kit-et ikke har betinget inkludering — samme mønster
# som {{TECH_REVIEW_AGENTS_DISPATCH}}.
if _sc_enabled:
    scout_agent_tool = f", Agent({PROJ_NAME}-scout)"
    scout_delegation_block = f"""## Delegering av lokalisering (scout)

Du har `Agent({PROJ_NAME}-scout)` — en lokaliserings-worker på en billigere modell. Den svarer
«hvor er X» med `fil:linje` + symbol, og returnerer ALDRI filinnhold. Alt den leser, holdes utenfor
DIN kontekst. Det er hele gevinsten, og den forsvinner hvis du bruker den feil.

**Dispatch den når** svaret krever et sveip: du vet ikke hvilke filer som er berørt, du trenger alle
kallsteder for et symbol, du leter etter en navnekonvensjon, eller du må vite om et mønster finnes
andre steder i kodebasen. Ett spørsmål per dispatch.

**Dispatch den IKKE når** du allerede kjenner stien, når ett `grep` i din egen Bash svarer, eller når
spørsmålet krever skjønn (hvilken løsning er riktig, er denne koden god, hva bør planen være).
Scouten vurderer ingenting — spør du den om en vurdering, får du en verdiløs sådan. En dispatch for
noe du kunne grep-et selv er netto TAP: du betaler oppstart og rapport for et svar du hadde.

**`measurement.truncated: true` ⟹ svaret er UFULLSTENDIG.** Taket ble nådd og noe ble utelatt —
still et smalere oppfølgingsspørsmål eller søk selv. Bygg ALDRI en fullstendighetspåstand («alle
kallsteder», «finnes ingen andre steder») på et avkortet svar.

**En NEGATIV påstand fra scouten — tomt `findings` med `status: "answered"`, eller et punkt i
`unresolved` — bekrefter du med ETT eget søk før du bygger på den.** Scouten kan ha søkt feil (feil
glob, for smal regex); et fravær den rapporterer er en hypotese, ikke et funn.

**Etter svaret — BINDENDE:** scout-rapporten er et kart, ikke kildemateriale. Sammenlign FØRST
`evidence.toplevel`/`evidence.head_sha` fra scout-rapporten mot dine EGNE (`git rev-parse
--show-toplevel` / `git rev-parse HEAD`) — ulike verdier betyr at scouten kan ha svart mot en annen
commit enn den du arbeider mot, og ethvert `fil:linje` fra rapporten er da uverifisert til du åpner
det uansett. Før du planlegger eller endrer et sted den peker på, ÅPNE det selv. Å skrive en plan
eller en kodeendring mot en `fil:linje` du ikke har lest, er samme defektklasse som å overta et tall
fra en plan uten å måle det på nytt. Motsier rapporten det du ser når du åpner fila: fila vinner, og
du noterer avviket.

**Rapporter bruken.** Hver scout-rapport bærer et `measurement`-objekt. Summer dem i rapportens
`scout_usage` (se `docs/superpowers/loop/report-schema.md`) — koordinatoren logger totalen. Brukte du
ingen scout: `{{"dispatches": 0, "bytes_read": 0, "findings": 0}}`. Det er et lovlig og ofte riktig
svar; feltet finnes for å måle rollen, ikke for å presse fram bruk av den.

"""
    scout_usage_line = (
        '  "scout_usage": { "dispatches": 0, "bytes_read": 0, "findings": 0 },\n'
    )
    scout_model_row = (
        f"| Lokalisering (scout) | {get('models.scout')} (effort {get('models.scout_effort')}) | "
        "Finner `fil:linje` på oppdrag fra planner/implementer og returnerer aldri filinnhold — "
        "arbeid som ikke trenger resonnering, og som holder søkeoverflaten ute av de dyre rollenes "
        "kontekst |\n"
    )
    scout_probe_bullet = (
        f"- `Agent` med `subagent_type: {PROJ_NAME}-scout`, prompt «Svar kun: "
        "{\"ok\": true}. Ikke les filer.» — scouten dispatches av planner/implementer, ikke av deg, "
        "men agent-registeret er sesjonsglobalt: er den ikke lastet her, feiler den først INNE i en "
        "worker, der feilen er dyrere å tolke.\n"
    )
else:
    scout_agent_tool = ""
    scout_delegation_block = ""
    scout_probe_bullet = ""
    scout_model_row = ""
    scout_usage_line = ""

# {{SCOUT_DELEGATION_BLOCK_IMPLEMENTER}}: samme blokk + implementerens rapporteringsplikt for
# dispatches=0 og vernet mot koordinator-pålagte minimumsdispatcher (målt 2026-09-16).
if _sc_enabled:
    scout_delegation_block_impl = scout_delegation_block.replace(
        "ikke for å presse fram bruk av den.\n",
        "ikke for å presse fram bruk av den. **Er `dispatches` 0, skriv\n"
        "én setning i `notes` om hvorfor** — typisk at planen allerede navnga fil og linje, slik at et\n"
        "scout-kall ikke ville spart noe. Det er en rapporteringsplikt, ikke en terskel du må forsvare:\n"
        "begrunnelsen er selve målingen av om delegeringen lønner seg for denne rollen.\n"
        "**Koordinatoren skal ikke pålegge deg et minste antall dispatcher** (målt 2026-09-16: tre runder på\n"
        "rad der et slikt pålegg i dispatch-prompten motsa denne linja, og der du hadde rett i å følge\n"
        "charteret). Ser du et slikt pålegg, følg charteret og noter avviket.\n", 1)
    assert scout_delegation_block_impl != scout_delegation_block
else:
    scout_delegation_block_impl = ""

# {{READONLY_CONTRACT}}: kontraktfila guard-reviewer-readonly.sh håndhever (TODO 365). Utledet
# fra SAMME kilder som charterne — en ny read-only rolle i config får vernet i samme /setup.
# Format per linje: <agent>\t<tillatte subagenter, komma, eller ->\t<ekstra verktøy, komma, eller ->
_ro = [(f"{PROJ_NAME}-reviewer", "-", "-"),
       (f"{PROJ_NAME}-code-reviewer", ",".join(a["name"] for a in tras) or "-", "-")]
_ro += [(a["name"], "-", ",".join(a.get("readonly_extra_tools") or []) or "-") for a in tras]
if _sc_enabled:
    _ro.append((f"{PROJ_NAME}-scout", "-", "-"))
readonly_contract = "\n".join("\t".join(r) for r in _ro)
readonly_probe_role = f"{PROJ_NAME}-scout" if _sc_enabled else f"{PROJ_NAME}-reviewer"

typecheck_case = "|".join(f"*{x}" for x in _tc_ext) or "__typecheck_av__"

_deny = _wb.get("env_denied_prefixes") or []
bootstrap = {
    "{{BOOTSTRAP_INSTALL_CMD}}": str(_wb.get("install_cmd", "") or ""),
    "{{BOOTSTRAP_LOCKFILE}}": str(_wb.get("lockfile", "") or ""),
    "{{BOOTSTRAP_INSTALL_MARKER}}": str(_wb.get("install_marker", "") or ""),
    "{{BOOTSTRAP_ENV_FILES}}": " ".join(f'"{x}"' for x in (_wb.get("env_files") or [])),
    "{{BOOTSTRAP_ENV_ALLOWED_KEYS}}": "\n".join(f"  {x}" for x in (_wb.get("env_allowed_keys") or [])),
    "{{BOOTSTRAP_ENV_DENY_REGEX}}": ("^(" + "|".join(_deny) + ")") if _deny else "",
}

# Lessons: ett tema = én mappe tasks/lessons/<tema>/. Oppfølgingskøen er tasks/followups/, ikke et
# tema — et gammelt «open-followups» i lista ignoreres (v3.0-configer hadde det).
_topics_own = [x for x in c["lessons_topics"] if x != "open-followups"]
lessons_topics_bullets = "\n".join(f"- `{x}/`" for x in _topics_own)
lessons_index_entries = "\n".join(f"- `{x}/` — <scope: fyll inn>" for x in _topics_own)

# Modellfamilier for implementer-dispatchen og guard-fix-round-model.sh. Rekkefølge = dybde.
_LADDER = ["haiku", "sonnet", "opus", "fable"]
def _family(model_id):
    _m = re.match(r"(?:claude-)?([a-z]+)", str(model_id))
    return _m.group(1) if _m else str(model_id)
def _at_least(fam):
    return "|".join(_LADDER[_LADDER.index(fam):]) if fam in _LADDER else fam
_impl_fam = _family(c["models"]["implementer"])
_deep_fam = _family(c["models"]["code_reviewer"])
if _impl_fam in _LADDER and _deep_fam in _LADDER and _LADDER.index(_deep_fam) < _LADDER.index(_impl_fam):
    _deep_fam = _impl_fam   # «dyp» er aldri grunnere enn implementeren selv
_below_impl = _LADDER[_LADDER.index(_impl_fam) - 1] if _impl_fam in _LADDER and _LADDER.index(_impl_fam) > 0 else "__ingen__"
_fixr3_impl_expect = "0" if _impl_fam == _deep_fam else "2"
_role_agent = {"planner": "planner", "reviewer": "reviewer", "implementer": "implementer",
               "code_reviewer": "code-reviewer", "scout": "scout"}
agent_memory_roles = (", ".join(f"`{PROJ_NAME}-{_role_agent[r]}`" for r in _am_roles) or "ingen roller (agent_memory.enabled_roles er tom)")

HEADER = ("<!--\n  GENERERT av /setup fra loop.config.yaml — IKKE rediger her.\n"
          "  Endre loop.config.yaml og kjør /setup på nytt.\n-->")

M = {
    "{{PROJECT_NAME}}": c["project_name"],
    "{{GITHUB_REPO}}": c["github_repo"],
    "{{LANGUAGE}}": c["language"],
    "{{DEV_SERVER_PORT}}": str(c["dev_server_port"]),
    "{{DEV_SERVER_PROCESS}}": c["dev_server_process"],
    "{{MODEL_PLANNER}}": c["models"]["planner"],
    "{{EFFORT_PLANNER}}": c["models"]["planner_effort"],
    "{{MODEL_REVIEWER}}": c["models"]["reviewer"],
    "{{EFFORT_REVIEWER}}": c["models"]["reviewer_effort"],
    "{{MODEL_IMPLEMENTER}}": c["models"]["implementer"],
    "{{EFFORT_IMPLEMENTER}}": c["models"]["implementer_effort"],
    "{{MODEL_CODE_REVIEWER}}": c["models"]["code_reviewer"],
    "{{EFFORT_CODE_REVIEWER}}": c["models"]["code_reviewer_effort"],
    # Utledes fra modell-nøklene — en håndskrevet streng drifter fra modellene den beskriver.
    # Valgfri override via models.display. Ukjent form (alias som `opus`) vises rått.
    "{{MODELS_DISPLAY}}": c["models"].get("display") or "/".join(
        (lambda mm: f"{mm.group(1).capitalize()}{mm.group(2).replace('-', '.')}" if mm else m)(
            re.fullmatch(r"claude-([a-z]+)-(\d+(?:-\d+)*?)(?:-\d{8})?", m))
        for m in (c["models"]["planner"], c["models"]["reviewer"],
                  c["models"]["implementer"], c["models"]["code_reviewer"])),
    "{{DEV_ENV_ID}}": str(c["environments"]["dev_id"]),
    "{{PROD_ENV_ID}}": str(c["environments"]["prod_id"]),
    "{{BASE_BRANCH}}": c["branch_strategy"]["base_branch"],
    "{{RELEASE_BRANCH}}": c["branch_strategy"]["release_branch"],
    "{{PROD_BRANCH}}": c["branch_strategy"]["prod_branch"],
    "{{CMD_BUILD}}": c["verification_commands"]["build"],
    "{{CMD_TYPE_CHECK}}": c["verification_commands"]["type_check"],
    "{{CMD_TYPE_CHECK_SCRIPT}}": c["verification_commands"]["type_check_script"],
    "{{CMD_LINT}}": c["verification_commands"]["lint"],
    "{{CMD_FORMAT_CHECK}}": c["verification_commands"]["format_check"],
    "{{CMD_TEST}}": c["verification_commands"]["test"],
    "{{CMD_E2E}}": c["verification_commands"]["e2e"],
    "{{CMD_WEB_SMOKE}}": c["verification_commands"]["web_smoke"],
    "{{CMD_E2E_PROBE}}": c["verification_commands"]["e2e_probe"],
    "{{TIER1_INVARIANTS}}": c["tier1_invariants"].rstrip("\n"),
    "{{TECH_REVIEW_AGENTS_DISPATCH}}": tech_block,
    "{{TECH_REVIEW_AGENT_NAMES}}": tech_review_agent_names,
    "{{TECH_REVIEW_TRIGGER_GLOBS}}": tech_review_trigger_globs,
    "{{TECH_REVIEW_SEVERITY_FLOORS}}": tech_review_severity_floors,
    "{{TECH_REVIEW_FLOOR_EXEMPTIONS}}": tech_review_floor_exemptions,
    "{{CANARY_FILE}}": c["canary_source"],
    "{{LESSONS_TOPICS_BULLETS}}": lessons_topics_bullets,
    "{{LESSONS_INDEX_ENTRIES}}": lessons_index_entries,
    "{{AGENT_MEMORY_ROLES}}": agent_memory_roles,
    "{{READONLY_CONTRACT}}": readonly_contract,
    "{{READONLY_PROBE_ROLE}}": readonly_probe_role,
    "{{TYPECHECK_ON_EDIT_CASE}}": typecheck_case,
    **bootstrap,
    "{{PAUSE_TRIGGERS}}": c["pause_triggers"],
    "{{RELEASE_COMMAND}}": c["release"]["command"],
    "{{HEALTH_CHECK_INTERVAL}}": str(c["release"]["health_check_merge_interval"]),
    "{{PIPELINE_MAX_IN_FLIGHT}}": str(_pmif),
    "{{PARALLEL_IMPLEMENTERS_MAX}}": str(_pimax),
    "{{MEMORY_PLANNER}}": memory_line("planner"),
    "{{MEMORY_REVIEWER}}": memory_line("reviewer"),
    "{{MEMORY_IMPLEMENTER}}": memory_line("implementer"),
    "{{MEMORY_CODE_REVIEWER}}": memory_line("code_reviewer"),
    "{{MEMORY_SCOUT}}": memory_line("scout"),
    "{{MODEL_SCOUT}}": str(get("models.scout") or ""),
    "{{EFFORT_SCOUT}}": str(get("models.scout_effort") or ""),
    "{{SCOUT_MAX_FINDINGS}}": str(_sc.get("max_findings") or ""),
    "{{SCOUT_AGENT_TOOL}}": scout_agent_tool,
    "{{SCOUT_DELEGATION_BLOCK_IMPLEMENTER}}": scout_delegation_block_impl,
    "{{SCOUT_DELEGATION_BLOCK}}": scout_delegation_block,
    "{{SCOUT_PROBE_BULLET}}": scout_probe_bullet,
    "{{SCOUT_MODEL_ROW}}": scout_model_row,
    "{{SCOUT_USAGE_LINE}}": scout_usage_line,
    "{{IMPLEMENTER_MODEL_ALIAS}}": _impl_fam,
    "{{DEEP_MODEL_ALIAS}}": _deep_fam,
    "{{IMPLEMENTER_DISPATCH_ALLOWED}}": _at_least(_impl_fam),
    "{{DEEP_DISPATCH_ALLOWED}}": _at_least(_deep_fam),
    "{{BELOW_IMPLEMENTER_ALIAS}}": _below_impl,
    "{{FIXR3_IMPL_EXPECT}}": _fixr3_impl_expect,
    "{{GENERATED_HEADER}}": HEADER,
}

def subst(text):
    for k, v in M.items():
        text = text.replace(k, v)
    return text

# --- Walk templates → render → write -------------------------------------
# SEED_ONLY: runtime-state-filer som /setup kun skal SEEDE (skrive hvis de ikke
# finnes), aldri overskrive ved re-kjøring. run-log.md akkumulerer koordinator-
# telemetri (append-only) — å regenerere den fra templaten ville slette
# kjørehistorikk. retro-log.md (TODO 158) er samme runtime-state-klasse —
# koordinatorens §8 mini-retro-entries ville forsvunnet ved regenerering.
# retro-triage.md (TODO 174) er også samme runtime-state-klasse — §8b-triagen
# av retro-loggen akkumulerer beslutninger over tid og ville forsvunnet ved
# regenerering. decision-log.md (TODO 246) er også samme runtime-state-klasse
# — nivå-B-beslutningsloggen akkumulerer over tid og ville forsvunnet ved
# regenerering. Alle fire templatenes egen header dokumenterer denne kontrakten.
SEED_ONLY = {
    "docs/superpowers/loop/run-log.md",
    "docs/superpowers/loop/retro-log.md",
    "docs/superpowers/loop/retro-triage.md",
    "docs/superpowers/loop/decision-log.md",
    # v3: prosjekt-eide filer. Skrives KUN første gang — prosjektet eier dem deretter.
    # CLAUDE.md importerer den genererte docs/loop-rules.md (se etter-stegene under).
    "CLAUDE.md",
    "tasks/lessons.md",
    "docs/naming-conventions.md",
    "docs/data-model.md",
    # v3.6: køsidens prosjektdel og artefakt-lenkene. queue-status.py er kit-eid og lik overalt;
    # tittel, eierskap, notater og leverte releaser står i queue-config.py. artifacts.md bærer
    # prosjektets URL-er — en regenerering ville slettet dem (kit-drift.py vokter Køsiden-raden).
    "tasks/queue-config.py",
    "docs/superpowers/loop/artifacts.md",
}
written, leftovers, preserved, skipped = [], [], [], []
PROJ = c["project_name"]
# SKIP_WHEN_OFF: templates som tilhører en valgfri rolle. Er rollen av, skal fila
# ikke genereres i det hele tatt (den ville ellers stått igjen med {{MODEL_SCOUT}}
# og trigget leftovers-gaten). En eksisterende generert fil fjernes IKKE automatisk
# — /setup sletter aldri; skriptet sier fra så mennesket kan slette bevisst.
SKIP_WHEN_OFF = set() if _sc_enabled else {f".claude/agents/{PROJ}-scout.md"}
if not _hooks_on["main_merge_guard"]:
    SKIP_WHEN_OFF |= {".claude/hooks/guard-main-merge.sh", ".claude/hooks/test-guard-main-merge.sh"}
if not _hooks_on["reviewer_readonly_guard"]:
    SKIP_WHEN_OFF |= {".claude/hooks/guard-reviewer-readonly.sh", ".claude/hooks/test-guard-reviewer-readonly.sh",
                      ".claude/hooks/reviewer-readonly.contract"}
if not _hooks_on["implementer_model_guard"]:
    SKIP_WHEN_OFF |= {".claude/hooks/guard-fix-round-model.sh", ".claude/hooks/test-guard-fix-round-model.sh"}
if not _hooks_on["compaction_checkpoint"]:
    SKIP_WHEN_OFF |= {".claude/hooks/sessionstart-checkpoint.sh", ".claude/hooks/precompact-checkpoint.sh",
                      ".claude/hooks/test-checkpoint-hooks.sh", "docs/superpowers/loop/steps/0c-sjekkpunkt.md"}
if not _hooks_on["session_start_lint"]:
    SKIP_WHEN_OFF.add(".claude/hooks/session-start-lint.sh")
if not _hooks_on["typecheck_on_edit"]:
    SKIP_WHEN_OFF.add(".claude/hooks/typecheck-on-edit.sh")
for dirpath, dirs, files in os.walk(TPL):
    dirs[:] = [d for d in dirs if d != "__pycache__"]
    for fn in files:
        src = os.path.join(dirpath, fn)
        rel = os.path.relpath(src, TPL)
        # Rename agent-filer: PROJECT_NAME-*.md → <project>-*.md
        out_rel = rel.replace("PROJECT_NAME-", f"{PROJ}-")
        dst = os.path.join(ROOT, out_rel)
        # Valgfri rolle av: ikke generer fila i det hele tatt.
        if out_rel in SKIP_WHEN_OFF:
            skipped.append(out_rel)
            continue
        # Seed-only: bevar eksisterende runtime-state — ikke klobb ved re-kjøring.
        if out_rel in SEED_ONLY and os.path.exists(dst):
            preserved.append(out_rel)
            continue
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        with open(src) as f: body = f.read()
        body = subst(body)
        rem = re.findall(r"\{\{[A-Z0-9_]+\}\}", body)
        if rem:
            leftovers.append((out_rel, sorted(set(rem))))
        with open(dst, "w") as f: f.write(body)
        shutil.copymode(src, dst)   # kjørbar-biten følger malen (./tasks/worktree-sweep.sh --gate o.l.)
        written.append(out_rel)

# --- Seed lessons-tema-filer og agent-minne (kun hvis de mangler) ----------------------
seeded, notes = [], []
def seed(rel, text):
    dst = os.path.join(ROOT, rel)
    if os.path.exists(dst):
        return
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    with open(dst, "w") as f: f.write(text)
    seeded.append(rel)

for _tp in _topics_own:
    # git sporer ikke tomme mapper — .gitkeep holder temaet synlig til første lesson skrives.
    if not os.path.isdir(os.path.join(ROOT, "tasks", "lessons", _tp)):
        seed(f"tasks/lessons/{_tp}/.gitkeep", "")
    if os.path.isfile(os.path.join(ROOT, "tasks", "lessons", f"{_tp}.md")):
        notes.append(f"tasks/lessons/{_tp}.md er en gammel temafil — kjør "
                     "python3 v3-agent-orchestrator/scripts/split-lessons.py (se MIGRATION.md)")
if _am_scope == "project":
    for _r in _am_roles:
        _agent = f"{PROJ}-{_role_agent[_r]}"
        seed(f".claude/agent-memory/{_agent}/MEMORY.md", f"""# {_agent} — rollehukommelse

Kontrakt (form, tak, kurering, eierskap): se charterets § Rollehukommelse og
`docs/loop-rules.md` § «Tre kunnskapsbaser». Ikke kopier den hit.

<!-- BOOTSTRAP-UNVERIFIED (satt opp av /setup) — SELVFJERNENDE.
     Står denne blokken her, er skrivestien til agent-minnet ennå ikke verifisert
     i drift. Første agent som leser dette: legg linja under i
     «## Påstander», SLETT hele denne blokken i samme redigering, og commit begge
     endringene sammen med arbeidet ditt.
       - (bootstrap) skrivesti verifisert <YYYY-MM-DD>, TODO <nr>
     Neste kurering fjerner bootstrap-linja igjen — den er et kvitteringsspor,
     ikke en påstand. -->

## Påstander

_(tom — fylles av agenten når en runde faktisk gir en observasjon)_
""")

# --- CLAUDE.md: sørg for importen av den genererte docs/loop-rules.md -------------------
# Et prosjekt med egen CLAUDE.md fra før får den ikke overskrevet (seed-only over) — men uten
# importen ville loop-reglene aldri nådd sesjonen. Én linje, idempotent.
_cm = os.path.join(ROOT, "CLAUDE.md")
with open(_cm) as f: _cmt = f.read()
if "@docs/loop-rules.md" not in _cmt:
    with open(_cm, "a") as f:
        f.write("\n\n## Loop- og kunnskapsregler\n\n@docs/loop-rules.md\n")
    notes.append("CLAUDE.md: la til `@docs/loop-rules.md`-import (fila fantes fra før og ble ellers ikke rørt)")

# --- .claude/settings.json: merge kit-ets hook-oppføringer (idempotent) ------------------
# Nøkkelen er selve kommandostrengen: finnes den allerede under hendelsen, røres oppføringen
# ikke (heller ikke matcheren). Alt annet i fila — permissions, andres hooks, plugins —
# bevares. Ugyldig JSON feiler høyt i stedet for å bli overskrevet. /setup sletter aldri:
# en avslått hook som fortsatt står der, rapporteres.
import json
_HOOKS = [
    ("main_merge_guard", "PreToolUse", "Bash", '"$CLAUDE_PROJECT_DIR/.claude/hooks/guard-main-merge.sh"'),
    ("reviewer_readonly_guard", "PreToolUse", ".*", '"$CLAUDE_PROJECT_DIR/.claude/hooks/guard-reviewer-readonly.sh"'),
    ("implementer_model_guard", "PreToolUse", "Agent", '"$CLAUDE_PROJECT_DIR/.claude/hooks/guard-fix-round-model.sh"'),
    ("typecheck_on_edit", "PostToolUse", "Edit|Write|MultiEdit", '"$CLAUDE_PROJECT_DIR/.claude/hooks/typecheck-on-edit.sh"'),
    ("session_start_lint", "SessionStart", None, 'bash "$CLAUDE_PROJECT_DIR/.claude/hooks/session-start-lint.sh"'),
    ("compaction_checkpoint", "SessionStart", "compact", 'sh "$CLAUDE_PROJECT_DIR/.claude/hooks/sessionstart-checkpoint.sh"'),
    ("compaction_checkpoint", "PreCompact", "auto", 'sh "$CLAUDE_PROJECT_DIR/.claude/hooks/precompact-checkpoint.sh"'),
]
_sp = os.path.join(ROOT, ".claude", "settings.json")
_settings = {}
if os.path.exists(_sp):
    try:
        with open(_sp) as f: _settings = json.load(f)
    except json.JSONDecodeError as e:
        sys.exit(f"FEIL: {_sp} er ikke gyldig JSON ({e}) — rett den, så merger /setup hookene.")
    if not isinstance(_settings, dict):
        sys.exit(f"FEIL: {_sp} er ikke et JSON-objekt.")
_hooks_cfg = _settings.setdefault("hooks", {})
_changed = False
for _key, _event, _matcher, _cmd in _HOOKS:
    _entries = _hooks_cfg.get(_event, [])
    _present = any(h.get("command") == _cmd for e in _entries for h in (e.get("hooks") or []))
    if _hooks_on[_key] and not _present:
        _entry = {"hooks": [{"type": "command", "command": _cmd}]}
        if _matcher is not None:
            _entry = {"matcher": _matcher, **_entry}
        _hooks_cfg.setdefault(_event, []).append(_entry)
        _changed = True
        notes.append(f"settings.json: registrerte {_key} ({_event})")
    elif not _hooks_on[_key] and _present:
        notes.append(f"settings.json: {_key} er AV i config, men står fortsatt registrert — fjern den manuelt")
if _changed:
    os.makedirs(os.path.dirname(_sp), exist_ok=True)
    with open(_sp, "w") as f:
        json.dump(_settings, f, indent=2, ensure_ascii=False); f.write("\n")

# --- .gitignore: runtime-filer fra hooks og worktree-rydding --------------------------
_GI = ["tasks/hook-blocks.log*", "tasks/hook-readonly-gate.log*", ".claude/worktrees/", ".claude/worktree-rescue/",
       "tasks/.loop-state/"]
_gp = os.path.join(ROOT, ".gitignore")
_git = open(_gp).read() if os.path.exists(_gp) else ""
_missing_gi = [x for x in _GI if x not in _git.splitlines()]
if _missing_gi:
    with open(_gp, "a") as f:
        f.write(("" if _git.endswith("\n") or not _git else "\n") + "\n# agent-orchestrator (v3): runtime-filer\n" + "\n".join(_missing_gi) + "\n")
    notes.append(f".gitignore: la til {', '.join(_missing_gi)}")

print(f"Skrev {len(written)} filer:")
for w in sorted(written): print(f"  ✓ {w}")

if preserved:
    print(f"\nBevart {len(preserved)} seed-only fil(er) (fantes fra før — ikke overskrevet):")
    for p in sorted(preserved): print(f"  • {p}")

if skipped:
    print(f"\nHoppet over {len(skipped)} fil(er) (rollen er slått av i config):")
    for sk in sorted(skipped):
        _exists = " — FINNES FORTSATT PÅ DISK, slett den manuelt" if os.path.exists(os.path.join(ROOT, sk)) else ""
        print(f"  ⊘ {sk}{_exists}")

if seeded:
    print(f"\nSeedet {len(seeded)} prosjekt-eid(e) fil(er) (fantes ikke):")
    for sd in sorted(seeded): print(f"  + {sd}")

if notes:
    print("\nEndringer i eksisterende prosjektfiler:")
    for n in notes: print(f"  ~ {n}")

# Vaktene kaller /usr/bin/jq hardkodet og slipper ALT gjennom (fail-open) hvis den mangler.
if (_hooks_on["main_merge_guard"] or _hooks_on["reviewer_readonly_guard"] or _hooks_on["implementer_model_guard"]) and not os.access("/usr/bin/jq", os.X_OK):
    print("\n⚠️  /usr/bin/jq finnes ikke — vaktene slipper da alt gjennom. Installer jq "
          "(Linux: apt install jq; macOS 15+ har den innebygd) før loopen kjøres.")

if leftovers:
    print("\n❌ GJENVÆRENDE TOKENS — kit-et er IKKE komplett:")
    for rel, toks in leftovers:
        print(f"  {rel}: {', '.join(toks)}")
    sys.exit("Fiks template/config og kjør /setup på nytt.")
print("\n✅ Ingen gjenværende tokens. Neste: kopier tech-review-agenter, commit, "
      "START FERSK SESJON, kjør agent-proben i run-loop.md.")
PY
```

## Etterpå (manuelt)

- **Restart kreves:** de genererte `<project>-*`-agentene er ikke i registeret
  før en ny sesjon starter. Start fersk sesjon FØR du kjører `/run-loop`.
- **Probe:** første handling i ny sesjon = agent-proben i `run-loop.md`
  (`{"ok": true}`-dispatch). «Agent type not found» → registeret tok ikke
  endringen; bekreft at filene ligger i `.claude/agents/` og start på nytt.
