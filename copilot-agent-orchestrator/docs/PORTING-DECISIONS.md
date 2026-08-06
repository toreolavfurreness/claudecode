# PORTING-DECISIONS — hvorfor Copilot-versjonen ikke er en bokstavelig kopi

Kilde: [`toreolavfurreness/claudecode` — `v2-agent-orchestrator`](https://github.com/toreolavfurreness/claudecode/tree/main/v2-agent-orchestrator)
(Claude Code). Dette dokumentet forklarer forskjellene, med **empiriske funn** (ikke
antakelser) fra en spike kjørt 2026-08-06 i GitHub Copilot CLI.

---

## 1. Spike-funn (målt, ikke antatt)

### 1a. Custom agent-registrering krever fortsatt fersk sesjon

Test: en ny agentfil (`.claude/agents/spike-probe.md`) ble lagt til i en allerede kjørende
sesjon. `extensions_reload` ble kjørt (rapporterte "0 extension(s) running — No extensions
found" — bekrefter at agenter og extensions/tools er to ULIKE registre). Deretter ble
`task`-verktøyet dispatchet med `agent_type: spike-probe`.

**Resultat:** `Unknown agent_type: spike-probe. Valid types are: explore, task,
general-purpose, ... lessons-writer, plan-reviewer, reviewer, ...` — agenten var ikke
tilgjengelig.

**Konklusjon:** Copilot CLI snapshotter agent-registeret ved sesjonsstart, akkurat som Claude
Code. Nye/endrede custom agent-filer krever en fersk sesjon for å bli synlige. Denne
begrensningen er IKKE unik for Claude Code.

**Konsekvens for designet:** se §2 — vi unngår dette problemet for de fire loop-rollene ved å
ikke registrere dem som navngitte custom agents i det hele tatt (se §3).

### 1b. In-session bakgrunnsagenter deler filsystem med foreldresesjonen

Test: en `task`-agent (`agent_type: general-purpose`, `mode: background`) fikk beskjed om å
opprette en markørfil i sitt working directory og rapportere `git rev-parse --show-toplevel`
+ branch-navn.

**Resultat:** agenten rapporterte nøyaktig samme sti og branch som foreldresesjonen
(`...\<foreldresesjonens-worktree>`, samme branch). Markørfilen dukket opp direkte i
foreldresesjonens arbeidskatalog.

**Konklusjon:** `task`-verktøyets bakgrunnsagenter kjører i EGET kontekstvindu, men SAMME
filsystem/worktree/branch som forelderen. Det finnes ingen ekvivalent til Claude Code sin
`isolation: worktree`-frontmatter-nøkkel på dette nivået.

### 1c. `create_session` gir ekte, verifisert worktree-isolasjon

Test: en barnesesjon ble opprettet med `create_session` (uten kickoff), deretter instruert
via `send_session_message` til å opprette en fil, committe den, og rapportere tilbake.

**Resultat:** `get_session` viste en HELT ANNEN sti (`...\toreolav2s-fantastic-succotash` vs.
foreldrens `...\toreolav2s-cuddly-goggles`) og egen branch. `get_changes_overview` bekreftet
et isolert commit (`spike: child session isolation probe`, 1 fil endret) usynlig fra
foreldresesjonens git-status. Sesjonen ble ryddet opp med `archive_session` etterpå.

**Konklusjon:** Copilot sin native "prosjekt-sesjon = egen worktree"-modell gir EKTE
filsystem-/git-isolasjon — sterkere garanti enn Claude Code sin `isolation: worktree`
(som er én attributt på en subagent-dispatch), men på et TYNGRE granularitetsnivå (hel sesjon,
ikke ett verktøykall).

---

## 2. Arkitektur-konsekvens: to isolasjonsnivåer, valgt per rolle

| Rolle | Muterer den kode/git-state? | Mekanisme | Begrunnelse |
|---|---|---|---|
| **planner** | Nei — leser + returnerer én ny planfil-tekst (koordinator skriver den) | In-session `task` (sync eller background) | Ingen delt-state-risiko: planneren returnerer tekst, koordinatoren (single-writer) skriver filen selv |
| **reviewer** | Nei — kun leser + returnerer JSON | In-session `task` | Rent lesende, ingen isolasjon nødvendig |
| **implementer** | Ja — skriver kode, committer, pusher, lager PR | Barnesesjon (`create_session`) | Krever ekte git-isolasjon; delt filsystem ville latt to samtidige implementer-dispatcher (på tvers av todos) kollidere |
| **code-reviewer** | Nei — leser PR-diff via `gh`, returnerer JSON | In-session `task` | Rent lesende (samme som kildens design — trenger ikke implementerens worktree) |
| **verifier** (pluggbar) | Ja — muterer bevisst i eget worktree for å bevise falsifiserbarhet, committer aldri | Barnesesjon (`create_session`) | Samme begrunnelse som implementer — mutasjon krever isolasjon |

**Avvik fra kilden:** planneren skriver IKKE selv til `tasks/plans/*.md` (slik den gjør i
Claude Code-versjonen). I Copilot-versjonen returnerer planneren plan-teksten som en del av
JSON-rapporten, og koordinatoren (eneste skriver til delt state) skriver filen. Dette unngår
å måtte gi planneren skrivetilgang/isolasjon den ellers ikke trenger, og er en STRENGERE
single-writer-disiplin enn kilden (som allerede sier "planneren skriver kun sin egen planfil,
aldri todo-frontmatter" — vi strammer inn ytterligere fordi vi mangler automatisk
worktree-isolasjon for lesende roller).

---

## 3. Arkitektur-konsekvens: ingen navngitte custom agents for loop-rollene

Siden §1a viser at nye/endrede agent-filer krever restart — akkurat den fellen kildens
`/setup` + "start fersk sesjon"-steg eksisterer for å håndtere — velger Copilot-versjonen en
ANNEN mekanisme som unngår problemet helt for planner/reviewer/implementer/code-reviewer:

- Rolle-instruksjonene ligger som vanlige tekstfiler i `templates/roles/*.md` (med
  `{{TOKEN}}`-plassholdere, som kilden).
- Koordinatoren (selve loop-sesjonen) leser `loop.config.yaml` OG relevant `templates/roles/*.md`
  **ved hver dispatch**, gjør tekstsubstitusjon i minnet, og sender resultatet som `prompt` til
  `task`/`create_session`. Ingenting "kompileres" til disk. Ingen `/setup`-steg. Ingen
  "GENERERT — ikke rediger"-filduplikering. Ingen restart nødvendig for å endre en rolle —
  neste dispatch bruker automatisk den oppdaterte teksten.
- Dette fjerner HELE klassen av feil kilden dokumenterer under "Herdinger fra live-drift":
  `display`-drift, `SEED_ONLY`-nullstilling av genererte filer, "agent-type not found" rett
  etter `/setup`. De problemene oppstår kun fordi Claude Code krever statiske,
  forhåndsregistrerte agent-filer — Copilot sitt `task`-verktøy tar prompt+model+effort som
  rene kall-parametre, så koordinatoren KAN gjøre substitusjonen ved kjøretid uten å bryte
  "ren mekanisme, ingen runtime-config-lesing av sikkerhetskritiske verdier"-prinsippet:
  det er fortsatt kun ÉN rolle (koordinatoren) som leser config, og substitusjonen skjer
  deterministisk (samme streng-erstatning som kildens skript) — bare i minnet i stedet for til
  disk.
- **Unntak — statiske prosjektfiler:** githooks, CI-workflow og `tasks/`-README-ene er IKKE
  agent-prompter — de er ekte prosjektfiler som må eksistere med riktige verdier (branch-navn
  osv.) uavhengig av noen kjørende sesjon. Disse rendres FORTSATT én gang til disk av et lite
  oppsett-skript (se `README.md` §Oppsett) — akkurat som kildens `/setup`, men med et MYE
  mindre virkefelt (kun scaffolding, ikke agent-/kommando-filer).
- `run-loop`/`todo-finish-worker`/`loop-health-check` — selve koordinator-kommandoene — MÅ
  fortsatt eksistere som filer under `.claude/commands/` (bekreftet: Copilot CLI eksponerer
  disse som kallbare "skills" med samme navn som filnavnet, jf. at `todo-plan`/`todo-execute`
  m.fl. allerede er synlige skills i dette prosjektet via de eksisterende `.claude/commands/`-
  filene). Disse KOPIERES én gang inn i prosjektet (samme som kildens prereq-stillas) og
  krever i så måte samme "fersk sesjon etter kopiering"-forbehold som kilden — men dette er et
  engangs-oppsett, ikke noe som gjentas per config-endring.

---

## 4. Modell/effort: runtime-parameter i stedet for kompilert frontmatter

Kildens begrunnelse for kompilerings-tvang er at Claude Code leser `model:`/`effort:` fra
agent-frontmatter **ved sesjonsstart**. Copilot sitt `task`-verktøy godtar derimot `model` og
`reasoning_effort` som **parametre på selve kallet** (bekreftet i verktøyskjemaet — se
`task`-verktøyets `model`/`reasoning_effort`-felter). Koordinatoren leser dermed
`loop.config.yaml` én gang ved sesjonsstart og bruker verdiene direkte som dispatch-parametre
— ingen kompilering, ingen tokens i separate agentfiler nødvendig for DETTE formålet.
`create_session`s `kickoff.model`/`kickoff.reasoning_effort` gir samme mulighet for
barnesesjon-roller (implementer, verifier).

---

## 5. Hva som IKKE er verifisert (usikkerhet som gjenstår)

- **`.claude/agents/`-konvensjonens generalitet.** Bevist å virke i DETTE prosjektet
  (pp-initiativkatalogen har allerede `reviewer`/`plan-reviewer`/`lessons-writer` registrert
  slik), men ikke testet i et helt ferskt/annet prosjekt uten forhistorie. Malen antar
  konvensjonen er generell (siden den også reflekterer Claude Code-konvensjonen 1:1), men et
  nytt prosjekt bør bekrefte dette i egen spike før man stoler fullt på det — spesielt siden vi
  uansett IKKE bruker `.claude/agents/` for loop-rollene (se §3), kun for `.claude/commands/`
  (skills). Bekreft at kommando-filene faktisk blir synlige som skills i et helt nytt prosjekt
  før produksjonsbruk.
- **Superpowers-ekvivalente skills / Playwright MCP** finnes i DETTE miljøet
  (`systematic-debugging`, `verification-before-completion`, `playwright-browser_*`), men er
  ikke garantert i ethvert Copilot CLI-oppsett — malen degraderer gracefully (samme mønster
  som kilden) i stedet for å anta tilstedeværelse.
- **Kostnad/overhead av barnesesjoner.** `create_session` er tyngre enn et subagent-kall
  (egen CLI-prosess, egen worktree-provisjonering). Spiken målte ikke nøyaktig tidsbruk, kun
  at flyten fungerer funksjonelt. Følg med på dette i `run-log.md` under reell bruk (se
  effektivitets-snapshot-feltet i helsesjekken).
