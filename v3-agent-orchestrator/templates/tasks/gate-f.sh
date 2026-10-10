#!/usr/bin/env bash
# Gate F (F0–F4) som ett kall — samme kommandoer som steps/5b-kode-review.md § Gate F, ordrett.
# Bruk: tasks/gate-f.sh <planfil> <N> [F3a_ref]
# Implementeren kjører den FØR fix-rapporten; koordinatoren kjører den på branch-snapshotet.
# Exit 0 = GRØNN, 1 = RØD (mekanisk retur), 2 = bruksfeil. F5 (stikkprøve) er fortsatt manuell.
# Fanger formfeil i V-blokka før planen sendes til review.
set -uo pipefail
P=${1:?planfil}; N=${2:?fix-runde N}; REF=${3:-}
[ -f "$P" ] || { echo "finner ikke $P" >&2; exit 2; }
H="#### V-blokk re-kjørt mot HEAD (fix-runde $N)"
W=$(mktemp); trap 'rm -f "$W"' EXIT
F0=$(grep -c '^```' "$P")
F1=$(awk '/^```/{c=!c;next} !c' "$P" | grep -cxF "$H")
awk -v h="$H" '/^```/{fc=!fc} !fc&&$0==h&&!seen{seen=1;f=1;next} f&&/^```/{c=!c} f&&!c&&/^#+ /{f=0} f' "$P" > "$W"
F2b=$(grep -c '^```' "$W")
F2c=$(awk '/^```/{c=!c;next} c&&NF' "$W" | wc -l | tr -d ' ')
F3a=$(awk '/^```/{fc=!fc} !fc&&/^## .*[Vv]erifisering/&&!seen{seen=1;f=1;next} f&&/^```/{c=!c} f&&!c&&/^#{1,2} /{f=0} f' "$P" | grep -oE '^((\| )?\*\*V([0-9]|-[A-Z])[0-9A-Za-z-]*\*\*|#{3,6} V([0-9]|-[A-Z])[0-9A-Za-z-]*)' | sed -E 's/^(#{3,6} |\| )?\*{0,2}//; s/\*{0,2}$//' | sort -u | wc -l | tr -d ' ')
F3b=$(awk '/^```/{c=!c;next} !c' "$W" | grep -oE '^\*\*V([0-9]|-[A-Z])[0-9A-Za-z-]*\*\*' | sort -u | wc -l | tr -d ' ')
F4=$(awk '/^```/{c=!c;next} !c' "$W" | grep -c -F 'Ingen tall arves fra en tidligere runde.')
echo "F0=$F0 F1=$F1 F2b=$F2b F2c=$F2c F3a=$F3a${REF:+ (ref $REF)} F3b=$F3b F4=$F4"
fail=()
[ $((F0 % 2)) = 0 ] || fail+=("F0 odde (ubalansert kodegjerde)")
[ "$F1" = 1 ] || fail+=("F1=$F1, må være 1 — overskriften må være ordrett: $H")
{ [ $((F2b % 2)) = 0 ] && [ "$F2b" -ge 2 ]; } || fail+=("F2b=$F2b, må være partall og >= 2")
[ "$F3b" -ge 1 ] || fail+=("F3b=0 — V-ID-er må stå på linjestart som **V1** (fet, utenfor kodegjerde)")
[ "$F2b" -ge $((2 * F3b)) ] || fail+=("F2b=$F2b < 2×F3b — hver V-ID trenger egen kodeblokk med output")
[ "$F2c" -ge $((2 * F3b)) ] || fail+=("F2c=$F2c < 2×F3b — for lite faktisk output i kodeblokkene")
[ "$F4" -ge 1 ] || fail+=("F4=0 — mangler setningen «Ingen tall arves fra en tidligere runde.»")
if [ -n "$REF" ] && [ "$REF" -gt 0 ]; then
  [ "$F3a" = "$REF" ] || fail+=("F3a=$F3a ≠ F3a_ref=$REF — § verifisering er endret")
  [ "$F3b" -ge "$F3a" ] || fail+=("F3b=$F3b < F3a=$F3a — alle V-kriterier må re-kjøres")
fi
[ ${#fail[@]} = 0 ] && { echo "GATE F (F0–F4): GRØNN — F5 stikkprøve gjenstår"; exit 0; }
printf 'RØD: %s\n' "${fail[@]}"; exit 1
