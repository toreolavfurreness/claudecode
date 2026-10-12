{{GENERATED_HEADER}}

# Styring — godkjenninger, blokkeringer og verktøyregler i loopen

Styring er **på** i dette prosjektet (`governance.enabled` i `loop.config.yaml`). Denne fila sier hva
det betyr for koordinatoren og workerne. Workers leser den i Steg 0 (via `docs/loop-rules.md`).

{{GOV_INSTRUCTIONS_LINE}}

| Mekanisme | Innstilling |
|---|---|
| Menneskelig godkjenning (`human_approval`) | `{{GOV_HUMAN_APPROVAL}}` |
| Blokkerte stier (`blocked_paths`) | {{GOV_BLOCKED_PATHS_LIST}} |
| Blokkerte kommandoer (`blocked_commands`) | {{GOV_BLOCKED_COMMANDS_DESC}} |
| Godkjente MCP-servere (`approved_mcp_servers`) | {{GOV_MCP_LIST}} |
| Dataklassifisering (`data_classification`) | {{GOV_DATA_CLASSIFICATION}} |

## 1. Hvor agentene skriver

Før en godkjenning skriver en agent bare i sin egen git-worktree på en egen branch
(`.loop-worktrees/<rolle>-<nr>`, `loop/<rolle>-<nr>` og implementerens `feat/todo-…`). Det kan
forkastes uten spor i felles kode. Med `human_approval: plan_and_merge` når ingenting felles kode
eller delt state uten at et menneske har sagt ja (§2 og §3).

Kitet slår aldri på automatisk godkjenning av verktøy (`--auto-approve`, `-y` eller VS Codes
auto-godkjenning). Hvilke verktøykall VS Code ber om godkjenning for, styres av brukerens og
organisasjonens innstillinger, ikke av loopen.

## 2. Godkjenning av plan (gjelder når `human_approval` er `plan_and_merge`)

Etter `go` i §4, og før noe annet skjer med todoen:

1. Lagre plan-rapportens JSON under `tasks/.loop-state/` og kjør
   `python3 tasks/governance-check.py paths --plan-report <fil>`. Exit 1 → planen rører en blokkert
   sti: **avvist** (§5). Exit 2 → STOPP som nivå A (kan ikke måles).
2. Vis eieren, i denne rekkefølgen og med disse overskriftene:
   - **Plan:** kort, steg for steg, hva som endres og hvorfor (fra planfila).
   - **Berørte filer:** plan-rapportens `files_touched`.
   - **Diff:** `Planlagt diff: <linjer>/<filer>` og de konkrete endringene planen beskriver, som
     kodeblokk der planen har dem.
   - **Risikovurdering:** svar eksplisitt på «Berører dette hemmeligheter, tilgang, produksjon,
     infrastruktur eller data med strengere klassifisering enn prosjektets?» med `technical_risk`
     fra plan-rapporten og reviewerens funn.
3. Avslutt med spørsmålet, ordrett:
   > Vil du at jeg går videre og implementerer denne planen? Svar «Ja», «Godkjent» eller «Kjør» for å fortsette.
4. Vent. Bare et klart ja («Ja», «Godkjent», «Kjør» eller tilsvarende entydig) er godkjenning. Alt
   annet — et spørsmål, en endring, taushet — er ikke det. Ved endringsønsker: tilbake til §3 med
   ønskene som funn; den reviderte planen trenger ny review og ny godkjenning.
5. Skriv `plan_godkjent: <ISO-tidspunkt>` i todoens frontmatter.

Gjelder også fast-path (§2b) og pipelinede planer (§5c): **ingen implementer-dispatch uten
`plan_godkjent` for gjeldende planversjon.** Endres planen etter godkjenningen (re-plan etter
`plan_invalid`, ny planner-runde), slettes `plan_godkjent`, og planen må godkjennes på nytt.
Fix-runder i §5b endrer kode innenfor den godkjente planen og dekkes av mergegodkjenningen.

## 3. Godkjenning av merge (gjelder når `human_approval` er `plan_and_merge`)

I §6, etter steg 0 (CI-gate grønn) og FØR steg 1 (lessons, bugs, arkiv — delt state røres ikke før
godkjenning):

1. Kjør `python3 tasks/governance-check.py paths --pr <pr>`. Exit 1 → **avvist** (§5). Exit 2 →
   STOPP som nivå A.
