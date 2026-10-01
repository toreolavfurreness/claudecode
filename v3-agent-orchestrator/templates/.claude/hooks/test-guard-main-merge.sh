#!/usr/bin/env bash
# {{PROJECT_NAME}} — regresjonsharness for .claude/hooks/guard-main-merge.sh (TODO 188, PR1).
#
# Kjøres: bash .claude/hooks/test-guard-main-merge.sh [sti-til-hook]
# HARNESS_PHASE=pre|post (default pre) velger hvilken forventet fasit (NÅ/ETTER)
# hver rad skåres mot. I PR1 er hooken uendret i begge faser — fase "pre" skal
# være grønn (0 AVVIK), fase "post" er en RØD-fase-demonstrasjon (rader med
# NÅ ≠ ETTER, samt post-only-rader, avviker mot dagens hook med vilje — se
# planens § 8 / Steg 5). Fasit for hver rad = hookens EGEN exit-kode
# (2 = BLOKKERT, 0 = SLIPPER) — ikke grep i eget skall (lesson 2026-08-31).
#
# Radtabellen (case-uttrykkene under) er GENERERT fra planens V1-V5+V4b-tabeller
# av implementerens autoringskript (ikke committet — se PR1-beskrivelsen for
# den mekaniske sed+grep-tellingen mot planfila, § 7.5). 147 rader:
#   V1  (K1-K32,  32) — regresjonsvern, alt dagens hook blokkerer i dag
#   V2  (N1-N40,  40) — nye BLOCK-rader (NEW_BLOCK)
#   V3  (A1-A21,  21) — falsk-positiv-vakt (negativ kontroll)
#   V4  (P1-P32 + P20b + P20c, 34) — parser-robusthet, tegnsett, hook-varianter
#   V4b (KH1-KH8,  8) — [KJENT HULL], DOM=KJENT når uendret
#   V5B (U1-U3,U10-U12, 6) — base-rommet, faste rader (heredoc/flerlinje/prosa)
#   V5C (U13-U18,  6) — oppslagsrommet, faste rader
# EXPECTED_SUM=147, EXPECTED_KNOWN=9 (8 KH-rader + P26), EXPECTED_MUTATIONS=8
# (asserteres FØRST i PR2 sin --mutate-modus; i PR1 finnes ingen mutasjonskjøringer —
# konstanten er deklarert her, men ubrukt, r4-pålegg fix-runde 1, MINDRE-2),
# EXPECTED_SKIP(pre)=12 (post-only-rader), EXPECTED_SKIP(post)=0.
# EXPECTED_SCORED_TOTAL(fase) = EXPECTED_SUM − EXPECTED_KNOWN − EXPECTED_SKIP(fase)
# (r4-pålegg, VIKTIG-5) — altså 126 i fase pre, 138 i fase post.
#
# Push-refspec- og base-generatorene (--gen-refspecs / --gen-baserefs) er en
# UAVHENGIG andre kilde (§ 0.2b): i fase pre sammenlignes referansemodellen
# (§ 5 pkt 10a/10b) mot DAGENS regex, ordrett hentet fra hookfila — ikke mot
# harnessens egen forestilling om hooken. 787 unike push-kandidater,
# 382 BLOCK→ALLOW, 30 ALLOW→BLOCK (r4-pålegg, MINDRE-9 la til en fjerde
# ekstra-akse — se planens § 0.2b).
#
# Ingen nettverkskall. Alle gh-kall går til en per-case stub i $T/bin/gh,
# nådd via GH_BIN-mekanismen (§ 0.5) — i PR1 er det ekvivalent med at hooken
# ikke eksporterer PATH i det hele tatt, så stubben nås uansett (målt i § 0.5,
# variant A). HEAD-oppslags-radene (N39/N40/A21/KH5) bruker et EKTE mini-repo,
# ikke en stub (§ 7.3, BLOKKERENDE-1s andre halvdel; forenklet i r4-pålegg
# MINDRE-8 til `git init -q "$D" && git -C "$D" symbolic-ref HEAD refs/heads/<gren>`,
# uten `git init -b`).

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HARNESS_PHASE="${HARNESS_PHASE:-pre}"

# --list-classes / --diff / --gen-refspecs / --gen-baserefs er egne modi uten
# et enkelt $1=<hook-sti> — hopp over HOOK-oppløsning/eksistenssjekk og
# HARNESS_PHASE-validering for dem (dispatchet under "{{PROD_BRANCH}}", etter at alle
# funksjoner er definert).
case "${1:-}" in
  --list-classes|--diff|--gen-refspecs|--gen-baserefs)
    HOOK=""
    ;;
  *)
    HOOK="${1:-$SCRIPT_DIR/guard-main-merge.sh}"
    if [ ! -f "$HOOK" ]; then
      echo "Fant ikke hook: $HOOK" >&2
      exit 1
    fi
    case "$HARNESS_PHASE" in
      pre|post) ;;
      *)
        echo "Ugyldig HARNESS_PHASE=$HARNESS_PHASE (må være pre eller post)" >&2
        exit 1
        ;;
    esac
    ;;
esac

EXPECTED_SUM=147
EXPECTED_KNOWN=9
# Asserteres FØRST i PR2 sin --mutate-modus; PR1 har ingen mutasjonskjøringer og
# denne konstanten er derfor ubrukt her (r4-pålegg fix-runde 1, MINDRE-2).
EXPECTED_MUTATIONS=8
if [ "$HARNESS_PHASE" = "pre" ]; then
  EXPECTED_SKIP=12
else
  EXPECTED_SKIP=0
fi
EXPECTED_SCORED_TOTAL=$((EXPECTED_SUM - EXPECTED_KNOWN - EXPECTED_SKIP))

# ───────────────────────── generert radtabell ────────────────────────────
# (se scratchpad/gen_harness.py hos implementeren for autoringsskriptet;
#  denne fila selv er den committede kilden — skriptet er ikke committet)

row_cmd() {
  case "$1" in
    K1) cat <<'CMDEOF'
git push origin {{PROD_BRANCH}}
CMDEOF
      ;;
    K2) cat <<'CMDEOF'
git push --set-upstream origin {{PROD_BRANCH}}
CMDEOF
      ;;
    K3) cat <<'CMDEOF'
git push origin HEAD:refs/heads/{{PROD_BRANCH}}
CMDEOF
      ;;
    K4) cat <<'CMDEOF'
git push origin {{BASE_BRANCH}}
CMDEOF
      ;;
    K5) cat <<'CMDEOF'
gh api --method PUT repos/org/repo/pulls/$PR_NUM/merge
CMDEOF
      ;;
    K6) cat <<'CMDEOF'
git push --force origin {{PROD_BRANCH}}
CMDEOF
      ;;
    K7) cat <<'CMDEOF'
git push origin :{{PROD_BRANCH}}
CMDEOF
      ;;
    K8) cat <<'CMDEOF'
gh pr create --title "x"
CMDEOF
      ;;
    K9) cat <<'CMDEOF'
gh pr create --title "x" --base {{PROD_BRANCH}}
CMDEOF
      ;;
    K10) cat <<'CMDEOF'
gh pr create --title "x" -B {{PROD_BRANCH}}
CMDEOF
      ;;
    K11) cat <<'CMDEOF'
gh pr create --title "x" --body "$(cat <<'EOF'
Some body text
EOF
)"
CMDEOF
      ;;
    K12) cat <<'CMDEOF'
gh pr create --title "x" --body "$(cat <<'EOF'
Husk aa bruke --base {{BASE_BRANCH}} naar du oppretter PR
EOF
)"
CMDEOF
      ;;
    K13) cat <<'CMDEOF'
gh pr create --title "x" --body "$(cat <<'EOF'
Bruk -B {{BASE_BRANCH}} som flagg
EOF
)"
CMDEOF
      ;;
    K14) cat <<'CMDEOF'
gh pr merge 123 --merge
CMDEOF
      ;;
    K15) cat <<'CMDEOF'
gh pr merge 123 --merge
CMDEOF
      ;;
    K16) cat <<'CMDEOF'
gh pr merge --merge
CMDEOF
      ;;
    K17) cat <<'CMDEOF'
gh api --method PUT repos/o/r/pulls/456/merge
CMDEOF
      ;;
    K18) cat <<'CMDEOF'
gh api -XPUT "repos/{owner}/{repo}/pulls/456/merge"
CMDEOF
      ;;
    K19) cat <<'CMDEOF'
gh api --method='PUT' repos/o/r/pulls/456/merge
CMDEOF
      ;;
    K20) cat <<'CMDEOF'
gh pr create --title "x" --base development
CMDEOF
      ;;
    K21) cat <<'CMDEOF'
gh pr create --title "x" --base "{{BASE_BRANCH}}"
CMDEOF
      ;;
    K22) cat <<'CMDEOF'
gh pr create --title "x" --base={{BASE_BRANCH}}
CMDEOF
      ;;
    K23) cat <<'CMDEOF'
gh pr create --title "x" --base {{BASE_BRANCH}}
CMDEOF
      ;;
    K24) cat <<'CMDEOF'
gh pr create --title "x" --base {{BASE_BRANCH}} --body "$(cat <<'EOF'
Se ogsaa --base {{PROD_BRANCH}} naevnt i teksten
EOF
)"
CMDEOF
      ;;
    K25) cat <<'CMDEOF'
gh pr merge --help
CMDEOF
      ;;
    K26) cat <<'CMDEOF'
gh pr create --help
CMDEOF
      ;;
    K27) cat <<'CMDEOF'
git push origin {{BASE_BRANCH}}:{{PROD_BRANCH}}
CMDEOF
      ;;
    K28) cat <<'CMDEOF'
git push origin {{PROD_BRANCH}}~1:{{PROD_BRANCH}}
CMDEOF
      ;;
    K29) cat <<'CMDEOF'
git push origin {{PROD_BRANCH}}^{}:{{BASE_BRANCH}}
CMDEOF
      ;;
    K30) cat <<'CMDEOF'
git push origin +HEAD:{{PROD_BRANCH}}
CMDEOF
      ;;
    K31) cat <<'CMDEOF'
git push origin +refs/heads/{{PROD_BRANCH}}
CMDEOF
      ;;
    K32) cat <<'CMDEOF'
git push origin {{PROD_BRANCH}}:{{BASE_BRANCH}}
CMDEOF
      ;;
    N1) cat <<'CMDEOF'
git add -A
git push origin {{PROD_BRANCH}}
CMDEOF
      ;;
    N2) cat <<'CMDEOF'
cd x && git push origin {{PROD_BRANCH}}
CMDEOF
      ;;
    N3) cat <<'CMDEOF'
gh api \
  --method PUT \
  repos/o/r/pulls/456/merge
CMDEOF
      ;;
    N4) cat <<'CMDEOF'
git push origin {{BASE_BRANCH}}
git push origin {{PROD_BRANCH}}
CMDEOF
      ;;
    N5) cat <<'CMDEOF'
git commit -m "x" && git push origin {{PROD_BRANCH}}
CMDEOF
      ;;
    N6) cat <<'CMDEOF'
git push origin "{{PROD_BRANCH}}"
CMDEOF
      ;;
    N7) cat <<'CMDEOF'
git push origin '{{PROD_BRANCH}}'
CMDEOF
      ;;
    N8) cat <<'CMDEOF'
git -C . push origin {{PROD_BRANCH}}
CMDEOF
      ;;
    N9) cat <<'CMDEOF'
GIT_TRACE=1 git push origin {{PROD_BRANCH}}
CMDEOF
      ;;
    N10) cat <<'CMDEOF'
/usr/bin/git push origin {{PROD_BRANCH}}
CMDEOF
      ;;
    N11) cat <<'CMDEOF'
command git push origin {{PROD_BRANCH}}
CMDEOF
      ;;
    N12) cat <<'CMDEOF'
sh -c "git push origin {{PROD_BRANCH}}"
CMDEOF
      ;;
    N13) cat <<'CMDEOF'
bash -c 'git push origin {{PROD_BRANCH}}'
CMDEOF
      ;;
    N14) cat <<'CMDEOF'
gh pr create --title x --base={{PROD_BRANCH}}
CMDEOF
      ;;
    N15) cat <<'CMDEOF'
gh pr create --title x --base "{{PROD_BRANCH}}"
CMDEOF
      ;;
    N16) cat <<'CMDEOF'
gh pr create --title x --base '{{PROD_BRANCH}}'
CMDEOF
      ;;
    N17) cat <<'CMDEOF'
gh pr create --title x --base "$BR"
CMDEOF
      ;;
    N18) cat <<'CMDEOF'
# rydder opp
git push origin {{PROD_BRANCH}}
CMDEOF
      ;;
    N19) cat <<'CMDEOF'
echo hei; git push origin {{PROD_BRANCH}}
CMDEOF
      ;;
    N20) cat <<'CMDEOF'
git push origin {{PROD_BRANCH}} # kommentar
CMDEOF
      ;;
    N21) cat <<'CMDEOF'
echo "$(git push origin {{PROD_BRANCH}})"
CMDEOF
      ;;
    N22) cat <<'CMDEOF'
gh pr merge 123 --merge --repo other/repo
CMDEOF
      ;;
    N23) cat <<'CMDEOF'
g\it push origin {{PROD_BRANCH}}
CMDEOF
      ;;
    N24) cat <<'CMDEOF'
gh pr create --title x --body "husk --base {{BASE_BRANCH}}"
CMDEOF
      ;;
    N25) cat <<'CMDEOF'
git push --mirror origin
CMDEOF
      ;;
    N26) cat <<'CMDEOF'
gh pr edit 123 --base {{PROD_BRANCH}}
CMDEOF
      ;;
    N27) cat <<'CMDEOF'
g''it push origin {{PROD_BRANCH}}
CMDEOF
      ;;
    N28) cat <<'CMDEOF'
"git" "push" origin {{PROD_BRANCH}}
CMDEOF
      ;;
    N29) cat <<'CMDEOF'
gh api graphql -f query='mutation { mergePullRequest(input: {x}) }'
CMDEOF
      ;;
    N30) cat <<'CMDEOF'
git push origin +{{PROD_BRANCH}}
CMDEOF
      ;;
    N31) cat <<'CMDEOF'
git push nonexistent-remote {{PROD_BRANCH}}
CMDEOF
      ;;
    N32) cat <<'CMDEOF'
git push --all origin
CMDEOF
      ;;
    N33) cat <<'CMDEOF'
git push upstream {{PROD_BRANCH}}
CMDEOF
      ;;
    N34) cat <<'CMDEOF'
