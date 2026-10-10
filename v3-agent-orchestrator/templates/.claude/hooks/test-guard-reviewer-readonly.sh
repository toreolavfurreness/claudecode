#!/usr/bin/env bash
# {{PROJECT_NAME}} — regresjonsharness for .claude/hooks/guard-reviewer-readonly.sh
#
# Kjøres: bash .claude/hooks/test-guard-reviewer-readonly.sh [sti-til-hook]
# Standard testmål: guard-reviewer-readonly.sh i samme katalog som denne fila.
# For rød→grønn-demonstrasjon: kjør mot en stubb som alltid `exit 0`
# (`printf '#!/usr/bin/env bash\nexit 0\n' > /tmp/stub.sh`) og mot fiksen, og
# lim begge kjøringer ordrett i PR-beskrivelsen.
#
# Fasit = hookens EGEN exit-kode (2 = BLOKKERT, 0 = SLIPPER) — ikke grep i eget
# skall. Hooken har ingen
# charter-tools:/disallowedTools:-tolkning fra hooken (strukturendring, ikke
# en lapp — se guard-reviewer-readonly.sh sin toppkommentar) — hooken leser nå
# KUN .claude/hooks/reviewer-readonly.contract for klassifisering, Agent-
# allowlist og ekstra verktøy. Per-case CLAUDE_PROJECT_DIR peker på FLERE
# separate mktemp -d-kataloger (aldri den ekte .claude/-mappa — MINDRE-funn
# runde 1):
#   FIXDIR         — SYNTETISK kontraktfil for A/B/C/X/K-casene
#   DFIXDIR        — KOPI av den EKTE .claude/agents/ + den EKTE
#                     .claude/hooks/reviewer-readonly.contract, for
#                     D-assertions (drift mot faktisk config)
#   NOFIXDIR       — INGEN kontraktfil (K1/K2/K7)
#   EMPTYFIXDIR    — 0-byte kontraktfil (K3)
#   GARBAGEFIXDIR  — ren søppeltekst uten TAB-felt (K4)
#   MALFORMEDFIXDIR— én linje mangler et felt (K5)
#   COMMENTFIXDIR  — et rollenavn med '#' i seg (K6)
# Ingen nettverkskall.
#
# Case-antall er hardkodet mot planens lister (reviewerens anbefaling, runde
# 3): et droppet case skal gjøre harnessen RØD, ikke usynlig.
#   A1–A33  (33) — Agent/Task-armen (A26 lagt til i koordinator-fix-runden,
#                  MINDRE 4: permission_mode er feltnavnet den ekte SDK-en
#                  bruker, ikke bare .mode. A27–A30 lagt til i koordinator-fix
#                  runde 2, VIKTIG 1/VIKTIG 2: A27–A29 er de tre bekreftede
#                  skygge-motprøvene mot `//`-fallback-kjeden i mode-sjekken,
#                  A30 er verdi-skann-escapen via permission_mode uten
#                  subagent_type. A31–A32 lagt til i koordinator-fix runde 3:
#                  A31 er MINDRE 1 (mode-felt er et array, ikke en streng —
#                  MÅ blokkeres, ikke droppes stille av et type-filter), A32
#                  er VIKTIG (Steg C ga tidligere WOULD-ALLOW(value-scan) for
#                  denne payloaden, deretter fail-closed BLOCK — nå er Steg C
#                  en ubetinget block() uten skann, se koordinator-fix runde
#                  5 VIKTIG 3). A33 lagt til i koordinator-fix runde 5,
#                  VIKTIG 4: isolation:false MÅTTE tidligere IKKE blokkere
#                  (jq `//` faller gjennom på false), nå speiler den
#                  type-bevarte mode-håndteringen og blokkerer alt ikke-null.
#   B1–B99  (99)  — Bash-armen (B98–B99 lagt til i koordinator-fix runde 5,
#                  MINDRE 1: `git fetch origin` med en skrivende refspec eller
#                  med --prune/--force ga tidligere exit=0 uendret av arm 1s
#                  størrelses-/tokenkontroll. B100–B103, en modus-uavhengig
#                  carve-in mot .claude/hooks/ lagt til i koordinator-fix
#                  runde 8, er SLETTET i runde 9 — se «Fix-runde 9»: carve-in-en
#                  bommet på seks av sju motprøvde skriveformer og blokkerte to
#                  legitime lesekommandoer, uten å tilføre noe i enforce-modus)
#   C1–C34  (34) — verktøynavn-armen (C23–C29 lagt til i koordinator-fix-runden,
#                  VIKTIG 2: én PASS-case per SESSION_SAFE-oppføring + to
#                  BLOCK-regresjonsbevis for SendMessage/Monitor som ble
#                  fjernet. C30–C33 lagt til i koordinator-fix runde 5,
#                  MINDRE 3: aliasene kjørende runtime (2.1.247) faktisk
#                  sender for BashOutput/KillShell/TaskOutput)
#                  C34 lagt til 2026-09-25: SubagentHandback (runtime 2.1.280).
#   X1–X11   (11) — robusthet (X6 lagt til i koordinator-fix runde 3, MINDRE 2:
#                  en patchet kopi av hooken med en ødelagt MODE_JQ_PATHS
#                  simulerer et feltnavn med spesialtegn — selvtesten MÅ
#                  blokkere i stedet for å feile stille. X7–X8 lagt til i
#                  koordinator-fix runde 5: X7 er VIKTIG 2 sin bekreftede
#                  motprøve — et `\n` etter tool_name forskjøv tidligere
#                  ALLE påfølgende felt i én posisjonell jq-lesing og slo
#                  gaten helt av. X8 er VIKTIG 5 — en 1 MB `isolation`-verdi
#                  skal fortsatt BLOKKERE og begge logglinjene skal forbli
#                  under 1 kB. X9–X10 lagt til i koordinator-fix runde 6:
#                  X9 er MINDRE 4 — agent_type med path-traversal-tegn
#                  saneres nå eksplisitt FØR CHARTER-stien bygges (samme
#                  exit-kode som før, men nå LOGGET). X10 er MINDRE 1 — en
#                  300-tegns multibyte-payload skal fortsatt være gyldig
#                  UTF-8 etter sanitize_logval()s avkorting, nå som
#                  LC_ALL=C.UTF-8 er satt eksplisitt. X11 lagt til i en
#                  fortsettelse av koordinator-fix runde 6 (Linux CI-funn,
#                  run 33492149355): CI-koblingen (VIKTIG 1) avdekket at
#                  X5/X8 var fail-OPEN på Linux (exit=0, forventet BLOCK) —
#                  rotårsak var Linux' MAX_ARG_STRLEN (128 KiB per
#                  argv-element), rammet BÅDE denne harnessens EGEN
#                  payload-bygging (`jq -n --arg ... "$stor_verdi"`, fikset
#                  til å bruke `jq -Rs` via stdin i X5/X8) OG hookens
#                  interne Bash-arm-skanner (perl kalt med $CMD som
#                  argv-element, fikset til stdin + en bash-side
#                  størrelsesvakt FØR perl startes). X11 er en dedikert
#                  regresjonsvakt for `list_contains()` (nå ren bash, ingen
#                  grep) med en 1.5 MB verdi som BEKREFTET feiler exec selv
#                  på macOS' totale ARG_MAX — rød på BEGGE plattformer ved
#                  reversering, ikke bare i Linux CI.)
#   D1–D5    (5) — drift mot EKTE config (uendret prinsipp fra koordinator-fix
#                  runde 6, VIKTIG 2, men datakilden er nå den EKTE
#                  kontraktfila i stedet for ekte charter-tools:-linjer): D1/D3
#                  itererer over de EKTE charterfilene i .claude/agents/ og
#                  spør hooken selv (Write-probe) om klassifiseringen —
#                  asserer at "ikke-read-only-settet er nøyaktig
#                  {{{PROJECT_NAME}}-implementer, {{PROJECT_NAME}}-planner}" (D1) og at
#                  hele WRITE_DENYLIST_EXACT blokkeres for enhver read-only-
#                  klassifisert rolle (D3). D2 uendret (code-reviewerens
#                  effektive Agent-allowlist). D4 er NY i runde 7: code-
#                  reviewerens Agent-felt i den EKTE kontraktfila må stemme
#                  eksakt med tech_review_agents-navnene i
#                  v3-agent-orchestrator/loop.config.yaml — en lens-agent lagt
#                  til i config, men glemt i kontrakten, blir rød automatisk.
#                  (Gamle D4–D8 testet charter-tools:/disallowedTools-
#                  parsingformer — q1/p1-clean, drift-strict-form,
#                  drift-yaml-blocklist, r1-write-surface,
#                  disagree-tools-grants — som IKKE lenger finnes; slettet,
#                  ikke bare erstattet, se PR-beskrivelsen for full liste.)
#                  D5 er NY i runde 8 (VIKTIG 4): en REN FIL-MOT-FIL-
#                  assersjon (ikke en hook-probe) som krever at
#                  .claude/agents/<rolle>.md for HVER rolle i den EKTE
#                  kontraktfila fortsatt har en disallowedTools:-linje som
#                  lister minst Write og Edit — det ENESTE gjenværende
#                  runtime-håndhevede filteret siden hooken selv
#                  ikke lenger leser charterfilene i det hele tatt.
#   K1–K17  (17) — NYE i runde 7: kontrakt-mekanikk med syntetiske roller —
#                  manglende/tom/søppel/delvis-uparsbar kontraktfil (K1–K7,
#                  inkludert at PARSE-FAIL faktisk logges), rolle uten
#                  Agent-liste blokkerer ALL dispatch (K8), rolle MED
#                  Agent-liste tillater kun de navngitte (K9–K10), en
#                  kontraktfil som prøver å grante Write/MultiEdit/mcp__* via
#                  ekstra-verktøy-feltet blokkeres likevel av
#                  WRITE_DENYLIST_EXACT (K11–K13), og
#                  {{PROJECT_NAME}}-planner/-implementer forblir ikke-read-only via
#                  den EKTE kontrakten (K14–K15). K16–K17 lagt til i runde 8
#                  (VIKTIG 1), symmetrisk med K11–K13: samme
#                  greedy-role-kontrakt prøver å grante Monitor/SendMessage —
#                  denylisten vinner uansett.
#   M1       (1) — meta: hver oppføring i hookens SESSION_SAFE MÅ ha en
#                  tilhørende C-case, ellers RØD (VIKTIG 2: selvassersjonen av
#                  case-ANTALL fanger droppede caser, ikke MANGLENDE dekning
#                  av et nytt SESSION_SAFE-verktøy — dette gjør begge deler).
#                  Koordinator-fix runde 2 (MINDRE 2): TodoWrite/BashOutput
#                  bokføres nå mot sine faktiske C-caser (C16/C15) i stedet
#                  for "", og run_m validerer i tillegg at case-IDen finnes
#                  i C_IDS og forventer PASS — en renummerering kan ikke
#                  lenger gi stille grønt.
#   SUM     202 (+ A17c/A32c/B74b = 3 ekstra scorede caser UTENFOR ID-listene,
#                se "Sluttassersjon 2" nederst i fila — faktisk scoret total
#                er 205)

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOOK="${1:-$SCRIPT_DIR/guard-reviewer-readonly.sh}"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

if [ ! -f "$HOOK" ]; then
  echo "Fant ikke hook: $HOOK" >&2
  exit 1
fi

FIXDIR="$(mktemp -d)"
DFIXDIR="$(mktemp -d)"
NOFIXDIR="$(mktemp -d)"
EMPTYFIXDIR="$(mktemp -d)"
GARBAGEFIXDIR="$(mktemp -d)"
MALFORMEDFIXDIR="$(mktemp -d)"
COMMENTFIXDIR="$(mktemp -d)"
cleanup() { rm -rf "$FIXDIR" "$DFIXDIR" "$NOFIXDIR" "$EMPTYFIXDIR" "$GARBAGEFIXDIR" "$MALFORMEDFIXDIR" "$COMMENTFIXDIR"; }
trap cleanup EXIT

mkdir -p "$FIXDIR/.claude/hooks" "$FIXDIR/tasks"
mkdir -p "$DFIXDIR/.claude/hooks" "$DFIXDIR/tasks"
cp -R "$REPO_ROOT/.claude/agents" "$DFIXDIR/.claude/agents"
cp "$REPO_ROOT/.claude/hooks/reviewer-readonly.contract" "$DFIXDIR/.claude/hooks/reviewer-readonly.contract"
mkdir -p "$NOFIXDIR/.claude/hooks" "$NOFIXDIR/tasks"
mkdir -p "$EMPTYFIXDIR/.claude/hooks" "$EMPTYFIXDIR/tasks"
: > "$EMPTYFIXDIR/.claude/hooks/reviewer-readonly.contract"
mkdir -p "$GARBAGEFIXDIR/.claude/hooks" "$GARBAGEFIXDIR/tasks"
printf 'dette er ikke en kontraktfil\nbare rot og tull\n' > "$GARBAGEFIXDIR/.claude/hooks/reviewer-readonly.contract"
mkdir -p "$MALFORMEDFIXDIR/.claude/hooks" "$MALFORMEDFIXDIR/tasks"
printf '{{PROJECT_NAME}}-code-reviewer\trls-migration-reviewer\t-\nbroken-role-missing-field\t-\n' > "$MALFORMEDFIXDIR/.claude/hooks/reviewer-readonly.contract"
mkdir -p "$COMMENTFIXDIR/.claude/hooks" "$COMMENTFIXDIR/tasks"
printf 'some-role#with-hash\t-\t-\n' > "$COMMENTFIXDIR/.claude/hooks/reviewer-readonly.contract"

