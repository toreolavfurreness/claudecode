# PORTING-DECISIONS — hvorfor kitet er bygget slik det er på GitHub Copilot

Dette dokumentet forklarer valgene som følger av plattformen: hva Copilot-harnessen gir, hva den
ikke gir, og hvordan kitet fyller hullene. Hvert valg viser til kilden det bygger på.
Plattformfaktaene er hentet fra GitHub Copilot- og VS Code-dokumentasjonen per oktober 2026.
Punktene merket **UVERIFISERT** er ikke målt ennå og skal sjekkes i den første valideringskjøringen
(se §9).

Kitet kjøres i **VS Code med Session Target = Copilot** (Copilot-harnessen på Agent Host). Den
harnessen bruker samme runtime som Copilot CLI og Copilot SDK, så alt under gjelder også for
Copilot CLI. Den eldre **Local**-harnessen i VS Code støttes ikke: der kan subagenter ikke få
oppfølgingsmeldinger, de kan ikke nestes uten egen innstilling, og prompt-filer og hooks oppfører seg
annerledes.

---

## 1. Rolleagenter som Copilot custom agents

**Plattform:** Copilot leser custom agents fra `.github/agents/*.agent.md`. Frontmatter har `name`,
`description`, `tools`, `model` (streng eller prioritert liste), `user-invocable`,
`disable-model-invocation` og `include-custom-instructions`. Agent-registeret leses ved sesjonsstart:
en ny eller endret agentfil krever en ny sesjon (`Unknown agent_type`).

**Valg:**
- Workerne har `user-invocable: false`. De dispatches av koordinatoren og skal ikke ligge i
  agentvelgeren.
- Workerne har `include-custom-instructions: true`. Uten den får en custom agent som kjøres som
  subagent **ikke** `AGENTS.md`, og charterne forutsetter at den er lest.
- `docs/loop-rules.md` leses eksplisitt i hver workers Steg 0. `AGENTS.md` lenker bare til den, og en
  lenke blir ikke lastet automatisk.
- `/run-loop` prober agentene med et trivielt `task`-kall før loopen starter, og ber om ny sesjon
  ved `Unknown agent_type`.

Kilder: `docs.github.com/copilot/reference/custom-agents-configuration`,
`docs.github.com/copilot/reference/copilot-cli-reference/cli-command-reference` (Repository custom
instructions for subagents).

## 2. Worktree per worker lages av koordinatoren

**Plattform:** Copilot har ingen innstilling som gir en subagent sin egen git-worktree. En
`task`-subagent har eget kontekstvindu, men deler filsystem, arbeidskatalog og branch med
koordinatoren. Worktree finnes bare per *sesjon* (`--worktree`, `/fork worktree`, VS Codes
«New Worktree»).

**Valg:** koordinatoren lager worktreen selv, rett før hver dispatch:

```bash
WT=$(bash scripts/bootstrap-worktree.sh <todo-nr> <rolle>)   # .loop-worktrees/<rolle>-<nr>
```

Stien sendes i prompten (`WORKTREE: <sti>`). Workerens Steg 0 går dit og verifiserer med
`git rev-parse --show-toplevel` før den gjør noe annet. Alle kommandoer og filendringer skjer der.
Opprydding gjøres av `tasks/worktree-sweep.sh` og `worktree-landed.sh`, som før.

**Hvorfor ikke en egen Copilot-sesjon per worker:** det gir sterkere isolasjon, men verktøyene for å
starte og styre andre sesjoner er ikke tilgjengelige i alle Copilot-overflater. Et skript med
`git worktree add` virker likt i VS Code, i CLI-en og i CI.

**Begrensning:** isolasjonen er en konvensjon workeren følger, ikke en grense plattformen håndhever.
`worktree-landed.sh` og `readonly-check.sh` (§3) fanger avvik etterpå.

## 3. Read-only håndheves av verktøylisten og kontrolleres etterpå

**Plattform:** en `preToolUse`-hook får `toolName` og `toolArgs`, men ikke hvilken agent eller
subagent som kaller verktøyet. En hook kan derfor ikke skille revieweren fra implementeren.

