---
name: setup
description: "Kompiler v3-copilot-agent-orchestrator/loop.config.yaml inn i kit-et: validerer config, rendrer templates/ til prosjektets .github/agents, .github/skills, .github/hooks, docs/, tasks/ og scripts/, og genererer .github/hooks/loop-guards.json. Kjøres manuelt etter at config er fylt ut."
disable-model-invocation: true
---

# /setup — kompiler loop.config.yaml inn i kit-et

> **Installasjon:** kopier denne fila (`v3-copilot-agent-orchestrator/setup.md`) til prosjektets
> `.github/skills/setup/SKILL.md` så den blir kjørbar som `/setup` i Copilot-chatten
> (`disable-model-invocation: true` — den kjøres bare når du skriver `/setup`). Den er bevisst
> IKKE tokenisert — den er bootstrapperen som *gjør* tokeniseringen, ikke en del av det genererte
> kit-et. Prosjektets `.github/skills/setup/SKILL.md` holdes byte-identisk med denne fila
> (`diff -q` MÅ gi exit 0) — endrer du den ene, kopier til den andre i samme PR.

Du kjører `/setup` i et prosjekt som har lagt v3-mappen
(`v3-copilot-agent-orchestrator/`) i roten og fylt ut `loop.config.yaml`. Kommandoen
leser config-en og **kompilerer** templates inn i prosjektets faktiske stier.

## Prinsipper (ufravikelige)

1. **Deterministisk substitusjon for sikkerhetsverdier.** Miljø-IDer,
   branch-navn, modellnavn og verifiserings-kommandoer erstattes av skriptet under — ikke
   av at du «redigerer inn» verdier med skjønn. Null sjanse for et hallusinert
   prosjekt-ID i et charter. Du driver skriptet; du skriver ikke verdiene selv.
2. **Validerings-gate — feil høyt.** Skriptet stopper hardt hvis (a) en påkrevd
   config-nøkkel mangler, (b) en modellverdi fortsatt er en plassholder (`<…>`), (c) det
   gjenstår `{{...}}`-tokens etter substitusjon, eller (d) en generert agent/skill har ugyldig
   YAML-frontmatter. En charter med `{{DEV_ENV_ID}}` igjen skal ALDRI genereres.
3. **Idempotent + «GENERERT»-merking.** Re-kjøring overskriver de genererte
   filene rent. Hver generert fil bærer en header som sier «ikke rediger her»
   (unntak: `.github/hooks/loop-guards.json` — JSON har ikke kommentarer; den er like fullt kit-eid).
4. **Kilde vs. generert adskilt.** Templates (med tokens) blir liggende i
   `v3-copilot-agent-orchestrator/templates/`. Skriptet skriver generert output til
   prosjektets `.github/`, `docs/`, `tasks/`, `scripts/` og `AGENTS.md`. Du kan alltid diffe de to.
5. **Prosjekt-eide filer seedes, aldri overskrives.** `AGENTS.md`, lessons-katalogen,
   lessons-tema-mappene, agent-minnet, doc-skjelettene, `tasks/queue-config.py` og
   `docs/loop/artifacts.md` skrives kun hvis de mangler.
   Kit-eide regler ligger i den genererte `docs/loop-rules.md`, som `AGENTS.md` lenker til.
6. **Eksisterende prosjektfiler merges minimalt og idempotent.** `AGENTS.md` får én
   linje som lenker til `docs/loop-rules.md` hvis lenken mangler (Copilot følger ingen
   import-syntaks — reglene må lenkes og leses), `.gitignore` får runtime-filene. Alt annet i
   filene bevares. `.github/hooks/loop-guards.json` er derimot **kit-eid og genereres på nytt**
   hver gang fra `hooks.*` — prosjektets egne hooks legges i andre `.json`-filer i
   `.github/hooks/`. `/setup` sletter aldri — en foreldet eller avslått fil rapporteres, fjernes ikke.
7. **Avslutt med restart + probe.** Agent-registeret og hookene lastes ved sesjonsstart.
   Etter `/setup`: start en FERSK Copilot-sesjon og kjør agent-proben fra
   run-loop-skillen (`.github/skills/run-loop/SKILL.md`) for å bekrefte at
   `<project>-*`-agentene er registrert.

## Steg

1. Bekreft at `v3-copilot-agent-orchestrator/loop.config.yaml` finnes og er fylt
   (ikke `loop.config.example.yaml` — kopier og fyll den først; plassholderne
   `<DYP_MODELL>`, `<KODE_MODELL>` og `<BILLIG_MODELL>` stopper skriptet til de er byttet ut
   med eksakte modellnavn fra Copilot-modellvelgeren / `/model`).
2. Kjør substitusjons-skriptet under fra prosjektroten. Det validerer, renamer
   agentene til `<project_name>-*.agent.md`, substituerer alle tokens, prepender
   GENERERT-headeren, skriver til prosjektets stier og genererer `.github/hooks/loop-guards.json`.
3. Les skriptets sluttrapport. Gjenværende-token-feil, frontmatter-feil eller manglende-nøkkel-feil
   → fiks config / templates og kjør på nytt. Aldri fortsett med en delvis
   generert kit.
4. **Tech-review-agenter:** kopier prosjektets egne domene-reviewere inn i
   `.github/agents/<navn>.agent.md` (se `v3-copilot-agent-orchestrator/examples/tech-review-agents/` for
   maler). Disse er pluggbare — code-revieweren dispatcher dem etter `tech_review_agents` i
   config (den får `agent`-verktøyet og navnelista fra samme liste). Hver av dem MÅ ha en
   eksplisitt `tools: [read, search, execute]` uten `edit` — Copilot gir agenten bare verktøyene
   som står der. Kjør `/setup` på nytt etter kopieringen: skriptet avviser en tech-review-agent med
   skrive-verktøy eller uten `tools:`-liste. Har prosjektet ingen → `tech_review_agents: []`.
5. **Stillas:** hvis prosjektet ikke allerede har det, kopier scaffolding
   (`githooks/` → `.githooks/` med `pre-push` + `pre-commit`, CI-workflow med
   `todo-nr-guard`) og sett `git config core.hooksPath .githooks` — se README steg 8.
6. **Kjør harnessene** (de ble generert sammen med hookene og skriptene):
   `bash .github/hooks/scripts/test-guard-main-merge.sh`,
   `bash .github/hooks/scripts/test-guard-fix-round-model.sh` og
   `bash scripts/test-readonly-check.sh` — alle skal gi `AVVIK: 0` / `ALLE OK`.
7. Commit de genererte filene. Start fersk sesjon (hooks og agenter lastes ved
   sesjonsstart). Kjør `/run-loop once`.

## Token-tabell (kanonisk vokabular)

Hver `{{TOKEN}}` i `templates/` mapper til én config-nøkkel. Skriptet er
autoritativt; tabellen er for mennesker. Modellnavn i eksemplene er nøytrale testverdier.

