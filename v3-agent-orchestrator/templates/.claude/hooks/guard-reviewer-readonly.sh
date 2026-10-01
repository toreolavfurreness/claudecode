#!/usr/bin/env bash
# {{PROJECT_NAME}} — PreToolUse hook: gjør read-only roller (reviewer/kode-reviewer/
# tech-review-agentene) faktisk skrivefri (TODO 187).
#
# Charter-prosaen "Du SKRIVER INGENTING TIL FILSYSTEMET" og
# `tools: Agent(a, b, c)` er hint, ikke håndhevede grenser (lesson 2026-08-31).
# Denne hooken er den håndhevende gaten, med TRE armer — alle default-deny
# allowlists (jf. TODO 188s regel: ikke jag en uendelig denylist):
#
#   Arm 1 (Bash)      — kommandoen må matche en allowlist av lese-kommandoer.
#                        Lander i "observe"-modus (logger WOULD-BLOCK,
#                        returnerer 0) — menneskets bindende beslutning
#                        (planens D7). Flippes til "enforce" av en egen
#                        oppfølgings-PR (TODO 187 Steg 13).
#   Arm 2 (Agent/Task)— subagent-type må stå i rollens EGEN Agent-liste i
#                        KONTRAKTFILA (se under). Håndhever fra dag én.
#   Arm 3 (alt annet) — verktøynavnet må stå i rollens ekstra-verktøy-felt i
#                        KONTRAKTFILA, eller i et fast SESSION_SAFE-sett —
#                        MED MINDRE verktøyet er i det harde
#                        WRITE_DENYLIST_EXACT-settet (Write, Edit, MultiEdit,
#                        NotebookEdit, SlashCommand, Skill, Monitor,
#                        SendMessage, mcp__*), som ALDRI kan grantes via
#                        kontraktfila for en read-only rolle. Håndhever fra
#                        dag én. Monitor/SendMessage lagt til i koordinator-
#                        fix runde 8 (VIKTIG 1) — se WRITE_DENYLIST_EXACT=
#                        under for hvorfor.
#
# KONTRAKTFILA (TODO 187 FIX-MODE RUNDE 7 — STRUKTURENDRING) —
# .claude/hooks/reviewer-readonly.contract, parset av parse_contract() under.
# Dette er hookens ENESTE beslutningsinput for (a) hvem som er read-only,
# (b) hvilke subagenter arm 2 tillater, (c) hvilke ekstra verktøy arm 3
# tillater utover SESSION_SAFE. Charterets `tools:`- og `disallowedTools:`-
# linjer LESES IKKE LENGER av denne hooken i det hele tatt.
#
# HVORFOR: elleve funn av samme feilklasse på tvers av seks runder (2026-08 —
# 2026-09), alle fra å behandle to menneskeskrevne prosalinjer i charteret som
# en håndhevet kontrakt. Runde 5 inverterte klassifiseringen (opt-out i
# stedet for opt-in). Runde 6 fikset en kommentar-på-tools:-linje-bypass
# (BLOKKERENDE 1) og et hull i skrive-denylistet (BLOKKERENDE 2) — men den
# samme fiksen la kommentar-strippingen inn i ÉN av tre konsumenter av
# rålinja, og runde 7s måling viste to NYE bypasser (kommentar på en
# disallowedTools-linje, og en identisk `disallowedTools: Write, Edit`-linje
# med en etterstilt kommentar) — konsumentene hadde driftet fra hverandre
# igjen. Rotårsaken er strukturell, ikke en enkelt streng-bug: prosa som
# tolkes flere steder kan alltid driftes ut av synk. Løsningen er å FJERNE
# tolkningen, ikke lappe den en gang til — én maskin-eid fil, ETT format,
# ingen kommentarsyntaks, eksakt linje-for-rolle-match. Se
# opphavsprosjektets docs/workflow.md (ikke med i kit-et) § TODO 187 runde 7 for full begrunnelse og formatet.
#
# Klassifisering "er denne rollen read-only?": rollenavnet (agent_type) MÅ stå
# som feltets første kolonne i kontraktfila. Tilstedeværelse = read-only.
# Fravær = ikke read-only (samme som {{PROJECT_NAME}}-planner/{{PROJECT_NAME}}-implementer
# i dag — de har bevisst ingen linje i kontrakten). Kontraktfila mangler, er
# uleselig, eller er uparsbar (inkludert tom eller søppel-innhold) → FAIL-
# CLOSED og HØYLYTT: enhver ikke-tom agent_type logges som PARSE-FAIL og
# BLOKKERES — en sikkerhetsgate uten en gyldig kontrakt skal aldri slippe
# noe gjennom, uansett hvilken rolle som spør.
#
# Logger:
#   tasks/hook-blocks.log         — BLOKKERT-linjer, samme format som de to
#                                    eksisterende vaktene.
#   tasks/hook-readonly-gate.log  — ALLE beslutninger for read-only roller
#                                    (ALLOW, BLOCK, WOULD-BLOCK, PARSE-FAIL).
#                                    Tom logg etter en runde med reviewere =
#                                    gaten er død (kanari-regel, se
#                                    opphavsprosjektets docs/workflow.md (ikke med i kit-et)).
#
# Se tasks/plans/todo-187-reviewer-read-only-ikke-handhevet.md for full spec.

set -uo pipefail

# ── PATH-konvensjon (MINDRE 6, koordinator-fix runde 5) ─────────────────────
# ÉN konvensjon i hele fila: sett en trygg, fast PATH (kun root-eide
# systemkataloger) helt øverst, FØR noen ekstern kommando kjøres, og bruk
# deretter bare kommandonavn (ingen /usr/bin/-prefiks) overalt. Tidligere var
# konvensjonen halvveis gjennomført: grep/jq/stat var hardkodet til
# /usr/bin/, mens perl (arm 1s HELE Bash-skanner), awk, sed, tr, date, mv
# gjorde et vanlig PATH-oppslag mot den ARVEDE PATH-en. Å sette PATH selv gir
# nøyaktig samme garanti som de harde /usr/bin/-prefiksene ga, for ALLE
# eksterne kommandokall i fila, inkludert de som tidligere IKKE var prefikset.
# Unntak (bevisst, MINDRE 5): jq-tilgjengelighetssjekken i Steg 1 bruker
# fortsatt det harde /usr/bin/jq-literalet, se kommentaren der.
export PATH="/usr/bin:/bin"

# ── Lokale eksplisitt satt (MINDRE 1, koordinator-fix runde 6) ─────────────
# ${v:0:$maxlen} i sanitize_logval() nedenfor er kun TEGNBASERT (ikke
# bytebasert) i en multibyte-bevisst locale. Målt av koordinatoren: 300 ×
# U+00E6 avkortet under LC_ALL=C ga et annet (og for UTF-8 potensielt
# ugyldig) resultat enn under en UTF-8-locale, fordi hooken tidligere arvet
# hvilken locale prosessen ble startet med. C.UTF-8 er valgt fordi den er
# glibc-innebygd og alltid tilgjengelig UTEN locale-gen — bekreftet med
# `locale -a` på både macOS (dette repoet) og er standard fallback-locale på
# Debian/Ubuntu (altså trygg tvers CI-plattform), i motsetning til en
# spesifikk språklocale som en_US.UTF-8 som kan mangle på minimale
# Ubuntu-images.
export LC_ALL=C.UTF-8

# ── Globale standardverdier (så decide()/block() alltid har noe å logge,
#    også i PARSE-FAIL-stien før noe er parset) ────────────────────────────
SESSION_ID="-"
AGENT_TYPE=""
TOOL=""
CWD=""
TOOL_INPUT_RAW="{}"
MODE="-"

INPUT="$(cat)"

# ── Loggstiutledning (speiler guard-main-merge.sh / guard-supabase-ref.sh) ──
PROJECT_DIR="${CLAUDE_PROJECT_DIR:-${CWD:-$(git -C "$(dirname "$0")" rev-parse --show-toplevel 2>/dev/null || echo "/tmp")}}"
LOG="$PROJECT_DIR/tasks/hook-blocks.log"
GATE_LOG="$PROJECT_DIR/tasks/hook-readonly-gate.log"

# ── Hjelpefunksjoner ─────────────────────────────────────────────────────

# list_contains <newline-separert liste> <streng>
# Bash 3.2 (macOS-default) feiler på "${arr[@]}" for tomme arrays under
# `set -u` — derfor brukes newline-separerte strenger i stedet for
# bash-arrays overalt i denne hooken.
#
# REN BASH, INGEN grep (VIKTIG, koordinator-fix runde 6 fortsettelse — Linux
# CI-funn). Tidligere: `printf '%s\n' "$list" | grep -qxF "$needle"` sendte
# $needle som ARGV-ELEMENT til `grep`. $needle er i flere kallsteder
# angriper-styrt og ubegrenset i lengde ($SUBAGENT fra `tool_input`, $TOOL
# fra `tool_name`) — over Linux' MAX_ARG_STRLEN (128 KiB per argv-element)
# ville `grep` feile å starte (E2BIG), og funksjonen returnere en
# ikke-null exit-kode. Verifisert av koordinatoren at DAGENS kallsteder
# tilfeldigvis alle lander trygt uansett (et "ikke funnet"-utfall fører
# alltid til BLOCK, aldri ALLOW) — men å stole på at et fremtidig kallsted
# ARVER samme heldige egenskap er skjørt. Løkken under bruker KUN bash-
# innebygde konstruksjoner (`while read` + `[` — begge shell-builtins, ALDRI
# en `exec()`), og er dermed strukturelt immun mot ARGV-lengdegrenser
# uansett hvor stor $needle er, på begge OS.
list_contains() {
  local list="$1" needle="$2" item
  [ -z "$needle" ] && return 1
  while IFS= read -r item; do
    [ "$item" = "$needle" ] && return 0
  done <<<"$list"
  return 1
}

