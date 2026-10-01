#!/usr/bin/env bash
# Oppsamler for forlatte agent-worktrees. Kjøres fra §6d i coordinator-runbook.md.
#
# Hvorfor denne finnes ved siden av §0b: §0b er en PER-RUNDE sikkerhetsgate med seks vakter som
# med rette feiler LUKKET — ved enhver advarsel er utfallet «INGEN rydding». Det gjør at trær
# hoper seg opp hver gang en agent dør, avbrytes eller etterlater en foreldreløs lås. Sweepen er
# ikke en svakere §0b; den har et ANNET og strengere-å-verifisere kriterium: et tre fjernes kun
# når ingenting i det kan gå tapt.
#
# Kriterium (alle må holde):
#   1. treet ligger under .claude/worktrees/
#   2. HEAD finnes på en remote branch, ELLER innholdet er bevist LANDET av
#      tasks/worktree-landed.sh (squash-merge/omdøping/arkivering — se den fila)
#   3. treet er rent, ELLER klassifikatoren sier LANDED — «fanget til RESCUE_DIR» er IKKE
#      lenger nok alene til å tillate sletting (se § 4b punkt 3 i planen)
#   4. en eventuell lås peker IKKE på en levende prosess
#   5. ingen ÅPEN PR bærer denne worktreens HEAD (verken via branch-navn eller commit-ancestry)
#   6. worktreens filer er ikke rørt de siste $AGE_MIN minuttene (default 1440 — se planens § 0b
#      om hvorfor IKKE 60: en levende, TENKENDE agent kan gå 60+ min uten å skrive) — hoppes over
#      i navngitt kjøring (TODO 401)
#
# Moduser:
#   (ingen flagg)     destruktiv kjøring — fjerner kvalifiserte trær
#   --dry-run         rapporterer uten å fjerne noe
#   --gate            verifiserer at sweepen har kjørt siden forrige §6-rad; sletter ALDRI
#   agent-<id> …      (TODO 401) navngitt kjøring: KUN de oppgitte trærne vurderes, og
#                     aldersvakten (kriterium 6) hoppes over for dem — alle andre vakter og
#                     redningen gjelder uendret. Et navn uten tre gir «IKKE FUNNET <navn>».
#                     Oppsummeringslinja bruker `wtsweep_named=`/`wtsweep_named_dry=`, ALDRI
#                     `wtsweep=` — kan kombineres med --dry-run, ikke med --gate.
#
# Denne fila skal ALDRI omdirigere stderr til null-enheten — se
# tasks/plans/todo-380-loopen-rydder-aldri-worktrees.md, dispatch-regelen. En kommandofeil skal
# være SYNLIG som feil, aldri en stille "ingen treff".
set -uo pipefail

DRY=0
GATE=0
NAMES=""
for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY=1 ;;
    --gate) GATE=1 ;;
    agent-|agent-*[!A-Za-z0-9_-]*)
      # Fix-runde 1 (VIKTIG, PR #980 kode-review r1): `agent-*` er et GLOB-mønster og matcher
      # derfor ALT som starter med «agent-», inkludert ETT argument som inneholder mellomrom
      # (f.eks. "agent-x graphify-…") eller en bokstavelig «*» (uekspandert p.g.a. sitering). Et
      # slikt argument delte seg opp i flere "navn" i NAMES-listen og kunne la et ikke-agent-tre
      # miste vakt 6. Denne grenen fanger ethvert tegn utenfor [A-Za-z0-9_-] etter «agent-» —
      # inkludert den tomme resten («agent-» alene) — og avviser høylytt FØR agent-*-grenen under.
      echo "UKJENT FLAGG: $arg (gyldig: --dry-run, --gate, agent-<id> …)"
      exit 2
      ;;
    agent-*) NAMES="$NAMES $arg " ;;
    *)
      echo "UKJENT FLAGG: $arg (gyldig: --dry-run, --gate, agent-<id> …)"
      exit 2
      ;;
  esac
done