**Valg, i to lag:**
1. Read-only-rollene (reviewer, code-reviewer, scout, tech-review-agentene) har ikke `edit` i
   `tools`. Copilot håndhever lista: et verktøy som ikke står der, finnes ikke for agenten.
2. Shell-tilgang (`execute`) trengs for `git` og `gh`, og kan i prinsippet skrive. Etter hver
   read-only-dispatch kjører koordinatoren `bash scripts/readonly-check.sh <WORKTREE> <base-sha>`.
   Er arbeidstreet ikke rent, eller har HEAD flyttet seg, forkastes rapporten og det blir nivå A.

Det er en kontroll etter handlingen, ikke en sperre før. Fordi hver read-only-rolle har sin egen
worktree, kan en skriving ikke treffe koordinatorens sjekkout eller en annen workers tre.

## 4. Vakter som Copilot-hooks

**Plattform:** hooks konfigureres i `.github/hooks/*.json` (versjon 1) med hendelsene `sessionStart`,
`preToolUse`, `postToolUse`, `preCompact`, `subagentStart`, `subagentStop`, `agentStop` og
`sessionEnd`. En `preToolUse`-hook blokkerer med `{"permissionDecision":"deny", …}` på stdout.
Krasj eller exit 2 blokkerer også, men timeout slipper kallet gjennom.

**Valg:**
- `/setup` genererer `.github/hooks/loop-guards.json` fra `hooks.*` i config. Fila er kit-eid og
  overskrives. Prosjektets egne hooks ligger i andre filer i samme mappe og blir aldri rørt.
- `guard-main-merge.sh` (`preToolUse` på `bash`) stopper push, PR og merge mot prod-branchen.
- `guard-fix-round-model.sh` (`preToolUse` på `task`) krever at implementer-dispatchen har `model`
  fra config, og den dype modellen fra fix-runde 3.
- `typecheck-on-edit.sh` (`postToolUse`) og `session-start-lint.sh` (`sessionStart`) er valgfrie
  komfort-hooks.
- `precompact-checkpoint.sh` (`preCompact`) logger om koordinatorens sjekkpunkt var ferskt.
- Skriptene finner prosjektroten med `git rev-parse --show-toplevel` (eller `$LOOP_PROJECT_DIR` hvis
  satt) og tåler at `toolArgs` kommer både som JSON-streng og som objekt.

**Ingen hook etter komprimering:** Copilot har ingen `sessionStart`-kilde for «etter komprimering»,
og `preCompact` kan bare varsle. Sjekkpunktet legges derfor ikke inn i konteksten automatisk.
Regelen i steg 0c er at koordinatoren leser sjekkpunktfila når den gjenopptar arbeid eller er usikker
på tilstanden, og før hvert steg.

Kilde: `docs.github.com/copilot/reference/hooks-reference`.

## 5. Tilbakesending av en worker er en fersk dispatch

**Plattform:** `write_agent` sender en melding til en agent *som fortsatt kjører*
(bakgrunnsmodus). Dokumentasjonen sier ikke at en ferdig subagent kan vekkes igjen.

**Valg:** standarden er en **fersk dispatch** av samme rolle. Prompten har med forrige rapport,
funnene og samme `WORKTREE`, så arbeidet fortsetter i samme tre. `write_agent` brukes bare til en
bakgrunnsworker som ennå ikke har levert. Det koster litt mer kontekst, men tilstanden ligger i
worktreen og rapporten, ikke i en samtale som kan forsvinne.

## 6. Modeller: lister, plassholdere og uavhengig familie

**Plattform:** `model` i en custom agent kan være en prioritert liste. Copilot prøver neste modell
hvis den første ikke er tilgjengelig. `task`-kallet tar `model` og valgfritt `reasoning_effort`.
Copilot gir tilgang til modeller fra flere leverandører, og hvilke som er tilgjengelige, avhenger av
organisasjonens policy.

**Valg:**
- `loop.config.yaml` beskriver hva rollen krever (dyp / kode / billig), ikke et merke. Eksempelfila har
  plassholdere, og `/setup` stopper hvis en står igjen.
- Hver rolle tar en liste. Settes en reserve fra en annen leverandør, overlever loopen at en policy
  slår av én modell.
