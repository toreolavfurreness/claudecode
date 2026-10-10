<!--
  GENERERT av /setup fra loop.config.yaml — IKKE rediger her (kun format-spec).
  Endre loop.config.yaml og kjør /setup på nytt.
  MERK: Loggen nederst er append-only data som koordinatoren skriver under
  kjøring — /setup SEEDER denne filen kun ved første generering (finnes den
  ikke fra før). Ved re-kjøring bevares den uendret (samme seed-only-vern som
  run-log.md og retro-log.md). Ved første generering er den tom (kun header +
  format-spec).
-->

# Loop retro-triage (§8b — drain av retro-log.md)

**Single-writer-kontrakt:** Kun koordinatoren skriver til denne filen. Rader appendes ved
§6c-helsesjekk (begge triggere — kø-tom/grooming OG hver N-te merge, se §8b i
`coordinator-runbook.md`). Workers rører ALDRI retro-triage.md.

**Formål:** `retro-log.md` samler observasjoner (§8), men ingenting leste dem tilbake inn i
køen — forslag ble skrevet, men aldri drenert. Denne fila er beslutnings-loggen som lukker den
sløyfen: hver `**Forbedringsforslag:**`-linje i `retro-log.md` klassifiseres nøyaktig én gang
.

`retro-log.md` forblir uendret og rent append-only — den er *observasjons*-loggen. Denne fila
er *beslutnings*-loggen. `retro-log.md` og dens template røres IKKE av §8b.

---

## Format-spec

Én rad per triagert retro-ENTRY (§8s mal garanterer én `Forbedringsforslag`-linje per entry).
Pipe-separert, samme sjanger som `run-log.md`:

```
<retro-entry-timestamp> | <outcome> | <ref> | <kort norsk begrunnelse>
```

| Felt | Type | Lovlige verdier | Kilde |
|---|---|---|---|
| `retro-entry-timestamp` | streng | timestamp-headeren (`## <timestamp> —`) til retro-entryen forslaget står i, ordrett fra `retro-log.md` | `retro-log.md` |
| `outcome` | enum | `adopted` \| `promoted` \| `obsolete` | Koordinatorens vurdering ved §8b |
| `ref` | streng / `-` | `TODO NN` ved `promoted`, ellers `-` | Koordinatorens kontekst |
| `<kort norsk begrunnelse>` | streng | fri tekst, norsk | Koordinatorens kontekst |

`outcome`-betydning:
- `adopted` — forslaget er allerede innført (funnet i eksisterende kø/kode/dokumentasjon).
- `promoted` — forslaget er fortsatt relevant og er fremmet til et todo-utkast (`status: deferred`
  + `tags: [forslag]`, samme konvensjon som øvrige grooming-forslag). `ref` peker på todo-nummeret.
- `obsolete` — forslaget er utdatert (forutsetningen har endret seg, eller er overtatt av noe annet).
- **«ingen»** (fra `retro-log.md`s tillatte `**Forbedringsforslag:** ingen`) → ingen rad skrives
  — hoppes over ved §8b som «ingen beslutning å logge».

**Skann-scope:** les alt FRA `## Logg`-headeren TIL SLUTTEN AV FILA i `retro-log.md` — entries
er selv `##`-headere, så en seksjonsgrense-basert scoping (stopp ved neste `##`) gir 0 treff.
Bruk `sed -n '/^## Logg/,$p' docs/superpowers/loop/retro-log.md`. Alt over `## Logg`
(format-spec + eksempel-entry) er utenfor scope; en naiv full-fil-`grep -c
'^\*\*Forbedringsforslag:\*\*'` over hele `retro-log.md` teller også disse to og gir 8 i stedet
for 6 reelle entries.

**Dedup-guard:** en rad hvis `retro-entry-timestamp` allerede finnes i denne fila hoppes over —
merkingen ER dedup-nøkkelen. `grep -qF "<ts> |"` FØR skriving, samme idempotens-mønster som
run-log-radens `timestamp | todo_nr`-prefikstreff.

**Dato-kun-begrensning:** minst én entry i `retro-log.md` bruker dato uten klokkeslett
(`## YYYY-MM-DD —`, ingen `THH:MM`). To slike dato-kun-entries samme dag ville kollidert på
denne nøkkelen — samme begrensning som `retro-log.md`s egen dedup-guard allerede har og
allerede aksepterer.

**Utestående tak:** promoteringer fra denne fila (rader med `outcome=promoted`) teller mot et
**utestående-tak på 3** — maks 3 §8b-promoterte todo-utkast (identifisert ved `ref=TODO NN` her)
som samtidig ligger utriagert i køen. Før §8b promoterer noe, telles hvor mange tidligere
§8b-promoterte utkast som fortsatt er utriagert; er det allerede 3, promoteres INGEN nye denne
runden. Taket gjelder på tvers av begge triggere og er IKKE et per-invokasjons-budsjett — det er
bundet til hvor mye som venter på triage, ikke til hvor ofte §8b kjører (se §8b i
`coordinator-runbook.md` for full utledning). Ved Trigger 1 (kø-tom/grooming) teller det §8b
faktisk promoterer denne runden i tillegg mot §7s eget, separate rundebudsjett på inntil 3 (§7 i
`coordinator-runbook.md`) — to uavhengige tak, ikke ett delt tak. Er antallet `promoted`-
kandidater større enn plassen som er igjen under utestående-taket, promoteres kun de høyest
rangerte (nyeste retro-entry-timestamp først); overskuddet får INGEN rad her og forblir
utriagerte til neste §8b-runde — skriv ALDRI `obsolete`/`adopted` på et forslag som fortsatt er
relevant, raden er permanent og dedup-nøkkelen (over) gjør den uangripelig.

Raden persisteres via **Delt-state-git-halen** (§6, steg 6 i `coordinator-runbook.md`): ved
Trigger 1 dekkes den av §7s hale (som kjører rett etterpå), ved Trigger 2 kjører §8b halen selv
med eget `$MSG="chore(loop): §8b retro-drain — N rader"` (se §8b i `coordinator-runbook.md` for
detaljer — ingen vertshale finnes ved Trigger 2).

---

## Eksempel-rad

```
2026-07-12T20:15 | promoted | TODO 12 | Todo opprettet for å annotere presedens-referanser i run-log direkte.
```

---

## Triage