# ── Kontraktfil — hookens ENESTE
# beslutningsinput. Speiler den EKTE .claude/hooks/reviewer-readonly.contract
# (seks read-only roller), PLUSS fire rene
# test-roller (no-tools-agent, readonly-no-agents, readonly-with-agents,
# greedy-role) som beviser at mekanismen er generisk — ikke hardkodet mot de
# seks ekte navnene. Charter-filer (.claude/agents/*.md) LESES IKKE LENGER av
# hooken i det hele tatt — INGEN syntetiske charterfiler trengs lenger for
# A/B/C/X-casene (hele tools:/disallowedTools:-tolkningen er slettet fra
# hooken, ikke lappet).
# NB: Agent-feltet på {{PROJECT_NAME}}-code-reviewer-linja under holdes BEVISST på
# de tre gamle navnene (rls-migration-reviewer,edge-function-reviewer,
# ios-design-reviewer) — A2-A4 prober disse tre spesifikt. race-reviewer
# dekkes IKKE herfra, men av D2 mot DFIXDIR (cp -R av den EKTE kontrakten,
# se over), som er den ekte kontrakten.
cat > "$FIXDIR/.claude/hooks/reviewer-readonly.contract" <<'CONTRACTEOF'
{{PROJECT_NAME}}-reviewer	-	-
{{PROJECT_NAME}}-code-reviewer	rls-migration-reviewer,edge-function-reviewer,ios-design-reviewer	-
rls-migration-reviewer	-	-
edge-function-reviewer	-	-
ios-design-reviewer	-	WebFetch
race-reviewer	-	-
no-tools-agent	-	-
readonly-no-agents	-	-
readonly-with-agents	allowed-x,allowed-y	-
greedy-role	-	Write,MultiEdit,mcp__x__apply_migration,Monitor,SendMessage
CONTRACTEOF

GATE_LOG="$FIXDIR/tasks/hook-readonly-gate.log"
LOG_BLOCKS="$FIXDIR/tasks/hook-blocks.log"

# ── Hjelpere ────────────────────────────────────────────────────────────────

# gate_log_lines — antall linjer i gate-loggen akkurat nå (0 hvis fila mangler).
gate_log_lines() {
  if [ -f "$GATE_LOG" ]; then wc -l < "$GATE_LOG" | tr -d ' '; else echo 0; fi
}

# gate_log_new_contains <fra-linje+1> <substreng> — sjekker om nye linjer
# lagt til etter forrige måling inneholder substrengen.
gate_log_new_contains() {
  local from="$1" needle="$2"
  [ -f "$GATE_LOG" ] || return 1
  tail -n +"$from" "$GATE_LOG" | /usr/bin/grep -qF "$needle"
}

run_hook() {
  # $1 = JSON payload, resten = ekstra env "KEY=VAL"-par
  local payload="$1"; shift
  printf '%s' "$payload" | CLAUDE_PROJECT_DIR="$FIXDIR" env "$@" bash "$HOOK" >/dev/null 2>/dev/null
  echo $?
}

run_hook_dfix() {
  local payload="$1"
  printf '%s' "$payload" | CLAUDE_PROJECT_DIR="$DFIXDIR" bash "$HOOK" >/dev/null 2>/dev/null
  echo $?
}

exitcode_to_dom() {
  case "$1" in
    2) echo BLOCK ;;
    0) echo PASS ;;
    *) echo "ERROR($1)" ;;
  esac
}

# ── A: Agent/Task-armen ──────────────────────────────────────────────────────
get_a_payload() {
  case "$1" in
    A1)  jq -n '{agent_type:"{{PROJECT_NAME}}-code-reviewer",tool_name:"Agent",tool_input:{subagent_type:"{{PROJECT_NAME}}-implementer"}}' ;;
    A2)  jq -n '{agent_type:"{{PROJECT_NAME}}-code-reviewer",tool_name:"Agent",tool_input:{subagent_type:"rls-migration-reviewer"}}' ;;
    A3)  jq -n '{agent_type:"{{PROJECT_NAME}}-code-reviewer",tool_name:"Agent",tool_input:{subagent_type:"edge-function-reviewer"}}' ;;
    A4)  jq -n '{agent_type:"{{PROJECT_NAME}}-code-reviewer",tool_name:"Agent",tool_input:{subagent_type:"ios-design-reviewer"}}' ;;
    A5)  jq -n '{agent_type:"{{PROJECT_NAME}}-code-reviewer",tool_name:"Agent",tool_input:{description:"x",prompt:"y"}}' ;;
    A6)  jq -n '{agent_type:"{{PROJECT_NAME}}-reviewer",tool_name:"Agent",tool_input:{subagent_type:"{{PROJECT_NAME}}-implementer"}}' ;;
    A7)  jq -n '{agent_type:"{{PROJECT_NAME}}-reviewer",tool_name:"Agent",tool_input:{subagent_type:"rls-migration-reviewer"}}' ;;
    A8)  jq -n '{tool_name:"Agent",tool_input:{subagent_type:"{{PROJECT_NAME}}-implementer"}}' ;;
    A9)  jq -n '{agent_type:"{{PROJECT_NAME}}-implementer",tool_name:"Agent",tool_input:{subagent_type:"{{PROJECT_NAME}}-code-reviewer"}}' ;;
    A10) jq -n '{agent_type:"rls-migration-reviewer",tool_name:"Agent",tool_input:{subagent_type:"{{PROJECT_NAME}}-implementer"}}' ;;
    A11) jq -n '{agent_type:"{{PROJECT_NAME}}-code-reviewer",tool_name:"Task",tool_input:{subagent_type:"{{PROJECT_NAME}}-implementer"}}' ;;
    A12) jq -n '{agent_type:"general-purpose",tool_name:"Agent",tool_input:{subagent_type:"{{PROJECT_NAME}}-implementer"}}' ;;
    A13) jq -n '{agent_type:"no-tools-agent",tool_name:"Agent",tool_input:{subagent_type:"rls-migration-reviewer"}}' ;;
    A14) jq -n '{agent_type:"{{PROJECT_NAME}}-code-reviewer",tool_name:"Agent",tool_input:{agent_type:"{{PROJECT_NAME}}-implementer"}}' ;;
    A15) jq -n '{agent_type:"{{PROJECT_NAME}}-code-reviewer",tool_name:"Agent",tool_input:{type:"{{PROJECT_NAME}}-implementer"}}' ;;
    A16) jq -n '{agent_type:"{{PROJECT_NAME}}-code-reviewer",tool_name:"Agent",tool_input:{subagent_type:"{{PROJECT_NAME}}-planner"}}' ;;
    A17) jq -n '{agent_type:"{{PROJECT_NAME}}-code-reviewer",tool_name:"Agent",tool_input:{description:"x",prompt:"y",spec:{subagent_type:"rls-migration-reviewer"}}}' ;;
    A18) jq -n '{agent_type:"{{PROJECT_NAME}}-code-reviewer",tool_name:"Agent",tool_input:{subagent_type:"fork"}}' ;;
    A19) jq -n '{agent_type:"{{PROJECT_NAME}}-code-reviewer",tool_name:"Agent",tool_input:{subagent_type:"rls-migration-reviewer",mode:"bypassPermissions"}}' ;;
    A20) jq -n '{agent_type:"{{PROJECT_NAME}}-code-reviewer",tool_name:"Agent",tool_input:{subagent_type:"rls-migration-reviewer",isolation:"worktree"}}' ;;
    A21) jq -n '{agent_type:"{{PROJECT_NAME}}-code-reviewer",tool_name:"Agent",tool_input:{subagent_type:"rls-migration-reviewer",mode:"plan"}}' ;;
    A22) jq -n '{agent_type:"{{PROJECT_NAME}}-reviewer",tool_name:"Agent",tool_input:{description:"x",prompt:"y",spec:{subagent_type:"rls-migration-reviewer"}}}' ;;
    A23) jq -n '{agent_type:"{{PROJECT_NAME}}-code-reviewer",tool_name:"Agent",tool_input:{description:"x",prompt:"y",name:"rls-migration-reviewer"}}' ;;
    A24) jq -n '{agent_type:"{{PROJECT_NAME}}-code-reviewer",tool_name:"Agent",tool_input:{description:"rls-migration-reviewer",prompt:"y"}}' ;;
    A25) jq -n '{agent_type:"{{PROJECT_NAME}}-code-reviewer",tool_name:"Agent",tool_input:{subagent_type:"rls-migration-reviewer",run_in_background:true}}' ;;
    A26) jq -n '{agent_type:"{{PROJECT_NAME}}-code-reviewer",tool_name:"Agent",tool_input:{subagent_type:"rls-migration-reviewer",permission_mode:"bypassPermissions"}}' ;;
    A27) jq -n '{agent_type:"{{PROJECT_NAME}}-code-reviewer",tool_name:"Agent",tool_input:{subagent_type:"rls-migration-reviewer",mode:"default",permission_mode:"bypassPermissions"}}' ;;
    A28) jq -n '{agent_type:"{{PROJECT_NAME}}-code-reviewer",tool_name:"Agent",tool_input:{subagent_type:"rls-migration-reviewer",permission_mode:"default",permissionMode:"bypassPermissions"}}' ;;
    A29) jq -n '{agent_type:"{{PROJECT_NAME}}-code-reviewer",tool_name:"Agent",tool_input:{subagent_type:"rls-migration-reviewer",mode:"",permission_mode:"bypassPermissions"}}' ;;
    A30) jq -n '{agent_type:"{{PROJECT_NAME}}-code-reviewer",tool_name:"Agent",tool_input:{description:"x",prompt:"y",mode:"default",permission_mode:"rls-migration-reviewer"}}' ;;
    A31) jq -n '{agent_type:"{{PROJECT_NAME}}-code-reviewer",tool_name:"Agent",tool_input:{subagent_type:"rls-migration-reviewer",mode:["bypassPermissions"]}}' ;;
    A32) jq -n '{agent_type:"{{PROJECT_NAME}}-code-reviewer",tool_name:"Agent",tool_input:{description:"d",prompt:"skriv fila",zz:"rls-migration-reviewer"}}' ;;
    A33) jq -n '{agent_type:"{{PROJECT_NAME}}-code-reviewer",tool_name:"Agent",tool_input:{subagent_type:"rls-migration-reviewer",isolation:false}}' ;;
  esac
}

get_a_expected() {
  case "$1" in
    A1|A5|A6|A7|A10|A11|A13|A14|A15|A16|A17|A18|A19|A20|A22|A23|A24|A26|A27|A28|A29|A30|A31|A32|A33) echo BLOCK ;;
    A2|A3|A4|A8|A9|A12|A21|A25) echo PASS ;;
  esac
}

get_a_desc() {
  case "$1" in
    A1) echo "code-reviewer -> {{PROJECT_NAME}}-implementer (kriterium 1)" ;;
    A2) echo "code-reviewer -> rls-migration-reviewer (kriterium 4)" ;;
    A3) echo "code-reviewer -> edge-function-reviewer" ;;
    A4) echo "code-reviewer -> ios-design-reviewer" ;;
    A5) echo "code-reviewer, alle tre felt tomme, ingen treff i verdi-skann" ;;
    A6) echo "{{PROJECT_NAME}}-reviewer -> {{PROJECT_NAME}}-implementer" ;;
    A7) echo "{{PROJECT_NAME}}-reviewer -> rls-migration-reviewer (kontraktens agent-felt er '-', ingen allowlist)" ;;
    A8) echo "hovedtraad (agent_type mangler) -> {{PROJECT_NAME}}-implementer" ;;
    A9) echo "{{PROJECT_NAME}}-implementer (ikke read-only) -> code-reviewer" ;;
    A10) echo "rls-migration-reviewer -> {{PROJECT_NAME}}-implementer" ;;
    A11) echo "code-reviewer, tool_name Task (alias) -> {{PROJECT_NAME}}-implementer" ;;
    A12) echo "general-purpose (ingen charterfil) -> {{PROJECT_NAME}}-implementer" ;;
    A13) echo "read-only rolle med tom agent-liste ('-') i kontrakten -> fail-closed" ;;
    A14) echo "fallback-kjede: feltet heter agent_type" ;;
    A15) echo "fallback-kjede: feltet heter type" ;;
    A16) echo "code-reviewer -> {{PROJECT_NAME}}-planner (har Write,Edit)" ;;
    A17) echo "ingen kjent felt truffet -> Steg C er en ubetinget BLOCK (VIKTIG 3 koordinator-fix runde 5: verdi-skannen er fjernet, den bestemte ikke lenger noe)" ;;
    A18) echo "subagent_type fork (dokumentert spesialverdi, ikke i charter)" ;;
    A19) echo "gyldig subagent + mode:bypassPermissions" ;;
    A20) echo "gyldig subagent + isolation:worktree" ;;
    A21) echo "gyldig subagent + mode:plan (eneste tillatte ikke-tomme mode)" ;;
    A22) echo "{{PROJECT_NAME}}-reviewer, tom AGENT_ALLOWLIST -> verdi-skann kan aldri treffe" ;;
    A23) echo "ingen subagent_type -> Steg C ubetinget BLOCK uansett 'name'-innhold (var tidligere en drift-eskape via verdi-skann, VIKTIG 1 runde 3)" ;;
    A24) echo "ingen subagent_type -> Steg C ubetinget BLOCK uansett 'description'-innhold (var tidligere en drift-eskape via verdi-skann, VIKTIG 1 runde 3)" ;;
    A25) echo "gyldig subagent + run_in_background:true -> PASS (VIKTIG 3 koordinator-fix: sjekk fjernet, dekket av TaskOutput)" ;;
    A26) echo "gyldig subagent + permission_mode:bypassPermissions (MINDRE 4 koordinator-fix: feltnavnet ekte SDK-en bruker) -> BLOCK" ;;
    A27) echo "skygge-motprove 1 (VIKTIG 1 runde 2): mode:default skygger IKKE lenger for permission_mode:bypassPermissions -> BLOCK" ;;
    A28) echo "skygge-motprove 2 (VIKTIG 1 runde 2): permission_mode:default skygger IKKE lenger for permissionMode:bypassPermissions -> BLOCK" ;;
    A29) echo "skygge-motprove 3 (VIKTIG 1 runde 2): mode:'' (tom streng, truthy i jq) skygger IKKE lenger for permission_mode:bypassPermissions -> BLOCK" ;;
    A30) echo "ingen subagent_type, permission_mode baerer et allowlistet agentnavn -> Steg C ubetinget BLOCK (var tidligere en verdi-skann-escape, VIKTIG 2 runde 2)" ;;
    A31) echo "MINDRE 1 koordinator-fix runde 3: mode-felt er et array (['bypassPermissions']), ikke en streng -> MAA blokkeres (select(type==string) droppet den tidligere STILLE)" ;;
    A32) echo "ingen subagent_type, allowlistet agentnavn under fritt/ukjent feltnavn 'zz' -> Steg C ubetinget BLOCK (verdi-skannen som ga WOULD-ALLOW(value-scan) er fjernet, VIKTIG 3 koordinator-fix runde 5)" ;;
    A33) echo "VIKTIG 4 koordinator-fix runde 5: isolation:false ga tidligere exit=0 (jq '//' faller gjennom pa false OG null) -> na BLOCK, speiler mode-handteringens type-bevarte sjekk" ;;
  esac
}

