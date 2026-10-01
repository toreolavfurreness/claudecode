<!--
  GENERERT av /setup fra loop.config.yaml — IKKE rediger her.
  Endre loop.config.yaml og kjør /setup på nytt.
-->

# Koordinator-runbook (fase 0, live-sesjon)

Du er koordinatoren. Du er eneste skriver til delt state. Workers gjør tungt arbeid i isolerte worktrees og returnerer rapporter (`report-schema.md`).

> ⚠️ **Forutsetning:** koordinatoren MÅ kjøre i en sesjon som ble startet ETTER at `.claude/agents/{{PROJECT_NAME}}-*.md` finnes på disk. Claude Code snapshotter agent-registeret ved sesjonsstart — nyopprettede custom agenter er ikke tilgjengelige i en allerede kjørende sesjon. Verifiser med to trivielle probe-dispatcher (`subagent_type: {{PROJECT_NAME}}-planner`, prompt: «Svar kun: {"ok": true}. Ikke les filer.» — ordrett identisk med preflight-proben i `run-loop.md`, som utløser planner-charterets probe-modus-unntak; og `subagent_type: {{PROJECT_NAME}}-code-reviewer`, prompt: «Svar kun: {"ok": true}. Ikke synk, ikke les filer.» — dekker §5b sitt register-oppslag for hele sesjonen, se §5b) før du starter en runde; «Agent type not found» betyr at du må starte en fersk sesjon. **Sesjonsstart-epoch (TODO 250B):** rett etter probe-dispatchene kjører du `date -u +%s` ÉN gang og noterer tallet som sesjonens `T_start`; umiddelbart etter kjører du i tillegg de tre kommandoene i «Kontrakt-vakt (TODO 250B)»s session-predikat (ledd (a)–(c)) og noterer resultatet HER — ikke først når §5b nås. `T_start` er ledd (b) i predikatet og re-måles ALDRI senere i sesjonen. Finnes ingen registrert `T_start`, er predikatet USANT og form A kjøres.

## Bevis-regel (global, jf. `report-schema.md`)

Enhver «bekreftet/verifisert X»-påstand i en worker-rapport MÅ følges av kommando + ordrett output. En prosa-bekreftelse UTEN kommando+output regnes som IKKE verifisert. Alle fire worker-chartere (planner, reviewer, implementer, code-reviewer) bærer nå denne regelen STRUKTURELT i egen «## Bevis»-seksjon — dispatch-promptene under (§3/§4/§5/§5b) holdes derfor bevisst MINIMALE og gjentar IKKE sitat-/anti-fab-instruksene: én kilde til bevis-kravet (charterne), ikke to. `evidence`-feltet i rapportene er en billig førstelinje-tripwire og erstatter ALDRI koordinatorens egen uavhengige sjekk (`git status`/`wc -l`/`gh pr view`/`gh pr diff`).

**Målt håndhevelse (2026-09-10).** Regelen over har eksistert hele tiden og er likevel brutt: median
dispatch-promptlengde gikk fra 1 676 tegn (uke 28) til 3 294 (uke 37), og over 72 dispatcher i uke
36–37 ga korteste tredjedel 54k subagent-tokens mot lengste tredjedels 176k — 3,2×. Konkret grense,
som er etterprøvbar i motsetning til ordet «minimale»: **review-funn siteres ALDRI inline i en
fix-/revisjons-dispatch.** Skriv rapporten til fil og pek på stien. Prompten skal bære oppdraget og
pekeren, ikke innholdet. Dette er ikke en ny regel — det er den gamle, gjort målbar.

## 0. Synk

```bash
git fetch origin {{BASE_BRANCH}} && git merge --ff-only origin/{{BASE_BRANCH}}
```
Speil-vennlig: fast-forwarder ekte `{{BASE_BRANCH}}` ELLER en sesjons-speil-branch (tip ==
`origin/{{BASE_BRANCH}}`, fordi `{{BASE_BRANCH}}` er utsjekket i et annet worktree) til
`origin/{{BASE_BRANCH}}`. En divergert branch (lokale commits utenfor delt state) feiler
høyt her — det er korrekt, ikke en regresjon. Working tree ikke ren → rapporter til
mennesket og stopp.

**Hook-aktivering (idempotent, ved sesjonsstart):** har prosjektet `.githooks/` fra
`scaffolding/` (pre-push, pre-commit-delt-checkout-vern), sett `core.hooksPath` — men overstyr
aldri en eksisterende verdi (den kan være satt bevisst):
```bash
[ -d .githooks ] && [ -z "$(git config --get core.hooksPath 2>/dev/null)" ] \
  && git config core.hooksPath .githooks && echo "core.hooksPath satt til .githooks"
```

## 0b. Rydd en worker-worktree (gjenbrukbar prosedyre)

Kalles fra §3, §4, §5, §5b og §5c — ALDRI av en worker selv (R6: workere kan ikke selv fjerne en
worktree eller slette en branch, worktree-vakten avviser dem).

**Inngangsdata:**
- `<wt_path>` — ALLTID en eksakt sti (worktreens absolutte rot fra en workers `evidence.toplevel`
  eller ferdig-rapportens `branch`-oppslag). Aldri et mønster, aldri et sveip.
- `<rolle>` ∈ {`planner`, `plan-reviewer`, `code-reviewer`, `implementer`}.
- `<pre_snapshot>` (OBLIGATORISK) — kanonisk form: `<pre_snapshot>` =
  `<scratch>/wt-pre-<seksjon>-<rolle>-<runde>.txt`, skrevet av koordinatoren umiddelbart FØR
  dispatchen (Steg 1b-regelen). **Generell regel: `<pre_snapshot>` er ALLTID fila som ble skrevet
  umiddelbart før DEN DISPATCHEN som skapte `<wt_path>` — aldri en fil navngitt etter en annen
  dispatch**, selv når to dispatch-steder gjenbruker samme filnavns-MØNSTER (se §5b og §5c for
  konkrete kallsteder der dette avviker fra filnavnet man skulle tro). **Én snapshot-fil per
  dispatch — gjenbruk ALDRI én fil på tvers av dispatches:** runde 2s snapshot inneholder runde 1s
  worktree, og runde 1s sti ville da blitt avvist som `preexisting`. Akkumulerte sti-lister bærer
  derfor PAR (sti, snapshot-fil), ikke bare stier.
- `<forventet_fil>` (valgfritt) — planfilen §0b skal kreve finnes på `origin/{{BASE_BRANCH}}` før
  rydding (kun planner-rollen).
- `<branch_kryss_sjekk>` (valgfritt) — branch-navnet ferdig-rapporten oppga, som ren kryss-sjekk.

**Rekkefølge:**

1. **R1s fem vakter** (mot returnert rapport — aldri sveip):
   - **Vakt 1:** `<wt_path>` er den EKSAKTE stien fra rapporten.
   - **Vakt 2:** `<wt_path>` MÅ være medlem av `git worktree list --porcelain` NÅ (dynamisk
     oppslag, kjørt fail-safe — se punkt 3).
   - **Vakt 3:** `<wt_path>` MÅ inneholde `.claude/worktrees/`.
   - **Vakt 4:** `<wt_path>` MÅ IKKE være din egen `git rev-parse --show-toplevel` (N1: ikke alle
     worktrees under `.claude/worktrees/` er worker-agenter — koordinator-/interaktive
     sesjons-worktrees ligger der også).
   - **Vakt 5 — stien MÅ VÆRE FRAVÆRENDE i `<pre_snapshot>`.** Kjør FØRST en
     **plausibilitetssjekk** (lukker en fail-open-feilmodus på et tomt/avkortet snapshot):
     `grep -c '^worktree ' <pre_snapshot>` MÅ gi `≥ 1`. Gir den `0` — snapshotet er tomt eller
     avkortet, f.eks. skrevet av en kommando som feilet etter at redirect-target-fila allerede var
     opprettet — ⇒ **ADVARSEL (`snapshot-missing`), INGEN rydding**: en tom fil ville ellers gitt
     `grep -cFx` = `0` for ENHVER oppgitt sti og dermed stille latt vakt 5 «passere» uansett —
     samme fail-open-klasse som BLOKKERENDE-2, på et annet artefakt. Består plausibilitetssjekken,
     kjør selve predikatet, ordrett form: `grep -cFx 'worktree <wt_path>' <pre_snapshot>` MÅ gi
     `0`. Gir den `≥ 1`, fantes worktreen FØR vi dispatchet ⇒ den er ikke vår ⇒ **ADVARSEL
     (`preexisting`), INGEN rydding**. Mangler eller er `<pre_snapshot>` uleselig ⇒ **ADVARSEL
     (`snapshot-missing`), INGEN rydding**. `-F` og `-x` er obligatoriske (uten `-x` matcher
     `agent-dead` linja for `agent-deadbeef`). **Snapshotet leses ALDRI som kilde til stier** — det
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
   (b) den **sti-utledede** `worktree-<basename(wt_path)>` — men KUN hvis basename matcher
   `^agent-[0-9a-f]+$` OG branchen finnes i `git branch --list 'worktree-agent-*'`.
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

## 1. Kø-utvelgelse (med ekte deps-gating)

Kjør dette python-skriptet — det resolver `deps`, ekskluderer claimed/brainstorm, og sorterer prioritert-først:

```bash
python3 - <<'PY'
import glob, re
def fm(p):
    t = open(p).read()
    m = re.search(r'^---\n(.*?)\n---', t, re.S)
    d = {}
    if m:
        for line in m.group(1).splitlines():
            mm = re.match(r'(\w+):\s*(.*)', line)
            if mm: d[mm.group(1)] = mm.group(2).strip().strip('"')
    body = t[m.end():] if m else t    # kun kroppen — IKKE frontmatteren (TODO 174: et fritekstfelt
                                       # som `observed:`/`saves:` med ordet «brainstorm» i prosa
                                       # skal ikke stille sende en todo ut av køen)
    d['_brainstorm'] = bool(re.search(r'krever[^.\n]*brainstorm|brainstorm\s+f.?r\s+plan|spec\s+f.?r\s+plan', body, re.I))
    d['_path'] = p
    return d
def as_int(v, default=9999):
    try: return int(v)
    except (ValueError, TypeError): return default
todos = {}
for p in glob.glob('tasks/todos/todo-*.md'):
    d = fm(p); nr = d.get('nr','')
    if not nr:
        print(f"ADVARSEL: mangler nr i {p}"); continue
    todos[nr] = d                                    # parse hver fil ÉN gang
def dep_done(nr):
    f = todos.get(nr)
    return f is None or f.get('status') == 'done'    # mangler fil ⟹ arkivert
rows = []
for nr, d in todos.items():
    deps = re.findall(r'"([^"]+)"', d.get('deps','') or '')
    tags_raw = d.get('tags', '')
    eligible = (d.get('status')=='open' and (d.get('claimed_by','null') in ('null','',None))
                and not d['_brainstorm'] and all(dep_done(x) for x in deps)
                and not re.search(r'\bforslag\b', tags_raw))
    pr = 0 if d.get('priority')=='prioritert' else 1
    rows.append((pr, as_int(d.get('order')), nr, d.get('status','?'), 'YES' if eligible else 'no', d['_path']))
for r in sorted(rows):
    print(f"elig={r[4]:3} pri={r[0]} order={r[1]:5} TODO {r[2]:5} {r[3]:10} {r[5]}")
open_todos = [d for d in todos.values() if d.get('status') == 'open']
loop_todos = [d for d in open_todos if re.search(r'\bloop\b', d.get('tags', '') or '')]
print(f"\nKø-sammensetning: {len(loop_todos)} av {len(open_todos)} åpne todos er loop-taggede.")
PY
```

Velg øverste rad med `elig=YES`. Ingen → §7 (grooming). **Kø-sammensetning-linjen er ren
rapportering** (TODO 174, Del C′) — den påvirker ALDRI valget over. Se «Du styrer køen
(rattet)» i `orchestration-loop.md` for hvordan mennesket bruker den (`priority: prioritert`
på en `loop`-tagget todo hvis loop-forbedringer sulter).

**TODO 246 — nivå B3:** dette valget (og et bevisst HOPP forbi øverste `elig=YES`-rad, innenfor
mennesket-godkjent rekkefølge) er nivå B3 i `decision-level.py`. Logg kun ved et FAKTISK hopp/valg
utenom triviell «øverste rad vant» — se § Pausepunkter for de fire logg-pliktene.

## 2. Claim + pre-løs lessons-tema

Sett `claimed_by: <din-sesjon>` i todo-fila.

**Pipelinet plan? Hopp §3/§4.** Er `plan:` satt på todoen OG planfila bærer en `**Status:**`-linje
som starter med `pipelinet` — se §5c, «Gjenopptakelse i §2»: §3 og §4 er allerede kjørt i en
tidligere runde og hoppes, etter ferskhets-gaten i §5c. Dette er **IKKE** fast-path (§2b):
`models` skal bære de faktiske planner-/reviewer-modellene fra markørlinja og `plan_review_rounds`
det faktiske tallet — aldri `skipped`/`0`.

**Graf-oppslag (før du velger tema):**
```bash
python3 tasks/graph-query.py --todo <nr>
python3 tasks/graph-query.py --file <sti>     # for hver fil todoen navngir
```
Gir todoens `deps`/`bugs`/`files`/`pr`, hvilke bugs som er **triagert til** den (og hvilke som bare
**omtaler** den), hvilke lessons som nevner den, og — per fil — hvilke todos som har rørt den,
hvilke bugs som bor der, og hvilke lessons som peker dit. Bruk `Foreslåtte lessons-tema`-linja i
outputen som **utgangspunkt** for tema-valget, ikke som fasit.

Grafen bygges on-demand (under ett sekund), skrives til stdout og **lagres aldri**. Det finnes ingen
`tasks/graph.json` å holde fersk — dukker en slik fil opp lokalt, er den et feilsøkings-artefakt
fra `--out` og skal ikke committes.

Gir grafen ingen treff **eller feiler kommandoen** (traceback, ikke-null exit) — fortsett med
`grep tasks/lessons.md`. **Dette steget skal aldri stoppe en runde.**

Grep `tasks/lessons.md` for 1–3 tema relevant for todoens domene (gyldige tema: {{LESSONS_TOPICS}}).

**Claim-release:** I ENHVER stopp-sti senere (teknisk risiko, blocked, failed, merge-konflikt) → sett `claimed_by: null` tilbake før du stopper, så todoen ikke lekker ut av køen.

## 2b. Fast-path (hopp §3/§4 → rett til §5)

En todo kan gå rett til §5 implementer (hopp over §3 planner og §4 reviewer) NÅR **alle tre**
betingelser holder:

- **(a)** ren mekanisk endring med **dokumentert presedens** — en arkivert todo eller lesson
  refereres eksplisitt (ikke bare «dette er trivielt»),
- **(b)** ingen teknisk-risiko-flagg mulig i det hele tatt (ingen migrasjon/RLS/Edge Function-
  deploy/native/EAS/iOS-Modal/secrets/prod-push kan oppstå),
- **(c)** todo-teksten inneholder **komplette verifiseringskriterier** (implementeren trenger
  ingen plan utover selve todo-fila).

**§5b kode-review kan ALDRI hoppes** — uansett fast-path. Dette gjelder uten unntak.

Ved fast-path: todo-teksten ER planen (`Plan: tasks/todos/todo-<nr>-<slug>.md`, «todo-tekst =
plan» — 151-presedens). Ingen endring i implementer-charteret; dette er et koordinator-side
rutevalg (§3/§4 dispatches rett og slett ikke).

**Run-log ved fast-path:** `models`-feltet skriver `skipped` for hoppede stadier →
`skipped/skipped/<impl-modell>/<code-reviewer-modell>`, `plan_review_rounds=0`.

**Presedens-referanser (annotert presist):**
- **TODO 151** (run-log 2026-07-12T02:30, `skipped/skipped/Sonnet4.6/Opus4.8`) = den
  **rene/kanoniske** fast-path-raden: planner+reviewer hoppet, code-reviewer FAKTISK KJØRT.
  Bruk denne som mal.
- **TODO 136** (run-log 2026-07-01T12:35, `Opus4.8/skipped/skipped/skipped`) siteres **KUN**
  for at «`skipped` er en gyldig per-stadie-verdi» i run-log-formatet. 136s
  `code-reviewer=skipped` forutdaterer og **BRYTER** §5b-aldri-hoppes-regelen over — den er
  **IKKE** en gyldig fast-path-mal og skal ikke etterlignes.

**Auditbar presedens:** når fast-path anvendes, MÅ du logge HVILKEN presedens (arkivert
todo/lesson) som påberopes — ikke bare `models=skipped`. Konkret: (i) §5-dispatch-noten
navngir presedensen, og (ii) §6 delt-state-commit-meldingen inkluderer den:
`chore(loop): TODO NN delt-state (fast-path; presedens: TODO XXX / lesson YYYY-MM-DD) — slug`.
Da er beslutningen sporbar i git-historikk, ikke bare implisitt i run-log-`skipped`.

## 3. Dispatch planner

Velg et **canary-mål** workeren ikke kan gjette: en fil+linje som ikke er en invariant og ikke gjentas i prompten (f.eks. `{{CANARY_FILE}}` linje N — varier N per dispatch). Noter den faktiske teksten selv (`sed -n 'Np' {{CANARY_FILE}}`).

**Pre-dispatch-snapshot (§0b vakt 5, R21) — umiddelbart FØR `Agent`-blokken under:**
```bash
git worktree list --porcelain > "<scratch>/wt-pre-3-planner-<runde>.txt"
```
Sjekk exit-koden fra DENNE kommandoen med det samme: ikke-null exit ⇒ dispatchen fortsetter uendret
(worktreen skal ikke droppes fordi et snapshot feilet), men noter paret som `snapshot-missing` — §0b
vil da selv gi ADVARSEL (`snapshot-missing`) og INGEN rydding for nettopp dette paret, i stedet for å
stille anta at et tomt/manglende snapshot betyr «ren». Én fil per dispatch — gjenbruk ALDRI én fil på
tvers av dispatches (se §0b, R21).

`Agent`: `subagent_type: {{PROJECT_NAME}}-planner`. Prompt:
> TODO <nr> (`tasks/todos/todo-<nr>-<slug>.md`). Relevante lessons-tema: <liste>. Canary: returner de første 8 ordene på linje <N> i `{{CANARY_FILE}}`. Følg charteret ditt. Returner plan-rapport som JSON.

Verifiser at `canary` matcher den faktiske teksten du noterte. Mismatch → re-dispatch eller eskalér (workeren leste sannsynligvis ikke filene). Koordinatoren (du) setter `plan:`-stien fra rapportens `plan_path` i todo-frontmatteren — workeren rører den ikke.

**Re-dispatch etter canary- eller bevis-mismatch:** akkumuleringen er per DISPATCH-FORSØK, ikke per
runde — en re-dispatch legger den forkastede workerens `evidence.toplevel` inn i §0b-lista med SITT
EGET pre-snapshot (fila tatt umiddelbart før nettopp DEN dispatchen), og §0b kalles for den også,
ikke bare for dispatch-forsøket som til slutt lyktes.

**Bevis-sjekk (`evidence`, se `report-schema.md`):** verifiser `evidence.toplevel` mot et **a-priori-kjennbart predikat** (du kjenner IKKE den harness-genererte worktree-stien på forhånd): stien MÅ inneholde `.claude/worktrees/` OG MÅ IKKE være hovedsjekkut-roten. Brudd → workeren skrev sannsynligvis planfilen til feil sted (2026-07-11-bug-klassen) — re-dispatch eller eskalér. `evidence` erstatter IKKE din egen uavhengige sjekk (`git status --porcelain` + `wc -l`/`tail` i workerens oppgitte worktree) — den er en billig førstelinje-tripwire, ikke et substitutt.

**Overlevering + commit + §0b-kall (eies av rydde-kontrakten, TODO 194 — TODO 219 punkt 1 skal
UTVIDE denne blokken, ikke legge til en ny).** Gjelder HVER runde, inkludert hver revisjonsrunde.
Kjøres HELT SIST i denne seksjonen, i rekkefølge:

(a) **Overlevering:** kopier `<wt_path>/<plan_path>` til `tasks/plans/<fil>`, verifiser med
`cmp -s`; avvik eller manglende kildefil ⇒ ADVARSEL og INGEN rydding. **Denne kopien ER bindingen
mellom rapport og sti for planner-rollen (§0b vakt 5b):** fila vi kopierte kom fra nøyaktig
`<wt_path>`. §0b MÅ nekte hvis kilden ikke fantes. **(a) kjøres ALLTID, på begge stier** — også når
(b) er en no-op for en pipelinet B (se under).

**Planfil-eierskap ved §3-overleveringen (TODO 252).** Etter at §5-implementeren er dispatchet er
planfila BRANCH-EID. Koordinatoren `cp`-er da ALDRI over `tasks/plans/todo-<nr>-<slug>.md` —
implementeren skriver fix-runde-seksjoner der (se Gate F, §5b), og en `cp` ville slette dem.
§6-arkiveringen av planfila skjer FØRST etter merge. Er en re-plan-runde nødvendig mens en PR er
åpen, går den via en ny planner-dispatch OG en ny implementer-fix-runde — aldri via en `cp` over
branchens versjon.

(b) **Commit + push.** Stage **EKSPLISITTE stier** `tasks/plans/todo-<nr>-<slug>.md` og
`tasks/todos/todo-<nr>-<slug>.md` — **aldri `git add -A tasks/`** — commit-melding
`chore(loop): TODO <nr> plan skrevet — <slug>` (revisjonsrunde: `… plan revidert (runde N) —
<slug>`), deretter samme forhåndssjekk + speil-guard + synk-hale som §6s Delt-state-git-hale (§6
steg 6, gjenbruk ordrett — ikke en forenklet variant):

```bash
# 0. Forhåndssjekk: ingenting usporet under tasks/plans/ som ikke skal til {{BASE_BRANCH}}
git status --porcelain -uall tasks/plans/

# 1. Speil-guard (identisk med §6 steg 1 / §5cs push-haler)
mb=$(git merge-base origin/{{BASE_BRANCH}} HEAD)
non_shared=$(git diff "$mb"..HEAD --name-only | grep -vE '^(tasks/|docs/superpowers/loop/)' || true)
[ -z "$non_shared" ] || { echo "FEIL: HEAD har commits utenfor delt state ($non_shared) — feil branch"; exit 1; }

# 2. Stage KUN de to filene over — aldri `git add -A tasks/` her
git add tasks/plans/todo-<nr>-<slug>.md tasks/todos/todo-<nr>-<slug>.md

# 3. Commit — tolerer «ingenting å committe»
git diff --cached --quiet && echo "ingenting å committe" \
  || git commit -m "chore(loop): TODO <nr> plan skrevet — <slug>"

# 4. Synk + push
git fetch origin {{BASE_BRANCH}} \
  && git rebase origin/{{BASE_BRANCH}} \
  && git push origin HEAD:{{BASE_BRANCH}}
```

**Eierskaps-peker (R20):** er dette en pipelinet B (§5c), eies **commiten** av §5cs pre-par-2-hale
— **kun (b) og (c)** flyttes dit, og (b) blir her en no-op («ingenting å committe»). §0b-kallet
skjer da i §5c, etter den halens push. Blokken er idempotent begge veier — leses «§3s avsluttende
blokk er da en no-op» som «hele blokken hoppes over», forsvinner `cp`-en, `git add` stager
ingenting, artefakt-gaten feiler, og B sin plan når aldri `origin/{{BASE_BRANCH}}` — en regresjon av
selve pipelinen i standardmodus (`max_in_flight: 1`).

(c) **Rydding:** kall §0b med `<rolle> = planner`, `<forventet_fil> = tasks/plans/<fil>`,
`<pre_snapshot> = <scratch>/wt-pre-3-planner-<runde>.txt`.

## 4. Dispatch reviewer + gate

**Pre-dispatch-snapshot (§0b vakt 5, R21) — umiddelbart FØR `Agent`-blokken under. Én fil per
revisjonsrunde:**
```bash
git worktree list --porcelain > "<scratch>/wt-pre-4-plan-reviewer-<runde>.txt"
```
Sjekk exit-koden med det samme; ikke-null ⇒ noter paret som `snapshot-missing` (samme regel som §3).

`Agent`: `subagent_type: {{PROJECT_NAME}}-reviewer`. Prompt:
> TODO <nr>. Plan: `<plan_path>`. Relevante lessons-tema: <liste>. Følg charteret ditt. Returner review-rapport som JSON.

**Bevis-sjekk (`evidence`):** match `evidence.reviewed_head` (PRIMÆR) mot SIN EGEN kopi av planfilen — den samme planfilen du dispatchet revieweren mot. Mismatch → revieweren leste sannsynligvis feil eller utdatert plan — re-dispatch eller eskalér. `evidence.toplevel` er SVAKT/sekundært for reviewer (beviser kun cwd, ikke at riktig artefakt ble lest — reviewer skriver ingenting).

**Rydding av plan-reviewerens worktree:** koordinatoren akkumulerer **paret**
(`evidence.toplevel`, rundens `<scratch>/wt-pre-4-plan-reviewer-<runde>.txt`) fra HVER §4-runde og
kaller §0b én gang per deduplisert sti — dedupliser på STIEN og behold den FØRSTE rundens
snapshot-fil for stien (samme regel som §6 steg 4(i)) — i `go`-grenen, i
`technical_risk`-grenen og ved TERMINERING av revisjons-løkka (etter 2 runder uten `go`).
**ALDRI i no-go-grenen** som sender funnene tilbake til planneren: reviewer-agenten skal leve
videre gjennom revisjonsrunden (TODO 244s kontinuitet). Eies av rydde-kontrakten (TODO 194) — TODO
244 skal utvide DENNE regelen, ikke legge til en ny. **Hvorfor paret og ikke bare stien (R21):**
runde 2s snapshot inneholder runde 1s worktree, så et felles snapshot ville avvist runde 1s sti som
`preexisting` og gjort vakt 5 til en permanent blokkering nettopp i akkumulerings-tilfellet.
**Akkumuleringen er per DISPATCH-FORSØK, ikke per runde:** en re-dispatch etter bevis-mismatch
(`evidence.reviewed_head`) legger den forkastede revieweren sitt `evidence.toplevel` inn i lista med
SITT eget pre-snapshot, og §0b kalles for den også — ikke bare for dispatch-forsøket som til slutt
gir `go`/`no-go`.

**Konsolideringsgate (før planner-revisjonen) — OBLIGATORISK.** En review-runde legger til lag og
fjerner ingen, så en plan som revideres flere ganger degraderer monotont uten et motgrep.

1. **Terskel:** mål `wc -l <plan_path>` FØR planner-revisjonen dispatches, og PÅ NYTT når den
   reviderte planen kommer tilbake. **≥ 400 linjer OG minst én tidligere runde ⇒ konsolider** før
   neste dispatch. «Tidligere runde» er mekanisk: §4-telleren > 0 ELLER
   `git log --oneline -- <plan_path>` viser ≥ 2 commits (overteller heller enn underteller —
   riktig feilretning for en gate). Et førsteutkast har ingen lag å konsolidere.
2. **Hva konsolidering ER:** skriv planen om til gjeldende sannhet — én versjon av hver påstand,
   ingen «r1 sa X, r2 rettet til Y». Behold begrunnelser som bærer implementeringen, og hvert
   bevisst avvist funn som én linje («**Vurdert og forkastet**: X — fordi Y»); strykes avvisningen,
   reiser neste reviewer funnet på nytt. Øvrig review-historikk strykes (run-log og PR-body bærer
   den).
3. **Hva den IKKE er:** ingen ny beslutning, ingen scope-endring, ingen ny planner-dispatch.
   Koordinatoren konsoliderer selv, eller gir omskrivingen til en fersk sub-agent MED
   funn-inventaret (K1) — ansvaret for K1–K3 er koordinatorens. Konsolideringen er ikke en
   revisjonsrunde og teller ikke mot 2-runders-grensen.
4. **Verifisering:**
   - **K1 — funn-inventar FØR omskriving:** hvert review-funn fra ALLE runder (review-rapportenes
     `findings[]` + `git log --format='%s%n%b' -- <plan_path>`), merket `innfoldet` eller
     `bevisst avvist`.
   - **K2 — gjenfinn hvert K1-funn i den NYE teksten** (innfoldet i planteksten, avvist som sin
     «Vurdert og forkastet»-linje). Et funn som ikke gjenfinnes er tapt — da er konsolideringen ikke
     ferdig.
   - **K3 — lengde:** skriv `wc -l` før/etter i commit-meldingen. En konsolidering som gjør fila
     lengre er ikke en konsolidering — begrunn økningen eksplisitt.