# WRITE_DENYLIST_EXACT / is_write_denylisted — ÉN hard, skrivende
# verktøy-denylist (BLOKKERENDE 2, koordinator-fix runde 6, presisert i
# runde 7 da tools:-/disallowedTools:-parsingen av charterfilene ble
# erstattet av kontraktfila .claude/hooks/reviewer-readonly.contract).
# Brukes ETT sted i dag: arm 3 trekker denne denylisten fra kontraktens
# ekstra-verktøy-felt (kolonne 3, EXTRA_TOOLS) for enhver rolle
# klassifisert IS_READONLY=1 (utledet av tilstedeværelse i kontrakten,
# ikke av en tools:-linje) — uansett om verktøyet står eksplisitt i det
# feltet. Målt av
# koordinatoren FØR denne fiksen: et charter med
# `tools: Read, Grep, Bash, MultiEdit, NotebookEdit, mcp__x__apply_migration`
# og `disallowedTools: Write, Edit` ble korrekt klassifisert read-only
# (Write/Edit blokkert), men MultiEdit, NotebookEdit og mcp__x__apply_migration
# slapp ALLE gjennom uendret — arm 3 sjekket kun om verktøyet var et BART
# TOKEN i tools:-linja, ikke om det var et verktøy denne rollen (etter egen
# klassifisering) ikke skulle ha. mcp__-prefikset dekker HELE mcp__*-
# navnerommet (Supabase/GitHub/enhver fremtidig MCP-server), ikke bare kjente
# navn — konsistent med hookens generelle default-deny-prinsipp (TODO 188).
#
# Monitor/SendMessage lagt til (VIKTIG 1, koordinator-fix runde 8): begge var
# fjernet fra SESSION_SAFE (se kommentaren over SESSION_SAFE= under, "FJERNET"),
# men det hindret KUN at de ble gitt ubetinget til alle read-only roller — en
# read-only rolles EGEN kontraktfil kunne likevel fortsatt EKSPLISITT grante
# dem via ekstra-verktøy-feltet, siden arm 3 (før denne fiksen) kun sjekket
# SESSION_SAFE og WRITE_DENYLIST_EXACT før den falt tilbake til å stole på
# kontraktens eget felt. Målt av koordinatoren: en kontraktlinje
# `evil-role\t-\tMonitor,SendMessage,WebFetch,Bash,Artifact` ga BEGGE exit=0
# for Monitor og SendMessage — nøyaktig de to styringskanalene hookens EGEN
# "FJERNET"-kommentar (se under) argumenterer hardest mot: SendMessage er en
# kanal til å instruere en allerede spawnet SKRIVENDE agent (arm 2s bruddtype
# i en annen innpakning), og Monitor bærer et `command`-felt (en
# kommando-kjøring, ikke et lesetak). Kontraktfilas tredje kolonne kunne altså
# dele ut nøyaktig det hooken selv sier aldri skal grantes. Ved å legge dem i
# DETTE settet (samme liste arm 3 allerede trekker fra kontraktens
# ekstra-verktøy-allowlist, ikke en ny, separat liste et annet sted — to
# lister som må holdes i synk var runde 6s rotårsak) kan INGEN kontraktfil
# lenger grante dem, uansett hva ekstra-verktøy-feltet sier.
#
# Artifact vurdert og BEVISST IKKE lagt til: `strings`-uttrekk av kjørende
# binær (2.1.185) viser den bak funksjonsnavnet `publishArtifact` med
# `isReadOnly(){return!1}` (altså ikke skrivefri) — men den er en
# INNHOLDS-PUBLISERINGSKANAL (viser strukturert innhold i klientens UI), ikke
# en styringskanal inn i en annen spawnet agent (SendMessage) eller en
# vilkårlig kommando-kjøring (Monitor), og den skriver ikke til
# filsystem/repo-tilstand — hverken av de to argumentene hookens egen
# "FJERNET"-kommentar bruker, gjelder for Artifact. Den faller derfor utenfor
# scopet for DENNE hooken (Du SKRIVER INGENTING TIL FILSYSTEMET / dispatch av
# skrivende agenter) og er ikke lagt til her — men er notert som en mulig
# fremtidig oppfølging (informasjonseksfiltrering er en annen risikoklasse enn
# filsystem-/repo-mutasjon, og bør i så fall vurderes i en egen, avgrenset
# todo, ikke smettes inn her uten egen analyse).
WRITE_DENYLIST_EXACT=$'Write\nEdit\nMultiEdit\nNotebookEdit\nSlashCommand\nSkill\nMonitor\nSendMessage'

is_write_denylisted() {
  local tok="$1"
  case "$tok" in
    mcp__*) return 0 ;;
  esac
  list_contains "$WRITE_DENYLIST_EXACT" "$tok"
}

# rotate_log_file <sti> — roterer en loggfil ved > 5 MB. Kan aldri feile
# hooken. Delt mellom LOG og GATE_LOG (VIKTIG 5, koordinator-fix runde 5):
# tidligere roterte KUN GATE_LOG — LOG (tasks/hook-blocks.log, den DELTE
# loggen for alle tre vaktene) hadde ingen rotasjon i det hele tatt.
#
# VIKTIG 1 (koordinator-fix runde 6): `stat -f%z` er BSD/macOS-syntaks.
# `stat -f` betyr "filsystem-info" på GNU/Linux (ikke "bruk dette formatet"),
# og `%z` er ikke en gyldig GNU-stat-formatkode for filsystem-info — kallet
# feiler på Linux, `|| echo 0` slår inn, og STØRRELSEN LESES ALLTID SOM 0.
# Rotasjonen har dermed vært STILLE DØD på enhver Linux-kjøring av denne
# hooken (inkludert CI, se VIKTIG 1s CI-kobling). `wc -c` er POSIX og gir
# identisk resultat på BSD/macOS og GNU/Linux uten dialekt-gren.
rotate_log_file() {
  local path="$1"
  if [ -f "$path" ]; then
    local size
    size="$(wc -c <"$path" 2>/dev/null | tr -d ' ')"
    if [ "${size:-0}" -gt 5242880 ] 2>/dev/null; then
      mv -f "$path" "${path}.1" 2>/dev/null || true
    fi
  fi
  return 0
}

# sanitize_logval <verdi> — MINDRE 3 runde 3 + VIKTIG 5 runde 5. Normaliserer
# (fjerner CR/LF, normaliserer literal ' | ') OG AVKORTER angriper-styrte
# verdier ($TI_ISOLATION, $SUBAGENT, tool_input-utdrag m.fl.) FØR de skrives
# til NOEN av de to loggene. Før runde 5 avkortet KUN decide()s lokale
# $compact (til 500 tegn, FØR sanitisering) — $reason var FRI i begge
# kallsteder (decide() sin egen GATE_LOG-linje OG block() sin egen
# LOG-linje). Målt av koordinatoren: en isolation-verdi på 1 000 000 × 'A' ga
# en logglinje på over 1 MB i tasks/hook-blocks.log — den DELTE loggen for
# alle tre vaktene. Ved å avkorte INNE i sanitize_logval selv dekkes begge
# logger og alle kallesteder med ÉN endring, samme rotårsaks-form som
# MODE/DEL-unifiseringen i tidligere runder.
sanitize_logval() {
  local v maxlen=200
  v="$(tr -d '\n\r' <<<"$1" 2>/dev/null)"
  v="${v// | / _ }"
  if [ "${#v}" -gt "$maxlen" ]; then
    v="${v:0:$maxlen}...(avkortet, ${#1} tegn totalt)"
  fi
  printf '%s' "$v"
}

# decide <ALLOW|BLOCK|WOULD-BLOCK|PARSE-FAIL> <arm> <årsak>
decide() {
  local outcome="$1" arm="$2" reason="$3"
  local ts compact
  ts="$(date '+%Y-%m-%dT%H:%M:%S')"
  compact="$(printf '%s' "$TOOL_INPUT_RAW" | jq -c '.' 2>/dev/null)"
  [ -z "$compact" ] && compact="$TOOL_INPUT_RAW"
  reason="$(sanitize_logval "$reason")"
  compact="$(sanitize_logval "$compact")"
  mkdir -p "$(dirname "$GATE_LOG")" 2>/dev/null || true
  rotate_log_file "$GATE_LOG"
  printf '%s | %s | %s | arm:%s | %s | %s | %s | %s | %s\n' \
    "$ts" "$(sanitize_logval "$SESSION_ID")" "$outcome" "$arm" "$(sanitize_logval "${AGENT_TYPE:--}")" "$(sanitize_logval "${TOOL:--}")" "$(sanitize_logval "$MODE")" "$reason" "$compact" \
    >> "$GATE_LOG" 2>/dev/null || true
  return 0
}