# ── B: Bash-armen ────────────────────────────────────────────────────────────
get_b_cmd() {
  case "$1" in
    B1) echo 'echo x > fil.txt' ;;
    B2) printf "sed -i '' 's/a/b/' fil.txt" ;;
    B3) echo 'cat a.txt | tee b.txt' ;;
    B4) echo 'git checkout -- lib/x.ts' ;;
    B5) echo 'git apply patch.diff' ;;
    B6) echo 'rm -rf tmpdir' ;;
    B7) printf 'python3 - <<'"'"'PY'"'"'\nopen("f","w")\nPY' ;;
    B8) printf 'git commit -m "x"' ;;
    B9) echo 'git push origin dev' ;;
    B10) printf 'gh pr comment 1 --body "x"' ;;
    B11) echo 'printf x >> fil.txt' ;;
    B12) echo 'gh api repos/o/r/pulls/1 --method PATCH -f title=x' ;;
    B13) printf "awk 'BEGIN{print \"x\" > \"f\"}'" ;;
    B14) printf "echo \$(sed -i '' 's/a/b/' f)" ;;
    B15) printf 'python3 -c "import json"' ;;
    B16) echo 'git diff' ;;
    B17) echo 'gh pr diff 123' ;;
    B18) echo 'git log --oneline -5' ;;
    B19) printf 'grep -rn "foo" tasks/' ;;
    B20) echo 'git rev-parse --show-toplevel' ;;
    B21) printf 'gh pr view 1 --json headRefOid' ;;
    B22) echo 'git fetch origin dev && git merge origin/dev' ;;
    B23) printf "sed -n '1,10p' tasks/plans/x.md" ;;
    B24) echo 'tail -5 fil.md' ;;
    B25) echo 'gh pr diff 1 | head -50' ;;
    B26) echo 'gh pr view 1 2>/dev/null' ;;
    B27) echo 'diff -q v3-agent-orchestrator/setup.md .claude/commands/setup.md' ;;
    B28) echo 'bash .claude/hooks/test-guard-reviewer-readonly.sh' ;;
    B31) printf 'grep -n "^a\\|^b" fil' ;;
    B32) printf "grep -nE '(npm|npx|git)' f" ;;
    B33) printf 'rg "foo\\|bar" lib/' ;;
    B34) printf 'grep -rn "useEffect()" app/' ;;
    B35) printf "git log --grep='fix|feat'" ;;
    B36) printf 'grep -nE "^(name|tools):" .claude/agents/x.md' ;;
    B37) printf 'git log --format="%%H > %%s"' ;;
    B38) echo 'git check-ignore -v tasks/hook-blocks.log' ;;
    B39) echo 'git branch --show-current' ;;
    B40) echo 'git worktree list' ;;
    B41) echo 'sort -o ut.txt inn.txt' ;;
    B42) printf "sed -n 'w ut.txt' f" ;;
    B43) printf 'sed "-i" '"''"' f' ;;
    B44) printf 'find . -name "*.tmp" -delete' ;;
    B45) printf 'find . -fprintf ut.txt "%%p"' ;;
    B46) echo 'git remote add x https://example.invalid/r.git' ;;
    B47) echo 'git remote set-url origin https://example.invalid/r.git' ;;
    B48) echo 'git fetch https://example.invalid/r.git main' ;;
    B49) echo 'git merge FETCH_HEAD' ;;
    B50) echo 'git diff --output=ut.diff' ;;
    B51) echo 'git branch nybranch' ;;
    B52) echo 'git config user.name x' ;;
    B53) echo 'git worktree add /tmp/w dev' ;;
    B54) echo 'git symbolic-ref HEAD refs/heads/x' ;;
    B55) printf 'echo "$(rm -rf x)"' ;;
    B56) echo 'bash ../../.claude/hooks/test-x.sh' ;;
    B57) echo 'bash .claude/hooks/test-x/../../../etc/passwd' ;;
    B58) echo 'bash .claude/hooks/typecheck-on-edit.sh' ;;
    B59) printf "echo 'uterminert" ;;
    B60) echo 'FOO=1 git diff' ;;
    B61) echo 'for f in a b; do cat $f; done' ;;
    B62) echo 'cat f > /dev/null && rm f' ;;
    B63) echo 'gh run download 1' ;;
    B64) echo 'git merge-base origin/dev HEAD' ;;
    B65) printf "git for-each-ref --format='%%(refname)' refs/heads" ;;
    B66) echo 'git config --get remote.origin.url' ;;
    B67) echo 'git symbolic-ref --short HEAD' ;;
    B68) printf ".claude/hooks/guard-reviewer-readonly.sh --whatever" ;;
    B69) printf '/usr/bin/grep -n "x" f' ;;
    B70) printf "sed -n '402p' docs/data-model.md" ;;
    B71) echo 'git status --porcelain v3-agent-orchestrator/ | wc -l' ;;
    B72) echo 'gh api repos/o/r/pulls/1' ;;
    B73) echo 'gh api repos/o/r/pulls/1 --method GET' ;;
    B74) echo 'echo x > fil.txt' ;;
    B75) echo 'echo x > fil.txt' ;;
    B76) echo 'echo x > fil.txt' ;;
    B77) printf "diff <(sed -i '' s/a/b/ f)" ;;
    B78) echo 'cat <(rm -rf x)' ;;
    B79) echo 'git -C /tmp/hovedsjekkut merge origin/dev' ;;
    B80) echo 'git -c core.pager=cat log --oneline -1' ;;
    B81) echo 'git --git-dir=/tmp/x/.git log' ;;
    B82) echo 'git --work-tree=/tmp/x checkout -- f' ;;
    B83) echo 'git --exec-path=/tmp log' ;;
    B84) echo 'git --config-env=core.pager=P log' ;;
    B85) echo 'gh --version pr diff 1' ;;
    B86) echo 'git --no-pager log --oneline -5' ;;
    B87) printf 'find . \\( -name "*.ts" -o -name "*.tsx" \\) -maxdepth 2' ;;
    B88) echo 'env FOO=1 git diff' ;;
    B89) echo 'env' ;;
    B90) printf 'bash "$CLAUDE_PROJECT_DIR"/.claude/hooks/../../etc/x.sh' ;;
    B91) printf 'bash "/etc"/.claude/hooks/guard-x.sh' ;;
    B92) printf 'bash "$CLAUDE_PROJECT_DIR"/.claude/hooks/test-guard-reviewer-readonly.sh' ;;
    B93) printf 'git log --oneline -3 | grep -c "fix"' ;;
    B94) echo 'rg --pre=cat foo' ;;
    B95) echo 'git grep -Ovim foo' ;;
    B96) echo 'gh api repos/o/r/pulls/1 -f title=x' ;;
    B97) echo 'sort --compress-program=gzip f' ;;
    B98) echo 'git fetch origin +refs/heads/dev:refs/heads/main' ;;
    B99) echo 'git fetch origin --prune --force' ;;
  esac
}

get_b_agent() {
  case "$1" in
    B29) echo "{{PROJECT_NAME}}-implementer" ;;
    B30) echo "__NONE__" ;;
    B76) echo "{{PROJECT_NAME}}-planner" ;;
    *) echo "{{PROJECT_NAME}}-code-reviewer" ;;
  esac
}

get_b_mode_env() {
  # LOOP_READONLY_GATE_BASH_MODE override. B74 = ingen override (default
  # observe). B75 = eksplisitt "observe" (monotont: kan ikke løsne).
  # Alle andre = "enforce" så exit-koden forblir fasit selv om
  # produksjons-default er observe (R6/D7).
  case "$1" in
    B74) echo "" ;;
    B75) echo "observe" ;;
    B29|B30|B76) echo "" ;;
    *) echo "enforce" ;;
  esac
}

get_b_expected() {
  case "$1" in
    B1|B2|B3|B4|B5|B6|B7|B8|B9|B10|B11|B12|B13|B14|B15) echo BLOCK ;;
    B16|B17|B18|B19|B20|B21|B22|B23|B24|B25|B26|B27|B28) echo PASS ;;
    B31|B32|B33|B34|B35|B36|B37|B38|B39|B40) echo PASS ;;
    B41|B42|B43|B44|B45|B46|B47|B48|B49|B50) echo BLOCK ;;
    B51|B52|B53|B54|B55|B56|B57|B58|B59|B60|B61|B62|B63) echo BLOCK ;;
    B64|B65|B66|B67) echo PASS ;;
    B69|B70|B71|B72|B73) echo PASS ;;
    B68) echo BLOCK ;;
    B74|B75|B76) echo PASS ;;
    B29|B30) echo PASS ;;
    B77|B78|B79|B80|B81|B82|B83|B84|B85) echo BLOCK ;;
    B86|B87) echo PASS ;;
    B88) echo BLOCK ;;
    B89) echo PASS ;;
    B90|B91) echo BLOCK ;;
    B92|B93) echo PASS ;;
    B94|B95|B96|B97) echo BLOCK ;;
    B98|B99) echo BLOCK ;;
  esac
}