5. **Utgangen:** velger du å revidere videre uten å konsolidere en plan over terskelen, skriv
   «konsolidering utsatt fordi …» i commit-meldingen. Stillhet er ikke en lovlig utgang.

Gate på `verdict`:
- `"no-go"` (≥1 BLOKKERENDE) → kjør **Konsolideringsgaten** over, og send så funnene tilbake til planner (§3, revisjons-runde) mot den (ev. konsoliderte) fila. **Hold en eksplisitt teller** («revisjonsrunde X/2») i kontekst. Etter **2** runder uten `go` → ⚠️ eskalér til mennesket, release claim.
- `"go"` → fortsett; VIKTIG/MINDRE-funn (ikke-blokkerende) bæres videre til §5-dispatchen.
  **Re-mål `effort` her (BINDENDE).** Et `go` betyr at oppgaven er kjent: skriv den målte
  størrelsen inn i todoens `effort` på den sammensatte formen `<kode>/<verifisering>`
  (`tasks/todos/README.md`), og behold det opprinnelige anslaget i brødteksten («opprettet som
  `S`»). Kilden er plan-rapporten — planneren skal oppgi begge halvdelene, og revieweren har
  allerede etterprøvd tallene planen kaller målt. Gjør det ALDRI i `no-go`-grenen: da er
  størrelsen nettopp det som ikke er avklart. Avviker den målte størrelsen fra anslaget med mer
  enn ett hakk i noen av halvdelene, skriv én linje om det i decision-log — det er
  kalibreringsdata, ikke støy.

Ved `technical_risk.flagged` (plan- eller review-rapport) → ⚠️ STOPP, release claim, rapporter risikoen, vent på menneskets go — **med mindre** `python3 tasks/decision-level.py --event technical_risk --context source=planner --context kind=<kind> --context executable_gate=<yes|no>` klassifiserer hendelsen som **nivå B5** (KUN plan-rapportens `technical_risk`, `kind ∈ {docs_selfmod, hook_selfmod}` og `executable_gate = true`; se § Pausepunkter under). En `technical_risk` flagget av REVIEWEREN er alltid nivå A, uansett innhold — reviewer-rapporten bærer ikke `kind`/`executable_gate` (`report-schema.md`).

> **Pipelinet B?** «Release claim» gjelder ALLTID den claimede todoen. Er dette en pipelinet,
> u-claimet B (§5c), har den ingen claim å frigi — B droppes ut av pipelinen og A fortsetter
> uendret. Se §5c, «Pausepunkt-samspill: B-sporet pauser mens A er sunn».

## 5. Dispatch implementer

> **Pipelining på?** Er `pipelining.max_in_flight` (dette prosjektet: `{{PIPELINE_MAX_IN_FLIGHT}}`)
> ≥ 1: gå til §5c FØR du dispatcher — §5c velger B (§5c, «Valg av B») og dispatcher par 1
> (implementer(A) + planner(B)) i ÉN melding. Kom hit tilbake for prompt-malen under når §5c er
> hoppet over (`max_in_flight: 0`) ELLER når §5c ikke fant en B å pare med (dispatch A-blokken
> alene med malen under). **I pipelinet modus (standardmodus, `max_in_flight: 1`) dispatches
> implementer(A) FRA §5c par 1, ikke herfra — det akkumulerte paret (`evidence.toplevel`,
> pre-snapshot) for §6s rydding hentes da fra §5cs par-1-snapshot (se §5c), ikke fra
> snapshot-linja rett under.**

**Pre-dispatch-snapshot (§0b vakt 5, R21) — kun i den IKKE-pipelinede grenen, umiddelbart FØR
`Agent`-blokken under (pipelinet gren: se §5cs par-1-snapshot i stedet):**
```bash
git worktree list --porcelain > "<scratch>/wt-pre-5-implementer-<runde>.txt"
```
Sjekk exit-koden med det samme; ikke-null ⇒ noter paret som `snapshot-missing`.

Noter `F3a_ref` = F3a-kommandoen (gate F, §5b) kjørt mot planfila du nå dispatcher; bær tallet i
kontekst sammen med `<N>`-telleren.

`Agent`: `subagent_type: {{PROJECT_NAME}}-implementer`. Prompt:
> TODO <nr>. Plan: `<plan_path>`. Relevante lessons-tema: <liste>.
> **Plan-review-funn å innarbeide (verdict=go, ikke-blokkerende):** <severity + ref + issue + fix> (`ref` er her et **plansteg**, f.eks. «Steg 3» — ikke `file:line`, jf. `report-schema.md:51–53`).
> Følg charteret ditt. Returner ferdig-rapport som JSON.

**Utelatelsesregel:** funn-linjen utelates **helt** (ikke skrevet som «ingen funn») ved **fast-path** (§2b — §4 er da aldri kjørt) og ved `verdict: "go"` uten VIKTIG/MINDRE-funn.

`status: "failed"|"blocked"` → ⚠️ STOPP, release claim, rapporter.

**Bevis-sjekk (`evidence`):** din uavhengige `gh pr view`/`gh pr diff` (se §5b) er OFFISIELT bevis for PR-INNHOLDET — derfor er implementerens `evidence` slanket til `{toplevel, branch}` (kun worktree + riktig branch, ingen ordrett bygg-/testoutput kreves i rapporten). Sjekk likevel at `evidence.branch` matcher `branch`-feltet i rapporten og at `evidence.toplevel` peker på en worktree, ikke hovedsjekkuten.

**Akkumulering for §6s rydding:** koordinatoren akkumulerer PARET (`evidence.toplevel`, rundens
pre-snapshot-fil) fra HVER implementer-dispatch (denne §5-dispatchen — ELLER, i pipelinet modus,
§5cs par-1-snapshot, se pipelining-boksen over — og hver fix-mode-runde i §5b) i en liste §6 sender
til §0b. Fix-mode dispatcher en NY `isolation: worktree`-implementer per runde (K4), så hver
fix-runde får en fersk worktree; §6s ene branch-nøklede oppslag ville bare truffet den siste uten
akkumulering. **Hvorfor PAR og ikke bare sti (R21):** fix-runde 2s snapshot inneholder fix-runde 1s
worktree; med ett felles snapshot ville runde 1s sti blitt avvist som `preexisting`, og vakt 5
hadde blokkert nettopp de stiene akkumuleringen finnes for.

**Bevaringsregel ved abort:** ved `status: failed|blocked`, technical_risk-stopp,
ikke-konvergerende revise-gate, merge-konflikt eller sesjonsdød nås §6 ALDRI. Implementer-
worktreene **BEHOLDES** da bevisst — de kan bære ucommittet arbeid, og mennesket eskaleres til
uansett. Koordinatoren LISTER de akkumulerte stiene i pause-rapporten. Ryddes av mennesket, TODO
245 — aldri av loopen.

## 5b. Uavhengig kode-review

### Probe (dekket av preflight — én gang per sesjon)

Agent-registeret er sesjonsglobalt og snapshottes ved sesjonsstart (se linje 10 over) — det endres
ikke under kjøring. Én probe for `{{PROJECT_NAME}}-code-reviewer` per koordinator-sesjon beviser
derfor nøyaktig like mye som én foran hver enkelt §5b-review. Proben kjøres i `/run-loop` sin
preflight (§ «Forutsetning»), ikke her.

**Unntak — §5b kjørt utenfor `/run-loop`:** da har ingen preflight kjørt, så proben må kjøres her
og nå — samme prompt og samme eskaleringsregel som preflight-proben, før review-dispatchen under.

- Får du `{"ok": true}` → fortsett til review-dispatch.
- «Agent type not found» (eller manglende `ok`) → ⚠️ STOPP, release claim, eskalér til mennesket: «§5b krever en koordinator-sesjon startet ETTER at `.claude/agents/{{PROJECT_NAME}}-code-reviewer.md` ble merget til `{{BASE_BRANCH}}`; start en fersk sesjon».

### Trigger-sett (kode, ikke skjønn)

Før review-dispatch beregner koordinatoren **SELV** hvilke tech-review-agenter diffen burde treffe
— en uavhengig kilde til «hva burde vært dispatchet», uavhengig av kode-reviewerens egen
`triggered`-lesning. Uten denne kilden kan gaten under ikke fange den farlige feilmodusen:
under-dispatch rapportert ærlig som `2/2` (svakheten i den tidligere charter-vakten, TODO 179).

1. **Pin filsettet til samme commit revieweren skal se** (plan-review V-2 — en løpende `gh pr diff`
   kan drifte mellom utregning og review):
   `gh pr view <pr> --json headRefOid` → `<sha>`.
2. **Utled filsettet fra den SHA-en**, ikke fra en løpende `gh pr diff`:
   `gh api --paginate "repos/{owner}/{repo}/compare/{{BASE_BRANCH}}...<sha>" --jq '.files[].filename'`
   (`{owner}`/`{repo}` er `gh`s egne innebygde plassholdere, løst mot repoets remote — ikke
   config-verdier). **`--paginate` er ikke valgfritt:** endepunktet returnerer maks 300 filer per
   side uten det, og et trunkert filsett ville gjort gulvet feil-åpent i stillhet — samme klasse
   som R1 (fail-høyt, aldri fail-open). Fallback KUN hvis `gh api` feiler: `gh pr diff <pr>
   --name-only` (merk: denne følger PR-ens nåværende HEAD og kan ha driftet siden steg 1 — bruk
   kun når compare-endepunktet er utilgjengelig).
3. **Kjør selektoren selv — ikke revieweren.** `python3` er ikke i read-only-rollenes
   Bash-allowlist (`guard-reviewer-readonly.sh` `@STANDALONE`, TODO 189 flipper armen til `enforce`),
   så reduksjonen må kjøres her. Rør filstiene fra steg 2 direkte gjennom et rør — ingen
   mellomfil nødvendig:
   `gh api --paginate "repos/{owner}/{repo}/compare/{{BASE_BRANCH}}...<sha>" --jq '.files[].filename' | python3 tasks/review-lens-select.py --files -`
   → JSON med `triggered`. Dette blir `fan_in.expected_by_selector` i gaten under.
4. Dispatch kode-revieweren som normalt (se Review-dispatch under).

### Review-dispatch

**Pre-dispatch-snapshot (§0b vakt 5, R21) — umiddelbart FØR `Agent`-blokken under. Én fil per
kode-review-runde:**
```bash
git worktree list --porcelain > "<scratch>/wt-pre-5b-code-reviewer-<runde>.txt"
```
Sjekk exit-koden med det samme; ikke-null ⇒ noter paret som `snapshot-missing`.

`Agent`: `subagent_type: {{PROJECT_NAME}}-code-reviewer`. Prompt:
> TODO <nr>. PR: `<pr_url>` (fra ferdig-rapporten). Relevante lessons-tema: <liste>. Følg charteret ditt. Returner code_review-rapport som JSON.

**Bevis-sjekk (`evidence`):** match `evidence.pr_head_sha` (PRIMÆR) mot din egen `gh pr view <pr> --json headRefOid` — bekrefter at revieweren faktisk reviewet siste commit (ikke en stale versjon av PR-en). Mismatch → re-dispatch reviewen. `evidence.toplevel` er SVAKT for code-reviewer (leser via `gh`, ikke worktree-filer).

**Rydding av kode-reviewerens worktree:** §0b kalles her — etter bevis-sjekken og FØR
Fan-in-verifiseringen, FØR severity-gulv-steget og FØR revise-gaten (som per «Rekkefølge (TODO
180B)» evalueres ETTER gulv-steget). Kode-revieweren er død i det rapporten er returnert, så
ryddingen er uavhengig av både gulvet og gate-utfallet. Kall §0b UBETINGET (244 beholder fersk
kode-reviewer i ALLE §5b-runder, inkludert revisjonsrunder) med `<rolle> = code-reviewer`,
`<pre_snapshot> = <scratch>/wt-pre-5b-code-reviewer-<runde>.txt` — også i fix-mode-runder
(§0bs Inngangsdata-regel: fila som ble skrevet umiddelbart FØR DENNE code-reviewer-dispatchen — se
§0b for den generelle regelen og §5s Fix-mode-dispatch-mal for implementer-PARETS egen,
IKKE-relaterte fil) — ingen `<forventet_fil>` — rollen «skriver ingenting», så vakt 5 (og ikke en
`cp`-binding) er den eneste bindingen mellom rapport og sti her. **Snapshotet er per
DISPATCH-FORSØK, ikke per runde:** en re-dispatch etter bevis-mismatch (`evidence.pr_head_sha`
over) skjer FØR nettopp DETTE §0b-kallet nås for den dispatchen — den forkastede kode-revieweren
har da sitt EGET pre-snapshot (tatt umiddelbart før nettopp DEN dispatchen, ikke gjenbrukt fra
runden), og §0b kalles UBETINGET for den også, ikke bare for dispatch-forsøket som til slutt går
videre til gate-evalueringen.

### Riving og migrasjon — tre ekstra gater

Gjelder når en PR **sletter eller erstatter en brukervendt flate** (ruter, sider, komponenter som
flyttes til et nytt sted). Klassen er farlig fordi **fravær ikke har noen feilmelding**: en
manglende komponent kaster ikke, logger ikke og bryter ingen test — den oppdages først når noen
leter etter noe som ikke er der.

**G1 — dekningslista genereres, skrives ikke.** Har prosjektet et dekningsdiff-verktøy (fjernede
filer mot erstatningsflaten): implementeren kjører det i §5 og limer outputen i PR-body-en,
code-revieweren kjører **samme** kommando i §5b. Outputen står **sammen med** en
`NOT_DETECTABLE_BY_DIFF`-seksjon — det verktøyet ikke ser (typisk CSS, layout, interpolert tekst).
Uten verktøy: dekningslista skrives manuelt og merkes **HÅNDSKREVET** (lavere tillit) i PR-body-en.

**G2 — varianttvang.** Har erstatningsflaten grener (uke/måned, desktop/mobil, roller), verifiseres
**hver gren** — ikke bare den som utløste arbeidet.

**G3 — falsifiser sammendraget i BEGGE retninger.** Gi code-revieweren dette som navngitt oppdrag
i §5b-dispatchen: (a) står alt som faktisk forsvinner på lista, og (b) er alt på lista faktisk
borte? Underdriving gir uinformert godkjenning; overdriving undergraver tilliten til lista neste
gang. Omstridte påstander verifiserer koordinatoren selv mot koden.

**Billig tilleggsgrep:** for hver hovedfunksjon den slettede flaten hadde — «hvor lever dette
etterpå?». Grep-sveiper ved riving dekker **både URL-form** (`/rute`) **og filsti-form** (f.eks.
`app/(gruppe)/rute/page.tsx`) — sistnevnte fanger tester som leser de slettede filene som kilde —
og hele repoet, ikke bare kildemappene.

### Gate (revise-gate på severity, ikke kun på verdict)

**Rekkefølge (TODO 180B):** evaluer denne gaten ETTER severity-gulv-steget i
Fan-in-verifiseringen under — gate-inputen er ALLTID de justerte severity-verdiene fra
`tasks/review-severity-floor.py`s `findings[]`-output — fra den SISTE kjøringen i runden (se
«Gulvunntak for ordlyd» under) — ALDRI `code_review.findings[]` slik den
ankom fra revieweren. Ved en fix-runde inngår i tillegg **Gate F** (TODO 252, V-blokk-re-verifisering,
under) i rekkefølgen: fix-rapport → Gate F → (rød ⇒ mekanisk retur, ingen ny review) → kode-review
r(N+1).

Les `code_review`-rapporten:

- Inneholder rapporten **≥1 BLOKKERENDE eller ≥1 VIKTIG** → **revise-gate**: send funnene tilbake til implementeren via fix-mode-dispatch (se fix-mode-mal under). Når fix-rapporten kommer tilbake: kjør **Gate F** (under) FØR du dispatcher kode-review r(N+1) — rød gate F ⇒ mekanisk retur, ingen ny review. **Hold en eksplisitt teller** («kode-review-runde X/2», samme mønster som §4). **TODO 246 — nivå B1:** etter **2** runder (`code_review_rounds = 2`) klassifiseres valget mellom (a) én ekstra målrettet fix-runde (runde 3), (b) merge med carry-forwards, eller (c) stopp, som **nivå B1** — `python3 tasks/decision-level.py --event revise_gate_choice --context code_review_rounds=2 --context action=<fix_round|merge_carry|stop> --context decision_logged=yes`. Koordinatoren velger selv (anbefalt handling), logger alle fire pliktene i § Pausepunkter, og fortsetter — mennesket kan vetoe i etterkant. Er den ene ekstra runden (`code_review_rounds = 3`) ALLEREDE brukt og revise-gaten fortsatt ikke tom (et nytt `fix_round`-forsøk) → dette er **nivå A0** (`decision-level.py` feiler høyt) → ⚠️ eskalér til mennesket, release claim. En LUKKENDE beslutning (`merge_carry`/`stop`) forblir nivå B1 uansett rundetall — se rundetak-vakten i § Pausepunkter.
- Kun MINDRE eller ingen funn (`verdict = "go"`, revise-gate ikke trigget) → fortsett til §6.
- Teknisk risiko som dukker opp i rapporten → ⚠️ STOPP, release claim, rapporter (samme som §4-gaten).

> **Pipelinet B?** Se presiseringen i §4 — «release claim» gjelder alltid den claimede todoen,
> aldri en pipelinet B.

**NB:** `verdict = "no-go"` trigges kun ved ≥1 BLOKKERENDE (identisk med plan-review). Revise-gaten er strengere — den trigges også ved ≥1 VIKTIG selv om `verdict = "go"`. Koordinatoren leser severity-arrayet direkte, ikke kun `verdict`.

**Fan-in-verifisering (TODO 180A — `observe`-modus, IKKE stoppende):**

`fan_in` er PÅKREVD i full modus (jf. `report-schema.md`). **Mangler feltet HELT** → kontraktbrudd,
behandles som usignert (re-dispatch reviewen) — samme prinsipp som 179s vakt: fravær er utvetydig
bevis på at vakten ble ignorert, aldri et stilltiende «alt er fint».

Er `fan_in` til stede: etter at `evidence.pr_head_sha` er bekreftet, fyll `fan_in.expected_by_selector`
med resultatet fra Trigger-sett-steget over. Revieweren skal ha levert feltet som en TOM array
(`"expected_by_selector": []`) — «utfylt» betyr her en IKKE-TOM array. Ankommer rapporten med en
IKKE-TOM `expected_by_selector`, er det et kontraktbrudd og behandles som usignert (re-dispatch
reviewen) — det feltet fylles KUN av koordinatoren, og først ETTER at rapporten er mottatt. Regn
deretter ut tre mengde-sammenligninger:

- `expected_by_selector ⊆ fan_in.dispatched` — brudd = **under-dispatch**
- `fan_in.returned == fan_in.dispatched` — brudd = **stille node**
- `fan_in.dispatched ⊆` navnene under `tech_review_agents` i config — brudd = **ukjent agent**

**I de første N = {{HEALTH_CHECK_INTERVAL}} §5b-kjøringene etter merge av TODO 180A** (N speiler
`release.health_check_merge_interval`): **logg** utfallet av
sammenligningen, **stopp ikke** ved avvik. Skriv `selector=<navn,navn>` (eller `selector=none` hvis
ingen agent ble trigget) sammen med utfallet i `run-log.md` felt 11 (den udokumenterte
fritekstkolonnen — se `report-schema.md`).

**Tellemetode for N (korrigert, TODO 180B):** 180As EGEN merge-rad bærer `selector=none`, skrevet
FØR gaten var i kraft — en naiv opptelling av alle `selector=`-forekomster i hele `run-log.md`
teller den raden med og gir et falskt for høyt tall. Tell i stedet KUN radene ETTER 180As
merge-rad:

  `awk '/\| 180A \|/{f=1;next} f' docs/superpowers/loop/run-log.md | grep -c "selector="`

**Ankeret er den FØRSTE forekomsten av `| 180A |`** — `{f=1;next}`-formen setter `f=1` kun ved
første treff og nullstiller det aldri, så en senere rad som tilfeldigvis også får `180A` i
todo-kolonnen kan ikke flytte vinduet. Verifiser likevel vinduets størrelse med `wc -l` ved
avlesning (antall rader inkludert i tellingen), ikke bare stol på selve tallet.

Les **TALLET** denne kommandoen skriver til stdout — `grep -c` returnerer **exit 1** (ikke exit 0)
ved null treff, så ikke la kommandoens exit-kode avbryte en gate som leser et lovlig «ennå ingen
observasjoner»-resultat. Passerer telleren {{HEALTH_CHECK_INTERVAL}}: gaten flippes til `enforce` —
dette er en navngitt del av **TODO 180B**s carry-forward CF-1, IKKE noe koordinatoren gjør stille
av seg selv i mellomtiden.

**Fan-in-form-kontrakt (TODO 250A + 250B — stoppende for `BINDING_CODES` når vakten er armert):**

**Invokasjon.** **Sjekk FØRST session-predikatet i «Kontrakt-vakt (TODO 250B)» under: er det SANT, hopp dit og kjør form B — er det USANT (eller uregistrert), kjør blokka under (form A) uendret** (TODO 250B — avgjørelsen står FØR den ubetingede form A-fenced-blokka under, ikke etter, slik at blokka aldri ser ut til å gjelde ubetinget). Skriv `code_review.fan_in` (med `expected_by_selector` fylt i steget over) til
`<scratch>/fan-in.json` — samme mønster som `<scratch>/findings-5b-<nr>-<runde>.json` i steget
under (`fan-in.json` selv er IKKE navngitt per todo/runde — det ligger utenfor TODO 321s scope) —
og kjør (koordinatoren, aldri revieweren; `python3` er ikke i read-only-rollenes Bash-allowlist, M6)
kommandoen i den fenced blokka under. Etter TODO 250B finnes **to** frosne CLI-former i denne fila,
og **hver av dem er entydig innenfor sin egen fensede kodeblokk**: **form A (uarmert)** er blokka
rett under, ORDRETT uendret fra før TODO 250B, med det fakultative hakeparentes-leddet for PR-head-SHA;
**form B (armert)** står i «Kontrakt-vakt (TODO 250B)»-blokka under og legger til de to
strict-flaggene. Begge skal stå som eneste linje i en fenced bash-kodeblokk, starte i kolonne 0 og
ikke inneholde backticks. Begge ekstraheres og kjøres ORDRETT av planens V17-gate, som kun leser
INNSIDEN av fensede kodeblokker — ingen prosa i denne fila skal sitere uttrekksmønstrene ordrett.

```bash
python3 tasks/review-fan-in-verify.py --fan-in <scratch>/fan-in.json [--pr-head-sha <sha>]
```

`<scratch>` og `<sha>` er plassholdere for leseren; de substitueres mekanisk og kommandoen kjøres i
to grener — uten det fakultative leddet, og med hakeparentesene fjernet. Dette er ordrett form A slik
V17 kjører den mot levende tre. Er session-predikatet i «Kontrakt-vakt (TODO 250B)» usant, brukes
DENNE formen (form A) uendret — den er IKKE fjernet, kun supplert.