gh pr merge 123 --merge -R other/repo
CMDEOF
      ;;
    N35) cat <<'CMDEOF'
gh pr merge 123 --merge --repo "$R"
CMDEOF
      ;;
    N36) cat <<'CMDEOF'
gh api --method PUT repos/other/repo/pulls/456/merge
CMDEOF
      ;;
    N37) cat <<'CMDEOF'
gh api graphql --input mutation.json
CMDEOF
      ;;
    N38) cat <<'CMDEOF'
gh api graphql -f query=@mutation.graphql
CMDEOF
      ;;
    N39) cat <<'CMDEOF'
git push
CMDEOF
      ;;
    N40) cat <<'CMDEOF'
git push origin
CMDEOF
      ;;
    A1) cat <<'CMDEOF'
npm run lint
CMDEOF
      ;;
    A2) cat <<'CMDEOF'
git status
CMDEOF
      ;;
    A3) cat <<'CMDEOF'
git log --oneline -5
CMDEOF
      ;;
    A4) cat <<'CMDEOF'
git fetch origin {{BASE_BRANCH}} && git merge origin/{{BASE_BRANCH}}
CMDEOF
      ;;
    A5) cat <<'CMDEOF'
git push origin claude/todo-188-x
CMDEOF
      ;;
    A6) cat <<'CMDEOF'
echo "aldri git push origin {{PROD_BRANCH}}"
CMDEOF
      ;;
    A7) cat <<'CMDEOF'
# git push origin {{PROD_BRANCH}}
CMDEOF
      ;;
    A8) cat <<'CMDEOF'
cat > f.md <<'EOF'
Kjør git push origin {{PROD_BRANCH}} manuelt
EOF
CMDEOF
      ;;
    A9) cat <<'CMDEOF'
gh pr merge 123 --merge
CMDEOF
      ;;
    A10) cat <<'CMDEOF'
gh api --method PUT "repos/{owner}/{repo}/pulls/456/merge" -f merge_method=merge
CMDEOF
      ;;
    A11) cat <<'CMDEOF'
gh pr view 123 --json baseRefName
CMDEOF
      ;;
    A12) cat <<'CMDEOF'
gh api repos/{owner}/{repo}/pulls/456 --jq .base.ref
CMDEOF
      ;;
    A13) cat <<'CMDEOF'
sh -c "echo hei"
CMDEOF
      ;;
    A14) cat <<'CMDEOF'
grep -rn "git push origin {{PROD_BRANCH}}" docs/
CMDEOF
      ;;
    A15) cat <<'CMDEOF'
ls src/github/api.ts
CMDEOF
      ;;
    A16) cat <<'CMDEOF'
gh pr merge 123 --merge
CMDEOF
      ;;
    A17) cat <<'CMDEOF'
gh pr edit 123 --base {{BASE_BRANCH}}
CMDEOF
      ;;
    A18) cat <<'CMDEOF'
gh pr edit 123 --title "x"
CMDEOF
      ;;
    A19) cat <<'CMDEOF'
gh api graphql -f query='query { repository { name } }'
CMDEOF
      ;;
    A20) cat <<'CMDEOF'
git push origin {{PROD_BRANCH}}-fix
CMDEOF
      ;;
    A21) cat <<'CMDEOF'
git push
CMDEOF
      ;;
    P1) cat <<'CMDEOF'
gh pr create --title x --body "$(cat <<-EOF
  tekst
  EOF
)" --base {{BASE_BRANCH}}
CMDEOF
      ;;
    P2) cat <<'CMDEOF'
gh pr create --title x --body "$(cat <<'EOF'
  tekst
  EOF
)" --base {{BASE_BRANCH}}
CMDEOF
      ;;
    P3) cat <<'CMDEOF'
gh pr create --title x --body "$(cat <<"EOF"
  tekst
  EOF
)" --base {{BASE_BRANCH}}
CMDEOF
      ;;
    P4) cat <<'CMDEOF'
gh pr create --title "x" --body "$(cat <<\EOF
--base {{BASE_BRANCH}} nevnt i prosa
EOF
)"
CMDEOF
      ;;
    P5) cat <<'CMDEOF'
gh pr create --title "x" --body "linje1
Husk --base {{BASE_BRANCH}} her"
CMDEOF
      ;;
    P6) cat <<'CMDEOF'
gh pr create --title "x" \
  --body "Husk --base {{BASE_BRANCH}} naar du lager PR"
CMDEOF
      ;;
    P7) cat <<'CMDEOF'
echo "git push origin {{PROD_BRANCH}}
CMDEOF
      ;;
    P8) cat <<'CMDEOF'
echo "hei
CMDEOF
      ;;
    P9) cat <<'CMDEOF'
git push origin {{PROD_BRANCH}} <<< x
CMDEOF
      ;;
    P12) cat <<'CMDEOF'
git push origin {{BASE_BRANCH}}
CMDEOF
      ;;
    P13) cat <<'CMDEOF'
npm run lint
CMDEOF
      ;;
    P14) cat <<'CMDEOF'
git push origin feature/{{PROD_BRANCH}}
CMDEOF
      ;;
    P15) cat <<'CMDEOF'
git push origin mainline
CMDEOF
      ;;
    P16) cat <<'CMDEOF'
echo a\;git push origin {{PROD_BRANCH}}
CMDEOF
      ;;
    P17) cat <<'CMDEOF'
git push origin ma\in
CMDEOF
      ;;
    P18) cat <<'CMDEOF'
git push origin {{BASE_BRANCH}}
CMDEOF
      ;;
    P19) cat <<'CMDEOF'
git push origin {{BASE_BRANCH}}
CMDEOF
      ;;
    P20) cat <<'CMDEOF'
gh pr merge 123 --merge
CMDEOF
      ;;
    P20b) cat <<'CMDEOF'
gh pr merge 123 --merge
CMDEOF
      ;;
    P20c) cat <<'CMDEOF'
gh pr merge 123 --merge
CMDEOF
      ;;
    P21) cat <<'CMDEOF'
gh pr create --title "x" --base {{BASE_BRANCH}} --body "$(cat <<'EOF'
Se koden i funksjonen f(x) — og (merk) parentesene
EOF
)"
CMDEOF
      ;;
    P22) cat <<'CMDEOF'
gh pr create --title "x" --base {{BASE_BRANCH}} --body "Toget gaar'nt i dag, sa vi tar bilen"
CMDEOF
      ;;
    P23) cat <<'CMDEOF'
gh pr create --title "x" --base {{BASE_BRANCH}} --body "kjor `npm test` for du merger"
CMDEOF
      ;;
    P24) cat <<'CMDEOF'
gh pr create --title "x" --base {{BASE_BRANCH}} --body "Ferdig ✅ — æøå og ÆØÅ"
CMDEOF
      ;;
    P25) cat <<'CMDEOF'
gh pr create --title "x" --base {{BASE_BRANCH}} --body "enslig ` backtick"
CMDEOF
      ;;
    P26) cat <<'CMDEOF'
sh -c "$SCRIPT"
CMDEOF
      ;;
    P27) cat <<'CMDEOF'
gh api --method PUT repos/{owner}/repo/pulls/456/merge
CMDEOF
      ;;
    P29) cat <<'CMDEOF'
git push origin {{BASE_BRANCH}}
CMDEOF
      ;;
    P31) cat <<'CMDEOF'
gh pr merge 123 --merge
CMDEOF
      ;;
    P32) cat <<'CMDEOF'
gh pr merge 123 --merge
CMDEOF
      ;;
    KH1) cat <<'CMDEOF'
$(echo git) push origin {{PROD_BRANCH}}
CMDEOF
      ;;
    KH2) cat <<'CMDEOF'
git push origin "$BRANCH"
CMDEOF
      ;;
    KH3) cat <<'CMDEOF'
gh pr edit 123 --base "$B"
CMDEOF
      ;;
    KH4) cat <<'CMDEOF'
nohup git push origin {{PROD_BRANCH}}
CMDEOF
      ;;
    KH5) cat <<'CMDEOF'
git push
CMDEOF
      ;;
    KH6) cat <<'CMDEOF'
gh api graphql -f query="$(cat <<'EOF'
mutation { mergePullRequest(x) }
EOF
)"
CMDEOF
      ;;
    KH7) cat <<'CMDEOF'
Q='mutation { mergePullRequest(x) }'; gh api graphql -f query="$Q"
CMDEOF
      ;;
    KH8) cat <<'CMDEOF'
git push origin //{{PROD_BRANCH}}
CMDEOF
      ;;
    U1) cat <<'CMDEOF'
gh pr create --title "x" --body "$(cat <<'EOF'
Some body text
EOF
)" --base {{BASE_BRANCH}}
CMDEOF
      ;;
    U2) cat <<'CMDEOF'
gh pr create --title "x" \
  --base {{BASE_BRANCH}}
CMDEOF
      ;;
    U3) cat <<'CMDEOF'
gh pr create --title "x" -B {{BASE_BRANCH}}
CMDEOF
      ;;
    U10) cat <<'CMDEOF'
gh pr create --title x --base {{PROD_BRANCH}}-fix
CMDEOF
      ;;
    U11) cat <<'CMDEOF'
gh pr create --title x --base {{PROD_BRANCH}}/foo
CMDEOF
      ;;
    U12) cat <<'CMDEOF'
gh pr create --title x --base {{BASE_BRANCH}} --body "se --base {{PROD_BRANCH}} i prosa"
CMDEOF
      ;;
    U13) cat <<'CMDEOF'
gh pr merge --repo other/repo 123 --merge
CMDEOF
      ;;
    U14) cat <<'CMDEOF'
gh pr merge "123" --merge
CMDEOF
      ;;
    U15) cat <<'CMDEOF'
gh pr merge --merge 123
CMDEOF
      ;;
    U16b) cat <<'CMDEOF'
gh api --method PUT repos/other/repo/pulls/456/merge
CMDEOF
      ;;
    U17) cat <<'CMDEOF'
gh api -X PUT repos/o/r/pulls/456/merge
CMDEOF
      ;;
    U18) cat <<'CMDEOF'
gh pr merge --repo other/repo --merge 123
CMDEOF
      ;;
    *) return 1 ;;
  esac
}

