<!--
  GENERERT av /setup fra loop.config.yaml — IKKE rediger her.
  Endre loop.config.yaml og kjør /setup på nytt.
-->

# 7. Grooming-modus (kø tom)

→ Kjerne: `coordinator-runbook.md` § 7 · Begrunnelser: `runbook-hvorfor.md` § 7

Kjør §6c-helsesjekk FØR grooming-forslag (se §6c over).

**§8b (drain retro-logg) har allerede kjørt via §6c/Trigger 1 — ikke kjør den på nytt her.** Se
«Etter §6c» over: ved grønn helsesjekk kjøres §8b der, FØR forslagene under skrives (§8b er
plassert etter §8 i dokumentet fordi den drainer §8s retro-logg, men *trigges* av §6c). §8b går
gjennom alle utriagerte `Forbedringsforslag`-linjer i `retro-log.md`; promoteringer derfra
oppretter todo-utkast på samme måte som forslagene under, og **teller mot rundebudsjettet rett
nedenfor** — det samlede antallet utkast mennesket må triagere denne runden er fortsatt maks 3,
ikke 3 + 3 (§8b har i tillegg sitt eget, uavhengige utestående-tak på tvers av runder — se §8b).
Retro-forslag er grunnede observasjoner og går foran §7s egne spekulative forslag når
rundebudsjettet deles.

Ingen kvalifisert todo → IKKE stopp tomt. Foreslå inntil **3** nye todos/bugs totalt denne runden (§8b-promoteringer fra samme runde + egne forslag, rundebudsjett) som UTKAST med `status: deferred` + `tags: [forslag]`, basert på backlog/arkiv/observasjoner. Auto-implementer ALDRI selvgenerert arbeid. Etter 3 forslag: STOPP og rapporter til mennesket for triage. (Exit-kriterium hindrer uendelig grooming.)

**Forslag-konvensjon:** Hvert grooming-forslag opprettes med disse to feltene i frontmatteren:
```yaml
status: deferred
tags: [forslag]
```
Kombinasjonen er dobbel gating: `status: deferred` holder forslaget ute av §1-køen (som kun plukker `status: open`), og `tags: [forslag]` holder det ute selv om noen ved uhell flipper statusen uten å fjerne taggen.

**Persistering:** de nye todo-utkast-filene under `tasks/todos/` er delt state. Kjør
**Delt-state-git-halen** (§6, steg 6) for å committe og pushe dem,
`$MSG="chore(loop): grooming — N forslag"`. Deretter §8 mini-retro.

**Triage (gjøres av mennesket):** Et forslag godkjennes ved å flippe `status: deferred → open` OG fjerne `forslag`-taggen (`tags: []`). Begge endringer er nødvendige — kun én av dem er ikke tilstrekkelig for å gjøre forslaget kvalifisert (`elig=YES`). Avviste forslag beholder `status: deferred` og kan slettes eller beholdes som referanse.