get_b_desc() {
  case "$1" in
    B1) echo "redirect >" ;;
    B2) echo "sed -i" ;;
    B3) echo "tee" ;;
    B4) echo "git checkout --" ;;
    B5) echo "git apply" ;;
    B6) echo "rm -rf" ;;
    B7) echo "python3 heredoc" ;;
    B8) echo "git commit" ;;
    B9) echo "git push origin dev" ;;
    B10) echo "gh pr comment" ;;
    B11) echo "append >>" ;;
    B12) echo "gh api --method PATCH" ;;
    B13) echo "awk redirect" ;;
    B14) echo "kommandosubstitusjon rundt sed -i" ;;
    B15) echo "python3 -c (dokumentert falsk positiv)" ;;
    B16) echo "git diff" ;;
    B17) echo "gh pr diff" ;;
    B18) echo "git log" ;;
    B19) echo "grep -rn" ;;
    B20) echo "git rev-parse --show-toplevel" ;;
    B21) echo "gh pr view --json" ;;
    B22) echo "charterets steg 0 (fetch+merge origin/dev)" ;;
    B23) echo "sed -n linjeomraade" ;;
    B24) echo "tail" ;;
    B25) echo "pipe til head" ;;
    B26) echo "stderr til /dev/null" ;;
    B27) echo "probe-invarianten" ;;
    B28) echo "kjor harnessen selv" ;;
    B31) echo "escapet alternasjon i dobbeltfnutt (BLOKKERENDE 1)" ;;
    B32) echo "parenteser+alternasjon i enkeltfnutt (BLOKKERENDE 1)" ;;
    B33) echo "rg alternasjon (BLOKKERENDE 1)" ;;
    B34) echo "parenteser i literal (BLOKKERENDE 1)" ;;
    B35) echo "git log --grep sitert alternasjon (BLOKKERENDE 1)" ;;
    B36) echo "reviewerens egen grep-kommando (BLOKKERENDE 1)" ;;
    B37) echo "> er literal inne i sitat" ;;
    B38) echo "planens eget D5-bevis (VIKTIG 2)" ;;
    B39) echo "git branch --show-current (VIKTIG 2)" ;;
    B40) echo "git worktree list (VIKTIG 2)" ;;
    B41) echo "sort -o (VIKTIG 1)" ;;
    B42) echo "sed w-kommando uten redirect (VIKTIG 1)" ;;
    B43) echo "sitert flagg i flaggposisjon - uavgjorbar" ;;
    B44) echo "find -delete (find-flagg-allowlist)" ;;
    B45) echo "find -fprintf (VIKTIG 1)" ;;
    B46) echo "git remote add (VIKTIG 1)" ;;
    B47) echo "git remote set-url (VIKTIG 1)" ;;
    B48) echo "git fetch mot fremmed url (VIKTIG 1)" ;;
    B49) echo "git merge FETCH_HEAD (VIKTIG 1)" ;;
    B50) echo "git diff --output (skriver uten redirect)" ;;
    B51) echo "git branch oppretter" ;;
    B52) echo "git config skriver" ;;
    B53) echo "git worktree add" ;;
    B54) echo "git symbolic-ref 2 argumenter" ;;
    B55) echo "kommandosubstitusjon i dobbeltfnutt" ;;
    B56) echo "carve-out tillater ikke traversering (relativ)" ;;
    B57) echo "carve-out tillater ikke traversering (dyp)" ;;
    B58) echo "ikke i carve-out (typecheck-on-edit)" ;;
    B59) echo "uterminert enkeltfnutt" ;;
    B60) echo "variabel-prefiks (dokumentert falsk positiv)" ;;
    B61) echo "kontrollstruktur (dokumentert falsk positiv)" ;;
    B62) echo "andre segment etter &&" ;;
    B63) echo "gh run download skriver filer" ;;
    B64) echo "git merge-base (VIKTIG 2)" ;;
    B65) echo "git for-each-ref (VIKTIG 2)" ;;
    B66) echo "git config --get (VIKTIG 2)" ;;
    B67) echo "git symbolic-ref --short (VIKTIG 2)" ;;
    B68) echo "guard-*.sh fjernet fra carve-out (MINDRE 2 koordinator-fix): frie argumenter mot vokteren selv blokkeres nå" ;;
    B69) echo "basename-normalisering av absolutt sti" ;;
    B70) echo "sed enkelt linjenummer" ;;
    B71) echo "git status --porcelain | wc -l" ;;
    B72) echo "gh api uten --method" ;;
    B73) echo "gh api --method GET eksplisitt" ;;
    B74) echo "observe-modus: exit 0 + WOULD-BLOCK i loggen" ;;
    B75) echo "env=observe mens default=observe: monotont, fortsatt exit 0" ;;
    B76) echo "{{PROJECT_NAME}}-planner er ikke read-only" ;;
    B77) echo "prosess-substitusjon <() (VIKTIG 1 runde 3)" ;;
    B78) echo "prosess-substitusjon <() rundt rm" ;;
    B79) echo "git -C globalt flagg foran merge (VIKTIG 2 runde 3)" ;;
    B80) echo "git -c globalt flagg" ;;
    B81) echo "git --git-dir globalt flagg" ;;
    B82) echo "git --work-tree globalt flagg" ;;
    B83) echo "git --exec-path globalt flagg" ;;
    B84) echo "git --config-env globalt flagg" ;;
    B85) echo "gh --version brukt som prefiks" ;;
    B86) echo "git --no-pager (eneste tillatte globale git-flagg)" ;;
    B87) echo "escapede find-parenteser er ikke separator" ;;
    B88) echo "env med argumenter (variabel-prefiks-omgaaelse)" ;;
    B89) echo "env uten argumenter" ;;
    B90) echo "carve-out: .. etter \$CLAUDE_PROJECT_DIR" ;;
    B91) echo "carve-out: sitert literal er ikke \$CLAUDE_PROJECT_DIR" ;;
    B92) echo "portabel carve-out-form via QUOTES[]-oppslag" ;;
    B93) echo "regresjonsvakt: pipe + git-flaggregel sammen" ;;
    B94) echo "rg --pre kjorer ekstern kommando (VIKTIG 2 runde 3)" ;;
    B95) echo "git grep -O<pager> (VIKTIG 2 runde 3)" ;;
    B96) echo "gh api -f impliserer POST (VIKTIG 2 runde 3)" ;;
    B97) echo "sort --compress-program (VIKTIG 2 runde 3)" ;;
    B98) echo "git fetch origin + skrivende refspec med ':' (MINDRE 1 koordinator-fix runde 5)" ;;
    B99) echo "git fetch origin --prune --force (MINDRE 1 koordinator-fix runde 5)" ;;
    B29) echo "negativ kontroll: ikke read-only rolle" ;;
    B30) echo "negativ kontroll: hovedtraad (R4)" ;;
  esac
}

# ── C: verktoynavn-armen ─────────────────────────────────────────────────────
get_c_payload() {
  local agent="{{PROJECT_NAME}}-code-reviewer"
  case "$1" in
    C17) agent="ios-design-reviewer" ;;
    C18) agent="{{PROJECT_NAME}}-reviewer" ;;
    C19|C20) agent="{{PROJECT_NAME}}-implementer" ;;
    C21|C22|C23|C24|C25|C26|C27|C28|C29|C30|C31|C32|C33|C34) agent="no-tools-agent" ;;
  esac
  local tool=""
  case "$1" in
    C1) tool="Write" ;;
    C2) tool="Edit" ;;
    C3) tool="MultiEdit" ;;
    C4) tool="NotebookEdit" ;;
    C5) tool="mcp__example__execute_sql" ;;
    C6) tool="mcp__claude_ai_Supabase__apply_migration" ;;
    C7) tool="mcp__claude_ai_Supabase__deploy_edge_function" ;;
    C8) tool="mcp__claude_ai_Supabase__list_tables" ;;
    C9) tool="mcp__github__create_or_update_file" ;;
    C10) tool="SlashCommand" ;;
    C11) tool="Skill" ;;
    C12) tool="Read" ;;
    C13) tool="Grep" ;;
    C14) tool="Glob" ;;
    C15) tool="BashOutput" ;;
    C16) tool="TodoWrite" ;;
    C17) tool="WebFetch" ;;
    C18) tool="WebFetch" ;;
    C19) tool="Write" ;;
    C20) tool="Write" ;;
    C21) tool="Read" ;;
    C22) tool="Write" ;;
    C23) tool="NotebookRead" ;;
    C24) tool="KillShell" ;;
    C25) tool="ExitPlanMode" ;;
    C26) tool="TaskOutput" ;;
    C27) tool="AskUserQuestion" ;;
    C28) tool="SendMessage" ;;
    C29) tool="Monitor" ;;
    C30) tool="AgentOutput" ;;
    C31) tool="AgentOutputTool" ;;
    C32) tool="BashOutputTool" ;;
    C33) tool="KillBash" ;;
    C34) tool="SubagentHandback" ;;
  esac
  if [ "$1" = "C20" ]; then
    jq -n --arg tool "$tool" '{tool_name:$tool,tool_input:{}}'
  else
    jq -n --arg agent "$agent" --arg tool "$tool" '{agent_type:$agent,tool_name:$tool,tool_input:{}}'
  fi
}

get_c_expected() {
  case "$1" in
    C1|C2|C3|C4|C5|C6|C7|C8|C9|C10|C11|C18|C22|C28|C29) echo BLOCK ;;
    C12|C13|C14|C15|C16|C17|C19|C20|C21|C23|C24|C25|C26|C27|C30|C31|C32|C33|C34) echo PASS ;;
  esac
}

get_c_desc() {
  case "$1" in
    C1) echo "Write (BLOKKERENDE 2)" ;;
    C2) echo "Edit (belte-og-bukseseler)" ;;
    C3) echo "MultiEdit (BLOKKERENDE 2)" ;;
    C4) echo "NotebookEdit (BLOKKERENDE 2)" ;;
    C5) echo "mcp Supabase execute_sql" ;;
    C6) echo "mcp Supabase apply_migration" ;;
    C7) echo "mcp Supabase deploy_edge_function" ;;
    C8) echo "mcp Supabase list_tables" ;;
    C9) echo "mcp github create_or_update_file" ;;
    C10) echo "SlashCommand" ;;
    C11) echo "Skill" ;;
    C12) echo "Read (SESSION_SAFE)" ;;
    C13) echo "Grep" ;;
    C14) echo "Glob" ;;
    C15) echo "BashOutput (skal IKKE havne i bash-armen)" ;;
    C16) echo "TodoWrite" ;;
    C17) echo "WebFetch, ios-design-reviewer har den i tools:" ;;
    C18) echo "WebFetch, {{PROJECT_NAME}}-reviewer har den IKKE i tools:" ;;
    C19) echo "Write, {{PROJECT_NAME}}-implementer (ikke read-only)" ;;
    C20) echo "Write, hovedtraad (R4)" ;;
    C21) echo "Read, rolle med tomme kontrakt-felt (SESSION_SAFE uansett)" ;;
    C22) echo "Write, samme rolle (fail-closed via WRITE_DENYLIST_EXACT)" ;;
    C23) echo "NotebookRead (SESSION_SAFE: leser .ipynb-celler, ingen skriveparameter) - VIKTIG 2 koordinator-fix" ;;
    C24) echo "KillShell (SESSION_SAFE: avslutter bakgrunnsprosess, skriver ikke fil/repo) - VIKTIG 2 koordinator-fix" ;;
    C25) echo "ExitPlanMode (SESSION_SAFE: sesjons-UI-modusbytte, ingen fil-/repo-effekt) - VIKTIG 2 koordinator-fix" ;;
    C26) echo "TaskOutput (SESSION_SAFE: leser allerede produsert subagent-output) - VIKTIG 2 koordinator-fix" ;;
    C27) echo "AskUserQuestion (SESSION_SAFE: venter paa menneskesvar, ingen mutasjon) - VIKTIG 2 koordinator-fix" ;;
    C28) echo "SendMessage MAA blokkeres - fjernet fra SESSION_SAFE (BLOKKERENDE koordinator-fix: styringskanal inn i spawnet skrivende agent)" ;;
    C29) echo "Monitor MAA blokkeres - fjernet fra SESSION_SAFE (BLOKKERENDE koordinator-fix: baerer et command-felt, hoerer hjemme i bash-armen)" ;;
    C30) echo "AgentOutput (SESSION_SAFE: kjorende runtime-alias for TaskOutput) - MINDRE 3 koordinator-fix runde 5" ;;
    C31) echo "AgentOutputTool (SESSION_SAFE: kjorende runtime-alias for TaskOutput) - MINDRE 3 koordinator-fix runde 5" ;;
    C32) echo "BashOutputTool (SESSION_SAFE: kjorende runtime-alias for BashOutput) - MINDRE 3 koordinator-fix runde 5" ;;
    C33) echo "KillBash (SESSION_SAFE: kjorende runtime-alias for KillShell) - MINDRE 3 koordinator-fix runde 5" ;;
    C34) echo "SubagentHandback (SESSION_SAFE: leverer sluttrapport til forelderen, runtime 2.1.280)" ;;
  esac
}

# ── X: robusthet ─────────────────────────────────────────────────────────────
get_x_expected() {
  case "$1" in
    X1|X2|X3|X4|X5) echo PASS ;;
    X6) echo BLOCK ;;
    X7) echo BLOCK ;;
    X8) echo PASS ;;
    X9) echo PASS ;;
    X10) echo PASS ;;
    X11) echo BLOCK ;;
  esac
}

get_x_desc() {
  case "$1" in
    X1) echo "tom stdin -> exit 0 + PARSE-FAIL" ;;
    X2) echo "ugyldig JSON -> exit 0 + PARSE-FAIL" ;;
    X3) echo "agent_type JSON-null -> exit 0 (hovedtraad-sti)" ;;
    X4) echo "tool_name mangler -> exit 0 (ingen arm kan velges)" ;;
    X5) echo "200 kB kommando -> BLOCK paa storrelsesvakt (MINDRE 2 koordinator-fix runde 5: tidsassersjonen fjernet - den beviste ingen differanse, kun exit-koden. MAXLEN bevisst IKKE hevet denne runden, se kommentar ved \$MAXLEN i hooken)" ;;
    X6) echo "MINDRE 2 koordinator-fix runde 3: MODE_JQ_PATHS injisert odelagt (simulerer feltnavn med spesialtegn) -> selvtesten MAA blokkere skygge-payloaden i stedet for a feile stille" ;;
    X7) echo "VIKTIG 2 koordinator-fix runde 5: tool_name med etterfolgende \\n forskjov tidligere agent_type til tom streng i den gamle ETT-jq-kall-parsingen -> na BLOCK (hvert felt fanges i egen kommandosubstitusjon)" ;;
    X8) echo "VIKTIG 5 koordinator-fix runde 5: 1 MB isolation-verdi -> fortsatt BLOCK, og begge logglinjene (hook-blocks.log og hook-readonly-gate.log) forblir under 1 kB" ;;
    X9) echo "MINDRE 4 koordinator-fix runde 6: agent_type='../../evil/evil' -> fortsatt exit=0 (samme utfall som i dag), men na via en eksplisitt PARSE-FAIL-sanering FOR CHARTER bygges, ikke bare 'fil finnes ikke'" ;;
    X10) echo "MINDRE 1 koordinator-fix runde 6: 300 x U+00E6 i en angriper-styrt reason-verdi -> sanitize_logval sin avkorting produserer fortsatt GYLDIG UTF-8 (LC_ALL=C.UTF-8 satt eksplisitt, tegnbasert ikke bytebasert avkorting)" ;;
    X11) echo "VIKTIG koordinator-fix runde 6 fortsettelse (Linux CI-funn, run 33492149355): regresjonsvakt for ARGV-lengdeklassen i list_contains() (arm 3) - 1.5 MB tool_name (bekreftet feiler exec/E2BIG selv pa macOS' totale ARG_MAX, ikke bare Linux' MAX_ARG_STRLEN) -> fortsatt BLOCK na som list_contains() er ren bash uten grep" ;;
  esac
}