# block <arm> <årsak> — logger begge steder, skriver norsk melding, exit 2.
block() {
  local arm="$1" reason="$2"
  decide "BLOCK" "$arm" "$reason"
  mkdir -p "$(dirname "$LOG")" 2>/dev/null || true
  local ts
  ts="$(date '+%Y-%m-%dT%H:%M:%S')"
  rotate_log_file "$LOG"
  reason="$(sanitize_logval "$reason")"
  printf '%s | BLOKKERT | %s | %s (rolle: %s, arm: %s)\n' "$ts" "$(sanitize_logval "${TOOL:--}")" "$reason" "$(sanitize_logval "${AGENT_TYPE:--}")" "$arm" >> "$LOG" 2>/dev/null || true
  {
    printf '{{PROJECT_NAME}}: %s (read-only rolle) blokkert av sikkerhets-hook (arm: %s).\n' "$AGENT_TYPE" "$arm"
    echo ""
    printf 'Årsak: %s\n' "$reason"
    echo ""
    echo "Ikke omgå dette — ikke via python3, node, heredoc, MCP eller en annen sti."
    echo "Rapporter funnet i rapporten din i stedet."
    echo ""
    echo "Det som ER lov: git diff/log/show/status, gh pr diff/view, grep, sed -n '<N,M>p',"
    echo "cat/head/tail, jq, diff, og verktøyene Read/Grep/Glob."
  } >&2
  exit 2
}

# parse_contract <sti> — TODO 187 FIX-MODE RUNDE 7. Leser kontraktfila ÉN
# gang og validerer den strengt. Format: én linje per read-only rolle, TRE
# felt adskilt av bokstavelig TAB — INGEN kommentarsyntaks noe sted (se
# toppkommentaren for hvorfor: kommentarer var selve rotårsaken til at tre
# konsumenter av samme rålinje driftet fra hverandre i runde 6/7).
#
#   <rollenavn>\t<agent-allowlist eller "->\t<ekstra-verktøy eller "-">
#
# - <rollenavn>  : må matche ^[A-Za-z0-9._-]+$, unikt i fila.
# - <agent-allowlist>: "-" (ingen subagent-dispatch tillatt) ELLER en
#   komma-separert liste av subagent-navn (arm 2s allowlist).
# - <ekstra-verktøy>: "-" (ingen ekstra verktøy utover SESSION_SAFE) ELLER en
#   komma-separert liste av verktøynavn (arm 3s allowlist utover
#   SESSION_SAFE — det harde WRITE_DENYLIST_EXACT-settet trekkes ALLTID fra,
#   uansett hva denne kolonnen sier, se arm 3 under).
#
# Enhver avvik fra dette — fil mangler/uleselig, tom fil, et felt som er
# tomt (der "-" var ment), et rollenavn utenfor det trygge charsettet, et
# duplisert rollenavn, eller et allowlist-felt med tegn utenfor
# [A-Za-z0-9_.,-] — gjør HELE fila uparsbar (CONTRACT_OK=0). Ingen
# delvis-parsing, ingen beste-forsøk: en fil vi ikke kan validere 100 % er
# like ubrukelig som en fil som mangler helt (kallerens ansvar å
# fail-closed på CONTRACT_OK=0, se Steg 4).
#
# MERK (MINDRE 1, koordinator-fix runde 8) — presisering av mekanikken,
# ikke en atferdsendring: "et felt som er tomt" over beskriver
# SLUTTRESULTATET av valideringen, IKKE en bokstavelig telling av "eksakt 3
# TAB-separerte felt" i selve `read`-linja (en tidligere versjon av denne
# kommentaren hevdet nettopp det, upresist). `IFS=$'\t' read` behandler TAB
# som IFS-WHITESPACE — samme kollaps-/strip-oppførsel som mellomrom under
# standard-IFS: flere TAB på rad kollapses til ÉTT skille, og
# ledende/etterstilte TAB fjernes FØR feltene i det hele tatt tildeles. En
# linje med etterstilt TAB, ledende TAB, en kollapset TAB-serie, en
# etterstilt blank linje, eller en fil uten avsluttende newline blir derfor
# LEST UT som om linja var strengt velformet — ikke avvist av selve
# `read`-linja. Dette er IKKE fail-open (verifisert av koordinatoren mot
# nøyaktig disse fem formene, i tillegg til de seks formene som ER bekreftet
# fail-closed: CRLF, duplisert rollelinje, rollenavn med etterstilt
# mellomrom, BOM, ledende blank linje, et fjerde felt): sikkerheten kommer
# fra feltVALIDERINGEN rett under `read` (charset-regex, ikke-tom-sjekk,
# duplikat-sjekk mot `seen`), ikke fra en antatt streng TAB-telling i
# `read`-linja selv. En linje der et felt reelt MANGLER (for få
# TAB-separerte segmenter til at alle tre variablene fylles) rammes likevel
# — IKKE av en "feil antall felt"-sjekk, men av at det manglende feltet
# leses som tom streng og deretter feiler `[ -n "${ct_role:-}" ] && ...`
# non-empty-sjekken under, akkurat som ethvert annet tomt felt.
#
# Setter globalt: CONTRACT_OK (1/0) og CONTRACT_LINES (newline-separerte,
# validerte rålinjer — hver "rolle<TAB>agenter<TAB>verktøy").
parse_contract() {
  local path="$1"
  CONTRACT_OK=0
  CONTRACT_LINES=""
  [ -f "$path" ] && [ -r "$path" ] || return 0

  local raw
  raw="$(cat "$path" 2>/dev/null)"
  [ -n "$raw" ] || return 0

  local seen="" line n=0
  local ct_role ct_agents ct_tools ct_extra
  while IFS= read -r line; do
    [ -n "$line" ] || return 0
    IFS=$'\t' read -r ct_role ct_agents ct_tools ct_extra <<<"$line"
    [ -z "${ct_extra:-}" ] || return 0
    [ -n "${ct_role:-}" ] && [ -n "${ct_agents:-}" ] && [ -n "${ct_tools:-}" ] || return 0
    printf '%s' "$ct_role" | grep -qE '^[A-Za-z0-9._-]+$' || return 0
    if [ "$ct_agents" != "-" ]; then
      printf '%s' "$ct_agents" | grep -qE '^[A-Za-z0-9_.,-]+$' || return 0
    fi
    if [ "$ct_tools" != "-" ]; then
      printf '%s' "$ct_tools" | grep -qE '^[A-Za-z0-9_.,-]+$' || return 0
    fi
    list_contains "$seen" "$ct_role" && return 0
    seen="$(printf '%s\n%s' "$seen" "$ct_role")"
    CONTRACT_LINES="$(printf '%s\n%s' "$CONTRACT_LINES" "$line")"
    n=$((n + 1))
  done <<<"$raw"

  [ "$n" -gt 0 ] || return 0
  CONTRACT_OK=1
  return 0
}

# ── 1. jq tilgjengelig? Parsbar stdin? ──────────────────────────────────────
# MINDRE 5 (dokumentert i opphavsprosjektets docs/workflow.md (ikke med i kit-et)): jq hardkodes fortsatt til
# /usr/bin/jq for selve tilgjengelighetssjekken, uavhengig av PATH-
# konvensjonen over — dette er hookens ENESTE bevisste fail-open (mangler
# /usr/bin/jq → exit 0 uten at noen arm kan evaluere payloaden, med én
# PARSE-FAIL-linje logget). Se opphavsprosjektets docs/workflow.md (ikke med i kit-et) for begrunnelsen og hvorfor
# den ikke er utnyttbar i praksis (roten på PATH-katalogene er ikke
# skrivbar for angriperen).
if ! command -v /usr/bin/jq >/dev/null 2>&1; then
  decide "PARSE-FAIL" "-" "jq (/usr/bin/jq) finnes ikke"
  exit 0
fi

# ── 2. Feltparsing — ETT jq-kall PER FELT (VIKTIG 2, koordinator-fix runde 5)
# Dette er 188-regelen anvendt her: ingen strukturert flerlinje-tekst leses
# linjeorientert. Tidligere ble alle fem felt hentet med ETT jq-kall og lest
# linje for linje fra én kommandosubstitusjon — et linjeskift i ÉN
# payload-verdi (f.eks. tool_name:"Write\n") forskjøv alle feltene ETTER den
# i den posisjonelle lesingen (agent_type ble lest som tom streng, og HELE
# gaten falt av siden ingen arm kunne velges). Bekreftet av koordinatoren:
# `{tool_name:"Write\n", agent_type:"{{PROJECT_NAME}}-code-reviewer", ...}` ga
# exit=0 på den gamle koden. Hvert felt fanges nå i sin EGEN
# kommandosubstitusjon — en embedded newline i ett felt kan aldri lenger
# forskyve et annet felt, siden de aldri deler en tekstblokk.
if ! printf '%s' "$INPUT" | jq -e 'type' >/dev/null 2>&1; then
  decide "PARSE-FAIL" "-" "ugyldig JSON eller tom stdin"
  exit 0
