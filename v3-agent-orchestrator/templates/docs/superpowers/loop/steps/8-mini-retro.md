<!--
  GENERERT av /setup fra loop.config.yaml — IKKE rediger her.
  Endre loop.config.yaml og kjør /setup på nytt.
-->

# 8. Mini-retro (kø-tom/stopp)

→ Kjerne: `coordinator-runbook.md` § 8 · Begrunnelser: `runbook-hvorfor.md` § 8

Ved kø-tom (samme syklus som §7) eller ved ethvert pausepunkt-stopp: skriv en 5-linjers
strukturert retro-entry til append-only `docs/superpowers/loop/retro-log.md`:

```
## <YYYY-MM-DDTHH:MM> — <kort kontekst: N todos kjørt denne sesjonen / stopp-årsak>
**Fungerte:** <1 konkret ting som gikk bra>
**Friksjon:** <1 konkret friksjonspunkt, om noe>
**Forbedringsforslag:** <1 konkret, handlingsbar idé — eller «ingen» hvis intet nytt>
```

**Dedup-guardet retro-entry-append, FØR git-halen** (samme idempotens-mønster som run-log-raden
i §6 steg 5 — matcher på entry-ens timestamp-header):

```bash
grep -qF "## $TS —" docs/superpowers/loop/retro-log.md \
  || printf '%s\n' "$ENTRY" >> docs/superpowers/loop/retro-log.md
```

Deretter **Delt-state-git-halen** (§6, steg 6), `$MSG="chore(loop): mini-retro — <kontekst>"`.
`retro-log.md` dekkes av `git add -A … docs/superpowers/loop/` i halen — ingen egen commit
nødvendig. `retro-log.md` er runtime-state (seed-only, samme vern som run-log.md — se lesson
2026-06-30): filen seedes av `/setup` én gang og regenereres ALDRI (kun appendes av
koordinatoren, akkurat som run-log.md).