run_x() {
  local id="$1" from
  from=$(( $(gate_log_lines) + 1 ))
  case "$id" in
    X1)
      code="$(printf '' | CLAUDE_PROJECT_DIR="$FIXDIR" bash "$HOOK" >/dev/null 2>/dev/null; echo $?)"
      [ "$code" = "0" ] && gate_log_new_contains "$from" "PARSE-FAIL" && { echo PASS; return; }
      echo "ERROR($code, ingen PARSE-FAIL)"
      ;;
    X2)
      code="$(printf 'dette er ikke json' | CLAUDE_PROJECT_DIR="$FIXDIR" bash "$HOOK" >/dev/null 2>/dev/null; echo $?)"
      [ "$code" = "0" ] && gate_log_new_contains "$from" "PARSE-FAIL" && { echo PASS; return; }
      echo "ERROR($code, ingen PARSE-FAIL)"
      ;;
    X3)
      local payload; payload="$(jq -n '{agent_type:null,tool_name:"Write",tool_input:{}}')"
      code="$(run_hook "$payload")"
      exitcode_to_dom "$code"
      ;;
    X4)
      local payload; payload="$(jq -n '{agent_type:"{{PROJECT_NAME}}-code-reviewer",tool_input:{}}')"
      code="$(run_hook "$payload")"
      exitcode_to_dom "$code"
      ;;
    X5)
      # MINDRE 2 (koordinator-fix runde 5): tidligere asserterte X5 BÅDE
      # exit=2 OG "< 250ms", men målte aldri en DIFFERANSE mot noe — 250ms
      # er godt over den faktiske kjøretiden (89-135ms observert av
      # koordinatoren), så assertionen beviste ingenting om en
      # ytelsesgate, kun at exit-koden var riktig. Fjernet den uærlige
      # tidsklaimen; testen sjekker nå kun det den faktisk kan bevise
      # (BLOCK-utfallet på en 200 kB kommando).
      #
      # VIKTIG (koordinator-fix runde 6 fortsettelse — Linux CI-funn, run
      # 33492149355): payloaden ble tidligere bygget med
      # `jq -n --arg cmd "$bigcmd" ...` — $bigcmd (~200 kB) ble sendt som
      # ARGV-ELEMENT til jq. Linux' MAX_ARG_STRLEN (128 KiB per argv-
      # element) er LAVERE enn 200 kB; macOS har ingen slik per-argument-
      # grense (kun en total ARG_MAX på 1 MiB), så dette var USYNLIG lokalt
      # (bekreftet: samme kall med 200 kB OG 1 MB lykkes uten feil på denne
      # maskinen) og feilet KUN på Linux CI — jq feilet å starte (E2BIG),
      # $payload ble tom streng, og hookens tom-stdin-PARSE-FAIL-vei ga
      # `exit=0` i stedet for `2`. $bigcmd sendes nå til jq via STDIN
      # (`-Rs`, rått input, slurpet som én streng) i stedet for som
      # argv-element — ingen OS-argv-grense gjelder for stdin.
      local bigcmd payload code
      bigcmd="git diff $(jq -nr '"x" * 200000')"
      payload="$(printf '%s' "$bigcmd" | jq -Rs '{agent_type:"{{PROJECT_NAME}}-code-reviewer",tool_name:"Bash",tool_input:{command: .}}')"
      code="$(run_hook "$payload" LOOP_READONLY_GATE_BASH_MODE=enforce)"
      if [ "$code" = "2" ]; then echo PASS; else echo "ERROR(exit=$code)"; fi
      ;;
    X6)
      # MINDRE 2 (koordinator-fix runde 3): kan ikke injisere et ekte
      # feltnavn med spesialtegn i MODE_FIELD_NAMES (den er hardkodet i
      # hooken), så vi simulerer utfallet direkte: injiser en ØDELAGT
      # MODE_JQ_PATHS-verdi RETT FØR selvtesten som skal fange akkurat dette,
      # i en patchet KOPI av hooken (den ekte .claude/hooks/-fila røres
      # aldri). Payloaden er ellers en helt gyldig, allowlistet
      # subagent-dispatch — uten selvtesten ville denne blitt ALLOW.
      local anchor_line patched_hook payload code
      anchor_line="$(/usr/bin/grep -n 'jq -n "\[\$MODE_JQ_PATHS\]"' "$HOOK" | head -1 | cut -d: -f1)"
      if [ -z "$anchor_line" ]; then
        echo "ERROR(fant ikke MODE_JQ_PATHS-selvtest-ankeret i hooken)"
        return
      fi
      patched_hook="$FIXDIR/x6-patched-hook.sh"
      {
        head -n "$((anchor_line - 1))" "$HOOK"
        printf '  MODE_JQ_PATHS='\''.["bad"x"]'\''\n'
        tail -n "+$anchor_line" "$HOOK"
      } > "$patched_hook"
      payload="$(jq -n '{agent_type:"{{PROJECT_NAME}}-code-reviewer",tool_name:"Agent",tool_input:{subagent_type:"rls-migration-reviewer"}}')"
      code="$(printf '%s' "$payload" | CLAUDE_PROJECT_DIR="$FIXDIR" bash "$patched_hook" >/dev/null 2>/dev/null; echo $?)"
      rm -f "$patched_hook"
      exitcode_to_dom "$code"
      ;;
    X7)
      # VIKTIG 2 (koordinator-fix runde 5) — reviewerens bekreftede motprøve:
      # på DEN GAMLE koden (ett jq-kall, lest posisjonelt linje for linje)
      # forskjøv \n i tool_name samtlige felt ETTER den, agent_type ble lest
      # som tom streng, og hele gaten falt av (exit=0) selv med et
      # Write-lignende tool_input. Fem uavhengige jq-kall (ett per felt) kan
      # ikke lenger krysskontaminere hverandre.
      local payload code
      payload="$(jq -n '{tool_name:"Write\n",agent_type:"{{PROJECT_NAME}}-code-reviewer",cwd:"/tmp/pr477",session_id:"P10",tool_input:{file_path:"/tmp/x",content:"y"}}')"
      code="$(run_hook "$payload")"
      exitcode_to_dom "$code"
      ;;
    X8)
      # VIKTIG 5 (koordinator-fix runde 5): en ubegrenset isolation-verdi
      # (målt av koordinatoren: 1 000 000 × 'A') ga tidligere en logglinje
      # på over 1 MB i tasks/hook-blocks.log. sanitize_logval() avkorter nå
      # ALLE verdier den normaliserer, i BEGGE logger. Isolation-sjekken
      # (Steg A) kjører FØR Steg B, så et gyldig subagent_type i samme
      # payload endrer ikke utfallet — isolation blokkerer uansett.
      #
      # VIKTIG (koordinator-fix runde 6 fortsettelse — Linux CI-funn, run
      # 33492149355): samme argv-klasse som X5 (se kommentaren der).
      # `jq -n --arg a "$biga" ...` sendte 1 000 000 tegn som ETT
      # argv-element til jq — over Linux' MAX_ARG_STRLEN (128 KiB), men
      # UNDER macOS' totale ARG_MAX på en måte som gjorde feilen usynlig
      # lokalt (bekreftet ved direkte test på denne maskinen: lykkes uten
      # feil). $biga sendes nå via STDIN (`-Rs`) i stedet. Koordinatorens
      # opprinnelige mistanke var `list_contains`s `grep -qxF "$needle"`
      # (samme argv-klasse) — VERIFISERT at isolation-sjekken (Steg A)
      # aldri når `list_contains` i det hele tatt (den blokkerer FØR Steg B,
      # der eneste `list_contains`-kallet med et angriper-styrt `$needle`
      # ligger) — men `list_contains` er likevel gjort argv-fri i hooken
      # (se `list_contains()`-kommentaren), siden ALLE dagens kallsteder med
      # et ubegrenset `$needle` er trygge kun ved en tilfeldighet
      # («ikke funnet» ⇒ BLOCK i alle dagens grener), ikke ved konstruksjon.
      local biga payload code from maxlen_gate maxlen_blocks
      biga="$(jq -nr '"A" * 1000000')"
      payload="$(printf '%s' "$biga" | jq -Rs '{agent_type:"{{PROJECT_NAME}}-code-reviewer",tool_name:"Agent",tool_input:{subagent_type:"rls-migration-reviewer",isolation: .}}')"
      from=$(( $(gate_log_lines) + 1 ))
      code="$(run_hook "$payload")"
      if [ "$code" != "2" ]; then echo "ERROR(exit=$code, forventet 2)"; return; fi
      maxlen_gate="$(tail -n +"$from" "$GATE_LOG" 2>/dev/null | awk '{ print length }' | sort -rn | head -1)"
      maxlen_blocks="$(tail -n 5 "$LOG_BLOCKS" 2>/dev/null | awk '{ print length }' | sort -rn | head -1)"
      [ -z "$maxlen_gate" ] && maxlen_gate=0
      [ -z "$maxlen_blocks" ] && maxlen_blocks=0
      if [ "$maxlen_gate" -lt 1024 ] && [ "$maxlen_blocks" -lt 1024 ]; then
        echo PASS
      else
        echo "ERROR(gate-linjelengde=$maxlen_gate, blocks-linjelengde=$maxlen_blocks)"
      fi
      ;;
    X9)
      # MINDRE 4 (koordinator-fix runde 6): $AGENT_TYPE interpoleres usanitert
      # inn i CHARTER-filstien. Målt av koordinatoren: '../../evil/evil',
      # 'p1/../p2' og 'p1 ' ga alle exit=0 via charter-ikke-funnet-stien i
      # dag (ikke utnyttbart, men uten en eksplisitt sanering). Etter fiksen
      # er utfallet FORTSATT exit=0 (ingen BLOCK→PASS/PASS→BLOCK-regresjon),
      # men nå via en eksplisitt PARSE-FAIL-avvisning FØR CHARTER settes —
      # verifiser at den faktisk logges (skiller fra den gamle stille stien).
      local payload code from
      from=$(( $(gate_log_lines) + 1 ))
      payload="$(jq -n '{agent_type:"../../evil/evil",tool_name:"Write",tool_input:{}}')"
      code="$(run_hook "$payload")"
      if [ "$code" != "0" ]; then echo "ERROR(exit=$code, forventet 0)"; return; fi
      if gate_log_new_contains "$from" "PARSE-FAIL"; then
        echo PASS
      else
        echo "ERROR(ingen PARSE-FAIL logget for ugyldig agent_type)"
      fi
      ;;
    X10)
      # MINDRE 1 (koordinator-fix runde 6): LC_ALL=C.UTF-8 er satt eksplisitt
      # FØR PATH-eksporten i hooken. En 300-tegns U+00E6-payload i et
      # tool_input-felt logges (sanitisert/avkortet) til GATE_LOG via en
      # SESSION_SAFE-ALLOW-vei (Read) — resultatet skal fortsatt være gyldig
      # UTF-8 etter avkorting, ikke brutt midt i en multibyte-sekvens.
      local ae payload code from line
      ae="$(jq -nr '"æ" * 300')"
      payload="$(jq -n --arg a "$ae" '{agent_type:"{{PROJECT_NAME}}-code-reviewer",tool_name:"Read",tool_input:{note:$a}}')"
      from=$(( $(gate_log_lines) + 1 ))
      code="$(run_hook "$payload")"
      if [ "$code" != "0" ]; then echo "ERROR(exit=$code, forventet 0 - Read er SESSION_SAFE)"; return; fi
      line="$(tail -n +"$from" "$GATE_LOG" 2>/dev/null)"
      if [ -z "$line" ]; then echo "ERROR(ingen ny logglinje funnet)"; return; fi
      if printf '%s' "$line" | iconv -f UTF-8 -t UTF-8 >/dev/null 2>/dev/null; then
        echo PASS
      else
        echo "ERROR(logglinjen er ugyldig UTF-8 etter avkorting)"
      fi
      ;;
    X11)
      # VIKTIG (koordinator-fix runde 6 fortsettelse — Linux CI-funn, run
      # 33492149355): regresjonsvakt for ARGV-lengdeklassen i
      # list_contains() (arm 3), UAVHENGIG av Linux/macOS-forskjellen i
      # MAX_ARG_STRLEN. 1.5 MB er BEKREFTET å feile exec (E2BIG, exit=126)
      # for en grep-basert argv-kommando selv på denne macOS-maskinens
      # TOTALE ARG_MAX. Denne caseen blir dermed rød
      # på BEGGE plattformer, ikke bare i Linux CI, hvis list_contains()
      # noensinne reintroduserer en grep-basert (argv-vei) implementasjon.
      # Payloaden bygges selv via STDIN (`jq -Rs`), ikke `--arg` (samme
      # klasse feil ville rammet TESTEN selv, se X5/X8-kommentarene).
      local hugetool payload code
      hugetool="$(jq -nr '"T" * 1500000')"
      payload="$(printf '%s' "$hugetool" | jq -Rs '{agent_type:"{{PROJECT_NAME}}-code-reviewer",tool_name: ., tool_input:{}}')"
      code="$(run_hook "$payload")"
      exitcode_to_dom "$code"
      ;;
  esac
}

# ── D: drift-assertions mot ekte charterfiler ───────────────────────────────

# discover_real_agents — bare charternavn (uten .md) i DFIXDIR (kopi av
# .claude/agents/, laget over). Brukt av D1/D3 (VIKTIG 2, koordinator-fix
# runde 6) til å ITERERE over de EKTE charterfilene i stedet for å
# hardkode rollelisten — et NYTT charter i .claude/agents/ blir dermed
# automatisk med i begge assertions uten en harness-endring.
discover_real_agents() {
  (cd "$DFIXDIR/.claude/agents" && ls -- *.md 2>/dev/null) | sed -E 's/\.md$//'
}

get_d_desc() {
  case "$1" in
    D1) echo "datadrevet (uendret siden runde 6, na drevet av den EKTE kontraktfila): settet av EKTE charter som IKKE er read-only er noyaktig {{{PROJECT_NAME}}-implementer, {{PROJECT_NAME}}-planner} - probet ved a sporre HOOKEN SELV (tool_name=Write)" ;;
    D2) echo "NY datadrevet: code-reviewer sin effektive Agent-allowlist leses fra den EKTE kontraktfila (samme uttrekk som D4) i stedet for en hardkodet tre-navns-liste - checked=0 (tom, mangler, eller '-') gir ERROR, samme prinsipp som D5" ;;
    D3) echo "datadrevet (uendret siden runde 6): for HVERT ekte charter Write-proben klassifiserer read-only via kontrakten, blokkeres OGSA hele WRITE_DENYLIST_EXACT (MultiEdit/NotebookEdit/SlashCommand/Skill/mcp__*)" ;;
    D4) echo "NY runde 7 (konfig-drift): code-reviewerens Agent-liste i den EKTE kontraktfila stemmer eksakt med tech_review_agents-navnene i v3-agent-orchestrator/loop.config.yaml" ;;
    D5) echo "NY runde 8 (VIKTIG 4): for HVER rolle i den EKTE kontraktfila har .claude/agents/<rolle>.md en disallowedTools:-linje som lister minst Write og Edit - ren fil-mot-fil-assersjon, ikke en hook-probe" ;;
  esac
}

