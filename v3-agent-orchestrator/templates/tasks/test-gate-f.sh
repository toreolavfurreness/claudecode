#!/usr/bin/env bash
# Regresjonstest for gate-f.sh (generert av /setup). Kjøres: bash tasks/test-gate-f.sh [<sti til gaten som testes>]
G=${1:-"$(dirname "$0")/gate-f.sh"}; fail=0
T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
# t <etikett> <forventet exit> <forventet tekst i output, eller -> <args…>
t() { out=$("$G" "${@:4}" 2>&1); got=$?
  if [ "$got" = "$2" ] && { [ "$3" = - ] || grep -qF -- "$3" <<<"$out"; }; then echo "OK   [$1]"
  else echo "AVVIK [$1] (fikk $got, ventet $2 «$3»)"; echo "$out" | sed 's/^/     /'; fail=1; fi; }
# plan <fil> <§-linjer…> -- <vinduslinjer…>: minimal plan. Vinduslinjer som starter med **V får kodeblokk.
plan() { f=$1; shift; { echo '## Verifisering'; while [ "$1" != -- ]; do echo "$1"; shift; done; shift
  echo '## Fix-runde 1'; echo '#### V-blokk re-kjørt mot HEAD (fix-runde 1)'
  for l in "$@"; do echo "$l"; case $l in '**V'*) printf '```\n$ cmd\nut\n```\n';; esac; done
  echo 'Ingen tall arves fra en tidligere runde.'; } > "$f"; }
plan "$T/gronn.md" '**V1**' '**V2**' -- '**V1**' '**V2**'
t 'grønn' 0 - "$T/gronn.md" 1 2
t 'ref-avvik' 1 '≠ F3a_ref=3' "$T/gronn.md" 1 3
t 'uten overskrift' 1 'F1=0' "$T/gronn.md" 9
plan "$T/range.md" '**V7**' '**V8**' '**V9**' -- '**V7**' 'V8–V9 som over'
t range 1 'mangler i fix-runde-seksjonen: V8 V9' "$T/range.md" 1
t 'lås-av' 1 'LÅS AV (ingen F3a_ref)' "$T/range.md" 1
t 'gulv-av' 0 'GULV AV' "$T/range.md" 1 0
plan "$T/slash.md" '**V7**' '**V8**' -- '**V7 / V8**'
t slash 1 'mangler i fix-runde-seksjonen: V7 V8' "$T/slash.md" 1
plan "$T/sub1.md" '**V11a**' '**V11b**' '**V11c**' -- '**V11**'
t sub1 0 - "$T/sub1.md" 1 1
plan "$T/sub2.md" '**V5**' '**V11**' -- '**V5a**' '**V5b**' '**V11**'
t sub2 0 - "$T/sub2.md" 1 2
plan "$T/eier0.md" '| V1 | x | Implementer |' '| V2 | x | Koordinator |' -- '**V1**'
t eier0 1 'mangler i fix-runde-seksjonen: V2' "$T/eier0.md" 1 2
plan "$T/eier1.md" '| V1 | x | Implementer |' '| V2 | x | Koordinator [koordinator] |' -- '**V1**'
t eier1 0 - "$T/eier1.md" 1 2:V2
t 'eier1-lås' 1 '≠ F3a_ref=2' "$T/eier1.md" 1 2
plan "$T/eier2.md" '**V1**' '**V2** [eier]' -- '**V1**' ' **V2** — eier kjører etter merge'
t eier2 0 'F3b=2 F3r=1' "$T/eier2.md" 1 2:V2
# bytte av merke: [eier] flyttet fra V1 til V2 etter at ref ble målt
plan "$T/bytte.md" '**V1**' '**V2** [eier]' -- '**V1**'
t bytte 1 'F3a=2:V2 ≠ F3a_ref=2:V1' "$T/bytte.md" 1 2:V1
plan "$T/null.md" 'V1 kjør testene' -- '**V1**'
t null 1 'F3a=0' "$T/null.md" 1
t null-ref 1 'F3a=0' "$T/null.md" ref
t null-gulv-av 0 'GULV AV' "$T/null.md" 1 0
sed 's/^## Verifisering$/## §4 V-kriterier (8)/' "$T/range.md" > "$T/anker.md"
t anker 0 3 "$T/anker.md" ref
{ echo '## Verifisering'; echo '**V1**'; echo '```'; echo '**V2**'; echo '### V3'; echo '```'; } > "$T/fence.md"
t fence 0 1 "$T/fence.md" ref
# ID-lignende, men ulest: tittel i feten, sammenslått, range, backtick, nummerert, avkrysning, uten siffer
plan "$T/ulest.md" '**V1**' '- **V2 gullsett**' '**V3/V4**' '**V5–V6**' '| `V7` | x |' '1. **V8**' '- [ ] **V9**' '**V-RP**' -- '**V1**'
t ulest-ref 1 'ulest i § Verifisering: V-RP V2 V3 V4 V6 V7 V8 V9' "$T/ulest.md" ref
t ulest 1 'ulest i § Verifisering: V-RP V2 V3 V4 V6 V7 V8 V9' "$T/ulest.md" 1
# ankeret. Engangsrepo: A (kode) – B (kode-commit) – C (plan-commit), D på sidegren fra A.
R=$T/repo; g() { git -C "$R" -c user.name=t -c user.email=t@t -c commit.gpgsign=false "$@"; }
c() { mkdir -p "$R/$(dirname "$1")"; echo "$2" > "$R/$1"; g add -A; g commit -qm "$2"; g rev-parse HEAD; }
git init -q "$R"; CA=$(c tasks/x.sh a); CB=$(c tasks/x.sh b); CC=$(c tasks/plans/p.md c); g checkout -q "$CA"; CD=$(c tasks/x.sh d)
# ta <etikett> <exit> <tekst> <F3a_ref> <tip> <ankerlinjer…>: gaten kjøres mot engangsrepoet
ta() { plan "$T/$1.md" '**V1**' -- "${@:6}" '**V1**'; GIT_DIR=$R/.git t "$1" "$2" "$3" "$T/$1.md" 1 "$4" $5; }
ta anker-gronn 0 'ANKER OK' 1 "$CC" "HEAD: $CB"
ta anker-lik 0 'ANKER OK' 1 "$CB" "HEAD: $CB"
ta anker-stale 1 'annet enn tasks/plans/' 0 "$CC" "HEAD: $CA"
ta anker-ikke-forfar 1 'ikke forfar' 1 "$CC" "HEAD: $CD"
ta anker-sha-lenger-ned 0 'ANKER OK' 1 "$CC" 'HEAD: se under' "**HEAD:** \`${CB:0:7}\` (branch x)"
ta anker-mangler 1 '0 HEAD-linje' 1 "$CC" '```' "HEAD: $CB" '```'
ta anker-to 1 '2 HEAD-linje' 1 "$CC" "HEAD: $CA" "HEAD: $CB"
ta anker-av 0 'GRØNN (ANKER AV)' 1 '' "HEAD: $CB"
ta anker-tip-ukjent 2 'ukjent tip' 1 finnes-ikke "HEAD: $CB"
[ $fail = 0 ] && echo "ALLE OK" || exit 1
