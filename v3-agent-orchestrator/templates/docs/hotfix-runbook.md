{{GENERATED_HEADER}}

# Hotfix-protokoll

**Trigger:** kode merget til `{{BASE_BRANCH}}` eller `{{PROD_BRANCH}}` utenfor en loop-sesjon
(hasteretting av en prod-feil, gjort direkte av den som fikser den — ikke via §3–§5b).
**Kutt hotfix-branchen fra `{{PROD_BRANCH}}`, ikke `{{BASE_BRANCH}}`** — en branch fra
`{{BASE_BRANCH}}` arver den åpne release-linjas uferdige tilstand.

**Én fiks = én rad.** Lander fiksen som to PR-er (`{{BASE_BRANCH}}` + port til `{{PROD_BRANCH}}`),
bærer raden `{{BASE_BRANCH}}`-PR-en; den andre klassifiseres i `## Avstemming` i run-loggen og får
aldri egen rad.

Fire punkter, alle obligatoriske:

1. **Én run-log-rad** i `docs/superpowers/loop/run-log.md`, `outcome=hotfix`:
   `<timestamp> | - | <slug> | hotfix | - | <PR-URL> | - | - | utenfor-loopen | <notat: symptom+rotårsak+fiks+filer> | -`
2. **Har prosjektet brukervendte release-notater:** én linje der også, merket tydelig som hotfix
   (f.eks. `**HOTFIX (prod-feil):**` foran beskrivelsen). Ingen slik praksis → hopp over.
3. **Bug-drop** i `tasks/bugs/inbox/` hvis rotårsaken ikke er lukket av selve fiksen.
4. **Forson** `{{PROD_BRANCH}}` → `{{BASE_BRANCH}}` (back-merge med merge-commit, ikke squash) hvis
   fiksen gikk rett til `{{PROD_BRANCH}}`.

## Dette er ALT

Ingen plan og ingen §4-review — hotfixen fikses og merges direkte. Run-log-avstemmingen ved
sesjonsstart (`.claude/commands/run-loop.md` § Preflight 4) fanger både en manglende rad og en
uforsonet `{{PROD_BRANCH}}`-hotfix — det er dit denne protokollen peker, ikke en egen mekanisme.
