<!--
  GENERERT av /setup fra loop.config.yaml — IKKE rediger her (kun § Format under).
  Endre loop.config.yaml og kjør /setup på nytt.
  MERK: Loggen nederst er append-only data koordinatoren skriver under kjøring —
  /setup overskriver IKKE eksisterende entries ved re-kjøring hvis du beholder
  dem. Ved første generering er den tom (kun format-spec). SEED_ONLY, samme
  vern som run-log.md/retro-log.md/retro-triage.md (`.github/skills/setup/SKILL.md`).
-->

# Beslutningslogg (koordinator)

**Single-writer-kontrakt:** Kun koordinatoren skriver til denne filen. Workers rører den ALDRI.

Nivå-B-beslutninger koordinatoren tar selv i stedet for å spørre mennesket — mot at hver av dem
er sporbar, begrunnet og vetobar. **Hvilke hendelser som er nivå A (spør) vs. nivå B (bestem selv +
logg her) er dokumentert ÉTT sted: `docs/loop/coordinator-runbook.md` § Pausepunkter**
(regeltabellene A1–A8/B1–B7, håndhevet mekanisk av `tasks/decision-level.py`) — denne fila kopierer
IKKE den lista (ingen-kopi-regelen, `docs/loop-rules.md` § «Tre kunnskapsbaser»).

**Veto:** svar i chatten — hver entry oppgir hvor lenge valget er reversibelt («Reversibel til»).

## Format

**Nivå A dekker uansett alltid** skriving mot prod-miljøet (`{{PROD_ENV_ID}}`), push/merge til
`{{PROD_BRANCH}}`, secrets og destruktive/irreversible operasjoner — se runbooken (peker over) for
den fulle, autoritative A1–A8/B1–B7-lista.

Entries **UNDER** `<!-- FORMAT-V2 -->`-markøren følger dette frosne formatet:

```
### <YYYY-MM-DD HH:MM> — TODO <nr> [<regel-id>]: <kort valg>

- **Grunnlag:** hva som utløste valget (målinger, rapport-utfall)
- **Valg:** hva koordinatoren gjorde
- **Alternativer forkastet:** (a) … (b) …
- **Reversibel til:** det siste punktet der valget kan omgjøres
```

Overskriften limes inn ordrett fra `header`-feltet i svaret fra `decision-level.py --event … --todo <nr> --title <tekst>`.

- **Nivå A-entries** får i tillegg tre linjer, som `decision-level.py --agreement` og
  `tasks/retro-numbers.py` leser: `- **Type:** <--event, ellers <slag> eller <slag>:<kort-navn>>`,
  `- **Anbefaling:** <koordinatorens anbefaling>` og `- **Eierens svar:**` i én av formene under. Leddet foran
  kolon i `Type` står i `SLAG` i `tasks/decision-level.py`, det eneste vokabularet (slag: `runder | eiervalg | risiko | kvittering | måling`).
  - `- **Eierens svar:** venter (spurt <YYYY-MM-DD HH:MM>)`: oppføringen skrives i det spørsmålet sendes.
  - `- **Eierens svar:** fulgt | avvek: <hva> (spurt <samme tid>, svart <YYYY-MM-DD HH:MM>)`: byttes inn når svaret kommer.
  - `- **Eierens svar:** ordre: <hva> (uoppfordret)`: eieren ga ordren uten å være spurt.
  - `- **Eierens svar:** se <svaroppføringens overskriftstid>`: bare når svaret likevel fikk egen oppføring. Den bærer da `(spurt …, svart …)`, og denne holdes utenfor slag og ventetid.

  Alle tider tas fra `date`, aldri fra hukommelsen. To redigeringer av en eksisterende entry er tillatt: å bytte
  ut `venter`-linja når svaret kommer, og at helsesjekkens D4 setter `Type`-linja ved `MANGLER_TYPE`/`UKJENT_TYPE`.
- `[B7]` fra runde 2 får `- **Konvergens:** gate-funn <prev>→<now>, ny feilklasse ja|nei, innhold
  nei, kost <credits>/<median>` (se `coordinator-runbook.md` § Konvergensregel; AI credits, eller
  `IKKE MÅLT` når bremsen ikke har tall).
- `[B1]` fra runde 2 får `- **Konvergens:** gate-funn <prev>→<now>, ny feilklasse ja|nei, innhold nei,
  kost <credits>/<median>`.

- `<regel-id>` ∈ `A1`…`A8` | `A0` | `B1`…`B8` | `D4` (helsesjekkens retting, `loop [D4]: rettet`) | `VETO av <B-id>` — hentet fra
  `python3 tasks/decision-level.py`, aldri fra hukommelsen. A-valg logges også (de bærer menneskets
  svar); `[B…]` er den greppbare diskriminatoren for nivå-B-avstemmingen i `.github/skills/loop-health-check/SKILL.md`
  Del D4.
- For `revise_gate_choice`-beslutninger (`[B1]`/`[A0]` på §5b-siden) ved `code_review_rounds >= 2`:
  legg til en femte linje, `- **Runde-SHA:** <pr_head_sha for runden>` — den samme SHA-en §5b
  «Trigger-sett»-steget allerede pinner (`gh pr view <pr> --json headRefOid`). Se
  `coordinator-runbook.md` § Pausepunkter «Residual» for hvorfor.
- `Reversibel til` er det eneste av de fire punktene som er strengt påkrevd i tillegg til
  `Grunnlag`/`Valg`/`Alternativer forkastet` — flere punkter (`Måling`, `Konsekvens`,
  `Carry-forwards`, `Retro-kandidat`, `Tilleggsvalg`) er tillatt etter de fire.
- **Splitt-terskel:** når loggen passerer ~400 linjer, periode-splitt den som `tasks/lessons/`-
  filene (kronologisk, `decision-log-<mnd><år>.md`). En `git mv` fjerner filen fra `SEED_ONLY` i
  `.github/skills/setup/SKILL.md` — splitt-todoen MÅ oppdatere `SEED_ONLY` (begge tvillinger) i SAMME
  PR, ellers seeder neste `/setup` en tom fil stille. `.github/skills/loop-health-check/SKILL.md` Del D3 (monoton
  entry-telling) fanger tapet hvis det likevel skjer.

Entries **OVER** markøren (skrevet i et annet, eldre format) er legacy —
**rettes ikke**, samme behandling som `run-log.md`s legacy-rader (`auto_decided=<nr>` uten kolon).

<!-- FORMAT-V2 — entries UNDER denne linja følger det frosne formatet i § Format. Entries OVER linja er legacy og rettes ikke. -->