**Exit-kode-kontrast.** Exit-koden betyr ulike ting i de to formene. **Form A:** exit `0` for
ethvert antall funn; utfallet leses fra `violations[]` og `signals.attest`. **Form B:** exit `0` =
akseptert, exit `3` = AVVIST (minst én kode i `BINDING_CODES`), og `verdict` sier det samme. **I
begge former** betyr enhver ANNEN exit-kode enn 0 (form A) eller 0/3 (form B) at SKRIPTET selv
feilet — da skriver du `attest=script-error` og går videre, aldri en avvisning. (`--self-test` er en
tredje modus med motsatt kontrakt: den exit'er `1` ved feil — se skriptets docstring.)

**Utfallstabellen (paritets-orakelet for V7 — FROSSET ORDRETT).**

| ID | Brudd-kode | Klasse |
|---|---|---|
| R1 | input-unreadable | logg |
| R2 | contract-missing-key | stopp |
| R3 | contract-bad-type | stopp |
| R4 | attestation-malformed | stopp |
| R5 | attestation-mismatch | stopp |
| R6 | returned-not-dispatched | logg |
| R7 | silent-node | logg |
| R8 | unknown-agent | logg |
| R9 | under-dispatch | logg |
| R10 | stale-lens-sha | stopp |
| R11 | attestations-missing | stopp |
| R12 | premature-return | betinget |
| R14 | live-key-unreadable | logg |

Bindende koder (`stopp`) stopper KUN når koordinatoren faktisk kjører form B (`--strict
--require-attestations`) — session-predikatet i «Kontrakt-vakt (TODO 250B)» avgjør hvilken form som
kjøres. `betinget` (R12) er en TREDJE klasse: den kan KUN stoppe når koordinatoren i tillegg ga
`--live-key` og nøkkelfilas `mode == "ledger"` — se «Liveness-vakt»-seksjonen under.

Seks koder er bindende (R2–R5, R10, R11) når koordinatoren kjører form B. R6–R9 er `logg` og eies av
**180B CF-1**; R1 er `logg` fordi den måler koordinatorens egen inndata-fil — det tilfellet dekkes
av den bindende regelen «manglende `fan_in` ⇒ usignert» over. Flippen ble gjort i TODO 250B. R14
(`live-key-unreadable`) er ALDRI bindende: den måler koordinatorens EGEN nøkkelfil, ikke et felt
revieweren fylte — nøyaktig samme argument som R1. R12 (`premature-return`) er BETINGET bindende —
kun i `mode=ledger` — se «Liveness-vakt (TODO 250C)»-seksjonen under for utfallstabellen per
brudd-kode og den målte per-sesjon-fastsettelsen av `live.mode`.

**Tre eksplisitte ikke-endringer:**

- `under-dispatch`, `silent-node` og `unknown-agent` er de samme tre sammenligningene 180A allerede
  kjører i `observe` i avsnittet over. Skriptet mekaniserer loggingen av dem, og ingenting mer.
  Flippen til `enforce` er og forblir **180B CF-1** — dette er en navngitt del av **TODO 180B**s
  carry-forward CF-1, IKKE noe koordinatoren gjør stille av seg selv i mellomtiden.
- De to eksisterende BINDENDE runbook-reglene går fortsatt foran skriptet: manglende `fan_in` ⇒
  usignert; ikke-tom `expected_by_selector` fra revieweren ⇒ usignert. For kodene i `BINDING_CODES`
  er skriptets exit 3 derimot BINDENDE — rapporten forkastes som usignert. For R6–R9 er skriptet
  fortsatt kun en logg.
- `attestations` er PÅKREVD når session-predikatet er sant: manglende nøkkel med ikke-tom `returned`
  er `attestations-missing` (R11) ⇒ stoppende. Er predikatet usant, kjøres form A, og manglende
  nøkkel er da `attest=legacy` og ikke et kontraktbrudd.

**Severity-gulv (TODO 180B — BINDENDE, håndhevet i kode, IKKE `observe`):**

I motsetning til fan-in-sammenligningen over (som kun logger i `observe`), er severity-gulvet
bindende fra denne PR-en av: `rls-migration-reviewer` og `edge-function-reviewer` var
`funn→BLOKKERENDE` automatisk FØR 180B; etter 180B er det et steg NOEN må ta. Etter at
`fan_in.expected_by_selector` er fylt over, kjør (`python3` er ikke i read-only-rollenes
Bash-allowlist, `guard-reviewer-readonly.sh:689`, TODO 189 er fortsatt `open`, så dette kjøres her,
av koordinatoren, aldri av revieweren), tre separate kall — de to fetchene gjør både
`{{BASE_BRANCH}}` og PR-hodet (`<sha>`) lesbare lokalt FØR selve skriptkallet:

```bash
git fetch origin {{BASE_BRANCH}}
```
```bash
git fetch origin pull/<pr>/head
```
```bash
python3 tasks/review-severity-floor.py --findings <scratch>/findings-5b-<nr>-<runde>.json --rev <sha>
```

(`<scratch>/findings-5b-<nr>-<runde>.json` = `code_review.findings[]` fra rapporten, skrevet til
sesjonens scratchpad-katalog — samme mønster som pre-snapshotene (`<scratch>/wt-pre-<seksjon>-
<rolle>-<runde>.txt`), navngitt per todo og runde for å unngå kollisjon på tvers av parallelle
implementere (§5d). `<sha>` = rundens `evidence.pr_head_sha` etter bevis-sjekken over, full
40-tegns SHA. De to fetchene over gjør både `{{BASE_BRANCH}}` og PR-hodet lesbare lokalt. Uten
dem, eller uten `--rev`, avvises hvert `floor_exempt`-merket funn mekanisk
(`ref_unresolvable`/`no_rev`), og gulvet gjelder.)

Gate-seksjonen over leser DENNE kommandoens `findings[]`-output — de justerte severity-verdiene —
ikke `code_review.findings[]` slik den ankom fra revieweren. Har skriptet hevet ett eller flere
funn til et agent-gulv, er det den hevede severityen som teller mot ≥1 BLOKKERENDE / ≥1 VIKTIG.

**Exit-koden fra DETTE skriptet SKAL leses — i motsetning til `grep -c`-tellingen over.** Exit ≠ 0,
eller en ikke-tom `violations[]` i output, er et kontraktbrudd: `process()` i skriptet ekskluderer
BEVISST ethvert funn med manglende/ukjent `source_agent` eller ugyldig `severity` fra
`findings[]`-arrayet — de havner KUN i `violations[]`, aldri i `findings[]`. Et BLOKKERENDE funn med
et slikt brudd er dermed usynlig for gate-seksjonen over hvis du kun leser `findings[]` og ignorerer
exit-koden. En kjøring som exit'er ≠ 0 her behandles derfor som en **USIGNERT** rapport — reviewen
re-dispatches, akkurat som ved manglende `fan_in` — og du MERGER ALDRI på en `findings[]`-output fra
en kjøring med exit ≠ 0.

**Gulvunntak for ordlyd (TODO 321 — BINDENDE).** Skriptet godtar
`"floor_exempt": "comment_doc_wording"` bare når agenten har klassen i `loop.config.yaml` og
funnets `ref` (`fil:N` eller `fil:N-M`) ved `<sha>` peker på kommentarlinjer eller på en `.md`-fil
under `docs/`. Godtatte funn står i `exempt[]` og beholder severity; avviste står i
`exempt_rejected[]` med `reason` og har fått gulvet som umerkede funn.

Unntaket vurderes i SAMME runde som funnet meldes inn, så det finnes ingen rettelse ennå å se for
DETTE funnet — skriptet ser aldri en rettelse, verken nå eller senere (se skriptets docstring).
Det som faktisk sjekkes, for HVERT funn i `exempt[]`, før gaten leser `findings[]`, er: (1) lesing
av `issue`/`fix` i funnet (hovedkriteriet under) — eneste kontroll av selve funnet; (2) fra r≥2, en
INDIREKTE sjekk: diffen mot forrige rundes verifiserte sha bekrefter at FORRIGE fix-runde bare
endret ordlyd i `<ref-fil>` — ikke at DETTE funnet er rettet. **Restklasse (ikke løst av denne
kontrakten):** en rettelse av et unntatt funn finnes aldri på beslutningstidspunktet — unntaket
avgjøres i samme runde funnet meldes, så merge-rutingen leser `findings[]` FØR noen rettelse kan
foreligge, og denne kontrakten differ den derfor aldri. Skjer ref-fila likevel endret i en SENERE
runde av en annen grunn, er det DEN rundens egen r≥2-sjekk som ser det — denne kontrakten
viderefører ikke referansen til ett bestemt unntatt funn på tvers av runder. `<ref-fil>` er stien i
funnets `ref` foran `:`.

**Hovedkriterium (alltid, uansett runde):** godta bare når `issue` og `fix` i funnet UTELUKKENDE
gjelder ordlyd på ref-linjene. Diffen under er et SUPPLEMENT — den bekrefter at ENDRINGEN som
faktisk ble gjort også bare er ordlyd, den erstatter aldri lesingen av `issue`/`fix`.

**r1** (ingen forrige kode-review-runde): les funnet mot PR-diffen for ref-fila. Begge fetchene
(`origin/{{BASE_BRANCH}}` og `origin/pull/<pr>/head`) er allerede kjørt i severity-gulv-blokken
over — ingen ny fetch her, kun selve diff-kommandoen:

```bash
git diff origin/{{BASE_BRANCH}}...<sha> -- <ref-fil>
```

**r≥2:** `<forrige_sha>` er forrige kode-review-rundes verifiserte `evidence.pr_head_sha`, skrevet
FULLT ut (40 tegn) i den rundens decision-log-entry (TODO 321) — les den derfra, aldri fra
hukommelse. En kort SHA er lov når den løses opp først: `git rev-parse <kort>`. Finner du ingen
decision-log-entry med `evidence.pr_head_sha` for forrige runde: avvis unntaket (samme fail-closed
prinsipp som `ref_unresolvable`).

```bash
git diff <forrige_sha>..<sha> -- <ref-fil>
```

**Kun r≥2:** avvis når en endret linje i hunkene (linjene etter første `@@`) verken er blank eller
en kommentarlinje, med mindre ref-fila ligger under `docs/` og er en `.md`-fil. En `---`-linje INNE
i en hunk er en fjernet `--`-kommentar, ikke et filhode. Endringer fra en `origin/{{BASE_BRANCH}}`-merge
i samme fil teller likt. Tom diff eller bare kommentarer: godta bare når `issue` og `fix`
utelukkende gjelder ordlyd (hovedkriteriet over).

**Avvis alltid** når `issue` eller `fix` sier at kode, SQL, en policy, en constraint eller en test
gjør noe annet enn kommentaren, når rettelsen krever endring utenfor kommentarlinjer eller en
`.md`-fil under `docs/`, eller når du er i tvil. **Restklasse (ikke løst av denne kontrakten):** en
rettelse som også krever en kodeendring i en ANNEN fil enn `<ref-fil>` fanges ikke mekanisk her —
se PR-teksten for TODO 321, punkt (b).

**Avvisning gjeninnfører gulvet.** Sett `"floor_exempt": null` på akkurat det funnet i
`<scratch>/findings-5b-<nr>-<runde>.json`, endre ingenting annet, og kjør skriptkommandoen over på
nytt med samme `<sha>`. Funnet heves da til agentens `severity_floor` og teller i revise-gaten.
Gaten leser den SISTE kjøringens `findings[]`, og exit-regelen over gjelder hver kjøring. Du legger
ALDRI TIL en merking.

Skriv sporet i `run-log.md` felt 11, ved siden av `selector=`:

- `floor=<antall hevet>` (rundens siste kjøring) — antall funn skriptets `raised[]` inneholder.
- `floor=none` brukes KUN når `findings[]` var TOM (ingenting å sjekke). Er arrayet ikke-tomt og
  ingenting ble hevet: skriv `floor=0`, ikke `floor=none`.
- `viol=<antall kontraktbrudd>` — antall funn skriptets `violations[]` inneholder, skrevet ved
  siden av `floor=` i SAMME felt. `viol=0` når arrayet er tomt. Skriptets stderr-oppsummeringslinje
  (`[review-severity-floor] hevet: N, pausepunkt: N, kontraktbrudd: N`) er kilden for begge tallene.
- `floor_exempt=<g>:godtatt,<a>:avvist` (TODO 321), skrevet ved siden av `floor=` i SAMME felt og
  summert over todoens kode-review-runder. Per runde er `<g>` = `unntak: N` fra rundens SISTE
  kjøring og `<a>` = `unntak: N` fra rundens FØRSTE kjøring minus `<g>`. Hadde ingen runde et funn i
  `exempt[]`: skriv `floor_exempt=0`. Skriptets egne avvisninger (`unntak avvist: N`) telles ikke
  her; de er behandlet som umerkede funn. Stderr-oppsummeringslinja over siterer den nye linja og
  er kilden for tallene.
- Har skriptets `pausepunkt[]` innhold (typisk funn fra `ios-design-reviewer`, gulv `PAUSEPUNKT`):
  skriv `pausepunkt=<agent>:<antall>` i tillegg, og bær funnet inn i PR-ens manuelle
  verifiseringssjekkliste. PAUSEPUNKT hever og senker ALDRI severity — det er et RUTINGS-gulv, ikke
  en rang — og skaper INGEN `outcome=paused`-rad (den formatendringen i `run-log.md` eies av
  TODO 210, ikke av denne kontrakten).

**Fravær av `floor=` på en `merged`-rad er et kontraktbrudd** — fravær er utvetydig bevis på at
steget ble hoppet over, aldri en stilltiende «alt var fint». I dag er `funn→BLOKKERENDE` automatisk;
etter denne PR-en er det et steg noen må ta, og det er nettopp derfor sporet finnes.

**Fravær av `floor_exempt=` på en rad som har `floor=` og er skrevet etter at TODO 321 er merget, er
også et kontraktbrudd.** Tokenet er selvrapportert som `floor=` (avsnittet under): tilstedeværelse
beviser ikke at diffene ble lest.

**`floor=` er IKKE «samme prinsipp som manglende `fan_in`» — den påstanden er usann og skal ikke
gjentas.** `fan_in` fylles av en ANNEN part (revieweren, deretter koordinatorens egen
`expected_by_selector`-utregning) — fravær av `fan_in` beviser dermed at et steg noen andre eier ble
hoppet over. `floor=` er derimot **selvrapportert** av koordinatoren selv: koordinatoren skriver
tallet inn i den samme runden som den kjører (eller unnlater å kjøre) skriptet. Fravær av `floor=`
er fortsatt bevis på at steget ble hoppet over — det holder. Men TILSTEDEVÆRELSE av `floor=` er
IKKE bevis på at skriptet faktisk ble kjørt korrekt: en rad som skriver `floor=0` kunne i prinsippet
vært skrevet av en koordinator som aldri kjørte kommandoen. Uavhengig verifisering av at gulvet
faktisk virker i drift er CF-4 (race-reviewer i live dispatch) / CF-6 (at ALLE observasjoner fra en
gulvet lens faktisk overlevde synthesizeren), ikke noe denne runbook-linja alene kan bevise.

**`auto_decided=<rad-eier>:<antall>` (TODO 246), skrevet ved siden av `selector=`/`floor=`/
`pipelined_from=` i SAMME frittekst-felt — IKKE en ny kolonne:**

- `<rad-eier>` = todo-nummeret som EIER run-log-raden (radens felt 2, den claimede todoen) —
  ALDRI beslutningens egen todo hvis den er en annen (f.eks. en B3-hopp av en ANNEN todo telles
  under den aktive todoens rad).
- `<antall>` = ALLE nivå-B-valg logget i denne runden, uansett hvilken todo de gjaldt.
- Nøyaktig ÉTT `auto_decided=`-token per rad — to tokens på samme rad gjør at avstemmingens
  `match()` bare fanger det siste (Del D4).
- Ingen nivå-B-valg denne runden ⇒ skriv `auto_decided=<rad-eier>:0` uansett — fravær av tokenet
  er et kontraktbrudd, ikke «tomt betyr null» (samme prinsipp som `floor=` over).
- `outcome=health`-rader bærer ALDRI `auto_decided=` — nivå-B-oppsummeringen ligger i
  `loop-health-check.md` Del D4 i stedet.
- **Legacy:** `auto_decided=<nr>` UTEN kolon (forekommer i dag på rader FØR denne PR-en) er
  pre-246 og IGNORERES av alle gater — ikke samme felt-semantikk som den nye kolon-formen.

**Partisjonering ved flere rader i SAMME runde (TODO 233, §5d — parallelle implementere) — TEMPORAL,
ikke rolle-basert (kode-review-funn).** Del D4s `sum`-avstemming
(`.claude/commands/loop-health-check.md`) summerer over ALLE rader siden forrige `health`-rad og
krever `sum == <antall>`. En runde med §5d armet skriver mer enn én rad (A sin `merged`-rad, og
enten B sin `merged`-rad eller B sin `paused`-rad ved eskalering, § 5.5) — uten en
partisjoneringsregel ville hver rad båret rundens FULLE `<n>`, og summen dobles mot avstemmingens
`<antall>`. En ren rolle-basert regel («A bærer alt, B bærer alltid `:0`») er FEIL: A merges først
(§ 5), så A-raden skrives i §6(A) MENS B fortsatt er i flukt. Ethvert nivå-B-valg som oppstår PÅ B
sitt spor ETTER at A-raden allerede er skrevet (f.eks. et B4-valg under B sin kode-review r2) har da
ingen bærer hvis B-raden er hardkodet til `:0` — en decision-log-entry uten et matchende
run-log-inkrement ⇒ D4 AVVIK ⇒ helsesjekk RØD.

Regelen er derfor **partisjonert på TID, ikke på rolle**: hver rad bærer nivå-B-valgene som var
kjent DA DEN raden ble skrevet. A-raden (skrevet FØRST, § 5 steg 1) bærer
`auto_decided=<A>:<n>`, der `<n>` er alle rundens nivå-B-valg kjent PÅ DET TIDSPUNKTET. **Enhver
senere rad i samme runde — B sin `merged`-rad (§5 steg 6) eller B sin `paused`-rad (§5.5) — bærer
`auto_decided=<B>:<m>`**, der `<m>` teller nivå-B-valg tatt ETTER at A-raden ble skrevet. `<m>` er
**normalt `0`** (de fleste runder har ingen nye nivå-B-valg på B sitt spor etter at A er ferdig),
men er **IKKE mandatert til å være `0`** — en fix-runde eller eskalering på B ETTER §6(A) kan
introdusere et B4-valg (f.eks. «arm re-synk i stedet for pausepunkt») som ikke har noen annen bærer
enn B-raden selv. Tokenet er fortsatt obligatorisk på ALLE rader i runden; det er FORDELINGEN og
TIDSPUNKTET som er definert, ikke plikten. `<rad-eier>`-definisjonen over («todo-nummeret som EIER
run-log-raden») gir A-raden ansvar for alt som er kjent FØR den skrives, og B-raden ansvar for
resten — ikke fordi B «alltid er null», men fordi B-raden skrives SIST og derfor er den eneste
gjenværende bæreren for alt som skjer i mellomtiden.

**Ankeret er navngitt (kode-review-funn, fix-runde 2, MINDRE 5).** Grensen mellom «kjent PÅ DET
TIDSPUNKTET» (A-raden) og «ETTER at A-raden ble skrevet» (B-raden) er A-radens `$TS` — run-log
felt 1, satt idet A-raden faktisk skrives (§ 5 steg 1). Enhver decision-log-entry med et
tidsstempel STØRRE ENN `$TS` hører til B-raden og telles i `<m>`; enhver med tidsstempel MINDRE
ENN ELLER LIK `$TS` hører til A-raden og telles i `<n>`.

**`attest=<verdi>` (TODO 250A — `observe`-spor i SAMME frittekst-felt, IKKE en ny kolonne):**

- **Verdier:** `ok` | `legacy` | `none` | `<kommaseparerte avvikskoder>` (skript-produsert), hver av
  dem med prefikset `strict:` når kontrakt-vakten var ARMERT i den runden (TODO 250B, form B) —
  pluss den koordinator-skrevne `script-error`, som ALDRI prefikses. Prefikset er telemetri: uten
  det kan man i ettertid ikke se om en grønn rad var bevoktet eller ubevoktet. Ingen mellomrom, ingen
  `|` (kolonneseparator).
- **Nøyaktig ÉTT `attest=`-token per rad** (samme regel som `auto_decided=` over).
- **`outcome=health`-rader bærer ALDRI `attest=`** (samme regel som `auto_decided=` over).
- **Skrives på rader som HAR hatt en §5b-kode-review.** En rad uten kode-review-runde har ingenting å
  attestere.
- **Fraværs-semantikken, eksplisitt kontrastert mot BEGGE naboene:** `attest=` er obligatorisk å
  SKRIVE, men — i motsetning til `floor=` og `auto_decided=`, som begge gjør fravær til et
  **kontraktbrudd** — er fravær av `attest=` IKKE et kontraktbrudd i denne releasen: ingen
  re-dispatch, ingen usignert-behandling. Forskjellen er bevisst: `floor=` og `auto_decided=` sporer
  BINDENDE steg, `attest=` sporer en kjøring som kan være armert (`strict:`-prefiks) eller uarmert
  (`observe`) — fravær er derfor ikke et kontraktbrudd (CF-250B-1) (TODO 250B — form B gjør vakten
  BINDENDE for enkelte rader, så «sporer en `observe`-logg» er ikke sant for alle rader). Flippen av
  `attest=`-FRAVÆR til kontraktbrudd ble VURDERT og forkastet i TODO 250B: tilstedeværelse av
  `attest=` er selvrapportert og beviser ikke at skriptet kjørte, så fravær som brudd ville vært
  bokføring uten bevisverdi. Spørsmålet er rutet til CF-250B-1 (TODO 210s run-log-format-runde).
  Opphavssignalet setningen tidligere refererte til er nå MÅLT (2026-09-07, ÉN harness) — se
  «Liveness-vakt (TODO 250C)» under for `live.mode`s per-sesjon-fastsettelse og den målte
  normaltilstanden.
- **Som for `floor=`:** TILSTEDEVÆRELSE er ikke bevis for at skriptet faktisk ble kjørt.
- Presedens-formulering: **samme felt som `selector=`/`floor=`/`auto_decided=`** — ALDRI referert ved
  feltnummer (nummeret er omstridt og eies av TODO 210, CF-246-1/CF-246-2).

**`vblock=<ok|stale|missing|legacy|stuck>` (TODO 252 — gate F, samme frittekst-felt):** semantikken
står i Gate F-seksjonen under («Telemetri»). Samme fraværs-klasse som `attest=`/`pipelined_from=` —
fravær er IKKE et kontraktbrudd i denne releasen.

**`live=<verdi>` — samme frittekst-felt som `selector=`/`floor=`/`auto_decided=`/`attest=`/
`vblock=`, ALDRI referert ved feltnummer (TODO 210, samme presedens som `attest=` over). Gyldige
tokener — UTEN semantikk her, for å unngå to kilder til samme mapping: semantikken og den ENESTE
bindende mappingen fra maskinlest tilstand til token står i «Liveness-vakt»-seksjonen pkt. 3
under.**

- `live=ledger`
- `live=ledger:unsafe`
- `live=worktree`
- `live=unavailable:no-signal`
- `live=unavailable:probe-failed`
- `live=unavailable:key-unreadable`
- `live=none`
- `live=script-error`

**Nøyaktig ÉTT `live=`-token per rad.** `outcome=health`-rader bærer den ALDRI. Fravær er IKKE et
kontraktbrudd i denne releasen — samme klasse som `attest=`/`vblock=`, ikke som
`floor=`/`auto_decided=`.

### Kontrakt-vakt (TODO 250B)

`--strict` OG `--require-attestations` gis av SAMME session-predikat — én bryter, ikke to, slik at
en sesjon aldri kan få en delvis armert vakt.

**Session-predikatet er sant når ALLE FIRE er sanne** (målt ÉN gang ved sesjonsstart, sammen med
`T_start`, FØR sesjonens første `git merge origin/{{BASE_BRANCH}}` — se «Forutsetning» øverst i denne fila — og
FRYST for hele sesjonen; re-måles ALDRI senere):

```bash
git show origin/{{BASE_BRANCH}}:.claude/agents/{{PROJECT_NAME}}-code-reviewer.md | grep -c -F 'ATTESTASJONSPÅBUD (TODO 250B)'
```
```bash
git log -1 --format=%ct origin/{{BASE_BRANCH}} -- .claude/agents/{{PROJECT_NAME}}-code-reviewer.md
```
```bash
grep -c -F 'ATTESTASJONSPÅBUD (TODO 250B)' .claude/agents/{{PROJECT_NAME}}-code-reviewer.md
```

- (a) tallet fra første kommando er `≥ 1` — påbudet er faktisk merget til `{{BASE_BRANCH}}`. Les TALLET, ikke
  exit-koden (`grep -c` gir exit 1 ved 0 treff, og 0 treff er her den lovlige default-tilstanden).
- (b) tallet fra andre kommando er MINDRE enn sesjonens `T_start` (registrert i «Forutsetning»-
  blokka). Begge er epoch-sekunder — sammenlign tallene direkte, ingen dato-parsing. Finnes ingen
  registrert `T_start`, er ledd (b) USANT.
- (c) tallet fra tredje kommando er `≥ 1`, kjørt UTEN `git show`, i koordinatorens EGET arbeidstre —
  den fila `Agent`-verktøyet faktisk laster charteret fra. (a)/(b) måler `origin/{{BASE_BRANCH}}`, som er en
  PROXY: en sjekkut som ligger bak `origin/{{BASE_BRANCH}}` kan ha et charter uten påbudet mens (a) og (b) begge
  er sanne.
- (d) alle tre målingene (a)–(c) ble utført FØR sesjonens FØRSTE `git merge origin/{{BASE_BRANCH}}` (i
  «Forutsetning»-blokka, sammen med `T_start` — ikke først når denne seksjonen leses). Et ledd som
  ikke ble målt i tide teller aldri som oppfylt.

**Finnes ingen registrert sesjonsstart-epoch, er predikatet USANT og form A kjøres** — et ledd som
ikke ble målt teller aldri som oppfylt.

**Form B — den armerte CLI-formen**, som ÉN linje i en fenced blokk, kolonne 0, uten backticks:

```bash
python3 tasks/review-fan-in-verify.py --fan-in <scratch>/fan-in.json --pr-head-sha <sha> --strict --require-attestations
```

Er predikatet usant, brukes **form A** (den som allerede står i «Invokasjon»-avsnittet over)
uendret. De to formene skilles LITERALT — se «Invokasjon» og planens V17-gate.

**Ærlig merking.** Alle kodene i `BINDING_CODES` er FORM-sjekker på felter revieweren selv fylte. De
beviser at kontrakten er overholdt, aldri at en lens faktisk kjørte. R12 (`premature-return`,
TODO 250C) dekker DELER av opphavsspørsmålet — se «Liveness-vakt»-seksjonen under for hva den måler
og hva den IKKE måler. `input-unreadable` (R1) er IKKE i `BINDING_CODES`. Den måler `--fan-in`-fila, som du selv
skrev — ikke et felt revieweren fylte. Er fila uleselig: ekstrahér `fan_in` på nytt ÉN gang. Er den
fortsatt uleselig, gjelder den BINDENDE runbook-regelen «manglende `fan_in` ⇒ usignert» (over) —
forkast og dispatch fersk. **R1 teller aldri mot A0-eskaleringen**, uavhengig av antall ganger den
fyrer.

**`reviewed_sha`-utveien.** R10 sjekker KUN attestasjoner der `reviewed_sha` normaliserer til minst
7 hex-tegn. `null` og ikke-normaliserbare verdier hoppes og føres i `signals.skipped[]` som
`R10:unnormalizable:<agent>`. Det betyr at en reviewer som skriver `null` alltid passerer R10. Det
er en KJENT og AKSEPTERT utvei i denne releasen: `null` er per `report-schema.md` lovlig og betyr
«lensen oppga ingen SHA», og koordinatoren har i denne PR-en ingen måte å skille de to tilfellene på.
Å gjøre en ikke-normaliserbar verdi stoppende ville bare lært revieweren å skrive `null` i stedet.
Lukking krever et opphavs-signal og eies av CF-250B-6. Les derfor `signals.skipped[]` — ikke bare
`violations[]`.

**Avvisnings-prosedyren — ingen ventetilstand noe sted.** Alt evalueres i koordinatorens egen tur i
det rapporten ankommer.

| Utfall | Handling | Teller | Eskalering |
|---|---|---|---|
| exit 0 med R1 (`input-unreadable`) i `violations[]` | Re-ekstrahér `fan_in`-objektet ÉN gang. Fortsatt uleselig ⇒ den BINDENDE regelen «manglende `fan_in` ⇒ usignert» gjelder | Teller IKKE som kode-review-runde | **ALDRI A0** — R1 måler koordinatorens egen fil |
| exit 3 pga. R2–R5/R10/R11 | Rapporten behandles som USIGNERT — forkast + dispatch fersk kode-reviewer umiddelbart, med bruddkoden sitert ordrett i prompten | Teller IKKE som kode-review-runde | **ANDRE forekomst av SAMME bruddkode i samme §5b-runde ⇒ nivå A0**, release claim, eskalér. Maks **2** re-dispatcher per §5b-runde, deretter A0. `input-unreadable` teller ikke med |
| exit ≠ 0/3 | `attest=script-error`, fortsett uten å blokkere | — | — |

**Ingen avvisning teller mot revise-budsjettet.**

**Av-armings-stien.** Mistenker du at vakten avviser ÆRLIGE rapporter, kan du foreslå å
**av-arme den for resten av sesjonen** — men av-arming er i dag et **nivå A0**-utfall i
`decision-level.py`, ikke et nivå B-valg (TODO 250B — `python3 tasks/decision-level.py
--event contract_guard_disarm --context decision_logged=yes` gir `{"level":"A","rule":"A0"}`, exit
`1`, fordi ingen B-regel matcher hendelsen ⇒ fail-closed). ⚠️ Dette er nivå A0 — **release claim og
eskalér til mennesket** før du av-armer. Får du go i en senere sesjon: kjør form A i alle gjenstående §5b-runder (`attest=` uten
`strict:`-prefiks, som da også er telemetrien som viser at vakten var av), og skriv én linje i
`decision-log.md` med grunnen og bruddkoden som utløste det. CF-250B-9 eier å innføre en dedikert
B-regel for denne stien; inntil den finnes, er av-arming en A-hendelse. Permanent av-arming gjøres
ved å fjerne kanari-strengen
`ATTESTASJONSPÅBUD (TODO 250B)` fra kode-reviewer-charteret i en EGEN PR (da blir ledd (a) og (c)
usanne av seg selv, og alle framtidige sesjoner kjører form A) — aldri ved å redigere skriptet eller
runbooken midt i en runde.

### Liveness-vakt (TODO 250C)

Worktree-semantikken er harness- OG rolleavhengig. `live.mode` er derfor en **per-sesjon**-verdi
koordinatoren fastsetter på nytt hver sesjon, ALDRI en konstant i koden.

**1. Per-sesjon-fastsettelsen — GRATIS, ingen probe.** Default er `unavailable`. Oppgradering er
KUN lovlig på en BEKREFTET observasjon i DENNE sesjonen:

- `ledger` krever at koordinatoren faktisk mottok task-notifikasjoner for lensene i denne sesjonen,
  ført ordrett i `<scratch>/lens-ledger.txt`, og at ledgeren er ikke-tom NÅR rapporten ankommer. Tom
  ledger ⇒ `unavailable`, aldri `ledger`.
- `worktree` krever i tillegg `isolation: worktree` på lens-charterne (⇒ `lens_isolation: "own"`) OG
  at et mid-snapshot faktisk er mulig. **Ingen av delene er sanne i dag.**
- **Uregistrert ⇒ `unavailable`.** Et ledd som ikke ble målt teller aldri som oppfylt (samme
  fail-open-form som kontrakt-vaktens session-predikat).

**2. Invokasjon — INGEN tredje frossen CLI-form.** `--live-key <scratch>/live-key.json` legges til
som siste argument på den formen session-predikatet allerede valgte (form A eller form B) — se
«Invokasjon»-avsnittet og planens entydighets-invariant. Nøkkelfila skrives av koordinatoren, fra
EGNE `git worktree list`-snapshots og EGNE task-notifikasjoner — ALDRI avledet fra rapportens egen
`evidence`.

**3. `live=`-tokenet — uttømmende mapping fra maskinlest tilstand.** Les ALDRI tokenet av
`signals.skipped[]`s form alene (bar vs. kvalifisert bekrefter ikke ALENE hvilket token som gjelder)
— bruk denne tabellen:

| Maskinlest tilstand | `live=`-token |
|---|---|
| `signals.live == "none"` (ingen `--live-key` gitt denne runden) | `live=none` |
| `signals.live == "unavailable"` OG `R14` (`live-key-unreadable`) i `violations[]` | `live=unavailable:key-unreadable` — kilden er `violations[]`, ALDRI en gjetning |
| `signals.live == "unavailable"`, INGEN `R14`-brudd, OG denne sesjonens probe (pkt. 1) var GYLDIG men ga ingen ekte signal | `live=unavailable:no-signal` — den målte tilstanden i denne harnessen (2026-09-07) |
| `signals.live == "unavailable"`, INGEN `R14`-brudd, OG denne sesjonens probe var UGYLDIG (`dispatched == []`) | `live=unavailable:probe-failed` |
| `signals.live == "ledger"` OG koordinatorens pkt. 1-fastsettelse var OPPFYLT denne runden | `live=ledger` |
| `signals.live == "ledger"` MEN vakten senere viste seg å avvise en ÆRLIG rapport (pkt. 6, auto-demotering) | `live=ledger:unsafe` |
| `signals.live == "worktree"` | `live=worktree` |
| skriptet exit'et ≠ 0/3 (krasj/bruksfeil) | `live=script-error` — koordinator-skrevet, ALDRI prefikset |

`:no-signal` og `:probe-failed` kommer BEGGE fra koordinatorens EGEN rad-fastsettelse (pkt. 1) — ikke
fra skriptets JSON, som ikke skiller de to. `:key-unreadable` kommer fra `violations[]`. Denne
tabellen er den ENESTE kilden til `live=`-tokenet; se «Utfallstabellen per brudd-kode» i pkt. 4
UNDER for `signals.skipped[]`-formene, som svarer på et ANNET spørsmål (hvorfor R12 ikke fyrte).

**Rad-nummerering — tre IKKE-sammenfallende systemer.** Denne tabellen omtaler tilstander i prosa,
ikke med et rad-nummer. Skriptets `D1.3`-kommentarer i `evaluate()` bruker en annen nummerering
(`rad 0`, `0b`, `1`, `2`, `3`, `8`, `10`, `11` — én per evaluerte gren i koden), og planens
verifiseringsblokk kan bruke en tredje. Referer ALLTID til en tilstand ved dens `signals.live`-verdi
+ brudd-/hopp-kode (som i tabellen over), ALDRI ved et bart rad-nummer alene — et rad-nummer uten
kildeangivelse er tvetydig på tvers av disse tre.

**4. Utfallstabellen per brudd-kode — ingen ventetilstand noe sted.** Alt evalueres i koordinatorens
egen tur i det rapporten ankommer. Re-dispatch-budsjettet i denne raden er DET SAMME, FELLES
budsjettet som «Kontrakt-vakt (TODO 250B)»s avvisnings-prosedyre bruker — maks **2** re-dispatcher
totalt per §5b-runde, på tvers av BEGGE tabellene, ikke 2 hver:

| Utfall | Handling | Teller | Eskalering |
|---|---|---|---|
| exit 3 pga. R12 (`premature-return`) — kun mulig når `live.mode = ledger` | Rapporten er USIGNERT: forkast + dispatch fersk kode-reviewer umiddelbart, med `premature-return` og de manglende agentnavnene sitert ordrett i prompten | Teller IKKE som kode-review-runde | Tredje forekomst (denne raden ELLER kontrakt-vaktens rad, til sammen) i samme §5b-runde ⇒ nivå A0 — **release claim og eskalér** |
| exit 0 med R14 (`live-key-unreadable`) i `violations[]` | Skriv `live=unavailable:key-unreadable`, hopp R12, fortsett uten å blokkere. Nøkkelfila er din egen | Teller IKKE | ALDRI A0 |
| `R12` i `signals.skipped[]` (kvalifisert grunn) | Normaltilstanden. Skriv `live=<token fra pkt. 3>` og fortsett | — | — |
| `R12` i `signals.skipped[]` i BAR form | To ulike årsaker: ingen `--live-key` ble gitt, ELLER `--fan-in` var uleselig (R1) og kortsluttet hele regelsettet. Les `live=`-tokenet fra pkt. 3-tabellen, ALDRI fra denne formen alene — `signals.live` er `"none"` i det første tilfellet og nøkkelfilas `mode` i det andre | — | — |
| `R12` verken i `violations[]` eller i `signals.skipped[]` | Regelen KJØRTE og fant ingenting — et POSITIVT resultat. Skriv `live=<token fra pkt. 3>` og fortsett. Ikke let etter en skipped-oppføring som ikke skal finnes | — | — |

**5. Absolutt timeout.** Ingen ventetilstand er foreskrevet. Utløper den absolutte timeouten (ETT
koordinator-tur): skriv `live=unavailable:no-signal`, hopp R12 og gå videre — aldri en tur til.

**6. Auto-demotering — men den er NIVÅ A, ikke en koordinator-handling.** Første gang du avviser en
rapport på R12 og selv vurderer rapporten som ÆRLIG, demoteres vakten til `mode: "unavailable"` for
resten av sesjonen. Men handlingen er ikke din: `python3 tasks/decision-level.py --event
liveness_guard_disarm --context decision_logged=yes` gir `{"level": "A", "rule": "A0", …}`, exit `1`
— av-arming av en vakt er en UKJENT hendelse og faller til A0 fail-closed. Skriv **`live=ledger:unsafe`**
på raden, ikke skriv nøkkelfila på nytt, og la mennesket avgjøre om vakten skal av-armes via
**release claim og eskalér**. «Logg det og gå videre» er eksplisitt IKKE lov. Denne stien er
uoppnåelig i dette prosjektet i dag (R12 fyrer kun i `mode=ledger`, som er målt uoppnåelig, pkt. 7) —
den står her fordi fila er en TEMPLATE og shippes til prosjekter der `mode=ledger` ER oppnåelig.

**7. Den målte tilstanden, datert.** Målingen 2026-09-07 i DETTE prosjektet ga `live.mode =
unavailable` (`live=unavailable:no-signal`) — worktree-signalet er målt DØDT, ikke bare umålt: en
nestet lens arver reviewerens worktree i stedet for å få sitt eget. `isolation: worktree` på
lens-charterne er det eneste kjente inngrepet som kan gjøre `mode=worktree` oppnåelig. Denne
observasjonen er HARNESS-BETINGET, ikke universell — fila er en template.

### Fix-mode-dispatch-mal (revise-runde)

**Commit-melding (BINDENDE, gjelder OGSÅ koordinator-utførte fix-runder).** Emnelinja i hver
fix-runde-commit MÅ inneholde `fix-runde <N>`. Grensen mellom rundene finnes ikke lagret noe annet
sted: `{{BASE_BRANCH}}` squash-merger (målt 58 av 60 siste commits har én forelder), så
`gh api repos/{owner}/{repo}/pulls/<n>/commits` er eneste overlevende kilde — og den er kun nyttig
hvis emnelinja bærer rundenummeret. Målt 2026-09-10: konvensjonen fulgtes uskrevet i 5 av 5 PR-er
med flere commits, men med hull der runder manglet nummer (196A: 4 av 5 funnet, 236: 1 av 2).
En koordinator-utført runde har ingen implementer å pålegge dette — koordinatoren skriver den selv.


**Pre-dispatch-snapshot (§0b vakt 5, R21) — umiddelbart FØR `Agent`-blokken under. Hver fix-runde
er en NY implementer-worktree (K4) og får derfor sin EGEN fil:**
```bash
git worktree list --porcelain > "<scratch>/wt-pre-5b-fixmode-<runde>.txt"
```
Sjekk exit-koden med det samme; ikke-null ⇒ noter paret som `snapshot-missing`.

`Agent`: `subagent_type: {{PROJECT_NAME}}-implementer`. Prompt:

> FIX-MODE for TODO `<nr>`. Du har ALLEREDE implementert denne og laget PR `<pr_url>` på branch `<branch>`. IKKE re-implementer og IKKE kjør `todo-execute.md` på nytt. Gjør KUN dette: (1) `git fetch origin <branch> && git checkout <branch>` og `git fetch origin {{BASE_BRANCH}} && git merge origin/{{BASE_BRANCH}}` for å bygge på ferskeste delt state før re-push (konflikt i planfila: behold BEGGE siders fix-runde-seksjoner, aldri `--ours`/`--theirs` på hele fila); (2) rett UTELUKKENDE disse kode-review-funnene: `<liste med severity + file:line + issue + fix>`; (2b) **SANNHETSKRAV FOR NY TEKST (BINDENDE).** Endrer eller legger du til en brukersynlig streng eller en kodekommentar som PÅSTÅR noe om systemets tilstand eller oppførsel: før du skriver den, finn ALLE kodeveier som når linja, og skriv ordrett i ferdig-rapporten (i) hvilke skriveoperasjoner som ALLEREDE er utført når linja emitteres, og (ii) hvilke som IKKE er det. Teksten må være sann på HVER slik vei — er den sann på én gren og usann på en annen, er den en defekt, ikke en unøyaktighet. Gjelder særlig feilmeldinger i en flerstegs skrivekjede uten transaksjon («ingenting ble lagret» er usant hvis steg 1 av 3 gikk gjennom) og kommentarer skrevet i presens om invarianter som ikke lenger holder. Bruker du en delt mapper/hjelpefunksjon, sjekk også at den nye grenen ikke kaprer kallstedets egen tekst; (3) kjør `{{CMD_BUILD}}` + `{{CMD_TYPE_CHECK}}` + relevante tester på nytt; (4) **re-kjør HELE V-blokken i planen mot HEAD og lim ordrett kommando + output inn i planfilas `#### V-blokk re-kjørt mot HEAD (fix-runde <N>)`-seksjon, med hvert `**V<id>**` på egen linje ved linjestart og minst én fenced kodeblokk under hvert, og med attestasjonslinjen ORDRETT til slutt: Ingen tall arves fra en tidligere runde. Rundens lesson-kandidater skrives i samme seksjon**; (5) `git push` til samme branch (samme PR — IKKE ny PR, IKKE ny `gh pr create`); (6) returner oppdatert ferdig-rapport. Rør ingenting utenom de oppgitte funnene (unntak: planfilas fix-runde-seksjon, jf. steg 4).

**Akkumulering + bevaring (peker, ikke kopi):** samme regel som §5, «Akkumulering for §6s
rydding»/«Bevaringsregel ved abort» — denne fix-runden er en NY implementer-worktree (K4) og
akkumuleres i SAMME liste med sitt eget PAR (`evidence.toplevel`, denne rundens
`wt-pre-5b-fixmode-<runde>.txt`).

### Gate F — V-blokk-re-verifisering (BINDENDE)

Kjøres av koordinatoren når fix-rapporten er mottatt og **FØR** kode-review r(N+1) dispatches.
`<N>` = fix-rundenummeret. Én kommando per kall (worktree-vakten avviser sammensatte git-kommandoer
og shell-aritmetikk); alle sammenligninger gjøres ved å LESE tallene, aldri med `$(( ))`. Alle
awk-programmer er **literale** — aldri i en shell-variabel (`awk "$PROGRAM"` avvises).

**Steg 0 — snapshot FØRST.** Planfila er BRANCH-EID fra §5-dispatch til merge (se planfil-eierskapet
under); koordinatorens arbeidskopi har derfor ALDRI seksjonen. To egne Bash-kall:

```bash
git fetch origin <branch>
```
```bash
git show origin/<branch>:tasks/plans/todo-<nr>-<slug>.md > <scratch>/plan-<N>.md
```
Feiler `git show` (fila finnes ikke på branchen) ⇒ `vblock=missing`, mekanisk retur.
**ALLE kommandoene under leser `<scratch>/plan-<N>.md` — også F3a-gulvet.** Bland aldri dev-kopien
og branch-snapshotet. Snapshotet skrives til `<scratch>`, ALDRI til en repo-relativ fil.

```bash
grep -c '^```' <scratch>/plan-<N>.md
```
F0: total fence-paritet. Må være **PARTALL**. Odde ⇒ RØD (`vblock=stale`).

```bash
awk '/^```/{c=!c;next} !c' <scratch>/plan-<N>.md | grep -c '^#### V-blokk re-kjørt mot HEAD (fix-runde <N>)$'
```
F1: les TALLET. Må være nøyaktig `1`.

```bash
awk '/^```/{fc=!fc} !fc&&/^#### V-blokk re-kjørt mot HEAD \(fix-runde <N>\)$/&&!seen{seen=1;f=1;next} f&&/^```/{c=!c} f&&!c&&/^#+ /{f=0} f' <scratch>/plan-<N>.md > <scratch>/vblock-<N>.txt
```
F2: vindusuttrekk. `fc` gjør START-ankeret fence-bevisst; `!seen` låser til FØRSTE ekte forekomst;
`c` gjør TERMINATOREN fence-bevisst; terminatoren er `^#+ `. **Awk-programmet står på ÉN linje.**

```bash
grep -c '^```' <scratch>/vblock-<N>.txt
```
F2b: fence-telling i vinduet. Må være **PARTALL** og **≥ 2**.

```bash
awk '/^```/{c=!c;next} c&&NF' <scratch>/vblock-<N>.txt | wc -l
```
F2c: antall ikke-fence, ikke-tomme linjer INNE i fencene i vinduet — reelt kommando-/output-innhold,
ikke bare balanserte fence-par. Må være **≥ 2 × F3b** (F3b lest fra kommandoen under). Uten F2c
består en seksjon med tomme fence-par F1, F2b og F4 samtidig som den ikke inneholder én eneste
faktisk output-linje.

```bash
awk '/^```/{fc=!fc} !fc&&/^## .*[Vv]erifisering/&&!seen{seen=1;f=1;next} f&&/^```/{c=!c} f&&!c&&/^#{1,2} /{f=0} f' <scratch>/plan-<N>.md | grep -oE '^((\| )?\*\*V([0-9]|-[A-Z])[0-9A-Za-z-]*\*\*|#{3,6} V([0-9]|-[A-Z])[0-9A-Za-z-]*)' | sed -E 's/^(#{3,6} |\| )?\*{0,2}//; s/\*{0,2}$//' | sort -u | wc -l
```
F3a: **gulvet** — antall **DISTINKTE** V-kriterier i planens verifiseringsseksjon, telt med `sort -u`
(symmetrisk med F3bs dedup — uten det kunne samme V-ID gjentatt i tabellform inflatere gulvet uten å
dekke flere distinkte kriterier). Start-ankeret er fence-bevisst og låst med `!seen`. Terminatoren er
**`^#{1,2} `, IKKE `^#+ `**. Regexen teller BÅDE tabellrader og linjestart-form, slik at gulvet virker
også for planer skrevet før dette formatkravet.

**Overskrifts-formen (rettet 2026-09-10).** Regexen matchet opprinnelig KUN fet form (`**V1**`,
`| **V1**`) og var blind for `### V1 — …`, som er en helt ordinær markdown-form. TODO 236s plan
bruker den formen: F3a ga **0** for 13 reelle kriterier, og runbookens egen tolkning av 0 er
`vblock=legacy` — «skrevet før formatkravet, gulvet ikke bindende». Gate F ville altså slått av sitt
eget gulv i stille, på en plan skrevet samme dag. Alternasjonen over dekker begge former, og
`sed`-en normaliserer til bar V-ID så `sort -u` ikke teller `### V4` og `**V4**` som to. **Målt
bakoverkompatibel:** TODO 296 `26 → 26`, TODO 289 `7 → 7`, TODO 267 `17 → 17`, TODO 236 `0 → 13`.
Dette er samme defektklasse som `tasks/todos/todo-281-gate-f-teller-literaler-ikke-klasser.md`
beskriver: en detektor som leter etter én skrivemåte i stedet for én klasse.

**Gulv-låsen (BINDENDE).** Ved §5-dispatch noterer koordinatoren `F3a_ref` = samme kommando kjørt mot
planfila den dispatchet, og bærer tallet i kontekst sammen med `<N>`-telleren. I hver fix-runde:

- `F3a ≠ F3a_ref` ⇒ **RØD** (`vblock=stale`). Implementerens carve-out dekker KUN fix-runde-seksjoner
  — F3a låser ANTALLET V-kriterier, ikke innholdet i § 6. En innholdsendring som bevarer antallet
  oppdages IKKE av gate F (innholds-hash er en åpen oppfølging, se CF-252-12).
- `F3a_ref = 0` ⇒ **`vblock=legacy`**: planen er skrevet før dette formatkravet. Gulvet (`F3b ≥ F3a`)
  er da IKKE bindende, men **F0, F1, F2b, F2c ≥ 2 × F3b, F3b ≥ 1, fences ≥ 2 × F3b, F4 og F5 (inkl.
  F5:none-regelen under) er fortsatt bindende**. Verken rød eller grønn — samme overgangsklasse som
  `attest=legacy` (se `attest=`-blokka i §5b for når den verdien oppstår).

```bash
awk '/^```/{c=!c;next} !c' <scratch>/vblock-<N>.txt | grep -oE '^\*\*V([0-9]|-[A-Z])[0-9A-Za-z-]*\*\*' | sort -u | wc -l
```
F3b: antall **DISTINKTE** V-ID-er i fix-runde-seksjonen — kun linjestart-form, kun utenfor
kodeblokker, telt med `sort -u`. Samme ID gjentatt flere ganger teller ÉN gang. Uten fence-filteret
teller limt § 6-tekst med. Må være **≥ 1**, og **≥ F3a** når `F3a_ref > 0`.

Fence-tellingen fra F2b OG innholdstellingen fra F2c må begge være **≥ 2 × F3b** — lest mot dette
(distinkte) F3b-tallet.

```bash
awk '/^```/{c=!c;next} !c' <scratch>/vblock-<N>.txt | grep -c -F 'Ingen tall arves fra en tidligere runde.'
```
F4: det frosne ankeret, kun utenfor kodeblokker. Må være **≥ 1**. `grep -F` er case-sensitiv.

**F5 — stikkprøve (BINDENDE, kjøres i et engangs-tre).** F1–F4 kan oppfylles av en implementer som
limer GAMLE tall inn i nye kodeblokker; F5 kan ikke.

```bash
git worktree add <scratch>/pr-<N> origin/<branch>
```
Velg **ÉN** V-kommando fra seksjonen, KUN blant kriterier planen har merket **`(F5-kvalifisert)`** —
rene lesekommandoer (`grep`, `awk`, `wc`, `git grep`, `git diff --name-only`), uten `$SP`-referanse,
og som ikke er bygg/test/e2e eller `/setup`. Velg den hvis tall ENDRET seg siden forrige runde,
ellers den første kvalifiserte. Kjør den ORDRETT med `<scratch>/pr-<N>` som cwd, og noter output.

**Rydd UBETINGET, FØR utfallet vurderes** — treet skal fjernes uansett om F5 lander grønn eller rød,
ellers etterlater en rød F5 et lekkende engangs-tre:

```bash
git worktree remove <scratch>/pr-<N> --force
```

Sammenlign SÅ output mot planens: avvik ⇒ samme utfall som en rød F1/F3/F4.

**Etterprøvbarhet:** logg hvilken V-ID du valgte i felt 11 (`vblock=ok(F5:V4)`). Finnes det ingen
`(F5-kvalifisert)`-kommando i seksjonen MEN `F3b ≥ 1`, velg i stedet **hvilken som helst kommando i
seksjonen** som fallback — dette dekker også en planer-kontrakt som ikke merker noen kriterier som
kvalifisert. Finnes fortsatt ingen kjørbar kommando å velge, er det **RØD** (`vblock=stale`, årsak
`F5:none`). `F5:none` er ALLTID RØD — med `F3b ≥ 1` via Utfall-klausulen under (`F5-avvik, inkl.
F5:none når F3b ≥ 1`), med `F3b = 0` fordi `F3b < 1` selv er rødt (jf. «Utfall» under) —
`vblock=ok(F5:none)` skal aldri skrives.

**Utfall.** Bryter ett av kravene (F0 odde; F3a ≠ F3a_ref; F1 ≠ 1; F2b odde eller < 2;
`F2c < 2 × F3b` (distinkt); F3b < 1; F3b < F3a når `F3a_ref > 0`; fences < 2 × F3b; F4 = 0;
F5-avvik, inkl. `F5:none` når `F3b ≥ 1`) ⇒ **fix-runden er ikke fullført**. Send den tilbake som en
**MEKANISK retur**: samme funn-liste, ingen ny review, og implementeren **ERSTATTER** seksjonen for
SAMME `<N>` (ikke ny seksjon, ikke `<N>+1`). En mekanisk retur bruker verken opp en revise-gate-runde
eller et trinn i modell-eskaleringens fix-rundetelling. Dispatch ALDRI kode-review r(N+1) på en rød
gate F.

**Øvre grense på mekaniske returer.** Etter **2** mekaniske returer på samme `<N>` er dette **nivå
A0 — eskalér til mennesket** med gate F sin ordrette output for alle tre forsøkene, og logg
`vblock=stuck` i felt 11.

**Fix-runde 0 finnes ikke som gate.** `<N>` starter på **1** ved den FØRSTE kode-review-drevne
fix-runden. Implementeringsrunden (r0) produserer ingen `#### V-blokk re-kjørt mot HEAD`-seksjon, og
koordinatoren kjører IKKE gate F på den.

**Telemetri.** Skriv `vblock=<ok|stale|missing|legacy|stuck>` i `run-log.md` felt 11, ved siden av
`selector=`/`floor=`/`auto_decided=`/`attest=`. `ok` = alle passerte i første forsøk;
`stale` = én eller flere rødnet og runden ble sendt mekanisk tilbake; `missing` = seksjonen eller
snapshotet fantes ikke; `legacy` = `F3a_ref = 0` (gulvet ikke bindende, resten passerte);
`stuck` = 2 mekaniske returer på samme `<N>`, eskalert. Legg alltid F5s valgte V-ID i parentes:
`vblock=ok(F5:V4)`. Én rad kan bære flere fix-runder — skriv da
`vblock=ok(F5:V4),stale(F5:V2)` i rundenes rekkefølge. **Fravær er IKKE et kontraktbrudd** i denne
releasen (samme klasse som `attest=`/`pipelined_from=`, ikke som `floor=`/`auto_decided=`).

**Modell-eskalering fra fix-runde 3 (nivå B).** Fix-runde 1 og 2 dispatches med
`models.implementer`. **Fix-runde 3 og senere** — den ekstra runden utover 2/2 og enhver
A0-godkjent runde etter den — dispatches med prosjektets DYPE modell
(`models.reviewer`/`models.code_reviewer`-klassen i `loop.config.yaml`), ikke `models.implementer`.
Mekanismen er en per-dispatch modell-override i `Agent`-blokken; charterets `model:`-frontmatter
står uendret (den leses ved sesjonsstart, ikke per dispatch). **Mekaniske gate F-returer teller
IKKE med i fix-rundetallet** — bare review-drevne fix-runder gjør det. **Støtter ikke
dispatch-verktøyet en per-kall-override, er dette nivå A0 — eskalér til mennesket. ALDRI stille
fallback til `models.implementer`.** Logg avviket i `run-log.md` felt 9 på formen
`<rask>(r1-rN)+<dyp>(fix rN+1, modellavvik)`, og som nivå-B-entry i `decision-log.md`.

**Re-vurdering.** Regelen re-vurderes etter **5** MERGE-rader med gate F i drift. Tell KUN
`merged`-rader ETTER denne todoens egen merge-rad, og `paused`-rader for samme todo teller ikke:
`awk '/\| <nr> \|/ && /\| merged \|/{f=1;next} f' docs/superpowers/loop/run-log.md | grep -c 'vblock='`
Les TALLET, ikke exit-koden. **Fjern eskaleringen KUN dersom minst 3 av de 5 er `ok`-rader fra
planer MED bindende gulv** (`vblock=ok`, ikke `vblock=legacy`) — `vblock=legacy`-rader teller med i
de 5, men er svakere datagrunnlag (gulvet var ikke bindende der); noter forholdet `ok`/`legacy` i
re-vurderingen. En eneste `vblock=stuck` er i seg selv grunn til å re-åpne gate F-designet,
uavhengig av modell-spørsmålet.

**Planfil-eierskap:** se §3-overleveringen («Planfil-eierskap ved §3-overleveringen») — planfila er
BRANCH-EID fra §5-dispatch til merge, og koordinatoren `cp`-er den aldri over i mellomtiden.

## 5c. Pipelining (plan neste todo mens denne implementeres)

**Trigger:** når du dispatcher §5-implementeren for todo **A**. Seksjonen står mellom §5b og §6
fordi den er et parallell-spor, ikke et steg i A-sekvensen: den starter ved §5-dispatch og løper til
B claimes eller loopen stopper.

**Tak (`loop.config.yaml`).** `pipelining.max_in_flight` er taket for hvor mange todos som kan ligge
i pipeline (plan påbegynt, ikke claimet) samtidig. Nøkkelen er valgfri; mangler den, er verdien `0`.
Verdien i dette prosjektet er `{{PIPELINE_MAX_IN_FLIGHT}}`. Er den `0`, er pipelining slått av og
hele §5c hoppes over. Med `1` pipelines nøyaktig én todo per runde, og taket nås normalt ikke — men
blir en B forbigått (se «Kø-stabilitet» under) og beholder planen sin, kan antallet u-claimede
planer i praksis overstige taket; det er akseptert i trinn 1. Trinn 2 (parallelle implementere,
§5d) hever IKKE dette taket — det claimer B i stedet for å pipeline en tredje todo, så antallet
u-claimede planer går mot 0 og taket forblir `1`. Taket finnes for
koordinator-konteksten, ikke for maskinen: plan- og review-rapportene for B lander i samme sesjon
som A-arbeidet.

**Mekanikk: parvis dispatch i ÉN melding — det finnes ingen «bakgrunn».** Parallelle subagenter
kjøres ved å sende flere `Agent`-blokker i SAMME melding; meldingen returnerer først når alle
blokkene i den er ferdige. Pipelining er derfor to par:

- **Par 1 (én melding):** `§5 implementer(A)` + `§3 planner(B)`.
- **Par 2 (én melding):** `§5b kode-reviewer(A)` + `§4 reviewer(B)`.

**Pre-dispatch-snapshot for par 2 (§0b vakt 5, R21) — rett før par 2 dispatches, ETT nytt sett,
ALDRI par 1s fil gjenbrukt:** par 1s worktrees (implementer(A), planner(B)) er per konstruksjon
fortsatt registrerte når par 2 dispatches, så par 1s snapshot ville avvist BEGGE som `preexisting`.
Kode-reviewer(A) bruker `<scratch>/wt-pre-5b-code-reviewer-<runde>.txt` (se §5b, «Review-dispatch»)
og reviewer(B) bruker `<scratch>/wt-pre-4-plan-reviewer-<runde>.txt` (se §4) — begge tatt PÅ NYTT,
rett før DENNE par-2-meldingen sendes, ikke gjenbrukt fra en tidligere runde.

**Par-meldingen returnerer først når BEGGE blokkene er ferdige.** A sin §5b starter derfor tidligst
når planner(B) også er ferdig: pipelining reduserer total tid for to todos, men øker latensen for A
isolert sett. Vent ikke en umiddelbar §5b — det er ikke en hengt agent. Trenger A en fix-mode-runde
samtidig som B trenger en revisjonsrunde, pares de på samme måte. Er det ingenting å pare med på
B-siden, dispatch A-blokken alene.

I det serielle vinduet MELLOM par 1 og par 2 gjør du arbeid på begge spor: for A — §5b sitt
Trigger-sett (`gh pr view --json headRefOid` → `gh api compare` → `tasks/review-lens-select.py`); for
B — uavhengig verifisering av plan-rapporten og commit-halen under.

**FØR par 1 dispatches: fetch én gang selv.**

```bash
git fetch origin {{BASE_BRANCH}}
```

**Pre-dispatch-snapshot for par 1 (§0b vakt 5, R21) — rett etter fetchen over, FØR par 1
dispatches:**
```bash
git worktree list --porcelain > "<scratch>/wt-pre-5c-par1-<runde>.txt"
```
Sjekk exit-koden med det samme; ikke-null ⇒ noter paret som `snapshot-missing`. **Denne filen er
BÅDE planner(B)s pre-snapshot for §0b-kallet lenger ned i denne seksjonen OG — i pipelinet modus —
implementer(A)s pre-snapshot for §6s rydding:** siden implementer(A) dispatches herfra og ikke fra
§5, finnes det ingen egen `wt-pre-5-implementer-`-fil for A i pipelinet modus. Koordinatoren
akkumulerer derfor paret (A sin `evidence.toplevel`, DENNE filen) inn i §6s liste på nøyaktig samme
måte som §5 gjør i den ikke-pipelinede grenen (se §5, «Dispatch implementer», og §6 steg 4).

Noter `F3a_ref` = F3a-kommandoen (gate F, §5b) kjørt mot planfila du nå dispatcher; bær tallet i
kontekst sammen med `<N>`-telleren.

Worker-worktreene er LINKEDE worktrees mot en delt `--git-common-dir`. Begge workerne i par 1 åpner
Steg 0 med `git fetch origin {{BASE_BRANCH}} && git merge origin/{{BASE_BRANCH}}`. To samtidige
fetches konkurrerer om `refs/remotes/origin/{{BASE_BRANCH}}.lock`, `FETCH_HEAD` og `packed-refs`;
taperen får ikke-null exit, `&&` kortslutter, merge kjøres ALDRI, og workeren fortsetter STILLE mot
stale state. Din fetch gjør begge workernes Steg 0 til en no-op-fetch mot en allerede fersk ref.

**Par-1-dispatch: legg dette tillegget i BEGGE promptene** (ordrett; det hører til paret, ikke til
charterne):

> Du kjører i et PIPELINET PAR (to workers samtidig, delt git-common-dir). Etter Steg 0, verifiser
> synken før du gjør noe annet: `git merge-base --is-ancestor origin/{{BASE_BRANCH}} HEAD` skal gi
> exit 0. Ikke-null exit betyr at fetch/merge tapte et ref-lock-kappløp — kjør
> `git fetch origin {{BASE_BRANCH}}` og `git merge origin/{{BASE_BRANCH}}` på nytt (hver som eget
> kall), og verifiser igjen. Feiler den andre gangen også: stopp og rapporter, ikke fortsett mot
> stale state.

De to tiltakene MÅ kombineres: uten koordinatorens fetch kan `--is-ancestor` gi falskt grønt mot en
stale ref; uten workerens verifisering blir et tapt kappløp stille.

**Valg av B (uten claim).** Kjør §1-skriptet på nytt rett før par 1. A er allerede claimet og faller
ut av `elig=YES`. Velg øverste `elig=YES` = B. Sett IKKE `claimed_by`, og endre IKKE `status`.

**B beholder `status: open` fram til claim.** Sett ALDRI `status: reviewed` på en pipelinet todo:
§1-skriptets elig-predikat krever `status == 'open'`, så `reviewed` gjør B usynlig for
kø-utvelgelsen — samme klasse som en død claim. Det eneste feltet du skriver på B før claim er
`plan:`.

**Planfila for B committes til `{{BASE_BRANCH}}` FØR par 2 — og det er ikke en claim.**
Plan-revieweren får en helt fersk worktree fra `origin/{{BASE_BRANCH}}` og ser kun det som er
committet og pushet; den vanlige rekkefølgen §3 → delt-state-commit → §4 gjelder derfor også her. En
committet planfil og en `plan:`-peker endrer ingenting i §1s elig-predikat (`status`, `claimed_by`,
`deps`, brainstorm, `tags`) — B står fortsatt `elig=YES` og kan når som helst forbigås. Bruk
EKSPLISITTE stier i denne halen; `git add -A tasks/` ville sveipet med usporede plan-kopier for
andre todos.

**Dette er den første av §5cs TRE push-haler til `{{BASE_BRANCH}}` midt i en todo-runde, før A
er merget** (denne, markør-halen lenger ned og drop-B-halen enda lenger ned). Par 1 har returnert,
så ingen implementer er i flukt — men A sin PR-branch er åpen, og halen stager derfor KUN B sine to
filer. Treffer forhåndssjekken under noe annet, stopp.

```bash
# 0. Forhåndssjekk: ingenting usporet under tasks/plans/ som ikke skal til {{BASE_BRANCH}}
git status --porcelain -uall tasks/plans/

# 1. Speil-guard (identisk med §6 steg 1)
mb=$(git merge-base origin/{{BASE_BRANCH}} HEAD)
non_shared=$(git diff "$mb"..HEAD --name-only | grep -vE '^(tasks/|docs/superpowers/loop/)' || true)
[ -z "$non_shared" ] || { echo "FEIL: HEAD har commits utenfor delt state ($non_shared) — feil branch"; exit 1; }

# 2. Overlevering: kopier B sin planfil fra planner(B)s worktree — ordrett samme form som §3 (a)
cp <wt_path_B>/<plan_path_B> tasks/plans/todo-<B>-<slug>.md || { echo "FEIL: overlevering feilet — ADVARSEL, ingen rydding for planner(B)"; exit 1; }
cmp -s <wt_path_B>/<plan_path_B> tasks/plans/todo-<B>-<slug>.md || { echo "FEIL: cmp -s avvik — ADVARSEL, ingen rydding for planner(B)"; exit 1; }

# 3. Stage KUN B sine to filer — aldri `git add -A tasks/` her
git add tasks/plans/todo-<B>-<slug>.md tasks/todos/todo-<B>-<slug>.md

# 4. Commit — tolerer «ingenting å committe»
git diff --cached --quiet && echo "ingenting å committe" \
  || git commit -m "chore(loop): TODO <B> plan skrevet (pipelinet fra TODO <A>) — <slug>"

# 5. Synk + push
git fetch origin {{BASE_BRANCH}} \
  && git rebase origin/{{BASE_BRANCH}} \
  && git push origin HEAD:{{BASE_BRANCH}}
```

**Overleveringen (steg 2 over) må lykkes FØR `git add` — avvik i `cmp -s` eller manglende kildefil
⇒ ADVARSEL og INGEN rydding for planner(B).** Dette ER bindingen mellom rapport og sti for
planner-rollen (§0b vakt 5b), ordrett samme prinsipp som §3 (a).

**§0b-kall — rett ETTER pushen (steg 5) over, for den OPPRINNELIGE par-1-runden:** kall §0b med
`<rolle> = planner`, `<forventet_fil> = tasks/plans/todo-<B>-<slug>.md`, `<pre_snapshot> =
<scratch>/wt-pre-5c-par1-<runde>.txt`. Par 1 har returnert, så planner(B) er død (R1 vakt 1), og
artefakt-gaten er nettopp blitt oppfyllbar av pushen over. (For påfølgende revisjonsrunder, se
under — `<pre_snapshot>` er DA en annen fil.)

**Revisjonsrunder:** en B-revisjonsrunde re-dispatcher planner(B) ALENE (§4s no-go-gren, «send
funnene tilbake til planner (§3, revisjons-runde)») — IKKE som del av et nytt par-1. Dispatchen
skjer da via §3, og §0bs Inngangsdata-regel gjelder ordrett: `<pre_snapshot>` er fila §3 faktisk
skriver umiddelbart før DEN dispatchen, altså `<scratch>/wt-pre-3-planner-<runde>.txt` (§3s eget
snapshot-mønster, ny `<runde>` per revisjonsrunde) — **ikke** `wt-pre-5c-par1-<runde>.txt`, som er
bundet til den opprinnelige par-1-dispatchen alene og aldri gjenbrukes. Denne halen — og
§0b-kallet i den — kjøres likevel på nytt FØR HVER av B sine par-2-runder, inkludert
§4-revisjonsrunder, men med `<pre_snapshot>` satt til riktig fil for runden:
`<scratch>/wt-pre-5c-par1-<runde>.txt` kun for den opprinnelige runden,
`<scratch>/wt-pre-3-planner-<runde>.txt` for hver etterfølgende revisjonsrunde.

**Eierskap (R20):** denne halen EIER plan-**commiten** for pipelinet B; §3s avsluttende blokk er da
en no-op **for commit-delen**. Motsatt vei eier §3 commiten på den ikke-pipelinede stien. Utvid
DENNE halen — ikke legg til en ny commit et tredje sted. **Overleveringens eierskap, presist:**
`cp` + `cmp -s` står skrevet BEGGE steder — i §3s blokk og i denne halen — fordi halen må kunne
leses selvstendig og fordi `git add` her ellers hviler på et steg som står et annet sted. Kjøres
begge (pipelinet B), er den andre **idempotent**: samme bytes kopieres på nytt og `cmp -s` passerer
trivielt. Invarianten er «**minst én av dem har kjørt før `git add`, og `cmp -s` ga exit 0**» —
ikke «nøyaktig én». Normativ eier per sti: §3 for den ikke-pipelinede, denne halen for den
pipelinede.

**Pipelinet-markør — skrives FØRST etter at §4 ga `go`.** Markøren bærer telemetrien som ellers kun
finnes i denne sesjonens kontekst, slik at en død sesjon ikke tvinger fram en fabrikert
run-log-rad. Bytt `**Status:**`-linja øverst i B sin planfil til:

```
**Status:** pipelinet fra TODO <A> — plan-review go (planner=<modell>, reviewer=<modell>, plan_review_rounds=<n>), ikke claimet
```

Skriv den aldri før `go`: en revisjonsrunde kopierer plannerens versjon over planfila og sletter alt
du la inn før den.

**Markøren committes og pushes STRAKS den er skrevet — en egen, andre commit i halen over.** Uten
dette overlever telemetrien kun i denne sesjonens kontekst og forsvinner ved sesjonsdød — akkurat
det problemet markøren finnes for å løse. Samme 0–4-nummerering og eksplisitt-sti-disiplin som
pre-par-2-halen over (TODO 231 CF-5: markør-halen manglet steg 0 + speil-guard foran `git add`):

```bash
# 0. Forhåndssjekk: ingenting usporet under tasks/plans/ som ikke skal til {{BASE_BRANCH}}
git status --porcelain -uall tasks/plans/

# 1. Speil-guard (identisk med §6 steg 1 / pre-par-2-halen over)
mb=$(git merge-base origin/{{BASE_BRANCH}} HEAD)
non_shared=$(git diff "$mb"..HEAD --name-only | grep -vE '^(tasks/|docs/superpowers/loop/)' || true)
[ -z "$non_shared" ] || { echo "FEIL: HEAD har commits utenfor delt state ($non_shared) — feil branch"; exit 1; }

# 2. Stage KUN markør-fila
git add tasks/plans/todo-<B>-<slug>.md

# 3. Commit — tolerer «ingenting å committe»
git diff --cached --quiet && echo "ingenting å committe" \
  || git commit -m "chore(loop): TODO <B> plan-review go, pipelinet fra TODO <A> — <slug>"

# 4. Synk + push
git fetch origin {{BASE_BRANCH}} \
  && git rebase origin/{{BASE_BRANCH}} \
  && git push origin HEAD:{{BASE_BRANCH}}
```

Denne andre commit-halen MÅ være pushet FØR B claimes — og, i en eventuell senere
revisjonsrunde av B, FØR DEN rundens par 2 (en ny §4-revisjon kopierer plannerens versjon over
planfila og sletter markøren igjen, se over). Den skal IKKE pushes før DENNE rundens par 2: B sin
plan-reviewer skal per konstruksjon IKKE se markøren — å pushe den her ville forhåndsstemplet
`plan-review go` FØR revieweren faktisk har sagt go, og styrt mot nøyaktig den grenen som er
forbudt. Grunnen markøren finnes: gjenopptakelsen i §2 (§ 3.1b) trenger den i en SENERE runde (når B
velges på nytt via §1) — uten pushen her ville telemetrien dø med denne sesjonen.

**Gjenopptakelse i §2.** Når B senere velges i §1: er `plan:` satt OG
`grep -c '^\*\*Status:\*\* pipelinet' <plan_path>` gir `1`, hopper du over §3 og §4 og går rett til
ferskhets-gaten under. Les samtidig `planner=`, `reviewer=` og `plan_review_rounds=` fra markørlinja
inn i `$MODELS` og `$PRR` for §6-raden, og `pipelined_from=<A>` fra samme linje. Mangler markøren,
kjøres §3/§4 som vanlig — fail-safe-retningen er full plan-runde, aldri hoppet gate.

**Dette er IKKE fast-path (§2b).** Fast-path skriver `skipped` for hoppede stadier og `$PRR = 0`.
Her ble §3/§4 FAKTISK kjørt, bare i en tidligere runde: `models` skal bære de faktiske planner-/
reviewer-modellene og `plan_review_rounds` det faktiske tallet — aldri `skipped`/`0`.

**Ferskhets-gate (kjøres ALLTID rett før §5 for B).** A kan ha endret filer B-planen bygger på.

**Steg 1 — hent plan-SHA (formatuavhengig):**

```bash
git fetch origin {{BASE_BRANCH}}
grep -m1 '^\*\*Plan-SHA:\*\*' tasks/plans/todo-<B>-<slug>.md | grep -oE '[0-9a-f]{40}'
```

**Tom output ⇒ planfila har ingen `**Plan-SHA:**` ⇒ ferskhets-gaten KAN IKKE kjøres ⇒ kjør full
§3/§4-runde** (fail-safe-retningen er alltid full plan-runde, aldri hoppet gate — samme prinsipp som
«Gjenopptakelse i §2»). Dette dekker planer skrevet før denne PR-en, som mangler `**Plan-SHA:**`
helt.

**Steg 2 — FILTRER fillista.** Rå-lista er plan-rapportens `files_touched[]`; er rapporten borte (ny
sesjon), les `## Filer som berøres` i planfila. Lista MÅ filtreres — den inneholder blant annet B sin
egen planfil, som per konstruksjon ble committet ETTER plan-SHA, og A sin runde har i mellomtiden
skrevet delt state (run-log-rad, lessons-append, todo-arkivering) som er irrelevant for planen:

```bash
printf '%s\n' <filer fra planen> \
  | grep -vE '^(tasks/plans/|tasks/todos/|tasks/todo_archive\.md|tasks/lessons)' \
  | grep -vE '^docs/superpowers/loop/(run-log|retro-log|retro-triage)\.md'
```

Alle de ekskluderte er **append-only delt state** som §6 skriver på vegne av A, ikke innhold en plan
kan bli stale mot. **Unntak, gitt som ferdig alternativ filterlinje (ikke en håndredigering av
ERE-en i drift):** skal B-planen ENDRE eksisterende lessons-innhold (omstrukturere, ikke bare få
appendet en lesson av §6), bruk denne varianten av første filter for den runden:

```bash
grep -vE '^(tasks/plans/|tasks/todos/|tasks/todo_archive\.md)'
```

(dvs. samme linje, med `|tasks/lessons` fjernet — ferdig utskrevet, ikke overlatt til fri
hånd-redigering av regexen under en aktiv runde).

**Reachability-sjekk (FØR Steg 3):**

```bash
git cat-file -e <plan-SHA>^{commit}
```

Ikke-null exit ⇒ plan-SHA-en er velformet men IKKE nåbar i dette repoet (force-push eller GC har
fjernet objektet) ⇒ samme fail-safe-gren som tom Plan-SHA over: kjør full §3/§4-runde, ikke Steg 3.
Uten denne sjekken skriver `git diff --stat <plan-SHA>..origin/{{BASE_BRANCH}}` «bad object» til
stderr med TOM stdout og exit `128` — leses stdout alene (som Steg 3 foreskriver), tolkes det
feilaktig som «fersk».

**Steg 3 — diff per gjenværende fil:**

```bash
git diff --stat <plan-SHA>..origin/{{BASE_BRANCH}} -- <fil>
```

**Les STDOUT for ferskhet — men et ikke-null exit fra `git diff` her er en GATE-FEIL, ikke grønt.**
`git diff --stat` avslutter med `0` både når filen er uendret og når den er endret — en gate på
exit-koden ALENE ville derfor vært permanent grønn for de vanlige tilfellene, så tom/ikke-tom stdout
er det som avgjør. Men reachability-sjekken over skal allerede ha fanget den ANDRE klassen
ikke-null-exit (`128`, «bad object») FØR Steg 3 kjører i det hele tatt — treffer Steg 3 likevel et
ikke-null exit, er det en gate-feil, ikke et grønt resultat. Samme for filteret: `grep -v` gir
exit 1 hvis alt filtreres bort.

**Alle utskrifter tomme ⇒ planen er fersk ⇒ gå til §5.** Minst én ikke-tom ⇒ nøyaktig ÉN
re-plan-runde: dispatch §3 på nytt med plan_path, plan-SHA og den ordrette diffen som input,
deretter §4 på nytt (samme revisjonsteller som ellers). Den reviderte planen skal bære en NY
`**Plan-SHA:**` (regelen står i plan-malen, `todo-plan.md` § «Plan-SHA», og gjelder enhver
revisjonsrunde — ikke bare denne) = `{{BASE_BRANCH}}`-tippen planneren synket mot. Kjør gaten om
igjen etterpå; andre kjøring er en kontroll på at `{{BASE_BRANCH}}` ikke flyttet seg UNDER
re-planen, ikke en uavhengig ferskhetssjekk. Er den fortsatt ikke-tom, har delt state flyttet seg
under føttene på deg ⇒ ⚠️ PAUSEPUNKT: frigi claim (A sin — se under), eskalér.

**Re-plan-runden kjører §3 i sin helhet**, inkludert §3s avsluttende overleverings-/commit-/
§0b-blokk — ingen egen rydde-regel her (peker, ikke kopi). **For reviewer(B) i par 2:** reviewer(B)
følger §4s §0b-kontrakt uendret, inkludert no-go-carve-outen — og reviewer(B)s worktrees
akkumuleres og dedupliseres på tvers av B sine §4-runder, hver med sitt eget pre-snapshot, nøyaktig
som i §4 (peker, ikke kopi).

`$PRR` for §6-raden er markørens `plan_review_rounds=` PLUSS rundene brukt i re-planen — noter
summen før du re-dispatcher §3, siden markøren overskrives av den reviderte planen og den
opprinnelige verdien ellers går tapt.

**Re-dispatch mot en allerede pushet plan.** Planfila for B ligger allerede på `{{BASE_BRANCH}}`
(forrige hale i dette avsnittet pushet den). En re-dispatch av planneren treffer derfor Steg 0 sin
`git merge origin/{{BASE_BRANCH}}` mot en usporet kopi av SIN EGEN plan i den nye worktreen —
«untracked working tree file … would be overwritten by merge» — samme feilklasse som lesson
2026-09-04 («Git-halens `git add -A tasks/` sveiper en usporet plan-kopi inn på dev»), IKKE
ref-lock-kappløpet fra R13b (det er en annen mekanisme — ikke bland remediene). Par-dispatch-malens
vanlige retry (fetch + merge på nytt) løser IKKE dette: den feiler identisk begge ganger og gir et
falskt pausepunkt. Legg derfor dette tillegget i re-dispatch-prompten til planneren:

```bash
rm -f tasks/plans/todo-<B>-<slug>.md
git merge origin/{{BASE_BRANCH}}
```

kjørt FØR resten av Steg 0 fortsetter.

**Kø-stabilitet.** Køen vinner ved claim, alltid. Kjør §1-skriptet på nytt rett FØR du claimer B. Er
B ikke lenger øverste `elig=YES` — fordi mennesket endret `priority`/`order`, satte
`status: deferred`, eller la inn en ny prioritert todo — claimes den nye øverste i stedet. B
beholder `plan:`-pekeren og planfila; en ferdig plan kastes ALDRI. Neste gang B når toppen, plukkes
planen opp igjen via gjenopptakelsen over.

**Drop-B-halen (planen er ALLEREDE pushet til `{{BASE_BRANCH}}`).** Fordi pre-par-2-halen (over)
pusher B sin planfil FØR §4-resultatet er kjent, kan «drop B» treffe en plan som allerede ligger på
`{{BASE_BRANCH}}` — den kan da ALDRI «forkastes ucommittet»; det finnes ingenting ucommittet å
forkaste. Bruk denne halen (samme eksplisitt-sti-disiplin som over) når planen allerede er pushet:

```bash
# 0. Forhåndssjekk: ingenting usporet under tasks/plans/ som ikke skal til {{BASE_BRANCH}}
git status --porcelain -uall tasks/plans/

# 1. Speil-guard (identisk med §6 steg 1 / pre-par-2-halen over)
mb=$(git merge-base origin/{{BASE_BRANCH}} HEAD)
non_shared=$(git diff "$mb"..HEAD --name-only | grep -vE '^(tasks/|docs/superpowers/loop/)' || true)
[ -z "$non_shared" ] || { echo "FEIL: HEAD har commits utenfor delt state ($non_shared) — feil branch"; exit 1; }

# 2. Drop B — fjern den allerede pushede planfila og nullstill plan:-pekeren
git rm tasks/plans/todo-<B>-<slug>.md
# rediger tasks/todos/todo-<B>-<slug>.md: sett plan: null
git add tasks/todos/todo-<B>-<slug>.md

# 3. Commit — tolerer «ingenting å committe»
git diff --cached --quiet && echo "ingenting å committe" \
  || git commit -m "chore(loop): TODO <B> droppet ut av pipelinen (fra TODO <A>) — planfil fjernet"

# 4. Synk + push
git fetch origin {{BASE_BRANCH}} \
  && git rebase origin/{{BASE_BRANCH}} \
  && git push origin HEAD:{{BASE_BRANCH}}
```

**§0b for planner(B) og reviewer(B) etter drop-B-halen over — artefakt-gaten hoppes over:** kall
§0b for BEGGE worktreene UTEN `<forventet_fil>`, fordi planfila nettopp er bevisst fjernet med
`git rm` over. Alle andre vakter og allowlisten gjelder uendret; planen ligger fortsatt i
git-historikken. Dette er den ene lovlige bruken av carve-outen i §0b punkt 6.

**Motsatt regel for de to grenene som dropper B FØR planen noensinne er committet**
(canary-mismatch for planner(B); `technical_risk.flagged: true` i B sin PLAN-rapport, par 1):
plannerens worktree **BEHOLDES** — den bærer den eneste kopien av planen, og begge grenene
eskalerer uansett til mennesket. Ryddes av mennesket (TODO 245), aldri av §0b.

**Pausepunkt-samspill: A treffer et pausepunkt.** Et pausepunkt stopper loopen. B claimes ALDRI
automatisk — heller ikke når A sin claim er frigitt. Gjør dette, i rekkefølge:

1. Er B sin blokk fortsatt i flukt i samme melding, la den fullføre. Planner og reviewer skriver
   ikke delt state, så det er trygt.
2. Har B en ferdig, `go`-et plan (§4 ga `go`): kjør commit-halen over (pipelinet-markør + push),
   slik at arbeidet overlever at sesjonen dør. Har B IKKE passert §4 ennå: sjekk om planfila
   allerede er pushet (pre-par-2-halen kjører FØR §4-resultatet er kjent — se over). Er den det,
   kjør drop-B-halen over for å fjerne den: en ureviewet plan i delt state er verre enn ingen plan.
   Er den ikke pushet ennå (fortsatt i par 1), er det ingenting å rydde.
3. Frigi A sin claim per pausepunkt-regelen og rapporter til mennesket at B har ferdig plan og
   fortsatt står `elig=YES`.
4. Ber mennesket deg eksplisitt fortsette med B mens A står uløst, gjelder to ekstra krav før §5:
   (a) ferskhets-gaten over, og (b) **overlapp-sjekk mot A sin åpne PR** —
   `gh pr diff <A-pr> --name-only` skal ikke inneholde noen av filene B-planen navngir. Ikke-tomt
   snitt ⇒ start ikke B: planen er laget mot en `{{BASE_BRANCH}}` uten A sine endringer, og de to
   PR-ene ville kollidert.

**Pausepunkt-samspill: B-sporet pauser mens A er sunn.** Speilbildet av avsnittet over, og like
bindende: **en pausetilstand i B-sporet stopper ALDRI A.** B er u-claimet og spekulativ; A er
claimet og i drift.

**TODO 246 — drop-regelen under er hygiene, ikke et pausepunkt-nivå.** De fire drop-tilfellene
under (technical_risk i plan/plan-review, §4 no-go 2 runder, canary-mismatch) kjøres UAVHENGIG av
om den utløsende hendelsen ellers ville vært klassifisert nivå A eller B av `decision-level.py` —
en pipelinet B som ikke besto §4/canary droppes alltid stille ut av pipelinen, den spørres aldri
OG den logges aldri som et nivå-B-valg.

- **«Release claim» i §3/§4/§5b refererer ALLTID til den CLAIMEDE todoen (A)** — aldri til en
  pipelinet, u-claimet B. B har ingen claim å frigi. Uten denne presiseringen er §4s ordlyd
  («⚠️ STOPP, release claim») en felle: en bokstavelig lesning ville frigitt A sin claim og avbrutt
  en helt sunn implementering på grunn av en spekulativ plan.
- **`technical_risk.flagged: true` i B sin PLAN-rapport (par 1, FØR pre-par-2-halen kjører)** ⇒ B
  **droppes ut av pipelinen** FØR planen noensinne committes — ingen revert-hale trengs, `plan:`
  har aldri vært satt. Risikoen rapporteres til mennesket SAMMEN MED A sin ferdig-rapport. A føres
  uendret videre til §5b/§6 med claimen intakt.
- **`technical_risk.flagged: true` i B sin PLAN-REVIEW-rapport (par 2, ETTER at pre-par-2-halen
  allerede har pushet planen)** ⇒ samme drop, men planen er allerede på `{{BASE_BRANCH}}`: kjør
  **drop-B-halen over** før du rapporterer. Risikoen rapporteres sammen med A sin ferdig-rapport. A
  føres uendret videre til §5b/§6 med claimen intakt.
- **§4 `no-go` to runder for B** ⇒ §4 kjører i par 2, ETTER pre-par-2-halen — planen er allerede
  pushet. Kjør **drop-B-halen over**. Funnene rapporteres sammen med A, A fortsetter.
- **Canary-mismatch for planner(B)** ⇒ oppdages i verifiseringen FØR pre-par-2-halen kjører (ingen
  re-dispatch midt i A sin runde — det ville forsinket par 2 uten gevinst) — B droppes ut av
  pipelinen før planen noensinne committes, ingen revert-hale trengs. Rapporteres sammen med A.
- I alle fire tilfellene beholder B `status: open` og `claimed_by: null`. `plan:` er `null` uten
  videre handling i de to tilfellene som oppdages FØR pre-par-2-halen (canary-mismatch,
  plan-rapport-risiko); i de to tilfellene som oppdages ETTER (plan-review-risiko, §4-no-go) settes
  `plan: null` av drop-B-halen over, og planfila fjernes fra `{{BASE_BRANCH}}`. Neste runde plukker
  B opp på vanlig måte via §1.

**Run-log.** Når B senere merges, skriv `pipelined_from=<A>` i `run-log.md` felt 11, ved siden av
`selector=`/`floor=`. Ingen ny kolonne, ingen ny `outcome`-verdi, ingen ny `pause_event`.
Fravær av nøkkelen betyr «ikke pipelinet» og er aldri et kontraktbrudd.

## 5d. Parallelle implementere (fil-disjunkt-gate — TODO 233)

**Trigger:** når B sin plan står `go` (§4, ordinært ELLER pipelinet via §5c) og B derfor ville blitt
claimet i EN SENERE runde. §5d avgjør om B i stedet claimes MED ÉN GANG og implementeres SAMTIDIG
med A, i stedet for å vente. §5d er en utvidelse av §5c (samme par-dispatch-mekanikk, «`§5
implementer(A)` + `§3 planner(B)`» byttes ut med «`§5 implementer(A)` + `§5 implementer(B)`»), ikke
en ny mekanisme. Taket er `parallel_implementers.max` i `loop.config.yaml`. Nøkkelen er valgfri;
mangler den, er verdien `1` — nøyaktig dagens sekvensielle atferd, og hele §5d hoppes over. Verdien
i dette prosjektet er `{{PARALLEL_IMPLEMENTERS_MAX}}`.

**Hever IKKE `pipelining.max_in_flight`.** De to nøklene teller forskjellige ting: `pipelining`
teller todos med plan men uten claim; `parallel_implementers` teller samtidig skrive-kapable
workere. B **claimes** i det øyeblikk §5d sier ja, så antallet u-claimede planer går mot 0 i samme
steg. **Invariant:** når §5d er armet, pipelines ingen NY todo (C) før in-flight-tabellen under er
**TOM** (alle spor `merged`, `paused` eller `frozen:*`) — «tom», ikke «≤ 1», ellers ville en tredje
todo kunne pipelines midt i en armet runde.

### §1-filter for B som parallell-kandidat — kan kun AVVISE, aldri godkjenne

Fravær av `files:` i todo-frontmatteren er normalen, ikke unntaket, i dagens kø — en gate som leser
fil-kanter og armer parallellitet på TOM kant-mengde ville vært fail-open. Filteret under kan derfor
kun avvise en kandidat; den bindende gaten er gate P/gate M lenger ned, der de faktiske
fillistene finnes.

1. **Pausepunkt-tag-eksklusjon (hard).** En kandidat med en tag i mengden
   `{migrasjon, rls, edge, native, eas, prod, secrets, vault, hooks}` kan ALDRI være B i et
   parallelt par.
2. **`deps`-kjede-sjekk (hard).** B sin `deps` må ikke inneholde A, og A sin `deps` må ikke
   inneholde B.
3. **Tidlig fil-avvisning (myk, kun negativ).** Har BEGGE `files:`, og snittet (`gate P`, under) er
   ikke-tomt → hopp B nå og spar en hel rundes arbeid. Har én eller ingen `files:` → ingen
   konklusjon ennå, gå videre til gate P.
4. **`technical_risk`-eksklusjon ved gate P (hard).** Ledd 1 er *frontmatter*-basert og kan ikke se
   risiko som først oppstår i planen. Er B sin plan-rapport (eller en reviewers rapport)
   `technical_risk.flagged: true` med noe ANNET enn `kind ∈ {docs_selfmod, hook_selfmod}` OG
   `executable_gate: true`, er B nivå A ⇒ ingen parallellitet (`report-schema.md:46`). En
   `technical_risk` flagget av en REVIEWER bærer aldri `kind`/`executable_gate` og er derfor
   ALLTID nivå A — se «B eskaleres til nivå A ETTER claim» under for grenen der dette inntreffer
   ETTER at B allerede har fått branch/PR/pinnet SHA.

### Gate P og gate M — to gater, samme skript (`tasks/parallel-disjoint.py`)

| Gate | Når | A-side (input) | B-side (input) | Retning ved manglende input |
|---|---|---|---|---|
| **Gate P** (prediktiv) | Etter §4 `go` for B, FØR B claimes | `gh pr diff <A-pr> --name-only` — MÅLT | B sin plan sitt `## Filer som berøres`-avsnitt — DEKLARERT (`--plan-b`) | ingen parallellitet (fail-closed) |
| **Gate M** (målt) | (i) inkrementelt etter HVER A-fix-runde (varsel), (ii) bindende FØR merge av **B** | `gh pr diff <A-pr> --name-only` | `gh pr diff <B-pr> --name-only` | **drop til serielt** (se under) |

```bash
gh pr diff <A-pr> --name-only > <scratch>/gate-a-<runde>.txt
python3 tasks/parallel-disjoint.py --a <scratch>/gate-a-<runde>.txt \
  --plan-b tasks/plans/todo-<B>-<slug>.md \
  --forbid-prefix app/ --forbid-prefix components/ --forbid-prefix lib/
```

`ok` (exit 0) ⇒ fortsett. `overlap` / `empty-a` / `empty-b` / `missing-section` / `client-code`
(exit 1) ⇒ ingen parallellitet denne runden; B beholder planen sin og claimes normalt via §1 i en
SENERE runde (samme fail-safe-retning som §5cs ferskhets-gate). `--forbid-prefix` er precondition
(C) fra e2e-kontrakten under — den kjøres i SAMME kall som selve disjunkt-sjekken, ikke separat.

**Gate M sin fail-retning er «drop til serielt», ikke pausepunkt.** Ikke-tomt snitt i gate M betyr
at **parallelliteten ikke lenger er gyldig** — typisk fordi A sin §5b-fix-runde lovlig utvidet A sin
diff etter at gate P sa ja — IKKE at gaten er defekt. Riktig respons er å degradere til den
serielle stien.

**Gate M (i) — inkrementelt varsel, etter HVER A-fix-runde.** B har ennå ikke nødvendigvis en egen
PR, så B-siden er den samme DEKLARERTE plan-listen gate P allerede leste:

```bash
gh pr diff <A-pr> --name-only > <scratch>/gate-m-a-<runde>.txt
python3 tasks/parallel-disjoint.py --a <scratch>/gate-m-a-<runde>.txt \
  --plan-b tasks/plans/todo-<B>-<slug>.md \
  --forbid-prefix app/ --forbid-prefix components/ --forbid-prefix lib/
```

Et rødt `overlap`/`empty-a`/`empty-b`-utfall her er kun et TIDLIG varsel (koordinatoren kan bestille
B sin re-synk tidligere); det er den BINDENDE formen (ii) under som faktisk styrer
merge-rekkefølgen for B.

**`client-code` er derimot BINDENDE for A allerede HER, ikke bare et varsel (kode-review-funn,
fix-runde 2, VIKTIG 2).** Gate M (ii) kjøres først rett FØR B sin merge, og sekvenslinja under
plasserer A sin `§6(A)` FØR gate M (ii) i det hele tatt kjører — uten en binding her ville A kunne
merges via `§6(A)` med `e2e_not_applicable` stående selv om en A-fix-runde allerede har rørt
`app/`/`components/`/`lib/`. Et `client-code`-utfall fra gate M (i) BLOKKERER derfor `§6(A)`: A MÅ
kjøre steg 2 (`npm run test:e2e`) og steg 2a (web-smoke) og rapportere det FAKTISKE utfallet FØR
`§6(A)` kjøres — se «Sekvensen skrevet som ÉN linje» under for hvor dette settes inn.

**Bokføring av utfallet — kolonnen `gate_m_i` (kode-review-funn, fix-runde 3, MINDRE 4).** Utfallet
av HVER gate M (i)-kjøring skrives UMIDDELBART inn i in-flight-tabellens `gate_m_i`-kolonne på A sin
rad (`ok` \| `client-code:<side>` \| `-`, se «In-flight-tabell» under). Uten den kolonnen ville
bindingen hvilt på koordinatorens arbeidsminne på tvers av flere dispatcher — nettopp den
feilmodusen §5d ellers designer bort. **«Ikke løst» er DEFINERT, ikke skjønn:** et `client-code:a`-
eller `client-code:ab`-utfall regnes som LØST først når A sin FERSKESTE ferdig-rapport (for A sin
gjeldende `pinned_sha`) rapporterer et FAKTISK utfall av steg 2 og steg 2a — altså
`verification.e2e_outcome` OG `verification.web_smoke_outcome` forskjellig fra `e2e_not_applicable`.
Fram til da blokkerer utfallet `§6(A)`. Kolonnen nullstilles ALDRI for hånd; den overskrives kun av
neste gate M (i)-kjøring.

**Gate M (ii) — bindende, FØR merge av B:**

```bash
gh pr diff <A-pr> --name-only > <scratch>/gate-m-a-<runde>.txt
gh pr diff <B-pr> --name-only > <scratch>/gate-m-b-<runde>.txt
python3 tasks/parallel-disjoint.py --a <scratch>/gate-m-a-<runde>.txt --b <scratch>/gate-m-b-<runde>.txt \
  --forbid-prefix app/ --forbid-prefix components/ --forbid-prefix lib/
```

**`--forbid-prefix` MÅ stå på BEGGE gate M-invokasjonene, ikke bare på gate P** (kode-review-funn):
gate P måler B sin DEKLARERTE plan-liste, og gate M finnes NETTOPP fordi den deklarasjonen kan
drive — en A- eller B-fix-runde kan lovlig rusle inn i `app/`/`components/`/`lib/` ETTER at gate P
sa ja. Uten flagget på gate M ville ingenting målt forbudet på nytt før merge, og e2e-kontrakten (D)
under ville hvilt på et premiss ingen lenger hadde bekreftet.

- `ok` ⇒ videre til MERGEABLE-sjekken (§6).
- **`overlap`/`empty-a`/`empty-b` ⇒ DROP TIL SERIELT** (ikke pausepunkt): B settes til
  `stadium: serialized`, og B-implementeren dispatches i fix-mode-stien
  `todo-finish-worker.md:46–47` (`git fetch origin {{BASE_BRANCH}} && git merge origin/{{BASE_BRANCH}}`) + re-kjøring av
  verifiseringssettet (`npm run build:web`, `npx tsc --noEmit`, `npm run format:check`,
  `npm run test:unit`) + push. **Ny kode-review-runde kreves KUN hvis merge-en måtte
  konfliktløses** — en ren merge endrer ingen linje B har skrevet, og §5b sitt trigger-sett er
  «nye commits som endrer B sin diff». Måles: rapporterte merge-en konflikt? ja ⇒ §5b `r_{n+1}`;
  nei ⇒ rett til MERGEABLE-sjekken.
- **`client-code` ⇒ DROP TIL SERIELT, OG `e2e_not_applicable` er IKKE LENGER LOVLIG for SIDEN(E)
  som drev inn i klientkode.** `e2e_not_applicable` var kun korrekt fordi gate P avviste
  `app/`/`components/`/`lib/` på BEGGE sider (§ 2.2 (D)); et `client-code`-utfall her falsifiserer
  nettopp det premisset. `tasks/parallel-disjoint.py` returnerer BEGGE siders treff uavhengig av
  hverandre (utskrift `client-code a=[...] b=[...]` — kode-review-funn, fix-runde 2, VIKTIG 1: en
  tidligere `or`-kortslutning i `evaluate()` gjorde at B sitt treff aldri ble beregnet når A allerede
  hadde ett). **E2e-kravet gjelder HVER side hvis liste er ikke-tom**: er BEGGE `a` og `b` ikke-tomme,
  MÅ BEGGE spor kjøre steg 2 (`npm run test:e2e`) og steg 2a (web-smoke) og rapportere det FAKTISKE
  utfallet FØR merge; er kun én side ikke-tom, gjelder kravet KUN det sporet, og det andre sporet
  beholder `e2e_not_applicable` uendret. For øvrig samme drop-til-serielt-prosedyre som
  `overlap`-grenen (re-synk + re-verifisering + push), pluss dette ekstra e2e-kravet for hver
  klientkode-rammet side.
- **⚠️ PAUSEPUNKT KUN hvis DENNE re-synk-stien selv feiler**: uløsbar merge-konflikt, eller rød
  re-verifisering etter en ren (konfliktfri) merge. En invariant som ER meningsfull ETTER re-synk
  (og som derfor kan brukes til å bekrefte at re-synken faktisk skjedde, i stedet for å anta det):
  `git merge-base --is-ancestor origin/{{BASE_BRANCH}} <B-head>` ⇒ exit `0` (B inneholder A).
  Ikke-null der er et ekte signal om at re-synken ikke skjedde.

### Sekvensen skrevet som ÉN linje (obligatorisk tørrkjøring, lesson 2026-09-05)

For `parallel_implementers.max = 2`:

```
§1 → claim A → §2 → §3 → §4(A) →
§5c: fetch → snapshot par1 → PAR 1 [impl(A) + planner(B)] →
pre-par-2-hale (push B-plan) → snapshot par2 → PAR 2 [code-rev(A) r1 + plan-rev(B)] →
§4-gate for B = go → markør-hale (push)  <- MÅ være pushet FØR B claimes ->
§5d: §1-filter(B) → GATE P → claim B → snapshot par3 →
PAR 3 [impl(A) fix-r1 (hvis revise-gate) + impl(B)] →
[gate M (i) varsel etter hver A-fix-runde — `client-code` for A er BINDENDE her: blokkerer §6(A) til A har kjørt steg 2 (`npm run test:e2e`) + steg 2a (web-smoke) og rapportert faktisk utfall] →
snapshot par4 → PAR 4 [code-rev(A) r2 (hvis) + code-rev(B) r1] → … →
A go ⇒ [gate M (i) sitt siste client-code-utfall for A? ja, ikke løst ⇒ A kjører steg 2+2a FØR §6(A)] → §6(A): delt state + merge A (KUN A sin rad til §0b) → dev-CI-differensial #1 →
B go ⇒ GATE M (ii) (bindende) → [overlap/empty-a/empty-b ⇒ drop til serielt: B synker mot dev + re-verifiserer. client-code ⇒ drop til serielt OG e2e-kravet gjelder HVER side som er ikke-tom (a=[...] b=[...])] →
MERGEABLE(B) → §6(B): delt state + merge B (KUN B sin rad til §0b) → dev-CI-differensial #2 → §6b → §6c
```

Hver «FØR/ETTER»-setning i §5d skal kunne spores mot DENNE linja.

### In-flight-tabell

Holdes i koordinatorens **scratchpad** — ALDRI som repo-relativ fil (§0bs regel om at
`<scratch>`-artefakter aldri legges i koordinatorens eget tre). Fil: `<scratch>/inflight-<runde>.md`.

| Kolonne | Kilde | Hvorfor den finnes |
|---|---|---|
| `todo` | §1/§5c | nøkkel |
| `rolle` | `A` \| `B` | merge-rekkefølge |
| `wt_path` | ferdig-rapportens `evidence.toplevel` | §0b vakt 1 krever EKSAKT sti |
| `pre_snapshot` | `<scratch>/wt-pre-5d-par<n>-<runde>.txt` | §0b vakt 5 krever PAR (sti, snapshot) |
| `branch` | ferdig-rapportens `branch` | §0b `<branch_kryss_sjekk>` |
| `pr` | ferdig-rapportens `pr_url` | gate M, MERGEABLE, §6 |
| `pinned_sha` | `gh pr view <pr> --json headRefOid` | §5b trigger-sett + fix-runde-diff |
| `gate_m_i` | gate M (i) — skrives etter HVER kjøring | `ok` \| `client-code:<side>` \| `-` (ikke kjørt ennå). Bærer bindingen som blokkerer `§6(A)`; «løst» er definert i «Gate M (i)» over |
| `stadium` | koordinator | `plan-go` \| `implementing` \| `code-review-r<n>` \| `fix-r<n>` \| `awaiting-merge` \| `serialized` (gate M overlap, venter på re-synk) \| `merged` \| `frozen:<event>` (B fryst, eskalert — se under) \| `paused:<event>` |

**§6(A) sender KUN rader med `rolle: A` til §0b; B sine rader ryddes av §6(B).** Tabellen ER
akkumuleringslista §6 sender til §0b, men i en armet parallell runde er §6(A) og §6(B) to
ADSKILTE §6-invokasjoner (se «Sekvensen» over: A sin merge kan skje mens B fortsatt implementerer).
Sender §6(A) HELE tabellen, ville §0b forsøkt å rydde B sin LEVENDE worktree — §0b har ingen
liveness-vakt utover sine fem sti-/snapshot-baserte sjekker, og B passerer alle fem. **Tilstandsvakt,
skrevet som ALLOWLIST, ikke denylist (kode-review-funn):** §0b kalles KUN på en rad hvis `stadium` ∈
`{merged}`. Enhver annen verdi utelates — inkludert `implementing`, `code-review-r*`, `fix-r*`,
`awaiting-merge`, `serialized`, `frozen:*`, `paused:*`, og enhver stadium-verdi som legges til senere
og ikke er tenkt på i dag. En denylist ville krevd at listen oppdateres i SAMME PR som hver ny
stadium-verdi innføres — glemmes det (nøyaktig slik `awaiting-merge` og `paused:*` manglet i en
tidligere revisjon av denne teksten), er en ny «i flukt»-verdi fail-open ved konstruksjon. Allowlisten
gjør det motsatte trygt: en ny stadium-verdi er automatisk utelatt (fail-closed) helt til noen
eksplisitt legger `merged` til den. Dedup-regelen fra §6 steg 4 (i) gjelder uendret innenfor hver
invokasjons egen delmengde: dedupliser på STIEN, behold FØRSTE rundes snapshot for stien.

### Par-dispatch-maltillegg for parallelle implementere

Legges i dispatch-prompten til BEGGE implementere når §5d er armet (samme mønster som TODO 231s
tillegg for pipelinede par):

- **Ref-lock (delt `.git`):** koordinatorens egen `git fetch origin {{BASE_BRANCH}}` FØR paret
  dispatches, PLUSS `git merge-base --is-ancestor origin/{{BASE_BRANCH}} HEAD` etter Steg 0 i
  BEGGE prompter (TODO 231-tiltaket, bevist i drift).
- **Stash-forbud (delt stash-stack):** bar `git stash`/`git stash pop` er FORBUDT for begge
  implementere denne runden; bruk en midlertidig WIP-commit i stedet. Koordinatoren tar
  `git stash list | wc -l` som baseline FØR par 1 og sammenligner etter hvert par; avvik ⇒
  ADVARSEL med SHA + branch til mennesket.
- **Pre-commit-re-synk (delt-state-push midt i flukt):** rett før `todo-finish-worker.md` steg 6
  («Commit + PR mot dev»), kjør `git fetch origin {{BASE_BRANCH}} && git diff origin/{{BASE_BRANCH}} --stat`;
  ikke-tom med filer implementeren ikke selv rørte ⇒ merge FØR commit.
- **e2e-kontrakten (D), BETINGET (kode-review-funn, fix-runde 2, VIKTIG 2):** se «Forutsetning for
  parallellitet (e2e)» under — `e2e_not_applicable` er KUN lovlig SÅ LENGE egen diff ikke rører
  `app/`, `components/` eller `lib/`; ellers kjøres steg 2 og 2a og det FAKTISKE utfallet
  rapporteres (konsistent med `todo-finish-worker.md:20`). **«Rører» MÅLES, det tolkes ikke**
  (kode-review-funn, fix-runde 3, MINDRE 5) — kjør ordrett, rett før steg 2:
  ```bash
  git diff origin/{{BASE_BRANCH}} --name-only | grep -E '^(app|components|lib)/'
  ```
  **Tom output ⇒ `e2e_not_applicable` er lovlig. Ikke-tom output ⇒ kjør steg 2
  (`npm run test:e2e`) og steg 2a (web-smoke) og rapporter det faktiske utfallet.** Dette er
  ORDRETT samme kommando som den normative målingen i «Forutsetning for parallellitet (e2e)»
  under — én måling, to kallsteder.

**Forutsetning for parallellitet (e2e), BETINGET per implementer (kode-review-funn, fix-runde 2,
VIKTIG 2 — rettet fra en tidligere ubetinget «begge hopper alltid»).** Gate P avviser enhver fil
under `app/`, `components/` eller `lib/` i B sin DEKLARERTE plan (`--forbid-prefix`, precondition
(C)) FØR B claimes — men en fix-runde på ENTEN A eller B kan lovlig utvide diffen etter det
punktet (samme observasjon som gate M sin `client-code`-gren over). En ubetinget «begge hopper
steg 2/2a» ville motsagt `todo-finish-worker.md:20`, som gjør `e2e_not_applicable` betinget av at
diffen FAKTISK ikke rører klientkode — ikke av at en gate sa det ikke gjorde det på et TIDLIGERE
tidspunkt. Regelen er derfor: `e2e_not_applicable` er lovlig for en implementer KUN SÅ LENGE dens
EGEN diff ikke rører `app/`, `components/` eller `lib/` på det tidspunktet steg 2/2a faktisk
kjøres; har diffen rømt inn i et av disse prefiksene (oppdaget av gate M over, eller av
implementeren selv), kjører DEN implementeren steg 2 (`npm run test:e2e`) og steg 2a (web-smoke)
og rapporterer det faktiske utfallet i stedet. **Den NORMATIVE målingen av «rører» er denne
kommandoen, kjørt av implementeren rett før steg 2** (kode-review-funn, fix-runde 3, MINDRE 5 — den
står ORDRETT likelydende i par-dispatch-maltillegget over, slik at implementeren ikke skal måtte
tolke ordet):

```bash
git diff origin/{{BASE_BRANCH}} --name-only | grep -E '^(app|components|lib)/'
```

Tom output ⇒ `e2e_not_applicable` er lovlig for DEN implementeren. Ikke-tom ⇒ steg 2 + steg 2a
kjøres og det faktiske utfallet rapporteres. `grep` returnerer exit 1 på tom output; det er
IKKE en feil her, kun «ingen klientkode rørt». Endres port-/Metro-kontensjonen med VILJE — f.eks.
når TODO 184 lukkes, eller når et klientkode-par skal parallelliseres — MÅ port- og
Metro-kontensjonen løses FØRST (per-implementer port + port-scopet drap, eller gjensidig
utelukkelse på e2e-steget: `e2e_blocked:parallel_exclusion`, navngi hvem som kjørte).

**Release claim med to claimede todos.** «Release claim» i §3/§4/§5b refererer normalt til DEN ENE
claimede todoen. Med §5d armet er BÅDE A og B claimet samtidig — et pausepunkt som rammer ÉN av dem
(f.eks. B eskalert til nivå A) skal derfor navngi HVILKEN av de to todo-numrene som eskaleres, og
frigi/beholde claim per todo individuelt: A sin claim røres ALDRI av en hendelse på B sitt spor, og
omvendt (se «B eskaleres til nivå A» under for det konkrete tilfellet).

### B eskaleres til nivå A ETTER claim

Med §5d kan B ha egen branch, åpen PR og pinnet SHA når en eskalering inntreffer — f.eks. fordi
kode-revieweren flagger `technical_risk` (alltid nivå A) eller fordi et pausepunkt oppdages under
implementeringen. §1-filterets ledd 1 og ledd 4 reduserer frekvensen, men kan ikke eliminere den.

- **A fortsetter uendret** til merge — A sin gyldighet avhenger ikke av B.
- **B fryses, ikke ryddes:** `stadium: frozen:<event>` i in-flight-tabellen. Branch, PR og pinnet
  SHA blir stående; worktreen ryddes IKKE (§0b hopper B denne runden, jf. tilstandsvakten over), og
  `claimed_by` beholdes slik at ingen annen runde plukker B opp.
- **Eskaleringsmeldingen til mennesket MÅ navngi B med `branch`, `pr` og `pinned_sha`** fra
  in-flight-tabellen — ellers må mennesket lete etter en halvferdig PR uten spor i run-loggen.
- **Run-log:** B får ingen rad før den lukkes. Blir runden avsluttet med B fryst, skrives B sin rad
  som `paused` med `pause_event` = eskaleringsårsaken, med `pipelined_from=<A>` (var B pipelinet)
  OG `parallel_with=<A>`, og med **`auto_decided=<B>:<m>`** satt per den TEMPORALE
  partisjoneringsregelen over (§ «Partisjonering ved flere rader i SAMME runde») — `<m>` teller
  nivå-B-valg tatt ETTER at A-raden ble skrevet, normalt `0` men ikke mandatert til å være det (selve
  eskalerings-hendelsen er som regel ikke et nivå-B-valg, men en etterfølgende re-synk-beslutning
  på B sitt spor kan være det).

### B4 dekker også arming av parallellitet — ingen ny regel i `decision-level.py`

`python3 tasks/decision-level.py --event pipeline_b_select` klassifiserer **B4** («Pipelining: valg
eller drop av B-sporet»). Valget «arm parallellitet for dette B-sporet» ER et valg om B-sporet —
B4 dekker også arming av parallellitet, ikke bare selve pipeline-valget. B4s forpliktelser
(decision-log-entry, `auto_decided=`, sluttmeldings-linje) er nøyaktig de riktige; ingen ny regel
(B8) er innført.

**Hygiene-carve-out (speiler TODO 246-avsnittet i §5c):** en NEKTELSE av å parallellisere
(§1-filter-avvisning, gate P `overlap`/`empty-*`, `technical_risk`-leddet) er **hygiene, ikke et
nivå-B-valg** — den logges aldri. Det samme gjelder **«drop til serielt» ved gate M `overlap`**:
degraderingen er tvungen av gaten, ikke valgt av koordinatoren. Kun det POSITIVE valget (arm
`parallel_implementers.max`-parallellitet) logges som B4.

**Mekanismen kan være inert på dagens kø, og det er forventet, ikke en defekt.** Er alle
`elig=YES`-kandidatene loop-/lessons-/docs-arbeid, vil gate P typisk gi `overlap` mot A (begge
rører `coordinator-runbook.md`/`orchestration-loop.md`) — fravær av `parallel_with=`-rader i
run-loggen over flere runder betyr da at gaten gjør jobben sin, ikke at maskineriet er ødelagt. Se
CF-233-6 (`open-followups.md`) for driftsbeviset dette venter på.

## 6. Skriv delt state (seriell, re-kjørbar) + merge (kun koordinator)

> **Selv-modifiserende PR-er.** Når en merget PR endret `.claude/commands/run-loop.md`,
> `docs/superpowers/loop/coordinator-runbook.md` eller
> `docs/superpowers/loop/report-schema.md`: re-les de endrede filene fra disk FØR neste §6-rad
> skrives og FØR neste worker dispatches. Koordinatorens kontekst er et snapshot fra
> sesjonsstart; å skrive telemetri med gammelt vokabular etter en vokabular-endring produserer
> en rad som ser gyldig ut, men er usann.

Fra ferdig-rapporten, `status: "implemented"`:
1. **Lessons:** for hver `lessons[]`, legg Pattern/Sjekkliste/Kilder i `tasks/lessons/<topic>.md` + én-linjes bullet i `tasks/lessons.md`. Konsolider om 2+ dekker samme mønster.
2. **Bugs:** `bugs_new[]` → `tasks/bugs.md`; `bugs_closed[]` → `tasks/bugs_archive.md` (opprett fila hvis den ikke finnes).
3. **Arkiver todo:** flytt til `tasks/todo_archive.md` (format: se eksisterende oppføringer). Slett `tasks/todos/todo-<nr>-<slug>.md`. Flytt planfil → `tasks/plans/archive/`.
4. **Merge:** verifiser base FØR merge — `gh pr view <pr> --json baseRefName -q .baseRefName` → MÅ være `{{BASE_BRANCH}}`, ALDRI `{{PROD_BRANCH}}`.

   **Todo-nr-kollisjonssjekk FØR merge (TO gater — hver ser en tilstand den andre strukturelt
   ikke ser):**
   - **(a)** `sh scripts/check-todo-nr-collisions.sh` i `{{BASE_BRANCH}}`-arbeidstreet. Dekker
     koordinatorens EGNE ucommitterte §6.3/§6b/§7-endringer (arkivering, bug-triage,
     nummer-reservasjon) — den eneste tilstanden (b) aldri ser, fordi (b) kun leser committede refs.
   - **(b)** `sh scripts/check-todo-nr-premerge.sh "$(gh pr view <pr> --json headRefName -q .headRefName)"`.
     Bygger `git merge-tree`-resultatet av fersk `origin/{{BASE_BRANCH}}` og PR-branchen og kjører
     (a)-scriptet mot DET — PR-ens **innkommende** nr mot fersk base.
     Exit: `0` ingen kollisjon — **men står det en WARN om fetch-svikt på stderr, er basen
     muligens foreldet og 0 er IKKE grønt** · `1` kollisjon → ⚠️ STOPP, IKKE merge, følg
     renummereringen i **§9**, re-kjør (b) · `2` intern feil (ukjent ref, ubeslektede historier,
     `tasks/` mangler) → ⚠️ STOPP, les ALDRI som grønt · `3` merge-konflikt → samme pause som en
     vanlig merge-konflikt; en konfliktsti under `tasks/todos/` med samme nr+slug og ulikt
     innhold ER en nr-kollisjon (§9).

   Kjør (b) som **siste handling før merge-kallet** — den leser `origin/{{BASE_BRANCH}}` på
   kjøretidspunktet og krymper TOCTOU-vinduet, men lukker det ikke. Avanserer
   `{{BASE_BRANCH}}` i mellomtiden, kjør (b) på nytt. CI-jobben `todo-nr-guard`
   (`scaffolding/github-workflows/ci.yml`) er backstop for NESTE PR, ikke for et race mot en
   base som flyttet seg etter siste grønne CI-kjøring.

   Deretter merge via REST som default (bruker core-kvoten i stedet for GraphQL — lesson 2026-07-13):
   ```bash
   gh api --method PUT "repos/{owner}/{repo}/pulls/<pr-nummer>/merge" -f merge_method=merge
   ```
   Verifiser `merged: true` i responsen, og sett deretter `stadium: merged` på DENNE invokasjonens
   rad i in-flight-tabellen FØR §0b-kallene under (kode-review-funn, fix-runde 2, MINDRE 4) —
   allowlisten i «In-flight-tabell» (§5d) gater §0b nettopp på denne verdien, og ingen tidligere
   linje sa NÅR den skulle skrives. Endepunktet tar PR-**nummer** (ikke URL), og nummeret må stå som et **literalt tall** i kallet — en shell-variabel blokkeres av `guard-main-merge.sh` (TODO 172 D). Faktumet at base settes ved PR-oppretting og ikke ved selve merge-operasjonen gjelder uansett merge-form. Fallback ved REST-problemer: `gh pr merge <pr> --merge` (bruker GraphQL-kvoten, som kan tømmes ved høyt volum — lesson 2026-07-13).

   `guard-main-merge.sh` er registrert i `PreToolUse` i `.claude/settings.json` (TODO 173) og
   kjører i alle sesjoner og alle worktrees — verifisert 2026-08-31 ved at en throwaway
   worktree-sub-agent ble blokkert på `gh pr merge`. Hooks lastes ved **sesjonsstart** fra
   **hovedsjekkuten** (`$CLAUDE_PROJECT_DIR` resolver dit også for worktree-agenter), så en
   endring i skriptet eller i `settings.json` får effekt først i en fersk sesjon etter at
   hovedsjekkuten er oppdatert — ikke i den sesjonen som gjorde endringen. Hooks kan i tillegg
   komme fra den gitignorerte `.claude/settings.local.json`; sjekk begge hvis atferden avviker.
   **Begrensning:** vakten inspiserer kun kommandoens FØRSTE linje — flerlinjede eller prefiksede
   kommandoer (`git add -A` ⏎ `git push origin main`, `cd x && git push origin main`) omgår den.
   Lukkes i TODO 188. Base-sjekken over er derfor fortsatt den vakten som aldri kan hoppes over.

   **GraphQL-kvote-fellen:** hvis vakten blokkerer med «kunne ikke bekrefte base (fail-safe)» midt
   i et løp, er årsaken sannsynligvis tom GraphQL-kvote, ikke en farlig merge — `gh pr view` bruker
   GraphQL, og lesson 2026-07-13 er nettopp at den kvoten tømmes under tunge løp. Verifiser base
   med core-REST (`gh api repos/{owner}/{repo}/pulls/<pr-nummer> --jq .base.ref`) og kjør
   merge-kommandoen manuelt i terminal.

   Merge-konflikt → ⚠️ STOPP, release claim, rapporter.

   **Worktree-rydding etter merge (§0b, erstatter det gamle inline-oppslaget):** ett §0b-kall per
   **deduplisert** akkumulert implementer-PAR fra §5 (sti + rundens pre-snapshot-fil), med
   `evidence.toplevel` som nøkkel og ferdig-rapportens `branch`-felt som ren `<branch_kryss_sjekk>`.
   (i) **Dedupliser sti-lista før iterasjon** — dedup på STIEN; behold den FØRSTE rundens
   snapshot-fil for stien (det er den som er «før» for nettopp den worktreen).
   (ii) **«Branchen finnes ikke» er IKKE ADVARSEL** og telles ikke i «bærer commits»-bøtta — kun
   `-d`-nekt på en EKSISTERENDE branch teller der (§0b punkt 8).
   (iii) **K3** (den forlatte basis-branchen, oppstått når workeren byttet branch selv) dekkes av
   den **sti-utledede** slettingen i §0b punkt 7(b) — IKKE av noe sveip.
   **Ingen glob-sveip legges inn her** — historiske foreldreløse branches (fra FØR denne PR-en)
   eies av mennesket via TODO 245, aldri av loopen selv.
   **Ved en §5d-armert (parallell) runde er A og B TO adskilte §6-invokasjoner** (§5d,
   «Sekvensen»): denne worktree-ryddingen kjører per invokasjon på DEN invokasjonens egen
   akkumulerte liste alene — §6(A) sender aldri B sin rad til §0b og omvendt (§5d, «In-flight-
   tabell», tilstandsvakten på `stadium`).

   **Serialisert merge + `{{BASE_BRANCH}}`-CI-differensial (KUN ved §5d-armert runde).** Rekkefølgen er
   claim-rekkefølge: A merges så snart A er klar (steg 1–6 over), UAVHENGIG av hvor B står — men
   **FØRST etter A-sidens egen gate M (i)-sjekk** (kode-review-funn, fix-runde 3, MINDRE 4): bærer A
   sin rad `gate_m_i = client-code:a` (eller `client-code:ab`) som IKKE er løst per definisjonen i
   §5d («Gate M (i)»), er `§6(A)` BLOKKERT til A har kjørt steg 2 (`npm run test:e2e`) og steg 2a
   (web-smoke) og rapportert det FAKTISKE utfallet. Er kolonnen `ok` eller `-`, er det ingen
   blokkering. Deretter:
   1. **`{{BASE_BRANCH}}`-CI-differensial #1** — mål CI-konklusjonen på `{{BASE_BRANCH}}`-tippen FØR A ble claimet (baseline,
      notert av koordinatoren ved claim-tidspunktet), og CI-konklusjonen på `{{BASE_BRANCH}}`-tippen ETTER A sin
      merge-commit:
      ```bash
      gh run list --branch {{BASE_BRANCH}} --limit 5 --json conclusion,status,headSha,workflowName,createdAt
      ```
      Velg kjøringen for den EKSAKTE merge-commit-SHA-en. `cancelled`/`null`/`in_progress` ⇒
      ikke-konklusiv ⇒ poll (maks 10 min), ALDRI rød og ALDRI grønn. rød → rød = ingen regresjon fra
      A ⇒ videre, med preeksisterende rødhet notert. grønn → rød = regresjon fra A ⇒
      ⚠️ PAUSEPUNKT (B merges ikke). Ikke-konklusiv etter 10 min ⇒ videre, med «CI ikke konklusiv»
      notert i §6-meldingen — IKKE pausepunkt (treg CI skal ikke stoppe loopen). **Ingen overlapp
      med TODO 216** (216 gjelder `statusCheckRollup` på en PR-**head** FØR merge; dette gjelder
      `{{BASE_BRANCH}}`-branchen ETTER hver merge — ulike SHA-er, ulikt formål).
   2. **B `go` ⇒ gate M, bindende** (§5d) — deretter **MERGEABLE-sjekk for B** mot ny `{{BASE_BRANCH}}`:
      ```bash
      gh pr view <B-pr> --json mergeable,mergeStateStatus -q '.mergeable + " " + .mergeStateStatus'
      ```
      `MERGEABLE` ⇒ fortsett. `UNKNOWN` ⇒ poll (maks 2 min), ikke rød. `CONFLICTING` ⇒
      ⚠️ PAUSEPUNKT — filene var per gate M disjunkte (målt med `gh pr diff` på BEGGE sider, ingen
      deklarerte lister), så en konflikt her betyr at én av gatene selv er defekt, ikke at runden er
      det; en fix-runde ville skjult defekten.
   3. **§6 for B** i sin helhet (steg 1–6, egen `$TS`), med `parallel_with=<A>` skrevet på B sin rad
      (og `pipelined_from=<A>` i tillegg hvis B også var pipelinet via §5c) — se notat-feltet under.
      A sin rad får `parallel_with=<B>`.
   4. **`{{BASE_BRANCH}}`-CI-differensial #2** — samme prosedyre som #1, men med #1 sitt utfall som BASELINE
      (kjedet, ikke uavhengig): rød → rød ⇒ ingen regresjon fra B. grønn → rød ⇒ regresjon som
      først oppsto når BEGGE var i `{{BASE_BRANCH}}` ⇒ ⚠️ PAUSEPUNKT, med begge SHA-er i eskaleringen. Dette er
      den ENESTE sjekken som fanger «fil-disjunkt ≠ atferds-disjunkt» i den retningen som faktisk
      betyr noe — risikoen manifesterer seg per definisjon først når begge PR-ene er i `{{BASE_BRANCH}}`.
