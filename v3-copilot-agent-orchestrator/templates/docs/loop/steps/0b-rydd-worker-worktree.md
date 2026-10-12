<!--
  GENERERT av /setup fra loop.config.yaml — IKKE rediger her.
  Endre loop.config.yaml og kjør /setup på nytt.
-->

# 0b. Rydd en worker-worktree (gjenbrukbar prosedyre)

→ Kjerne: `coordinator-runbook.md` § 0b · Begrunnelser: `runbook-hvorfor.md` § 0b

Kalles fra §3, §4, §5, §5b og §5c — ALDRI av en worker selv (R6: en worker fjerner aldri en
worktree og sletter aldri en branch; for read-only-rollene fanger `scripts/readonly-check.sh` et
brudd, se «Worktree per dispatch» under).

## Worktree per dispatch (gjelder §3, §4, §5, §5b, §5c og §5d)

En `task`-subagent deler filsystem og arbeidskatalog med koordinatoren. Isolasjonen lages derfor av
koordinatoren selv, FØR hver dispatch, med `scripts/bootstrap-worktree.sh`. Stegfilene peker hit i
stedet for å gjenta prosedyren.

1. **Pre-snapshot FØRST** (vakt 5 under): `git worktree list --porcelain > "<pre_snapshot>"`,
   umiddelbart før bootstrap-kallet i punkt 2. Snapshotet tas altså FØR treet finnes, slik at
   vakt 5 («stien er fraværende i snapshotet») beviser at treet ble laget for nettopp denne
   dispatchen.
2. **Lag treet:**
   ```bash
   WT=$(bash scripts/bootstrap-worktree.sh <todo-nr> <etikett>)
   ```
   Skriptet lager `.loop-worktrees/<etikett>-<todo-nr>` på branchen `loop/<etikett>-<todo-nr>` fra
   `origin/{{BASE_BRANCH}}` og skriver BARE stien til stdout. Noter stien som `WORKTREE`.
   **Finnes treet allerede, gjenbruker skriptet det** — derfor etikett-regelen i punkt 3. Exit ≠ 0 eller
   ingen sti ⇒ INGEN dispatch (en worker uten eget tre ville jobbet i hovedsjekkuten); rett årsaken
   og kjør punkt 1–2 på nytt.
3. **Etikett — én sti per dispatch-forsøk:** `planner-r<runde>`, `plan-reviewer-r<runde>`,
   `code-reviewer-r<runde>`, `rca-r<runde>` (rotårsaksanalysen i §5b), med `-f<n>` (n = 2, 3, …)
   for hver re-dispatch i samme runde (canary-/bevis-mismatch, kontrakt-vakt-avvisning). Implementeren
   får `implementer` ved §5-dispatchen, og fix-mode-rundene i §5b GJENBRUKER det treet (se §5b,
   «Fix-mode-dispatch-mal»). En sti gjenbrukes aldri av en annen rolle eller en senere todo.
   Siden skriptet gjenbruker en eksisterende sti, er en unik etikett det ENESTE som hindrer at et
   nytt forsøk havner i en forkastet workers tre: før bootstrap-kallet skal stien
   `.loop-worktrees/<etikett>-<todo-nr>` IKKE stå i pre-snapshotet (unntak: fix-runder i
   implementer-treet). UVERIFISERT: at skriptet godtar etiketter med runde-/forsøkssuffiks.
4. **Noter før dispatch:** `git -C "<WORKTREE>" branch --show-current` → `<bootstrap_branch>`
   (normalt `loop/<etikett>-<todo-nr>`; punkt 7 (b) under) og, RETT FØR dispatch,
   `git -C "<WORKTREE>" rev-parse HEAD` → `<base_sha>` (read-only-sjekken i punkt 6). For
   kode-revieweren settes treet først på PR-hodet, se §5b «Review-dispatch».
5. **Dispatch** med `WORKTREE: <WORKTREE>` som første linje i prompten. Workerens Steg 0 er
   `cd "<WORKTREE>"` og en sjekk av at `git rev-parse --show-toplevel` er lik WORKTREE; alle
   kommandoer og fil-endringer skjer der. Scout får ingen egen worktree: den kjører i
   oppdragsgiverens WORKTREE, som oppdragsgiveren gir i scout-prompten. Probe-dispatcher
   (`{"ok": true}`) får ingen WORKTREE.
