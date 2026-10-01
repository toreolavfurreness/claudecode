<!--
  GENERERT av /setup fra loop.config.yaml — IKKE rediger her (kun § Format under).
  Endre loop.config.yaml og kjør /setup på nytt.
  MERK: Loggen nederst er append-only data koordinatoren skriver under kjøring —
  /setup overskriver IKKE eksisterende entries ved re-kjøring hvis du beholder
  dem. Ved første generering er den tom (kun format-spec). SEED_ONLY, samme
  vern som run-log.md/retro-log.md/retro-triage.md (`.claude/commands/setup.md`).
-->

# Beslutningslogg (koordinator, TODO 246)

**Single-writer-kontrakt:** Kun koordinatoren skriver til denne filen. Workers rører den ALDRI.

Nivå-B-beslutninger koordinatoren tar selv i stedet for å spørre mennesket — mot at hver av dem
er sporbar, begrunnet og vetobar. **Hvilke hendelser som er nivå A (spør) vs. nivå B (bestem selv +
logg her) er dokumentert ÉTT sted: `docs/superpowers/loop/coordinator-runbook.md` § Pausepunkter**
(regeltabellene A1–A8/B1–B7, håndhevet mekanisk av `tasks/decision-level.py`) — denne fila kopierer
IKKE den lista (ingen-kopi-regelen, `docs/loop-rules.md` § «Tre kunnskapsbaser»).

**Veto:** svar i chatten — hver entry oppgir hvor lenge valget er reversibelt («Reversibel til»).

## Format

**Nivå A dekker uansett alltid** skriving mot prod-miljøet (`{{PROD_ENV_ID}}`), push/merge til
`{{PROD_BRANCH}}`, secrets og destruktive/irreversible operasjoner — se runbooken (peker over) for
den fulle, autoritative A1–A8/B1–B7-lista.

Entries **UNDER** `<!-- FORMAT-V2 (TODO 246) -->`-markøren følger dette frosne formatet:

```
### <YYYY-MM-DD HH:MM> — TODO <nr> [<regel-id>]: <kort valg>

- **Grunnlag:** hva som utløste valget (målinger, rapport-utfall)
- **Valg:** hva koordinatoren gjorde
- **Alternativer forkastet:** (a) … (b) …
- **Reversibel til:** det siste punktet der valget kan omgjøres
```

- `<regel-id>` ∈ `A1`…`A8` | `A0` | `B1`…`B7` | `VETO av <B-id>` — hentet fra
  `python3 tasks/decision-level.py`, aldri fra hukommelsen. A-valg logges også (de bærer menneskets
  svar); `[B…]` er den greppbare diskriminatoren for nivå-B-avstemmingen i `loop-health-check.md`
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
  `.claude/commands/setup.md` — splitt-todoen MÅ oppdatere `SEED_ONLY` (begge tvillinger) i SAMME
  PR, ellers seeder neste `/setup` en tom fil stille. `loop-health-check.md` Del D3 (monoton
  entry-telling) fanger tapet hvis det likevel skjer.

Entries **OVER** markøren (fantes før TODO 246, skrevet i et annet, eldre format) er legacy —
**rettes ikke**, samme behandling som `run-log.md`s legacy-rader (`auto_decided=<nr>` uten kolon).

<!-- FORMAT-V2 (TODO 246) — entries UNDER denne linja følger det frosne formatet i § Format. Entries OVER linja er legacy (pre-246) og rettes ikke. -->