| Token | Config-nøkkel |
|---|---|
| `{{PROJECT_NAME}}` | `project_name` (også agent-filnavn) |
| `{{GITHUB_REPO}}` | `github_repo` |
| `{{LANGUAGE}}` | `language` |
| `{{DEV_SERVER_PORT}}` | `dev_server_port` |
| `{{DEV_SERVER_PROCESS}}` | `dev_server_process` |
| `{{MODEL_PLANNER}}` / `{{MODEL_REVIEWER}}` / `{{MODEL_IMPLEMENTER}}` / `{{MODEL_CODE_REVIEWER}}` | `models.<rolle>` (streng eller prioritert liste) — rendres som YAML-flytliste, f.eks. `["deep-model-a", "deep-model-b"]`; brukes i agentenes `model:` og i Modeller-tabellen |
| `{{MODEL_SCOUT}}` | `models.scout` — samme form; påkrevd iff `scout.enabled` |
| `{{EFFORT_PLANNER}}` / `{{EFFORT_REVIEWER}}` / `{{EFFORT_IMPLEMENTER}}` / `{{EFFORT_CODE_REVIEWER}}` / `{{EFFORT_SCOUT}}` | `models.<rolle>_effort` (valgfri: `low`/`medium`/`high`/`xhigh`) — rendres som verdien, eller `standard` når nøkkelen mangler (= send ingen `reasoning_effort`). Står aldri i agent-frontmatter |
| `{{DISPATCH_ARGS_PLANNER}}` / `{{DISPATCH_ARGS_REVIEWER}}` / `{{DISPATCH_ARGS_IMPLEMENTER}}` / `{{DISPATCH_ARGS_CODE_REVIEWER}}` / `{{DISPATCH_ARGS_SCOUT}}` | første modell + effort for rollen, rendret som argument-ledd i koordinatorens `task`-kall: `model: "code-model-b", reasoning_effort: "high"` (effort-leddet utelates når `*_effort` mangler; tom streng for scout når den er av) |
| `{{DEEP_DISPATCH_ARGS}}` | `models.code_reviewer[0]` + `models.code_reviewer_effort` som argument-ledd — fix-runde 3+ og rotårsaksanalysen (§5b) |
| `{{IMPLEMENTER_MODEL_ALIAS}}` / `{{DEEP_MODEL_ALIAS}}` | første modell i `models.implementer` / `models.code_reviewer` — `model`-verdien i implementer-dispatchen (§5/§5b) |
| `{{IMPLEMENTER_DISPATCH_ALLOWED}}` / `{{DEEP_DISPATCH_ALLOWED}}` | bash-`case`-mønster med siterte modellnavn (`"code-model-b"\|"deep-model-a"`): implementer-lista ∪ kode-reviewer-lista / kode-reviewer-lista alene. Brukt av `guard-fix-round-model.sh` |
| `{{BELOW_IMPLEMENTER_ALIAS}}` / `{{FIXR3_IMPL_EXPECT}}` | testdata for `test-guard-fix-round-model.sh`: en modell utenfor implementer-mønsteret (første scout-modell som ikke står i det, ellers `__modell-utenfor-config__`); `0` hvis implementerens første modell også står i kode-reviewer-lista, ellers `2` (blokkert) |
| `{{MODELS_DISPLAY}}` | første modell per rolle, `planner/reviewer/implementer/code_reviewer` skilt med `/` (`deep-model-a/deep-model-a/code-model-b/deep-model-a`); valgfri override `models.display` |
| `{{SCOUT_MAX_FINDINGS}}` | `scout.max_findings` — påkrevd iff `scout.enabled` |
| `{{SCOUT_AGENT_TOOL}}` | `, agent` i planner-/implementer-`tools:`-lista når scout er på (tom streng når den er av) |
| `{{SCOUT_DELEGATION_BLOCK}}` | rendret delegerings-seksjon i planner-/implementer-charteret (tom streng når scout er av) |
| `{{SCOUT_DELEGATION_BLOCK_IMPLEMENTER}}` | som `{{SCOUT_DELEGATION_BLOCK}}` + implementerens rapporteringsplikt for `dispatches: 0` (tom streng når scout er av) |
| `{{SCOUT_PROBE_BULLET}}` | rendret probe-punkt (`task` med `agent_type: "<project>-scout"`) i run-loop-skillens preflight (tom streng når scout er av) |
| `{{SCOUT_MODEL_ROW}}` | rendret rad i Modeller-tabellen i `docs/orchestration-loop.md` (tom streng når scout er av) |
| `{{SCOUT_USAGE_LINE}}` | rendret `scout_usage`-linje i plan-/ferdig-rapport-eksemplene i `report-schema.md` (tom streng når scout er av) |
| `{{DEV_ENV_ID}}` / `{{PROD_ENV_ID}}` | `environments.dev_id` / `environments.prod_id` |
| `{{BASE_BRANCH}}` / `{{RELEASE_BRANCH}}` / `{{PROD_BRANCH}}` | `branch_strategy.*` |
| `{{CMD_BUILD}}` / `{{CMD_TYPE_CHECK}}` / `{{CMD_TYPE_CHECK_SCRIPT}}` / `{{CMD_LINT}}` / `{{CMD_FORMAT_CHECK}}` / `{{CMD_TEST}}` / `{{CMD_E2E}}` / `{{CMD_WEB_SMOKE}}` / `{{CMD_E2E_PROBE}}` | `verification_commands.*` |
| `{{TIER1_INVARIANTS}}` | `tier1_invariants` (blokk) |
| `{{TECH_REVIEW_AGENTS_DISPATCH}}` | `tech_review_agents` (rendret blokk, inkl. `trigger_globs` per agent — B2a) |
| `{{TECH_REVIEW_AGENT_TOOL}}` | `, agent` i code-reviewerens `tools:`-liste når `tech_review_agents` er ikke-tom (tom streng ellers) |
| `{{TECH_REVIEW_AGENT_NAMES}}` | `tech_review_agents[].name` (rendret navneliste i code-reviewer-charterets brødtekst, `ingen (…)` når lista er tom) |
| `{{TECH_REVIEW_TRIGGER_GLOBS}}` | `tech_review_agents[].trigger_globs` (rendret Python-dict-literal `{navn: [glob, …]}`, brukt av `tasks/review-lens-select.py`) |
| `{{TECH_REVIEW_SEVERITY_FLOORS}}` | `tech_review_agents[].severity_floor` (rendret Python-dict-literal `{navn: gulv-eller-None}`, brukt av `tasks/review-severity-floor.py` OG `tasks/review-fan-in-verify.py`) |
| `{{TECH_REVIEW_FLOOR_EXEMPTIONS}}` | `tech_review_agents[].floor_exempt` (valgfri; rendret Python-dict-literal `{navn: [klasse, …]}`, `[]` for agenter uten nøkkelen, brukt av `tasks/review-severity-floor.py`) |
| `{{CANARY_FILE}}` | `canary_source` |
| `{{PAUSE_TRIGGERS}}` | `pause_triggers` |
| `{{RELEASE_COMMAND}}` | `release.command` |
| `{{HEALTH_CHECK_INTERVAL}}` | `release.health_check_merge_interval` |
| `{{PIPELINE_MAX_IN_FLIGHT}}` | `pipelining.max_in_flight` — valgfri nøkkel, default `0` |
| `{{PARALLEL_IMPLEMENTERS_MAX}}` | `parallel_implementers.max` — valgfri nøkkel, default `1` (§5d) |
| `{{RETRO_FILE_CLASSES}}` | `retro_file_classes` — valgfri nøkkel (rendret Python-liste `CLASSES = [(navn, (mønster, …)), …]`, brukt av `tasks/retro-numbers.py`). Fravær ⇒ tester og planer/docs/loop |
| `{{LESSONS_TOPICS_BULLETS}}` / `{{LESSONS_INDEX_ENTRIES}}` | `lessons_topics` (rendret liste i `docs/loop-rules.md` / seedet `tasks/lessons.md`). Hvert tema blir en mappe `tasks/lessons/<tema>/`; `open-followups` i lista ignoreres (oppfølginger ligger i `tasks/followups/`) |
| `{{AGENT_MEMORY_ROLES}}` | `agent_memory.enabled_roles` (rendret agentnavn-liste i `docs/loop-rules.md`) |
| `{{TYPECHECK_ON_EDIT_CASE}}` | `hooks.typecheck_on_edit_extensions` (rendret `case`-mønster, f.eks. `*.ts\|*.tsx`) |
| `{{BOOTSTRAP_INSTALL_CMD}}` / `{{BOOTSTRAP_LOCKFILE}}` / `{{BOOTSTRAP_INSTALL_MARKER}}` | `worktree_bootstrap.install_cmd` / `.lockfile` / `.install_marker` — valgfri seksjon, tom = hopp over |
| `{{BOOTSTRAP_ENV_FILES}}` / `{{BOOTSTRAP_ENV_ALLOWED_KEYS}}` / `{{BOOTSTRAP_ENV_DENY_REGEX}}` | `worktree_bootstrap.env_files` / `.env_allowed_keys` / `.env_denied_prefixes` |
| `{{GENERATED_HEADER}}` | fast tekst (se skript) |

