<!--
  GENERERT av /setup fra loop.config.yaml — IKKE rediger her.
  Endre loop.config.yaml og kjør /setup på nytt.
-->

# 8b. Drain retro-logg (ved §6c-helsesjekk — begge triggere — kun koordinator)

→ Kjerne: `coordinator-runbook.md` § 8b · Begrunnelser: `runbook-hvorfor.md` § 8b

**Modellert nøyaktig på §6b (drain bug-innboks)** — samme single-writer-mønster, samme sjanger.
Trigges av §6c-helsesjekk, begge triggere (se «Etter §6c»-forover-pekeren — uten den ville en
koordinator som leser §6c ovenfra og ned aldri lære at dette steget finnes): ved Trigger 1
(kø-tom/grooming) kjøres §8b FØR §7s grooming-forslag skrives (se forover-peker i §7); ved
Trigger 2 (hver N-te merge) kjøres §8b rett etter helseraden er skrevet, uavhengig av om
grooming kjører i samme runde. Uten denne todelte kadensen fyrer §8b nesten aldri — kø-tom er en
sjelden hendelse sammenlignet med merge-takten.

**Nivå B6:** hvilke Forbedringsforslag-linjer som forfremmes (`promoted`) eller lukkes
(`adopted`/`obsolete`) under er nivå B6 i `decision-level.py`. Logg per §8b-runde som faktisk
promoterer/lukker minst én rad — ikke per enkelt rad.

Les alt FRA `## Logg`-headeren TIL SLUTTEN AV FILA i `docs/superpowers/loop/retro-log.md` —
entries er selv `##`-headere, så en seksjonsgrense-basert scoping gir 0 treff (`##
Logg`-header til neste `##`-header matcher intet, siden hver entry allerede er en `##`-header).
Bruk `sed -n '/^## Logg/,$p' docs/superpowers/loop/retro-log.md`. Alt over `## Logg`
(format-spec + eksempel-entry) er utenfor scope; en naiv full-fil-`grep -c` over hele fila gir 8
i stedet for 6 reelle entries. For hver `Forbedringsforslag`-linje i scopet som ikke allerede
har en rad i `docs/superpowers/loop/retro-triage.md`:

- **Allerede innført** → append en rad med `outcome=adopted`.
- **Fortsatt relevant** → fremm til et todo-utkast (`status: deferred` + `tags: [forslag]`, samme
  konvensjon som §7s øvrige grooming-forslag) og append en rad med `outcome=promoted` og
  `ref=TODO NN` — **men kun hvis utestående-taket under tillater det**.
- **Utdatert** → append en rad med `outcome=obsolete`.
- **«ingen»** (fra `retro-log.md`s tillatte `**Forbedringsforslag:** ingen`) → hopp over uten
  rad — ingen beslutning å logge.

**Utestående-tak:** maks **3 utestående §8b-promoteringer** av gangen. Før du promoterer, tell
hvor mange tidligere §8b-promoterte todo-utkast som fortsatt ligger utriagert i køen (utkast med
`ref=TODO NN` fra `retro-triage.md` som ennå ikke er triagert av mennesket). Er det allerede 3,
promoteres INGEN nye denne runden — kandidatene forblir utriagerte i `retro-log.md` (ingen rad
skrives for dem her; de vurderes på nytt ved neste §8b-runde). Taket gjelder **på tvers av begge
triggere og er IKKE et per-invokasjons-budsjett**: det er bundet til hvor mange §8b-drafts som
venter på triage, ikke til hvor ofte §8b kjører — ellers ville hyppig Trigger 2-kjøring (hver
N-te merge) fylle køen ubegrenset, siden et per-invokasjons-budsjett gir friskt rom hver eneste
gang. Ved Trigger 1 (kø-tom) teller det §8b faktisk
promoterer denne runden i tillegg mot §7s EGNE, separate rundebudsjett på inntil 3 (se §7) — to
uavhengige tak som begge må være oppfylt, ikke ett delt tak.

<!-- mekanisk-kandidat: utestående-tak 3 — tell tags: [forslag]-todos med §8b-opphav (mangler) -->

Er antallet `promoted`-kandidater (etter utestående-taket over) større enn plassen som er igjen,
promoteres kun de høyest rangerte (rangér etter retro-entry-timestamp, nyeste først). De
overskytende kandidatene får INGEN rad i `retro-triage.md` — de forblir utriagerte og plukkes
opp ved neste §8b-runde. Skriv ALDRI `obsolete`/`adopted` på et forslag du fortsatt vurderer som
relevant; raden er permanent, og dedup-nøkkelen (under) gjør den uangripelig.

**Idempotens:** en retro-entry-timestamp som allerede har en rad i `retro-triage.md` hoppes over
— dedup-guardet append, FØR git-halen (samme idempotens-mønster som run-log-raden i §6 steg 5 og
retro-log-entryen i §8):

```bash
grep -qF "$TS |" docs/superpowers/loop/retro-triage.md \
  || printf '%s\n' "$ROW" >> docs/superpowers/loop/retro-triage.md
```

**Persistering:** `retro-triage.md`-raden og evt. nye todo-utkast-filer er delt state og MÅ
committes og pushes før §8b anses ferdig — hvordan avhenger av hvilken trigger som fyrte:

- **Trigger 1 (kø-tom/grooming):** §7 kjører rett etterpå og committer uansett sin egen
  **Delt-state-git-hale** (§6, steg 6, `$MSG="chore(loop): grooming — N forslag"`) — §8bs
  endringer fanges opp av DEN halen (samme `git add -A tasks/ docs/superpowers/loop/`), så
  ingen egen invokasjon er nødvendig her.
- **Trigger 2 (hver N-te merge):** ingen slik vertshale finnes — §6c har allerede kjørt sin
  EGEN hale for helseraden FØR §8b starter (se «Etter §6c»), og ingenting kjører automatisk
  etterpå. §8b MÅ derfor selv kjøre **Delt-state-git-halen** (§6, steg 6) med eget
  `$MSG="chore(loop): §8b retro-drain — N rader"`. Uten denne invokasjonen blir working tree
  skitten etter §8b, og neste todo treffer §0s «Working tree ikke ren → rapporter til
  mennesket og stopp» (hver Trigger-2-kjøring som
  skrev noe, stoppet loopen ved neste todo, siden ingen hale committet den).

`retro-triage.md` er runtime-state (seed-only, samme vern som `run-log.md`/`retro-log.md`):
filen seedes av `/setup` én gang og regenereres ALDRI (kun appendes av
koordinatoren).

`docs/superpowers/loop/retro-log.md` selv røres IKKE av dette steget — den forblir ren
append-only observasjonslogg (§8 skriver dit, ikke §8b). Kun `retro-triage.md` skrives til her.