# Fix-runde 1 (MINDRE, PR #980 kode-review r1): `--gate` sletter aldri noe og leser KUN
# `wtsweep=` — å kombinere den med agent-<id> ville stille antyde at gaten også dekker den
# navngitte kjøringen (den gjør aldri det, se `tok`-beregningen under). Avvis kombinasjonen
# høylytt i stedet for å la den stille ignorere navnene.
if [ "$GATE" -eq 1 ] && [ -n "$NAMES" ]; then
  echo "UKJENT FLAGG: --gate kan ikke kombineres med agent-<id> (--gate leser kun wtsweep=, aldri wtsweep_named=; bruk --dry-run eller ingen flagg for navngitt kjøring)"
  exit 2
fi

REPO_ROOT=$(git rev-parse --show-toplevel) || exit 1
cd "$REPO_ROOT" || exit 1

REF="origin/{{BASE_BRANCH}}"
AGE_MIN="${AGE_MIN:-1440}"
# Overstyrbar KUN for test-harnesser (V4c stubber klassifikatoren til rc 127); i normal drift
# er default alltid riktig sti i dette repoet.
LANDED_SCRIPT="${LANDED_SCRIPT_OVERRIDE:-$REPO_ROOT/tasks/worktree-landed.sh}"
SWEEP_LOG="$REPO_ROOT/tasks/metrics/worktree-sweep-log.jsonl"
RUNLOG="$REPO_ROOT/docs/superpowers/loop/run-log.md"
RESCUE_DIR=".claude/worktree-rescue/$(date +%Y-%m-%dT%H%M%S)"

# ---------------------------------------------------------------------------
# --gate: token-basert, IKKE tidsstempel-basert (fix-runde 2, B1) — en tidsstempel-
# sammenligning er strukturelt sårbar selv når sweepen (§6 steg 4b) kjører FØR raden
# skrives (§6 steg 5) i SAMME syklus: skriver steg 5 raden i et senere minutt enn
# sweepens egen "ts", er sweepens tidsstempel BY CONSTRUCTION eldre — falskt RØDT på
# en sweep som faktisk kjørte. Gaten leser derfor kun INNHOLDET i siste §6-rad i
# run-log.md og krever at raden bærer et `wtsweep=<n>/<n>`-token, skrevet inn
# SAMTIDIG med resten av raden (§6 steg 4b/5, ikke ettermontert).
#
# Radfilteret er POSITIVT (fix-runde 3, mikro): kun rader med outcome=`merged`
# (literalen `| merged |`) teller som «siste §6-rad». Et negativt filter
# (`grep -v health`) ble forkastet fordi kolonne 4 på {{BASE_BRANCH}} også har `paused` (20),
# `resumed` (5) og `housekeeping` (1) i tillegg til `health` (19) og `merged` (113) —
# disse tre radtypene skriver ikke nødvendigvis `wtsweep=` (§6 steg 4b eies av
# MERGE-syklusen), og et negativt filter ville latt en paused/resumed/housekeeping-
# rad telle som siste §6-rad og gitt falskt RØDT.
#
# Token til stede og velformet ⇒ GRØNN. Token helt FRAVÆRENDE (§6 steg 4b ble ikke
# kjørt/skrevet) ⇒ RØD. ENHVER `wtsweep=`-forekomst i raden som ikke matcher
# `^wtsweep=[0-9]+/[0-9]+$` ⇒ RØD, selv om en SENERE forekomst i samme rad er
# velformet (fix-runde 3, mikro — kun å sjekke SISTE forekomst lot
# `wtsweep=feilet:x; … wtsweep=3/1` gi GRØNN). `--dry-run` skriver `wtsweep_dry=`,
# ALDRI `wtsweep=`, i sin oppsummeringslinje — et dry-run-token kan derfor aldri
# forveksles med et ekte, og teller ikke som noen `wtsweep=`-forekomst i det hele
# tatt (understrengen `wtsweep=` finnes ikke i `wtsweep_dry=`).
# Ingen §6-rad ennå (fersk run-log, ingen merged-rad ennå) ⇒ GRØNN — ingenting å
# måle mot. `tasks/metrics/worktree-sweep-log.jsonl` er REN DIAGNOSTIKK og leses
# ikke av gaten. Sletter ALDRI.
# ---------------------------------------------------------------------------
if [ "$GATE" -eq 1 ]; then
  if [ ! -f "$RUNLOG" ]; then
    echo "GATE RØD — run-log.md mangler ($RUNLOG)"
    exit 1
  fi
  last_row=$(grep -E '^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}' "$RUNLOG" | grep -F '| merged |' | tail -1)
  if [ -z "$last_row" ]; then
    echo "GATE GRØNN — ingen §6-rad ennå (fersk run-log, ingen merged-rad ennå); ingenting å kreve sweep mot"
    exit 0
  fi
  tokens=$(printf '%s\n' "$last_row" | grep -oE 'wtsweep=[^[:space:];]*')
  if [ -z "$tokens" ]; then
    echo "GATE RØD — siste §6-rad mangler wtsweep=-token (§6 steg 4b ble ikke kjørt/skrevet): $last_row"
    exit 1
  fi
  bad_token=""
  while IFS= read -r t; do
    [ -z "$t" ] && continue
    if ! printf '%s' "$t" | grep -Eq '^wtsweep=[0-9]+/[0-9]+$'; then
      bad_token="$t"
    fi
  done <<EOF
