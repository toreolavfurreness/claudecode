<!--
  GENERERT av /setup fra loop.config.yaml — IKKE rediger her (kun format-spec).
  Endre loop.config.yaml og kjør /setup på nytt.
  MERK: Loggen nederst er append-only data som koordinatoren skriver under
  kjøring — /setup SEEDER denne filen kun ved første generering (finnes den
  ikke fra før). Ved re-kjøring bevares den uendret (samme seed-only-vern som
  run-log.md, lesson 2026-06-30 — run-log ble klobbet før den beskyttelsen
  fantes). Ved første generering er den tom (kun header + format-spec).
-->

# Loop retro-log (koordinator mini-retro)

**Single-writer-kontrakt:** Kun koordinatoren skriver til denne filen. Entries appendes ved
kø-tom (§7/§8 i `coordinator-runbook.md`) eller ved ethvert pausepunkt-stopp. Workers rører
ALDRI retro-log.md.

**Formål:** loop-evaluering blir en del av loopen selv, ikke noe som skjer først når mennesket
spør (opphav: TODO 158, loop-evaluering 2026-07-12).

---

## Format-spec

Én entry per §8-invokasjon. Fast 5-linjers struktur:

```
## <YYYY-MM-DDTHH:MM> — <kort kontekst: N todos kjørt denne sesjonen / stopp-årsak>
**Fungerte:** <1 konkret ting som gikk bra>
**Friksjon:** <1 konkret friksjonspunkt, om noe — «ingen» hvis intet nevneverdig>
**Forbedringsforslag:** <1 konkret, handlingsbar idé — «ingen» hvis intet nytt>
```

**Dedup-guard:** entry-appenden matcher på timestamp-headeren (`## <timestamp> —`) FØR skriving
— samme idempotens-mønster som run-log-radens `timestamp | todo_nr`-nøkkel. To entries med
samme minutt-timestamp støttes derfor ikke av denne guarden; bruk et distinkt tidspunkt per
invokasjon (se `run-log.md` for presedens-unntaket dette mønsteret er hentet fra).

Entryen persisteres via samme delt-state-git-hale som run-log-raden (§6/§8 i
`coordinator-runbook.md`) — ingen egen commit-mekanikk her.

---

## Eksempel-entry

```
## 2026-07-12T20:15 — kø tom etter 5 todos denne sesjonen
**Fungerte:** Fast-path (§2b) sparte to hele planner/reviewer-runder på rene mekaniske todos.
**Friksjon:** Speil-guarden i git-halen krevde tre iterasjoner å få timing-robust.
**Forbedringsforslag:** Vurder å annotere presedens-referanser i run-log direkte, ikke bare i commit-meldingen.
```

---

## Logg