**Uten token, styrt av config:**

- `hooks.*` avgjør hvilke hook-skript som genereres (`SKIP_WHEN_OFF`) og hvilke som registreres i
  den genererte `.github/hooks/loop-guards.json` (`version: 1`, hver oppføring
  `{"type": "command", "bash": "…", "cwd": ".", "timeoutSec": N}`):

  | Config-nøkkel | Hendelse | Kommando | Default |
  |---|---|---|---|
  | `main_merge_guard` | `preToolUse` | `bash .github/hooks/scripts/guard-main-merge.sh` | PÅ |
  | `implementer_model_guard` | `preToolUse` | `bash .github/hooks/scripts/guard-fix-round-model.sh` | PÅ |
  | `typecheck_on_edit_extensions` (ikke-tom) | `postToolUse` | `bash .github/hooks/scripts/typecheck-on-edit.sh` | AV |
  | `session_start_lint` | `sessionStart` | `bash .github/hooks/scripts/session-start-lint.sh` | AV |
  | `compaction_checkpoint` | `preCompact` | `sh .github/hooks/scripts/precompact-checkpoint.sh` | AV |

  `compaction_checkpoint` styrer også om `docs/loop/steps/0c-sjekkpunkt.md` genereres.
  `hooks.reviewer_readonly_guard` finnes ikke lenger og avvises med forklaring: read-only-rollene
  har ikke `edit` i `tools:`, og koordinatoren kjører `scripts/readonly-check.sh` etter hver
  read-only-dispatch (`scripts/readonly-check.sh` og `scripts/test-readonly-check.sh` genereres alltid).
- `agent_memory.enabled_roles` seeder `tasks/agent-memory/<agent>/MEMORY.md` for hver påslått rolle.
  Kun `scope: project` finnes (fila sjekkes inn); andre verdier avvises.

## Substitusjons-skript

Krever `python3` med `pyyaml`. Mangler `pyyaml` → skriptet sier fra (feil
høyt) — installer med `pip install pyyaml`. Kjør fra prosjektroten:

```bash
python3 - <<'PY'
import sys, os, re, shutil, json
try:
    import yaml
except ImportError:
    sys.exit("FEIL: pyyaml mangler. Installer: pip install pyyaml")

ROOT = os.getcwd()
KIT  = os.path.join(ROOT, "v3-copilot-agent-orchestrator")
TPL  = os.path.join(KIT, "templates")
CFG  = os.path.join(KIT, "loop.config.yaml")

if not os.path.exists(CFG):
    sys.exit(f"FEIL: {CFG} finnes ikke. Kopier loop.config.example.yaml → loop.config.yaml og fyll den.")

with open(CFG) as f:
    c = yaml.safe_load(f)
if not isinstance(c, dict):
    sys.exit(f"FEIL: {CFG} er tom eller ikke et YAML-objekt.")

# --- Plassholder-sjekk for modeller (FØR alt annet — feil høyt) -------------
# Eksempelfila har <DYP_MODELL>, <KODE_MODELL> og <BILLIG_MODELL> som modellnavn. En
# plassholder som slipper gjennom, ville blitt en agent med en modell som ikke finnes —
# og Copilot faller da stille tilbake til en annen modell enn den rollen er valgt for.
_models_raw = c.get("models")
if isinstance(_models_raw, dict):
    _ph = []
    for _k, _v in _models_raw.items():
        for _x in (_v if isinstance(_v, list) else [_v]):
            if isinstance(_x, str) and ("<" in _x or ">" in _x):
                _ph.append(f"models.{_k}: {_x}")
    if _ph:
        sys.exit(
            "FEIL: loop.config.yaml har fortsatt plassholdere under models:\n  - "
            + "\n  - ".join(_ph)
            + "\n  Bytt dem ut med eksakte modellnavn fra Copilot-modellvelgeren (/model) og kjør /setup på nytt."
        )

# --- Valider påkrevde nøkler (feil høyt) ---------------------------------
REQUIRED = [
    "project_name","github_repo","language","dev_server_port","dev_server_process",
    "models.planner","models.reviewer","models.implementer","models.code_reviewer",
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

# --- Valider modeller (lister per rolle, valgfri effort) -------------------
# Hver rolle tar en prioritert LISTE av modellnavn (Copilot prøver neste hvis den første ikke
# er tilgjengelig). En enkelt streng godtas og gjøres om til en liste med ett element.
# Navnene rendres inn i YAML-frontmatter, i bash-`case`-mønstre (guard-fix-round-model.sh) og i
# run-loggens `|`-separerte rader — tegn som ville brutt ut av noen av dem, avvises.
VALID_EFFORTS = {"low", "medium", "high", "xhigh"}
_MODEL_ROLES = ["planner", "reviewer", "implementer", "code_reviewer", "scout"]
_BAD_MODEL_CHARS = re.compile(r'["\\`$|\n\r\t]')
_mc = c["models"]
if not isinstance(_mc, dict):
    sys.exit(f"FEIL: models må være et objekt, fikk {_mc!r}.")
_unknown_models = set(_mc) - set(_MODEL_ROLES) - {f"{r}_effort" for r in _MODEL_ROLES} - {"display"}
if _unknown_models:
    sys.exit(f"FEIL: ukjente nøkler under models: {sorted(_unknown_models)}.")
def model_list(role, required=True):
    v = _mc.get(role)
    if v is None and not required:
        return []
    if isinstance(v, str):
        v = [v]
    if (not isinstance(v, list) or not v
            or not all(isinstance(x, str) and x.strip() for x in v)):
        sys.exit(f"FEIL: models.{role} må være et modellnavn eller en ikke-tom liste av modellnavn, fikk {v!r}.")
    v = [x.strip() for x in v]
    _bad = [x for x in v if _BAD_MODEL_CHARS.search(x)]
    if _bad:
        sys.exit(f"FEIL: models.{role} har modellnavn med ugyldige tegn (\" \\ ` $ | eller linjeskift): {_bad!r}.")
    if len(set(v)) != len(v):
        sys.exit(f"FEIL: models.{role} har duplikater: {v!r}.")
    return v
def model_effort(role):
    v = _mc.get(f"{role}_effort")
    if v is None or v == "":
        return None
    if v not in VALID_EFFORTS:
        sys.exit(f"FEIL: models.{role}_effort må være en av {sorted(VALID_EFFORTS)} (eller utelatt), fikk {v!r}.")
    return v
_md = _mc.get("display")
if _md is not None and (not isinstance(_md, str) or "|" in _md or "\n" in _md):
    sys.exit(f"FEIL: models.display må være en enlinjes tekst uten `|`, fikk {_md!r}.")

# --- Valider trigger_globs per tech-review-agent (fail høyt) ----
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

# --- Valider severity_floor per tech-review-agent (fail høyt) ---
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

# --- Valider floor_exempt per tech-review-agent (valgfri, fail høyt) ---
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

