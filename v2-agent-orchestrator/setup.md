# /setup — kompiler loop.config.yaml inn i kit-et

> **Installasjon:** kopier denne fila til prosjektets `.claude/commands/setup.md`
> så den blir kjørbar som `/setup`. Den er bevisst IKKE tokenisert — den er
> bootstrapperen som *gjør* tokeniseringen, ikke en del av det genererte kit-et.

Du kjører `/setup` i et prosjekt som har lagt v2-mappen
(`v2-agent-orchestrator/`) i roten og fylt ut `loop.config.yaml`. Kommandoen
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
   `v2-agent-orchestrator/templates/`. Skriptet skriver generert output til
   prosjektets `.claude/`, `docs/`, `tasks/`. Du kan alltid diffe de to.
5. **Avslutt med restart + probe.** Agent-registeret lastes ved sesjonsstart.
   Etter `/setup`: start en FERSK sesjon og kjør agent-proben fra
   `run-loop.md` for å bekrefte at `<project>-*`-agentene er registrert.

## Steg

1. Bekreft at `v2-agent-orchestrator/loop.config.yaml` finnes og er fylt
   (ikke `loop.config.example.yaml` — kopier og fyll den først).
2. Kjør substitusjons-skriptet under fra prosjektroten. Det validerer, renamer
   agentene til `<project_name>-*`, substituerer alle tokens, prepender
   GENERERT-headeren, og skriver til prosjektets stier.
3. Les skriptets sluttrapport. Gjenværende-token-feil eller manglende-nøkkel-feil
   → fiks config / templates og kjør på nytt. Aldri fortsett med en delvis
   generert kit.
4. **Tech-review-agenter:** kopier prosjektets egne domene-reviewere inn i
   `.claude/agents/` (se `v2-agent-orchestrator/examples/` for maler). Disse
   er pluggbare — code-revieweren dispatcher dem etter `tech_review_agents` i
   config. Har prosjektet ingen → sett `tech_review_agents: []`.
5. **Stillas:** hvis prosjektet ikke allerede har det, kopier scaffolding
   (`pre-push`-hook, CI-workflow) — se `scaffolding/` og README §«Forutsetninger».
6. Commit de genererte filene. Start fersk sesjon. Kjør `/run-loop once`.

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
| `{{MODELS_DISPLAY}}` | `models.display` |
| `{{DEV_ENV_ID}}` / `{{PROD_ENV_ID}}` | `environments.dev_id` / `environments.prod_id` |
| `{{BASE_BRANCH}}` / `{{RELEASE_BRANCH}}` / `{{PROD_BRANCH}}` | `branch_strategy.*` |
| `{{CMD_BUILD}}` / `{{CMD_TYPE_CHECK}}` / `{{CMD_TYPE_CHECK_SCRIPT}}` / `{{CMD_LINT}}` / `{{CMD_TEST}}` / `{{CMD_E2E}}` | `verification_commands.*` |
| `{{TIER1_INVARIANTS}}` | `tier1_invariants` (blokk) |
| `{{TECH_REVIEW_AGENTS_DISPATCH}}` | `tech_review_agents` (rendret blokk) |
| `{{CANARY_FILE}}` | `canary_source` |
| `{{LESSONS_TOPICS}}` | `lessons_topics` (komma-liste) |
| `{{PAUSE_TRIGGERS}}` | `pause_triggers` |
| `{{RELEASE_COMMAND}}` | `release.command` |
| `{{HEALTH_CHECK_INTERVAL}}` | `release.health_check_merge_interval` |
| `{{GENERATED_HEADER}}` | fast tekst (se skript) |

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
KIT  = os.path.join(ROOT, "v2-agent-orchestrator")
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
    "models.code_reviewer_effort","models.display",
    "environments.dev_id","environments.prod_id",
    "branch_strategy.base_branch","branch_strategy.release_branch","branch_strategy.prod_branch",
    "verification_commands.build","verification_commands.type_check",
    "verification_commands.type_check_script","verification_commands.lint",
    "verification_commands.test","verification_commands.e2e",
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

# --- Render block-tokens --------------------------------------------------
topics = ", ".join(c["lessons_topics"])
tras = c.get("tech_review_agents") or []
if tras:
    lines = []
    for a in tras:
        lines.append(f"   - Hvis diffen berører {a['trigger']} → dispatcher `{a['name']}`-agenten "
                     f"som frisk sub-agent (egen kontekst, ser kun diffen). Severity-map: {a['severity_map']}.")
    tech_block = "\n".join(lines)
else:
    tech_block = "   - (Ingen tech-review-agenter konfigurert — hopp over sikkerhets-/domene-armen.)"

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
    "{{MODELS_DISPLAY}}": c["models"]["display"],
    "{{DEV_ENV_ID}}": str(c["environments"]["dev_id"]),
    "{{PROD_ENV_ID}}": str(c["environments"]["prod_id"]),
    "{{BASE_BRANCH}}": c["branch_strategy"]["base_branch"],
    "{{RELEASE_BRANCH}}": c["branch_strategy"]["release_branch"],
    "{{PROD_BRANCH}}": c["branch_strategy"]["prod_branch"],
    "{{CMD_BUILD}}": c["verification_commands"]["build"],
    "{{CMD_TYPE_CHECK}}": c["verification_commands"]["type_check"],
    "{{CMD_TYPE_CHECK_SCRIPT}}": c["verification_commands"]["type_check_script"],
    "{{CMD_LINT}}": c["verification_commands"]["lint"],
    "{{CMD_TEST}}": c["verification_commands"]["test"],
    "{{CMD_E2E}}": c["verification_commands"]["e2e"],
    "{{TIER1_INVARIANTS}}": c["tier1_invariants"].rstrip("\n"),
    "{{TECH_REVIEW_AGENTS_DISPATCH}}": tech_block,
    "{{CANARY_FILE}}": c["canary_source"],
    "{{LESSONS_TOPICS}}": topics,
    "{{PAUSE_TRIGGERS}}": c["pause_triggers"],
    "{{RELEASE_COMMAND}}": c["release"]["command"],
    "{{HEALTH_CHECK_INTERVAL}}": str(c["release"]["health_check_merge_interval"]),
    "{{GENERATED_HEADER}}": HEADER,
}

def subst(text):
    for k, v in M.items():
        text = text.replace(k, v)
    return text

# --- Walk templates → render → write -------------------------------------
written, leftovers = [], []
PROJ = c["project_name"]
for dirpath, _, files in os.walk(TPL):
    for fn in files:
        src = os.path.join(dirpath, fn)
        rel = os.path.relpath(src, TPL)
        # Rename agent-filer: PROJECT_NAME-*.md → <project>-*.md
        out_rel = rel.replace("PROJECT_NAME-", f"{PROJ}-")
        dst = os.path.join(ROOT, out_rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        with open(src) as f: body = f.read()
        body = subst(body)
        rem = re.findall(r"\{\{[A-Z_]+\}\}", body)
        if rem:
            leftovers.append((out_rel, sorted(set(rem))))
        with open(dst, "w") as f: f.write(body)
        written.append(out_rel)

print(f"Skrev {len(written)} filer:")
for w in sorted(written): print(f"  ✓ {w}")

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