4b. **Worktree-sweep — kjøres HER, FØR raden under skrives (fix-runde 1, B1).** Kjør
   `./tasks/worktree-sweep.sh` nå og fang dens oppsummeringslinje i `$WTSWEEP`
   (`wtsweep=<fjernet>/<beholdt> ...`). **Ikke etter §6b, og ikke i §6c/§6d sin egen
   dokumentposisjon** — en rad som allerede er skrevet i steg 5 kan ikke få `wtsweep=`
   ettermontert. `--gate` (§6c, Del A) er token-basert, IKKE tidsstempel-basert (fix-runde 2,
   B1): den leser INNHOLDET i denne syklusens §6-rad og krever at `wtsweep=<n>/<n>` faktisk
   står der — et tidsstempel-sammenligning ble forkastet fordi steg 5 kan skrive raden i et
   senere minutt enn sweepens egen kjøretid selv når rekkefølgen (steg 4b FØR steg 5) er
   riktig, noe som ga falskt RØDT på en sweep som faktisk kjørte. Se §6d for hvorfor denne
   oppsamleren finnes ved siden av §0b — den fulle forklaringen står der, ikke duplisert her.
   Feiler kallet (script mangler, `exit 2`-flagg-feil): sett `$WTSWEEP` til en tydelig
   feilverdi (`wtsweep=feilet:<årsak>`) i stedet for å utelate tokenet — et manglende token er
   umulig å skille fra «glemte å skrive det», og gaten gir RØDT på begge (fravær ELLER
   feil-formet verdi).

   **Deretter: navngitt kjøring for denne todoens egne trær (TODO 401).** Kallet over rydder
   normalt ikke denne todoens egne trær: de er rørt siste døgn, og aldersvakten (`AGE_MIN`,
   §6d punkt 4) beholder dem. Kjør derfor også `./tasks/worktree-sweep.sh agent-<id> agent-<id> …`
   med ett `agent-<id>` per worktree-isolert dispatch denne todoen har hatt: planner,
   plan-reviewer, implementer og kode-reviewer, alle runder og forkastede re-dispatcher.
   **Navngi bare dispatcher der koordinatoren har mottatt resultatet (sluttrapport eller feil).**
   `<id>` er agent-ID-en fra dispatch-resultatet; treet er `.claude/worktrees/agent-<id>`, som
   også er `basename` av rapportens `evidence.toplevel`. Oppgi navnet, ikke stien: alt annet enn
   `agent-…` avvises med `exit 2`. Scout og lenser har ingen egen worktree og navngis ikke.
   **Aldri** en agent fra et pipelinet (§5c) eller parallelt (§5d) B-spor: den kan fortsatt leve,
   og låsen er ikke noe vern — en agent vekket med `SendMessage` er målt uten lås (2026-09-25).
   **Et agent-ID som har vært navngitt i en navngitt kjøring, er dødt: det skal aldri vekkes med
   `SendMessage` igjen, dispatch en fersk agent.** Skriptet vurderer KUN de navngitte trærne og
   hopper over aldersvakten for dem; alle andre vakter og redningen gjelder uendret. Et navn uten
   tre gir `IKKE FUNNET <navn>` (typisk allerede ryddet av §0b i steg 4) — det er ingen feil.
   Oppsummeringslinja er `wtsweep_named=<fjernet>/<beholdt> …`. Skriv begge tokenene inn i
   notat-feltet i steg 5, skilt med `; ` og ALDRI med komma:
   `…; wtsweep=<n>/<n>; wtsweep_named=<n>/<n>`. Gaten leser tokenet fram til mellomrom eller `;`,
   så `wtsweep=3/1,wtsweep_named=2/0` blir ett feilformet token ⇒ RØD. Feiler kallet, eller er
   ID-ene tapt (f.eks. etter kontekst-komprimering): skriv `wtsweep_named=feilet:<årsak>`; trærne
   tas da av døgnsweepen når `AGE_MIN` er passert. `--gate` leser KUN `wtsweep=`, og
   `wtsweep_named=` inneholder ikke den understrengen: den navngitte kjøringen kan verken gjøre
   gaten grønn eller rød.

   **Overgang (TODO 401):** 401s egen §6-rad SKAL bære både `wtsweep=` og `wtsweep_named=`.

   **Overgang: 380s egen §6-rad SKAL bære `wtsweep=` — kjør steg 4b allerede for 380-mergen**
   (fix-runde 3, mikro).