$tokens
EOF
  if [ -n "$bad_token" ]; then
    echo "GATE RØD — wtsweep-token er ikke velformet ($bad_token) i siste §6-rad: $last_row"
    exit 1
  fi
  last_token=$(printf '%s\n' "$tokens" | tail -1)
  echo "GATE GRØNN — siste §6-rad bærer $last_token"
  exit 0
fi

# ---------------------------------------------------------------------------
# Vakt 5-oppsett: åpne PR-er, OID-basert. Feiler HELE sweepen lukket (ingen sletting).
# ---------------------------------------------------------------------------
TMP=$(mktemp -d) || exit 1
trap 'rm -rf "$TMP"' EXIT

if ! git fetch origin -q; then
  echo "AVBRUTT — git fetch origin feilet; kan ikke verifisere åpne PR-er trygt. Ingen sletting."
  exit 1
fi

if ! command -v gh > /dev/null; then
  echo "AVBRUTT — gh mangler; kan ikke verifisere åpne PR-er trygt. Ingen sletting."
  exit 1
fi
if ! command -v jq > /dev/null; then
  echo "AVBRUTT — jq mangler; kan ikke parse gh pr list trygt. Ingen sletting."
  exit 1
fi

if ! pr_json=$(gh pr list --state open --json headRefName,headRefOid --limit 200); then
  echo "AVBRUTT — gh pr list feilet. Ingen sletting denne kjøringen."
  exit 1
fi
if ! pr_count=$(printf '%s' "$pr_json" | jq 'length'); then
  echo "AVBRUTT — jq kunne ikke telle gh pr list-resultatet. Ingen sletting."
  exit 1
fi
case "$pr_count" in
  '' | *[!0-9]*)
    echo "AVBRUTT — pr_count er ikke et tall ($pr_count). Ingen sletting."
    exit 1
    ;;
esac
if [ "$pr_count" -ge 200 ]; then
  echo "AVBRUTT — gh pr list traff taket (>=200 åpne PR-er); listen er ikke komplett. Ingen sletting."
  exit 1
fi
printf '%s' "$pr_json" | jq -r '.[] | "\(.headRefName)\t\(.headRefOid)"' > "$TMP/open-prs.tsv"

removed=0; kept=0; rescued=0
seen=" "

