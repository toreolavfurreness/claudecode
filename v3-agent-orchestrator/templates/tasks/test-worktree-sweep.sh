#!/usr/bin/env bash
# Harness for tasks/worktree-sweep.sh — dekker § 7 V3-V6 (åpen-PR-vakt, fail-safe-batteri,
# bevarte vakter/gate/AGE_MIN, klassifikator-kallsted+redning) og mutantene M5/M6/M7/M8/M11 (§ 8).
# M5 (klassifikator-kallsted fjernet, fallgjennom-form) ble erstattet av M7 i fix-runde 2, men er
# GJENINNFØRT i fix-runde 3 (mikro) ved siden av M7 — eierbeslutning: mutantbudsjettet er utvidet
# fra 6 til 8 for DENNE PR-en (M1, M2P, M3P, M4, M5, M6, M7, M8). M8 er nytt i fix-runde 3 og
# dekker den raske veien i sweepen (--ignored-only-kallet nøytralisert). Se planens
# fix-runde 3-seksjon for begge begrunnelsene.
#
# M9/M10 (env-delmengde) ble lagt til i tasks/test-worktree-landed.sh (oppfølging 1),
# ikke i DENNE fila — M-nummereringen er delt på tvers av de to harnessene. M11 (under, V3(c))
# er oppfølging 2: OID-ancestry-grenen i vakt 5 ga falskt treff når wt_head allerede var
# forgjenger til {{BASE_BRANCH}}, siden `git merge-base --is-ancestor` da er sann for ENHVER åpen PR laget
# fra {{BASE_BRANCH}}.
# N-blokken dekker navngitt kjøring (agent-<id> …): aldersvakten hoppes over kun for
# navngitte trær, lås/åpen-PR-vaktene gjelder uendret, et navn uten tre gir «IKKE FUNNET», og
# oppsummeringslinja bruker wtsweep_named=/wtsweep_named_dry= — aldri wtsweep=. D-seksjonen
# beviser at docker aldri blokkerer sweepen (global stub, ingen ekte docker-CLI kalles noe sted i
# denne fila).
#
# Sjekket inn (fix-runde 1, R5) etter at et scratchpad-only harness i en tidligere runde
# hadde en NÆRLIGGENDE feil: worktree-sweep.sh finner sitt eget REPO_ROOT via
# `git rev-parse --show-toplevel` (PWD-avhengig, ikke sti-argument-avhengig). Uten en hard
# vakt FØR ethvert ikke-dry-run-kall kunne et cd-glipp latt harnesset kjøre mot AGENTENS EGEN
# ekte worktree i stedet for engangsrepoet. Denne fila bærer den vakten permanent, i stedet
# for å stole på disiplin i en engangs-prompt.
#
# Bruk: tasks/test-worktree-sweep.sh
# Utskrift: sitat av hver test + "TESTS_OK" til slutt. Exit 0 kun hvis ALLE tester passerte.
set -uo pipefail

REPO_ROOT=$(git rev-parse --show-toplevel) || { echo "HARNESS-FEIL:oppsett:repo-root"; exit 2; }
SWEEP_SRC="$REPO_ROOT/tasks/worktree-sweep.sh"
LANDED_SRC="$REPO_ROOT/tasks/worktree-landed.sh"

SANDBOX_ROOT=$(mktemp -d) || { echo "HARNESS-FEIL:oppsett:mktemp-sandbox"; exit 2; }
SANDBOX_ROOT=$(cd "$SANDBOX_ROOT" && pwd -P)
FAKEBIN="$SANDBOX_ROOT/.fakebin"
mkdir -p "$FAKEBIN"
trap 'rm -rf "$SANDBOX_ROOT"' EXIT

# global docker-stub. Ingen kjøring i denne harnessen skal noensinne kalle den ekte
# docker-CLI-en (M4 målte en ~50 min heng mot en hengende daemon) — stubben skriver en markør
# (D0/D1 under) i stedet for å berøre disk.
DOCKER_MARK="$SANDBOX_ROOT/docker-called.log"
cat > "$FAKEBIN/docker" <<EOF
#!/usr/bin/env bash
echo "\$*" >> "$DOCKER_MARK"
sleep 5
EOF
chmod +x "$FAKEBIN/docker"

all_ok=1
fail() {
  echo "FEIL: $1"
  all_ok=0
}