# --- Kryssjekk: CLI-basert e2e krever en probe (fail-closed) --
# Preflightens §1 (run-loop-skillen) faller tilbake til "tilgjengelig" for en tom
# CLI-probe (et tomt skall avslutter med exit 0) — uten denne sjekken kunne et
# feilkonfigurert prosjekt generere et kit som rapporterer bevisløs "E2E:
# tilgjengelig" for hver eneste runde. MCP-basert e2e kjennes på ordet «MCP» i
# verdien (MCP-verktøy heter <server>/<verktøy>, f.eks. playwright/browser_navigate).
_e2e   = (get("verification_commands.e2e") or "").strip()
_probe = (get("verification_commands.e2e_probe") or "").strip()
if _e2e and not re.search(r"\bMCP\b", _e2e) and not _probe:
    sys.exit(
        "FEIL: verification_commands.e2e er CLI-basert (" + _e2e + ") men e2e_probe er tom.\n"
        "  Preflightens §1 ville rapportert «E2E: tilgjengelig» uten bevis (tomt skall = exit 0).\n"
        "  Sett verification_commands.e2e_probe, eller gjør e2e MCP-basert (verdien nevner «MCP»)."
    )

# --- Valider agent_memory (valgfri nøkkel — fravær = minne AV for alle roller) --
# Rollehukommelse er en vanlig, innsjekket fil per agent: tasks/agent-memory/<agent>/MEMORY.md.
# Agenten leser den i Steg 0 og foreslår endringer i rapporten (`memory_candidates`);
# koordinatoren er eneste skriver. Det finnes bare prosjekt-scope (fila ligger i repoet).
# Ugyldig scope/rollenavn feiler høyt, samme prinsipp som resten av skriptet (prinsipp 2) —
# en stille no-op ville latt en typo passere som «av».
VALID_MEMORY_ROLES = {"planner", "reviewer", "implementer", "code_reviewer", "scout"}
_am = c.get("agent_memory") or {}
if not isinstance(_am, dict):
    sys.exit(f"FEIL: agent_memory må være et objekt med scope/enabled_roles, fikk {_am!r}.")
_unknown_am = set(_am) - {"scope", "enabled_roles"}
if _unknown_am:
    sys.exit(f"FEIL: ukjente nøkler under agent_memory: {sorted(_unknown_am)}.")
_am_scope = _am.get("scope", "project")
_am_roles = _am.get("enabled_roles") or []
if _am_scope != "project":
    sys.exit(
        f"FEIL: agent_memory.scope er {_am_scope!r}, men bare \"project\" støttes.\n"
        "  Rollehukommelsen er en innsjekket fil (tasks/agent-memory/<agent>/MEMORY.md) som\n"
        "  koordinatoren skriver og agenten leser i Steg 0 — det finnes ingen bruker- eller\n"
        "  maskinlokal variant. Sett scope: project (eller utelat nøkkelen)."
    )
if not isinstance(_am_roles, list):
    sys.exit(f"FEIL: agent_memory.enabled_roles må være en liste, fikk {_am_roles!r}.")
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
# §5d). Default MÅ være 1, ALDRI 0 — 0 implementere ville betydd «ingen
# implementering» (R7), ikke «av», til forskjell fra pipelining der 0 er den
# korrekte «av»-verdien. Ugyldig verdi feiler høyt, samme prinsipp som over.
_pim = c.get("parallel_implementers") or {}
_pimax = _pim.get("max", 1)
if isinstance(_pimax, bool) or not isinstance(_pimax, int) or _pimax < 1:
    sys.exit(
        f"FEIL: parallel_implementers.max må være et heltall >= 1 "
        f"(1 = dagens sekvensielle atferd), fikk {_pimax!r}."
    )

# --- Valider retro_file_classes (valgfri nøkkel — fravær = standardlista) ---
# Filklassene tasks/retro-numbers.py fordeler tillagte linjer på. Første treff
# vinner, og det som ikke treffer, er appkode. Substituert på SETUP-TID.
_rfc = c.get("retro_file_classes")
if _rfc is None:
    _rfc = [
        {"name": "tester", "patterns": ["e2e/", "__tests__", ".test.", ".spec."]},
        {"name": "planer/docs/loop", "patterns": ["tasks/", "docs/", ".github/", ".md"]},
    ]
if not isinstance(_rfc, list) or not all(
    isinstance(k, dict) and isinstance(k.get("name"), str) and k["name"]
    and isinstance(k.get("patterns"), list) and k["patterns"]
    and all(isinstance(p, str) and p for p in k["patterns"])
    for k in _rfc
):
    sys.exit("FEIL: retro_file_classes må være en liste av {name: <tekst>, patterns: [<tekst>, …]}.")
retro_file_classes = "CLASSES = [" + ", ".join(
    f"({k['name']!r}, {tuple(k['patterns'])!r})" for k in _rfc) + "]"

# --- Valider scout (valgfri nøkkel — fravær = scout AV) -------------------
# Lokaliserings-workeren (§3/§5). Fravær ⇒ enabled = False ⇒ charteret genereres
# ikke, og planner/implementer får verken `agent`-verktøyet eller delegerings-
# seksjonen — dagens atferd, uendret. Er den PÅ, er modell + tak påkrevd: en scout
# uten modell ville arvet en annen modell og gjort hele rollen (en billigere modell
# for lokalisering) til en ren kostnad.
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
    # Sannhetstest, ikke `is None`: models.scout: "" eller [] ville gitt et charter uten modell.
    if not _mc.get("scout"):
        sys.exit("FEIL: scout.enabled er true, men disse mangler:\n  - models.scout")
    _sc_max = _sc.get("max_findings")
    if isinstance(_sc_max, bool) or not isinstance(_sc_max, int) or _sc_max < 1:
        sys.exit(
            f"FEIL: scout.max_findings må være et heltall >= 1 når scout.enabled er true, "
            f"fikk {_sc_max!r}."
        )

# Modell-lister og effort per rolle (validert over; scout kun når den er på).
MODELS  = {r: model_list(r) for r in ("planner", "reviewer", "implementer", "code_reviewer")}
MODELS["scout"] = model_list("scout") if _sc_enabled else model_list("scout", required=False)
EFFORTS = {r: model_effort(r) for r in _MODEL_ROLES}

# --- Valider hooks (valgfri nøkkel — fravær = vaktene PÅ, komfort-hookene AV) ----
# Vaktene (guard-main-merge, guard-fix-round-model) håndhever nivå-A-invarianter og er PÅ
# med mindre de slås av eksplisitt. Komfort-hookene er stack-avhengige og AV som default.
_hk = c.get("hooks") or {}
if not isinstance(_hk, dict):
    sys.exit(f"FEIL: hooks må være et objekt, fikk {_hk!r}.")
if "reviewer_readonly_guard" in _hk:
    sys.exit(
        "FEIL: hooks.reviewer_readonly_guard finnes ikke lenger — fjern nøkkelen fra loop.config.yaml.\n"
        "  Read-only-rollene håndheves nå i to lag: (1) de har ikke `edit` i `tools:` (Copilot gir\n"
        "  agenten bare verktøyene som står der), og (2) koordinatoren kjører\n"
        "  `bash scripts/readonly-check.sh <WORKTREE> <base-sha>` etter hver read-only-dispatch\n"
        "  (genereres alltid). En hook kan ikke gjøre jobben: preToolUse-payloaden sier ikke\n"
        "  hvilken agent som kaller verktøyet."
    )