while IFS= read -r p; do
  [ -z "$p" ] && continue
  [ "$p" = "$PWD" ] && continue
  case "$p" in *"/.claude/worktrees/"*) ;; *) continue ;; esac
  n=$(basename "$p")

  # Navngitt kjøring (§6 steg 4b, TODO 401): KUN de navngitte trærne vurderes.
  if [ -n "$NAMES" ]; then
    case "$NAMES" in *" $n "*) seen="$seen$n " ;; *) continue ;; esac
  fi

  # Vakt 1: treet finnes fortsatt på disk.
  if [ ! -d "$p" ]; then
    echo "PRUNE    $n — mangler på disk"
    [ $DRY -eq 0 ] && git worktree prune
    continue
  fi

  # Vakt 4: lås som peker på en LEVENDE prosess respekteres. Literal streng (-F), 5 linjer
  # etter «worktree $p» — dekker også detached HEAD (som har en ekstra linje før «locked»).
  lock_block=$(git worktree list --porcelain | grep -F -A5 "worktree $p")
  lockpid=$(printf '%s\n' "$lock_block" | sed -n 's/^locked .*pid \([0-9]*\).*/\1/p' | head -1)
  if [ -n "$lockpid" ] && ps -p "$lockpid" > /dev/null; then
    echo "BEHOLDT  $n — låst av levende pid $lockpid"
    kept=$((kept + 1))
    continue
  fi

  # Vakt 5: åpen PR bærer denne worktreens HEAD — via branch-navn ELLER commit-ancestry.
  if ! wt_branch=$(git -C "$p" rev-parse --abbrev-ref HEAD); then
    echo "BEHOLDT  $n — rev-parse (branch) feilet"
    kept=$((kept + 1))
    continue
  fi
  if ! wt_head=$(git -C "$p" rev-parse HEAD); then
    echo "BEHOLDT  $n — rev-parse (HEAD) feilet"
    kept=$((kept + 1))
    continue
  fi
  # OID-ancestry-grenen under skal KUN telle som treff når wt_head IKKE allerede er
  # forgjenger til $REF (oppfølging 2, TODO 380): er wt_head inneholdt i {{BASE_BRANCH}}, er `git
  # merge-base --is-ancestor "$wt_head" "$proid"` sann for ENHVER åpen PR laget fra {{BASE_BRANCH}} —
  # en hvilken som helst {{BASE_BRANCH}}-basert PR "inneholder" enhver {{BASE_BRANCH}}-commit i sin historikk. Det
  # gir et falskt treff (treet fremstår som «bærer HEAD for en åpen PR») så lenge minst
  # én PR er åpen, altså i praksis alltid — målt på et 380-planlegger-tre hvis HEAD var en
  # vanlig {{BASE_BRANCH}}-commit. Er wt_head i {{BASE_BRANCH}}, kan ingen åpen PR være avhengig av NETTOPP dette
  # treet på en unik måte, og OID-sjekken hopper derfor over — treet faller videre til de
  # neste vaktene (klassifikator, mtime, osv.). Navnegrenen (branch-navn = PR-ens
  # headRefName) er UENDRET og gjelder uansett.
  git merge-base --is-ancestor "$wt_head" "$REF"
  wt_in_dev_rc=$?
  if [ "$wt_in_dev_rc" -ge 2 ]; then
    echo "BEHOLDT  $n — {{BASE_BRANCH}}-ancestry-sjekk feilet (usikkert utfall)"
    kept=$((kept + 1))
    continue
  fi
  wt_head_in_dev=0
  [ "$wt_in_dev_rc" -eq 0 ] && wt_head_in_dev=1
  open_pr_hit=0
  open_pr_err=0
  while IFS=$'\t' read -r prname proid; do
    [ -z "$prname" ] && continue
    if [ "$wt_branch" = "$prname" ]; then
      open_pr_hit=1
      break
    fi
    if [ "$wt_head_in_dev" -eq 1 ]; then
      continue
    fi
    git merge-base --is-ancestor "$wt_head" "$proid"
    mb_rc=$?
    if [ "$mb_rc" -eq 0 ]; then
      open_pr_hit=1
      break
    elif [ "$mb_rc" -ge 2 ]; then
      open_pr_err=1
    fi
  done < "$TMP/open-prs.tsv"
  if [ "$open_pr_hit" -eq 1 ]; then
    echo "BEHOLDT  $n — bærer HEAD/branch for en åpen PR"
    kept=$((kept + 1))
    continue
  fi
  if [ "$open_pr_err" -eq 1 ]; then
    echo "BEHOLDT  $n — ancestry-sjekk mot en åpen PR feilet (usikkert utfall)"
    kept=$((kept + 1))
    continue
  fi

  # Vakt 2: HEAD finnes på en remote branch ⇒ ingen commit kan gå tapt via ren SHA-sjekk.
  head_on_remote=0
  if remote_hits=$(git branch -r --contains "$wt_head"); then
    [ -n "$remote_hits" ] && head_on_remote=1
  else
    echo "BEHOLDT  $n — branch -r --contains feilet"
    kept=$((kept + 1))
    continue
  fi

  # Vakt 3: skittenhet.
  if ! dirty_out=$(git -C "$p" status --porcelain -uall); then
    echo "BEHOLDT  $n — status feilet"
    kept=$((kept + 1))
    continue
  fi
  dirty=0
  [ -n "$dirty_out" ] && dirty=1

  landed_moved_list=""
  if [ "$head_on_remote" -eq 1 ] && [ "$dirty" -eq 0 ]; then
    # rask vei — commit er kjent trygg, og ingenting uncommittet å tape. MEN
    # `status --porcelain` ser ALDRI ignorerte filer (fix-runde 1, R2) — uten denne
    # sjekken ville `worktree remove --force` fortsatt kunne slette en ignorert fil
    # utenfor allowlisten (f.eks. .env.local/*.log) selv om treet ellers er «rent».
    # Meldingsprefikset er BEVISST forskjellig fra den fulle klassifikator-grenen under
    # (fix-runde 3, mikro, punkt 2) — «klassifikator:» er reservert for den FULLE
    # `bash "$LANDED_SCRIPT" "$p" --ref "$REF"`-kjøringen, slik at et testtilfelle kan
    # bekrefte at DEN RASKE VEIEN faktisk ble tatt (og ikke falt gjennom til fallbacken).
    ignored_out=$(bash "$LANDED_SCRIPT" "$p" --ref "$REF" --ignored-only)
    ignored_rc=$?
    if [ "$ignored_rc" -ne 0 ]; then
      reason=$(printf '%s\n' "$ignored_out" | tail -1)
      echo "BEHOLDT  $n — ignorert-fil (rask vei): $reason"
      kept=$((kept + 1))
      continue
    fi
  else
    # Klassifikator-gren (§ 4b punkt 3): rc = 0 ⇒ fjern; alt annet ⇒ BEHOLD. Fangsten under er
    # ren dokumentasjon og gir ALDRI i seg selv lov til å slette.
    classifier_out=$(bash "$LANDED_SCRIPT" "$p" --ref "$REF")
    classifier_rc=$?
    if [ "$classifier_rc" -ne 0 ]; then
      reason=$(printf '%s\n' "$classifier_out" | tail -1)
      echo "BEHOLDT  $n — klassifikator: $reason"
      kept=$((kept + 1))
      continue
    fi
    landed_moved_list=$(printf '%s\n' "$classifier_out" | sed -n 's/^LANDED-MOVED://p')
  fi

  # Vakt 6 — ikke rørt siste $AGE_MIN minutter. Siste linje i forsvar mot en agent som
  # fortsatt leser/tenker uten å skrive. rc != 0 fra find ⇒ BEHOLD.
  if [ -z "$NAMES" ]; then
    recent=$(find "$p" -type f \
      ! -path "$p/.git" \
      ! -path "*/node_modules/*" \
      ! -path "*/test-results/*" \
      ! -path "*/playwright-report/*" \
      ! -path "*/.expo/*" \
      ! -path "*/dist/*" \
      ! -path "*/__pycache__/*" \
      ! -path "*/supabase/.temp/*" \
      -mmin -"$AGE_MIN" -print -quit)
    find_rc=$?
  else
    # Navngitt kjøring: agentene har returnert. AGE_MIN=0 er IKKE «av» (-mmin -0 treffer ferske
    # og fremtidsdaterte filer), så vakten hoppes over eksplisitt.
    recent=""
    find_rc=0
  fi
  if [ "$find_rc" -ne 0 ]; then
    echo "BEHOLDT  $n — mtime-sjekk (find) feilet"
    kept=$((kept + 1))
    continue
  fi
  if [ -n "$recent" ]; then
    mtime_epoch=$(stat -f %m "$recent" 2>"$TMP/stat.err") || mtime_epoch=""
    if [ -n "$mtime_epoch" ]; then
      mins_ago=$(((($(date +%s) - mtime_epoch)) / 60))
      echo "BEHOLDT  $n — rørt for $mins_ago min siden ($recent)"
    else
      echo "BEHOLDT  $n — rørt innenfor $AGE_MIN min ($recent)"
    fi
    kept=$((kept + 1))
    continue
  fi

  # Redning av landed-moved-filer FØR fjerning (r2 VIKTIG-4) — verifisert med cmp -s.
  # Ett pass: teller alltid; kopierer+verifiserer kun i en faktisk (ikke-dry) kjøring.
  moved_count=0
  rescue_ok=1
  if [ -n "$landed_moved_list" ]; then
    while IFS= read -r moved; do
      [ -z "$moved" ] && continue
      moved_count=$((moved_count + 1))
      if [ $DRY -eq 0 ]; then
        mkdir -p "$RESCUE_DIR/$n/$(dirname "$moved")"
        cp "$p/$moved" "$RESCUE_DIR/$n/$moved"
        cmp -s "$p/$moved" "$RESCUE_DIR/$n/$moved" || rescue_ok=0
      fi
    done <<EOF