# ---------------------------------------------------------------------------
# R5 — hard sandkasse-vakt. Kalles FØR ethvert kall til worktree-sweep.sh, UANSETT flagg
# (fix-runde 2, MINDRE: også `--gate`-kall rutes nå gjennom `run_sweep`, selv om `--gate` aldri
# sletter noe — konsistens er billigere enn å holde et unntak fra vakten i live). Sammenligner
# BÅDE `pwd -P` og git sin egen `--show-toplevel`-resolusjon mot sandkasse-roten.
# ---------------------------------------------------------------------------
assert_in_sandbox() {
  work="$1"
  case "$work" in
    "$SANDBOX_ROOT"/*) : ;;
    *)
      echo "GUARD-FEIL: fixture-sti $work er UTENFOR sandkassen $SANDBOX_ROOT — avbryter" >&2
      exit 2
      ;;
  esac
  real_top=$(cd "$work" && git rev-parse --show-toplevel) || { echo "GUARD-FEIL: git rev-parse --show-toplevel feilet for $work" >&2; exit 2; }
  real_top_phys=$(cd "$real_top" && pwd -P)
  case "$real_top_phys" in
    "$SANDBOX_ROOT"/*) : ;;
    *)
      echo "GUARD-FEIL: git-toplevel $real_top_phys for $work er UTENFOR sandkassen $SANDBOX_ROOT — avbryter FØR kjøring" >&2
      exit 2
      ;;
  esac
}

backdate_wt() {
  find "$1" -type f -exec touch -t 202001010000 {} \;
}

mkgh() {
  # $1 = fixture-fil (JSON), $2 = rc
  cat > "$FAKEBIN/gh" <<EOF
#!/usr/bin/env bash
if [ "\$1" = "pr" ] && [ "\$2" = "list" ]; then
  cat "$1"
  exit $2
fi
exit 1
EOF
  chmod +x "$FAKEBIN/gh"
}

new_harness() {
  # $1 = varname som mottar arbeidstre-stien
  bare=$(mktemp -d -p "$SANDBOX_ROOT")
  git init --bare -q "$bare/origin.git"
  work=$(mktemp -d -p "$SANDBOX_ROOT")
  work=$(cd "$work" && pwd -P)
  git init -q -b {{BASE_BRANCH}} "$work"
  git -C "$work" remote add origin "$bare/origin.git"
  git -C "$work" config user.email test@example.com
  git -C "$work" config user.name "Test Harness"
  mkdir -p "$work/tasks" "$work/docs/superpowers/loop" "$work/tasks/metrics"
  cp "$SWEEP_SRC" "$work/tasks/worktree-sweep.sh"
  cp "$LANDED_SRC" "$work/tasks/worktree-landed.sh"
  chmod +x "$work/tasks/worktree-sweep.sh" "$work/tasks/worktree-landed.sh"
  printf 'seed\n' > "$work/README.md"
  git -C "$work" add -A
  git -C "$work" commit -q -m seed
  git -C "$work" push -q -u origin {{BASE_BRANCH}}
  assert_in_sandbox "$work"
  eval "$1=\"\$work\""
}

run_sweep() {
  # run_sweep <workdir> <extra-args...> — ALLTID gjennom sandkasse-vakten, uansett flagg.
  work="$1"
  shift
  assert_in_sandbox "$work"
  ( cd "$work" && PATH="$FAKEBIN:$PATH" AGE_MIN="${AGE_MIN_OVERRIDE:-0}" LANDED_SCRIPT_OVERRIDE="${LANDED_SCRIPT_OVERRIDE:-}" bash tasks/worktree-sweep.sh "$@" 2>&1 )
}

apply_mutant() {
  # apply_mutant <workdir> <python-heredoc-fil>
  work="$1"; py="$2"
  python3 "$py" "$work/tasks/worktree-sweep.sh"
  if diff -q "$SWEEP_SRC" "$work/tasks/worktree-sweep.sh" > /dev/null; then
    fail "mutant traff ikke: $py"
    return 1
  fi
  echo "--- mutant-diff (bekrefter treff) ---"
  diff -u "$SWEEP_SRC" "$work/tasks/worktree-sweep.sh" || true
  echo "--- slutt diff ---"
}

echo "############ V3 — åpen PR-vakt (R6: navn-only vs OID-only, disjunkte caser) ############"
new_harness W3
# (a) case-a matcher UTELUKKENDE på branch-NAVN: HEAD er IKKE ancestor av noen åpen PRs OID.
git -C "$W3" checkout -q -b case-a {{BASE_BRANCH}}
echo "case-a own work" > "$W3/case-a-only.txt"
git -C "$W3" add -A
git -C "$W3" commit -q -m "case-a: eget arbeid, ikke i noen åpen PRs ancestry"
# Pushet til origin (vakt 2, head_on_remote) — UAVHENGIG av vakt 5 (åpen-PR). Slik isolerer M6
# (som kun fjerner vakt 5) presist: uten push ville M6(a) falle videre til klassifikatoren og
# feile med «ingen-treff» i stedet for å bevise at DET var vakt 5 som holdt treet BEHOLDT.
git -C "$W3" push -q -u origin case-a
# decoy: en EKTE, eksisterende commit i SAMME repo som IKKE er ancestor av case-a (fix-runde 2,
# MINDRE — en fiktiv 40-tegns OID i fixturen risikerte at `git merge-base --is-ancestor` en dag
# fikk kalles med en SHA som ikke finnes i objektbasen i det hele tatt; en ekte, ikke-relatert
# commit gjør testen robust mot at navnetreff-kortslutningen i loopen under noen gang endres).
git -C "$W3" checkout -q -b decoy {{BASE_BRANCH}}
echo "decoy: eksisterer i repoet, men usett av case-a" > "$W3/decoy.txt"
git -C "$W3" add -A
git -C "$W3" commit -q -m "decoy: ekte commit, ikke ancestor av case-a"
decoy_oid=$(git -C "$W3" rev-parse decoy)
git -C "$W3" checkout -q {{BASE_BRANCH}}
git -C "$W3" worktree add -q ".claude/worktrees/case-a" case-a
backdate_wt "$W3/.claude/worktrees/case-a"
head_a=$(git -C "$W3" rev-parse case-a)
# headRefOid i fixture er decoy-committen (EKTE, finnes i repoet, men ikke ancestor av head_a) —
# kun navnet skal treffe.
printf '[{"headRefName":"case-a","headRefOid":"%s"}]\n' "$decoy_oid" > "$W3/pr-fixture.json"
mkgh "$W3/pr-fixture.json" 0
out=$(run_sweep "$W3" --dry-run)
echo "FULLOUT>>>"
echo "$out"
echo "<<<FULLOUT"
if printf '%s' "$out" | grep -qF "BEHOLDT  case-a — bærer HEAD/branch for en åpen PR"; then
  echo "V3(a)=PASS (navn-only)"
else
  fail "V3(a): case-a ikke BEHOLDT via navnetreff"
fi

# (b) case-b matcher UTELUKKENDE på OID-ancestry: branch-navnet er et ANNET navn enn PR-ens
# headRefName, men HEAD er ancestor av en åpen PRs headRefOid.
new_harness W3b
git -C "$W3b" checkout -q -b feat/upstream-name {{BASE_BRANCH}}
echo change > "$W3b/upstream.txt"
git -C "$W3b" add -A
git -C "$W3b" commit -q -m "upstream work"
git -C "$W3b" push -q -u origin feat/upstream-name
upstream_head=$(git -C "$W3b" rev-parse feat/upstream-name)
git -C "$W3b" checkout -q {{BASE_BRANCH}}
git -C "$W3b" branch fix-local-round2 "$upstream_head"
git -C "$W3b" worktree add -q ".claude/worktrees/case-b" fix-local-round2
backdate_wt "$W3b/.claude/worktrees/case-b"
printf '[{"headRefName":"feat/upstream-name","headRefOid":"%s"}]\n' "$upstream_head" > "$W3b/pr-fixture.json"
mkgh "$W3b/pr-fixture.json" 0
out=$(run_sweep "$W3b" --dry-run)
echo "FULLOUT>>>"
echo "$out"
echo "<<<FULLOUT"
if printf '%s' "$out" | grep -qF "BEHOLDT  case-b — bærer HEAD/branch for en åpen PR"; then
  echo "V3(b)=PASS (OID-only)"
else
  fail "V3(b): case-b ikke BEHOLDT via OID-ancestry"
fi

# (c) wt_head er ALLEREDE forgjenger til {{BASE_BRANCH}} (målt: et planlegger-
# tre hvis HEAD var en vanlig {{BASE_BRANCH}}-commit ble BEHOLDT for alltid fordi `git merge-base
# --is-ancestor "$wt_head" "$proid"` er sann for ENHVER åpen PR laget fra {{BASE_BRANCH}}). case-c sin branch
# har INGEN nye commits oppå {{BASE_BRANCH}} — HEAD ER {{BASE_BRANCH}} sin HEAD. Den åpne PR-en (stub) er et ANNET navn
# enn case-c, med et hode som BYGGER PÅ {{BASE_BRANCH}} (en ny commit oppå {{BASE_BRANCH}}). Uten {{BASE_BRANCH}}-ancestry-unntaket
# ville OID-sjekken (case-c sin HEAD er ancestor av PR-ens hode, siden PR-ens hode er en
# etterkommer av nettopp den {{BASE_BRANCH}}-committen) gitt et falskt treff. Treet skal IKKE beholdes av
# vakt 5 — forventet utfall her er et rent, ubrukt tre som faller helt gjennom til VILLE FJERNET.
new_harness W3c
git -C "$W3c" branch case-c {{BASE_BRANCH}}
# Den åpne PR-ens (stub) egen commit lages FØR case-c sin worktree (samme rekkefølge-
# disiplin som case-a/case-b: worktree add er ALLTID siste git-operasjon på hovedtreet) —
# ellers plukker `git add -A` under opp den allerede eksisterende nested worktree-katalogen
# som et embedded repo.
git -C "$W3c" checkout -q -b other-open-pr {{BASE_BRANCH}}
echo "en annen, åpen PR sitt eget arbeid" > "$W3c/other-pr.txt"
git -C "$W3c" add -A
git -C "$W3c" commit -q -m "annen åpen PR: ny commit oppå {{BASE_BRANCH}}"
git -C "$W3c" push -q -u origin other-open-pr
other_pr_head=$(git -C "$W3c" rev-parse other-open-pr)
git -C "$W3c" checkout -q {{BASE_BRANCH}}
git -C "$W3c" worktree add -q ".claude/worktrees/case-c" case-c
backdate_wt "$W3c/.claude/worktrees/case-c"
printf '[{"headRefName":"other-open-pr","headRefOid":"%s"}]\n' "$other_pr_head" > "$W3c/pr-fixture.json"
mkgh "$W3c/pr-fixture.json" 0
out=$(run_sweep "$W3c" --dry-run)
echo "FULLOUT>>>"
echo "$out"
echo "<<<FULLOUT"
if printf '%s' "$out" | grep -qF "BEHOLDT  case-c — bærer HEAD/branch for en åpen PR"; then
  fail "V3(c): case-c ble FORTSATT feilaktig BEHOLDT via OID-ancestry mot en {{BASE_BRANCH}}-basert PR"
elif printf '%s' "$out" | grep -qF "VILLE FJERNET case-c"; then
  echo "V3(c)=PASS ({{BASE_BRANCH}}-ancestry-unntaket hindret falskt treff — treet falt gjennom til VILLE FJERNET)"
else
  fail "V3(c): uventet utfall (verken det gamle falske treffet eller VILLE FJERNET) — se FULLOUT over"
fi

echo "############ M6 — hele åpen-PR-vakten fjernet (fix-runde 1, R6: navn+OID i ÉN mutant) ############"
# R6: forrige runde fjernet KUN OID-grenen, og case-a flippet likevel — bevis på at case-a IKKE
# faktisk var navn-only konstruert. Nå som case-a/case-b er disjunkte (over), utvider vi M6 til
# å fjerne BEGGE grenene i ÉN mutant (holder mutantbudsjettet på 6 i stedet for å legge til en
# syvende) — begge caser SKAL da flippe til VILLE FJERNET.
cat > "$SANDBOX_ROOT/mutate-m6.py" <<'PY'
import sys
p = sys.argv[1]
s = open(p).read()
marker_start = '  open_pr_hit=0\n  open_pr_err=0\n  while IFS=$\'\\t\' read -r prname proid; do'
marker_end = '  done < "$TMP/open-prs.tsv"\n'
i = s.index(marker_start)
j = s.index(marker_end) + len(marker_end)
replacement = (
    '  open_pr_hit=0\n'
    '  open_pr_err=0\n'
    '  : # MUTANT M6: åpen-PR-vakten helt fjernet (både navn- og OID-gren)\n'
)
s2 = s[:i] + replacement + s[j:]
assert s2 != s, "marker not found"
open(p, "w").write(s2)
PY
apply_mutant "$W3" "$SANDBOX_ROOT/mutate-m6.py"
out=$(run_sweep "$W3" --dry-run)
echo "FULLOUT>>>"
echo "$out"
echo "<<<FULLOUT"
if printf '%s' "$out" | grep -qF "VILLE FJERNET case-a"; then
  echo "M6(a)=PASS(flippet til FJERNET)"
else
  fail "M6(a): case-a flippet ikke"
fi

cp "$W3/tasks/worktree-sweep.sh" "$W3b/tasks/worktree-sweep.sh"
out=$(run_sweep "$W3b" --dry-run)
echo "FULLOUT>>>"
echo "$out"
echo "<<<FULLOUT"
if printf '%s' "$out" | grep -qF "VILLE FJERNET case-b"; then
  echo "M6(b)=PASS(flippet til FJERNET)"
else
  fail "M6(b): case-b flippet ikke"
fi

echo "############ M11 — {{BASE_BRANCH}}-ancestry-unntaket fjernes (oppfølging 2) ############"
# Gjeninnfører den ekte feilen: OID-sjekken kjøres mot ENHVER åpen PR uansett om wt_head
# allerede er forgjenger til {{BASE_BRANCH}}. Skal ramme KUN V3(c) (flipper til det gamle falske treffet),
# V3(b) skal forbli UENDRET (case-b sin HEAD er IKKE en forgjenger til {{BASE_BRANCH}}, så unntaket
# påvirker den aldri i utgangspunktet).
cat > "$SANDBOX_ROOT/mutate-m11.py" <<'PY'
import sys
p = sys.argv[1]
s = open(p).read()
marker = '    if [ "$wt_head_in_dev" -eq 1 ]; then\n      continue\n    fi\n'
assert marker in s, "marker not found"
replacement = '    # MUTANT M11: {{BASE_BRANCH}}-ancestry-unntaket fjernet\n'
s2 = s.replace(marker, replacement, 1)
assert s2 != s, "mutant traff ikke"
open(p, "w").write(s2)
PY
apply_mutant "$W3c" "$SANDBOX_ROOT/mutate-m11.py"
out=$(run_sweep "$W3c" --dry-run)
echo "FULLOUT>>>"
echo "$out"
echo "<<<FULLOUT"
if printf '%s' "$out" | grep -qF "BEHOLDT  case-c — bærer HEAD/branch for en åpen PR"; then
  echo "M11(c)=PASS(flippet tilbake til det gamle falske treffet)"
else
  fail "M11(c): case-c flippet ikke tilbake"
fi

# V3(b) skal forbli uendret av M11 — case-b sin HEAD er ikke en forgjenger til {{BASE_BRANCH}} i
# utgangspunktet, så unntaket har aldri noen effekt på den casen. $FAKEBIN/gh må pekes
# TILBAKE til W3b sin EGEN fixture her — den ble sist satt til W3c sin fixture (V3(c)/M11(c)
# over), og en OID fra et ANNET scratch-repo er ikke gyldig i W3b sin objektbase.
cp "$W3c/tasks/worktree-sweep.sh" "$W3b/tasks/worktree-sweep.sh"
mkgh "$W3b/pr-fixture.json" 0
out=$(run_sweep "$W3b" --dry-run)
echo "FULLOUT>>>"
echo "$out"
echo "<<<FULLOUT"
if printf '%s' "$out" | grep -qF "BEHOLDT  case-b — bærer HEAD/branch for en åpen PR"; then
  echo "M11(b)=PASS(V3(b) uendret av M11, som forventet)"
else
  fail "M11(b): V3(b) ble uventet påvirket av M11"
fi

echo "############ V4 — fail-safe-batteri ############"
new_harness W4a
git -C "$W4a" branch case-status {{BASE_BRANCH}}
git -C "$W4a" worktree add -q ".claude/worktrees/case-status" case-status
backdate_wt "$W4a/.claude/worktrees/case-status"
printf '[]\n' > "$W4a/pr-fixture.json"
mkgh "$W4a/pr-fixture.json" 0
cat > "$FAKEBIN/git" <<'EOF'
#!/usr/bin/env bash
REALGIT=/usr/bin/git
if [ "$1" = "-C" ] && [ "$3" = "status" ] && printf '%s' "$2" | grep -q "case-status"; then
  exit 1
fi
exec "$REALGIT" "$@"
EOF
chmod +x "$FAKEBIN/git"
out=$(run_sweep "$W4a" --dry-run)
echo "FULLOUT>>>"
echo "$out"
echo "<<<FULLOUT"
rm -f "$FAKEBIN/git"
if printf '%s' "$out" | grep -qF "BEHOLDT  case-status — status feilet"; then
  echo "V4(a)=PASS"
else
  fail "V4(a): status-feil ikke fanget"
fi

new_harness W4b
git -C "$W4b" branch case-anything {{BASE_BRANCH}}
git -C "$W4b" worktree add -q ".claude/worktrees/case-anything" case-anything
backdate_wt "$W4b/.claude/worktrees/case-anything"
mkgh /dev/null 1
out=$(run_sweep "$W4b" --dry-run)
echo "FULLOUT>>>"
echo "$out"
echo "<<<FULLOUT"
if printf '%s' "$out" | grep -qF "AVBRUTT — gh pr list feilet"; then
  echo "V4(b)=PASS"
else
  fail "V4(b): gh-feil ikke fanget"
fi
if printf '%s' "$out" | grep -qF "FJERNET"; then
  fail "V4(b)-INGEN-SLETTING: FJERNET-token funnet etter gh-feil"
else
  echo "V4(b)-INGEN-SLETTING=PASS"
fi

new_harness W4c
git -C "$W4c" branch case-dirty {{BASE_BRANCH}}
git -C "$W4c" worktree add -q ".claude/worktrees/case-dirty" case-dirty
echo dirty > "$W4c/.claude/worktrees/case-dirty/uncommitted.txt"
backdate_wt "$W4c/.claude/worktrees/case-dirty"
printf '[]\n' > "$W4c/pr-fixture.json"
mkgh "$W4c/pr-fixture.json" 0
cat > "$FAKEBIN/stub-landed.sh" <<'EOF'
#!/usr/bin/env bash
exit 127
EOF
chmod +x "$FAKEBIN/stub-landed.sh"
out=$(LANDED_SCRIPT_OVERRIDE="$FAKEBIN/stub-landed.sh" run_sweep "$W4c" --dry-run)
echo "FULLOUT>>>"
echo "$out"
echo "<<<FULLOUT"
if printf '%s' "$out" | grep -qF "BEHOLDT  case-dirty — klassifikator:"; then
  echo "V4(c)=PASS"
else
  fail "V4(c): klassifikator-stub-127 ikke fanget"
fi

new_harness W4d
git -C "$W4d" branch case-cap {{BASE_BRANCH}}
git -C "$W4d" worktree add -q ".claude/worktrees/case-cap" case-cap
backdate_wt "$W4d/.claude/worktrees/case-cap"
python3 - "$W4d/pr-fixture.json" <<'PY'
import json, sys
entries = [{"headRefName": f"branch-{i}", "headRefOid": "a" * 40} for i in range(200)]
open(sys.argv[1], "w").write(json.dumps(entries))
PY
mkgh "$W4d/pr-fixture.json" 0
out=$(run_sweep "$W4d" --dry-run)
echo "FULLOUT>>>"
echo "$out"
echo "<<<FULLOUT"
if printf '%s' "$out" | grep -qF "AVBRUTT — gh pr list traff taket"; then
  echo "V4(d)=PASS"
else
  fail "V4(d): 200-tak ikke fanget"
fi

echo "############ V5 — bevarte vakter, gate (inkl. B1-sekvens), vakt 6 ############"
new_harness W5a
git -C "$W5a" branch case-live {{BASE_BRANCH}}
git -C "$W5a" worktree add -q ".claude/worktrees/case-live" case-live
backdate_wt "$W5a/.claude/worktrees/case-live"
git -C "$W5a" worktree lock ".claude/worktrees/case-live" --reason "claude agent case-live (pid $$ start now)"
printf '[]\n' > "$W5a/pr-fixture.json"
mkgh "$W5a/pr-fixture.json" 0
out=$(run_sweep "$W5a" --dry-run)
echo "FULLOUT>>>"
echo "$out"
echo "<<<FULLOUT"
if printf '%s' "$out" | grep -qF "BEHOLDT  case-live — låst"; then
  echo "V5(a)-basic=PASS"
else
  fail "V5(a)-basic: lås mot levende pid ikke respektert"
fi

new_harness W5a2
git -C "$W5a2" branch case-det {{BASE_BRANCH}}
git -C "$W5a2" worktree add -q --detach ".claude/worktrees/case-det" {{BASE_BRANCH}}
backdate_wt "$W5a2/.claude/worktrees/case-det"
lockline_path=$(git -C "$W5a2" rev-parse --path-format=absolute --git-common-dir)
mkdir -p "$lockline_path/worktrees/case-det"
printf 'locked custom-reason pid %s\n' "$$" > "$lockline_path/worktrees/case-det/locked"
printf '[]\n' > "$W5a2/pr-fixture.json"
mkgh "$W5a2/pr-fixture.json" 0
out=$(run_sweep "$W5a2" --dry-run)
echo "FULLOUT>>>"
echo "$out"
echo "<<<FULLOUT"
if printf '%s' "$out" | grep -qF "BEHOLDT  case-det — låst av levende pid $$"; then
  echo "V5(a)-detached=PASS"
else
  fail "V5(a)-detached: detached-HEAD-lås ikke respektert"
fi

echo "############ V5(c) — gate: token-basert wtsweep=<n>/<n>, IKKE tidsstempel (fix-runde 2, B1) ############"
new_harness W5c
touch "$W5c/docs/superpowers/loop/run-log.md"
out=$(run_sweep "$W5c" --gate)
echo "FULLOUT>>>"
echo "$out"
echo "<<<FULLOUT"
if printf '%s' "$out" | grep -qF "GATE GRØNN"; then
  echo "V5(c)-fersk=PASS (ingen §6-rad ennå ⇒ GRØNN)"
else
  fail "V5(c)-fersk: gate ikke grønn på fersk run-log uten §6-rad"
fi

echo "--- V5(c)-a: siste §6-rad bærer wtsweep=2/0 ⇒ GRØNN ---"
printf '2026-09-21T10:00 | 380 | x | merged | - | url | 1 | 1 | m | note | wtsweep=2/0\n' > "$W5c/docs/superpowers/loop/run-log.md"
out=$(run_sweep "$W5c" --gate)
echo "FULLOUT>>>"
echo "$out"
echo "<<<FULLOUT"
if printf '%s' "$out" | grep -qF "GATE GRØNN"; then
  echo "V5(c)-a=PASS (wtsweep=2/0 ⇒ GRØNN)"
else
  fail "V5(c)-a: gate ikke grønn med velformet wtsweep-token"
fi

echo "--- V5(c)-b: NY §6-rad UTEN token, appendet ETTER en rad MED token (simulerer hoppet §6d) ⇒ RØD ---"
printf '2026-09-21T11:00 | 380 | x | merged | - | url | 1 | 1 | m | note | -\n' >> "$W5c/docs/superpowers/loop/run-log.md"
out=$(run_sweep "$W5c" --gate)
echo "FULLOUT>>>"
echo "$out"
echo "<<<FULLOUT"
if printf '%s' "$out" | grep -qF "GATE RØD"; then
  echo "V5(c)-b=PASS (token mangler i siste rad ⇒ RØD)"
else
  fail "V5(c)-b: gate ikke rød når siste §6-rad mangler wtsweep-token"
fi

echo "--- V5(c)-c: siste §6-rad bærer wtsweep=feilet:x (steg 4b sitt eget kall feilet) ⇒ RØD ---"
printf '2026-09-21T12:00 | 380 | x | merged | - | url | 1 | 1 | m | note | wtsweep=feilet:x\n' >> "$W5c/docs/superpowers/loop/run-log.md"
out=$(run_sweep "$W5c" --gate)
echo "FULLOUT>>>"
echo "$out"
echo "<<<FULLOUT"
if printf '%s' "$out" | grep -qF "GATE RØD"; then
  echo "V5(c)-c=PASS (wtsweep=feilet:x ⇒ RØD)"
else
  fail "V5(c)-c: gate ikke rød med feil-formet wtsweep-token"
fi

echo "--- V5(c)-helserad: en helserad ETTER en gyldig token-rad skal IKKE telle som siste §6-rad — gaten hopper forbi den og finner tokenet under ⇒ GRØNN ---"
new_harness W5ch
printf '2026-09-21T09:00 | 380 | x | merged | - | url | 1 | 1 | m | note | wtsweep=3/1\n' > "$W5ch/docs/superpowers/loop/run-log.md"
printf '2026-09-21T09:30 | - | loop-health-check | health | - | - | 0 | 0 | m | -\n' >> "$W5ch/docs/superpowers/loop/run-log.md"
out=$(run_sweep "$W5ch" --gate)
echo "FULLOUT>>>"
echo "$out"
echo "<<<FULLOUT"
if printf '%s' "$out" | grep -qF "GATE GRØNN"; then
  echo "V5(c)-helserad=PASS (helserad hoppet over, fant wtsweep=3/1 under)"
else
  fail "V5(c)-helserad: gate ignorerte ikke helseraden ved leting etter siste §6-rad"
fi

echo "--- V5(c)-paused (fix-runde 3, mikro, punkt 1): merged-rad MED token, etterfulgt av paused-rad, skal fortsatt gi GRØNN — positivt merged-filter, ikke negativt helse-unntak ---"
printf '2026-09-21T09:45 | 380 | x | paused | - | url | 1 | 1 | m | note | -\n' >> "$W5ch/docs/superpowers/loop/run-log.md"
out=$(run_sweep "$W5ch" --gate)
echo "FULLOUT>>>"
echo "$out"
echo "<<<FULLOUT"
if printf '%s' "$out" | grep -qF "GATE GRØNN"; then
  echo "V5(c)-paused=PASS (paused-rad hoppet over, fant wtsweep=3/1 i den forrige merged-raden)"
else
  fail "V5(c)-paused: gate ble RØD av en paused-rad — radfilteret er ikke rent positivt på merged"
fi

echo "--- V5(c)-multi (fix-runde 3, mikro, punkt 4): siste §6-rad bærer BÅDE wtsweep=feilet:x OG wtsweep=3/1 — ENHVER feil-formet forekomst skal gi RØD, selv om en senere er velformet ---"
printf '2026-09-21T13:00 | 380 | x | merged | - | url | 1 | 1 | m | note | wtsweep=feilet:x; wtsweep=3/1\n' > "$W5c/docs/superpowers/loop/run-log.md"
out=$(run_sweep "$W5c" --gate)
echo "FULLOUT>>>"
echo "$out"
echo "<<<FULLOUT"
if printf '%s' "$out" | grep -qF "GATE RØD"; then
  echo "V5(c)-multi=PASS (feil-formet forekomst fanget selv med en velformet forekomst senere i raden)"
else
  fail "V5(c)-multi: gate ble GRØNN selv om raden inneholder en feil-formet wtsweep-forekomst"
fi

echo "--- V5(c)-dry (fix-runde 3, mikro, punkt 4): siste §6-rad bærer KUN wtsweep_dry=<n>/<n> (et --dry-run-token) — skal IKKE bestå som bevis på en ekte sweep ⇒ RØD ---"
printf '2026-09-21T14:00 | 380 | x | merged | - | url | 1 | 1 | m | note | wtsweep_dry=2/0\n' > "$W5c/docs/superpowers/loop/run-log.md"
out=$(run_sweep "$W5c" --gate)
echo "FULLOUT>>>"
echo "$out"
echo "<<<FULLOUT"
if printf '%s' "$out" | grep -qF "GATE RØD"; then
  echo "V5(c)-dry=PASS (wtsweep_dry= alene teller ikke som et ekte wtsweep=-token)"
else
  fail "V5(c)-dry: gate godtok et wtsweep_dry=-token som bevis på en ekte sweep-kjøring"
fi

echo "--- M7 — gaten ignorerer wtsweep-tokenet og returnerer alltid GRØNN (erstatter M5, se planens fix-runde 2-seksjon for hvorfor) ---"
new_harness W5cmut
printf '2026-09-21T10:00 | 380 | x | merged | - | url | 1 | 1 | m | note | wtsweep=2/0\n' > "$W5cmut/docs/superpowers/loop/run-log.md"
printf '2026-09-21T11:00 | 380 | x | merged | - | url | 1 | 1 | m | note | -\n' >> "$W5cmut/docs/superpowers/loop/run-log.md"
cat > "$SANDBOX_ROOT/mutate-m7-gate.py" <<'PY'
import sys
p = sys.argv[1]
s = open(p).read()
marker_start = "  tokens=$(printf '%s\\n' \"$last_row\""
marker_end = (
    '  last_token=$(printf \'%s\\n\' "$tokens" | tail -1)\n'
    '  echo "GATE GRØNN — siste §6-rad bærer $last_token"\n'
    '  exit 0\n'
    'fi\n'
)
i = s.index(marker_start)
j = s.index(marker_end) + len(marker_end)
replacement = (
    '  : # MUTANT M7: gaten ignorerer wtsweep-tokenet og returnerer alltid GRØNN\n'
    '  echo "GATE GRØNN — MUTANT: token ignorert (alltid grønn uansett innhold)"\n'
    '  exit 0\n'
    'fi\n'
)
s2 = s[:i] + replacement + s[j:]
assert s2 != s, "marker not found"
open(p, "w").write(s2)
PY
apply_mutant "$W5cmut" "$SANDBOX_ROOT/mutate-m7-gate.py"
out=$(run_sweep "$W5cmut" --gate)
echo "FULLOUT>>>"
echo "$out"
echo "<<<FULLOUT"
if printf '%s' "$out" | grep -qF "GATE GRØNN"; then
  echo "M7=PASS (case (b) flippet feilaktig til GRØNN — mutanten fanget)"
else
  fail "M7: gate-mutanten flippet ikke case (b) til GRØNN som forventet"
fi

echo "############ V5(d) — vakt 6, begge retninger ############"
new_harness W5d
git -C "$W5d" branch case-fresh {{BASE_BRANCH}}
git -C "$W5d" worktree add -q ".claude/worktrees/case-fresh" case-fresh
printf '[]\n' > "$W5d/pr-fixture.json"
mkgh "$W5d/pr-fixture.json" 0
out=$(AGE_MIN_OVERRIDE=60 run_sweep "$W5d" --dry-run)
echo "FULLOUT>>>"
echo "$out"
echo "<<<FULLOUT"
if printf '%s' "$out" | grep -qF "rørt for"; then
  echo "V5(d)-fersk=PASS"
else
  fail "V5(d)-fersk: vakt 6 fanget ikke et ferskt tre"
fi
find "$W5d/.claude/worktrees/case-fresh" -type f -exec touch -t 202001010000 {} \;
out=$(AGE_MIN_OVERRIDE=60 run_sweep "$W5d" --dry-run)
echo "FULLOUT>>>"
echo "$out"
echo "<<<FULLOUT"
if printf '%s' "$out" | grep -qF "rørt for"; then
  fail "V5(d)-gammel: vakt6-linja fortsatt der etter tilbakedatering"
else
  echo "V5(d)-gammel=PASS (vakt6-linja borte)"
fi

echo "############ V6 — klassifikator kalt fra sweepen; R2: ignorert fil på RASK VEI ############"
new_harness W6
git -C "$W6" checkout -q -b squashed {{BASE_BRANCH}}
printf 'landed content\n' > "$W6/feature-x.md"
git -C "$W6" add -A
git -C "$W6" commit -q -m "unlanded commit, content squash-merges senere"
git -C "$W6" checkout -q {{BASE_BRANCH}}
git -C "$W6" worktree add -q ".claude/worktrees/case-squash" squashed
backdate_wt "$W6/.claude/worktrees/case-squash"
printf 'landed content\n' > "$W6/feature-x-landed.md"
git -C "$W6" add feature-x-landed.md
git -C "$W6" commit -q -m "{{BASE_BRANCH}}: innholdet landet under et annet navn"
git -C "$W6" push -q origin {{BASE_BRANCH}}
printf '[]\n' > "$W6/pr-fixture.json"
mkgh "$W6/pr-fixture.json" 0
out=$(run_sweep "$W6" --dry-run)
echo "FULLOUT>>>"
echo "$out"
echo "<<<FULLOUT"
if printf '%s' "$out" | grep -qF "VILLE FJERNET case-squash"; then
  echo "V6(landed)=PASS"
else
  fail "V6(landed): klassifikator-kallsted fant ikke landed-moved-tilfellet"
fi
if printf '%s' "$out" | grep -qF "redning=1"; then
  echo "V6(redning-varslet)=PASS"
else
  fail "V6(redning-varslet): redning=1 mangler i --dry-run-output"
fi

echo "--- V6(rask-vei-ignorert), R2: rent tre, HEAD på remote, ignorert fil UTENFOR allowlisten ⇒ BEHOLDT ---"
new_harness W6r
git -C "$W6r" checkout -q -b case-fastpath {{BASE_BRANCH}}
# .gitignore må være COMMITTET (fix-runde 3, mikro, punkt 2) — en ukommittert .gitignore gjør
# treet DIRTY (status --porcelain ser den som untracked), som tvinger sweepen til den FULLE
# klassifikator-grenen i stedet for den raske veien. Revieweren målte at en mutant som
# nøytraliserer --ignored-only likevel ga PASS her, nettopp fordi den raske veien ALDRI ble tatt.
printf '*.local\n' > "$W6r/.gitignore"
git -C "$W6r" add .gitignore
git -C "$W6r" commit -q -m "case-fastpath: committer .gitignore slik at treet forblir rent"
git -C "$W6r" push -q -u origin case-fastpath
git -C "$W6r" checkout -q {{BASE_BRANCH}}
git -C "$W6r" worktree add -q ".claude/worktrees/case-fastpath" case-fastpath
backdate_wt "$W6r/.claude/worktrees/case-fastpath"
# Treet er COMMIT-rent (status --porcelain tomt — .gitignore er committet, .env.local er
# IGNORERT av den, ikke untracked) og HEAD er pushet til origin — kvalifiserer for den «raske
# veien». En IGNORERT fil utenfor allowlisten ligger der (f.eks. en lekket .env.local som
# avviker fra hovedsjekkutens kopi) — uten R2-fiksen ville sweepen fjernet treet og med det
# denne fila, siden `status --porcelain` aldri ser ignorerte filer.
printf 'IGNORERT_HEMMELIGHET=1\n' > "$W6r/.claude/worktrees/case-fastpath/.env.local"
# Tilbakedater IGJEN etter å ha skrevet .env.local (fix-runde 3, mikro) — ellers fanger vakt 6
# (mtime) treet av en HELT ANNEN grunn enn den denne casen skal måle, og M8 (under) ville da
# feilaktig PASSere selv om --ignored-only-kallet var nøytralisert, fordi vakt 6 uansett hadde
# reddet treet.
backdate_wt "$W6r/.claude/worktrees/case-fastpath"
printf '[]\n' > "$W6r/pr-fixture.json"
mkgh "$W6r/pr-fixture.json" 0
dirty_check=$(git -C "$W6r/.claude/worktrees/case-fastpath" status --porcelain -uall)
if [ -n "$dirty_check" ]; then
  fail "V6(rask-vei-ignorert)-oppsett: treet er DIRTY før sweep kjøres ($dirty_check) — fast-path-forutsetningen holder ikke"
else
  echo "V6(rask-vei-ignorert)-oppsett=PASS (treet er rent — status --porcelain tomt)"
fi
out=$(run_sweep "$W6r" --dry-run)
echo "FULLOUT>>>"
echo "$out"
echo "<<<FULLOUT"
if printf '%s' "$out" | grep -qF "BEHOLDT  case-fastpath — ignorert-fil (rask vei):"; then
  echo "V6(rask-vei-ignorert)=PASS"
else
  fail "V6(rask-vei-ignorert): rask vei fjernet et tre med en ignorert fil utenfor allowlisten, eller falt gjennom til full klassifikator"
fi
if printf '%s' "$out" | grep -qF "BEHOLDT  case-fastpath — klassifikator:"; then
  fail "V6(rask-vei-ignorert)-ikke-fallback: BEHOLDT-grunnen starter med 'klassifikator:' — den raske veien ble IKKE tatt"
else
  echo "V6(rask-vei-ignorert)-ikke-fallback=PASS (BEHOLDT-grunnen starter ikke med 'klassifikator:')"
fi

echo "--- M8: den raske veiens --ignored-only-kall nøytraliseres (fix-runde 3, mikro) ---"
cat > "$SANDBOX_ROOT/mutate-m8.py" <<'PY'
import sys
p = sys.argv[1]
s = open(p).read()
marker = '    ignored_out=$(bash "$LANDED_SCRIPT" "$p" --ref "$REF" --ignored-only)\n    ignored_rc=$?\n'
replacement = '    ignored_out="MUTANT"; ignored_rc=0  # MUTANT M8: --ignored-only-kallet nøytralisert\n'
assert marker in s, "marker not found"
s2 = s.replace(marker, replacement)
assert s2 != s
open(p, "w").write(s2)
PY
apply_mutant "$W6r" "$SANDBOX_ROOT/mutate-m8.py"
out=$(run_sweep "$W6r" --dry-run)
echo "FULLOUT>>>"
echo "$out"
echo "<<<FULLOUT"
if printf '%s' "$out" | grep -qF "VILLE FJERNET case-fastpath"; then
  echo "M8=PASS (rask vei nøytralisert ⇒ VILLE FJERNET en ignorert-fil-case)"
else
  fail "M8: nøytralisert --ignored-only flippet ikke V6(rask-vei-ignorert) til VILLE FJERNET"
fi

echo "--- M5 (fallgjennom-form, gjeninnført fix-runde 3, mikro — eier-godkjent budsjettutvidelse 6→8): fjern klassifikator-kallet (gjeninnfør gammel vakt-2-eneste-oppførsel) ---"
cat > "$SANDBOX_ROOT/mutate-m5.py" <<'PY'
import sys
p = sys.argv[1]
s = open(p).read()
marker = (
    '  else\n'
    '    # Klassifikator-gren (§ 4b punkt 3): rc = 0 ⇒ fjern; alt annet ⇒ BEHOLD. '
    'Fangsten under er\n'
    '    # ren dokumentasjon og gir ALDRI i seg selv lov til å slette.\n'
    '    classifier_out=$(bash "$LANDED_SCRIPT" "$p" --ref "$REF")\n'
    '    classifier_rc=$?\n'
    '    if [ "$classifier_rc" -ne 0 ]; then\n'
    "      reason=$(printf '%s\\n' \"$classifier_out\" | tail -1)\n"
    '      echo "BEHOLDT  $n — klassifikator: $reason"\n'
    '      kept=$((kept + 1))\n'
    '      continue\n'
    '    fi\n'
    "    landed_moved_list=$(printf '%s\\n' \"$classifier_out\" | sed -n 's/^LANDED-MOVED://p')\n"
    '  fi'
)
assert marker in s, "marker not found"
replacement = (
    '  else\n'
    '    # MUTANT M5: klassifikator-kallet fjernet.\n'
    '    if [ "$head_on_remote" -ne 1 ]; then\n'
    '      echo "BEHOLDT  $n — HEAD ${wt_head:0:8} finnes IKKE på origin"\n'
    '      kept=$((kept + 1))\n'
    '      continue\n'
    '    fi\n'
    '  fi'
)
s2 = s.replace(marker, replacement)
assert s2 != s
open(p, "w").write(s2)
PY
apply_mutant "$W6" "$SANDBOX_ROOT/mutate-m5.py"
out=$(run_sweep "$W6" --dry-run)
echo "FULLOUT>>>"
echo "$out"
echo "<<<FULLOUT"
if printf '%s' "$out" | grep -qF "BEHOLDT  case-squash — HEAD"; then
  echo "M5=PASS"
else
  fail "M5: klassifikator-kallsted-fjerning flippet ikke V6(landed)"
fi

echo "############ N — navngitt kjøring ############"
new_harness WN
git -C "$WN" checkout -q -b feat/n3 {{BASE_BRANCH}}
echo n3 > "$WN/n3.txt"
git -C "$WN" add -A
git -C "$WN" commit -q -m "n3: eget arbeid bak en åpen PR"
git -C "$WN" push -q -u origin feat/n3
n3_head=$(git -C "$WN" rev-parse feat/n3)
git -C "$WN" checkout -q {{BASE_BRANCH}}
git -C "$WN" branch n1 {{BASE_BRANCH}}
git -C "$WN" branch n2 {{BASE_BRANCH}}
git -C "$WN" branch other {{BASE_BRANCH}}
git -C "$WN" worktree add -q ".claude/worktrees/agent-n1" n1
git -C "$WN" worktree add -q ".claude/worktrees/agent-n2" n2
git -C "$WN" worktree add -q ".claude/worktrees/agent-n3" feat/n3
git -C "$WN" worktree add -q ".claude/worktrees/agent-other" other
backdate_wt "$WN/.claude/worktrees/agent-other"
touch -t 203001010000 "$WN/.claude/worktrees/agent-n1/README.md"   # fremtidig mtime: treffer -mmin -N for alle N >= 0, også -mmin -0
git -C "$WN" worktree lock ".claude/worktrees/agent-n2" --reason "claude agent agent-n2 (pid $$ start now)"
printf '[{"headRefName":"feat/n3","headRefOid":"%s"}]\n' "$n3_head" > "$WN/pr-fixture.json"
mkgh "$WN/pr-fixture.json" 0
run_wn() { AGE_MIN_OVERRIDE=1440 run_sweep "$WN" "$@"; }

echo "--- R1: run_wn --dry-run (uten navn) ---"
out=$(run_wn --dry-run)
echo "FULLOUT>>>"
echo "$out"
echo "<<<FULLOUT"
if printf '%s' "$out" | grep -qF "BEHOLDT  agent-n1 — rørt for"; then
  echo "N1-uten-navn=PASS"
else
  fail "N1-uten-navn: agent-n1 ikke BEHOLDT via aldersvakt uten navn"
fi
if printf '%s' "$out" | grep -qF "VILLE FJERNET agent-other"; then
  echo "N4-kontroll=PASS"
else
  fail "N4-kontroll: agent-other ikke VILLE FJERNET uten navn"
fi

echo "--- R2: run_wn --dry-run agent-n1 agent-n2 agent-n3 agent-nx (navngitt) ---"
out=$(run_wn --dry-run agent-n1 agent-n2 agent-n3 agent-nx)
echo "FULLOUT>>>"
echo "$out"
echo "<<<FULLOUT"
if printf '%s' "$out" | grep -qF "VILLE FJERNET agent-n1"; then
  echo "N1-navngitt=PASS"
else
  fail "N1-navngitt: agent-n1 ikke VILLE FJERNET i navngitt modus"
fi
if printf '%s' "$out" | grep -qF "BEHOLDT  agent-n2 — låst av levende pid $$"; then
  echo "N2-lås=PASS"
else
  fail "N2-lås: agent-n2 ikke BEHOLDT via lås i navngitt modus"
fi
if printf '%s' "$out" | grep -qF "BEHOLDT  agent-n3 — bærer HEAD/branch for en åpen PR"; then
  echo "N3-åpen-PR=PASS"
else
  fail "N3-åpen-PR: agent-n3 ikke BEHOLDT via åpen PR i navngitt modus"
fi
if printf '%s' "$out" | grep -qF "agent-other"; then
  fail "N4-filter: agent-other dukket opp i navngitt kjøring"
else
  echo "N4-filter=PASS"
fi
ikke_funnet_lines=$(printf '%s\n' "$out" | grep -c '^IKKE FUNNET')
if [ "$ikke_funnet_lines" -eq 1 ] && printf '%s' "$out" | grep -qF "IKKE FUNNET agent-nx"; then
  echo "N-ikke-funnet=PASS"
else
  fail "N-ikke-funnet: forventet nøyaktig én linje 'IKKE FUNNET agent-nx', fikk $ikke_funnet_lines"
fi
if printf '%s' "$out" | grep -qE '^wtsweep_named_dry=[0-9]+/[0-9]+ ' \
  && [ "$(printf '%s' "$out" | grep -cF 'wtsweep=')" -eq 0 ] \
  && ! printf '%s' "$out" | grep -qF 'rørt for'; then
  echo "N-oppsummering=PASS"
else
  fail "N-oppsummering: oppsummeringslinja i navngitt tørrkjøring var ikke som forventet"
fi

echo "--- R3: run_wn agent-n1 (destruktiv, i sandkassen) ---"
out3=$(run_wn agent-n1)
echo "FULLOUT>>>"
echo "$out3"
echo "<<<FULLOUT"
if printf '%s' "$out3" | grep -qF "FJERNET  agent-n1" \
  && [ ! -d "$WN/.claude/worktrees/agent-n1" ] \
  && [ -d "$WN/.claude/worktrees/agent-other" ] \
  && printf '%s' "$out3" | grep -qE '^wtsweep_named=1/0 '; then
  echo "N1-destruktiv=PASS"
else
  fail "N1-destruktiv: navngitt destruktiv fjerning av agent-n1 ga ikke forventet utfall"
fi

echo "--- R4: run_wn (døgnsweep, destruktiv) ---"
out4=$(run_wn)
if printf '%s' "$out4" | grep -qF "FJERNET  agent-other"; then
  echo "R4-oppsett=PASS (agent-other fjernet av døgnsweepen)"
else
  fail "R4-oppsett: agent-other ikke fjernet av døgnsweepen (grunnlag for N6)"
fi

echo "--- N6: run-log-rader bygd av faktiske token fra R3/R4 ---"
named_tok=$(printf '%s\n' "$out3" | grep -oE '^wtsweep[a-z_]*=[0-9]+/[0-9]+' | head -1)
dogn_tok=$(printf '%s\n' "$out4" | grep -oE '^wtsweep=[0-9]+/[0-9]+' | head -1)
if [ -z "$named_tok" ] || [ -z "$dogn_tok" ]; then
  fail "N6-oppsett: named_tok eller dogn_tok tomt (named_tok=$named_tok dogn_tok=$dogn_tok)"
else
  printf '2026-09-25T10:00 | 401 | x | merged | - | url | 1 | 1 | m | note | %s\n' "$named_tok" > "$WN/docs/superpowers/loop/run-log.md"
  out=$(run_wn --gate)
  if printf '%s' "$out" | grep -qF "GATE RØD — siste §6-rad mangler wtsweep=-token"; then
    echo "N6-kun-navngitt=PASS"
  else
    fail "N6-kun-navngitt: en rad med bare $named_tok ga ikke RØD-grunnteksten"
  fi
  printf '2026-09-25T10:05 | 401 | x | merged | - | url | 1 | 1 | m | note | %s; %s\n' "$dogn_tok" "$named_tok" > "$WN/docs/superpowers/loop/run-log.md"
  out=$(run_wn --gate)
  if printf '%s' "$out" | grep -qF "GATE GRØNN — siste §6-rad bærer $dogn_tok"; then
    echo "N6-begge=PASS"
  else
    fail "N6-begge: en rad med $dogn_tok; $named_tok ga ikke GRØNN"
  fi
fi

echo "--- N5: run_wn --dry-run <sti> (avvises) ---"
out=$(run_wn --dry-run "$WN/.claude/worktrees/agent-n2")
rc=$?
if [ "$rc" -eq 2 ] \
  && printf '%s' "$out" | grep -qF "UKJENT FLAGG:" \
  && ! printf '%s' "$out" | grep -qE '^(VILLE FJERNET|BEHOLDT)'; then
  echo "N5-sti-avvist=PASS"
else
  fail "N5-sti-avvist: en sti som argument ble ikke avvist høylytt (rc=$rc)"
fi

echo "--- N5b (VIKTIG): 'agent-*' og et navn med internt mellomrom avvises ---"
out=$(run_wn --dry-run 'agent-*')
rc_wild=$?
out2=$(run_wn --dry-run 'agent-n1 agent-other')
rc_space=$?
if [ "$rc_wild" -eq 2 ] && ! printf '%s' "$out" | grep -qE '^(VILLE FJERNET|BEHOLDT)' \
  && [ "$rc_space" -eq 2 ] && ! printf '%s' "$out2" | grep -qE '^(VILLE FJERNET|BEHOLDT)'; then
  echo "N5b=PASS"
else
  fail "N5b: 'agent-*' (rc=$rc_wild) eller 'agent-n1 agent-other' (rc=$rc_space) ble ikke avvist høylytt"
fi

echo "--- N-gate-navngitt (MINDRE): --gate + navn avvises ---"
out=$(run_wn --gate agent-n2)
rc=$?
if [ "$rc" -eq 2 ] && printf '%s' "$out" | grep -qF "UKJENT FLAGG:" \
  && ! printf '%s' "$out" | grep -qE '^GATE (RØD|GRØNN)'; then
  echo "N-gate-navngitt=PASS"
else
  fail "N-gate-navngitt: --gate kombinert med et navn ble ikke avvist høylytt (rc=$rc)"
fi

echo "############ D — docker kan ikke blokkere sweepen ############"
if [ ! -e "$DOCKER_MARK" ]; then
  echo "D1=PASS (ingen sweep-kjøring i harnessen har kalt docker)"
else
  fail "D1: docker-stubben ble kalt av en sweep-kjøring: $(cat "$DOCKER_MARK")"
fi
if (cd "$WN" && PATH="$FAKEBIN:$PATH" docker info > /dev/null) && grep -qx 'info' "$DOCKER_MARK"; then
  echo "D0=PASS (positiv kontroll: stubben nås og skriver markøren)"
else
  fail "D0: docker-stubben (positiv kontroll) ble ikke nådd/skrev ikke markøren"
fi

echo "---"
if [ "$all_ok" -eq 1 ]; then
  echo "TESTS_OK"
  exit 0
fi
echo "TESTS_FAILED"
exit 1
