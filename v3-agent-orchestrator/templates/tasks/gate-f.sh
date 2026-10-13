#!/usr/bin/env bash
# Gate F (F0–F4) som ett kall. Denne fila er ENESTE definisjon av gaten.
# Bruk: tasks/gate-f.sh <planfil> <N> [F3a_ref] [tip]   |   tasks/gate-f.sh <planfil> ref
# Implementeren kjører den FØR fix-rapporten; koordinatoren kjører den på branch-snapshotet.
# Exit 0 = GRØNN, 1 = RØD (mekanisk retur), 2 = bruksfeil. F5 (stikkprøve) er fortsatt manuell.
# Fanger formfeil i V-blokka før planen sendes til review.
# Regler (test: bash tasks/test-gate-f.sh):
# 1. En ID-linje er, utenfor kodegjerder: valgfritt sitat-/listeprefiks, så **, | eller ### , så ID-en,
#    så et skilletegn. En ID har siffer (V9, V-B4). Prosa uten dekorasjon er aldri en ID-linje.
# 2. Sikkerhetsnett: en linje i § Verifisering som starter med **, |, # eller backtick fulgt av en
#    V-ID som ikke ble lest etter regel 1, gir RØD med ID-en navngitt. Kursiv er ikke en etikett.
# 3. Én V-ID per linje. Range (V7–V13) og sammenslåtte overskrifter telles ikke.
# 4. Sub-kriterier rulles opp: V11a og V2-R0b leses som V11 og V2, V-B4w som V-B4.
# 5. En ID er eier-kjørt når minst én av ID-linjene dens i § Verifisering bærer [koordinator] eller
#    [eier]. Eier-kjørte ID-er er unntatt gulvet og fence-kravet, og står med navn i ref-en.
# 6. Ankeret: fix-runde-seksjonen har nøyaktig én linje «HEAD: <sha>» utenfor kodegjerder,
#    med kode-commitens SHA. Med <tip> kreves at ankeret er forfar-lik <tip>, og at bare tasks/plans/
#    er endret mellom dem. <tip> er HEAD hos implementeren og origin/<branch> hos koordinatoren.
#    Uten <tip> sjekkes ikke ankeret, og gaten skriver ANKER AV.
set -uo pipefail
P=${1:?planfil}; N=${2:?fix-runde N, eller «ref»}; REF=${3:-}; TIP=${4:-}; AV=
[ -f "$P" ] || { echo "finner ikke $P" >&2; exit 2; }
[ -z "$TIP" ] || git rev-parse -q --verify "$TIP^{commit}" >/dev/null || { echo "ukjent tip: $TIP" >&2; exit 2; }
ID='^[[:space:]>-]*(\*\*|\| ?(\*\*)?|#{3,6} )(V[0-9]+|V-[A-Z]+[0-9]+)[a-z]?(-[0-9A-Za-z]+)*[[:space:]]*(\*\*|\||—|–|:|\(|\.|$).*'
OWN='\[(koordinator|eier)\]'
H="#### V-blokk re-kjørt mot HEAD (fix-runde $N)"
D=$(mktemp -d); trap 'rm -rf "$D"' EXIT
ids() { sed -nE "s/$ID/\\3/p" | sort -u; }
n() { wc -l < "$1" | tr -d ' '; }
j() { paste -sd"$1" "$2"; }
awk '/^```/{c=!c;next} c{next} /^## .*([Vv]erifisering|V-kriterier)/&&!s{s=1;f=1;next} f&&/^#{1,2} /{f=0} f' "$P" > "$D/sec"
ids < "$D/sec" > "$D/all"
grep -E "$ID" "$D/sec" | grep -iE "$OWN" | ids > "$D/exempt"
comm -23 "$D/all" "$D/exempt" > "$D/owned"
# Sikkerhetsnett: alt i § Verifisering som LIGNER en ID-etikett, men ikke ble lest som en.
awk '{ l=$0; sub(/^[[:space:]>-]*([0-9]+\. |\[[ xX]\] )?/,"",l); if (l !~ /^(\*\*|[|#`])[^[:alnum:]]*V(-[A-Z]|[0-9])/) next
  sub(/^[^[:alnum:]]*/,"",l); e=match(l,/\*\*|\||`/); if (e) l=substr(l,1,e-1)
  while (match(l,/V[0-9]+|V-[A-Z]+[0-9]*/)) { print substr(l,RSTART,RLENGTH); l=substr(l,RSTART+RLENGTH) } }' "$D/sec" | sort -u | comm -23 - "$D/all" > "$D/unread"
F3a=$(n "$D/all"); F3e=$(n "$D/owned")
REFNOW=$F3a; [ -s "$D/exempt" ] && REFNOW="$F3a:$(j , "$D/exempt")"
fail=(); pf=()
[ "$F3a" -gt 0 ] || pf+=("F3a=0 — fant ingen V-kriterier under «## …Verifisering»/«## …V-kriterier» (UGYLDIG, ikke legacy)")
[ -s "$D/unread" ] && pf+=("ID-lignende, men ulest i § Verifisering: $(j ' ' "$D/unread") — skriv én ID per linje som **V9**, | V9 | eller ### V9 (ID-en må ha siffer, tittel utenfor feten, ingen range eller sammenslåing)")
if [ "$N" = ref ]; then
  [ ${#pf[@]} = 0 ] && { echo "$REFNOW"; exit 0; }
  printf 'RØD: %s\n' "${pf[@]}" >&2; exit 1
fi
awk -v h="$H" '/^```/{c=!c} !c&&$0==h&&!s{s=1;f=1;next} f&&!c&&/^#+ /{f=0} f' "$P" > "$D/w"
awk '/^```/{c=!c;next} !c' "$D/w" > "$D/wtext"
ids < "$D/wtext" > "$D/win"
comm -23 "$D/owned" "$D/win" > "$D/missing"
comm -23 "$D/win" "$D/exempt" > "$D/run"
F0=$(grep -c '^```' "$P")
F1=$(awk '/^```/{c=!c;next} !c' "$P" | grep -cxF "$H")
F2b=$(grep -c '^```' "$D/w")
F2c=$(awk '/^```/{c=!c;next} c&&NF' "$D/w" | wc -l | tr -d ' ')
F3b=$(n "$D/win"); F3r=$(n "$D/run")
F4=$(grep -c -F 'Ingen tall arves fra en tidligere runde.' "$D/wtext")
echo "F0=$F0 F1=$F1 F2b=$F2b F2c=$F2c F3a=$REFNOW${REF:+ (ref $REF)} F3e=$F3e F3b=$F3b F3r=$F3r F4=$F4"
[ $((F0 % 2)) = 0 ] || fail+=("F0 odde (ubalansert kodegjerde)")
[ "$F1" = 1 ] || fail+=("F1=$F1, må være 1 — overskriften må være ordrett: $H")
{ [ $((F2b % 2)) = 0 ] && [ "$F2b" -ge 2 ]; } || fail+=("F2b=$F2b, må være partall og >= 2")
[ "$F3b" -ge 1 ] || fail+=("F3b=0 — V-ID-er må stå på linjestart som **V1** (fet, utenfor kodegjerde)")
[ "$F2b" -ge $((2 * F3r)) ] || fail+=("F2b=$F2b < 2×$F3r — hver av disse trenger egen kodeblokk med output: $(j ' ' "$D/run")")
[ "$F2c" -ge $((2 * F3r)) ] || fail+=("F2c=$F2c < 2×$F3r — for lite faktisk output i kodeblokkene for: $(j ' ' "$D/run")")
[ "$F4" -ge 1 ] || fail+=("F4=0 — mangler setningen «Ingen tall arves fra en tidligere runde.»")
if [ -z "$TIP" ]; then AV=" (ANKER AV)"; echo "ANKER AV (ingen tip) — HEAD-ankeret er ikke sjekket mot branch-tippen"
else
  sed -nE 's/^[[:space:]>*-]*HEAD:[*` ]*([0-9a-f]{7,40})([^0-9A-Za-z].*)?$/\1/p' "$D/wtext" | sort -u > "$D/anchor"
  a=$(j ' ' "$D/anchor")
  if [ "$(n "$D/anchor")" != 1 ]; then fail+=("$(n "$D/anchor") HEAD-linje(r) med SHA i fix-runde-seksjonen (${a:-ingen}), må være nøyaktig 1 — skriv «HEAD: <sha>» på egen linje utenfor kodeblokk")
  elif ! git merge-base --is-ancestor "$a" "$TIP" 2>/dev/null; then fail+=("ankeret $a er ikke forfar til tippen $TIP — V-blokken er målt mot en annen commit enn branchen")
  elif ! git diff --quiet "$a" "$TIP" -- ':(top)' ':(top,exclude)tasks/plans'; then fail+=("annet enn tasks/plans/ er endret mellom ankeret $a og tippen $TIP — commit koden, kjør V-blokken på nytt, skriv nytt anker, commit planfila alene")
  else echo "ANKER OK ($a)"; fi
fi
if [ "$REF" = 0 ]; then
  echo "GULV AV — F3a_ref=0 gitt eksplisitt (kun delt planfil, krever decision-log-rad); logg vblock=legacy"
else
  fail+=(${pf[@]+"${pf[@]}"})
  [ -s "$D/missing" ] && fail+=("mangler i fix-runde-seksjonen: $(j ' ' "$D/missing") — én ID per linje som **V8**; range (V7–V13) og sammenslåtte overskrifter telles ikke; eier-kjørte kriterier merkes [koordinator]/[eier] i § Verifisering")
  if [ -z "$REF" ]; then echo "LÅS AV (ingen F3a_ref) — gulvet håndheves, men § Verifisering er ikke låst"
  elif [ "$REFNOW" != "$REF" ]; then fail+=("F3a=$REFNOW ≠ F3a_ref=$REF — § Verifisering (antall eller hvilke ID-er som er eier-merket) er endret, eller ref er målt med gammel gate: mål på nytt med «ref»")
  fi
fi
[ ${#fail[@]} = 0 ] && { echo "GATE F (F0–F4): GRØNN$AV — F5 stikkprøve gjenstår"; exit 0; }
printf 'RØD: %s\n' "${fail[@]}"; exit 1