$landed_moved_list
EOF
  fi

  if [ $DRY -eq 1 ]; then
    echo "VILLE FJERNET $n${dirty:+ (dirty=$dirty)} redning=$moved_count"
    continue
  fi

  if [ "$rescue_ok" -ne 1 ]; then
    echo "BEHOLDT  $n — redning av landed-moved-fil(er) kunne ikke verifiseres"
    kept=$((kept + 1))
    continue
  fi
  [ "$moved_count" -gt 0 ] && rescued=$((rescued + moved_count))

  [ -n "$lockpid" ] && git worktree unlock "$p"
  if git worktree remove --force "$p"; then
    echo "FJERNET  $n"
    removed=$((removed + 1))
  else
    echo "BEHOLDT  $n — remove feilet"
    kept=$((kept + 1))
  fi
done < <(git worktree list --porcelain | awk '/^worktree /{p=$2} /^$/{if(p!="")print p; p=""}')

for name in $NAMES; do
  case "$seen" in *" $name "*) ;; *) echo "IKKE FUNNET $name" ;; esac
done

[ $DRY -eq 0 ] && git worktree prune

echo "---"
# wtsweep= (ekte kjøring) vs. wtsweep_dry= (--dry-run) — fix-runde 3, mikro, punkt 4: gaten skal
# ALDRI kunne forveksle et dry-run-tall med bevis på at sweepen faktisk fjernet noe.
# wtsweep_named= (navngitt kjøring, TODO 401) er en egen understreng som ALDRI inneholder
# `wtsweep=` — gaten (som leser KUN `wtsweep=`) kan derfor verken bli grønn eller rød av den.
tok=wtsweep
[ -n "$NAMES" ] && tok=wtsweep_named
[ $DRY -eq 1 ] && tok="${tok}_dry"
echo "$tok=$removed/$kept  rescued=$rescued  wt_igjen=$(git worktree list | wc -l | tr -d ' ')  disk_ledig=$(df -h / | tail -1 | awk '{print $4}')"
[ -d "$RESCUE_DIR" ] && echo "rescue=$RESCUE_DIR (gitignorert — commit den hvis noe der er ekte arbeid)"

if [ $DRY -eq 0 ] && [ -z "$NAMES" ]; then
  mkdir -p "$(dirname "$SWEEP_LOG")"
  ts=$(date +%Y-%m-%dT%H:%M)
  printf '{"ts":"%s","removed":%d,"kept":%d,"rescued":%d}\n' "$ts" "$removed" "$kept" "$rescued" >> "$SWEEP_LOG"
fi