run_d() {
  case "$1" in
    D1)
      # Datadrevet (VIKTIG 2, koordinator-fix runde 6): probe HVERT ekte
      # charter med tool_name=Write. Write er ALLTID i WRITE_DENYLIST_EXACT
      # (BLOKKERENDE 2), så exit=2 <=> rollen ER read-only, exit=0 <=> den
      # er IKKE read-only. Asserer deretter at IKKE-read-only-settet er
      # NØYAKTIG {{{PROJECT_NAME}}-implementer, {{PROJECT_NAME}}-planner} — verken mer
      # (et charter som skulle vært read-only, men ikke er det) eller mindre
      # (implementer/planner ved et uhell blitt lenket ned).
      local name payload code ok=1 non_readonly="" nonreadonly_sorted expected_sorted
      for name in $(discover_real_agents); do
        payload="$(jq -n --arg a "$name" '{agent_type:$a,tool_name:"Write",tool_input:{}}')"
        code="$(run_hook_dfix "$payload")"
        case "$code" in
          0) non_readonly="$non_readonly $name" ;;
          2) : ;;
          *) ok=0; echo "   (D1: $name ga uventet exit=$code for Write-probe)" >&2 ;;
        esac
      done
      nonreadonly_sorted="$(printf '%s\n' $non_readonly | grep -v '^$' | sort | tr '\n' ' ')"
      expected_sorted="$(printf '%s\n' {{PROJECT_NAME}}-implementer {{PROJECT_NAME}}-planner | sort | tr '\n' ' ')"
      if [ "$nonreadonly_sorted" != "$expected_sorted" ]; then
        ok=0
        echo "   (D1: ikke-read-only-sett = '$nonreadonly_sorted', forventet '$expected_sorted')" >&2
      fi
      [ "$ok" = "1" ] && echo PASS || echo "ERROR"
      ;;
    D2)
      # Datadrevet (koordinator-fix): code-reviewerens
      # effektive Agent-allowlist leses fra den EKTE kontraktfila (samme
      # awk-uttrekk som D4 bruker) i stedet for en hardkodet tre-navns-liste
      # — et nytt tech-review-navn i kontrakten (f.eks. race-reviewer) blir
      # dermed automatisk med i probingen, uten en harness-endring.
      # Uttrekket MÅ speile hookens EGEN semantikk
      # (guard-reviewer-readonly.sh:460): feltverdien "-" betyr TOM
      # allowlist, IKKE ett navn med verdien "-" — en naiv `tr ',' '\n'`
      # ville gitt nettopp det og prøvd hooken med subagent_type:"-", som
      # blir rød av feil grunn (plan-review runde 2, VIKTIG 2).
      # checked=0 ⇒ ERROR, ordrett samme prinsipp som D5 (MINDRE 2/runde 9)
      # — en tom allowlist skal IKKE tolkes som et vakuøst grønt PASS.
      local contract_agents names name ok=1 payload code checked=0
      contract_agents="$(awk -F'\t' '$1=="{{PROJECT_NAME}}-code-reviewer"{print $2}' "$REPO_ROOT/.claude/hooks/reviewer-readonly.contract" 2>/dev/null)"
      if [ -z "$contract_agents" ] || [ "$contract_agents" = "-" ]; then
        names=""
      else
        names="$(printf '%s' "$contract_agents" | tr ',' ' ')"
      fi
      for name in $names; do
        checked=$((checked + 1))
        payload="$(jq -n --arg n "$name" '{agent_type:"{{PROJECT_NAME}}-code-reviewer",tool_name:"Agent",tool_input:{subagent_type:$n}}')"
        code="$(run_hook_dfix "$payload")"
        [ "$code" = "0" ] || { ok=0; echo "   (D2: $name ga exit=$code, forventet 0)" >&2; }
      done
      if [ "$checked" -eq 0 ] && [ "$contract_agents" != "-" ]; then
        ok=0
        echo "   (D2: checked=0 - Agent-allowlisten er tom eller mangler, ingenting ble faktisk assertert)" >&2
      fi
      # '-' er lovlig: prosjektet har ingen tech-review-agenter (tech_review_agents: []).
      # Da gjenstår kun ikke-medlem-proben under, som fortsatt skal blokkere.
      payload="$(jq -n '{agent_type:"{{PROJECT_NAME}}-code-reviewer",tool_name:"Agent",tool_input:{subagent_type:"ikke-medlem"}}')"
      code="$(run_hook_dfix "$payload")"
      [ "$code" = "2" ] || { ok=0; echo "   (D2: ikke-medlem ga exit=$code, forventet 2)" >&2; }
      [ "$ok" = "1" ] && echo PASS || echo "ERROR"
      ;;
    D3)
      # Datadrevet (VIKTIG 2, koordinator-fix runde 6): for HVERT ekte
      # charter som D1s Write-probe klassifiserer read-only (exit=2),
      # verifiser at HELE WRITE_DENYLIST_EXACT (BLOKKERENDE 2) også
      # blokkeres — ikke bare Write/Edit. Erstatter den tidligere
      # hardkodede rollelisten (samme M1-mønster: les av EKTE data i
      # stedet for en liste som kan gå ut av synk).
      local name payload code ok=1
      for name in $(discover_real_agents); do
        payload="$(jq -n --arg a "$name" '{agent_type:$a,tool_name:"Write",tool_input:{}}')"
        code="$(run_hook_dfix "$payload")"
        [ "$code" = "2" ] || continue
        for tool in MultiEdit NotebookEdit SlashCommand Skill Monitor SendMessage mcp__example__execute_sql; do
          payload="$(jq -n --arg a "$name" --arg t "$tool" '{agent_type:$a,tool_name:$t,tool_input:{}}')"
          code="$(run_hook_dfix "$payload")"
          [ "$code" = "2" ] || { ok=0; echo "   (D3: $name/$tool ga exit=$code, forventet 2)" >&2; }
        done
      done
      [ "$ok" = "1" ] && echo PASS || echo "ERROR"
      ;;
    D4)
      # NY — konfig-drift, leser filene direkte
      # (ingen hook-probing nødvendig): code-reviewerens Agent-felt i den
      # EKTE kontraktfila skal stemme eksakt (som mengde) med navnene under
      # tech_review_agents: i v3-agent-orchestrator/loop.config.yaml. Et nytt
      # tech-review-navn lagt til i config, men glemt i kontrakten (eller
      # omvendt), gjør denne caseen rød.
      local contract_agents config_names contract_sorted config_sorted
      contract_agents="$(awk -F'\t' '$1=="{{PROJECT_NAME}}-code-reviewer"{print $2}' "$REPO_ROOT/.claude/hooks/reviewer-readonly.contract" 2>/dev/null)"
      if [ -z "$contract_agents" ]; then echo "ERROR(fant ikke {{PROJECT_NAME}}-code-reviewer-linje i ekte kontraktfil)"; return; fi
      contract_sorted="$(printf '%s' "$contract_agents" | tr ',' '\n' | sort | tr '\n' ' ')"
      # '-' = tom allowlist (tech_review_agents: []). Samme transform som config-sida under gir da
      # nøyaktig det en tom navneliste gir der, så tom-mot-tom sammenlignes likt.
      [ "$contract_agents" = "-" ] && contract_sorted="$(printf '%s\n' | sort | tr '\n' ' ')"
      config_names="$(awk '/^tech_review_agents:/{flag=1; next} /^[A-Za-z_]+:/{flag=0} flag' "$REPO_ROOT/v3-agent-orchestrator/loop.config.yaml" | grep -E '^[[:space:]]*-[[:space:]]*name:' | sed -E 's/^[[:space:]]*-[[:space:]]*name:[[:space:]]*//')"
      config_sorted="$(printf '%s\n' $config_names | sort | tr '\n' ' ')"
      if [ "$contract_sorted" = "$config_sorted" ]; then
        echo PASS
      else
        echo "ERROR(kontrakt='$contract_sorted', config='$config_sorted')"
      fi
      ;;
    D5)
      # NY (VIKTIG 4, koordinator-fix runde 8) — `disallowedTools` er nå det
      # ENESTE runtime-håndhevede filteret igjen: hooken slettet
      # ALL tools:/disallowedTools:-tolkning i runde 7 (se toppkommentaren),
      # så INGENTING i hookens beslutningssti lenger leser charterfilene.
      # Uten denne caseen kan `disallowedTools: Write, Edit` fjernes fra et
      # charter uten at noe blir rødt — revieweren målte nettopp det
      # (199/199 OK etter fjerning). Dette er en REN FIL-MOT-FIL-assersjon:
      # for HVER rollelinje i den EKTE kontraktfila skal
      # .claude/agents/<rolle>.md finnes OG ha en disallowedTools:-linje som
      # lister minst Write OG Edit (rekkefølge/andre medlemmer er likegyldig).
      # IKKE en hook-probe — hooken skal ikke gjeninnføre charter-parsing.
      # MINDRE 2 (koordinator-fix runde 9): `ok` startet på 1 og løkka under
      # gir null iterasjoner hvis kontraktfila er tom/mangler — caseen printet
      # da PASS uten å ha assertert NOE (vakuøst grønt). `checked` teller
      # faktisk behandlede rollelinjer; 0 behandlede -> ERROR med forklarende
      # stderr-linje, i stedet for et grønt resultat som ikke beviser noe.
      local role ok=1 file line checked=0
      for role in $(awk -F'\t' '{print $1}' "$REPO_ROOT/.claude/hooks/reviewer-readonly.contract" 2>/dev/null); do
        [ -n "$role" ] || continue
        checked=$((checked + 1))
        file="$REPO_ROOT/.claude/agents/$role.md"
        if [ ! -f "$file" ]; then
          ok=0
          echo "   (D5: $role - charterfil $file finnes ikke)" >&2
          continue
        fi
        line="$(/usr/bin/grep -m1 -E '^disallowedTools:' "$file" 2>/dev/null)"
        if [ -z "$line" ]; then
          ok=0
          echo "   (D5: $role - ingen disallowedTools:-linje i $file)" >&2
          continue
        fi
        if ! printf '%s' "$line" | /usr/bin/grep -qE '(^|[^A-Za-z])Write([^A-Za-z]|$)'; then
          ok=0
          echo "   (D5: $role - disallowedTools mangler Write: '$line')" >&2
        fi
        if ! printf '%s' "$line" | /usr/bin/grep -qE '(^|[^A-Za-z])Edit([^A-Za-z]|$)'; then
          ok=0
          echo "   (D5: $role - disallowedTools mangler Edit: '$line')" >&2
        fi
      done
      if [ "$checked" -eq 0 ]; then
        ok=0
        echo "   (D5: 0 rollelinjer behandlet - kontraktfila er tom, mangler eller uleselig, ingenting ble faktisk assertert)" >&2
      fi
      [ "$ok" = "1" ] && echo PASS || echo "ERROR"
      ;;
  esac
}

# ── K: kontrakt-mekanikk — beviser egenskapene
# den nye kontraktfila MÅ ha, uavhengig av de fem ekte rollenavnene (bruker
# egne syntetiske roller i FIXDIRs kontrakt, se fixture-oppsettet over):
#   K1–K2   kontraktfil mangler helt -> BLOCK for subagent, PASS for hovedtråd
#   K3      kontraktfil er 0 byte (tom)
#   K4      kontraktfil er ren søppeltekst (ingen TAB-felt i det hele tatt)
#   K5      kontraktfil har én linje som mangler et felt -> HELE fila
#           uparsbar, selv om resten av linjene er velformede (ingen
#           delvis-parsing)
#   K6      et rollenavn med en '#' i seg -> feiler charset-valideringen som
#           enhver annen søppel-verdi. Beviser BLOKKERENDE 1/2 fra runde 5/6
#           (kommentar-parsing) er strukturelt UMULIG nå: formatet har ingen
#           kommentarsyntaks å parse feil i utgangspunktet.
#   K7      PARSE-FAIL faktisk logget når kontraktfila mangler (ikke bare at
#           exit-koden tilfeldigvis stemmer)
#   K8      rolle med agent-felt "-" -> ALL Agent-dispatch BLOCK
#   K9–K10  rolle med agent-felt "allowed-x,allowed-y" -> kun de to PASS,
#           alt annet BLOCK
#   K11–K13 kontraktfil som (feilaktig/ondsinnet) prøver å grante
#           Write/MultiEdit/mcp__* via ekstra-verktøy-feltet -> denylisten
#           vinner uansett, fortsatt BLOCK
#   K14–K15 {{PROJECT_NAME}}-planner/{{PROJECT_NAME}}-implementer (ikke i kontrakten,
#           som i dag) er fortsatt IKKE read-only via den EKTE kontrakten
#   K16–K17 NYE i koordinator-fix runde 8 (VIKTIG 1), symmetrisk med K11–K13:
#           kontraktfila prøver å grante Monitor/SendMessage via
#           ekstra-verktøy-feltet -> WRITE_DENYLIST_EXACT vinner uansett,
#           fortsatt BLOCK (regresjonsbevis for funnet: FØR denne fiksen ga
#           begge exit=0)
get_k_expected() {
  case "$1" in
    K1|K3|K4|K5|K6|K8|K10|K11|K12|K13|K16|K17|K18|K19) echo BLOCK ;;
    K2|K7|K9|K14|K15) echo PASS ;;
  esac
}

