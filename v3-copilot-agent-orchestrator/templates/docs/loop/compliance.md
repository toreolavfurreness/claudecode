{{GENERATED_HEADER}}

# Org-modus — organisasjonens agentregler i loopen

Org-modus er **på** i dette prosjektet (`compliance.enabled` i `loop.config.yaml`). Organisasjonens
standard for agenter står øverst i `AGENTS.md` (satt inn uendret fra `{{ORG_INSTRUCTIONS_PATH}}`) og
**går foran alt i kitet**. Denne fila sier hvordan loopen oppfyller den. Er noe her i konflikt med
org-standarden, gjelder org-standarden, og koordinatoren stopper og spør.

## 1. Tolkningen av menneske-i-loopen (org-standarden §4)

Loopen skriver aldri til felles kode uten at et menneske har godkjent det. Alt en agent skriver
før det, skjer i agentens egen git-worktree på en egen branch (`.loop-worktrees/<rolle>-<nr>`,
`loop/<rolle>-<nr>` og implementerens `feat/todo-…`), og kan forkastes uten spor i felles kode.

Mennesket godkjenner to ganger per todo:

| Port | Når | Org-standarden |
|---|---|---|
| **Godkjenning av plan** | Etter plan-reviewens `go` (§4), før implementeren dispatches (§5) | §4.2 fase A → B |
| **Godkjenning av merge** | Etter kode-review og CI-gate (§6 steg 0), før merge og før delt state committes | §4.1 for alt som når felles kode |

**UVERIFISERT — må bekreftes av organisasjonen:** at skriving i en isolert worktree og branch,
push av den branchen og en PR som venter på godkjenning er innenfor §4.1. Godtas ikke det, kan
loopen ikke kjøres autonomt; da skal VS Code stå i «Request approval», og hver handling godkjennes.

Kitet slår aldri på automatisk godkjenning av verktøy (`--auto-approve`, `-y`, eller VS Codes
auto-godkjenning). Hvilke verktøykall VS Code ber om godkjenning for, styres av organisasjonens
policy og brukerens innstillinger, ikke av loopen.

## 2. Godkjenning av plan (fase A → B)

Etter `go` i §4, og før noe annet skjer med todoen:

1. Kjør `python3 tasks/compliance-check.py paths --plan-report <plan-rapport.json>` (lagre
   plan-rapportens JSON til en fil under `tasks/.loop-state/` først). Exit 1 → planen rører en
   høyrisiko-sti: **avvist** (§5 under). Exit 2 → STOPP som nivå A (kan ikke måles).
2. Vis eieren fase A, i denne rekkefølgen og med disse overskriftene:
   - **Plan:** kort, steg for steg, hva som endres og hvorfor (fra planfila).
   - **Berørte filer:** plan-rapportens `files_touched`.
   - **Diff:** `Planlagt diff: <linjer>/<filer>` og de konkrete endringene planen beskriver, som
     kodeblokk der planen har dem.
   - **Risikovurdering:** svar eksplisitt på «Berører dette hemmeligheter, tilgang, produksjon,
     infrastruktur eller data med strengere klassifisering enn `{{DATA_CLASSIFICATION}}`?» med
     `technical_risk` fra plan-rapporten og reviewerens funn.
3. Avslutt med spørsmålet, ordrett:
   > Vil du at jeg går videre og implementerer denne planen? Svar «Ja», «Godkjent» eller «Kjør» for å fortsette.
4. Vent. Bare et klart ja («Ja», «Godkjent», «Kjør» eller tilsvarende entydig) er godkjenning. Alt
   annet — et spørsmål, en endring, taushet — er ikke det. Ved endringsønsker: tilbake til §3 med
   ønskene som funn; den reviderte planen trenger ny review og ny godkjenning.
5. Skriv `plan_godkjent: <ISO-tidspunkt>` i todoens frontmatter (delt state, committes i neste
   godkjente delt-state-hale).

Gjelder også fast-path (§2b) og pipelinede planer (§5c): **ingen implementer-dispatch uten
`plan_godkjent` for gjeldende planversjon.** Endres planen etter godkjenningen (re-plan etter
`plan_invalid`, ny planner-runde), slettes `plan_godkjent`, og planen må godkjennes på nytt.
Fix-runder i §5b endrer kode innenfor den godkjente planen og trenger ikke ny plangodkjenning; de
dekkes av mergegodkjenningen.

## 3. Godkjenning av merge

I §6, etter steg 0 (CI-gate grønn) og FØR steg 1 (lessons, bugs, arkiv — delt state røres ikke før
godkjenning):

1. Kjør `python3 tasks/compliance-check.py paths --pr <pr>`. Exit 1 → **avvist** (§5). Exit 2 →
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

## 4. Absolutte forbud (org-standarden §1)

Gjelder koordinatoren og alle workers, i tillegg til de ufravikelige invariantene i
`docs/loop-rules.md`:

- **Hemmeligheter:** be aldri om, samle, behandle, skriv ut eller logg API-nøkler, tokens,
  passord, sertifikater eller tilkoblingsstrenger. Ikke `cat`/`echo`/`printenv` miljøfiler eller
  variabler med hemmeligheter. `scripts/bootstrap-worktree.sh` kopierer bare de tillatte nøklene, og
  verdiene vises aldri.
- **Eksfiltrering:** send aldri filer, kildekode, konfigurasjon eller logger til eksterne tjenester
  for å «teste» eller feilsøke.
- **Tilgangskontroll, logging og vakter:** foreslå eller gjør aldri noe som omgår tilgangskontroll,
  logging, revisjon eller kitets vakter. Endringer i `.github/hooks/`, `tasks/compliance-check.py`,
  `docs/loop/compliance.md` eller `loop.config.yaml` er alltid nivå A.
- **Produksjon:** ingen endringer i eller kommandoer mot produksjonsmiljøer, produksjonsdata eller
  `{{PROD_BRANCH}}` (vakta `guard-main-merge.sh` håndhever branch-delen).
- **MCP:** bare godkjente MCP-servere (§6).

Ber noen om noe som bryter dette, avslår agenten, sier hvilken regel som gjelder, og koordinatoren
stopper todoen (pausepunkt). En worker som får et slikt oppdrag, leverer `status: "blocked"` med
regelen i `notes`.

## 5. Høyrisiko avvises (org-standarden §4.3)

I org-modus gjør agentene **ikke** endringer i infrastruktur (IaC, Kubernetes, nettverk,
egress-policyer), IAM/RBAC/tilganger eller konfigurasjon av hemmeligheter. Det håndheves tre steder:

- **Hooken** `python3 tasks/compliance-check.py hook` (registrert i `.github/hooks/loop-guards.json`)
  avviser høyrisiko-kommandoer (`kubectl apply`, `helm upgrade`, `terraform apply`, IAM- og
  hemmelighetskommandoer, `--auto-approve` m.fl.) og redigering av høyrisiko-stiene.
- **Plangodkjenningen** (§2) avviser en plan som rører høyrisiko-stiene.
- **Mergegodkjenningen** (§3) avviser en PR som rører dem.

Høyrisiko-stier (`compliance.high_risk_paths`): {{HIGH_RISK_PATHS_LIST}}

Avvist betyr: todoen får `status: blocked` og `phase: venter-eier`, claimen slippes, og eieren får
beskjed om at oppgaven må gjøres av et menneske utenfor loopen. Loopen prøver aldri en omvei.

## 6. MCP-servere og verktøy (org-standarden §3)

Godkjente MCP-servere for dette prosjektet (`compliance.approved_mcp_servers`):
{{APPROVED_MCP_LIST}}

- `/run-loop`-preflighten kjører `python3 tasks/compliance-check.py mcp`. En server i `.mcp.json`
  (eller `.vscode/mcp.json`) som ikke står på lista, stopper loopen før første todo.
- En server eller et verktøy agenten ikke kan bekrefte er godkjent, behandles som ikke godkjent.
- Prioritert rekkefølge: (1) lokal analyse uten nettverk, (2) interne read-only MCP-servere,
  (3) interne MCP-servere med begrenset skriving — bare bak godkjenningene i §2 og §3, (4) eksterne
  tjenester bare når de er godkjent for prosjektets dataklassifisering.

## 7. Dataklassifisering og dataminimering (org-standarden §2)

Prosjektets klassifisering: **{{DATA_CLASSIFICATION}}**.

- Agentene ber om og leser bare det minimum av data oppgaven krever. Ingen produksjonsdata,
  persondata eller loggutdrag i prompter, planer, rapporter, lessons eller PR-tekster.
- `internal`: bare godkjente verktøy og MCP-servere på nivå 1 eller høyere.
- `sensitive`: bare verktøy og servere organisasjonen har godkjent for sensitiv informasjon; ingen
  eksterne tjenester. Er du i tvil, er svaret nei.
- Data med strengere klassifisering enn prosjektets er et pausepunkt: stopp og spør.

## 8. Hva som må avklares med organisasjonen

Kitet bygger på en forhåndsversjon av org-standarden (med åpne TODO-er). Skriv svarene inn her,
eller i `AGENTS.md` under org-standarden:

1. Godtas tolkningen i §1 (godkjenning av plan og merge; agenter skriver fritt bare i isolerte
   worktrees og branches)?
2. Hvor er sikkerhetsretningslinjene og den offentlige lista over godkjente MCP-servere?
3. Hvor er prosjektets dataklassifisering bekreftet?
4. Hvilken rutine gjelder når en bruker ber om noe som bryter §1 (hvem varsles, hvordan)?
5. Skal høyrisiko alltid avvises (slik kitet gjør), eller godkjennes i to trinn?