5. **Run-log merged-rad (dedup-guardet), FØR git-halen:**
   ```bash
   # $TS holdes KONSTANT ved en re-kjøring av samme §6-invokasjon (se «Re-kjørbarhet» under).
   ROW="$TS | $TODO_NR | $SLUG | merged | $PAUSE | $PR | $PRR | $CRR | $MODELS | - | $DEGR"
   grep -qF "$TS | $TODO_NR |" docs/superpowers/loop/run-log.md \
     || printf '%s\n' "$ROW" >> docs/superpowers/loop/run-log.md
   ```
   Telemetri: (a) ferdig-rapportens `todo_nr`, `slug`, `pr_url`; (b) egne kontekst-tellere
   (§4-revisjonsrunder → `$PRR`, §5b-kode-review-runder → `$CRR`; fast-path (§2b): `skipped`
   for hoppede stadier, `$PRR=0`); (c) Modeller-tabellen i `docs/orchestration-loop.md` →
   `$MODELS`; (d) `verification.e2e_outcome` + `verification.web_smoke_outcome` fra
   ferdig-rapporten → `$DEGR`, etter formelen i `run-log.md`:
   ```
   outcome=health                                       ⟹ degradation = "-"   (carve-out)
   outcome=paused UTEN ferdig-rapport                   ⟹ degradation = "-"   (carve-out)
   e2e_outcome == e2e_green OG web_smoke_outcome == e2e_green
                                                        ⟹ degradation = "-"
   ellers                                                  "e2e=<e2e_outcome>;web_smoke=<web_smoke_outcome>"
   ```
   Manglende `*_outcome`-felt i en ferdig-rapport (rader som HAR en rapport) ⟹
   `e2e_blocked:missing_outcome_field` for det manglende feltet — aldri stille `-`.
   `e2e_not_applicable` er IKKE en degradering, men logges eksplisitt (redundant nøkkel=verdi,
   ikke en slurvefeil — gjør kolonnen eksakt greppbar). Denne formelen skal være ordrett den
   samme i `run-log.md`, denne fila og deres genererte tvillinger — avvik er en ny
   silent-node-failure-kilde. `printf` (ikke heredoc-&&-kjede) unngår
   del-eksekverings-fellen. Dedup-nøkkelen er `timestamp | todo_nr` — **to rader for samme
   todo i samme minutt støttes IKKE av denne nøkkelen**; bruk et distinkt `$TS` per rad
   (129-presedensen, run-log 2026-07-11T18:52 ×2, er et historisk unntak FRA FØR denne
   guarden fantes — ikke en gjentakbar mal). Workers rører ALDRI run-log.md.

   **NB — notat-feltet (`selector=`/`floor=`/`viol=`/`floor_exempt=`/`pipelined_from=`/`parallel_with=`/
   `auto_decided=`/`attest=`/`vblock=`/`scout=`/`wtsweep=`) er IKKE med i `$ROW`-malen over.** De fleste
   appenderes som SISTE felt etter at raden er skrevet (§5b, §5c, §5d, § Pausepunkter) — feltets eget
   NUMMER er omstridt mellom spec-tabellen og de faktiske radene (eies av TODO 210, CF-246-1/CF-246-2,
   ikke løst av denne PR-en). `wtsweep=` er UNNTAKET: verdien er allerede kjent FØR raden skrives
   (§6 steg 4b over), så den skrives inn i notat-feltet SAMTIDIG med resten av raden i steg 5, ikke
   appendert etterpå — se steg 4b for hvorfor rekkefølgen er bindende (B1). `auto_decided=` er
   OBLIGATORISK på ALLE ikke-`health`-rader (også når verdien er `:0`)
   og FORBUDT på `outcome=health`-rader. `attest=` (TODO 250A) skrives i samme felt, KUN på rader
   som har hatt en §5b-kode-review, ALDRI på `outcome=health`-rader — og til forskjell fra
   `auto_decided=` er fravær IKKE et kontraktbrudd (`observe`, se §5b). `parallel_with=<annen-todo>`
   (TODO 233, §5d) skrives på BEGGE rader i en §5d-armert runde — A får `parallel_with=<B>`, B får
   `parallel_with=<A>` (og bærer `pipelined_from=<A>` I TILLEGG hvis B også var pipelinet via §5c;
   de to nøklene er ikke gjensidig utelukkende). Fravær av `parallel_with=` betyr «ikke parallell»
   og er ALDRI et kontraktbrudd — samme prinsipp som `pipelined_from=`.

   **`scout=<dispatches>d/<KB>kb` (lokaliserings-workeren).** Skrives i samme felt, på ALLE
   ikke-`health`-rader så lenge `scout.enabled` er `true` i `loop.config.yaml`. Summer
   `scout_usage` fra ALLE rapportene som gjaldt denne raden — plan-rapporten, ferdig-rapporten og
   hver fix-rundes ferdig-rapport — og regn `<KB>` som `bytes_read / 1024` avrundet til nærmeste
   heltall. Ingen scout brukt: `scout=0` (kortformen). Til forskjell fra `attest=`/`parallel_with=`
   er FRAVÆR HER ET KONTRAKTBRUDD: en manglende `scout=` kan ikke skilles fra en runde uten
   scout-bruk, og da måler serien ingenting — som er hele grunnen til at tokenet finnes. Mangler
   `scout_usage` i en rapport (og scout er på), be workeren om feltet i stedet for å gjette;
   fabrikkert telemetri er verre enn ingen. Kunne workeren ikke spørres i det hele tatt (sesjonen
   avsluttet uten rapport, eller rapporten har `status: "blocked"`/`"failed"` og likevel mangler
   `scout_usage`): skriv `scout=unknown` — ALDRI `scout=0`, som betyr «spurt, ingen brukt» og ville
   kollapset «ikke brukt» og «ikke kjent» til samme verdi (`report-schema.md` § frittekst-notatfelt).
   Er `scout.enabled` `false`, utelates tokenet helt.

   **Hva `scout=`-serien kan og ikke kan svare på.** `<KB>` er filinnhold scouten leste i stedet
   for en dyrere rolle — en ØVRE GRENSE for spart kontekst, ikke en besparelse (`report-schema.md`
   § Scout-rapport). Les den derfor som en TREND over mange runder, holdt opp mot rundenes øvrige
   form (`plan_review_rounds`, antall fix-runder, `vblock=`): stiger fix-rundene i takt med at
   `scout=` stiger, koster delegeringen kvalitet i stedet for å spare kontekst. Ett enkelt høyt
   tall betyr ingenting.