6. **Etter rapporten:** `evidence.toplevel` MÅ være lik WORKTREE, tegn for tegn. Avvik ⇒ rapporten
   forkastes (re-dispatch med ny etikett eller eskalér). **Read-only-roller** (plan-reviewer,
   code-reviewer, rotårsaksanalysen) sjekkes i tillegg, FØR rapporten leses:
   ```bash
   bash scripts/readonly-check.sh <WORKTREE> <base_sha>
   ```
   Skriptet feiler hvis `git status --porcelain` i treet ikke er tom eller HEAD har flyttet seg fra
   `<base_sha>`: exit 0 = OK, 1 = brudd, 2 = kan ikke måles (behandles som brudd). Exit ≠ 0 ⇒
   rapporten forkastes og hendelsen er nivå A (⚠️ STOPP, release claim,
   eskalér med skriptets utskrift). Treet ryddes IKKE: §0b gir da `dirty` og beholder det som bevis.
   Read-only-rollene har heller ikke `edit` i `tools` (Copilot håndhever verktøylista); sjekken
   fanger skriving via shell.

**Inngangsdata:**
- `<wt_path>` — ALLTID en eksakt sti: WORKTREE-stien koordinatoren selv fikk fra bootstrap-skriptet
  for dispatchen, bekreftet av workerens `evidence.toplevel` (punkt 6 over). Aldri et mønster,
  aldri et sveip.
- `<rolle>` ∈ {`planner`, `plan-reviewer`, `code-reviewer`, `implementer`}.
- `<pre_snapshot>` (OBLIGATORISK) — kanonisk form: `<pre_snapshot>` =
  `<scratch>/wt-pre-<seksjon>-<rolle>-<runde>.txt`, skrevet av koordinatoren umiddelbart FØR
  bootstrap-kallet for dispatchen (punkt 1 over). **Generell regel: `<pre_snapshot>` er ALLTID fila
  som ble skrevet umiddelbart før bootstrap-kallet for DEN DISPATCHEN som fikk `<wt_path>` — aldri
  en fil navngitt etter en annen dispatch**, selv når to dispatch-steder gjenbruker samme
  filnavns-MØNSTER (se §5b og §5c for konkrete kallsteder der dette avviker fra filnavnet man skulle
  tro). **Én snapshot-fil per dispatch — gjenbruk ALDRI én fil på tvers av dispatches:** runde 2s
  snapshot inneholder runde 1s worktree, og runde 1s sti ville da blitt avvist som `preexisting`.
  Akkumulerte sti-lister bærer derfor PAR (sti, snapshot-fil), ikke bare stier.
- `<bootstrap_branch>` — branchen bootstrap-skriptet opprettet for treet (punkt 4 over).
- `<forventet_fil>` (valgfritt) — planfilen §0b skal kreve finnes på `origin/{{BASE_BRANCH}}` før
  rydding (kun planner-rollen).
- `<branch_kryss_sjekk>` (valgfritt) — branch-navnet ferdig-rapporten oppga, som ren kryss-sjekk.

**Rekkefølge:**

