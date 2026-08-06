{{GENERATED_HEADER}}

# Hotfix-protokoll

**Trigger:** kode merget til `{{BASE_BRANCH}}` eller `{{PROD_BRANCH}}` utenfor en loop-sesjon
(hasteretting av en prod-feil, gjort direkte av den som fikser den — ikke via §3-§5b).
**Kutt hotfix-branchen fra `{{PROD_BRANCH}}`, ikke `{{BASE_BRANCH}}`** — en branch kuttet fra
`{{BASE_BRANCH}}` arver den åpne release-linjas eventuelle udaterte tilstand og kan gi et korrekt,
men forvirrende, rødt kryss fra release-gaten midt i en hastesituasjon.

**Én fiks = én rad.** Lander fiksen som to PR-er (dev + main-port), bærer raden dev-PR-en;
main-PR-en klassifiseres i `## Avstemming`-seksjonen i run-loggen og får ALDRI egen rad.

Inntreffer dette, gjelder nøyaktig tre punkter — alle obligatoriske:

1. **Én run-log-rad** i `docs/superpowers/loop/run-log.md`, `outcome=hotfix`, i formatet fra
   format-spec-en, gjengitt ordrett:
   `<timestamp> | - | <slug> | hotfix | - | <PR-URL> | - | - | utenfor-loopen | <notat: symptom+rotårsak+fiks+filer> | -`
2. **Har prosjektet en brukervendt release-notat-praksis:** legg til én linje der også, i den
   BRUKERVENDTE endringstabellen (ikke i bug-/begrunnelsestabeller), merket tydelig som hotfix
   (f.eks. prefikset `**HOTFIX (prod-feil):**` foran den brukervendte beskrivelsen). Kolonnerekkefølgen
   kan variere mellom notater — les det aktuelle notatet FØR du skriver linja. Har prosjektet ingen
   slik praksis: hopp over dette punktet.
3. **Bug-drop** i `tasks/bugs/inbox/` hvis rotårsaken ikke er lukket av selve fiksen.

## Dette er ALT

Ingen plan, ingen §4-review, ingen verifikator-arm — hotfixen fikses og merges direkte av den som
finner den. Sesjonsstartens `### 0c`-blokk i `.claude/commands/run-loop.md` fanger uforsonede
main-hotfixer automatisk (main→dev-sjekken der) — det er dit denne protokollen peker, ikke en
egen mekanisme her.