6. **Delt-state-git-hale (gjenbrukbar — samme blokk brukes av §6c/§7/§8/§8b, se der):**
   ```bash
   # 1. Speil-guard: HEAD er dev ELLER et rent speil (tip == origin/{{BASE_BRANCH}}, fordi
   #    {{BASE_BRANCH}} er utsjekket i et annet worktree) — ingen ikke-delt-state-commits.
   #    merge-base-formen er timing-robust uavhengig av fetch-rekkefølge: is-ancestor mot
   #    origin/{{BASE_BRANCH}} ville vært skjør avhengig av om origin/{{BASE_BRANCH}} er
   #    fetchet post-merge (etter at PR-en er merget ligger origin/{{BASE_BRANCH}} foran
   #    speilets HEAD, så is-ancestor ville feile på et ellers legitimt speil FØR neste
   #    fetch — den holder kun post-fetch). merge-base-formen passerer BEGGE (ekte
   #    {{BASE_BRANCH}} og rent speil, tom diff mot felles ancestor) og avviser en drevet
   #    feature-branch (kode-commits i diffen) — uansett fetch-rekkefølge.
   mb=$(git merge-base origin/{{BASE_BRANCH}} HEAD)
   non_shared=$(git diff "$mb"..HEAD --name-only | grep -vE '^(tasks/|docs/superpowers/loop/)' || true)
   [ -z "$non_shared" ] || { echo "FEIL: HEAD har commits utenfor delt state ($non_shared) — feil branch"; exit 1; }

   # 2. Stage KUN delt state — ingen glemt sti (fikser tidligere 'git add docs/'-glippen)
   git add -A tasks/ docs/superpowers/loop/

   # 2b. Delt-checkout-vern: indeksen deles med andre sesjoner i hovedsjekkouten — et `git add`
   #     derfra blir ellers med i denne commiten. `.githooks/pre-commit` er kun backstop.
   leaked=$(git diff --cached --name-only | grep -vE '^(tasks/|docs/superpowers/loop/)' || true)
   [ -z "$leaked" ] || { echo "FEIL: stagede filer utenfor delt state: $leaked — av-stage med 'git restore --staged <fil>'"; exit 1; }

   # 3. Commit — tolerer «ingenting å committe» (idempotens ved re-kjøring)
   git diff --cached --quiet && echo "ingenting å committe" || git commit -m "$MSG"

   # 4. Synk + push: fetch henter mergede PR-er, rebase replayer delta, push via HEAD-refspec
   git fetch origin {{BASE_BRANCH}} \
     && git rebase origin/{{BASE_BRANCH}} \
     && git push origin HEAD:{{BASE_BRANCH}}
   ```
   `$MSG` for §6 = `"chore(loop): TODO $TODO_NR delt-state — $SLUG"` (fast-path: append
   `(fast-path; presedens: TODO XXX / lesson YYYY-MM-DD)` per §2b-audit-kravet).

   **`$MSG`-suffiks ved ADVARSEL fra §0b (VIKT-6 fra r2, r5-formen):** er rundens ADVARSEL-teller
   `> 0`, append `(wtwarn=<n>: <role>@<basename> — <reason>; …)` til `$MSG` (maks tre oppføringer,
   deretter `…`). `<role>` ∈ `planner` | `plan-reviewer` | `code-reviewer` | `implementer`.
   `<basename>` er worktree-katalogens navn (`agent-<hex>`) — **aldri den absolutte stien**.
   `<reason>` er ett ord fra enumet `dirty` | `locked` | `artifact-missing` | `cmd-error` |
   `branch-not-deleted` | `preexisting` | `snapshot-missing` | `unknown-path` |
   `handoff-mismatch` | `branch-mismatch`. ADVARSLER som oppstod
   på et pipelinet B-spor føres i A sin melding, med `<B-nr>:` foran rolle-leddet. Samme presedens
   som fast-path-parentesen over. Kanalen bærer ÅRSAK og dekker **kun mergede runder** — abort-
   runder når aldri §6 og dekkes av pause-rapporten (§5, «Bevaringsregel ved abort»). Den
   maskinlesbare TELLEREN `wtwarn=<antall>` i `run-log.md` eies av TODO 194B — denne suffiksen er
   ikke det.

   **Re-kjørbarhet, ikke atomisk:** commit→fetch→rebase→push er IKKE én atomisk operasjon —
   seksjonen er derfor «seriell, re-kjørbar», ikke «atomisk». Recovery:
   **(a)** commit OK men push avvist → re-kjør HELE git-halen (steg 1–4 over); speil-guarden
   passerer fortsatt (ingen nye ikke-delt-state-commits), og steg 3 blir automatisk
   «ingenting å committe» (allerede committet). Ved denne recoveryen re-kjøres **KUN
   git-halen — ALDRI rad-/retro-appendene** (run-log-rad i steg 5, §8-retro-entry): de står
   allerede i working tree/er allerede committet, og re-kjøring av selve append-kommandoen
   ville trigget dedup-guardens «allerede der»-gren uansett, så det er unødvendig arbeid.
   (Dette er også grunnen til at §6c sin health-rad IKKE trenger egen dedup-guard — den
   berøres aldri av denne recoveryen.)
   **(b)** rebase-konflikt → ⚠️ PAUSEPUNKT: release claim, eskalér til mennesket.

