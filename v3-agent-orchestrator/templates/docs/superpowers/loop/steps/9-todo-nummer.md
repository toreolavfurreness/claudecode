<!--
  GENERERT av /setup fra loop.config.yaml — IKKE rediger her.
  Endre loop.config.yaml og kjør /setup på nytt.
-->

# 9. Todo-nummer: reservasjon, kollisjon og renummerering

→ Kjerne: `coordinator-runbook.md` § 9

Racet ved *valg* av `nr` kan ikke lukkes uten atomisk reservasjon. §6.4 gate (b) evaluerer
merge-RESULTATET og fanger den andre siden av en kollisjon rett før merge — men krymper, lukker
ikke, vinduet. Risikoen øker med §5c/§5d (flere spor i flukt) og med flere koordinator-sesjoner.

**Valg av nr:** `git fetch origin {{BASE_BRANCH}}`, så `sh scripts/check-todo-nr-collisions.sh --next`
(regner mot arbeidstreet ∪ `origin/{{BASE_BRANCH}}`). Gjelder hver ny todo — grooming (§7),
bug-triage (§6b) og forslag.

**Reservasjon teller FØRST når** minimal frontmatter (tittel + `nr` + status) er committet **og
pushet** til `{{BASE_BRANCH}}`. Commit og push den minimale fila FØR resten skrives. Todos som
fødes inne i en feature-PR er ikke reservert — de bæres av §6.4 gate (b).

**Retningsregel: «sist inn flytter».** Ved kollisjon renummererer PR-en som ennå ikke har merget;
den allerede mergede står urørt.

**Renummerering** (trigges av gate (b) exit 1, eller exit 3 med en reell nr-kollisjon under
`tasks/todos/`):
1. Nye nr med `--next` mot fersk `origin/{{BASE_BRANCH}}`; for en epic tas alle N samtidig.
2. `git mv` filnavn + oppdater `nr`, `order`, `deps` (og `plan:`/planfilnavn).
3. Prosa: `git grep -niE 'todo-0*<gammelt-nr>([^0-9]|$)' -- tasks docs` — klassifiser **hvert**
   treff. Vakten validerer kun `nr`-unikhet og er grønn mens prosa peker på feil todo.
4. Bare-tall-referanser (`438–443`) fanges ikke av grep — les de flyttede filene manuelt
   (`git diff --name-only`). Sjekkliste, ikke vakt.
5. Re-kjør gate (b) før nytt merge-forsøk.