1. **R1s fem vakter** (mot returnert rapport — aldri sveip):
   - **Vakt 1:** `<wt_path>` er den EKSAKTE WORKTREE-stien du laget for dispatchen, og
     rapportens `evidence.toplevel` er lik den.
   - **Vakt 2:** `<wt_path>` MÅ være medlem av `git worktree list --porcelain` NÅ (dynamisk
     oppslag, kjørt fail-safe — se punkt 3).
   - **Vakt 3:** `<wt_path>` MÅ inneholde `.loop-worktrees/`.
   - **Vakt 4:** `<wt_path>` MÅ IKKE være din egen `git rev-parse --show-toplevel` (N1: ikke alle
     worktrees under `.loop-worktrees/` er worker-agenter — koordinator-/interaktive
     sesjons-worktrees ligger der også).
   - **Vakt 5 — stien MÅ VÆRE FRAVÆRENDE i `<pre_snapshot>`.** Kjør FØRST en
     **plausibilitetssjekk** (lukker en fail-open-feilmodus på et tomt/avkortet snapshot):
     `grep -c '^worktree ' <pre_snapshot>` MÅ gi `≥ 1`. Gir den `0` — snapshotet er tomt eller
     avkortet, f.eks. skrevet av en kommando som feilet etter at redirect-target-fila allerede var
     opprettet — ⇒ **ADVARSEL (`snapshot-missing`), INGEN rydding**: en tom fil ville ellers gitt
     `grep -cFx` = `0` for ENHVER oppgitt sti og dermed stille latt vakt 5 «passere» uansett —
     samme fail-open-klasse som BLOKKERENDE-2, på et annet artefakt. Består plausibilitetssjekken,
     kjør selve predikatet, ordrett form: `grep -cFx 'worktree <wt_path>' <pre_snapshot>` MÅ gi
     `0`. Gir den `≥ 1`, fantes worktreen FØR vi laget den for dispatchen ⇒ den er ikke vår ⇒ **ADVARSEL
     (`preexisting`), INGEN rydding**. Mangler eller er `<pre_snapshot>` uleselig ⇒ **ADVARSEL
     (`snapshot-missing`), INGEN rydding**. `-F` og `-x` er obligatoriske (uten `-x` matcher
     `planner-r1-4` linja for `planner-r1-41`). **Snapshotet leses ALDRI som kilde til stier** — det
     er et predikat over én oppgitt sti, aldri en iterasjonskilde. Det er forskjellen fra det
     forkastede sveipet (r2 BLOKK-4).
   - **Vakt 5b (kun `<rolle> = planner`):** `cp`-kilden i Steg 2 (a) ER bindingen mellom rapport og
     sti — fila vi kopierte kom fra nøyaktig `<wt_path>`. Fantes ikke kildefila, eller feilet
     `cmp -s`, ⇒ **ADVARSEL (`handoff-mismatch`), INGEN rydding**.

2. **Idempotens, kvalifisert:** er stien IKKE en registrert worktree (vakt 2 feiler), splittes
   utfallet i to grener på sesjonens allerede-ryddet-sett:
   - **(a)** står stien i settet ⇒ stien er **allerede ryddet** — stille no-op (ingen handling,
     ingen ADVARSEL, ingen telling). Normal tilstand ved dedupliserte kall, ved §3/§5c-overlappet,
     ved §4s akkumulering og ved en re-kjørt §6.
   - **(b)** står den ikke i settet ⇒ **ADVARSEL (`unknown-path`), ingen handling** — mulig
     fabrikert eller fremmed-slettet sti.
   Begge grener er ikke-destruktive; forskjellen er utelukkende signal.

3. **Fail-safe på kommandofeil:** alle tre oppslagene (`worktree list`, `locked`, `status`) kjøres
   **uten `2>/dev/null`**, stdout skrives til fil, og **exit-koden sjekkes separat**. `worktree
   list` og `locked`-oppslaget er repo-globale og kjøres uten `-C` (de leser hele repoets
   worktree-register, ikke én enkelt sti). `status` er den ENESTE av de tre som må navngi treet
   den inspiserer — se punkt 5 for ordrett form (`git -C <wt_path> status …`); uten `-C` kjører
   status i koordinatorens EGEN cwd og allowlisten blir en stille no-op.
   **exit ≠ 0 ⇒ ADVARSEL, INGEN rydding** — tom output er ALDRI det samme som ren worktree.
   **Dokumentert carve-out for `grep -c`:** `grep -c` returnerer exit `1` når tellingen er `0`, og
   `0` er den GODKJENTE tilstanden i vakt 5 og i idempotens-settet. For `grep -c` er derfor
   **exit `0` og `1` BEGGE gyldige** (0 = treff, 1 = ingen treff); **exit `≥ 2` er `cmd-error` ⇒
   ADVARSEL**. Uten carve-outen ville vakt 5 alltid fyrt rødt.

4. **`locked`-sjekk** (dynamisk, samme fail-safe-regel som punkt 3).

5. **Rolle-bevisst allowlist** på `git -C <wt_path> status --porcelain -uall` (ordrett form —
   `<wt_path>` MÅ oppgis eksplisitt, jf. punkt 3): **0 ELLER 1 linje**. 0 linjer ⇒
   rydd (betinget av exit-kode `0` fra selve status-kommandoen, punkt 3). 1 linje ⇒ statusfelt
   (tegn 1–2) ∈ {`??`, ` M`, `M `, `MM`, `AM`, `A `} OG sti (tegn 4–) strengt lik forventet
   planfil — **denne 1-linje-grenen gjelder KUN `<rolle> = planner` MED `<forventet_fil>`
   oppgitt.** `implementer` forventer TOM output (0 linjer) uansett, på linje med
   `plan-reviewer` og `code-reviewer` («skriver ingenting») — ikke-tom ⇒ ADVARSEL (`dirty`),
   ingen sletting. Er `<rolle> = planner` men `<forventet_fil>` UTELATT, gjelder samme
   nulltoleranse: enhver ikke-tom output ⇒ ADVARSEL (`dirty`).

