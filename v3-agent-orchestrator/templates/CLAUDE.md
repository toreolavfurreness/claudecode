# {{PROJECT_NAME}} — CLAUDE.md

> **Ansvarsdeling:**
>
> - **Denne filen** (`CLAUDE.md`) — prosjektets egne atferdsregler og infrastruktur. Eies av
>   prosjektet; `/setup` skrev den én gang og overskriver den aldri.
> - **`docs/loop-rules.md`** — loop-, lessons- og kunnskapsbase-reglene. Eies av kit-et, genereres
>   av `/setup` og importeres under. Rediger den ikke her — endre malen og kjør `/setup` på nytt.
> - **`docs/orchestration-loop.md`** — operatør-guide for den autonome loopen.

@docs/loop-rules.md

## Infrastruktur

<!-- Fyll inn: stack, hosting, database, eksterne tjenester. Behold miljø-ID-ene under ordrett —
     de er Tier-1 og står også i docs/loop-rules.md. -->

| Miljø    | ID                 | URL / konsoll | Brukes av |
| -------- | ------------------ | ------------- | --------- |
| **Dev**  | `{{DEV_ENV_ID}}`  | <fyll inn>    | Lokal utvikling, preview, e2e |
| **Prod** | `{{PROD_ENV_ID}}` | <fyll inn>    | Produksjon |

**ALDRI bruk en annen miljø-ID for kall, migrasjoner eller deploys.** Dev = daglig arbeid. Prod
kun ved planlagte releaser (`{{RELEASE_COMMAND}}`).

## Dokumentasjon

- Loop-regler: `docs/loop-rules.md`
- Loop-operatør-guide: `docs/orchestration-loop.md`
- Navnekonvensjoner: `docs/naming-conventions.md`
- Datamodell: `docs/data-model.md`
<!-- Legg til arkitektur, design-system o.l. etter hvert som de finnes. -->

## Språk

Svar alltid på {{LANGUAGE}}, uavhengig av hva brukeren skriver. Kode, variabler, commits og
lagrede dataverdier er på engelsk.

## Ufravikelige invarianter

{{TIER1_INVARIANTS}}

## Kodepraksis

- Forklar alltid hva koden gjør og hvorfor — ikke bare lever koden.
- **Trivielle endringer** (tekst, farge, enkel bug): gjør direkte uten å vente på bekreftelse.
- **Arkitekturvalg og oppgaver med 3+ steg:** skriv plan og vent på bekreftelse.
- Aldri lagre API-nøkler eller passord i koden.
- Aldri commit direkte til `{{PROD_BRANCH}}` — alltid branch + PR.
- Når noe feiler: be om feilmeldingen og feilsøk før du går videre.
- Etter feil fra brukeren: skriv en lesson i riktig tema-mappe under `tasks/lessons/`.

### Navnekonvensjoner

`docs/naming-conventions.md` er **obligatorisk lesning** før enhver oppgave som oppretter eller
endrer filer, mapper, variabler, funksjoner, komponenter, typer, databaseobjekter, branches,
commit-meldinger eller env-variabler. Avvik krever eksplisitt bekreftelse og dokumenteres i
fila under «Unntak og avvik».

## Det du ikke gjør

- Ikke introduser nye teknologier uten å forklare tydelig hvorfor.
- Ikke anta at brukeren kjenner terminologi.
- Ikke gi lange kodeblokker uten forklaring.
- Ikke fortsett til neste steg uten bekreftelse.
- Ikke late som du vet noe du ikke vet — si fra tydelig.