- Anbefalingen er at reviewer og code-reviewer bruker en annen modellfamilie enn planner og
  implementer, så den uavhengige reviewen ikke deler blindsoner med arbeidet den gransker.
- `*_effort` er valgfri og sendes som `reasoning_effort` i `task`-kallet.

## 7. Skills i stedet for slash-kommandoer

**Plattform:** Copilot-harnessen laster ikke `.prompt.md`-filer. Skills i `.github/skills/<navn>/SKILL.md`
vises som `/<navn>` i chatten. `disable-model-invocation: true` gjør at de bare kjøres når brukeren
ber om det.

**Valg:** alle kommandoene er skills med `disable-model-invocation: true`, slik at loopen aldri
starter fordi modellen syntes det passet. `/setup` er også en skill.

## 8. Kostnad i AI credits

**Plattform:** Copilot fakturerer i AI credits. Hendelsen `assistant.usage` (modell, tokens,
multiplikator) sendes live, men lagres normalt ikke i sesjonsloggen
(`~/.copilot/session-state/<id>/events.jsonl`). `/usage` viser totalene for sesjonen.

**Valg:** `tasks/measure-cost.py` summerer `assistant.usage` fra `events.jsonl` når hendelsene finnes,
og tar ellers imot manuelle tall fra `/usage` (`--credits`). Mangler begge, er svaret `IKKE MÅLT`,
aldri 0. Kostnadsbremsen bruker AI credits. Uten tall gjelder den eksisterende regelen for manglende
data: nivå A.

## 9. Må verifiseres i første kjøring

Punktene under er ikke målt ennå. De står også som `UVERIFISERT:` der de brukes i kitet. Skriv
resultatet i valideringsnotatet (ARCHITECTURE §6, steg 6), og rett kitet der virkeligheten avviker.

**Dispatch og agenter**
1. At `task` i VS Code-harnessen tar imot `model` og `reasoning_effort` slik stegfilene sender dem, og
   at `guard-fix-round-model.sh` ser feltene i `toolArgs`. Kitet sender bare den første modellen i lista.
2. At subagent-verktøyet heter `task` i payloaden. Heter det noe annet, er modellvakta stille av.
3. At en custom agent som kjøres som subagent kan kalle en annen custom agent med `agent`-verktøyet
   (code-reviewer → tech-review-agenter, planner/implementer → scout). Hvis ikke: sett
   `scout.enabled: false` og la koordinatoren dispatche tech-review-agentene i §5b.
4. Om flere `task`-kall i samme tur kjører parallelt (§5c, §5d og lensene i §5b).

**Worktree og shell**
5. Om shell-katalogen beholdes mellom kall. Agentene antar at den ikke gjør det og starter hvert kall
   med `cd "<WORKTREE>" &&`.
6. At ingen worker har endret filer utenfor sin `WORKTREE`: `git status` i hovedsjekkouten er ren etter
   runden.

**Hooks**
7. At VS Code laster `.github/hooks/*.json` og `.github/skills/*/SKILL.md` uten ekstra innstillinger.
8. Om `preToolUse`-hooks fyrer for verktøykall som subagenter gjør (§6 ber om en engangstest med en
   kastbar worker).
9. Verktøynavnene i payloaden: vaktene godtar `bash` og `run_in_terminal` for shell, og `edit`, `create`,
   `apply_patch`, `str_replace_editor` og VS Code-navnene for redigering. Feltnavnet for filstien
   (`path`, `file_path` eller `filePath`) og patch-formatet til `apply_patch` er antatt.
10. At `additionalContext` fra `sessionStart` og `postToolUse` faktisk vises for agenten.

**Kostnad**
11. Om `events.jsonl` inneholder `assistant.usage` på deres versjon, og om summen av `cost` er lik AI
    credits i `/usage`. `python3 tasks/measure-cost.py --calibrate --credits <n>` er beviset.
12. Om VS Code-sesjoner skrives til `~/.copilot/session-state`, om `COPILOT_SESSION_ID` er satt i
    shell-kall, og om koordinatoren kan lese AI credits-totalen selv (`/usage` er en brukerkommando).
    Kan den ikke det, blir per-todo-kost `IKKE MÅLT`, og kostnadsbremsen faller til nivå A.