fi

TOOL="$(printf '%s' "$INPUT" | jq -r '.tool_name // ""' 2>/dev/null)"
AGENT_TYPE="$(printf '%s' "$INPUT" | jq -r '.agent_type // ""' 2>/dev/null)"
CWD="$(printf '%s' "$INPUT" | jq -r '.cwd // ""' 2>/dev/null)"
SESSION_ID="$(printf '%s' "$INPUT" | jq -r '(.session_id // "-")' 2>/dev/null)"
TOOL_INPUT_RAW="$(printf '%s' "$INPUT" | jq -r '(.tool_input // {} | tostring)' 2>/dev/null)"

[ -z "$SESSION_ID" ] && SESSION_ID="-"
[ -z "$TOOL_INPUT_RAW" ] && TOOL_INPUT_RAW="{}"

# Gjenbruk PROJECT_DIR-utledningen nå som CWD er kjent fra payloaden.
PROJECT_DIR="${CLAUDE_PROJECT_DIR:-${CWD:-$PROJECT_DIR}}"
LOG="$PROJECT_DIR/tasks/hook-blocks.log"
GATE_LOG="$PROJECT_DIR/tasks/hook-readonly-gate.log"

# ── 3. Tidlig retur: hovedtråd (tom/"null" agent_type) MÅ virke (R4) ───────
if [ -z "$AGENT_TYPE" ] || [ "$AGENT_TYPE" = "null" ]; then
  exit 0
fi

# ── 3b. AGENT_TYPE-sanering (MINDRE 4, koordinator-fix runde 6 — fortsatt
# gyldig etter runde 7s strukturendring). $AGENT_TYPE er angriper-styrt
# input og sammenlignes streng-mot-streng mot kontraktfilas rollekolonne
# under. Dette er nå ren inputhygiene (avviser rare/urimelige identifikator-
# verdier FØR sammenligning og logging) — IKKE lenger en path-traversal-vakt,
# siden ingen filsti bygges fra $AGENT_TYPE lenger (runde 7 fjernet
# charter-per-rolle-oppslaget helt, se toppkommentaren).
if ! printf '%s' "$AGENT_TYPE" | grep -qE '^[A-Za-z0-9._-]+$'; then
  decide "PARSE-FAIL" "-" "agent_type inneholder tegn utenfor det trygge identifikator-settet"
  exit 0
fi

# ── 4. Kontraktfil — parse ÉN gang, fail-closed ved ethvert avvik (TODO 187
# FIX-MODE RUNDE 7). Se parse_contract() og toppkommentaren for format og
# begrunnelse. En ikke-tom agent_type uten en gyldig kontrakt å slå opp mot
# BLOKKERES alltid — en sikkerhetsgate uten kontrakt skal aldri slippe
# gjennom, uansett hvilken rolle som spør.
CONTRACT="$PROJECT_DIR/.claude/hooks/reviewer-readonly.contract"
parse_contract "$CONTRACT"

if [ "$CONTRACT_OK" -ne 1 ]; then
  decide "PARSE-FAIL" "-" "kontraktfil ($CONTRACT) mangler, er uleselig eller uparsbar"
  block "contract" "read-only-kontraktfila mangler eller er ugyldig - fail-closed, ingen subagent-rolle kan evalueres uten en gyldig kontrakt"
fi

# ── 5. Slå opp $AGENT_TYPE i kontrakten — eksakt linje-for-rolle-match,
# ingen tolkning. Tilstedeværelse = read-only (regel 4, toppkommentaren).
# Fravær = ikke read-only (samme som {{PROJECT_NAME}}-planner/{{PROJECT_NAME}}-
# implementer, som bevisst ikke har en linje i kontrakten).
IS_READONLY=0
AGENT_ALLOWLIST=""
EXTRA_TOOLS=""
CT_ROLE=""
CT_AGENTS=""
CT_TOOLS=""
while IFS= read -r CONTRACT_LINE; do
  [ -n "$CONTRACT_LINE" ] || continue
  IFS=$'\t' read -r CT_ROLE CT_AGENTS CT_TOOLS <<<"$CONTRACT_LINE"
  if [ "$CT_ROLE" = "$AGENT_TYPE" ]; then
    IS_READONLY=1
    [ "$CT_AGENTS" = "-" ] || AGENT_ALLOWLIST="$(printf '%s' "$CT_AGENTS" | tr ',' '\n')"
    [ "$CT_TOOLS" = "-" ] || EXTRA_TOOLS="$(printf '%s' "$CT_TOOLS" | tr ',' '\n')"
    break
  fi
done <<<"$CONTRACT_LINES"

if [ "$IS_READONLY" -ne 1 ]; then
  exit 0
fi

# Fra her: $AGENT_TYPE er en READ-ONLY rolle.

# Ingen tool_name å vurdere — ingen arm kan velges (R4).
if [ -z "$TOOL" ]; then
  exit 0
fi

# Verktøy som passerer uansett kontrakt-innhold (SESSION_SAFE), MED en
# etterprøvbar begrunnelse per verktøy for hvorfor det ikke kan mutere
# filsystem/repo-tilstand. En uverifisert "beviselig ikke-muterende"-påstand
# er ikke et bevis (koordinatorens fix-mode-runde, TODO 187) — derfor listes
# begrunnelsen her, ikke bare i en samle-kommentar.
#
#   Read           — leser en fil, returnerer innhold. Ingen skriveparameter.
#   Grep           — søker i filinnhold (ripgrep-wrapper), returnerer treff.
#   Glob           — matcher filnavn mot mønster, returnerer stier.
#   NotebookRead   — leser celler fra en .ipynb, returnerer innhold.
#   TodoWrite      — muterer KUN agentens egen in-memory todo-liste for
#                    UI-visning i denne sesjonen, ikke filsystemet eller repoet.
#   BashOutput     — henter bufret stdout/stderr fra en allerede kjørende
#                    bakgrunnsprosess. Leser en buffer, starter ikke noe nytt.
#   KillShell      — avslutter en bakgrunnsprosess (SIGTERM). Reduserer
#                    kjørende tilstand, skriver ikke til filsystem/repo.
#   ExitPlanMode   — sesjons-UI-signal (bytter agentens modus), ingen
#                    filsystem- eller repo-effekt.
#   TaskOutput     — henter allerede produsert output fra en spawnet subagent
#                    (les av ferdig resultat), skriver ikke noe nytt selv.
#   AskUserQuestion — presenterer et spørsmål til mennesket og venter på svar;
#                    ingen fil-/repo-mutasjon i seg selv.
#
# FJERNET (runde koordinator-fix, TODO 187 FIX-MODE): Monitor og SendMessage
# lå i settet fra runde 3s VIKTIG 4, men begge er selv en styringskanal inn i
# kjørende/skrivende prosesser:
#   - SendMessage bærer i kjørende runtime-dokumentasjon presis definisjonen
#     "continue a previously spawned agent with its context intact" — altså
#     en kanal til å instruere en allerede spawnet SKRIVENDE agent (f.eks.
#     general-purpose eller {{PROJECT_NAME}}-implementer) om å utføre skriving på
#     read-only-rollens vegne. Det er nøyaktig bruddet arm 2 finnes for å
#     stoppe (TODO 173 Steg 15), bare pakket inn i en annen kanal.
#   - Monitor bærer et `command`-felt (kjører et skall-kommando-vindu til en
#     betingelse er oppfylt) — det er ikke et lesetak, det er en kommando-
#     kjøring, og hører hjemme i Bash-armens skanner, ikke i en ubetinget
#     SESSION_SAFE-allowlist.
# Kravet VIKTIG 4 opprinnelig dekket (holde §5b-fanouten i live) krever kun
# TaskOutput + AskUserQuestion — de to er beholdt, de to øvrige er fjernet.
#
# VIKTIG (koordinator-fix runde 8): å fjerne dem fra SESSION_SAFE stengte kun
# den UBETINGEDE veien. Kontraktens EGET ekstra-verktøy-felt kunne likevel
# fortsatt eksplisitt grante begge (arm 3s tredje sjekk, se under) — se
# WRITE_DENYLIST_EXACT= sin kommentar lenger opp i fila for det målte funnet
# og fiksen. Begge er nå ALLTID nektet for en read-only rolle, uansett hva
# kontraktfila sier, ikke bare fraværende fra standard-allowlisten.
#
# MINDRE 3 (koordinator-fix runde 5): kjørende runtime (2.1.247) registrerer
# aliaser for flere av disse verktøyene under ANDRE navn enn de dokumenterte
# (`aliases:["AgentOutputTool","BashOutputTool","AgentOutput","BashOutput"]`
# og `aliases:["KillShell","KillBash"]`) — uten disse i settet ville en
# tool_name som ankommer under aliasnavnet falle gjennom til arm 3s
# tools:-linje-sjekk og bli BLOKKERT, noe som i praksis brekker §5b-
# fanoutens resultatlesing (det ENESTE formålet TaskOutput/BashOutput ble
# beholdt for). Alle fire har IDENTISK semantikk til sine kjente søsken:
#   AgentOutputTool/AgentOutput — alias for TaskOutput (leser allerede
#                                 produsert subagent-resultat).
#   BashOutputTool              — alias for BashOutput (leser bufret
#                                 stdout/stderr fra en kjørende bakgrunnsprosess).
#   KillBash                    — alias for KillShell (avslutter en
#                                 bakgrunnsprosess).
SESSION_SAFE=$'Read\nGrep\nGlob\nNotebookRead\nTodoWrite\nBashOutput\nBashOutputTool\nKillShell\nKillBash\nExitPlanMode\nTaskOutput\nAgentOutput\nAgentOutputTool\nAskUserQuestion'