6. **Artefakt-gate når `<forventet_fil>` er oppgitt:**
   `git cat-file -e origin/{{BASE_BRANCH}}:<forventet_fil>` exit 0 OG innholdslikhet
   (`git show origin/{{BASE_BRANCH}}:<forventet_fil> > <scratch>/artifact-gate-<basename(wt_path)>.txt`,
   deretter `diff <scratch>/artifact-gate-<basename(wt_path)>.txt <forventet_fil>` exit 0) — utledet
   av `<wt_path>`, som allerede er del av §0bs Inngangsdata (ingen ny, udeklarert `<runde>`-parameter
   trengs). Samme `<scratch>`-plassholder som pre-snapshotene, ALDRI en repo-relativ fil (den ville
   blitt en usporet fil i koordinatorens eget tre og felt neste §0-synk). Ikke oppfylt ⇒ ADVARSEL
   (`artifact-missing`), INGEN rydding. **Utelates argumentet, hoppes gaten over** — den ene
   lovlige bruken er drop-B-grenene i §5c, der planfila er bevisst fjernet med `git rm`.

7. **Rekkefølge (ordinalregel, R21): sti→branch-oppslaget kjøres FØRST, og resultatet LAGRES.**
   Deretter, og først da, kjøres `git worktree remove <wt_path> --force`. Etter exit 0 fra denne
   kjøres `git branch -d` — for de LAGREDE verdiene, aldri fra et nytt oppslag (stien er da borte
   fra `git worktree list`, og et nytt oppslag ville gitt tom branch og stille droppet
   PR-branch-slettingen — en funksjonell regresjon mot dagens §6-blokk). To branches slettes med
   `git branch -d`, begge KUN etter exit 0 fra `remove`:
   (a) den **lagrede** verdien fra `awk`-oppslaget (sti → branch, samme streng-match-form som
   dagens §6-blokk), og
   (b) den **noterte** `<bootstrap_branch>` (branchen bootstrap-skriptet lagde for treet, notert
   FØR dispatch) — men KUN hvis den er ulik (a) OG finnes i `git branch --list '<bootstrap_branch>'`.
   Den blir forlatt når workeren byttet til sin egen branch (K3).
   **Aldri `-D`.** Legg samtidig `<wt_path>` inn i sesjonens allerede-ryddet-sett (lista
   koordinatoren holder i kontekst over stier §0b har ryddet i denne sesjonen) — det er DEN lista
   punkt 2 (a) slår opp i, ikke akkumulerings-/dedup-lista fra §3/§4/§5/§5b/§5c.

8. **Exit-tilstander skilles:** «branchen finnes ikke» ⇒ normalt, ingen ADVARSEL, telles ikke.
   «`-d` nektet på en EKSISTERENDE branch» ⇒ telles i «bærer commits»-bøtta og rapporteres «krever
   manuell vurdering» **med branch-navn OG den nå-slettede stien**.

9. Er `<branch_kryss_sjekk>` oppgitt og ≠ branchen oppslaget fant: ADVARSEL (`branch-mismatch`),
   ikke slett.

10. **ADVARSEL-regelen:** feilet/avvist rydding går til stderr, telles i rundens `wtwarn`, og
    rapporteres i koordinatorens runde-rapport — **aldri et pausepunkt**. Årsaken oppgis fra det
    **engelske enumet**: `dirty` | `locked` | `artifact-missing` | `cmd-error` |
    `branch-not-deleted` | `preexisting` | `snapshot-missing` | `unknown-path` |
    `handoff-mismatch` | `branch-mismatch`. Ingen fritekst.

11. `$2`, `core.quotePath` og awk-reserverte navn: branch-navn kan inneholde `/` — streng-match
    (ikke split på `/`) håndterer det korrekt; ikke-ASCII-filnavn i `git status --porcelain` kan
    bli quotet av `core.quotePath=true` — sjekk denne innstillingen hvis allowlisten uventet ikke
    matcher.
