#!/usr/bin/env bash
# Regresjonstest for gate-f.sh (generert av /setup). Kjøres: bash tasks/test-gate-f.sh
# Selvstendig: bygger en minimal plan med to V-kriterier og én grønn fix-runde-seksjon.
G="$(dirname "$0")/gate-f.sh"; fail=0
P=$(mktemp); M=$(mktemp); trap 'rm -f "$P" "$M"' EXIT
F='```'
cat > "$P" <<PLAN
# Plan

## Verifisering

**V1** — testene er grønne.
**V2** — lint er grønn.

## Fix-runder

#### V-blokk re-kjørt mot HEAD (fix-runde 1)

**V1**
${F}
\$ npm test
ok 12 tests
${F}

**V2**
${F}
\$ npm run lint
0 problems
${F}

Ingen tall arves fra en tidligere runde.
PLAN
t() { "$G" "${@:2}" >/dev/null; got=$?; [ "$got" = "$1" ] && echo "OK   $*" || { echo "AVVIK $* (fikk $got)"; fail=1; }; }
t 0 "$P" 1 2          # grønn fix-runde
t 1 "$P" 1 3          # F3a ≠ ref
t 1 "$P" 9            # overskrift for fix-runde 9 mangler
sed '/^#### V-blokk re-kjørt mot HEAD (fix-runde 1)$/,$ s/^\*\*\(V[0-9]*\)\*\*/\1/' "$P" > "$M"
t 1 "$M" 1 2          # V-ID-er uten fet linjestart-form
grep -v '^Ingen tall arves' "$P" > "$M"
t 1 "$M" 1 2          # attestasjonslinja mangler
t 2 /finnes/ikke.md 1 # bruksfeil
[ $fail = 0 ] && echo "ALLE OK" || exit 1