get_k_desc() {
  case "$1" in
    K1) echo "kontraktfil mangler -> subagent -> BLOCK" ;;
    K2) echo "kontraktfil mangler -> hovedtraad -> PASS (R4 uendret)" ;;
    K3) echo "kontraktfil er 0 byte -> BLOCK" ;;
    K4) echo "kontraktfil er ren soppeltekst uten TAB-felt -> BLOCK" ;;
    K5) echo "en linje mangler et felt -> HELE fila uparsbar, ingen delvis-parsing" ;;
    K6) echo "en ANNEN linje i kontrakten har '#' i rollenavnet -> hele fila uparsbar for ALLE roller (ingen kommentarsyntaks finnes a feile i)" ;;
    K7) echo "PARSE-FAIL faktisk logget nar kontraktfila mangler" ;;
    K8) echo "readonly-no-agents: agent-felt '-' -> ALL Agent-dispatch BLOCK" ;;
    K9) echo "readonly-with-agents: allowed-x -> PASS" ;;
    K10) echo "readonly-with-agents: ikke-medlem -> BLOCK" ;;
    K11) echo "greedy-role: kontrakten prover a grante Write -> denylisten vinner, BLOCK" ;;
    K12) echo "greedy-role: kontrakten prover a grante MultiEdit -> denylisten vinner, BLOCK" ;;
    K13) echo "greedy-role: kontrakten prover a grante mcp__x__apply_migration -> denylisten vinner, BLOCK" ;;
    K14) echo "{{PROJECT_NAME}}-planner (ikke i EKTE kontrakt) -> Write -> PASS" ;;
    K15) echo "{{PROJECT_NAME}}-implementer (ikke i EKTE kontrakt) -> Agent-dispatch -> PASS" ;;
    K16) echo "greedy-role: kontrakten prover a grante Monitor -> denylisten vinner, BLOCK (VIKTIG 1 runde 8)" ;;
    K17) echo "greedy-role: kontrakten prover a grante SendMessage -> denylisten vinner, BLOCK (VIKTIG 1 runde 8)" ;;
    K18) echo "{{READONLY_PROBE_ROLE}} (read-only rolle i EKTE kontrakt) -> Write -> BLOCK (BLOKKERENDE fix-runde: scout inn i read-only-handhevingen)" ;;
    K19) echo "{{READONLY_PROBE_ROLE}} (read-only rolle i EKTE kontrakt) -> Bash-skriving (echo x > f), enforce-modus -> BLOCK" ;;
  esac
}

run_k() {
  case "$1" in
    K1)
      local payload code
      payload="$(jq -n '{agent_type:"{{PROJECT_NAME}}-code-reviewer",tool_name:"Write",tool_input:{}}')"
      code="$(printf '%s' "$payload" | CLAUDE_PROJECT_DIR="$NOFIXDIR" bash "$HOOK" >/dev/null 2>/dev/null; echo $?)"
      exitcode_to_dom "$code"
      ;;
    K2)
      local payload code
      payload="$(jq -n '{tool_name:"Write",tool_input:{}}')"
      code="$(printf '%s' "$payload" | CLAUDE_PROJECT_DIR="$NOFIXDIR" bash "$HOOK" >/dev/null 2>/dev/null; echo $?)"
      exitcode_to_dom "$code"
      ;;
    K3)
      local payload code
      payload="$(jq -n '{agent_type:"{{PROJECT_NAME}}-code-reviewer",tool_name:"Write",tool_input:{}}')"
      code="$(printf '%s' "$payload" | CLAUDE_PROJECT_DIR="$EMPTYFIXDIR" bash "$HOOK" >/dev/null 2>/dev/null; echo $?)"
      exitcode_to_dom "$code"
      ;;
    K4)
      local payload code
      payload="$(jq -n '{agent_type:"{{PROJECT_NAME}}-code-reviewer",tool_name:"Write",tool_input:{}}')"
      code="$(printf '%s' "$payload" | CLAUDE_PROJECT_DIR="$GARBAGEFIXDIR" bash "$HOOK" >/dev/null 2>/dev/null; echo $?)"
      exitcode_to_dom "$code"
      ;;
    K5)
      local payload code
      payload="$(jq -n '{agent_type:"{{PROJECT_NAME}}-code-reviewer",tool_name:"Write",tool_input:{}}')"
      code="$(printf '%s' "$payload" | CLAUDE_PROJECT_DIR="$MALFORMEDFIXDIR" bash "$HOOK" >/dev/null 2>/dev/null; echo $?)"
      exitcode_to_dom "$code"
      ;;
    K6)
      # MERK: agent_type i PAYLOADEN er et vanlig, gyldig rollenavn — det er
      # kontraktFILAS ene linje som har '#' i rollenavn-feltet. Beviser at
      # parse_contract() forkaster HELE fila (fail-closed for ALLE roller,
      # ikke bare den ugyldige linja) fordi INGEN linje kan ha et tegn
      # utenfor det trygge charsettet — helt uavhengig av agent_type-
      # saneringen i steg 3b (som ville fanget en '#' i selve PAYLOADEN,
      # men IKKE en '#' inni kontraktfila — de to er separate vakter).
      local payload code
      payload="$(jq -n '{agent_type:"{{PROJECT_NAME}}-code-reviewer",tool_name:"Write",tool_input:{}}')"
      code="$(printf '%s' "$payload" | CLAUDE_PROJECT_DIR="$COMMENTFIXDIR" bash "$HOOK" >/dev/null 2>/dev/null; echo $?)"
      exitcode_to_dom "$code"
      ;;
    K7)
      local payload code
      payload="$(jq -n '{agent_type:"{{PROJECT_NAME}}-code-reviewer",tool_name:"Write",tool_input:{}}')"
      code="$(printf '%s' "$payload" | CLAUDE_PROJECT_DIR="$NOFIXDIR" bash "$HOOK" >/dev/null 2>/dev/null; echo $?)"
      if [ "$code" != "2" ]; then echo "ERROR(exit=$code, forventet 2)"; return; fi
      if [ -f "$NOFIXDIR/tasks/hook-readonly-gate.log" ] && /usr/bin/grep -qF "PARSE-FAIL" "$NOFIXDIR/tasks/hook-readonly-gate.log"; then
        echo PASS
      else
        echo "ERROR(PARSE-FAIL ikke logget for manglende kontraktfil)"
      fi
      ;;
    K8)
      local payload code
      payload="$(jq -n '{agent_type:"readonly-no-agents",tool_name:"Agent",tool_input:{subagent_type:"whatever-name"}}')"
      code="$(run_hook "$payload")"
      exitcode_to_dom "$code"
      ;;
    K9)
      local payload code
      payload="$(jq -n '{agent_type:"readonly-with-agents",tool_name:"Agent",tool_input:{subagent_type:"allowed-x"}}')"
      code="$(run_hook "$payload")"
      exitcode_to_dom "$code"
      ;;
    K10)
      local payload code
      payload="$(jq -n '{agent_type:"readonly-with-agents",tool_name:"Agent",tool_input:{subagent_type:"ikke-medlem"}}')"
      code="$(run_hook "$payload")"
      exitcode_to_dom "$code"
      ;;
    K11)
      local payload code
      payload="$(jq -n '{agent_type:"greedy-role",tool_name:"Write",tool_input:{}}')"
      code="$(run_hook "$payload")"
      exitcode_to_dom "$code"
      ;;
    K12)
      local payload code
      payload="$(jq -n '{agent_type:"greedy-role",tool_name:"MultiEdit",tool_input:{}}')"
      code="$(run_hook "$payload")"
      exitcode_to_dom "$code"
      ;;
    K13)
      local payload code
      payload="$(jq -n '{agent_type:"greedy-role",tool_name:"mcp__x__apply_migration",tool_input:{}}')"
      code="$(run_hook "$payload")"
      exitcode_to_dom "$code"
      ;;
    K14)
      local payload code
      payload="$(jq -n '{agent_type:"{{PROJECT_NAME}}-planner",tool_name:"Write",tool_input:{}}')"
      code="$(run_hook_dfix "$payload")"
      exitcode_to_dom "$code"
      ;;
    K15)
      local payload code
      payload="$(jq -n '{agent_type:"{{PROJECT_NAME}}-implementer",tool_name:"Agent",tool_input:{subagent_type:"anything-at-all"}}')"
      code="$(run_hook_dfix "$payload")"
      exitcode_to_dom "$code"
      ;;
    K16)
      local payload code
      payload="$(jq -n '{agent_type:"greedy-role",tool_name:"Monitor",tool_input:{}}')"
      code="$(run_hook "$payload")"
      exitcode_to_dom "$code"
      ;;
    K17)
      local payload code
      payload="$(jq -n '{agent_type:"greedy-role",tool_name:"SendMessage",tool_input:{}}')"
      code="$(run_hook "$payload")"
      exitcode_to_dom "$code"
      ;;
    K18)
      # {{PROJECT_NAME}}-scout er nå en
      # linje i den EKTE kontrakten (reviewer-readonly.contract) — kjøres mot
      # DFIXDIR (kopi av den EKTE kontrakten + de EKTE charterne), samme rigg
      # som K14/K15 bruker for å bevise det NEGATIVE (planner/implementer er
      # IKKE i kontrakten). Her beviser vi det POSITIVE: scout ER i kontrakten,
      # og Write blokkeres.
      local payload code
      payload="$(jq -n '{agent_type:"{{READONLY_PROBE_ROLE}}",tool_name:"Write",tool_input:{}}')"
      code="$(run_hook_dfix "$payload")"
      exitcode_to_dom "$code"
      ;;
    K19)
      # Samme rigg som K18, men Bash-skriving i EKSPLISITT enforce-modus (ikke
      # default observe) — se get_b_mode_env-kommentaren over for hvorfor
      # enforce brukes når exit-koden skal være fasit.
      local payload code
      payload="$(jq -n '{agent_type:"{{READONLY_PROBE_ROLE}}",tool_name:"Bash",tool_input:{command:"echo x > f"}}')"
      code="$(printf '%s' "$payload" | CLAUDE_PROJECT_DIR="$DFIXDIR" LOOP_READONLY_GATE_BASH_MODE="enforce" bash "$HOOK" >/dev/null 2>/dev/null; echo $?)"
      exitcode_to_dom "$code"
      ;;
  esac
}

# ── M: meta-assertion — hvert SESSION_SAFE-verktøy i den EKTE hooken MÅ ha en
# tilhørende C-case. En selv-assersjon av case-ANTALL (som over) fanger et
# DROPPET case, men ikke et NYTT SESSION_SAFE-verktøy som aldri fikk et case i
# utgangspunktet (VIKTIG 2) — derfor leses
# SESSION_SAFE ut av selve hook-fila her, i stedet for å hardkodes på nytt.
get_m_desc() {
  case "$1" in
    M1) echo "hvert SESSION_SAFE-verktoy i hooken har en tilhoerende C-case" ;;
  esac
}

# session_safe_tool_has_case <verktøynavn> — hvilken C-case (hvis noen)
# tester at nettopp dette verktøyet PASSerer via SESSION_SAFE (ikke via
# charterets tools:-linje — derfor peker disse alle på "no-tools-agent"-caser
# der SESSION_SAFE er den ENESTE mulige PASS-veien).
session_safe_tool_has_case() {
  case "$1" in
    Read) echo "C21" ;;
    Grep) echo "" ;;
    Glob) echo "" ;;
    NotebookRead) echo "C23" ;;
    TodoWrite) echo "C16" ;;
    BashOutput) echo "C15" ;;
    KillShell) echo "C24" ;;
    ExitPlanMode) echo "C25" ;;
    TaskOutput) echo "C26" ;;
    AskUserQuestion) echo "C27" ;;
    AgentOutput) echo "C30" ;;
    AgentOutputTool) echo "C31" ;;
    BashOutputTool) echo "C32" ;;
    KillBash) echo "C33" ;;
    SubagentHandback) echo "C34" ;;
    *) echo "__UKJENT__" ;;
  esac
}

# id_in_c_ids <id> — er $1 et faktisk medlem av C_IDS? Brukt av run_m til å
# fange en renummerering/sletting av en C-case som session_safe_tool_has_case
# fortsatt peker mot (MINDRE 2, koordinator-fix runde 2).
id_in_c_ids() {
  local needle="$1" c
  for c in $C_IDS; do
    [ "$c" = "$needle" ] && return 0
  done
  return 1
}

run_m() {
  case "$1" in
    M1)
      local raw line tools tool missing=""
      line="$(/usr/bin/grep -m1 '^SESSION_SAFE=' "$HOOK")"
      if [ -z "$line" ]; then echo "ERROR(fant ikke SESSION_SAFE= i hooken)"; return; fi
      raw="${line#SESSION_SAFE=\$\'}"
      raw="${raw%\'}"
      tools="$(printf '%b' "$raw")"
      while IFS= read -r tool; do
        [ -z "$tool" ] && continue
        local hit; hit="$(session_safe_tool_has_case "$tool")"
        if [ "$hit" = "__UKJENT__" ]; then
          missing="$missing $tool(ingen-mapping-i-harness)"
          continue
        fi
        if [ -n "$hit" ]; then
          if ! id_in_c_ids "$hit"; then
            missing="$missing $tool(peker-mot-ukjent-case-$hit)"
            continue
          fi
          local exp; exp="$(get_c_expected "$hit")"
          if [ "$exp" != "PASS" ]; then
            missing="$missing $tool(case-$hit-forventer-$exp-ikke-PASS)"
          fi
        fi
      done <<< "$tools"
      if [ -n "$missing" ]; then
        echo "ERROR(SESSION_SAFE-bokforing feil:$missing)"
      else
        echo PASS
      fi
      ;;
  esac
}