_HOOK_BOOLS = {"main_merge_guard": True, "implementer_model_guard": True,
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

# --- Tech-review-agenter: navn + read-only-verktøy (fail høyt) -----------------
# readonly_extra_tools fantes for en kontraktfil som ikke lenger finnes: en tech-review-agents
# verktøy står i dens egen `tools:`-liste i .github/agents/<navn>.agent.md. Finnes agentfila
# allerede, sjekkes det at den ikke har skrive-verktøy — en lens som kan skrive, deler
# arbeidstre med kode-revieweren og ville gjort hele fan-in-runden usignert.
_EDIT_TOOLS = {"edit", "create", "write", "apply_patch", "str_replace_editor", "notebookedit", "multiedit"}
_AGENT_NAME = re.compile(r"[a-z0-9][a-z0-9-]*")
notes_pre = []
for _a in (c.get("tech_review_agents") or []):
    _n = _a.get("name")
    if not isinstance(_n, str) or not _AGENT_NAME.fullmatch(_n):
        sys.exit(f"FEIL: tech_review_agents[].name må være kebab-case ([a-z0-9-]), fikk {_n!r}.")
    if "readonly_extra_tools" in _a:
        sys.exit(
            f"FEIL: tech_review_agents[{_n}].readonly_extra_tools finnes ikke lenger — fjern nøkkelen.\n"
            f"  Agentens verktøy står i `tools:` i .github/agents/{_n}.agent.md (aldri `edit`)."
        )
    _ap = os.path.join(ROOT, ".github", "agents", f"{_n}.agent.md")
    if not os.path.exists(_ap):
        notes_pre.append(f".github/agents/{_n}.agent.md finnes ikke ennå — kopier den fra "
                         "v3-copilot-agent-orchestrator/examples/tech-review-agents/ (Steg 4)")
        continue
    with open(_ap) as f:
        _txt = f.read()
    _fm = re.match(r"---\n(.*?)\n---\n", _txt, re.S)
    try:
        _meta = yaml.safe_load(_fm.group(1)) if _fm else None
    except yaml.YAMLError as e:
        sys.exit(f"FEIL: .github/agents/{_n}.agent.md har ugyldig YAML-frontmatter ({e}).")
    if not isinstance(_meta, dict):
        sys.exit(f"FEIL: .github/agents/{_n}.agent.md mangler YAML-frontmatter.")
    _tools = _meta.get("tools")
    if isinstance(_tools, str):
        _tools = [t.strip() for t in _tools.split(",")]
    if not isinstance(_tools, list) or not _tools:
        sys.exit(f"FEIL: .github/agents/{_n}.agent.md mangler en eksplisitt `tools:`-liste — "
                 "uten den får agenten alle verktøy, også `edit`. Bruk tools: [read, search, execute].")
    _w = [t for t in _tools if str(t).split("/")[-1].lower() in _EDIT_TOOLS]
    if _w:
        sys.exit(f"FEIL: .github/agents/{_n}.agent.md har skrive-verktøy {_w} i tools: — "
                 "en tech-review-agent er read-only. Fjern dem.")

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
# inn i tasks/review-lens-select.py. Globene substitueres på
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
# (begge konsumerer samme token). Samme kontrakt og
# struktur som {{TECH_REVIEW_TRIGGER_GLOBS}} over — substituert på SETUP-TID,
# aldri lest fra loop.config.yaml ved kjøretid.
if tras:
    _floor_lines = [f"    {a['name']!r}: {a['severity_floor']!r}," for a in tras]
    tech_review_severity_floors = "SEVERITY_FLOORS = {\n" + "\n".join(_floor_lines) + "\n}"
else:
    tech_review_severity_floors = "SEVERITY_FLOORS = {}"

# {{TECH_REVIEW_FLOOR_EXEMPTIONS}}: Python-dict-literal {navn: [klasse, …]} rendret
# inn i tasks/review-severity-floor.py. [] for agenter uten nøkkelen.
# Substituert på SETUP-TID, aldri lest fra loop.config.yaml ved kjøretid.
if tras:
    _exempt_lines = [f"    {a['name']!r}: {list(a.get('floor_exempt') or [])!r}," for a in tras]
    tech_review_floor_exemptions = "FLOOR_EXEMPTIONS = {\n" + "\n".join(_exempt_lines) + "\n}"
else:
    tech_review_floor_exemptions = "FLOOR_EXEMPTIONS = {}"

# {{TECH_REVIEW_AGENT_TOOL}} / {{TECH_REVIEW_AGENT_NAMES}}: code-revieweren får `agent`-verktøyet
# (kalle andre custom agents som subagent) KUN når det finnes tech-review-agenter, og navnelista
# står i charterets brødtekst. Utledet fra samme tras-liste som tech_block over — aldri hardkod
# agentnavn i en template igjen (hardkodede navn drev fra tech_review_agents og feilet dispatch
# med «Unknown agent_type» når en ny lens-agent ble lagt i config men ikke i charteret).
if tras:
    tech_review_agent_tool = ", agent"
    tech_review_agent_names = ", ".join(f"`{a['name']}`" for a in tras)
else:
    tech_review_agent_tool = ""
    tech_review_agent_names = "ingen (tech_review_agents er tom)"

# --- Modell-tokens ---------------------------------------------------------
# {{MODEL_X}} rendres til en YAML-flytliste (["a", "b"]) — gyldig både i agent-frontmatteren
# (`model:` tar en prioritert liste) og som lesbar tekst i docs. JSON-strenger er gyldige
# YAML-skalarer, og navnene er validert fri for tegn som bryter ut.
def flow_list(v):
    return json.dumps(v, ensure_ascii=False)
def primary(role):
    return MODELS[role][0] if MODELS[role] else ""
def dispatch_args(role, model_role=None):
    """Rendret argument-ledd for et `task`-kall: `model: "<første modell>"` + valgfri
    `reasoning_effort` fra models.<rolle>_effort (utelates når effort ikke er satt)."""
    m = primary(model_role or role)
    if not m:
        return ""
    e = EFFORTS[model_role or role]
    return f'model: "{m}"' + (f', reasoning_effort: "{e}"' if e else "")
def case_pattern(names):
    # bash-`case`-mønster med siterte literaler: "a"|"b". Sitering gjør mellomrom, punktum og
    # parenteser i modellnavn trygge; " \ ` $ | er avvist i valideringen.
    return "|".join(f'"{n}"' for n in names)
def _uniq(seq):
    out = []
    for x in seq:
        if x not in out: out.append(x)
    return out

_impl_list = MODELS["implementer"]
_deep_list = MODELS["code_reviewer"]          # «dyp modell» = kode-reviewerens liste (§5b, fix-runde 3+)
_impl_allowed = _uniq(_impl_list + _deep_list)  # implementer-modellene ELLER dyp modell
_below_impl = next((m for m in MODELS["scout"] if m not in _impl_allowed), "__modell-utenfor-config__")
_fixr3_impl_expect = "0" if _impl_list[0] in _deep_list else "2"
_role_agent = {"planner": "planner", "reviewer": "reviewer", "implementer": "implementer",
               "code_reviewer": "code-reviewer", "scout": "scout"}
agent_memory_roles = (", ".join(f"`{PROJ_NAME}-{_role_agent[r]}`" for r in _am_roles) or "ingen roller (agent_memory.enabled_roles er tom)")

# {{SCOUT_AGENT_TOOL}} / {{SCOUT_DELEGATION_BLOCK}}: begge er TOMME når scout er av,
# slik at planner-/implementer-charterne genereres uten scout-spor (samme «tom streng,
# ikke tomt ledd»-regel som {{TECH_REVIEW_AGENT_TOOL}}). Blokken rendres her og ikke i
# templaten fordi kit-et ikke har betinget inkludering — samme mønster som
# {{TECH_REVIEW_AGENTS_DISPATCH}}.
if _sc_enabled:
    scout_agent_tool = ", agent"
    _scout_args = dispatch_args("scout")
    scout_delegation_block = f"""## Delegering av lokalisering (scout)

Du har `agent`-verktøyet og kan dispatche `{PROJ_NAME}-scout` — en lokaliserings-worker på en
billigere modell: `task` med `agent_type: "{PROJ_NAME}-scout"`, `{_scout_args}`, `mode: "sync"`.
Den svarer «hvor er X» med `fil:linje` + symbol, og returnerer ALDRI filinnhold. Alt den leser,
holdes utenfor DIN kontekst. Det er hele gevinsten, og den forsvinner hvis du bruker den feil.

**Gi den worktreen din.** Scouten har ingen egen worktree og deler filsystem med deg: første linje
i prompten er `WORKTREE: <din WORKTREE>`, ellers søker den i hovedsjekkuten. Kjør
`git -C "<WORKTREE>" rev-parse HEAD; git -C "<WORKTREE>" status --porcelain` rett FØR og rett ETTER
dispatchen (du endrer ingenting mens den kjører). Ulik utskrift betyr at scouten har skrevet —
forkast svaret og noter det i `notes`. Scouten har ikke `edit`, men den har `execute`.

**Dispatch den når** svaret krever et sveip: du vet ikke hvilke filer som er berørt, du trenger alle
kallsteder for et symbol, du leter etter en navnekonvensjon, eller du må vite om et mønster finnes
andre steder i kodebasen. Ett spørsmål per dispatch.

**Dispatch den IKKE når** du allerede kjenner stien, når ett søk med din egen `search`/`execute`
svarer, eller når spørsmålet krever skjønn (hvilken løsning er riktig, er denne koden god, hva bør
planen være). Scouten vurderer ingenting — spør du den om en vurdering, får du en verdiløs sådan. En
dispatch for noe du kunne søkt opp selv er netto TAP: du betaler oppstart og rapport for et svar du
hadde.

**`measurement.truncated: true` ⟹ svaret er UFULLSTENDIG.** Taket ble nådd og noe ble utelatt —
still et smalere oppfølgingsspørsmål eller søk selv. Bygg ALDRI en fullstendighetspåstand («alle
kallsteder», «finnes ingen andre steder») på et avkortet svar.

**En NEGATIV påstand fra scouten — tomt `findings` med `status: "answered"`, eller et punkt i
`unresolved` — bekrefter du med ETT eget søk før du bygger på den.** Scouten kan ha søkt feil (feil
glob, for smal regex); et fravær den rapporterer er en hypotese, ikke et funn.

**Etter svaret — BINDENDE:** scout-rapporten er et kart, ikke kildemateriale. Sammenlign FØRST
`evidence.toplevel`/`evidence.head_sha` fra scout-rapporten mot dine EGNE (`git rev-parse
--show-toplevel` / `git rev-parse HEAD` i WORKTREE) — ulike verdier betyr at scouten har svart mot
et annet tre eller en annen commit enn den du arbeider mot, og ethvert `fil:linje` fra rapporten er
da uverifisert til du åpner det uansett. Før du planlegger eller endrer et sted den peker på, ÅPNE
det selv. Å skrive en plan eller en kodeendring mot en `fil:linje` du ikke har lest, er samme
defektklasse som å overta et tall fra en plan uten å måle det på nytt. Motsier rapporten det du ser
når du åpner fila: fila vinner, og du noterer avviket.

**Rapporter bruken.** Hver scout-rapport bærer et `measurement`-objekt. Summer dem i rapportens
`scout_usage` (se `docs/loop/report-schema.md`) — koordinatoren logger totalen. Brukte du
ingen scout: `{{"dispatches": 0, "bytes_read": 0, "findings": 0}}`. Det er et lovlig og ofte riktig
svar; feltet finnes for å måle rollen, ikke for å presse fram bruk av den.

"""
    scout_usage_line = (
        '  "scout_usage": { "dispatches": 0, "bytes_read": 0, "findings": 0 },\n'
    )
    scout_model_row = (
        f"| Lokalisering (scout) | {flow_list(MODELS['scout'])} (effort {EFFORTS['scout'] or 'standard'}) | "
        "Finner `fil:linje` på oppdrag fra planner/implementer og returnerer aldri filinnhold — "
        "arbeid som ikke trenger resonnering, og som holder søkeoverflaten ute av de dyre rollenes "
        "kontekst |\n"
    )
    scout_probe_bullet = (
        f"- `task` med `agent_type: \"{PROJ_NAME}-scout\"`, `mode: \"sync\"`, prompt «Svar kun: "
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
# dispatches=0 og vernet mot koordinator-pålagte minimumsdispatcher.
if _sc_enabled:
    scout_delegation_block_impl = scout_delegation_block.replace(
        "ikke for å presse fram bruk av den.\n",
        "ikke for å presse fram bruk av den. **Er `dispatches` 0, skriv\n"
        "én setning i `notes` om hvorfor** — typisk at planen allerede navnga fil og linje, slik at et\n"
        "scout-kall ikke ville spart noe. Det er en rapporteringsplikt, ikke en terskel du må forsvare:\n"
        "begrunnelsen er selve målingen av om delegeringen lønner seg for denne rollen.\n"
        "**Koordinatoren skal ikke pålegge deg et minste antall dispatcher** (målt: tre runder på\n"
        "rad der et slikt pålegg i dispatch-prompten motsa denne linja, og der du hadde rett i å følge\n"
        "charteret). Ser du et slikt pålegg, følg charteret og noter avviket.\n", 1)
    assert scout_delegation_block_impl != scout_delegation_block
else:
    scout_delegation_block_impl = ""

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

HEADER = ("<!--\n  GENERERT av /setup fra loop.config.yaml — IKKE rediger her.\n"
          "  Endre loop.config.yaml og kjør /setup på nytt.\n-->")

M = {
    "{{PROJECT_NAME}}": c["project_name"],
    "{{GITHUB_REPO}}": c["github_repo"],
    "{{LANGUAGE}}": c["language"],
    "{{DEV_SERVER_PORT}}": str(c["dev_server_port"]),
    "{{DEV_SERVER_PROCESS}}": c["dev_server_process"],
    "{{MODEL_PLANNER}}": flow_list(MODELS["planner"]),
    "{{MODEL_REVIEWER}}": flow_list(MODELS["reviewer"]),
    "{{MODEL_IMPLEMENTER}}": flow_list(MODELS["implementer"]),
    "{{MODEL_CODE_REVIEWER}}": flow_list(MODELS["code_reviewer"]),
    "{{MODEL_SCOUT}}": flow_list(MODELS["scout"]) if MODELS["scout"] else "",
    # Effort er valgfri; «standard» = send ikke reasoning_effort (harnessens standard gjelder).
    "{{EFFORT_PLANNER}}": EFFORTS["planner"] or "standard",
    "{{EFFORT_REVIEWER}}": EFFORTS["reviewer"] or "standard",
    "{{EFFORT_IMPLEMENTER}}": EFFORTS["implementer"] or "standard",
    "{{EFFORT_CODE_REVIEWER}}": EFFORTS["code_reviewer"] or "standard",
    "{{EFFORT_SCOUT}}": EFFORTS["scout"] or "standard",
    # Ferdige argument-ledd for koordinatorens `task`-kall (model + valgfri reasoning_effort).
    "{{DISPATCH_ARGS_PLANNER}}": dispatch_args("planner"),
    "{{DISPATCH_ARGS_REVIEWER}}": dispatch_args("reviewer"),
    "{{DISPATCH_ARGS_IMPLEMENTER}}": dispatch_args("implementer"),
    "{{DISPATCH_ARGS_CODE_REVIEWER}}": dispatch_args("code_reviewer"),
    "{{DISPATCH_ARGS_SCOUT}}": dispatch_args("scout"),
    # Fix-runde 3+ og rotårsaksanalyse: dyp modell (kode-reviewerens) med dens effort.
    "{{DEEP_DISPATCH_ARGS}}": dispatch_args("implementer", model_role="code_reviewer"),
    # Utledes fra modell-nøklene — en håndskrevet streng drifter fra modellene den beskriver.
    # Første modell per rolle, i rekkefølgen planner/reviewer/implementer/code_reviewer.
    # Valgfri override via models.display.
    "{{MODELS_DISPLAY}}": _md or "/".join(primary(r) for r in ("planner", "reviewer", "implementer", "code_reviewer")),
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
    "{{TECH_REVIEW_AGENT_TOOL}}": tech_review_agent_tool,
    "{{TECH_REVIEW_AGENT_NAMES}}": tech_review_agent_names,
    "{{TECH_REVIEW_TRIGGER_GLOBS}}": tech_review_trigger_globs,
    "{{TECH_REVIEW_SEVERITY_FLOORS}}": tech_review_severity_floors,
    "{{TECH_REVIEW_FLOOR_EXEMPTIONS}}": tech_review_floor_exemptions,
    "{{CANARY_FILE}}": c["canary_source"],
    "{{LESSONS_TOPICS_BULLETS}}": lessons_topics_bullets,
    "{{LESSONS_INDEX_ENTRIES}}": lessons_index_entries,
    "{{AGENT_MEMORY_ROLES}}": agent_memory_roles,
    "{{TYPECHECK_ON_EDIT_CASE}}": typecheck_case,
    **bootstrap,
    "{{PAUSE_TRIGGERS}}": c["pause_triggers"],
    "{{RELEASE_COMMAND}}": c["release"]["command"],
    "{{HEALTH_CHECK_INTERVAL}}": str(c["release"]["health_check_merge_interval"]),
    "{{PIPELINE_MAX_IN_FLIGHT}}": str(_pmif),
    "{{PARALLEL_IMPLEMENTERS_MAX}}": str(_pimax),
    "{{RETRO_FILE_CLASSES}}": retro_file_classes,
    "{{SCOUT_MAX_FINDINGS}}": str(_sc.get("max_findings") or ""),
    "{{SCOUT_AGENT_TOOL}}": scout_agent_tool,
    "{{SCOUT_DELEGATION_BLOCK_IMPLEMENTER}}": scout_delegation_block_impl,
    "{{SCOUT_DELEGATION_BLOCK}}": scout_delegation_block,
    "{{SCOUT_PROBE_BULLET}}": scout_probe_bullet,
    "{{SCOUT_MODEL_ROW}}": scout_model_row,
    "{{SCOUT_USAGE_LINE}}": scout_usage_line,
    # guard-fix-round-model.sh + koordinatorens implementer-dispatch (§5/§5b):
    "{{IMPLEMENTER_MODEL_ALIAS}}": _impl_list[0],
    "{{DEEP_MODEL_ALIAS}}": _deep_list[0],
    "{{IMPLEMENTER_DISPATCH_ALLOWED}}": case_pattern(_impl_allowed),
    "{{DEEP_DISPATCH_ALLOWED}}": case_pattern(_deep_list),
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
# kjørehistorikk. retro-log.md er samme runtime-state-klasse —
# koordinatorens §8 mini-retro-entries ville forsvunnet ved regenerering.
# retro-triage.md er også samme runtime-state-klasse — §8b-triagen
# av retro-loggen akkumulerer beslutninger over tid og ville forsvunnet ved
# regenerering. decision-log.md er også samme runtime-state-klasse
# — nivå-B-beslutningsloggen akkumulerer over tid og ville forsvunnet ved
# regenerering. Alle fire templatenes egen header dokumenterer denne kontrakten.
SEED_ONLY = {
    "docs/loop/run-log.md",
    "docs/loop/retro-log.md",
    "docs/loop/retro-triage.md",
    "docs/loop/decision-log.md",
    # v3: prosjekt-eide filer. Skrives KUN første gang — prosjektet eier dem deretter.
    # AGENTS.md lenker til den genererte docs/loop-rules.md (se etter-stegene under).
    "AGENTS.md",
    "tasks/lessons.md",
    "docs/naming-conventions.md",
    "docs/data-model.md",
    # v3.6: køsidens prosjektdel og artefakt-lenkene. queue-status.py er kit-eid og lik overalt;
    # tittel, eierskap, notater og leverte releaser står i queue-config.py. artifacts.md bærer
    # prosjektets URL-er — en regenerering ville slettet dem (kit-drift.py vokter Køsiden-raden).
    "tasks/queue-config.py",
    "docs/loop/artifacts.md",
}
written, leftovers, preserved, skipped = [], [], [], []
PROJ = c["project_name"]
# SKIP_WHEN_OFF: templates som tilhører en valgfri rolle. Er rollen av, skal fila
# ikke genereres i det hele tatt (den ville ellers stått igjen med {{MODEL_SCOUT}}
# og trigget leftovers-gaten). En eksisterende generert fil fjernes IKKE automatisk
# — /setup sletter aldri; skriptet sier fra så mennesket kan slette bevisst.
# scripts/readonly-check.sh og scripts/test-readonly-check.sh står ALDRI her: read-only-
# sjekken etter hver read-only-dispatch er ikke valgfri.
SKIP_WHEN_OFF = set() if _sc_enabled else {f".github/agents/{PROJ}-scout.agent.md"}
if not _hooks_on["main_merge_guard"]:
    SKIP_WHEN_OFF |= {".github/hooks/scripts/guard-main-merge.sh", ".github/hooks/scripts/test-guard-main-merge.sh"}
if not _hooks_on["implementer_model_guard"]:
    SKIP_WHEN_OFF |= {".github/hooks/scripts/guard-fix-round-model.sh", ".github/hooks/scripts/test-guard-fix-round-model.sh"}
if not _hooks_on["compaction_checkpoint"]:
    SKIP_WHEN_OFF |= {".github/hooks/scripts/precompact-checkpoint.sh",
                      ".github/hooks/scripts/test-checkpoint-hooks.sh", "docs/loop/steps/0c-sjekkpunkt.md"}
if not _hooks_on["session_start_lint"]:
    SKIP_WHEN_OFF.add(".github/hooks/scripts/session-start-lint.sh")
if not _hooks_on["typecheck_on_edit"]:
    SKIP_WHEN_OFF.add(".github/hooks/scripts/typecheck-on-edit.sh")
for dirpath, dirs, files in os.walk(TPL):
    dirs[:] = [d for d in dirs if d != "__pycache__"]
    for fn in files:
        src = os.path.join(dirpath, fn)
        rel = os.path.relpath(src, TPL)
        # Rename agent-filer: PROJECT_NAME-*.agent.md → <project>-*.agent.md
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

# --- Frontmatter-gate: hver generert .agent.md og SKILL.md MÅ ha gyldig YAML-frontmatter ---
# En agent med ødelagt frontmatter lastes ikke, og feilen viser seg først som «Unknown
# agent_type» i en fersk sesjon. Feil høyt her i stedet.
bad_frontmatter = []
for _rel in written:
    if not (_rel.endswith(".agent.md") or _rel.endswith("/SKILL.md")):
        continue
    with open(os.path.join(ROOT, _rel)) as f: _t = f.read()
    _fm = re.match(r"---\n(.*?)\n---\n", _t, re.S)
    try:
        _meta = yaml.safe_load(_fm.group(1)) if _fm else None
    except yaml.YAMLError as e:
        bad_frontmatter.append(f"{_rel}: {str(e).splitlines()[0]}")
        continue
    if not isinstance(_meta, dict) or not _meta.get("name") or not _meta.get("description"):
        bad_frontmatter.append(f"{_rel}: mangler frontmatter med name + description")

# --- Seed lessons-tema-filer og agent-minne (kun hvis de mangler) ----------------------
seeded, notes = [], list(notes_pre)
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
                     "python3 v3-copilot-agent-orchestrator/scripts/split-lessons.py (se MIGRATION.md)")
for _r in _am_roles:
    _agent = f"{PROJ}-{_role_agent[_r]}"
    seed(f"tasks/agent-memory/{_agent}/MEMORY.md", f"""# {_agent} — rollehukommelse

Kontrakt (form, tak, kurering, eierskap): se charterets § Rollehukommelse og
`docs/loop-rules.md` § «Tre kunnskapsbaser». Ikke kopier den hit.
Agenten leser fila i Steg 0 og foreslår endringer som `memory_candidates` i rapporten;
koordinatoren er eneste skriver.

<!-- BOOTSTRAP-UNVERIFIED (satt opp av /setup) — SELVFJERNENDE.
     Står denne blokken her, er skrivestien til agent-minnet ennå ikke verifisert
     i drift. Første agent som leser dette: foreslå i rapportens `memory_candidates`
     at linja under legges i «## Påstander» OG at hele denne blokken slettes.
     Koordinatoren gjør begge endringene i samme commit.
       - (bootstrap) skrivesti verifisert <YYYY-MM-DD>, TODO <nr>
     Neste kurering fjerner bootstrap-linja igjen — den er et kvitteringsspor,
     ikke en påstand. -->

## Påstander

_(tom — fylles av koordinatoren fra agentens `memory_candidates` når en runde faktisk gir en observasjon)_
""")

# --- AGENTS.md: sørg for lenken til den genererte docs/loop-rules.md -------------------
# Copilot leser AGENTS.md som egendefinerte instrukser, men følger ingen import-syntaks — reglene
# må lenkes og leses. Et prosjekt med egen AGENTS.md fra før får den ikke overskrevet (seed-only
# over) — men uten lenken ville loop-reglene aldri nådd sesjonen. Én linje, idempotent
# (nøkkel = lenkemålet).
LOOP_RULES_LINE = ("Loop-reglene står i [`docs/loop-rules.md`](docs/loop-rules.md). "
                   "Les og følg den før alt loop-arbeid.")
_cm = os.path.join(ROOT, "AGENTS.md")
with open(_cm) as f: _cmt = f.read()
if "](docs/loop-rules.md)" not in _cmt:
    with open(_cm, "a") as f:
        f.write(("" if _cmt.endswith("\n") else "\n") + "\n## Loop- og kunnskapsregler\n\n" + LOOP_RULES_LINE + "\n")
    notes.append("AGENTS.md: la til lenken til docs/loop-rules.md (fila fantes fra før og ble ellers ikke rørt)")
if re.search(r"^@docs/loop-rules\.md\s*$", _cmt, re.M):
    notes.append("AGENTS.md: linja `@docs/loop-rules.md` er en importsyntaks Copilot ikke følger — "
                 "fjern den manuelt (lenken over gjør jobben)")

# --- .github/hooks/loop-guards.json: GENERERT (kit-eid, overskrives) ---------------------
# Copilot laster alle .github/hooks/*.json (version 1). Kit-et eier denne ene fila og skriver
# den på nytt hver gang fra hooks.* — prosjektets egne hooks ligger i andre filer i samme mappe
# og røres aldri. Hookene filtrerer selv på toolName (payloaden har ingen matcher).
_HOOK_REG = [
    ("main_merge_guard",        "preToolUse",  "bash .github/hooks/scripts/guard-main-merge.sh",      30),
    ("implementer_model_guard", "preToolUse",  "bash .github/hooks/scripts/guard-fix-round-model.sh", 30),
    ("typecheck_on_edit",       "postToolUse", "bash .github/hooks/scripts/typecheck-on-edit.sh",     120),
    ("session_start_lint",      "sessionStart","bash .github/hooks/scripts/session-start-lint.sh",    120),
    ("compaction_checkpoint",   "preCompact",  "sh .github/hooks/scripts/precompact-checkpoint.sh",   30),
]
_hooks_doc = {"version": 1, "hooks": {}}
for _key, _event, _cmd, _timeout in _HOOK_REG:
    if _hooks_on[_key]:
        _hooks_doc["hooks"].setdefault(_event, []).append(
            {"type": "command", "bash": _cmd, "cwd": ".", "timeoutSec": _timeout})
_hp_rel = ".github/hooks/loop-guards.json"
_hp = os.path.join(ROOT, _hp_rel)
_new_hooks = json.dumps(_hooks_doc, indent=2, ensure_ascii=False) + "\n"
_old_hooks = open(_hp).read() if os.path.exists(_hp) else None
if _old_hooks is not None and _old_hooks != _new_hooks:
    notes.append(f"{_hp_rel}: overskrevet (kit-eid — egne hooks hører hjemme i en annen fil i .github/hooks/)")
os.makedirs(os.path.dirname(_hp), exist_ok=True)
with open(_hp, "w") as f: f.write(_new_hooks)
written.append(_hp_rel)

# --- Foreldede filer fra eldre kit-versjoner: rapporteres, slettes aldri -------------------
for _old in (".github/hooks/scripts/guard-reviewer-readonly.sh",
             ".github/hooks/scripts/test-guard-reviewer-readonly.sh",
             ".github/hooks/scripts/reviewer-readonly.contract",
             ".github/hooks/scripts/sessionstart-checkpoint.sh"):
    if os.path.exists(os.path.join(ROOT, _old)):
        notes.append(f"{_old} er foreldet (ikke lenger del av kit-et) — slett den manuelt")

# --- .gitignore: runtime-filer fra hooks og worktree-rydding --------------------------
_GI = ["tasks/hook-blocks.log*", ".loop-worktrees/", ".loop-worktree-rescue/", "tasks/.loop-state/"]
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
    print("\nEndringer og merknader i prosjektfiler:")
    for n in notes: print(f"  ~ {n}")

# Vaktene trenger jq og slipper ALT gjennom (fail-open) hvis den mangler. Sjekk mot det de
# genererte skriptene faktisk kaller: en hardkodet /usr/bin/jq, ellers jq på PATH.
_guards = [os.path.join(ROOT, w) for w in written if w.startswith(".github/hooks/scripts/guard-")]
_needs_abs = any("/usr/bin/jq" in open(g).read() for g in _guards)
if _guards and ((_needs_abs and not os.access("/usr/bin/jq", os.X_OK)) or (not _needs_abs and not shutil.which("jq"))):
    print("\n⚠️  jq finnes ikke der vaktene leter etter den — vaktene slipper da alt gjennom. Installer jq "
          "(Linux: apt install jq; macOS 15+ har den innebygd) før loopen kjøres.")

if bad_frontmatter:
    print("\n❌ UGYLDIG FRONTMATTER — agentene/skillene lastes ikke:")
    for b in bad_frontmatter: print(f"  {b}")
if leftovers:
    print("\n❌ GJENVÆRENDE TOKENS — kit-et er IKKE komplett:")
    for rel, toks in leftovers:
        print(f"  {rel}: {', '.join(toks)}")
if leftovers or bad_frontmatter:
    sys.exit("Fiks template/config og kjør /setup på nytt.")
print("\n✅ Ingen gjenværende tokens. Neste: kopier tech-review-agenter, commit, "
      "START FERSK SESJON, kjør agent-proben i run-loop-skillen.")
PY
```

## Etterpå (manuelt)

- **Restart kreves:** de genererte `<project>-*`-agentene, skillene og hookene i
  `.github/hooks/loop-guards.json` er ikke lastet før en ny sesjon starter. Start fersk
  Copilot-sesjon FØR du kjører `/run-loop`.
- **Probe:** første handling i ny sesjon = agent-proben i run-loop-skillen
  (`{"ok": true}`-dispatch med `task`). `Unknown agent_type: <navn>` → registeret tok ikke
  endringen; bekreft at filene ligger i `.github/agents/` som `<navn>.agent.md` med gyldig
  frontmatter, og start på nytt.
- **UVERIFISERT:** at VS Code-harnessen laster `.github/hooks/*.json` og `.github/skills/*/SKILL.md`
  uten ekstra innstillinger. Ser du ikke `/run-loop` i chatten, eller blokkerer ikke
  `guard-main-merge.sh` en push-test mot prod-branchen i en fersk sesjon, sjekk Copilot-
  innstillingene for agent-skills og hooks før loopen kjøres.