## 6b. Drain bug-innboks (hver syklus, kun koordinator)

Sjekk `tasks/bugs/inbox/` for nye `bug-*.md` (mennesker slipper dem her — én fil per bug, ingen konflikt). For hver:
- **Reell, ikke-planlagt bug** → legg en oppføring i `tasks/bugs.md` (format: se eksisterende).
- **Bug som bør fikses nå** → forfremm til en ny todo (`tasks/todos/todo-NN-fix-<slug>.md`, sett `priority` etter innboks-filens vurdering).
- **Ugyldig/duplikat** → noter og forkast.
Slett den drainede innboks-fila etterpå. Dette er koordinatorens skriving (single-writer) — mennesker rører aldri `bugs.md` selv.

## 6c. Helsesjekk + release-rådgiver (betinget, kun koordinator)

**Koordinatoren** kjører `/loop-health-check` (`.claude/commands/loop-health-check.md`) når én av
to deterministiske triggere slår inn. Workers dispatches aldri til denne oppgaven — single-writer-
kontrakten gjelder.

### Triggerlogikk

**Trigger 1 — Kø tom / grooming (§7):** Kjør §6c FØR grooming-forslag, slik at mennesket får
en samlet statusrapport samtidig. Helseraden som skrives nullstiller merge-telleren (Trigger 2).

**Trigger 2 — Hver N-te merge (N={{HEALTH_CHECK_INTERVAL}}):** Tell rader med `outcome=merged` etter den *siste* raden
med `outcome=health` i `docs/superpowers/loop/run-log.md`:

```bash
awk '
  /\| health \|/ { count=0; next }
  /\| merged \|/ { count++ }
  END { print count }
' docs/superpowers/loop/run-log.md
```

Count ≥ {{HEALTH_CHECK_INTERVAL}} → kjør §6c nå (før neste dispatch). Helseraden som §6c skriver blir den nye
nullstillings-markøren. Ingen health-rad ennå → tell fra toppen av fila.

**Begge triggere skriver en health-rad** → telleren nullstilles alltid uansett hvilken som fyrer.

**Persistering:** health-raden appendes til `docs/superpowers/loop/run-log.md` (ingen dedup-guard
her, se «Re-kjørbarhet»-noten under §6 steg 6 for hvorfor det ikke trengs), deretter kjøres
**Delt-state-git-halen** (§6, steg 6 — samme blokk, `$MSG="chore(loop): helsesjekk — health-rad"`).
`loop-health-check.md` Del C appender kun raden selv — commit/push skjer via denne halen; ingen
edit i `loop-health-check.md` er nødvendig.

### Etter §6c

- Grønn helsesjekk → kjør §8b (drain retro-logg), deretter §8c (agér på tallene — uten denne
  forover-pekeren lærer en koordinator som leser ovenfra og ned aldri at steget finnes),
  fortsett så normalt (til grooming eller neste todo).
- Rød helsesjekk (regresjon eller infra-feil) → ⚠️ PAUSEPUNKT: eskalér til mennesket med detaljer,
  sett `pause_event=helsesjekk-rød` i health-raden, release evt. aktiv claim og stopp loopen.
  §8b og §8c kjøres IKKE.

**TODO 246 — Del D:** `/loop-health-check` kjører i tillegg Del D (regelmotor-selvtest,
regel-paritet, monoton decision-log, nivå-B-oppsummering + avstemming mot run-loggen) som en del av
DENNE helsesjekken, FØR «Etter §6c» over evalueres — se `loop-health-check.md` Del D. Rødt i Del D
er samme klasse som Del A/A6: rød helsesjekk, §8b kjøres IKKE.

## 6d. Worktree-sweep (hver syklus, kun koordinator)

**Selve kjøringen skjer i §6 steg 4b, IKKE her** (fix-runde 1, B1) — denne seksjonen beskriver
HVORFOR mekanismen finnes og HVA den gjør; §6 steg 4b eier NÅR den kjøres. Tidligere sto det her
at kallet skjedde «etter §6b», som i praksis betydde etter at §6 steg 5 allerede hadde skrevet
raden — en rad kan ikke få `wtsweep=` ettermontert. Ett steg, ingen skjønn: `$WTSWEEP`-verdien
fanget i §6 steg 4b skrives inn i DENNE syklusens §6-rad i run-log.md, som en del av selve
rad-skrivingen i steg 5 — ikke som en etterfølgende redigering. Hentes ordrett fra sweepens egen
oppsummeringslinje, ikke anslått.

**Gaten (§6c, Del A) er token-basert, ikke tidsstempel-basert** (fix-runde 2, B1). Den leser
INNHOLDET i siste §6-rad i run-log.md og krever at raden bærer et `wtsweep=<n>/<n>`-token. Grunnen
til at et tidsstempel-sammenligning ble forkastet i fix-runde 1: selv med riktig rekkefølge
(steg 4b FØR steg 5) kan steg 5 skrive raden i et SENERE minutt enn sweepens egen `ts`, som by
construction gjør sweepens tidsstempel eldre enn radens — falskt RØDT på en sweep som faktisk
kjørte i samme syklus. Et innholds-sjekk er immun mot denne racen fordi den ikke sammenligner
tidspunkter i det hele tatt.