row_meta() {
  case "$1" in
    K1) printf '%s%s%s%s%s%s%s%s%s%s\n' 'both' '0' 'BLOCK' 'BLOCK' '' '' '' 'A-PUSH-MAIN' 'A-PUSH-MAIN' 'git push origin {{PROD_BRANCH}}' ;;
    K2) printf '%s%s%s%s%s%s%s%s%s%s\n' 'both' '0' 'BLOCK' 'BLOCK' '' '' '' 'A-PUSH-MAIN' 'A-PUSH-MAIN' 'git push --set-upstream origin {{PROD_BRANCH}}' ;;
    K3) printf '%s%s%s%s%s%s%s%s%s%s\n' 'both' '0' 'BLOCK' 'BLOCK' '' '' '' 'A-PUSH-MAIN' 'A-PUSH-MAIN' 'git push origin HEAD:refs/heads/{{PROD_BRANCH}}' ;;
    K4) printf '%s%s%s%s%s%s%s%s%s%s\n' 'both' '0' 'ALLOW' 'ALLOW' '' '' '' '' '' 'git push origin {{BASE_BRANCH}}' ;;
    K5) printf '%s%s%s%s%s%s%s%s%s%s\n' 'both' '0' 'BLOCK' 'BLOCK' '' 'INGEN' 'INGEN' 'A-REST-UTEN-PR' 'A-REST-UTEN-PR' 'REST-merge med shell-variabel (fail-safe, ingen nettverk)' ;;
    K6) printf '%s%s%s%s%s%s%s%s%s%s\n' 'both' '0' 'BLOCK' 'BLOCK' '' '' '' 'A-PUSH-MAIN' 'A-PUSH-MAIN' 'git push --force origin {{PROD_BRANCH}}' ;;
    K7) printf '%s%s%s%s%s%s%s%s%s%s\n' 'both' '0' 'BLOCK' 'BLOCK' '' '' '' 'A-PUSH-MAIN' 'A-PUSH-MAIN' 'git push origin :{{PROD_BRANCH}}' ;;
    K8) printf '%s%s%s%s%s%s%s%s%s%s\n' 'both' '0' 'BLOCK' 'BLOCK' '' '' '' 'A-BASE-MANGLER' 'A-BASE-MANGLER' 'gh pr create uten --base' ;;
    K9) printf '%s%s%s%s%s%s%s%s%s%s\n' 'both' '0' 'BLOCK' 'BLOCK' '' '' '' 'A-BASE-MAIN' 'A-BASE-MAIN' 'gh pr create --base {{PROD_BRANCH}}' ;;
    K10) printf '%s%s%s%s%s%s%s%s%s%s\n' 'both' '0' 'BLOCK' 'BLOCK' '' '' '' 'A-BASE-MANGLER' 'A-BASE-MAIN' 'gh pr create -B {{PROD_BRANCH}} (aarsak endres NAA->ETTER)' ;;
    K11) printf '%s%s%s%s%s%s%s%s%s%s\n' 'both' '0' 'BLOCK' 'BLOCK' '' '' '' 'A-BASE-MANGLER' 'A-BASE-MANGLER' 'heredoc-body, uten --base' ;;
    K12) printf '%s%s%s%s%s%s%s%s%s%s\n' 'both' '0' 'BLOCK' 'BLOCK' '' '' '' 'A-BASE-MANGLER' 'A-BASE-MANGLER' 'body naevner --base {{BASE_BRANCH}} i prosa' ;;
    K13) printf '%s%s%s%s%s%s%s%s%s%s\n' 'both' '0' 'BLOCK' 'BLOCK' '' '' '' 'A-BASE-MANGLER' 'A-BASE-MANGLER' 'body naevner -B {{BASE_BRANCH}} i prosa' ;;
    K14) printf '%s%s%s%s%s%s%s%s%s%s\n' 'both' '0' 'BLOCK' 'BLOCK' '' 'pr view 123 --json baseRefName -q .baseRefName' 'api repos/{owner}/{repo}/pulls/123 --jq .base.ref' 'A-MERGE-BASE-MAIN' 'A-MERGE-BASE-MAIN' 'gh pr merge 123, base={{PROD_BRANCH}}' ;;
    K15) printf '%s%s%s%s%s%s%s%s%s%s\n' 'both' '0' 'BLOCK' 'BLOCK' '' 'pr view 123 --json baseRefName -q .baseRefName' 'api repos/{owner}/{repo}/pulls/123 --jq .base.ref' 'A-MERGE-UBEKREFTET' 'A-MERGE-UBEKREFTET' 'gh pr merge 123, stub feiler' ;;
    K16) printf '%s%s%s%s%s%s%s%s%s%s\n' 'both' '0' 'BLOCK' 'BLOCK' '' 'INGEN' 'INGEN' 'A-MERGE-UTEN-PR' 'A-MERGE-UTEN-PR' 'gh pr merge --merge, ingen ikke-flagg-token' ;;
    K17) printf '%s%s%s%s%s%s%s%s%s%s\n' 'both' '0' 'BLOCK' 'BLOCK' '' 'pr view 456 --json baseRefName -q .baseRefName' 'api repos/o/r/pulls/456 --jq .base.ref' 'A-REST-BASE-MAIN' 'A-REST-BASE-MAIN' 'gh api --method PUT .../456/merge' ;;
    K18) printf '%s%s%s%s%s%s%s%s%s%s\n' 'both' '0' 'BLOCK' 'BLOCK' '' 'pr view 456 --json baseRefName -q .baseRefName' 'api repos/{owner}/{repo}/pulls/456 --jq .base.ref' 'A-REST-BASE-MAIN' 'A-REST-BASE-MAIN' 'gh api -XPUT .../456/merge' ;;
    K19) printf '%s%s%s%s%s%s%s%s%s%s\n' 'both' '0' 'BLOCK' 'BLOCK' '' 'pr view 456 --json baseRefName -q .baseRefName' 'api repos/o/r/pulls/456 --jq .base.ref' 'A-REST-BASE-MAIN' 'A-REST-BASE-MAIN' 'gh api --method='\''PUT'\'' .../456/merge' ;;
    K20) printf '%s%s%s%s%s%s%s%s%s%s\n' 'both' '0' 'ALLOW' 'ALLOW' '' '' '' '' '' '--base development (grense)' ;;
    K21) printf '%s%s%s%s%s%s%s%s%s%s\n' 'both' '0' 'ALLOW' 'ALLOW' '' '' '' '' '' '--base "{{BASE_BRANCH}}"' ;;
    K22) printf '%s%s%s%s%s%s%s%s%s%s\n' 'both' '0' 'ALLOW' 'ALLOW' '' '' '' '' '' '--base={{BASE_BRANCH}}' ;;
    K23) printf '%s%s%s%s%s%s%s%s%s%s\n' 'both' '0' 'ALLOW' 'ALLOW' '' '' '' '' '' '--base {{BASE_BRANCH}}' ;;
    K24) printf '%s%s%s%s%s%s%s%s%s%s\n' 'both' '0' 'ALLOW' 'ALLOW' '' '' '' '' '' '--base {{BASE_BRANCH}} + body naevner --base {{PROD_BRANCH}}' ;;
    K25) printf '%s%s%s%s%s%s%s%s%s%s\n' 'both' '0' 'BLOCK' 'BLOCK' '' 'INGEN' 'INGEN' 'A-MERGE-UTEN-PR' 'A-MERGE-UTEN-PR' 'gh pr merge --help' ;;
    K26) printf '%s%s%s%s%s%s%s%s%s%s\n' 'both' '0' 'BLOCK' 'BLOCK' '' 'INGEN' 'INGEN' 'A-BASE-MANGLER' 'A-BASE-MANGLER' 'gh pr create --help' ;;
    K27) printf '%s%s%s%s%s%s%s%s%s%s\n' 'both' '0' 'BLOCK' 'BLOCK' '' '' '' 'A-PUSH-MAIN' 'A-PUSH-MAIN' '{{BASE_BRANCH}}:{{PROD_BRANCH}}' ;;
    K28) printf '%s%s%s%s%s%s%s%s%s%s\n' 'both' '0' 'BLOCK' 'BLOCK' '' '' '' 'A-PUSH-MAIN' 'A-PUSH-MAIN' '{{PROD_BRANCH}}~1:{{PROD_BRANCH}}' ;;
    K29) printf '%s%s%s%s%s%s%s%s%s%s\n' 'both' '0' 'BLOCK' 'BLOCK' '' '' '' 'A-PUSH-MAIN' 'A-PUSH-MAIN' '{{PROD_BRANCH}}^{}:{{BASE_BRANCH}}' ;;
    K30) printf '%s%s%s%s%s%s%s%s%s%s\n' 'both' '0' 'BLOCK' 'BLOCK' '' '' '' 'A-PUSH-MAIN' 'A-PUSH-MAIN' '+HEAD:{{PROD_BRANCH}}' ;;
    K31) printf '%s%s%s%s%s%s%s%s%s%s\n' 'both' '0' 'BLOCK' 'BLOCK' '' '' '' 'A-PUSH-MAIN' 'A-PUSH-MAIN' '+refs/heads/{{PROD_BRANCH}}' ;;
    K32) printf '%s%s%s%s%s%s%s%s%s%s\n' 'both' '0' 'BLOCK' 'BLOCK' '' '' '' 'A-PUSH-MAIN' 'A-PUSH-MAIN' '{{PROD_BRANCH}}:{{BASE_BRANCH}}' ;;
    N1) printf '%s%s%s%s%s%s%s%s%s%s\n' 'both' '0' 'ALLOW' 'BLOCK' 'NEW_BLOCK' '' '' '' 'A-PUSH-MAIN' 'flerlinjet: add / push {{PROD_BRANCH}}' ;;
    N2) printf '%s%s%s%s%s%s%s%s%s%s\n' 'both' '0' 'ALLOW' 'BLOCK' 'NEW_BLOCK' '' '' '' 'A-PUSH-MAIN' 'cd x && push {{PROD_BRANCH}}' ;;
    N3) printf '%s%s%s%s%s%s%s%s%s%s\n' 'both' '0' 'ALLOW' 'BLOCK' 'NEW_BLOCK' 'INGEN' 'api repos/o/r/pulls/456 --jq .base.ref' '' 'A-REST-BASE-MAIN' 'flerlinjet REST-merge (backslash-fortsettelse)' ;;
    N4) printf '%s%s%s%s%s%s%s%s%s%s\n' 'both' '0' 'ALLOW' 'BLOCK' 'NEW_BLOCK' '' '' '' 'A-PUSH-MAIN' 'push {{BASE_BRANCH}} deretter push {{PROD_BRANCH}}' ;;
    N5) printf '%s%s%s%s%s%s%s%s%s%s\n' 'both' '0' 'ALLOW' 'BLOCK' 'NEW_BLOCK' '' '' '' 'A-PUSH-MAIN' 'commit && push {{PROD_BRANCH}}' ;;
    N6) printf '%s%s%s%s%s%s%s%s%s%s\n' 'both' '0' 'ALLOW' 'BLOCK' 'NEW_BLOCK' '' '' '' 'A-PUSH-MAIN' 'push origin "{{PROD_BRANCH}}" (dobbeltsitat)' ;;
    N7) printf '%s%s%s%s%s%s%s%s%s%s\n' 'both' '0' 'ALLOW' 'BLOCK' 'NEW_BLOCK' '' '' '' 'A-PUSH-MAIN' 'push origin '\''{{PROD_BRANCH}}'\'' (enkeltsitat)' ;;
    N8) printf '%s%s%s%s%s%s%s%s%s%s\n' 'both' '0' 'ALLOW' 'BLOCK' 'NEW_BLOCK' '' '' '' 'A-PUSH-MAIN' 'git -C . push origin {{PROD_BRANCH}}' ;;
    N9) printf '%s%s%s%s%s%s%s%s%s%s\n' 'both' '0' 'ALLOW' 'BLOCK' 'NEW_BLOCK' '' '' '' 'A-PUSH-MAIN' 'env-prefiks foran git' ;;
    N10) printf '%s%s%s%s%s%s%s%s%s%s\n' 'both' '0' 'ALLOW' 'BLOCK' 'NEW_BLOCK' '' '' '' 'A-PUSH-MAIN' 'absolutt sti til git' ;;
    N11) printf '%s%s%s%s%s%s%s%s%s%s\n' 'both' '0' 'ALLOW' 'BLOCK' 'NEW_BLOCK' '' '' '' 'A-PUSH-MAIN' 'command-wrapper' ;;
    N12) printf '%s%s%s%s%s%s%s%s%s%s\n' 'both' '0' 'ALLOW' 'BLOCK' 'NEW_BLOCK' '' '' '' 'A-PUSH-MAIN' 'sh -c wrapper' ;;
    N13) printf '%s%s%s%s%s%s%s%s%s%s\n' 'both' '0' 'ALLOW' 'BLOCK' 'NEW_BLOCK' '' '' '' 'A-PUSH-MAIN' 'bash -c wrapper' ;;
    N14) printf '%s%s%s%s%s%s%s%s%s%s\n' 'both' '0' 'ALLOW' 'BLOCK' 'NEW_BLOCK' '' '' '' 'A-BASE-MAIN' '--base={{PROD_BRANCH}}' ;;
    N15) printf '%s%s%s%s%s%s%s%s%s%s\n' 'both' '0' 'ALLOW' 'BLOCK' 'NEW_BLOCK' '' '' '' 'A-BASE-MAIN' '--base "{{PROD_BRANCH}}"' ;;
    N16) printf '%s%s%s%s%s%s%s%s%s%s\n' 'both' '0' 'ALLOW' 'BLOCK' 'NEW_BLOCK' '' '' '' 'A-BASE-MAIN' '--base '\''{{PROD_BRANCH}}'\''' ;;
    N17) printf '%s%s%s%s%s%s%s%s%s%s\n' 'both' '0' 'ALLOW' 'BLOCK' 'NEW_BLOCK' '' '' '' 'A-BASE-UAVGJORT' 'uavgjorbar base-variabel' ;;
    N18) printf '%s%s%s%s%s%s%s%s%s%s\n' 'both' '0' 'ALLOW' 'BLOCK' 'NEW_BLOCK' '' '' '' 'A-PUSH-MAIN' 'kommentarlinje foran push {{PROD_BRANCH}}' ;;
    N19) printf '%s%s%s%s%s%s%s%s%s%s\n' 'both' '0' 'ALLOW' 'BLOCK' 'NEW_BLOCK' '' '' '' 'A-PUSH-MAIN' 'echo; push {{PROD_BRANCH}}' ;;
    N20) printf '%s%s%s%s%s%s%s%s%s%s\n' 'both' '0' 'BLOCK' 'BLOCK' '' '' '' 'A-PUSH-MAIN' 'A-PUSH-MAIN' 'push {{PROD_BRANCH}} med etterfoelgende kommentar (maalt BLOCK i dag)' ;;
    N21) printf '%s%s%s%s%s%s%s%s%s%s\n' 'both' '0' 'ALLOW' 'BLOCK' 'NEW_BLOCK' '' '' '' 'A-PUSH-MAIN' 'push {{PROD_BRANCH}} inne i kommandosubstitusjon' ;;
    N22) printf '%s%s%s%s%s%s%s%s%s%s\n' 'both' '0' 'ALLOW' 'BLOCK' 'NEW_BLOCK' 'pr view 123 --json baseRefName -q .baseRefName' 'api repos/other/repo/pulls/123 --jq .base.ref' '' 'A-MERGE-BASE-MAIN' 'merge 123 mot other/repo (kartet sier {{PROD_BRANCH}})' ;;
    N23) printf '%s%s%s%s%s%s%s%s%s%s\n' 'both' '0' 'ALLOW' 'BLOCK' 'NEW_BLOCK' '' '' '' 'A-PUSH-MAIN' 'escapet g\it' ;;
    N24) printf '%s%s%s%s%s%s%s%s%s%s\n' 'both' '0' 'ALLOW' 'BLOCK' 'NEW_BLOCK' '' '' '' 'A-BASE-MANGLER' 'body naevner --base {{BASE_BRANCH}}, ingen --base gitt' ;;
    N25) printf '%s%s%s%s%s%s%s%s%s%s\n' 'both' '0' 'ALLOW' 'BLOCK' 'NEW_BLOCK' '' '' '' 'A-PUSH-ALLREFS' '--mirror' ;;
    N26) printf '%s%s%s%s%s%s%s%s%s%s\n' 'both' '0' 'ALLOW' 'BLOCK' 'NEW_BLOCK' 'INGEN' 'INGEN' '' 'A-EDIT-BASE-MAIN' 'gh pr edit --base {{PROD_BRANCH}}' ;;
    N27) printf '%s%s%s%s%s%s%s%s%s%s\n' 'both' '0' 'ALLOW' 'BLOCK' 'NEW_BLOCK' '' '' '' 'A-PUSH-MAIN' 'g'\'''\''it (konkatenasjons-deref)' ;;
    N28) printf '%s%s%s%s%s%s%s%s%s%s\n' 'both' '0' 'ALLOW' 'BLOCK' 'NEW_BLOCK' '' '' '' 'A-PUSH-MAIN' '"git" "push" (sitert kommandonavn)' ;;
    N29) printf '%s%s%s%s%s%s%s%s%s%s\n' 'both' '0' 'ALLOW' 'BLOCK' 'NEW_BLOCK' 'INGEN' 'INGEN' '' 'A-GQL-MERGE' 'graphql mergePullRequest' ;;
    N30) printf '%s%s%s%s%s%s%s%s%s%s\n' 'both' '0' 'ALLOW' 'BLOCK' 'NEW_BLOCK' '' '' '' 'A-PUSH-MAIN' '+{{PROD_BRANCH}}' ;;
    N31) printf '%s%s%s%s%s%s%s%s%s%s\n' 'both' '0' 'ALLOW' 'BLOCK' 'NEW_BLOCK' '' '' '' 'A-PUSH-MAIN' 'annen remote enn origin' ;;
    N32) printf '%s%s%s%s%s%s%s%s%s%s\n' 'both' '0' 'ALLOW' 'BLOCK' 'NEW_BLOCK' '' '' '' 'A-PUSH-ALLREFS' '--all' ;;
    N33) printf '%s%s%s%s%s%s%s%s%s%s\n' 'both' '0' 'ALLOW' 'BLOCK' 'NEW_BLOCK' '' '' '' 'A-PUSH-MAIN' 'upstream {{PROD_BRANCH}}' ;;
    N34) printf '%s%s%s%s%s%s%s%s%s%s\n' 'both' '0' 'ALLOW' 'BLOCK' 'NEW_BLOCK' 'pr view 123 --json baseRefName -q .baseRefName' 'api repos/other/repo/pulls/123 --jq .base.ref' '' 'A-MERGE-BASE-MAIN' 'merge 123 -R other/repo' ;;
    N35) printf '%s%s%s%s%s%s%s%s%s%s\n' 'both' '0' 'BLOCK' 'BLOCK' '' 'pr view 123 --json baseRefName -q .baseRefName' 'INGEN' 'A-MERGE-BASE-MAIN' 'A-MERGE-UBEKREFTET' 'uavgjorbar --repo (aarsak endres NAA->ETTER)' ;;
    N36) printf '%s%s%s%s%s%s%s%s%s%s\n' 'both' '0' 'ALLOW' 'BLOCK' 'NEW_BLOCK' 'pr view 456 --json baseRefName -q .baseRefName' 'api repos/other/repo/pulls/456 --jq .base.ref' '' 'A-REST-BASE-MAIN' 'REST-merge mot other/repo' ;;
    N37) printf '%s%s%s%s%s%s%s%s%s%s\n' 'both' '0' 'ALLOW' 'BLOCK' 'NEW_BLOCK' 'INGEN' 'INGEN' '' 'A-GQL-UAVGJORT' 'graphql --input fil' ;;
    N38) printf '%s%s%s%s%s%s%s%s%s%s\n' 'both' '0' 'ALLOW' 'BLOCK' 'NEW_BLOCK' 'INGEN' 'INGEN' '' 'A-GQL-UAVGJORT' 'graphql -f query=@fil' ;;
    N39) printf '%s%s%s%s%s%s%s%s%s%s\n' 'both' '0' 'ALLOW' 'BLOCK' 'NEW_BLOCK' '' '' '' 'A-PUSH-HEAD-MAIN' 'bar git push, HEAD={{PROD_BRANCH}} (ekte mini-repo)' ;;
    N40) printf '%s%s%s%s%s%s%s%s%s%s\n' 'both' '0' 'ALLOW' 'BLOCK' 'NEW_BLOCK' '' '' '' 'A-PUSH-HEAD-MAIN' 'git push origin uten refspec, HEAD={{PROD_BRANCH}}' ;;
    A1) printf '%s%s%s%s%s%s%s%s%s%s\n' 'both' '0' 'ALLOW' 'ALLOW' '' '' '' '' '' 'npm run lint (irrelevant)' ;;
    A2) printf '%s%s%s%s%s%s%s%s%s%s\n' 'both' '0' 'ALLOW' 'ALLOW' '' '' '' '' '' 'git status' ;;
    A3) printf '%s%s%s%s%s%s%s%s%s%s\n' 'both' '0' 'ALLOW' 'ALLOW' '' '' '' '' '' 'git log' ;;
    A4) printf '%s%s%s%s%s%s%s%s%s%s\n' 'both' '0' 'ALLOW' 'ALLOW' '' '' '' '' '' 'fetch+merge {{BASE_BRANCH}}' ;;
    A5) printf '%s%s%s%s%s%s%s%s%s%s\n' 'both' '0' 'ALLOW' 'ALLOW' '' '' '' '' '' 'push til feature-branch' ;;
    A6) printf '%s%s%s%s%s%s%s%s%s%s\n' 'both' '0' 'ALLOW' 'ALLOW' '' '' '' '' '' 'prosa i echo' ;;
    A7) printf '%s%s%s%s%s%s%s%s%s%s\n' 'both' '0' 'ALLOW' 'ALLOW' '' '' '' '' '' 'ren kommentarlinje' ;;
    A8) printf '%s%s%s%s%s%s%s%s%s%s\n' 'both' '0' 'ALLOW' 'ALLOW' '' '' '' '' '' 'heredoc-kropp med push {{PROD_BRANCH}} i prosa (fixtur for M1)' ;;
    A9) printf '%s%s%s%s%s%s%s%s%s%s\n' 'both' '0' 'ALLOW' 'ALLOW' '' 'pr view 123 --json baseRefName -q .baseRefName' 'api repos/{owner}/{repo}/pulls/123 --jq .base.ref' '' '' 'gh pr merge 123, base={{BASE_BRANCH}}' ;;
    A10) printf '%s%s%s%s%s%s%s%s%s%s\n' 'both' '0' 'ALLOW' 'ALLOW' '' 'pr view 456 --json baseRefName -q .baseRefName' 'api repos/{owner}/{repo}/pulls/456 --jq .base.ref' '' '' 'koordinatorens egen merge-kommando' ;;
    A11) printf '%s%s%s%s%s%s%s%s%s%s\n' 'both' '0' 'ALLOW' 'ALLOW' '' '' '' '' '' 'rent oppslag, ingen merge' ;;
    A12) printf '%s%s%s%s%s%s%s%s%s%s\n' 'both' '0' 'ALLOW' 'ALLOW' '' '' '' '' '' 'rent api-oppslag' ;;
    A13) printf '%s%s%s%s%s%s%s%s%s%s\n' 'both' '0' 'ALLOW' 'ALLOW' '' '' '' '' '' 'sh -c uten git/gh' ;;
    A14) printf '%s%s%s%s%s%s%s%s%s%s\n' 'both' '0' 'ALLOW' 'ALLOW' '' '' '' '' '' 'grep etter strengen' ;;
    A15) printf '%s%s%s%s%s%s%s%s%s%s\n' 'both' '0' 'ALLOW' 'ALLOW' '' '' '' '' '' 'filsti som ligner github' ;;
    A16) printf '%s%s%s%s%s%s%s%s%s%s\n' 'both' '0' 'ALLOW' 'ALLOW' '' 'pr view 123 --json baseRefName -q .baseRefName' 'api repos/{owner}/{repo}/pulls/123 --jq .base.ref' '' '' 'speiler N22: kartet er betinget, oppslaget nevner ikke other/repo' ;;
    A17) printf '%s%s%s%s%s%s%s%s%s%s\n' 'both' '0' 'ALLOW' 'ALLOW' '' 'INGEN' 'INGEN' '' '' 'gh pr edit --base {{BASE_BRANCH}}' ;;
    A18) printf '%s%s%s%s%s%s%s%s%s%s\n' 'both' '0' 'ALLOW' 'ALLOW' '' 'INGEN' 'INGEN' '' '' 'gh pr edit uten base' ;;
    A19) printf '%s%s%s%s%s%s%s%s%s%s\n' 'both' '0' 'ALLOW' 'ALLOW' '' 'INGEN' 'INGEN' '' '' 'graphql query (ikke mutasjon)' ;;
    A20) printf '%s%s%s%s%s%s%s%s%s%s\n' 'both' '0' 'BLOCK' 'ALLOW' 'INTENTIONAL_UNBLOCK' '' '' 'A-PUSH-MAIN' '' '{{PROD_BRANCH}}-fix (falsk positiv i dag, U-REFNORM)' ;;
    A21) printf '%s%s%s%s%s%s%s%s%s%s\n' 'both' '0' 'ALLOW' 'ALLOW' '' '' '' '' '' 'bar git push, HEAD={{BASE_BRANCH}} (ekte mini-repo)' ;;
    P1) printf '%s%s%s%s%s%s%s%s%s%s\n' 'both' '0' 'BLOCK' 'ALLOW' 'INTENTIONAL_UNBLOCK' '' '' 'A-BASE-MANGLER' '' 'heredoc <<-EOF foer --base {{BASE_BRANCH}}' ;;
    P2) printf '%s%s%s%s%s%s%s%s%s%s\n' 'both' '0' 'BLOCK' 'ALLOW' 'INTENTIONAL_UNBLOCK' '' '' 'A-BASE-MANGLER' '' 'heredoc <<'\''EOF'\'' foer --base {{BASE_BRANCH}}' ;;
    P3) printf '%s%s%s%s%s%s%s%s%s%s\n' 'both' '0' 'BLOCK' 'ALLOW' 'INTENTIONAL_UNBLOCK' '' '' 'A-BASE-MANGLER' '' 'heredoc <<"EOF" foer --base {{BASE_BRANCH}}' ;;
    P4) printf '%s%s%s%s%s%s%s%s%s%s\n' 'both' '0' 'BLOCK' 'BLOCK' '' '' '' 'A-BASE-MANGLER' 'A-BASE-MANGLER' 'escapet heredoc-delimiter, prosa i kropp' ;;
    P5) printf '%s%s%s%s%s%s%s%s%s%s\n' 'both' '0' 'BLOCK' 'BLOCK' '' '' '' 'A-BASE-MANGLER' 'A-BASE-MANGLER' 'flerlinjet body-streng, prosa' ;;
    P6) printf '%s%s%s%s%s%s%s%s%s%s\n' 'both' '0' 'BLOCK' 'BLOCK' '' '' '' 'A-BASE-MANGLER' 'A-BASE-MANGLER' 'backslash-fortsettelse, prosa' ;;
    P7) printf '%s%s%s%s%s%s%s%s%s%s\n' 'both' '0' 'ALLOW' 'BLOCK' 'NEW_BLOCK' '' '' '' 'A-UAVGJORT' 'uterminert sitat, nevner push {{PROD_BRANCH}}' ;;
    P8) printf '%s%s%s%s%s%s%s%s%s%s\n' 'both' '0' 'ALLOW' 'ALLOW' '' '' '' '' '' 'uterminert sitat, ingen git/gh' ;;
    P9) printf '%s%s%s%s%s%s%s%s%s%s\n' 'both' '0' 'BLOCK' 'BLOCK' '' '' '' 'A-PUSH-MAIN' 'A-PUSH-MAIN' 'here-string etter push {{PROD_BRANCH}}' ;;
    P10) printf '%s%s%s%s%s%s%s%s%s%s\n' 'both' '0' 'ALLOW' 'BLOCK' 'NEW_BLOCK' '' '' '' 'A-FOR-LANG' '300 kB kommando som nevner git' ;;
    P11) printf '%s%s%s%s%s%s%s%s%s%s\n' 'both' '0' 'ALLOW' 'ALLOW' '' '' '' '' '' '300 kB kommando uten git/gh' ;;
    P12) printf '%s%s%s%s%s%s%s%s%s%s\n' 'post' '0' '' 'BLOCK' '' '' 'INGEN' '' 'A-PERL-MANGLER' 'perl-mangler variant' ;;
    P13) printf '%s%s%s%s%s%s%s%s%s%s\n' 'post' '0' '' 'ALLOW' '' '' '' '' '' 'perl-mangler variant, irrelevant kommando' ;;
    P14) printf '%s%s%s%s%s%s%s%s%s%s\n' 'both' '0' 'ALLOW' 'ALLOW' '' '' '' '' '' 'feature/{{PROD_BRANCH}}' ;;
    P15) printf '%s%s%s%s%s%s%s%s%s%s\n' 'both' '0' 'ALLOW' 'ALLOW' '' '' '' '' '' 'mainline' ;;
    P16) printf '%s%s%s%s%s%s%s%s%s%s\n' 'both' '0' 'ALLOW' 'ALLOW' '' '' '' '' '' 'escapet ; er literal' ;;
    P17) printf '%s%s%s%s%s%s%s%s%s%s\n' 'both' '0' 'ALLOW' 'BLOCK' 'NEW_BLOCK' '' '' '' 'A-PUSH-MAIN' 'ma\in (escapet indre tegn)' ;;
    P18) printf '%s%s%s%s%s%s%s%s%s%s\n' 'post' '0' '' 'BLOCK' '' '' 'INGEN' '' 'A-SKANNER' 'perl-stub-tom variant' ;;
    P19) printf '%s%s%s%s%s%s%s%s%s%s\n' 'post' '0' '' 'BLOCK' '' '' 'INGEN' '' 'A-SKANNER' 'perl-stub-exit3 variant' ;;
    P20) printf '%s%s%s%s%s%s%s%s%s%s\n' 'both' '0' 'BLOCK' 'BLOCK' '' 'pr view 123 --json baseRefName -q .baseRefName' 'api repos/{owner}/{repo}/pulls/123 --jq .base.ref' 'A-MERGE-UBEKREFTET' 'A-MERGE-UBEKREFTET' 'STUB_SLEEP=8 (exec sleep, bundet sti)' ;;
    P20b) printf '%s%s%s%s%s%s%s%s%s%s\n' 'post' '0' '' 'BLOCK' '' '' 'api repos/{owner}/{repo}/pulls/123 --jq .base.ref' '' 'A-MERGE-UBEKREFTET' 'STUB_SLEEP_CHILD=8 (barnebarn arver stdout)' ;;
    P20c) printf '%s%s%s%s%s%s%s%s%s%s\n' 'post' '0' '' 'BLOCK' '' '' 'api repos/{owner}/{repo}/pulls/123 --jq .base.ref' '' 'A-MERGE-UBEKREFTET' 'STUB_HANG_AFTER_CLOSE=8 (barn lukker stdout, lever videre)' ;;
    P21) printf '%s%s%s%s%s%s%s%s%s%s\n' 'both' '0' 'ALLOW' 'ALLOW' '' '' '' '' '' 'parenteser i body' ;;
    P22) printf '%s%s%s%s%s%s%s%s%s%s\n' 'both' '0' 'ALLOW' 'ALLOW' '' '' '' '' '' 'apostrof i dobbeltfnutt' ;;
    P23) printf '%s%s%s%s%s%s%s%s%s%s\n' 'both' '0' 'ALLOW' 'ALLOW' '' '' '' '' '' 'backtick-par i body' ;;
    P24) printf '%s%s%s%s%s%s%s%s%s%s\n' 'post' '0' '' 'ALLOW' '' '' '' '' '' 'len-probe (UTF-8 body)' ;;
    P25) printf '%s%s%s%s%s%s%s%s%s%s\n' 'both' '0' 'ALLOW' 'BLOCK' 'NEW_BLOCK' '' '' '' 'A-UAVGJORT' 'enslig (uterminert) backtick' ;;
    P26) printf '%s%s%s%s%s%s%s%s%s%s\n' 'both' '1' 'ALLOW' 'ALLOW' '' '' '' '' '' '[KJENT HULL] uavgjorbart sh -c-argument' ;;
    P27) printf '%s%s%s%s%s%s%s%s%s%s\n' 'both' '0' 'BLOCK' 'BLOCK' '' 'pr view 456 --json baseRefName -q .baseRefName' 'INGEN' 'A-REST-BASE-MAIN' 'A-REST-UBEKREFTET' 'blandet placeholder-form (aarsak endres NAA->ETTER)' ;;
    P28) printf '%s%s%s%s%s%s%s%s%s%s\n' 'post' '0' '' 'BLOCK' '' '' '' '' 'A-INPUT' 'ugyldig JSON paa stdin' ;;
    P29) printf '%s%s%s%s%s%s%s%s%s%s\n' 'post' '0' '' 'BLOCK' '' '' '' '' 'A-INPUT' 'jq-mangler variant' ;;
    P30) printf '%s%s%s%s%s%s%s%s%s%s\n' 'post' '0' '' 'ALLOW' '' '' '' '' '' 'tom stdin' ;;
    P31) printf '%s%s%s%s%s%s%s%s%s%s\n' 'post' '0' '' 'BLOCK' '' '' 'INGEN' '' 'A-GH-MANGLER' 'gh-mangler variant (GH_BIN tom)' ;;
    P32) printf '%s%s%s%s%s%s%s%s%s%s\n' 'post' '0' '' 'ALLOW' '' '' 'api repos/{owner}/{repo}/pulls/123 --jq .base.ref' '' '' 'positiv kanari: stubben ble faktisk naadd' ;;
    KH1) printf '%s%s%s%s%s%s%s%s%s%s\n' 'both' '1' 'ALLOW' 'ALLOW' '' '' '' '' '' '[KJENT HULL] kommandonavn fra substitusjon' ;;
    KH2) printf '%s%s%s%s%s%s%s%s%s%s\n' 'both' '1' 'ALLOW' 'ALLOW' '' '' '' '' '' '[KJENT HULL] uavgjorbar refspec' ;;
    KH3) printf '%s%s%s%s%s%s%s%s%s%s\n' 'both' '1' 'ALLOW' 'ALLOW' '' 'INGEN' 'INGEN' '' '' '[KJENT HULL] uavgjorbar base i pr edit' ;;
    KH4) printf '%s%s%s%s%s%s%s%s%s%s\n' 'both' '1' 'ALLOW' 'ALLOW' '' '' '' '' '' '[KJENT HULL] wrapper utover command/env/sh -c' ;;
    KH5) printf '%s%s%s%s%s%s%s%s%s%s\n' 'both' '1' 'ALLOW' 'ALLOW' '' '' '' '' '' '[KJENT HULL] HEAD-oppslag som ikke kan avgjoeres' ;;
    KH6) printf '%s%s%s%s%s%s%s%s%s%s\n' 'both' '1' 'ALLOW' 'ALLOW' '' 'INGEN' 'INGEN' '' '' '[KJENT HULL] mutasjon i heredoc-kropp' ;;
    KH7) printf '%s%s%s%s%s%s%s%s%s%s\n' 'both' '1' 'ALLOW' 'ALLOW' '' 'INGEN' 'INGEN' '' '' '[KJENT HULL] mutasjon via uavgjorbar variabel' ;;
    KH8) printf '%s%s%s%s%s%s%s%s%s%s\n' 'both' '1' 'ALLOW' 'ALLOW' '' '' '' '' '' '[KJENT HULL] dst normaliserer til refs/heads/{{PROD_BRANCH}} (R4-11)' ;;
    U1) printf '%s%s%s%s%s%s%s%s%s%s\n' 'both' '0' 'BLOCK' 'ALLOW' 'INTENTIONAL_UNBLOCK' '' '' 'A-BASE-MANGLER' '' 'B2 — base etter heredoc-kropp' ;;
    U2) printf '%s%s%s%s%s%s%s%s%s%s\n' 'both' '0' 'BLOCK' 'ALLOW' 'INTENTIONAL_UNBLOCK' '' '' 'A-BASE-MANGLER' '' 'B3 — backslash-fortsettelse' ;;
    U3) printf '%s%s%s%s%s%s%s%s%s%s\n' 'both' '0' 'BLOCK' 'ALLOW' 'INTENTIONAL_UNBLOCK' '' '' 'A-BASE-MANGLER' '' 'B12 — -B kortform' ;;
    U10) printf '%s%s%s%s%s%s%s%s%s%s\n' 'both' '0' 'BLOCK' 'ALLOW' 'INTENTIONAL_UNBLOCK' '' '' 'A-BASE-MAIN' '' 'avgjorbar base {{PROD_BRANCH}}-fix' ;;
    U11) printf '%s%s%s%s%s%s%s%s%s%s\n' 'both' '0' 'BLOCK' 'ALLOW' 'INTENTIONAL_UNBLOCK' '' '' 'A-BASE-MAIN' '' 'avgjorbar base {{PROD_BRANCH}}/foo' ;;
    U12) printf '%s%s%s%s%s%s%s%s%s%s\n' 'both' '0' 'BLOCK' 'ALLOW' 'INTENTIONAL_UNBLOCK' '' '' 'A-BASE-MAIN' '' 'reell base {{BASE_BRANCH}}, prosa naevner {{PROD_BRANCH}}' ;;
    U13) printf '%s%s%s%s%s%s%s%s%s%s\n' 'both' '0' 'BLOCK' 'ALLOW' 'INTENTIONAL_UNBLOCK' 'INGEN' 'api repos/other/repo/pulls/123 --jq .base.ref' 'A-MERGE-UTEN-PR' '' '--repo foer, PR-nr foer --merge' ;;
    U14) printf '%s%s%s%s%s%s%s%s%s%s\n' 'both' '0' 'BLOCK' 'ALLOW' 'INTENTIONAL_UNBLOCK' 'INGEN' 'api repos/{owner}/{repo}/pulls/123 --jq .base.ref' 'A-MERGE-UTEN-PR' '' 'sitert PR-nummer' ;;
    U15) printf '%s%s%s%s%s%s%s%s%s%s\n' 'both' '0' 'BLOCK' 'ALLOW' 'INTENTIONAL_UNBLOCK' 'INGEN' 'api repos/{owner}/{repo}/pulls/123 --jq .base.ref' 'A-MERGE-UTEN-PR' '' 'PR-nummer etter --merge' ;;
    U16b) printf '%s%s%s%s%s%s%s%s%s%s\n' 'both' '0' 'BLOCK' 'ALLOW' 'INTENTIONAL_UNBLOCK' 'pr view 456 --json baseRefName -q .baseRefName' 'api repos/other/repo/pulls/456 --jq .base.ref' 'A-REST-BASE-MAIN' '' 'dagens oppslag mot feil (cwd-)repo' ;;
    U17) printf '%s%s%s%s%s%s%s%s%s%s\n' 'both' '0' 'BLOCK' 'ALLOW' 'INTENTIONAL_UNBLOCK' 'pr view 456 --json baseRefName -q .baseRefName' 'api repos/o/r/pulls/456 --jq .base.ref' 'A-REST-BASE-MAIN' '' '-X PUT mellomromsform' ;;
    U18) printf '%s%s%s%s%s%s%s%s%s%s\n' 'both' '0' 'BLOCK' 'ALLOW' 'INTENTIONAL_UNBLOCK' 'INGEN' 'api repos/other/repo/pulls/123 --jq .base.ref' 'A-MERGE-UTEN-PR' '' '--repo foer, --merge foer PR-nr' ;;
    *) printf '' ;;
  esac
}

row_stub() {
  case "$1" in
    K14) echo 'map:default={{PROD_BRANCH}}' ;;
    K15) echo 'fail:1' ;;
    K17) echo 'map:default={{PROD_BRANCH}}' ;;
    K18) echo 'map:default={{PROD_BRANCH}}' ;;
    K19) echo 'map:default={{PROD_BRANCH}}' ;;
    N3) echo 'map:default={{PROD_BRANCH}}' ;;
    N22) echo 'map:other/repo={{PROD_BRANCH}};default={{BASE_BRANCH}}' ;;
    N34) echo 'map:other/repo={{PROD_BRANCH}};default={{BASE_BRANCH}}' ;;
    N35) echo 'map:default={{PROD_BRANCH}}' ;;
    N36) echo 'map:other/repo={{PROD_BRANCH}};default={{BASE_BRANCH}}' ;;
    A9) echo 'map:default={{BASE_BRANCH}}' ;;
    A10) echo 'map:default={{BASE_BRANCH}}' ;;
    A16) echo 'map:other/repo={{PROD_BRANCH}};default={{BASE_BRANCH}}' ;;
    P12) echo 'variant:perl-mangler' ;;
    P13) echo 'variant:perl-mangler' ;;
    P18) echo 'variant:perl-stub-tom' ;;
    P19) echo 'variant:perl-stub-exit3' ;;
    P20) echo 'sleep:8' ;;
    P20b) echo 'sleep_child:8' ;;
    P20c) echo 'hang_after_close:8' ;;
    P24) echo 'variant:len-probe' ;;
    P27) echo 'map:default={{PROD_BRANCH}}' ;;
    P29) echo 'variant:jq-mangler' ;;
    P31) echo 'map:default={{BASE_BRANCH}} variant:gh-mangler' ;;
    P32) echo 'map:default={{BASE_BRANCH}}' ;;
    U13) echo 'map:other/repo={{BASE_BRANCH}};default={{PROD_BRANCH}}' ;;
    U14) echo 'map:default={{BASE_BRANCH}}' ;;
    U15) echo 'map:default={{BASE_BRANCH}}' ;;
    U16b) echo 'map:other/repo={{BASE_BRANCH}};default={{PROD_BRANCH}}' ;;
    U17) echo 'map:o/r={{BASE_BRANCH}};default={{PROD_BRANCH}}' ;;
    U18) echo 'map:other/repo={{BASE_BRANCH}};default={{PROD_BRANCH}}' ;;
    *) echo "" ;;
  esac
}

row_repo() {
  case "$1" in
    N39) echo '{{PROD_BRANCH}}' ;;
    N40) echo '{{PROD_BRANCH}}' ;;
    A21) echo '{{BASE_BRANCH}}' ;;
    KH5) echo 'none' ;;
    *) echo "" ;;
  esac
}

row_special() {
  case "$1" in
    P10) echo 'longcmd_git' ;;
    P11) echo 'longcmd_nogit' ;;
    P28) echo 'invalid_json' ;;
    P30) echo 'empty_stdin' ;;
    *) echo "" ;;
  esac
}

row_walltime() {
  case "$1" in
    P20) echo '7' ;;
    P20b) echo '7' ;;
    P20c) echo '7' ;;
    *) echo "" ;;
  esac
}

ALL_IDS="K1 K2 K3 K4 K5 K6 K7 K8 K9 K10 K11 K12 K13 K14 K15 K16 K17 K18 K19 K20 K21 K22 K23 K24 K25 K26 K27 K28 K29 K30 K31 K32 N1 N2 N3 N4 N5 N6 N7 N8 N9 N10 N11 N12 N13 N14 N15 N16 N17 N18 N19 N20 N21 N22 N23 N24 N25 N26 N27 N28 N29 N30 N31 N32 N33 N34 N35 N36 N37 N38 N39 N40 A1 A2 A3 A4 A5 A6 A7 A8 A9 A10 A11 A12 A13 A14 A15 A16 A17 A18 A19 A20 A21 P1 P2 P3 P4 P5 P6 P7 P8 P9 P10 P11 P12 P13 P14 P15 P16 P17 P18 P19 P20 P20b P20c P21 P22 P23 P24 P25 P26 P27 P28 P29 P30 P31 P32 KH1 KH2 KH3 KH4 KH5 KH6 KH7 KH8 U1 U2 U3 U10 U11 U12 U13 U14 U15 U16b U17 U18"

# ───────────────────────── hjelpefunksjoner ──────────────────────────────

write_gh_stub() {
  local dest="$1"
  cat > "$dest" <<'GHSTUBEOF'
#!/usr/bin/env perl
# Per-case gh-stub for TODO 188-harnessen. Leser KUN STUB_*-miljøvariabler —
# hooken får ingen test-override (§ 7.3).
use strict;
use warnings;

my $log = $ENV{GH_ARGV_LOG};
if (defined $log && length $log) {
  if (open(my $fh, ">>", $log)) {
    print $fh join(" ", @ARGV), "\n";
    close $fh;
  }
}

if ($ENV{STUB_FAIL}) { exit 1; }

my $map = defined $ENV{STUB_MAP} ? $ENV{STUB_MAP} : "";
my $argvstr = join(" ", @ARGV);
my $answer = "{{BASE_BRANCH}}";
for my $pair (split /;/, $map) {
  next unless length $pair;
  my ($k, $v) = split /=/, $pair, 2;
  next unless defined $v;
  if ($k eq "default") { $answer = $v; next; }
  if (index($argvstr, $k) >= 0) { $answer = $v; }
}

if (defined $ENV{STUB_SLEEP} && length $ENV{STUB_SLEEP}) {
  # (§ 0.4) exec, IKKE et barn — ellers maaler P20 stubben i stedet for
  # timeout-wrapperen.
  exec "/bin/sleep", $ENV{STUB_SLEEP};
  exit 126;
}
if (defined $ENV{STUB_SLEEP_CHILD} && length $ENV{STUB_SLEEP_CHILD}) {
  # (§ 0.4, P20b) barnebarn arver STDOUT og holder kommandosubstitusjonen aapen.
  my $pid = fork();
  if (!defined $pid) { exit 125; }
  if ($pid == 0) {
    exec "/bin/sleep", $ENV{STUB_SLEEP_CHILD};
    exit 126;
  }
  exit 0;
}
if (defined $ENV{STUB_HANG_AFTER_CLOSE} && length $ENV{STUB_HANG_AFTER_CLOSE}) {
  # (r4-pålegg VIKTIG-3, P20c) direkte barn lukker STDOUT men lever videre.
  print "$answer\n";
  close(STDOUT);
  sleep($ENV{STUB_HANG_AFTER_CLOSE});
  exit 0;
}

print "$answer\n";
exit 0;
GHSTUBEOF
  chmod +x "$dest"
}

write_gen_refspecs_pl() {
  local dest="$1"
  cat > "$dest" <<'REFSPECSPLEOF'
#!/usr/bin/env perl
# TODO 188, § 0.2b — push-refspec-generator, "pre"-fase-gate (VIKTIG-3/VIKTIG-4,
# r4-pålegg MINDRE-9). Sammenligner referansemodellen (§ 5 pkt 10a steg 1-5)
# mot DAGENS regex, ordrett transkribert fra guard-main-merge.sh blokk 1
# (hooken er uendret i PR1 — se plan-header). Kjøres av
# .claude/hooks/test-guard-main-merge.sh --gen-refspecs.
#
# Eksakte forventede tall (§ 0.2b, ikke ">="-skralle, jf. S5-lesson):
#   BASISRAMME=728  AKSE_A=31 AKSE_B=8 AKSE_C=12 AKSE_D=8
#   UNIKE=787  BLOCK_TO_ALLOW=382  ALLOW_TO_BLOCK=30
#   PRED_A=264 PRED_B=119 PRED_VIOL=0  VIKTIG4_PRED30=30
use strict;
use warnings;

my $EXP_BASIS = 728;
my $EXP_A = 31;
my $EXP_B = 8;
my $EXP_C = 12;
my $EXP_D = 8;
my $EXP_UNIQUE = 787;
my $EXP_B2A = 382;
my $EXP_A2B = 30;
my $EXP_PREDA = 264;
my $EXP_PREDB = 119;

my @REFS = ('{{PROD_BRANCH}}', '{{PROD_BRANCH}}-fix', 'mainline', '{{PROD_BRANCH}}/sub', '{{PROD_BRANCH}}.x', 'main_x', '{{PROD_BRANCH}},x', '{{PROD_BRANCH}}+x',
            '{{PROD_BRANCH}}@{1}', '{{PROD_BRANCH}}~1', '{{PROD_BRANCH}}^{}', '{{BASE_BRANCH}}', 'HEAD');

sub strip_rev_suffix {
  my ($s) = @_;
  my $changed = 1;
  while ($changed) {
    $changed = 0;
    if ($s =~ s/(~[0-9]*|\^\{[^}]*\}|\^[0-9]*|\@\{[^}]*\})$//) { $changed = 1; }
  }
  return $s;
}

sub normalize_word_blocks {
  my ($word) = @_;
  $word =~ s/^\+//;
  my ($src, $dst);
  if ($word =~ /^([^:]*):(.*)$/) { $src = $1; $dst = $2; }
  else { $src = ''; $dst = $word; }
  $src =~ s{^refs/heads/}{};
  $dst =~ s{^refs/heads/}{};
  $src = strip_rev_suffix($src);
  return ($src eq '{{PROD_BRANCH}}' || $dst eq '{{PROD_BRANCH}}') ? 1 : 0;
}

# Referansemodellens verdikt for "git push <remote> <ord...>" (§ 5 pkt 10a).
sub ref_model_block {
  my ($remote, @words) = @_;
  for my $w (@words) {
    return 1 if $w eq '--mirror' || $w eq '--all';
  }
  for my $w (@words) {
    next if $w eq '--mirror' || $w eq '--all';
    return 1 if normalize_word_blocks($w);
  }
  return 0;
}

# DAGENS regex-verdikt for "git push ...", ORDRETT transkribert fra
# guard-main-merge.sh blokk 1 (§ 0.2b: "dagens verdikt er hookens ordrette
# regex fra blokk 1"). Hooken er uendret i PR1 (plan-header, verifisert
# `git log` mot .claude/hooks/guard-main-merge.sh).
sub today_block {
  my ($cmd) = @_;
  return 0 unless $cmd =~ /^git\s+push\b/;
  if ($cmd =~ /\borigin\s+{{PROD_BRANCH}}\b|-u\s+origin\s+{{PROD_BRANCH}}\b|HEAD:{{PROD_BRANCH}}\b|:{{PROD_BRANCH}}\b|refs\/heads\/{{PROD_BRANCH}}\b/) {
    return 1;
  }
  return 0;
}

my %seen;
my @candidates;

sub add_candidate {
  my ($cmd, $remote, @words) = @_;
  return if $seen{$cmd}++;
  push @candidates, { cmd => $cmd, remote => $remote, words => [@words] };
}

# Basisramme: 2 x 2 x 13 x 14 = 728
for my $sign ('', '+') {
  for my $prefix ('', 'refs/heads/') {
    for my $r (@REFS) {
      for my $dstsuffix ('', map { ":$_" } @REFS) {
        my $word = "$sign$prefix$r$dstsuffix";
        add_candidate("git push origin $word", 'origin', $word);
      }
    }
  }
}
my $basis_total = scalar(@candidates);

# Akse (a): remote-navn
my @axis_a_words = ('{{PROD_BRANCH}}', '{{PROD_BRANCH}}-fix', '{{BASE_BRANCH}}', '+{{PROD_BRANCH}}', '{{PROD_BRANCH}}:{{BASE_BRANCH}}', '{{BASE_BRANCH}}:{{PROD_BRANCH}}', 'HEAD:{{PROD_BRANCH}}',
                     ':{{PROD_BRANCH}}', '{{PROD_BRANCH}}~1', 'refs/heads/{{PROD_BRANCH}}');
my $axis_a_start = scalar(@candidates);
for my $remote ('upstream', 'origin2', 'nonexistent-remote') {
  for my $w (@axis_a_words) {
    add_candidate("git push $remote $w", $remote, $w);
  }
}
for my $w (@axis_a_words) {
  add_candidate("git push origin $w", 'origin', $w);
}
my $axis_a_count_raw = scalar(@candidates) - $axis_a_start;

# Akse (b): to refspecs i ett kall
my $axis_b_start = scalar(@candidates);
my @axis_b_forms = (
  ['{{BASE_BRANCH}}', '{{PROD_BRANCH}}'], ['{{BASE_BRANCH}}', '+{{PROD_BRANCH}}'], ['{{PROD_BRANCH}}', '{{BASE_BRANCH}}'], ['+{{PROD_BRANCH}}', '{{BASE_BRANCH}}'],
  ['{{BASE_BRANCH}}', '{{PROD_BRANCH}}-fix'], ['{{PROD_BRANCH}}-fix', '{{BASE_BRANCH}}'], ['{{BASE_BRANCH}}', 'HEAD:{{PROD_BRANCH}}'], ['{{BASE_BRANCH}}', '{{PROD_BRANCH}}:{{BASE_BRANCH}}'],
);
for my $pair (@axis_b_forms) {
  my ($w1, $w2) = @$pair;
  add_candidate("git push origin $w1 $w2", 'origin', $w1, $w2);
}
my $axis_b_count_raw = scalar(@candidates) - $axis_b_start;

# Akse (c): refs/heads/ paa dst
my $axis_c_start = scalar(@candidates);
my @axis_c_srcs = ('{{BASE_BRANCH}}', 'HEAD', '{{PROD_BRANCH}}-fix', '');
for my $r (@REFS[0..3]) {
  for my $s (@axis_c_srcs) {
    my $word = $s eq '' ? "refs/heads/$r" : "$s:refs/heads/$r";
    add_candidate("git push origin $word", 'origin', $word);
  }
}
my $axis_c_count_raw = scalar(@candidates) - $axis_c_start;

# Akse (d) — r4-pålegg MINDRE-9: path-normaliseringsformer paa dst
my $axis_d_start = scalar(@candidates);
my @axis_d_forms = ('/{{PROD_BRANCH}}', '//{{PROD_BRANCH}}', '{{PROD_BRANCH}}/', './{{PROD_BRANCH}}');
for my $f (@axis_d_forms) {
  add_candidate("git push origin $f", 'origin', $f);
  add_candidate("git push origin {{BASE_BRANCH}}:$f", 'origin', "{{BASE_BRANCH}}:$f");
}
my $axis_d_count_raw = scalar(@candidates) - $axis_d_start;

my $total = scalar(@candidates);
my $b2a = 0;
my $a2b = 0;
my @b2a_list;
my @a2b_list;

for my $c (@candidates) {
  my $t = today_block($c->{cmd});
  my $r = ref_model_block($c->{remote}, @{$c->{words}});
  if ($t == 1 && $r == 0) { $b2a++; push @b2a_list, $c; }
  elsif ($t == 0 && $r == 1) { $a2b++; push @a2b_list, $c; }
}

# Sikkerhetspredikat (A)/(B) på alle BLOCK->ALLOW-kandidater (§ 0.2b).
my $predA = 0;
my $predB = 0;
my $predViol = 0;
for my $c (@b2a_list) {
  my $anybroke = 0;
  for my $w (@{$c->{words}}) {
    my $ww = $w; $ww =~ s/^\+//;
    my ($src, $dst);
    if ($ww =~ /^([^:]*):(.*)$/) { $src = $1; $dst = $2; }
    else { $src = ''; $dst = $ww; }
    $src =~ s{^refs/heads/}{};
    $dst =~ s{^refs/heads/}{};
    $src = strip_rev_suffix($src);
    my $target = $dst ne '' ? $dst : $src;
    next if $target eq '';
    my $refname = "refs/heads/$target";
    my $out = `git check-ref-format --normalize '$refname' 2>/dev/null`;
    chomp $out;
    my $rc = $? >> 8;
    if ($rc == 0) {
      if ($out eq 'refs/heads/{{PROD_BRANCH}}') { $anybroke = 1; }
      else { $predA++; }
    } else {
      $predB++;
    }
  }
  $predViol++ if $anybroke;
}

# VIKTIG-4 (r4-pålegg): assersjon (6) — hver ALLOW->BLOCK-kandidat har,
# UAVHENGIG re-utledet fra selve ordene (ikke gjenbruk av ref_model_block sin
# bool), src ELLER dst ordrett "{{PROD_BRANCH}}" ETTER normalisering, ELLER inneholder
# --mirror/--all. Antallet som tilfredsstiller dette skal være EKSAKT 30.
my $viktig4_ok = 0;
for my $c (@a2b_list) {
  my $satisfied = 0;
  for my $w (@{$c->{words}}) {
    if ($w eq '--mirror' || $w eq '--all') { $satisfied = 1; last; }
    my $ww = $w; $ww =~ s/^\+//;
    my ($src, $dst);
    if ($ww =~ /^([^:]*):(.*)$/) { $src = $1; $dst = $2; }
    else { $src = ''; $dst = $ww; }
    $src =~ s{^refs/heads/}{};
    $dst =~ s{^refs/heads/}{};
    $src = strip_rev_suffix($src);
    if ($src eq '{{PROD_BRANCH}}' || $dst eq '{{PROD_BRANCH}}') { $satisfied = 1; last; }
  }
  $viktig4_ok++ if $satisfied;
}

print "BASISRAMME (2x2x13x14)             TOTALT: $basis_total\n";
print "AKSE (a) remote-navn (raa)         TOTALT: $axis_a_count_raw\n";
print "AKSE (b) to refspecs (raa)         TOTALT: $axis_b_count_raw\n";
print "AKSE (c) refs/heads/ paa dst (raa) TOTALT: $axis_c_count_raw\n";
print "AKSE (d) path-edge-former (raa)    TOTALT: $axis_d_count_raw   (r4-pålegg MINDRE-9)\n";
print "UNIKE KANDIDATER TOTALT            : $total\n";
print "  BLOCK->ALLOW                     : $b2a\n";
print "  ALLOW->BLOCK                     : $a2b\n";
print "  predikat (A) gyldig annet refnavn: $predA\n";
print "  predikat (B) ugyldig refnavn     : $predB\n";
print "  predikat-brudd                   : $predViol  (maa vaere 0)\n";
print "  VIKTIG-4 assersjon (6) oppfylt   : $viktig4_ok av $a2b (maa vaere eksakt 30)\n";

my $fail = 0;
sub check {
  my ($label, $got, $want) = @_;
  if ($got != $want) {
    print "FEIL: $label = $got, forventet EKSAKT $want\n";
    $fail = 1;
  }
}
check("BASISRAMME", $basis_total, $EXP_BASIS);
check("AKSE(a)", $axis_a_count_raw, $EXP_A);
check("AKSE(b)", $axis_b_count_raw, $EXP_B);
check("AKSE(c)", $axis_c_count_raw, $EXP_C);
check("AKSE(d)", $axis_d_count_raw, $EXP_D);
check("UNIKE", $total, $EXP_UNIQUE);
check("BLOCK->ALLOW", $b2a, $EXP_B2A);
check("ALLOW->BLOCK", $a2b, $EXP_A2B);
check("predikat(A)", $predA, $EXP_PREDA);
check("predikat(B)", $predB, $EXP_PREDB);
check("predikat-brudd", $predViol, 0);
check("VIKTIG-4 assersjon(6)", $viktig4_ok, $EXP_A2B);

if ($fail) {
  print "GEN-REFSPECS: FEIL\n";
  exit 1;
} else {
  print "GEN-REFSPECS: OK\n";
  exit 0;
}
REFSPECSPLEOF
}

write_gen_baserefs_pl() {
  local dest="$1"
  cat > "$dest" <<'BASEREFSPLEOF'
#!/usr/bin/env perl
# TODO 188, § 0.2b — base-rommet-generator, "pre"-fase-gate. Kryssproduktet
# {--base V, --base=V, -B V, -BV} x {13 refs + "{{PROD_BRANCH}}", '{{PROD_BRANCH}}', $BR} = 64
# kandidater, kjørt mot DAGENS blokk 2 (ordrett transkribert) og mot
# referansemodellen for § 5 pkt 10b. Ingen forhåndsspesifisert fasit-telling
# finnes i planen for dette rommet (i motsetning til push-refspecs' 787/382/30)
# — denne kjøringen ER selve den mekaniske referansemålingen (limes i
# PR1-beskrivelsen). Kjøres av .claude/hooks/test-guard-main-merge.sh
# --gen-baserefs.
use strict;
use warnings;

my @REFS = ('{{PROD_BRANCH}}', '{{PROD_BRANCH}}-fix', 'mainline', '{{PROD_BRANCH}}/sub', '{{PROD_BRANCH}}.x', 'main_x', '{{PROD_BRANCH}},x', '{{PROD_BRANCH}}+x',
            '{{PROD_BRANCH}}@{1}', '{{PROD_BRANCH}}~1', '{{PROD_BRANCH}}^{}', '{{BASE_BRANCH}}', 'HEAD');
my @VALUES = (@REFS, '"{{PROD_BRANCH}}"', "'{{PROD_BRANCH}}'", '$BR');

# DAGENS regex, ordrett fra blokk 2 (guard-main-merge.sh):
#   --base {{PROD_BRANCH}} (mellomrom, literal) => BLOCK
#   ellers, hvis --base (langform) IKKE finnes i det hele tatt => BLOCK
#   (dette fanger ogsaa -B/-BV — ingen langform "--base" er tilstede der,
#   saa hooken tolker dem alle som "uten --base", uansett verdi — § 0.3 K10/U3)
#   ellers => ALLOW
sub today_base_block {
  my ($cmd) = @_;
  return (0, '') unless $cmd =~ /^gh\s+pr\s+create\b/;
  if ($cmd =~ /--base\s+{{PROD_BRANCH}}\b/) { return (1, 'A-BASE-MAIN'); }
  if ($cmd !~ /--base\b/) { return (1, 'A-BASE-MANGLER'); }
  return (0, '');
}

# Referansemodellen (§ 5 pkt 10b): utled den deref'ede verdien uavhengig av
# flagg-form, BLOCK hvis og bare hvis verdien er ordrett "{{PROD_BRANCH}}" (etter
# sitatfjerning), eller uavgjørbar (leder med "$"), eller flagget mangler.
sub ref_base_block {
  my ($cmd) = @_;
  return (0, '') unless $cmd =~ /^gh\s+pr\s+create\b/;
  my $val;
  if ($cmd =~ /--base=(\S+)/)      { $val = $1; }
  elsif ($cmd =~ /--base\s+(\S+)/) { $val = $1; }
  elsif ($cmd =~ /-B(\S+)/)        { $val = $1; }  # dekker baade "-B V" og "-BV" via \S+-fangst etter split
  if (!defined $val) { return (1, 'A-BASE-MANGLER'); }
  $val =~ s/^["']//; $val =~ s/["']$//;
  if ($val =~ /^\$/) { return (1, 'A-BASE-UAVGJORT'); }
  if ($val eq '{{PROD_BRANCH}}') { return (1, 'A-BASE-MAIN'); }
  return (0, '');
}

my @candidates;
for my $v (@VALUES) {
  push @candidates, "gh pr create --title x --base $v";
  push @candidates, "gh pr create --title x --base=$v";
  push @candidates, "gh pr create --title x -B $v";
  push @candidates, "gh pr create --title x -B$v";
}
my $total = scalar(@candidates);

my $b2a = 0; my $a2b = 0;
my @b2a_list; my @a2b_list;
for my $cmd (@candidates) {
  my ($t, $treason) = today_base_block($cmd);
  my ($r, $rreason) = ref_base_block($cmd);
  if ($t == 1 && $r == 0) { $b2a++; push @b2a_list, $cmd; }
  elsif ($t == 0 && $r == 1) { $a2b++; push @a2b_list, "$cmd  (kode: $rreason)"; }
}

print "BASEROM KRYSSPRODUKT (4 flaggformer x 16 verdier) TOTALT: $total\n";
print "  BLOCK->ALLOW (dagens hook stod feil pga -B/--base=-blindhet): $b2a\n";
print "  ALLOW->BLOCK (ny presis --base=/-B-deteksjon)               : $a2b\n";
print "\n-- ALLOW->BLOCK-utdrag (foerste 8) --\n";
print "  $_\n" for (@a2b_list[0 .. (scalar(@a2b_list) > 8 ? 7 : $#a2b_list)]);

my $fail = 0;
if ($total != 64) { print "FEIL: TOTAL=$total, forventet 64\n"; $fail = 1; }
if ($b2a + $a2b > $total) { print "FEIL: b2a+a2b > total (umulig)\n"; $fail = 1; }

if ($fail) {
  print "GEN-BASEREFS: FEIL\n";
  exit 1;
} else {
  print "GEN-BASEREFS: OK\n";
  exit 0;
}
BASEREFSPLEOF
}

make_mini_repo() {
  local dir="$1" branch="$2"
  case "$branch" in
    none)
      mkdir -p "$dir"
      ;;
    *)
      # (r4-pålegg, MINDRE-8) ingen `git init -b` — versjonsuavhengig form.
      git init -q "$dir" >/dev/null 2>&1
      git -C "$dir" symbolic-ref HEAD "refs/heads/$branch" >/dev/null 2>&1
      ;;
  esac
}

mutate_hook_variant() {
  local variant="$1" src="$2" dest="$3"
  case "$variant" in
    perl-mangler)
      # Dagens hook kaller bart "perl -e" to steder (base-oppslag). PR2s
      # tilgjengelighetssjekk (A-PERL-MANGLER) finnes ikke i PR1 ennå — denne
      # mutasjonen viser likevel at DAGENS hook ikke bounder alt bak perl
      # (kun push/gh-pr-formene som faktisk kaller perl rammes).
      sed 's/perl -e/perl_FINNES_IKKE_188 -e/g' "$src" > "$dest"
      ;;
    jq-mangler)
      sed 's#/usr/bin/jq#/usr/bin/jq_FINNES_IKKE_188#g' "$src" > "$dest"
      ;;
    perl-stub-tom|perl-stub-exit3|len-probe|gh-mangler)
      # PR2-only konstruksjoner (inline perl-skanner, GH_BIN-blokk) finnes ikke
      # i dagens hook — kopien er en ren passthrough i PR1 (post-only rad,
      # meningsfull foerst naar PR2 lander).
      cp "$src" "$dest"
      ;;
    *)
      cp "$src" "$dest"
      ;;
  esac
  chmod +x "$dest"
}

build_longcmd() {
  # ~300000 byte, sendes via STDIN (aldri argv) — Linux' MAX_ARG_STRLEN
  # (128 KiB per argv-element) felte nøyaktig dette i TODO 187s CI-runde.
  local kind="$1"
  local pad
  pad="$(head -c 300000 /{{BASE_BRANCH}}/zero | tr '\0' 'x')"
  if [ "$kind" = "git" ]; then
    printf 'echo %s; git status' "$pad"
  else
    printf 'echo %s' "$pad"
  fi
}

build_input_json() {
  # cmd via STDIN til jq (-Rs), ALDRI som --arg-argv-element (samme
  # ARG_MAX-hensyn som build_longcmd).
  local cmd="$1" cwd="$2"
  printf '%s' "$cmd" | /usr/bin/jq -Rs --arg cwd "$cwd" '{tool_input: {command: .}, cwd: $cwd}'
}

# Årsakskatalog (§ 5 pkt 12, VIKTIG-7). ÅRSAK_NÅ/ÅRSAK_ETTER i radtabellen er
# SYMBOLSKE KODER, ikke hookens bokstavelige "Årsak: ..."-tekst — denne
# funksjonen oversetter kode -> grep -E-mønster mot den ordrette teksten.
# De ni kodene som faktisk finnes i DAGENS hook er beholdt ordrett (uendret
# tekst); resten er PR2-only og brukes kun i fase post (§ V9-differensialet).
reason_pattern_for_code() {
  case "$1" in
    A-PUSH-MAIN) echo 'git push direkte til {{PROD_BRANCH}}' ;;
    A-PUSH-ALLREFS) echo 'git push med --mirror/--all pusher alle refs, inkludert {{PROD_BRANCH}}' ;;
    A-BASE-MAIN) echo 'gh pr create med --base {{PROD_BRANCH}}' ;;
    A-BASE-MANGLER) echo 'gh pr create uten --base \(defaulter til {{PROD_BRANCH}}\)' ;;
    A-BASE-UAVGJORT) echo 'gh pr create med uavgjørbar base \(fail-safe\)' ;;
    A-EDIT-BASE-MAIN) echo 'gh pr edit med --base {{PROD_BRANCH}}' ;;
    A-MERGE-BASE-MAIN) echo 'gh pr merge av PR #[0-9]+ — base er {{PROD_BRANCH}}' ;;
    A-MERGE-UBEKREFTET) echo 'gh pr merge av PR #[0-9]+ — kunne ikke bekrefte base \(fail-safe\)' ;;
    A-MERGE-UTEN-PR) echo 'gh pr merge uten PR-argument \(fail-safe\)' ;;
    A-REST-BASE-MAIN) echo 'gh api REST-merge av PR #[0-9]+ — base er {{PROD_BRANCH}}' ;;
    A-REST-UBEKREFTET) echo 'gh api REST-merge av PR #[0-9]+ — kunne ikke bekrefte base \(fail-safe\)' ;;
    A-REST-UTEN-PR) echo 'gh api REST-merge uten uttrekkbart PR-nummer \(fail-safe\)' ;;
    A-GQL-MERGE) echo 'gh api graphql med mergePullRequest \(fail-safe\)' ;;
    A-GQL-UAVGJORT) echo 'gh api graphql med query fra fil \(--input/@\) - fail-safe' ;;
    A-PUSH-HEAD-MAIN) echo 'git push uten refspec med {{PROD_BRANCH}} utsjekket' ;;
    A-INPUT) echo 'kunne ikke lese tool_input \(jq exit=[0-9-]+\) - fail-closed' ;;
    A-UAVGJORT) echo 'uavgjørbar kommando \(.*\) - fail-safe' ;;
    A-FOR-LANG) echo 'kommando for lang \(over 262144 byte\) - uavgjorbar innen tidsbudsjett' ;;
    A-SKANNER) echo 'skanneren ga intet resultat \(perl exit=[0-9-]+\) - fail-closed' ;;
    A-PERL-MANGLER) echo 'perl \(/usr/bin/perl\) finnes ikke - fail-closed' ;;
    A-GH-MANGLER) echo 'gh finnes ikke i PATH - kan ikke bekrefte base \(fail-closed\)' ;;
    A-DYBDE) echo 'for dyp nesting \(over 5\) - uavgjorbar' ;;
    *) echo "$1" ;;
  esac
}

# Felles case-oppsett (fix-runde 2, MINDRE-5): brukt av BÅDE run_case() og
# cmd_diff(), slik at de to kjøremodiene ikke kan divergere i hvilke
# stub-tokens (map:/fail:/sleep:/sleep_child:/hang_after_close:/variant:) som
# tolkes. Før fiksen tolket cmd_diff() kun map:/fail: — variant-, sleep-,
# sleep_child- og hang_after_close-rader ble aldri mutert/stubbet i --diff,
# så en variant-båret regresjon kunne stå usett i --diff selv om run_case()
# fanget den.
#
# Setter (uten `local` — bevisst dynamisk skop inn i callerens variabler, som
# MÅ deklarere alle disse `local` FØR kallet): T BINDIR stubspec repo special
# walltime variant cwd_val cmd input.
setup_case_fixture() {
  local _id="$1"
  T="$(mktemp -d)"
  BINDIR="$T/bin"
  mkdir -p "$BINDIR" "$T/proj"
  write_gh_stub "$BINDIR/gh"

  stubspec="$(row_stub "$_id")"
  repo="$(row_repo "$_id")"
  special="$(row_special "$_id")"
  walltime="$(row_walltime "$_id")"

  unset STUB_MAP STUB_FAIL STUB_SLEEP STUB_SLEEP_CHILD STUB_HANG_AFTER_CLOSE 2>/dev/null || true
  variant=""
  local tok
  for tok in $stubspec; do
    case "$tok" in
      map:*) export STUB_MAP="${tok#map:}" ;;
      fail:*) export STUB_FAIL="1" ;;
      sleep:*) export STUB_SLEEP="${tok#sleep:}" ;;
      sleep_child:*) export STUB_SLEEP_CHILD="${tok#sleep_child:}" ;;
      hang_after_close:*) export STUB_HANG_AFTER_CLOSE="${tok#hang_after_close:}" ;;
      variant:*) variant="${tok#variant:}" ;;
    esac
  done

  if [ -n "$repo" ]; then
    cwd_val="$T/work"
    make_mini_repo "$cwd_val" "$repo"
  else
    cwd_val="$T"
  fi

  case "$special" in
    invalid_json) input='ikke-json{{{' ;;
    empty_stdin) input='' ;;
    longcmd_git) cmd="$(build_longcmd git)"; input="$(build_input_json "$cmd" "$cwd_val")" ;;
    longcmd_nogit) cmd="$(build_longcmd nogit)"; input="$(build_input_json "$cmd" "$cwd_val")" ;;
    *) cmd="$(row_cmd "$_id")"; input="$(build_input_json "$cmd" "$cwd_val")" ;;
  esac
}

# Resolverer effektiv hook-sti for én base-hook + variant (samme funksjon
# brukes av run_case() for ÉN hook og av cmd_diff() for HVER av de to
# hookene som sammenlignes — se MINDRE-5 over).
resolve_effective_hook() {
  local _base="$1" _variant="$2"
  if [ -n "$_variant" ]; then
    local _out
    _out="$T/hook-variant-$RANDOM-$RANDOM.sh"
    mutate_hook_variant "$_variant" "$_base" "$_out"
    printf '%s' "$_out"
  else
    printf '%s' "$_base"
  fi
}

# ───────────────────────── run_case ──────────────────────────────────────

TOTAL_COUNT=0
SKIP_COUNT=0
KNOWN_COUNT=0
OK_COUNT=0
AVVIK_COUNT=0
FAIL_SELFCHECK=0

run_case() {
  local id="$1"
  local rec
  rec="$(row_meta "$id")"
  local phase known want_now want_after klass argv_now argv_after reason_now reason_after desc
  IFS=$'\x1f' read -r phase known want_now want_after klass argv_now argv_after reason_now reason_after desc <<< "$rec"

  TOTAL_COUNT=$((TOTAL_COUNT + 1))

  local want="" argv_expected="" reason_expected=""
  if [ "$HARNESS_PHASE" = "pre" ] && [ "$phase" = "post" ]; then
    printf '%-6s %-6s %-9s %-5s %-6s %s\n' "$id" "-" "-" "-" "SKIP" "$desc"
    SKIP_COUNT=$((SKIP_COUNT + 1))
    return 0
  fi
  if [ "$HARNESS_PHASE" = "pre" ]; then
    want="$want_now"; argv_expected="$argv_now"; reason_expected="$reason_now"
  else
    want="$want_after"; argv_expected="$argv_after"; reason_expected="$reason_after"
  fi

  local T BINDIR stubspec repo special walltime variant cwd_val cmd input
  setup_case_fixture "$id"

  local effective_hook
  effective_hook="$(resolve_effective_hook "$HOOK" "$variant")"

  local argvlog="$T/gh-argv.log"
  local stdoutf="$T/stdout.log" stderrf="$T/stderr.log"
  local start end elapsed rc actual

  start=$(date +%s)
  printf '%s' "$input" | GH_ARGV_LOG="$argvlog" PATH="$BINDIR:$PATH" CLAUDE_PROJECT_DIR="$T/proj" bash "$effective_hook" >"$stdoutf" 2>"$stderrf"
  rc=$?
  end=$(date +%s)
  elapsed=$((end - start))

  case "$rc" in
    2) actual="BLOCK" ;;
    0) actual="ALLOW" ;;
    *) actual="ERROR($rc)" ;;
  esac

  local dom="OK" note=""

  if [ "$actual" != "$want" ]; then
    dom="AVVIK"
    note=" [forventet $want, fikk $actual]"
  fi

  if [ -n "$walltime" ] && [ "$elapsed" -gt "$walltime" ]; then
    dom="AVVIK"
    note="$note [TIDSBUDSJETT ${elapsed}s > ${walltime}s]"
  fi

  local loglines=0
  if [ -f "$argvlog" ]; then
    loglines=$(wc -l < "$argvlog" | tr -d ' ')
  fi
  if [ -n "$argv_expected" ]; then
    if [ "$argv_expected" = "INGEN" ]; then
      if [ "$loglines" -ne 0 ]; then
        dom="AVVIK"
        note="$note [ARGV: forventet INGEN, fikk $loglines linje(r)]"
      fi
    else
      local actual_argv=""
      [ -f "$argvlog" ] && actual_argv="$(cat "$argvlog")"
      if [ "$loglines" -ne 1 ] || [ "$actual_argv" != "$argv_expected" ]; then
        dom="AVVIK"
        note="$note [ARGV: forventet '$argv_expected', fikk '$actual_argv']"
      fi
    fi
  else
    # S8 (r4-pålegg, MINDRE-10; utvidet i fix-runde 2, VIKTIG-1): rad uten et
    # gh-stub-token (map:/fail:/sleep:/sleep_child:/hang_after_close: —
    # `variant:` alene bytter kun hook-variant og lover ikke noe gh-kall) skal
    # ha tom argv-logg for fasen den skåres i. Den forrige betingelsen krevde
    # i tillegg at HELE $stubspec var tom, som lot rader med KUN `variant:`
    # (f.eks. P13/P24 — post-only, tom ARGV_FORVENTET_ETTER) unnslippe denne
    # sjekken helt: verken S7 (som bare gjelder gh-stub-tokens) eller denne
    # grenen (blokkert av det ikke-tomme stubspec-et) fanget dem. Målt med en
    # hook-mutant som legger til et ekstra `gh pr view 999 ... || true`-kall
    # etter FIRST-utledningen: uten fiksen rapporterte P13/P24 OK i fase post
    # mens K4/A1/P30 (rader uten noen STUB) korrekt felte mutanten.
    local has_gh_stub=0
    case "$stubspec" in
      *map:*|*fail:*|*sleep:*|*sleep_child:*|*hang_after_close:*) has_gh_stub=1 ;;
    esac
    if [ "$has_gh_stub" -eq 0 ] && [ "$loglines" -ne 0 ]; then
      dom="AVVIK"
      note="$note [ARGV: uventet gh-kall, $loglines linje(r), raden har ingen gh-stub-token]"
    fi
  fi

  if [ -n "$reason_expected" ]; then
    local reason_pattern
    reason_pattern="$(reason_pattern_for_code "$reason_expected")"
    # Forankret mot linjestart (r4-pålegg fix-runde 1, MINDRE-3): et uforankret
    # grep mot HELE stderr matcher også hookens egen ekko av $CMD i
    # "kjør med vilje"-teksten — målt falsk match: en gh pr create-tittel som
    # bokstavelig inneholder årsaksfrasen ("fiks: git push direkte til {{PROD_BRANCH}}").
    if ! grep -qE -- "^Årsak: $reason_pattern" "$stderrf" 2>/dev/null; then
      dom="AVVIK"
      note="$note [AARSAK: kode '$reason_expected' ('$reason_pattern') ikke funnet i stderr]"
    fi
  fi

  if [ "$known" = "1" ] && [ "$dom" = "OK" ]; then
    dom="KJENT"
  fi

  printf '%-6s %-6s %-9s %-5s %-6s %s%s\n' "$id" "$want" "$actual" "${elapsed}s" "$dom" "$desc" "$note"

  case "$dom" in
    OK) OK_COUNT=$((OK_COUNT + 1)) ;;
    KJENT) KNOWN_COUNT=$((KNOWN_COUNT + 1)) ;;
    AVVIK) AVVIK_COUNT=$((AVVIK_COUNT + 1)) ;;
  esac

  rm -rf "$T"
}

run_self_checks() {
  # S1/S2/S3 — strukturelle, gjelder tabellen selv, uavhengig av fase/kjoring.
  local id rec phase known want_now want_after klass argv_now argv_after reason_now reason_after desc
  for id in $ALL_IDS; do
    rec="$(row_meta "$id")"
    IFS=$'\x1f' read -r phase known want_now want_after klass argv_now argv_after reason_now reason_after desc <<< "$rec"
    if [ "$phase" = "post" ]; then
      if [ -n "$want_now" ]; then
        echo "S3-BRUDD: $id er post-only men har WANT_NOW satt" >&2
        FAIL_SELFCHECK=1
      fi
    else
      if [ -z "$want_now" ]; then
        echo "S3-BRUDD: $id er 'both' men mangler WANT_NOW" >&2
        FAIL_SELFCHECK=1
      fi
      if [ "$want_now" != "$want_after" ] && [ -z "$klass" ]; then
        echo "S1-BRUDD: $id har WANT_NOW($want_now) != WANT_AFTER($want_after) uten CHANGE_KLASSE" >&2
        FAIL_SELFCHECK=1
      fi
      if [ -n "$klass" ]; then
        if [ "$want_now" = "$want_after" ]; then
          echo "S2-BRUDD: $id har CHANGE_KLASSE=$klass men WANT_NOW==WANT_AFTER" >&2
          FAIL_SELFCHECK=1
        elif [ "$want_now" = "ALLOW" ] && [ "$want_after" = "BLOCK" ] && [ "$klass" != "NEW_BLOCK" ]; then
          echo "S2-BRUDD: $id er ALLOW->BLOCK men klasse=$klass (forventet NEW_BLOCK)" >&2
          FAIL_SELFCHECK=1
        elif [ "$want_now" = "BLOCK" ] && [ "$want_after" = "ALLOW" ] && [ "$klass" != "INTENTIONAL_UNBLOCK" ]; then
          echo "S2-BRUDD: $id er BLOCK->ALLOW men klasse=$klass (forventet INTENTIONAL_UNBLOCK)" >&2
          FAIL_SELFCHECK=1
        fi
      fi
    fi

    # S7 (r4-pålegg fix-runde 1, VIKTIG-1): rader som setter opp en gh-stub
    # (map:/fail:/sleep:/sleep_child:/hang_after_close: — IKKE variant: alene,
    # som kun bytter ut hook-varianten uten å love et gh-kall) må ha eksplisitt
    # ARGV_FORVENTET for hver fase raden faktisk skåres i (ordrett argv-linje
    # eller literalen INGEN). Uten dette gjør run_case() ALDRI noen ARGV-sjekk
    # for raden (§ run_case, argv_expected tom + stubspec ikke-tom er det ene
    # hullet S8 ikke dekker) — en mutant som f.eks. hardkoder BASE={{PROD_BRANCH}} og
    # aldri kaller gh, overlever da umerket på nettopp disse radene.
    local stubspec_s7
    stubspec_s7="$(row_stub "$id")"
    case "$stubspec_s7" in
      *map:*|*fail:*|*sleep:*|*sleep_child:*|*hang_after_close:*)
        if [ "$phase" != "post" ] && [ -z "$argv_now" ]; then
          echo "S7-BRUDD: $id har STUB ($stubspec_s7) men mangler ARGV_FORVENTET_NAA" >&2
          FAIL_SELFCHECK=1
        fi
        if [ -z "$argv_after" ]; then
          echo "S7-BRUDD: $id har STUB ($stubspec_s7) men mangler ARGV_FORVENTET_ETTER" >&2
          FAIL_SELFCHECK=1
        fi
        ;;
    esac
  done
}

cmd_gen_refspecs() {
  local T pl
  T="$(mktemp -d)"
  pl="$T/gen-refspecs.pl"
  write_gen_refspecs_pl "$pl"
  perl "$pl"
  local rc=$?
  rm -rf "$T"
  return $rc
}

cmd_gen_baserefs() {
  local T pl
  T="$(mktemp -d)"
  pl="$T/gen-baserefs.pl"
  write_gen_baserefs_pl "$pl"
  perl "$pl"
  local rc=$?
  rm -rf "$T"
  return $rc
}

cmd_list_classes() {
  local id rec phase known want_now want_after klass argv_now argv_after reason_now reason_after desc
  echo "-- NEW_BLOCK --"
  for id in $ALL_IDS; do
    rec="$(row_meta "$id")"
    IFS=$'\x1f' read -r phase known want_now want_after klass argv_now argv_after reason_now reason_after desc <<< "$rec"
    [ "$klass" = "NEW_BLOCK" ] && echo "$id"
  done
  echo "-- INTENTIONAL_UNBLOCK --"
  for id in $ALL_IDS; do
    rec="$(row_meta "$id")"
    IFS=$'\x1f' read -r phase known want_now want_after klass argv_now argv_after reason_now reason_after desc <<< "$rec"
    [ "$klass" = "INTENTIONAL_UNBLOCK" ] && echo "$id"
  done
}

cmd_diff() {
  local old="$1" new="$2"
  if [ ! -f "$old" ] || [ ! -f "$new" ]; then
    echo "Bruk: --diff <gammel-hook> <ny-hook>" >&2
    exit 1
  fi
  local id rec phase known want_now want_after klass argv_now argv_after reason_now reason_after desc
  local diffcount=0
  for id in $ALL_IDS; do
    rec="$(row_meta "$id")"
    IFS=$'\x1f' read -r phase known want_now want_after klass argv_now argv_after reason_now reason_after desc <<< "$rec"

    local T BINDIR stubspec repo special walltime variant cwd_val cmd input
    setup_case_fixture "$id"
    local effective_old effective_new
    effective_old="$(resolve_effective_hook "$old" "$variant")"
    effective_new="$(resolve_effective_hook "$new" "$variant")"

    local rc_old rc_new v_old v_new
    printf '%s' "$input" | PATH="$BINDIR:$PATH" CLAUDE_PROJECT_DIR="$T/proj" bash "$effective_old" >/dev/null 2>/dev/null; rc_old=$?
    printf '%s' "$input" | PATH="$BINDIR:$PATH" CLAUDE_PROJECT_DIR="$T/proj" bash "$effective_new" >/dev/null 2>/dev/null; rc_new=$?
    case "$rc_old" in 2) v_old=BLOCK ;; 0) v_old=ALLOW ;; *) v_old="ERROR($rc_old)" ;; esac
    case "$rc_new" in 2) v_new=BLOCK ;; 0) v_new=ALLOW ;; *) v_new="ERROR($rc_new)" ;; esac

    if [ "$v_old" != "$v_new" ]; then
      local ok=0
      if [ "$v_old" = "BLOCK" ] && [ "$v_new" = "ALLOW" ] && [ "$klass" = "INTENTIONAL_UNBLOCK" ]; then ok=1; fi
      if [ "$v_old" = "ALLOW" ] && [ "$v_new" = "BLOCK" ] && [ "$klass" = "NEW_BLOCK" ]; then ok=1; fi
      if [ "$ok" -eq 0 ]; then
        echo "DIFF-AVVIK: $id  $v_old -> $v_new  (klasse=${klass:-INGEN})"
        diffcount=$((diffcount + 1))
      fi
    fi
    rm -rf "$T"
  done
  echo "Uklassifiserte differanser: $diffcount"
  [ "$diffcount" -eq 0 ]
}

# ───────────────────────── {{PROD_BRANCH}} ──────────────────────────────────────────

case "${1:-}" in
  --list-classes)
    cmd_list_classes
    exit 0
    ;;
  --diff)
    # r4-pålegg fix-runde 1, MINDRE-5: "$2"/"$3" er uavgjort under set -u når
    # --diff kalles uten argumenter — ${2:-}/${3:-} lar cmd_diff selv nå sin
    # bruksmelding i stedet for å dø her med "unbound variable".
    cmd_diff "${2:-}" "${3:-}"
    exit $?
    ;;
  --gen-refspecs)
    cmd_gen_refspecs
    exit $?
    ;;
  --gen-baserefs)
    cmd_gen_baserefs
    exit $?
    ;;
esac

run_self_checks
if [ "$FAIL_SELFCHECK" -ne 0 ]; then
  echo "Selv-assersjon feilet — se S*-BRUDD over. Avbryter før noen rad kjøres." >&2
  exit 1
fi

printf '%-6s %-6s %-9s %-5s %-6s %s\n' "ID" "ØNSKET" "ACTUAL" "TID" "DOM" "BESKRIVELSE"
printf -- '----------------------------------------------------------------------------------------------------------------------\n'

for id in $ALL_IDS; do
  run_case "$id"
done

printf -- '----------------------------------------------------------------------------------------------------------------------\n'
SCORED=$((OK_COUNT + AVVIK_COUNT))
echo "Scorede caser: $SCORED  |  OK: $OK_COUNT  |  AVVIK: $AVVIK_COUNT"
echo "EXPECTED_SUM=$EXPECTED_SUM EXPECTED_KNOWN=$EXPECTED_KNOWN EXPECTED_SKIP=$EXPECTED_SKIP EXPECTED_SCORED_TOTAL=$EXPECTED_SCORED_TOTAL"
echo "ACTUAL_SUM=$TOTAL_COUNT ACTUAL_KNOWN=$KNOWN_COUNT ACTUAL_SKIP=$SKIP_COUNT ACTUAL_SCORED=$SCORED"

STATUS=0
if [ "$TOTAL_COUNT" -ne "$EXPECTED_SUM" ]; then
  echo "S5-BRUDD: TOTAL_COUNT=$TOTAL_COUNT != EXPECTED_SUM=$EXPECTED_SUM" >&2
  STATUS=1
fi
if [ "$KNOWN_COUNT" -ne "$EXPECTED_KNOWN" ]; then
  echo "S5-BRUDD: KNOWN_COUNT=$KNOWN_COUNT != EXPECTED_KNOWN=$EXPECTED_KNOWN" >&2
  STATUS=1
fi
if [ "$SKIP_COUNT" -ne "$EXPECTED_SKIP" ]; then
  echo "S5-BRUDD: SKIP_COUNT=$SKIP_COUNT != EXPECTED_SKIP=$EXPECTED_SKIP" >&2
  STATUS=1
fi
if [ "$SCORED" -ne "$EXPECTED_SCORED_TOTAL" ]; then
  echo "S5-BRUDD: SCORED=$SCORED != EXPECTED_SCORED_TOTAL=$EXPECTED_SCORED_TOTAL" >&2
  STATUS=1
fi
if [ "$AVVIK_COUNT" -ne 0 ]; then
  STATUS=1
fi

exit $STATUS