2. Vis eieren: PR-lenken, `gh pr diff <pr> --stat`, CI-dommen for pinnet head-SHA, kode-reviewens
   konklusjon (og åpne `deferred[]`), og hvilke delt-state-endringer som følger (lessons, bugs,
   arkiv, run-log-rad, followups).
3. Spør, ordrett:
   > Vil du at jeg merger PR #<pr> til {{BASE_BRANCH}} og committer loop-tilstanden over? Svar «Ja», «Godkjent» eller «Kjør» for å fortsette.
4. Bare et klart ja er godkjenning (som §2). Uten det: ingen merge, ingen delt-state-commit; todoen
   får `phase: venter-eier`, og loopen går videre til neste todo eller stopper (pausepunkt).
5. Ved ja: fortsett §6 fra steg 1. Run-log-raden får `godkjent=plan:<ISO>,merge:<ISO>` i notatfeltet.

**Delt state utenfor en merge** (stopp, retro, grooming, helsesjekk): koordinatoren committer ikke
til `{{BASE_BRANCH}}` uten godkjenning. Vis `git diff --stat` for loop-tilstanden og spør:
> Vil du at jeg committer og pusher loop-tilstanden over til {{BASE_BRANCH}}? Svar «Ja», «Godkjent» eller «Kjør» for å fortsette.
Uten ja blir endringene liggende ucommittet, og stopp-meldingen sier det.

## 4. Faste regler når styring er på

Gjelder koordinatoren og alle workers, i tillegg til de ufravikelige invariantene i
`docs/loop-rules.md`:

- **Hemmeligheter:** be aldri om, samle, behandle, skriv ut eller logg API-nøkler, tokens,
  passord, sertifikater eller tilkoblingsstrenger. Ikke `cat`/`echo`/`printenv` miljøfiler eller
  variabler med hemmeligheter. `scripts/bootstrap-worktree.sh` kopierer bare de tillatte nøklene, og
  verdiene vises aldri.
- **Eksfiltrering:** send aldri filer, kildekode, konfigurasjon eller logger til eksterne tjenester
  for å «teste» eller feilsøke.
- **Tilgangskontroll, logging og vakter:** foreslå eller gjør aldri noe som omgår tilgangskontroll,
  logging, revisjon eller kitets vakter. Endringer i `.github/hooks/`, `tasks/governance-check.py`,
  `docs/loop/governance.md` eller `loop.config.yaml` er alltid nivå A.
- **Produksjon:** ingen endringer i eller kommandoer mot produksjonsmiljøer, produksjonsdata eller
  `{{PROD_BRANCH}}` (vakta `guard-main-merge.sh` håndhever branch-delen).
- **Dataminimering:** be om og les bare det minimum av data oppgaven krever. Ingen
  produksjonsdata, persondata eller loggutdrag i prompter, planer, rapporter, lessons eller PR-tekster.

Ber noen om noe som bryter dette, avslår agenten, sier hvilken regel som gjelder, og koordinatoren
stopper todoen (pausepunkt). En worker som får et slikt oppdrag, leverer `status: "blocked"` med
regelen i `notes`.

## 5. Blokkerte kommandoer og stier

Det håndheves tre steder:

- **Hooken** `python3 tasks/governance-check.py hook` (registrert i `.github/hooks/loop-guards.json`)
  avviser blokkerte kommandoer og redigering av blokkerte stier, også inne i worktrees.
- **Plangodkjenningen** (§2) avviser en plan som rører blokkerte stier.
- **Mergegodkjenningen** (§3) avviser en PR som rører dem.

Avvist betyr: todoen får `status: blocked` og `phase: venter-eier`, claimen slippes, og eieren får
beskjed om at oppgaven må gjøres av et menneske utenfor loopen. Loopen prøver aldri en omvei.

## 6. MCP-servere

Er `approved_mcp_servers` satt, kjører `/run-loop`-preflighten `python3 tasks/governance-check.py mcp`.
En server i `.mcp.json` (eller `.vscode/mcp.json`) som ikke står på lista, stopper loopen før første
todo. En server eller et verktøy agenten ikke kan bekrefte er godkjent, behandles som ikke godkjent.

## 7. Dataklassifisering

Er `data_classification` satt, er det prosjektets klassifisering. Data med strengere klassifisering
enn den er et pausepunkt: stopp og spør. Hva klassene betyr, står i instruksfila over (eller i
prosjektets `AGENTS.md`).