# ── Case-lister (selv-assertion mot planens tall — reviewerens anbefaling) ──
A_IDS="A1 A2 A3 A4 A5 A6 A7 A8 A9 A10 A11 A12 A13 A14 A15 A16 A17 A18 A19 A20 A21 A22 A23 A24 A25 A26 A27 A28 A29 A30 A31 A32 A33"
B_IDS="B1 B2 B3 B4 B5 B6 B7 B8 B9 B10 B11 B12 B13 B14 B15 B16 B17 B18 B19 B20 B21 B22 B23 B24 B25 B26 B27 B28 B29 B30 B31 B32 B33 B34 B35 B36 B37 B38 B39 B40 B41 B42 B43 B44 B45 B46 B47 B48 B49 B50 B51 B52 B53 B54 B55 B56 B57 B58 B59 B60 B61 B62 B63 B64 B65 B66 B67 B68 B69 B70 B71 B72 B73 B74 B75 B76 B77 B78 B79 B80 B81 B82 B83 B84 B85 B86 B87 B88 B89 B90 B91 B92 B93 B94 B95 B96 B97 B98 B99"
C_IDS="C1 C2 C3 C4 C5 C6 C7 C8 C9 C10 C11 C12 C13 C14 C15 C16 C17 C18 C19 C20 C21 C22 C23 C24 C25 C26 C27 C28 C29 C30 C31 C32 C33 C34"
X_IDS="X1 X2 X3 X4 X5 X6 X7 X8 X9 X10 X11"
D_IDS="D1 D2 D3 D4 D5"
K_IDS="K1 K2 K3 K4 K5 K6 K7 K8 K9 K10 K11 K12 K13 K14 K15 K16 K17 K18 K19"
M_IDS="M1"

EXPECTED_A=33
EXPECTED_B=99
EXPECTED_C=34
EXPECTED_X=11
EXPECTED_D=5
EXPECTED_K=19
EXPECTED_M=1
EXPECTED_SUM=202

count_words() { echo "$1" | wc -w | tr -d ' '; }

ACTUAL_A=$(count_words "$A_IDS")
ACTUAL_B=$(count_words "$B_IDS")
ACTUAL_C=$(count_words "$C_IDS")
ACTUAL_X=$(count_words "$X_IDS")
ACTUAL_D=$(count_words "$D_IDS")
ACTUAL_K=$(count_words "$K_IDS")
ACTUAL_M=$(count_words "$M_IDS")
ACTUAL_SUM=$((ACTUAL_A + ACTUAL_B + ACTUAL_C + ACTUAL_X + ACTUAL_D + ACTUAL_K + ACTUAL_M))

if [ "$ACTUAL_A" -ne "$EXPECTED_A" ] || [ "$ACTUAL_B" -ne "$EXPECTED_B" ] || \
   [ "$ACTUAL_C" -ne "$EXPECTED_C" ] || [ "$ACTUAL_X" -ne "$EXPECTED_X" ] || \
   [ "$ACTUAL_D" -ne "$EXPECTED_D" ] || [ "$ACTUAL_K" -ne "$EXPECTED_K" ] || \
   [ "$ACTUAL_M" -ne "$EXPECTED_M" ] || [ "$ACTUAL_SUM" -ne "$EXPECTED_SUM" ]; then
  echo "HARNESS-FEIL: case-antall stemmer ikke med planens lister." >&2
  echo "  A: forventet $EXPECTED_A, faktisk $ACTUAL_A" >&2
  echo "  B: forventet $EXPECTED_B, faktisk $ACTUAL_B" >&2
  echo "  C: forventet $EXPECTED_C, faktisk $ACTUAL_C" >&2
  echo "  X: forventet $EXPECTED_X, faktisk $ACTUAL_X" >&2
  echo "  D: forventet $EXPECTED_D, faktisk $ACTUAL_D" >&2
  echo "  K: forventet $EXPECTED_K, faktisk $ACTUAL_K" >&2
  echo "  M: forventet $EXPECTED_M, faktisk $ACTUAL_M" >&2
  echo "  SUM: forventet $EXPECTED_SUM, faktisk $ACTUAL_SUM" >&2
  echo "Et droppet case skal vaere RODT, ikke usynlig (reviewerens anbefaling runde 3)." >&2
  exit 1
fi

printf '%-4s %-7s %-14s %-6s %s\n' "ID" "ONSKET" "FAKTISK" "DOM" "BESKRIVELSE"
printf -- '----------------------------------------------------------------------------------------------------\n'

total=0
ok=0

# A17c/A32c (koordinator-fix runde 5, VIKTIG 3): de gamle A17b/A32b-
# assertionene (fra runde 3) sjekket at Steg Cs verdi-skann fortsatt logget
# WOULD-ALLOW(value-scan) for disse to payloadene, som bevis på at skannen
# kjørte selv om resultatet var fail-closed BLOCK. Skannen er nå SLETTET
# (Steg C er en ubetinget block()), så den markøren skal ALDRI mer
# forekomme — sjekk det motsatte: at INGEN nye linjer for A17/A32 inneholder
# den gamle markøren, som bevis på at mekanismen faktisk er borte, ikke bare
# at exit-koden tilfeldigvis stemmer.
from17=0
from32=0
for id in $A_IDS; do
  expected="$(get_a_expected "$id")"
  payload="$(get_a_payload "$id")"
  if [ "$id" = "A17" ]; then
    from17=$(( $(gate_log_lines) + 1 ))
  fi
  if [ "$id" = "A32" ]; then
    from32=$(( $(gate_log_lines) + 1 ))
  fi
  code="$(run_hook "$payload")"
  actual="$(exitcode_to_dom "$code")"
  desc="$(get_a_desc "$id")"
  total=$((total + 1))
  if [ "$actual" = "$expected" ]; then
    dom="OK"
    ok=$((ok + 1))
  else
    dom="AVVIK"
  fi
  printf '%-4s %-7s %-14s %-6s %s\n' "$id" "$expected" "$actual" "$dom" "$desc"
done

# A17c/A32c er FULLVERDIGE skårede caser (CI-gatens tellerhull):
# tidligere printet disse "AVVIK" UTEN å røre $total/$ok,
# så sluttsjekken (`[ "$ok" -ne "$total" ]`) aldri så dem — en fremtidig
# regresjon her ville gitt "AVVIK"-tekst i output OG exit=0 samtidig, fordi
# harnessens EGEN "Scorede caser"-linje ikke inkluderte dem. total++ ALLTID,
# ok++ kun ved faktisk OK, akkurat som alle andre caser i fila.
total=$((total + 1))
if gate_log_new_contains "$from17" "WOULD-ALLOW(value-scan)"; then
  printf '%-4s %-7s %-14s %-6s %s\n' "A17c" "fravaer" "MARKOR-FUNNET" "AVVIK" "WOULD-ALLOW(value-scan) skal IKKE lenger forekomme for A17 (Steg C-skannen er slettet)"
else
  ok=$((ok + 1))
  printf '%-4s %-7s %-14s %-6s %s\n' "A17c" "fravaer" "OK" "OK" "WOULD-ALLOW(value-scan) forekommer ikke lenger for A17, som forventet"
fi
total=$((total + 1))
if gate_log_new_contains "$from32" "WOULD-ALLOW(value-scan)"; then
  printf '%-4s %-7s %-14s %-6s %s\n' "A32c" "fravaer" "MARKOR-FUNNET" "AVVIK" "WOULD-ALLOW(value-scan) skal IKKE lenger forekomme for A32 (Steg C-skannen er slettet)"
else
  ok=$((ok + 1))
  printf '%-4s %-7s %-14s %-6s %s\n' "A32c" "fravaer" "OK" "OK" "WOULD-ALLOW(value-scan) forekommer ikke lenger for A32, som forventet"
fi

for id in $B_IDS; do
  expected="$(get_b_expected "$id")"
  cmd="$(get_b_cmd "$id")"
  agent="$(get_b_agent "$id")"
  modeenv="$(get_b_mode_env "$id")"
  desc="$(get_b_desc "$id")"
  from=$(( $(gate_log_lines) + 1 ))

  if [ "$agent" = "__NONE__" ]; then
    payload="$(jq -n --arg cmd "$cmd" '{tool_name:"Bash",tool_input:{command:$cmd}}')"
  else
    payload="$(jq -n --arg a "$agent" --arg cmd "$cmd" '{agent_type:$a,tool_name:"Bash",tool_input:{command:$cmd}}')"
  fi

  if [ -n "$modeenv" ]; then
    code="$(printf '%s' "$payload" | CLAUDE_PROJECT_DIR="$FIXDIR" LOOP_READONLY_GATE_BASH_MODE="$modeenv" bash "$HOOK" >/dev/null 2>/dev/null; echo $?)"
  else
    code="$(printf '%s' "$payload" | CLAUDE_PROJECT_DIR="$FIXDIR" env -u LOOP_READONLY_GATE_BASH_MODE bash "$HOOK" >/dev/null 2>/dev/null; echo $?)"
  fi
  actual="$(exitcode_to_dom "$code")"
  total=$((total + 1))
  if [ "$actual" = "$expected" ]; then
    dom="OK"
    ok=$((ok + 1))
  else
    dom="AVVIK"
  fi
  printf '%-4s %-7s %-14s %-6s %s\n' "$id" "$expected" "$actual" "$dom" "$desc"

  if [ "$id" = "B74" ]; then
    # Fullverdig skåret case (CI-gatens tellerhull)
    # — se A17c/A32c-kommentaren over for begrunnelsen.
    total=$((total + 1))
    if gate_log_new_contains "$from" "WOULD-BLOCK"; then
      ok=$((ok + 1))
      printf '%-4s %-7s %-14s %-6s %s\n' "B74b" "logglinje" "har-markor" "OK" "WOULD-BLOCK funnet i gate-loggen (observe-modus analyserer, biter ikke)"
    else
      printf '%-4s %-7s %-14s %-6s %s\n' "B74b" "logglinje" "MANGLER" "AVVIK" "WOULD-BLOCK IKKE funnet (exit-kode alene beviser ikke at bash-armen analyserte)"
    fi
  fi
done

for id in $C_IDS; do
  expected="$(get_c_expected "$id")"
  payload="$(get_c_payload "$id")"
  code="$(run_hook "$payload")"
  actual="$(exitcode_to_dom "$code")"
  desc="$(get_c_desc "$id")"
  total=$((total + 1))
  if [ "$actual" = "$expected" ]; then
    dom="OK"
    ok=$((ok + 1))
  else
    dom="AVVIK"
  fi
  printf '%-4s %-7s %-14s %-6s %s\n' "$id" "$expected" "$actual" "$dom" "$desc"
done

for id in $X_IDS; do
  expected="$(get_x_expected "$id")"
  actual="$(run_x "$id")"
  desc="$(get_x_desc "$id")"
  total=$((total + 1))
  if [ "$actual" = "$expected" ]; then
    dom="OK"
    ok=$((ok + 1))
  else
    dom="AVVIK"
  fi
  printf '%-4s %-7s %-14s %-6s %s\n' "$id" "$expected" "$actual" "$dom" "$desc"
done

for id in $D_IDS; do
  expected="PASS"
  actual="$(run_d "$id")"
  desc="$(get_d_desc "$id")"
  total=$((total + 1))
  if [ "$actual" = "$expected" ]; then
    dom="OK"
    ok=$((ok + 1))
  else
    dom="AVVIK"
  fi
  printf '%-4s %-7s %-14s %-6s %s\n' "$id" "$expected" "$actual" "$dom" "$desc"
done

for id in $K_IDS; do
  expected="$(get_k_expected "$id")"
  actual="$(run_k "$id")"
  desc="$(get_k_desc "$id")"
  total=$((total + 1))
  if [ "$actual" = "$expected" ]; then
    dom="OK"
    ok=$((ok + 1))
  else
    dom="AVVIK"
  fi
  printf '%-4s %-7s %-14s %-6s %s\n' "$id" "$expected" "$actual" "$dom" "$desc"
done

for id in $M_IDS; do
  expected="PASS"
  actual="$(run_m "$id")"
  desc="$(get_m_desc "$id")"
  total=$((total + 1))
  if [ "$actual" = "$expected" ]; then
    dom="OK"
    ok=$((ok + 1))
  else
    dom="AVVIK"
  fi
  printf '%-4s %-7s %-14s %-6s %s\n' "$id" "$expected" "$actual" "$dom" "$desc"
done

printf -- '----------------------------------------------------------------------------------------------------\n'
echo "Scorede caser: $total  |  OK: $ok  |  AVVIK: $((total - ok))"

# Sluttassersjon 2 (CI-gatens tellerhull, punkt 3):
# $total (den RUNTIME-inkrementerte telleren, inkludert A17c/A32c/B74b som
# ligger UTENFOR A_IDS/B_IDS-listene) må stemme med et hardkodet forventet
# antall. Uten denne ville et fremtidig case som ved en feil ALDRI kjører
# (f.eks. en løkke som dropper ut tidlig) senke $total OG $ok likt — og
# `[ "$ok" -ne "$total" ]` under ville forbli falskt grønn.
EXPECTED_TOTAL_SCORED=$((EXPECTED_SUM + 3))
if [ "$total" -ne "$EXPECTED_TOTAL_SCORED" ]; then
  echo "HARNESS-FEIL: antall FAKTISK SCOREDE caser stemmer ikke (A17c/A32c/B74b inkludert)." >&2
  echo "  total: forventet $EXPECTED_TOTAL_SCORED, faktisk $total" >&2
  echo "Et case som aldri kjørte (og dermed aldri ble scoret) skal vaere RODT, ikke usynlig." >&2
  exit 1
fi

if [ "$ok" -ne "$total" ]; then
  exit 1
fi
exit 0