**Radfilteret er POSITIVT, IKKE et negativt helse-unntak** (fix-runde 3, mikro — retter en påstand
som tidligere sto her og feilaktig hevdet «samme skille som §6c Trigger 2»: Trigger 2 sin
`awk`-teller bruker BEGGE literalene `| health |` og `| merged |` sammen i én tilstandsmaskin, mens
gaten her bruker KUN `| merged |` alene, positivt). Kolonne 4 i run-log.md har flere verdier enn
`merged`/`health`: målt på dev er fordelingen `merged` 113, `paused` 20, `health` 19, `resumed` 5,
`housekeeping` 1. Et negativt filter (`grep -v health`) ville latt en `paused`/`resumed`/
`housekeeping`-rad telle som «siste §6-rad» og gitt falskt RØDT, siden disse radtypene ikke
nødvendigvis bærer `wtsweep=`. Gaten leter derfor etter siste rad med literalen `| merged |` og
ignorerer alt annet (health, paused, resumed, housekeeping) uansett hvor de står i loggen.

**Hvorfor denne finnes ved siden av §0b.** §0b er en per-runde sikkerhetsgate med seks vakter, og
den feiler med rette LUKKET: ved enhver advarsel er utfallet «INGEN rydding». Konsekvensen er at
hver agent som dør, avbrytes, eller etterlater en foreldreløs lås, legger igjen et tre som INGEN
senere plukker opp. Det er ikke en defekt i §0b — det er et manglende oppsamlingssteg bak den.
Målt 2026-09-09: 30 trær, 4,1 GB, det eldste flere uker gammelt, og disken gikk full som følge.
Målt igjen 2026-09-21 (TODO 380): sweepen hadde ALDRI kjørt (`grep -c wtsweep run-log.md` = 0) —
72 trær, 19,4 GB, og `--dry-run` viste at den ville slettet treet som bar HEAD-branchen til en
åpen PR.

**Sweepen er ikke en svakere §0b.** Den har et annet kriterium, valgt fordi det er billig å
verifisere og umulig å ta feil av: et tre fjernes kun når **ingenting i det kan gå tapt**.

1. HEAD finnes på en remote branch (`git branch -r --contains`) ⇒ ingen commit kan gå tapt. Er
   dette IKKE tilfelle (typisk squash-merge, der HEAD-committen selv aldri lander på integrasjons-
   branchen), eller er treet skittent: `tasks/worktree-landed.sh` avgjør INNHOLDSMESSIG om alt som
   ikke er committet trygt likevel finnes der (samme sti, omdøpt/arkivert, eller flyttet — se fila
   for klassene). Kun et rc 0 fra den (LANDED) tillater fjerning; alt annet ⇒ BEHOLD. Filer den
   melder `LANDED-MOVED` reddes til `.claude/worktree-rescue/<ts>/` og verifiseres byte-for-byte
   FØR treet fjernes.
2. Ingen ÅPEN PR bærer denne worktreens HEAD — verken via branch-NAVN eller commit-ancestry mot en
   åpen PRs `headRefOid` (en implementer som fortsetter på et lokalt `fix-…-local`-navn er vanlig
   praksis og må ikke miste vernet fordi navnet ikke matcher PR-branchen).
3. En lås som peker på en LEVENDE pid respekteres. En foreldreløs lås (pid borte, typisk etter
   maskin-restart) er ikke et vern — den er søppel fra en død agent. Låsen kan også SLIPPES mens
   agenten fortsatt lever (målt) — den er en bonus, ikke et liveness-signal.
4. Treet er ikke rørt de siste `AGE_MIN` minutter (default 1440) — vern mot en levende, TENKENDE
   agent uten skriving og uten lås. Målt 62 og 218 minutter uten skriving i to levende trær samme
   dag — en lavere terskel ville IKKE beskyttet dem.

   **Unntak — navngitt kjøring (§6 steg 4b, TODO 401):** trær som navngis der, tilhører agenter
   som har returnert; aldersvakten hoppes over for dem. Alle andre vakter gjelder uendret.
5. Enhver kommandofeil underveis (status, `gh`, `git branch -r`, `find`) ⇒ BEHOLD, aldri stille
   videre som om svaret var «ingen treff».

Rescue-katalogen er gitignorert. Se på den kun hvis noe faktisk mangler; commit derfra bare det som
viser seg å være ekte arbeid. Ved tvil: `--dry-run` rapporterer uten å røre noe.

**Innkalling er mekanisk, ikke prosa (TODO 380).** `/loop-health-check` Del A kjører
`./tasks/worktree-sweep.sh --gate`, som leser siste ikke-helse-§6-rad i run-log.md og feiler
RØDT (§8b kjøres ikke) hvis den raden mangler `wtsweep=<n>/<n>`-tokenet eller bærer et
feil-formet ett (`wtsweep=feilet:…`) — se §6 steg 4b/5 for hvorfor det er nettopp raden, ikke en
tidsstempel-sammenligning, som avgjør (fix-runde 2, B1). `tasks/metrics/worktree-sweep-log.jsonl`
er ren diagnostikk og leses ikke av gaten. `/todo-done` steg 13b kjører KUN `--dry-run` + `--gate`
— den sletter aldri selv; gaten er mekanismen som gjør en uteblitt sweep synlig, ikke steg 13b.

**Docker prunes aldri automatisk, og sweepen rapporterer det ikke lenger (TODO 401; gjelder kun prosjekter med Docker-basert testharness)** — `docker
info` hang ~50 min mot en hengende daemon (tørrkjøring 2026-09-25) og holdt sweepen etter at
vurderingen var ferdig; macOS har ingen `timeout`, og `perl -e 'alarm …'` stopper ikke
docker-CLI-en (målt). En kjørende harness-container eier volumet sitt. Er `disk_ledig=` lav, kjør
`docker system df` for hånd; viser den `Containers=0B`, er `docker volume prune -f` trygt.
Et database-image som f.eks. Postgres deklarerer `VOLUME /var/lib/postgresql/data`, så hver
container uten navngitt volum lager et anonymt et; ryddes containeren aldri (daemon hang, disk full, agent avbrutt), blir volumet stående.
Målt 2026-09-09: 465 anonyme volumer, 18,7 GB. Dette er en selvforsterkende sløyfe — full disk gir
hengende daemon gir uryddede containere gir fullere disk — så les tallet, ikke bare hopp over det.

## 7. Grooming-modus (kø tom)

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

## 8. Mini-retro (kø-tom/stopp)

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

## 8b. Drain retro-logg (ved §6c-helsesjekk — begge triggere — kun koordinator)

**Modellert nøyaktig på §6b (drain bug-innboks)** — samme single-writer-mønster, samme sjanger.
Trigges av §6c-helsesjekk, begge triggere (se «Etter §6c»-forover-pekeren — uten den ville en
koordinator som leser §6c ovenfra og ned aldri lære at dette steget finnes): ved Trigger 1
(kø-tom/grooming) kjøres §8b FØR §7s grooming-forslag skrives (se forover-peker i §7); ved
Trigger 2 (hver N-te merge) kjøres §8b rett etter helseraden er skrevet, uavhengig av om
grooming kjører i samme runde. Uten denne todelte kadensen fyrer §8b nesten aldri — kø-tom er en
sjelden hendelse sammenlignet med merge-takten (opphav: TODO 174 fix-mode).

**TODO 246 — nivå B6:** hvilke Forbedringsforslag-linjer som forfremmes (`promoted`) eller lukkes
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
gang (opphav: TODO 174 fix-mode runde 2). Ved Trigger 1 (kø-tom) teller det §8b faktisk
promoterer denne runden i tillegg mot §7s EGNE, separate rundebudsjett på inntil 3 (se §7) — to
uavhengige tak som begge må være oppfylt, ikke ett delt tak.

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
  mennesket og stopp» (opphav: TODO 174 fix-mode runde 2-funn — hver Trigger-2-kjøring som
  skrev noe, stoppet loopen ved neste todo, siden ingen hale committet den).

`retro-triage.md` er runtime-state (seed-only, samme vern som `run-log.md`/`retro-log.md` — se
lesson 2026-06-30): filen seedes av `/setup` én gang og regenereres ALDRI (kun appendes av
koordinatoren).

`docs/superpowers/loop/retro-log.md` selv røres IKKE av dette steget — den forblir ren
append-only observasjonslogg (§8 skriver dit, ikke §8b). Kun `retro-triage.md` skrives til her.

## 8c. Agér på tallene (ved §6c-helsesjekk — begge triggere — kun koordinator)

**Hvorfor dette steget finnes.** Vi måler mye — `measure-cost.py`, `run-log.md`,
`decision-log.md`, `retro-triage.md`, lessons-filene — og fram til 2026-09-17 var det ingen
prosedyre som PLIKTET noen å gjøre noe med det som ble målt. Resultatet var målbart: 29 av 33
BLOKKERENDE review-funn den uka tilhørte én og samme feilklasse — «en vakt som ikke kan bli rød
av riktig grunn» — og hver enkelt ble funnet på nytt, av en fersk reviewer, til full pris.
Mønsteret lå i tallene fra dag to. Eieren måtte peke på det. Det er den feilen dette steget
lukker: *tall og statistikk er ikke verdt noe om ingen agerer på dem.*

Kjøres rett etter §8b, ved begge §6c-triggere, og **kun ved grønn helsesjekk** (rød helsesjekk
er et pausepunkt — da kjøres verken §8b eller §8c).

### Steg 1 — mål, to kilder

```bash
python3 tasks/lesson-classes.py --days 7      # feilklasser i lessons
python3 tasks/measure-cost.py "$(date -v-30d +%F)" --trend   # 30-dagersvindu: kostnad, review-runder, Gate F, $/dag
```

`--trend` skriver de samme fire dommene som Trend-seksjonen i måle-artifactet, fra samme
datauttrekk og samme terskelfunksjon — så en graf som viser oppgang og en §8c-kjøring som sier
«uendret» kan ikke sprike. Den avslutter med **exit 1** hvis minst én måling har gått feil vei.

Alle fire målingene er «lavere er bedre», og dommen er snittet av de siste N mot de N før
(N ≤ 5, minst 3 på hver side). Under 3+3 punkter skriver den «for få til en retning» i stedet for
en pil — en retning utledet av to punkter er støy, og en pil ville påstått noe dataene ikke bærer.

Vinduet er 7 døgn fordi det er langt nok til at en klasse rekker å gjenta seg, og kort nok til
at en klasse vi allerede har gatet faller ut av det igjen. Scriptet klassifiserer hver lesson i
ÉN primærklasse (tittel + `**Problem:**`-linja; ikke `**Løsning:**`/`**Unngå:**`, som nesten
alltid nevner et verktøy uten at DET er feilklassen) og rangerer klassene etter volum.

### Steg 2 — les handlingslinja

Hver kilde skriver enten en «ingen handling»-linje eller en `§8c-HANDLING`-linje:

- `Alle forekommende klasser har en mekanisk gate. Ingen §8c-handling.` og `Ingen måling går feil
  vei.` → ferdig. Ingen rad, ingen commit. Dette er det normale utfallet, og steget koster da under
  ett sekund.
- `§8c-HANDLING: «<klasse>» (N lessons) er den høyest rangerte klassen uten mekanisk gate.` →
  gå til steg 3.
- `§8c-HANDLING (måletall): «<måling>» <endring>` → gå til steg 3.

Fyrer begge, håndteres begge — de er to ulike spørsmål («hvilken feil gjentar vi?» og «hvilket
tall går feil vei?»), ikke to varsler om det samme. Taket på én klasse per kjøring gjelder
lesson-siden; måletall-siden har sjelden mer enn én måling i rødt om gangen, og har den det, ta
den største.

**Terskelen er gate-dekning, ikke et råtall.** Første versjon av scriptet brukte «≥ 3 forekomster
på ≤ 7 dager ⇒ plikt», og fikk 6 av 6 klasser over terskel på første kjøring. En teller som alltid
utløser er nøyaktig like verdiløs som en vakt som aldri blir rød — samme feilklasse som steget
finnes for å bekjempe. Kriteriet er derfor: *klassen forekommer OG ingen mekanisk gate dekker den
ennå*, og **maks én klasse håndteres per §8c-kjøring** (kostnadsgrep: én handling per helsesjekk,
ikke en liste).

### Steg 3 — handle. Nøyaktig ett av tre utfall, alle logget

Utfallet er nivå B (bestem selv, logg, mennesket kan vetoe). Rad i `decision-log.md`, format som
presedensen `### 2026-09-17 03:10 — §6c/e2e [B]: …`:

```
### <dato> <tid> — §8c [B]: <klasse> — <gate innført | todo NN | ikke gatebar: grunn>
```

| Utfall | Når | Hva du gjør |
|---|---|---|
| **a) Innfør gaten nå** | Regelen er mekanisk uttrykkbar og koster < ~30 linjer | Legg regelen **der klassen faktisk kan observeres**: `tasks/vblock-lint.py` for mønstre som står i en planfil, ellers en hook i `.claude/hooks/`, et eget script under `tasks/`, eller et CI-steg. Linteren leser kun planfiler, så en klasse som ikke er et planfil-mønster (f.eks. branch-alder) er fortsatt gatebar — bare ikke der. Legg nye linter-regler inn som SOFT først (se nivå-noten der). Oppdater `GATES`-tabellen i `tasks/lesson-classes.py` slik at verdien **peker på stedet gaten faktisk kjører**, og **motprøv begge veier**: regelen MÅ være rød på et navngitt, datert historisk eksempel fra klassen og ren på den fiksede formen. Uten motprøven har du lagt til en vakt av samme klasse du prøvde å gate — og fordi en ikke-tom `GATES`-verdi filtrerer klassen ut av `ungated`, slår du den da permanent av for §8c. En gate som ikke er koblet inn noe sted kan aldri bli rød: da er raden «regelsett skrevet, ikke koblet inn», ikke «gate innført», og `GATES` skal stå tom. |
| **b) Fremm til todo** | Gaten er reell, men for stor for en helsesjekk | Todo-utkast (`status: deferred`, `tags: [forslag]`), og `ref=TODO NN` i decision-log-raden. Teller mot §8bs utestående-tak på 3. |
| **c) Ikke gatebar** | Klassen krever skjønn en maskin ikke har | Skriv grunnen i raden, og sett klassens `GATES`-verdi i `tasks/lesson-classes.py` til `'ikke gatebar: <grunn>'` — ellers foreslår scriptet den samme klassen ved hver eneste helsesjekk. |

**For en måletall-handling** er de samme tre utfallene: (a) innfør tiltaket nå, (b) fremm til todo,
(c) forklart avvik — men (c) krever her en ÅRSAK, ikke bare «ikke gatebar». En kostnadsøkning som
skyldes at loopen kjørte flere timer den dagen er en forklaring; «tallet svinger» er ikke. Skriv
årsaken i raden, så neste §8c kan se om den fortsatt holder.

**«Ingenting skjedde» er ikke et lovlig utfall.** Er handlingslinja der, skal én av de tre radene
skrives. Det er hele poenget med steget.

### Steg 4 — mål effekten av forrige §8c-handling

Før du forlater steget: finn forrige `§8c [B]`-rad i `decision-log.md` og sjekk om klassen den
handlet på faktisk har falt. To kilder, begge mekaniske:

```bash
# Hvor ofte gaten faktisk fyrer. `log_run()` skriver nøkkelen `hard` (ikke `level`) —
# verifisert mot en ekte loggrad 2026-09-17. Feiler kommandoen med «No such file»,
# har linteren aldri kjørt med `--log`, og svaret er «ukjent», ikke «null».
# Tallet teller HARD-FUNN, ikke bekreftede defekter — en falsk positiv teller likt.
# Les det sammen med `rules`-feltet i samme loggrad og med klassens fall i
# `lesson-classes.py`, aldri alene.
python3 -c 'import json; print(sum(json.loads(l)["hard"] for l in open("tasks/metrics/vblock-lint-log.jsonl")))'
python3 tasks/lesson-classes.py --days 7 --json | python3 -c \
  'import json,sys; d=json.load(sys.stdin); print({k: len(v) for k, v in d["classes"].items()})'
```

Falt klassen ikke etter to helsesjekker, var gaten feil gate — noter det i den nye raden og
vurder utfall (b) eller (c) i stedet. En gate som er innført og aldri fyrer er ikke et bevis på
at klassen er borte; den er like ofte et bevis på at gaten ikke kan se klassen.

**Persistering:** endringer i `tasks/`, `docs/superpowers/loop/` og decision-log-raden committes
via **Delt-state-git-halen** (§6, steg 6) med `$MSG="chore(loop): §8c — <klasse>"`. Ved Trigger 1
fanges de av §7s hale (samme mønster som §8b); ved Trigger 2 MÅ §8c kjøre halen selv — ellers
treffer neste todo §0s «Working tree ikke ren → stopp».

## 9. Todo-nummer: reservasjon, kollisjon og renummerering

Racet ved *valg* av `nr` kan ikke lukkes uten atomisk reservasjon. §6.4 gate (b) evaluerer
merge-RESULTATET og fanger den andre siden av en kollisjon rett før merge — men krymper, lukker
ikke, vinduet. Risikoen øker med §5c/§5d (flere spor i flukt) og med flere koordinator-sesjoner.

**Valg av nr:** `git fetch origin {{BASE_BRANCH}}`, så `sh scripts/check-todo-nr-collisions.sh --next`
(regner mot arbeidstreet ∪ `origin/{{BASE_BRANCH}}`). Gjelder hver ny todo — grooming (§7),
bug-triage (§6b) og forslag.

**Reservasjon teller FØRST når** minimal frontmatter (tittel + `nr` + status) er committet **og
pushet** til `{{BASE_BRANCH}}`. Commit og push den minimale fila FØR resten skrives. Todos som
fødes inne i en feature-PR er ikke reservert — de bæres av §6.4 gate (b).

**Retningsregel: «sist inn flytter».** Ved kollisjon renummererer PR-en som ennå ikke har merget;
den allerede mergede står urørt.

**Renummerering** (trigges av gate (b) exit 1, eller exit 3 med en reell nr-kollisjon under
`tasks/todos/`):
1. Nye nr med `--next` mot fersk `origin/{{BASE_BRANCH}}`; for en epic tas alle N samtidig.
2. `git mv` filnavn + oppdater `nr`, `order`, `deps` (og `plan:`/planfilnavn).
3. Prosa: `git grep -niE 'todo-0*<gammelt-nr>([^0-9]|$)' -- tasks docs` — klassifiser **hvert**
   treff. Vakten validerer kun `nr`-unikhet og er grønn mens prosa peker på feil todo.
4. Bare-tall-referanser (`438–443`) fanges ikke av grep — les de flyttede filene manuelt
   (`git diff --name-only`). Sjekkliste, ikke vakt.
5. Re-kjør gate (b) før nytt merge-forsøk.

## Pausepunkter (nivå A — spør + eskalér; nivå B — bestem selv, logg, mennesket kan vetoe, TODO 246)

**Klassifiser ALLTID mekanisk, aldri fra hukommelsen:**
```bash
python3 tasks/decision-level.py --event <navn> --context k=v...
```
stdout: `{"level":"A"|"B","rule":"<id>","trigger":"…","obligations":[…],"violations":[…]}`.
`rule = "A0"` er fail-closed (ukjent hendelse, manglende påkrevd kontekst, eller rundetak
overskredet) — `level` er da ALLTID `"A"`, exit-koden ≠ 0, og valget behandles som et vanlig
nivå-A-pausepunkt under. Et ikke-klassifiserbart valg blir ALDRI stilltiende et nivå-B-valg.
`--dump-rules`/`--self-test` finnes for verifisering — se `loop-health-check.md` Del D.

**Alle punktene under er nivå A** (uendret oppførsel: STOPP, release claim, eskalér) **med unntak
av kode-reviewer-revise-gate-punktet**, som nå er delt i nivå A og nivå B1 — se undertabellen.

- Teknisk risiko flagget (§4) eller truffet (§5/§6)
- Brainstorm-påkrevd todo (hoppet over i §1)
- Reviewer no-go som ikke konvergerer etter 2 runder (§4)
- Kode-reviewer revise-gate — **nivå B1 innenfor taket** (koordinatoren bestemmer selv og logger,
  se «Nivå B»-tabellen under); eskalerer til mennesket (nivå A, uendret pausepunkt-oppførsel) KUN
  når den ene ekstra fix-runden `extra_allowed`-budsjettet ga (`code_review_rounds = 3`) også er
  brukt og revise-gaten fortsatt ikke er tom (§5b)
- Agent-probe i preflight feiler («Agent type not found», dekker §5b) → fersk koordinator-sesjon kreves
- Merge-konflikt (§6.4)
- Rebase-konflikt i delt-state-git-halen (§6/§6c/§7/§8/§8b)
- Ferskhets-gaten for en pipelinet plan er fortsatt ikke-tom etter én re-plan-runde (§5c)
- `git`/working-tree ikke ren (§0)
- `canary`-mismatch som ikke løses (§3)
- Helsesjekk rød (§6c) — regresjon eller infra-feil i integrert `{{BASE_BRANCH}}`

### Nivå A — regeltabell (`decision-level.py`, A1–A8)

| ID | Trigger |
|---|---|
| A1 | Skriving mot prod-miljøet (`{{PROD_ENV_ID}}`) eller kjøring av `{{RELEASE_COMMAND}}` |
| A2 | Env-variabler, secrets eller vault |
| A3 | Native/EAS-bygg, TestFlight-distribusjon eller iOS-Modal-endring |
| A4 | Push eller merge til `{{PROD_BRANCH}}` |
| A5 | Destruktiv eller irreversibel operasjon (datasletting, force-push, drop) |
| A6 | Avvik fra `CLAUDE.md` eller `docs/naming-conventions.md` som krever menneskets bekreftelse |
| A7 | Apply av migrasjon eller RLS-endring mot dev (`{{DEV_ENV_ID}}`) |
| A8 | Edge Function-deploy (dev eller prod) |

De ti punktene i lista over er egne, ELDRE pausepunkter (utenfor `decision-level.py`s
15-rads regeltabell) og forblir nivå A uansett — A1–A8 dekker et ANNET, mer spesifikt sett
hendelser (prod-skriving, secrets, native, `{{PROD_BRANCH}}`, destruktive operasjoner,
naming-avvik, migrasjon/RLS mot dev, Edge Function-deploy) som koordinatoren klassifiserer
eksplisitt før den handler (§2c, §5c).

### Nivå B — regeltabell (`decision-level.py`, B1–B7)

| ID | Trigger |
|---|---|
| B1 | §5b revise-gate **etter 2/2**: én ekstra målrettet fix-runde (runde 3) vs. merge m/carry-forwards vs. stopp — og de samme valgene innenfor taket |
| B2 | Splitt av en todo i del-todos |
| B3 | Valg eller hopp av neste todo innenfor mennesket-godkjent rekkefølge (§1) |
| B4 | Pipelining: valg eller drop av B-sporet (§5c) |
| B5 | Godkjenning av `technical_risk` fra **plan-rapporten** når `kind ∈ {docs_selfmod, hook_selfmod}` **og** `executable_gate = true` |
| B6 | Retro-triage: hvilke retro-observasjoner som promoteres eller lukkes (§8b) |
| B7 | §4 plan-review: ny revisjonsrunde vs. drop/`open` — **kun når `plan_review_rounds < 2`** |

**Pinnet (mot tvetydighet):** rundebetingelsene i B1/B7s triggertekst over («etter 2/2»,
«kun når `plan_review_rounds < 2`») er PROSA for menneskelesere og for V7-paritet mot
`--dump-rules` — de er IKKE en betingelse i selve B1/B7-regelmatchingen i `decision-level.py`.
Rundetak bor UTELUKKENDE i rundetak-vakten under; B1 matcher på `event=revise_gate_choice` +
`action ∈ {fix_round, merge_carry, stop}` alene, og B7 matcher på `event=plan_review_choice` +
`action ∈ {revise, drop}` alene. **B5 krever begge betingelser** (`kind`  OG `executable_gate`);
et `technical_risk` med `kind=migration` treffer A7 fordi B5s `kind`-betingelse er usann — IKKE
fordi A7 evalueres først (rekkefølgen A-block-før-B-block er likevel reell og bindende, se
skriptets docstring). **`technical_risk` fra en REVIEWER (ikke planneren) bærer aldri
`kind`/`executable_gate` og klassifiseres derfor ALLTID som nivå A** — B5 gjelder kun
plan-rapportens `technical_risk` (§4 «Ved `technical_risk.flagged`» over). **`hook_selfmod`s
eksakte scope** (hvilke filer i `.claude/hooks/` som teller, og at hooks som håndhever en
nivå-A-invariant som `guard-main-merge.sh`/`guard-supabase-ref.sh` ALDRI er B5 uansett
`executable_gate`) er definert i `report-schema.md` — B5-raden over gjentar den ikke, for å
unngå at D2s ordrette paritet-diff (tabellrad ↔ `TRIGGER_BY_ID`) driver fra scope-prosaen.

**Rundetak-vakt (evalueres FØR alt annet i `decision-level.py`, uavhengig av `--event`):** taket
er **2** (frosset fra §4/§5b-eskaleringene). `extra_allowed = 1` er et **FIX-RUNDE-BUDSJETT** for
`revise_gate_choice`-siden alene — IKKE et globalt rundebudsjett: å LUKKE gaten (`merge_carry`/
`stop`) er alltid B1, uansett hvor mange runder som allerede er brukt. Kun et NYTT `fix_round`-
forsøk utover budsjettet er A0.

| `code_review_rounds` | `action=fix_round` | `action ∈ {merge_carry, stop}` |
|---|---|---|
| `0`–`1` (innenfor taket) | **B1** | **B1** |
| `2` (revise-gate 2/2) | **B1** (autoriserer runde 3) | **B1** |
| `3` (den ene ekstra er brukt) | **A0** — en fjerde fix-runde krever mennesket | **B1** (lukking er fortsatt B) |
| `≥ 4` | **A0** for et NYTT fix-runde-forsøk | **B1** (lukking er fortsatt B, uansett rundetall) |

Uavhengig av tabellen over: **ved `code_review_rounds >= 2` er `--context decision_logged=yes`
PÅKREVD for ETHVERT `--event`**, ikke bare `revise_gate_choice` — en koordinator kan ikke smugle
rundekontekst forbi loggplikten via et annet hendelsesnavn (lukker et BLOKKERENDE plan-review-
funn om event-navn-lekkasje).

**Residual, navngitt — IKKE lukket, hverken av skriptet eller av Del D4 i denne PR-en:**
`decision_logged=yes` og run-loggens `code_review_rounds` skrives av SAMME aktør (koordinatoren) i
samme runde — en under-rapportering av begge likt ville passere klassifiseringen uoppdaget her, og
V14/V16 er konsistenskontroller mellom to selvrapporter, ikke verifisering mot en uavhengig kilde
(plan-review r2, VIKTIG-funn 2). Forberedt, men IKKE koblet inn: hver `[B1]`/`[A0]`-decision-log-
entry for en `revise_gate_choice`-beslutning bærer i tillegg **`Runde-SHA:`** — den samme
`pr_head_sha` §5b «Trigger-sett»-steget allerede pinner for den runden (§5b over, `gh pr view <pr>
--json headRefOid`). En fremtidig todo kan la `loop-health-check.md` Del D4 verifisere at hver slik
SHA faktisk finnes (`git cat-file -e`) og at antall DISTINKTE runde-SHA-er for todoen er
`>= code_review_rounds - 1`; **denne PR-en skriver kun feltet** — se `loop-health-check.md` Del D4
«Residual» for den eksplisitte, dokumenterte avgrensningen (ingen `git log`-avhengig gate er lagt
til Del D ennå).

**De fire logg-pliktene (alle fire, ellers er det ikke et gyldig nivå-B-valg):**

1. Decision-log-entry i frosset format (`docs/superpowers/loop/decision-log.md` § Format) — for
   `revise_gate_choice`-beslutninger ved `code_review_rounds >= 2` bærer entryen i tillegg
   `**Runde-SHA:** <sha>` (se «Residual» over).
2. `auto_decided=<rad-eier>:<antall>` i `run-log.md` felt 11, ved siden av `selector=`/`floor=`/
   `pipelined_from=` (se §6 steg 5).
3. Én linje i sluttmeldingen: `<regel-id> — <kort valg> (reversibel til <punkt>; veto: svar i
   chatten)`.
4. Regel-IDen er hentet fra `python3 tasks/decision-level.py`, ikke fra hukommelsen.

**Veto:** mennesket kan når som helst svare i chatten og overstyre et logget nivå-B-valg —
koordinatoren ruller da tilbake til «Reversibel til»-punktet i decision-log-entryen.