# ── 5. Arm-dispatch på EKSAKT strenglikhet (aldri regex — MINDRE runde 1) ──
if [ "$TOOL" = "Bash" ]; then
  # ── Arm 1 — Bash (observe-modus, D7) ─────────────────────────────────────
  CMD="$(printf '%s' "$TOOL_INPUT_RAW" | jq -r '.command // ""' 2>/dev/null)"

  ENV_MODE="${LOOP_READONLY_GATE_BASH_MODE:-}"
  EFFECTIVE_BASH_MODE="observe"
  if [ "$ENV_MODE" = "enforce" ]; then
    EFFECTIVE_BASH_MODE="enforce"
  fi

  # ── Størrelsesvakt FLYTTET til bash, FØR perl kalles (VIKTIG, koordinator-
  # fix runde 6 fortsettelse — Linux CI-funn). Rotårsak: Linux har
  # MAX_ARG_STRLEN = 131072 byte PER ENKELT argv-element (macOS har ingen
  # slik grense). `perl -e "$BASHSCAN_PERL" -- "$CMD"` sendte $CMD som ett
  # argv-element — en 200 kB kommando overskrider grensen på Linux, `exec`
  # feiler med E2BIG FØR perl-programmet i det hele tatt starter, `2>/dev/null`
  # svelget feilen, og arm 1 i observe-modus falt tilbake til exit 0. Målt av
  # koordinatoren i CI (run 33492149355, ubuntu-latest): X5 (200 kB) ga
  # `exit=0` i stedet for BLOCK — fail-OPEN, kun på Linux. BASH_ARM_MAXLEN
  # under er SAMME TALL som perl-skriptets interne $MAXLEN (8192, se
  # kommentaren der — IKKE hevet, runde 5s beslutning står). Ved å avgjøre
  # størrelsen HER, i bash (streng-lengde i minnet, ingen ny prosess), kan
  # verktøyet aldri felles av grensen det selv skal håndheve — perl startes
  # nå ALDRI med en kommando over grensen, uansett transportkanal.
  BASH_ARM_MAXLEN=8192
  if [ "${#CMD}" -gt "$BASH_ARM_MAXLEN" ]; then
    SCAN_REASON="kommando for lang (over $BASH_ARM_MAXLEN tegn - uavgjorbar innen tidsbudsjett)"
    if [ "$EFFECTIVE_BASH_MODE" = "enforce" ]; then
      block "bash" "$SCAN_REASON"
    else
      decide "WOULD-BLOCK" "bash" "$SCAN_REASON"
      exit 0
    fi
  fi

  # ── Fase-1–4-skanneren (D6+D9) — implementert i Perl for korrekthet
  # (ekte tilstandsmaskin for sitering/escaping, ikke regex på rå tekst —
  # TODO 188s regel) og ytelse (bash 3.2s tegn-for-tegn-løkker er O(n²) på
  # store strenger, målt av plan-reviewen runde 3 til 54s på 200 kB).
  # Programmet ligger inline (ikke en egen fil — «Filer som berøres» lister
  # kun guard-reviewer-readonly.sh + test-fila).
  read -r -d '' BASHSCAN_PERL <<'PERLEOF'
use strict;
use warnings;

# MAXLEN bevisst IKKE hevet i koordinator-fix runde 5 (MINDRE 2): heving ville
# UTVIDE hvor mye ustrukturert tekst som slipper forbi størrelsesvakten og inn
# i full skanning etter enforce-flippen — i strid med runde 5s regel om at
# ingen fiks skal utvide. X5s tidsassersjon i harnessen ble i stedet rettet
# til å teste det den FAKTISK kan bevise (BLOCK-utfallet ved 200 kB), ikke en
# komparativ ytelsespåstand den aldri målte differansen for. Vurderes på nytt
# ved selve enforce-flippen (TODO 187 Steg 13), med en ekte før/etter-måling
# da (se opphavsprosjektets docs/workflow.md (ikke med i kit-et)).
my $MAXLEN = 8192;

# $cmd leses nå fra STDIN, ikke @ARGV (VIKTIG, koordinator-fix runde 6
# fortsettelse — Linux CI-funn). Rotårsak: Linux' MAX_ARG_STRLEN (128 KiB
# per argv-element) har INGEN motsvarighet for stdin — å sende payloaden på
# stdin fjerner HELE argv-lengdeklassen som feilmodus, ikke bare
# størrelsesvakt-tilfellet bash allerede filtrerer FØR dette skriptet
# startes (se BASH_ARM_MAXLEN i den kallende bash-koden). Denne interne
# $MAXLEN-sjekken er dermed nå et REDUNDANT sikkerhetsnett (input hit skal
# aldri kunne overstige 8192 tegn, siden bash allerede har filtrert), ikke
# den eneste linja — samme forsvar-i-dybde-prinsipp som resten av hooken.
my $cmd;
{
  local $/;
  $cmd = <STDIN>;
}
$cmd = '' unless defined $cmd;

if (length($cmd) > $MAXLEN) {
  print "BLOCK\tkommando for lang (over $MAXLEN tegn - uavgjorbar innen tidsbudsjett)\n";
  exit 0;
}

my @quotes;
my $skeleton = '';
my $state = 'NONE'; # NONE | SQ | DQ
my $buf = '';
my $len = length($cmd);
my $i = 0;

while ($i < $len) {
  my $c = substr($cmd, $i, 1);
  if ($state eq 'NONE') {
    if ($c eq '\\') {
      if ($i + 1 >= $len) { print "BLOCK\tuterminert escape\n"; exit 0; }
      $skeleton .= '__';
      $i += 2;
    } elsif ($c eq "'") {
      $state = 'SQ'; $buf = ''; $i += 1;
    } elsif ($c eq '"') {
      $state = 'DQ'; $buf = ''; $i += 1;
    } else {
      $skeleton .= $c; $i += 1;
    }
  } elsif ($state eq 'SQ') {
    if ($c eq "'") {
      push @quotes, $buf;
      $skeleton .= 'Q' . $#quotes;
      $state = 'NONE'; $i += 1;
    } else {
      $buf .= $c; $i += 1;
    }
  } elsif ($state eq 'DQ') {
    if ($c eq '\\') {
      if ($i + 1 >= $len) { print "BLOCK\tuterminert escape i dobbeltfnutt\n"; exit 0; }
      $buf .= $c . substr($cmd, $i + 1, 1);
      $i += 2;
    } elsif ($c eq '"') {
      if (index($buf, '$(') >= 0 || index($buf, '`') >= 0) {
        print "BLOCK\tekspansjon inni dobbeltfnutt\n"; exit 0;
      }
      push @quotes, $buf;
      $skeleton .= 'Q' . $#quotes;
      $state = 'NONE'; $i += 1;
    } else {
      $buf .= $c; $i += 1;
    }
  }
}

if ($state ne 'NONE') { print "BLOCK\tuterminert sitat\n"; exit 0; }

if (index($skeleton, '<(') >= 0 || index($skeleton, '>(') >= 0) {
  print "BLOCK\tprosess-substitusjon\n"; exit 0;
}

my $redir_check = $skeleton;
$redir_check =~ s/[0-9]?&?>>?\s*\/dev\/null//g;
$redir_check =~ s/[0-9]?>&[0-9]//g;
if (index($redir_check, '>') >= 0) { print "BLOCK\tredirect\n"; exit 0; }
if (index($skeleton, '<<') >= 0) { print "BLOCK\theredoc\n"; exit 0; }

my @segments = split /&&|\|\||\$\(|`|;|\||&|\(|\)|\n/, $skeleton;

sub deref {
  my ($tok) = @_;
  if ($tok =~ /^Q(\d+)$/) { return $quotes[$1]; }
  return undef;
}
sub is_qtoken { my ($tok) = @_; return $tok =~ /^Q\d+$/; }
sub effective_name {
  my ($tok) = @_;
  if (is_qtoken($tok)) { return deref($tok); }
  return $tok;
}

my @STANDALONE = qw(cat head tail wc ls grep egrep fgrep rg jq diff uniq cut tr nl column echo printf date pwd cd basename dirname stat file which type true false test);
my %STANDALONE = map { $_ => 1 } @STANDALONE;
$STANDALONE{'['} = 1;
$STANDALONE{'sw_vers'} = 1;
$STANDALONE{'uname'} = 1;

my %FIND_FLAGS = map { $_ => 1 } qw(-name -iname -path -type -maxdepth -mindepth -not -o -a -print -print0 -newer -size -empty -regex -prune);
my %GIT_UNCONDITIONAL = map { $_ => 1 } qw(diff log show status rev-parse rev-list ls-files ls-tree cat-file blame grep describe shortlog check-ignore merge-base for-each-ref name-rev whatchanged);
my %GIT_CONDITIONAL = map { $_ => 1 } qw(fetch merge remote config branch worktree symbolic-ref stash);
my %GH_SUBCMDS_SIMPLE = (
  'pr' => { diff=>1, view=>1, list=>1, checks=>1, status=>1 },
  'issue' => { view=>1, list=>1 },
  'run' => { view=>1, list=>1 },
  'repo' => { view=>1 },
  'label' => { list=>1 },
  'release' => { view=>1, list=>1 },
  'auth' => { status=>1 },
);

sub block_reason { print "BLOCK\t$_[0]\n"; exit 0; }

# Carve-out SNEVRET (MINDRE 2, koordinator-fix-runde TODO 187): kun
# test-*.sh (aldri guard-*.sh — den vokteren skal ikke kunne kjøre SEG SELV
# med frie argumenter), og kun UTEN argumenter (bare kommandoordet alene i
# segmentet). Tidligere versjon matchet kun $ft (segmentets FØRSTE token) og
# gjorde deretter `next` for HELE segmentet uansett hva som fulgte —
# `.claude/hooks/guard-reviewer-readonly.sh --whatever` ga dermed ALLOW med
# et fritt, angriper-styrt argument inn i selve vakten (som appender til
# gate-loggen — logg-injeksjon, se opphavsprosjektets docs/workflow.md (ikke med i kit-et) restrisiko-avsnitt).
sub check_carveout_token {
  my ($tok) = @_;
  if ($tok =~ m{^(?:\./)?\.claude/hooks/test-[A-Za-z0-9._-]+\.sh$}) { return 1; }
  if ($tok =~ m{^Q(\d+)/\.claude/hooks/test-[A-Za-z0-9._-]+\.sh$}) {
    my $idx = $1;
    if (defined $quotes[$idx] && $quotes[$idx] eq '$CLAUDE_PROJECT_DIR') { return 1; }
    return 0;
  }
  return 0;
}

foreach my $seg (@segments) {
  my $s = $seg;
  $s =~ s/^\s+|\s+$//g;
  next if $s eq '';

  my @tokens = split /\s+/, $s;
  next unless @tokens;

  my $ft = $tokens[0];

  if (@tokens == 1 && check_carveout_token($ft)) { next; }

  my $ft_name0 = effective_name($ft);
  if (defined $ft_name0 && ($ft_name0 eq 'bash' || $ft_name0 eq 'sh')) {
    if (@tokens == 2 && check_carveout_token($tokens[1])) { next; }
    block_reason("kommando '$ft_name0' er ikke i allowlisten (kun motprove-carve-out mot .claude/hooks/test-*.sh UTEN argumenter tillatt)");
  }

  my $name = effective_name($ft);
  if (!defined $name) { block_reason("uavgjorbar kommandoposisjon (sitert verdi kan ikke slas opp)"); }
  $name =~ s{^.*/}{};

  if ($name eq 'git') {
    my $idx = 1;
    if ($idx < @tokens) {
      my $t1 = $tokens[$idx];
      if ($t1 eq '--no-pager' || $t1 eq '-P') { $idx++; }
    }
    if ($idx >= @tokens) { block_reason("git uten underkommando"); }
    my $subtok = $tokens[$idx];
    if (is_qtoken($subtok)) { block_reason("git <sitert underkommando> - uavgjorbar"); }
    if ($subtok =~ /^-/) { block_reason("globalt git-flagg foran underkommando ('$subtok')"); }
    my $subcmd = $subtok;
    my @rest = @tokens[($idx+1)..$#tokens];

    foreach my $t (@tokens) {
      if ($t eq '--output' || $t =~ /^--output=/) { block_reason("git --output skriver uten shell-redirect"); }
    }

    if ($GIT_UNCONDITIONAL{$subcmd}) {
      if ($subcmd eq 'grep') {
        foreach my $t (@rest) {
          if ($t =~ /^-O/) { block_reason("git grep -O<pager> kjorer ekstern pager/editor"); }
        }
      }
      next;
    }
    if (!$GIT_CONDITIONAL{$subcmd}) { block_reason("git-underkommando '$subcmd' ikke i allowlisten"); }

    my @nonflag = grep { !/^-/ } @rest;
    my @flags = grep { /^-/ } @rest;

    if ($subcmd eq 'stash') {
      if (@rest && $rest[0] eq 'list') { next; }
      block_reason("git stash <annet enn list>");
    } elsif ($subcmd eq 'fetch') {
      # MINDRE 1 (koordinator-fix runde 5): tidligere sjekket koden KUN
      # $nonflag[0], og lot deretter HELE resten av kommandolinjen passere
      # ukontrollert. `git fetch origin +refs/heads/dev:refs/heads/main`
      # (skrivende refspec) og `git fetch origin --prune --force` (kan
      # slette/omskrive lokale referanser) ga BEGGE exit=0 (målt av
      # koordinatoren). Reject nå eksplisitt prune/force/refmap-flagg, og
      # ethvert non-flag-argument utover et bart 'origin' som inneholder ':'
      # (en skrivende refspec kan aldri være et bart ref-navn).
      foreach my $t (@flags) {
        if ($t eq '--prune' || $t eq '-p' || $t eq '--force' || $t eq '-f' || $t =~ /^--refmap(=|$)/) {
          block_reason("git fetch flagg '$t' kan omskrive/slette lokale referanser");
        }
      }
      if (@nonflag == 0) { next; }
      if ($nonflag[0] ne 'origin') { block_reason("git fetch mot annet enn origin"); }
      for (my $j = 1; $j < @nonflag; $j++) {
        if (index($nonflag[$j], ':') >= 0) {
          block_reason("git fetch med skrivende refspec (inneholder ':')");
        }
      }
      next;
    } elsif ($subcmd eq 'merge') {
      if (@nonflag == 1 && $nonflag[0] =~ m{^origin/}) { next; }
      block_reason("git merge av annet enn origin/<branch>");
    } elsif ($subcmd eq 'remote') {
      my $ok = 1;
      foreach my $t (@nonflag) { $ok = 0 unless ($t eq 'show' || $t eq 'get-url'); }
      if ($ok) { next; }
      block_reason("git remote skriver (add/set-url/rename/remove)");
    } elsif ($subcmd eq 'config') {
      my $ok = (@nonflag <= 1);
      foreach my $t (@flags) {
        $ok = 0 unless ($t eq '--get' || $t eq '--get-all' || $t eq '--get-regexp' || $t eq '--list' || $t eq '-l');
      }
      if ($ok) { next; }
      block_reason("git config skriver");
    } elsif ($subcmd eq 'branch') {
      my $ok = (@nonflag == 0);
      foreach my $t (@flags) {
        unless ($t eq '--show-current' || $t eq '-v' || $t eq '-vv' || $t eq '--list' || $t eq '-a' || $t eq '--all' || $t eq '-r' || $t eq '--remotes' || $t =~ /^--format/ || $t =~ /^--sort/) {
          $ok = 0;
        }
      }
      if ($ok) { next; }
      block_reason("git branch oppretter/endrer");
    } elsif ($subcmd eq 'worktree') {
      if (@rest && $rest[0] eq 'list') { next; }
      block_reason("git worktree <annet enn list>");
    } elsif ($subcmd eq 'symbolic-ref') {
      if (@nonflag <= 1) { next; }
      block_reason("git symbolic-ref med 2+ argumenter (skriver)");
    }
    block_reason("git-underkommando '$subcmd' - uhandtert gren");
  }
  elsif ($name eq 'gh') {
    my $idx = 1;
    if ($idx >= @tokens) { block_reason("gh uten underkommando"); }
    my $t1 = $tokens[$idx];
    if ($t1 eq '--version' || $t1 eq '--help') {
      if (@tokens == 2) { next; }
      block_reason("gh --version/--help brukt som prefiks til en underkommando");
    }
    if (is_qtoken($t1)) { block_reason("gh <sitert underkommando> - uavgjorbar"); }
    if ($t1 =~ /^-/) { block_reason("globalt gh-flagg foran underkommando ('$t1')"); }
    if ($t1 eq 'search') { next; }
    if ($t1 eq 'api') {
      my @rest = @tokens[($idx+1)..$#tokens];
      my $method = undef;
      my $mutating_field = 0;
      for (my $j = 0; $j < @rest; $j++) {
        my $t = $rest[$j];
        if ($t eq '--method' || $t eq '-X') {
          $method = effective_name($rest[$j+1]) if defined $rest[$j+1];
        } elsif ($t =~ /^--method=(.*)$/) {
          my $v = $1; $method = is_qtoken($v) ? deref($v) : $v;
        } elsif ($t =~ /^-X(.+)$/) {
          my $v = $1; $method = is_qtoken($v) ? deref($v) : $v;
        } elsif ($t eq '-f' || $t eq '-F' || $t eq '--raw-field' || $t eq '--field' || $t eq '--input') {
          $mutating_field = 1;
        } elsif ($t =~ /^-[fF]./) {
          $mutating_field = 1;
        }
      }
      if ($mutating_field) { block_reason("gh api med -f/-F/--raw-field/--input (implisitt POST)"); }
      if (defined $method && uc($method) ne 'GET') { block_reason("gh api med --method/-X != GET"); }
      next;
    }
    if (exists $GH_SUBCMDS_SIMPLE{$t1}) {
      my $idx2 = $idx + 1;
      if ($idx2 >= @tokens) { block_reason("gh $t1 uten underkommando"); }
      my $t2 = $tokens[$idx2];
      if (is_qtoken($t2)) { block_reason("gh $t1 <sitert underkommando> - uavgjorbar"); }
      if ($GH_SUBCMDS_SIMPLE{$t1}{$t2}) { next; }
      block_reason("gh $t1 $t2 ikke i allowlisten");
    }
    block_reason("gh-underkommando '$t1' ikke i allowlisten");
  }
  elsif ($name eq 'sed') {
    my @rest = @tokens[1..$#tokens];
    my $script_checked = 0;
    my $script_ok = 0;
    my $flag_bad = 0;
    my $no_script = 1;
    foreach my $t (@rest) {
      if (!$script_checked) {
        if (is_qtoken($t)) {
          my $lit = deref($t);
          if ($lit =~ /^-/) { block_reason("sed med sitert flagg i flaggposisjon - uavgjorbar"); }
          $script_checked = 1; $no_script = 0;
          $script_ok = ($lit =~ /^[0-9]+(,[0-9]+)?p$/) ? 1 : 0;
        } elsif ($t =~ /^-/) {
          unless ($t eq '-n' || $t eq '-E' || $t eq '-r') { $flag_bad = 1; }
        } else {
          $script_checked = 1; $no_script = 0;
          $script_ok = ($t =~ /^[0-9]+(,[0-9]+)?p$/) ? 1 : 0;
        }
      }
    }
    if ($flag_bad) { block_reason("sed-flagg utenfor lesemodus"); }
    if ($no_script) { block_reason("sed uten lesbart script"); }
    if (!$script_ok) { block_reason("sed-script er ikke ren lese-form ('<N>p' / '<N>,<M>p')"); }
    next;
  }
  elsif ($name eq 'find') {
    my @rest = @tokens[1..$#tokens];
    foreach my $t (@rest) {
      if ($t =~ /^-/ && !$FIND_FLAGS{$t}) { block_reason("find-flagg '$t' ikke i allowlisten"); }
    }
    next;
  }
  elsif ($name eq 'sort') {
    my @rest = @tokens[1..$#tokens];
    foreach my $t (@rest) {
      if ($t eq '-o' || $t eq '--output' || $t =~ /^--output=/ || $t =~ /^--compress-program/) {
        block_reason("sort $t skriver/kjorer ekstern kommando");
      }
    }
    next;
  }
  elsif ($name eq 'rg') {
    my @rest = @tokens[1..$#tokens];
    foreach my $t (@rest) {
      if ($t eq '--pre' || $t =~ /^--pre=/) { block_reason("rg --pre kjorer en ekstern kommando"); }
    }
    next;
  }
  elsif ($name eq 'env') {
    my @rest = @tokens[1..$#tokens];
    if (@rest) { block_reason("env med argumenter (variabel-prefiks-omgaelse)"); }
    next;
  }
  elsif ($STANDALONE{$name}) {
    next;
  }
  else {
    block_reason("kommando '$name' er ikke i allowlisten");
  }
}

print "ALLOW\n";
exit 0;
PERLEOF

  # $CMD sendes nå på STDIN, ikke som argv-element (VIKTIG, koordinator-fix
  # runde 6 fortsettelse — Linux CI-funn, se BASH_ARM_MAXLEN-kommentaren
  # over og $cmd-kommentaren inni PERLEOF). `set -o pipefail` INNE i
  # command-substitusjonens subshell gjør at $? etter substitusjonen er
  # PERLENS egen exit-kode (siden `printf` selv praktisk talt aldri feiler),
  # uavhengig av `printf`s alltid-0. MERK: ${PIPESTATUS[1]} er IKKE brukbar
  # her — PIPESTATUS oppdateres for pipelinen INNE i subshell-en som kjører
  # $(...), og er ikke synlig i det ytre skallet etterpå; under `set -u`
  # gir det "unbound variable" fordi den ytre PIPESTATUS aldri fylles med
  # et element[1] (denne runden fikk vi det bekreftet i CI-diagnosen).
  SCAN_OUT="$(set -o pipefail; printf '%s' "$CMD" | perl -e "$BASHSCAN_PERL" 2>/dev/null)"
  PERL_STATUS=$?
  SCAN_STATUS="${SCAN_OUT%%$'\t'*}"

  if [ "$SCAN_STATUS" = "ALLOW" ]; then
    decide "ALLOW" "bash" "kommando i allowlisten"
    exit 0
  fi

  # «Perl feilet» og «perl sa ingenting» var tidligere IKKE skillbare — begge
  # ga en tom $SCAN_REASON og samme fail-closed utfall, men uten synlig
  # årsak i loggen (koordinator-fix runde 6 fortsettelse). En helt tom
  # $SCAN_OUT kan bare skje hvis perl aldri fikk kjøre skriptet sitt ferdig
  # (skriptet selv printer ALLTID enten "ALLOW" eller "BLOCK<tab>årsak" før
  # exit) — logg det eksplisitt med perlens exit-kode, i stedet for en tom
  # streng. Fail-closed-UTFALLET er uendret (samme BLOCK/WOULD-BLOCK-gren
  # som før); kun synligheten er ny.
  if [ -z "$SCAN_OUT" ]; then
    SCAN_REASON="perl-skanneren feilet eller ga intet resultat (perl exit=$PERL_STATUS) - fail-closed"
  else
    SCAN_REASON="${SCAN_OUT#*$'\t'}"
  fi

  if [ "$EFFECTIVE_BASH_MODE" = "enforce" ]; then
    block "bash" "$SCAN_REASON"
  else
    decide "WOULD-BLOCK" "bash" "$SCAN_REASON"
    exit 0
  fi

elif [ "$TOOL" = "Agent" ] || [ "$TOOL" = "Task" ]; then
  # ── Arm 2 — Agent/Task (D8, håndhever fra dag én) ────────────────────────
  #
  # MODE_FIELD_NAMES — feltnavn som kan bære en permission-mode-verdi. Steg A
  # vurderer VERDIEN til ALLE disse, ikke bare det første ikke-tomme treffet
  # i en `//`-kjede — en slik kjede lar et tomt/benignt forfelt skygge for et
  # forhøyet bakfelt, siden tom streng er truthy i jq og `//` da ikke faller
  # videre (VIKTIG 1, koordinator-fix runde 2. Motprøver: `{mode:"default",
  # permission_mode:"bypassPermissions"}`, `{permission_mode:"default",
  # permissionMode:"bypassPermissions"}`, `{mode:"",
  # permission_mode:"bypassPermissions"}` ga alle exit=0 med den gamle
  # `//`-kjeden).
  #
  # Feltnavnene `mode`, `isolation`, `subagent_type`, `model`,
  # `run_in_background`, `name`, `team_name` er dokumentert i den lokalt
  # installerte @anthropic-ai/claude-code@2.1.247 (MINDRE 4, koordinator-fix
  # runde 5: oppdatert fra 2.1.185 — kjørende versjon er nå et enkelt-fil-app
  # UTEN `sdk-tools.d.ts`; revieweren verifiserte i selve binæren, ikke i en
  # typedefinisjonsfil, at BÅDE `permission_mode` og `permissionMode` er
  # reelle observerte feltnavn — ikke lenger en hedget, uverifisert antakelse
  # slik runde 2 måtte notere det som).
  MODE_FIELD_NAMES=$'mode\npermission_mode\npermissionMode'

  # MODE_JQ_PATHS-selvtesten (MINDRE 2, koordinator-fix runde 3) BLIR
  # STÅENDE uendret — den vokter Steg As mode-validering, som faktisk
  # avgjør beslutningen. Den ANDRE selvtesten som pleide å stå her
  # (DEL_JQ_ARGS, for Steg Cs verdi-skann) er FJERNET sammen med resten av
  # Steg C, se kommentaren ved Steg C under (VIKTIG 3, koordinator-fix
  # runde 5).
  MODE_JQ_PATHS="$(printf '%s\n' "$MODE_FIELD_NAMES" | sed -E 's/^(.+)$/.["\1"]/' | tr '\n' ',' | sed -E 's/,$//')"
  if ! jq -n "[$MODE_JQ_PATHS]" >/dev/null 2>&1; then
    block "agent" "MODE_JQ_PATHS kompilerer ikke (jq-syntaksfeil i feltnavnliste — fail-closed, ikke stille tomt)"
  fi

  # MINDRE 1 (koordinator-fix runde 3): `select(type=="string" and
  # length>0)` droppet tidligere STILLE enhver ikke-streng mode-verdi (f.eks.
  # et array-formet `{"mode":["bypassPermissions"]}`) — fail-OPEN, og
  # inkonsistent med isolation-sjekken under. Hent i stedet ALLE ikke-null
  # verdier MED typen bevart (jq -c), og bloker eksplisitt («mode-felt til
  # stede men ikke streng») hvis en av dem ikke er en streng, i stedet for å
  # la dem falle ut av select() umerket.
  TI_MODE_RAW="$(printf '%s' "$TOOL_INPUT_RAW" | jq -c "[$MODE_JQ_PATHS] | .[] | select(. != null)" 2>/dev/null)"
  TI_MODE_VALUES=""
  while IFS= read -r TI_MODE_RAWVAL; do
    [ -z "$TI_MODE_RAWVAL" ] && continue
    TI_MODE_RAWTYPE="$(printf '%s' "$TI_MODE_RAWVAL" | jq -r 'type' 2>/dev/null)"
    if [ "$TI_MODE_RAWTYPE" != "string" ]; then
      block "agent" "mode-felt til stede men ikke en streng (type: ${TI_MODE_RAWTYPE:-ukjent})"
    fi
    TI_MODE_STRVAL="$(printf '%s' "$TI_MODE_RAWVAL" | jq -r '.' 2>/dev/null)"
    if [ -n "$TI_MODE_STRVAL" ]; then
      TI_MODE_VALUES="$(printf '%s\n%s' "$TI_MODE_VALUES" "$TI_MODE_STRVAL")"
    fi
  done <<EOF
$TI_MODE_RAW
EOF
  TI_MODE_VALUES="$(printf '%s\n' "$TI_MODE_VALUES" | grep -v '^$' || true)"

  # isolation (VIKTIG 4, koordinator-fix runde 5): speiler nå mode-feltets
  # TYPE-BEVARTE håndtering (jq -c + select(. != null)) i stedet for den
  # gamle `.isolation // ""`, som falt gjennom på BÅDE null OG false — jq
  # sin `//`-operator er falsy for begge. Målt av koordinatoren:
  # isolation=false ga tidligere exit=0 (gaten fyrte IKKE), mens
  # kommentaren HER (skrevet i runde 3) feilaktig hevdet at isolation-
  # sjekken allerede dekket et array-formet felt og brukte den som
  # forbildet for mode-fiksen — presis omvendt av virkeligheten. Blokkerer
  # nå ETHVERT ikke-null isolation-felt uansett type.
  TI_ISOLATION_RAW="$(printf '%s' "$TOOL_INPUT_RAW" | jq -c '.isolation | select(. != null)' 2>/dev/null)"
  MODE="$(printf '%s\n' "$TI_MODE_VALUES" | grep -v '^$' | head -1)"
  [ -z "$MODE" ] && MODE="-"

  # Steg A — parameter-validering FØRST, uavhengig av identitet (VIKTIG 3
  # runde 2). ALLE mode-bærende felt vurderes (VIKTIG 1 runde 2) — blokkér
  # hvis NOEN av dem har en ikke-tom verdi ulik default/plan, ikke bare
  # første treff i en fallback-kjede.
  while IFS= read -r TI_MODE_ONE; do
    [ -z "$TI_MODE_ONE" ] && continue
    if [ "$TI_MODE_ONE" != "default" ] && [ "$TI_MODE_ONE" != "plan" ]; then
      block "agent" "forhøyet permission-mode ('$TI_MODE_ONE')"
    fi
  done < <(printf '%s\n' "$TI_MODE_VALUES")
  if [ -n "$TI_ISOLATION_RAW" ]; then
    TI_ISOLATION_STRVAL="$(printf '%s' "$TI_ISOLATION_RAW" | jq -r 'if type=="string" then . else tostring end' 2>/dev/null)"
    block "agent" "isolation satt ('$TI_ISOLATION_STRVAL')"
  fi
  # Ingen separat run_in_background-sjekk her (fjernet i koordinator-fix-runden,
  # TODO 187 FIX-MODE VIKTIG 3): payload UTEN feltet gir samme utfall som
  # payload MED feltet satt til true, fordi bakgrunnsdispatch er verktøyets
  # DEFAULT, ikke et unntak — en sjekk som kun fanger den eksplisitte
  # `true`-verdien dekker ikke det faktiske overflatearealet og var derfor en
  # dokumentert kontroll som ikke fantes. Bakgrunnsdispatch av en allowlistet
  # subagent er identisk med synkron dispatch av samme subagent for arm 2s
  # formål (samme skrivetilgang, samme charter) — resultatet leses uansett kun
  # via TaskOutput, som er eksplisitt tillatt i SESSION_SAFE.

  # MERK (TODO 187 FIX-MODE RUNDE 7): den gamle "uscopet charter"-eskapen
  # (et bart Agent/Task-token uten Agent(...)-parentes tillot ALL
  # subagent-dispatch) er FJERNET. Kontraktfilas AGENT_ALLOWLIST er nå
  # eneste kilde — "-" (tom allowlist) betyr at ALL Agent/Task-dispatch for
  # denne rollen blokkeres i Steg B under, ikke at den tillates.

  # Steg B — fallback-kjede på feltnavn.
  SUBAGENT="$(printf '%s' "$TOOL_INPUT_RAW" | jq -r '.subagent_type // .agent_type // .type // ""' 2>/dev/null)"

  if [ -n "$SUBAGENT" ]; then
    if list_contains "$AGENT_ALLOWLIST" "$SUBAGENT"; then
      decide "ALLOW" "agent" "'$SUBAGENT' i allowlist"
      exit 0
    fi
    block "agent" "subagent_type '$SUBAGENT' er ikke i kontraktens Agent-allowlist for '$AGENT_TYPE'"
  fi

  # Steg C — SLETTET verdi-skann (VIKTIG 3, koordinator-fix runde 5). Steg C
  # ble GJORT fail-closed i forrige runde (BEGGE utfall av skannen endte i
  # block()) — men kompilerings-selvtesten for DEL_JQ_ARGS (skannens
  # jq-del(...)-argumentliste) kjørte likevel FØR denne uunngåelige
  # blokkeringen, og kunne selv blokkere på et helt ubeslektet grunnlag (en
  # skrivefeil i feltnavnlisten OTHER_KNOWN_FIELDS). Målt av koordinatoren:
  # BÅDE en payload med skann-TREFF og en payload UTEN treff ga identisk
  # `exit=2` — skannens utfall kunne altså ikke lenger påvirke
  # beslutningen i det hele tatt. Netto: en beregning som IKKE bestemte noe,
  # hadde likevel makt til å avbryte hele §5b-tech-review-fanouten på et
  # urelatert grunnlag. Fjernet: skann-løkken, KNOWN_AGENT_FIELDS,
  # OTHER_KNOWN_FIELDS, DEL_JQ_ARGS og selvtesten for DEL_JQ_ARGS. Steg C er
  # nå en UBETINGET block() — samme faktiske utfall (BLOCK) som før
  # skanningen, men uten den døde beregningen og uten dens feilmodus. Hele
  # tool_input tas med i årsaken for full synlighet i stedet for skannens
  # enkelt-verdi-logging (sanitize_logval avkorter trygt, se VIKTIG 5).
  # Dette lukker også MINDRE-funnet om at Steg C skrev TO logglinjer for ÉN
  # beslutning (én fra decide()s WOULD-ALLOW(value-scan), én fra det
  # påfølgende block()-kallet) — nå er det ETT block()-kall, altså én linje,
  # slik kommentaren over sanitize_logval() alltid har forutsatt.
  block "agent" "ingen subagent-type i kjente felt (subagent_type/agent_type/type) — payload: $TOOL_INPUT_RAW"

else
  # ── Arm 3 — alt annet (D10, håndhever fra dag én) ────────────────────────
  if list_contains "$SESSION_SAFE" "$TOOL"; then
    decide "ALLOW" "tool" "SESSION_SAFE-verktøy"
    exit 0
  fi
  # BLOKKERENDE 2 (koordinator-fix runde 6, uendret prinsipp etter runde 7s
  # strukturendring): det harde skrive-denylistet (WRITE_DENYLIST_EXACT +
  # mcp__-prefiks) sjekkes FØR kontraktens ekstra-verktøy-felt får lov til å
  # grante noe — uansett hva kontraktfila sier. En rolle klassifisert
  # IS_READONLY=1 kan ALDRI få disse verktøyene via arm 3.
  if is_write_denylisted "$TOOL"; then
    block "tool" "verktøy '$TOOL' er i det harde skrive-denylistet (Write/Edit/MultiEdit/NotebookEdit/SlashCommand/Skill/Monitor/SendMessage/mcp__*) - kan ikke grantes til en read-only rolle via kontraktfila"
  fi
  if list_contains "$EXTRA_TOOLS" "$TOOL"; then
    decide "ALLOW" "tool" "star i kontraktens ekstra-verktoy-felt for '$AGENT_TYPE'"
    exit 0
  fi
  block "tool" "verktøy '$TOOL' star verken i kontraktens ekstra-verktoy-felt eller i SESSION_SAFE"
fi

# Skal aldri nås (alle grener over exit'er eksplisitt) — men en vakt skal
# aldri arve exit-kode fra siste kommando (MINDRE-funn runde 1).
exit 0
