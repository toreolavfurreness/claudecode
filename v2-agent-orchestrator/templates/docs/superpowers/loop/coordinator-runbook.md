<!--
  GENERERT av /setup fra loop.config.yaml — IKKE rediger her.
  Endre loop.config.yaml og kjør /setup på nytt.
-->

# Koordinator-runbook (fase 0, live-sesjon)

Du er koordinatoren. Du er eneste skriver til delt state. Workers gjør tungt arbeid i isolerte worktrees og returnerer rapporter (`report-schema.md`).

> ⚠️ **Forutsetning:** koordinatoren MÅ kjøre i en sesjon som ble startet ETTER at `.claude/agents/{{PROJECT_NAME}}-*.md` finnes på disk. Claude Code snapshotter agent-registeret ved sesjonsstart — nyopprettede custom agenter er ikke tilgjengelige i en allerede kjørende sesjon. Verifiser med en triviell probe-dispatch (`subagent_type: {{PROJECT_NAME}}-planner`) før du starter en runde; «Agent type not found» betyr at du må starte en fersk sesjon.

> 📋 **Loop-optimalisering:** les `docs/superpowers/loop/optimization-backlog.md` ved sesjonsstart
> (finnes filen ikke ennå — ingen åpne tiltak, hopp over). Den er en persistent, koordinator-eid
> liste over ting som skal gjøre LOOPEN selv (ikke prosjektet) raskere/billigere/mer pålitelig —
> f.eks. merge-rekkefølge, lessons-gjenbruk, canary-verifisering. Anvend tiltak merket «ship nå» der
> de er relevante for denne sesjonen, og oppdater tiltakets status-kolonne (ikke startet → shippet
> `<runde>` / avvist `<hvorfor>`) når du gjør det — samme append-modell som lessons/run-log. Bruk
> §6c's `worktrees_stale`/`plan_revision_rate`-felt i `run-log.md` (helserader) til å se om
> tiltakene faktisk monner over flere runder.

> 🪝 **Hook-aktivering (idempotent, gjør ved sesjonsstart):** sjekk om
> `core.hooksPath` allerede er satt i hovedcheckouten FØR du setter den —
> **aldri overstyr** en eksisterende verdi (den kan være satt bevisst til noe
> annet):
> ```bash
> if [ -z "$(git config --get core.hooksPath 2>/dev/null)" ]; then
>   git config core.hooksPath .githooks
>   echo "core.hooksPath satt til .githooks"
> else
>   echo "core.hooksPath allerede satt — urørt: $(git config --get core.hooksPath)"
> fi
> ```
> Dette aktiverer `.githooks/pre-commit` (delt-checkout-vern-backstop — se §6
> pkt. 6 for pre-commit-DISIPLINEN den er et sikkerhetsnett bak, aldri en
> erstatning for den) **OG samtidig** den eksisterende `.githooks/pre-push`-
> hooken (samme katalog — `core.hooksPath` peker på hele katalogen). Dette er
> en FORVENTET sideeffekt, ikke en regresjon.

## 0. Argument-fortolkning + synk

**Argument-fortolkning (FØR synk):** Hvis `$ARGUMENTS` matcher et kjent domene-tag (`ai`, `design`, `sync`, `fundament`, `metrics`):
```bash
echo "tags_filter: [$ARGUMENTS]" > tasks/session-queue-filter.md
cat tasks/session-queue-filter.md
```
**Verifiser skrivingen lyktes** (les filen tilbake — ikke anta at Write/redirect-kallet fullførte stille). Behandle resten av loopen som tomt argument (kontinuerlig modus). Rapporter: «Sesjon-kø-filter satt: `$ARGUMENTS`». §1-skriptet under leser denne filen automatisk.

**Synk:**
```bash
git fetch origin {{BASE_BRANCH}} && git reset --hard origin/{{BASE_BRANCH}}
```
Lokal `{{BASE_BRANCH}}` i en koordinator-container eier ALDRI unik historikk — koordinatoren committer+pusher umiddelbart etter hvert steg, aldri på tvers av turer. En hard reset er derfor trygg per konstruksjon og unngår at en foreldet/divergert lokal branch (f.eks. fra en gjenbrukt container) krever manuell diagnose midt i en runde. Working tree ikke ren (`git status --porcelain` ikke-tom FØR reset) → rapporter til mennesket og stopp i stedet for å reset — det er den eneste situasjonen der noe kan gå tapt.

## 1. Kø-utvelgelse (med ekte deps-gating)

Kjør dette python-skriptet — det resolver `deps`, ekskluderer claimed/brainstorm, og sorterer prioritert-først:

```bash
python3 - <<'PY'
import glob, re, os
def fm(p):
    t = open(p).read()
    m = re.search(r'^---\n(.*?)\n---', t, re.S)
    d = {}
    if m:
        for line in m.group(1).splitlines():
            mm = re.match(r'(\w+):\s*(.*)', line)
            if mm: d[mm.group(1)] = mm.group(2).strip().strip('"')
    d['_brainstorm'] = bool(re.search(r'krever[^.\n]*brainstorm|brainstorm\s+f.?r\s+plan|spec\s+f.?r\s+plan', t, re.I))
    d['_path'] = p
    m2 = re.search(r'^tags:\s*\[(.*?)\]', t, re.M)
    d['_tags_raw'] = m2.group(1) if m2 else ''
    return d
def as_int(v, default=9999):
    try: return int(v)
    except (ValueError, TypeError): return default
# Konsumer tasks/session-queue-filter.md hvis den finnes (§0 skriver den — MÅ leses her, ikke bare dokumenteres)
filter_tags = []
if os.path.exists('tasks/session-queue-filter.md'):
    m = re.search(r'tags_filter:\s*\[(.*?)\]', open('tasks/session-queue-filter.md').read())
    if m:
        filter_tags = [t.strip() for t in m.group(1).split(',') if t.strip()]
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
    tags_raw = d.get('_tags_raw', d.get('tags', ''))
    in_filter = (not filter_tags) or any(t in tags_raw for t in filter_tags)
    eligible = (d.get('status')=='open' and (d.get('claimed_by','null') in ('null','',None))
                and not d['_brainstorm'] and all(dep_done(x) for x in deps)
                and not re.search(r'\bforslag\b', tags_raw)
                and not re.search(r'\butredning\b', tags_raw)   # krever websøk-verktøy workers ikke har — koordinator håndterer bevisst, se §1-note
                and not re.search(r'\beier-ops\b', tags_raw)     # eier utfører selv (prod/OAuth/manuelt) — loopen dispatcher aldri disse
                and in_filter)
    pr = 0 if d.get('priority')=='prioritert' else 1
    rows.append((pr, as_int(d.get('order')), nr, d.get('status','?'), 'YES' if eligible else 'no', d['_path']))
for r in sorted(rows):
    print(f"elig={r[4]:3} pri={r[0]} order={r[1]:5} TODO {r[2]:5} {r[3]:10} {r[5]}")
PY
```

Velg øverste rad med `elig=YES`. Ingen → §7 (grooming).

**Note — todos tagget `eier-ops`:** ekskludert maskinelt — de utføres av EIER (prod-berøring, ekte
OAuth-kontoer, manuelle røyktester). Koordinatoren rapporterer at de venter; dispatcher aldri.

**Note — todos tagget `utredning`:** disse er ekskludert fra automatisk seleksjon fordi de krever websøk/nettlesing (`WebFetch`/`WebSearch`), verktøy verken planner eller implementer har i sitt `tools:`-sett. Håndter dem selv som koordinator (les todoen, gjør research-arbeidet, eller rapporter til mennesket at den venter på en dedikert research-økt) — ikke dispatch dem blindt til en planner som ikke kan fullføre dem.

**Note — todos som krever en produktbeslutning uten mekanisk markør:** `_brainstorm`-regex-en over fanger kun eksplisitte fraser («krever … brainstorm»). En todo kan trenge eiers bekreftelse (f.eks. et produktvalg todoen selv sier «eier bør bekrefte») uten å matche regex-en. Les alltid selve todo-teksten før dispatch, ikke kun `elig=YES`-kolonnen — scriptet er en heuristikk, ikke en fullstendig erstatning for koordinatorens egen lesing.

## 1b. Opprett/oppdater status-artifact (anbefalt, menneske-synlig fremdrift)

Etter første kjøring av §1-skriptet (du har nå den fulle kvalifiserte todo-listen for denne
sesjonens scope): bygg **én** HTML-status-artifact (via `Artifact`-verktøyet) med en tabell over
alle kvalifiserte todos — nr, tittel, prioritet, pipeline-status, PR-lenke. Skriv fila til
scratchpad-mappen (IKKE inn i repoet — dette er ikke delt state, det er et vindu inn i
koordinatorens fremdrift for mennesket, og skal aldri commites/pushes).

Rediger samme fil og kall `Artifact` på nytt med **samme `file_path`** (redeployer til samme URL,
ikke en ny) ved hvert pipeline-stadieskifte for en todo:

| Stadieskifte | Steg |
|---|---|
| Todo claimet | §2 |
| Plan skrevet | §3 |
| Sendt til plan-review | §4 |
| Reviewer go/no-go (inkl. revisjonsrunde) | §4-gate |
| Implementer dispatchet | §5 |
| PR opprettet / sendt til kode-review | §5b |
| Kode-review go/revise-gate | §5b-gate |
| Merget til `{{BASE_BRANCH}}` | §6 |
| Pause/eskalert (uansett pausepunkt) | der pausepunktet inntreffer |

Statusverdiene skal speile pipeline-stadiet (kø → planlegger → til review → implementerer →
kode-review → merget → pause/eskalert) — ikke bare et binært ferdig/ikke-ferdig. Mennesket skal se
HVOR i pipelinen hver todo står uten å lese hver worker-rapport selv.

Artifacten er et supplement til, ikke en erstatning for, run-log.md (§6.5) — sistnevnte er den
autoritative, persistente kilden; artifacten er et ferskt, forgjengelig øyeblikksbilde for denne
sesjonen.

### Design — mørkt tema, låst palett (konvensjon, kopier direkte)

Bygg videre på denne eksakte CSS-variabel-oppsettet fremfor å reoppfinne fargevalg per sesjon:

```css
:root {
  --bg: #0e1014; --bg-deep: #0b0d11;
  --surface: #16191f; --surface-alt: #13161b;
  --border: #2c333d; --border-subtle: #232a33;
  --text-primary: #eef1f4; --text-secondary: #cdd3da;
  --text-muted: #8a929e; --text-weak: #6b7480;

  --teal: #4cc6d1; --teal-fill: rgba(76,198,209,.10); --teal-border: rgba(76,198,209,.32);
  --green: #5bbf7a; --green-fill: rgba(91,191,122,.12);
  --amber: #d6a455; --amber-fill: rgba(214,164,85,.12);
  --coral: #e0654f; --coral-fill: rgba(224,101,79,.12);
  --purple: #9b8cce; --purple-fill: rgba(155,140,206,.12);

  /* Pipeline-stadiefarger — ÉN pr. stadie, KUN seks (se regel 2 under) */
  --s-queue: #6b7480;       --s-queue-fill: rgba(107,116,128,.28);
  --s-plan: #8f7fc4;        --s-plan-fill: rgba(143,127,196,.28);
  --s-review: #9b8cce;      --s-review-fill: rgba(155,140,206,.28);
  --s-impl: #3f9aa3;        --s-impl-fill: rgba(63,154,163,.28);
  --s-codereview: #4cc6d1;  --s-codereview-fill: rgba(76,198,209,.28);
  --s-merged: #5bbf7a;      --s-merged-fill: rgba(91,191,122,.28);
}
```

`--teal` er brand-/aksentfargen (eyebrow, aktive rad-highlights, kø-tall). `--green`/`--amber`/
`--coral` er semantiske (go/pause/no-go) og brukes BÅDE i statustekst og i hendelsesloggens
event-tags — ikke bland dem med stadiefargene over, selv der de tilfeldigvis ligner (f.eks.
`--s-merged` og `--green` er begge grønne, men betyr «dette stadiet» vs. «dette utfallet»).

**Layout, fire seksjoner i denne rekkefølgen:**

1. **Header** — eyebrow (`Koordinator-loop · sesjon <navn>`, `--teal`, uppercase, letter-spacing)
   + `h1` (sesjonens tema i ett par ord) + `.sub` (kø-filter i `<code>` + én kort statuslinje som
   oppdateres ved hver redeploy — «N todos merget», «kø tom», «venter på eier-go», osv.).
2. **Kø-status** — KPI-rad (grid av bokser: Totalt / I kø / Aktiv / Merget / Venter, 1px gap på
   `--border-subtle`-bakgrunn, tall i `ui-monospace` + `font-variant-numeric: tabular-nums`) over
   en tabell med kolonnene **Nr · Todo (tittel+slug) · Prioritet · Deps · Pipeline & status ·
   Detalj · PR**. Én rad pr. todo; aktiv rad får `background: var(--teal-fill)`.
3. **Pipeline & status-kolonnen** — inline mini-stepper: **seks** prikker koblet med en tynn
   horisontal linje, pluss en fargekodet statustekst under dottene. Nøytral prikk
   (`--surface-alt`-fyll, `--border`-kant) inntil stadiet er `done`/`active` — da fylles den med
   stadiets farge fra paletten over; `active` får i tillegg en `box-shadow`-glow i stadiets
   fill-variant. Statusteksten under matcher IKKE nødvendigvis siste stadiets farge — bruk
   semantisk farge for utfall (`--coral` for no-go/blocked, `--amber` for eksplisitt
   eier-go-pause, `--s-merged`/`--green` for ferdig).
4. **Hendelseslogg** — kronologisk, append-only liste nederst. Hver rad: løpenummer + én
   fargekodet event-tag-chip (typiske tags: `sync`/`claim`/`plan`/`revisjon`/`go`/`no-go`/
   `commit`/`pause`/`eier`/`merget`/`helsesjekk`) + kort norsk tekst + ev. lenke (PR/commit-sha).
   Siste rad får klassen `.now` (fremhevet tekstfarge) inntil neste hendelse skjer, da flyttes
   `.now` videre og forrige rad blir vanlig.

**Fem låste regler (brutt/lært underveis — gjenta ikke):**

1. **Redeploy til SAMME `file_path` ved HVER stadieskifte** — merge, go/no-go-verdikt, pause,
   eier-go mottatt, helsesjekk-resultat. Ikke bare når mennesket eksplisitt spør «husk å oppdatere
   artifact». Hvis du er usikker på om noe endret status nok til å redeploye: redeploy — kostnaden
   ved en ekstra redeploy er null, kostnaden ved et stille-utdatert vindu er tillit.
2. **Nøyaktig SEKS synlige pipeline-stadier — ikke åtte.** «Claimet» og «kø» er ÉN visuell prikk
   (kø-prikken dekker begge); ikke gi «claimet» en egen dot. Numrene i tooltip/legend må stemme:
   hvis kø er posisjon 1, er planlegging posisjon 2 — ikke 3. En bruker fanget nøyaktig dette
   avviket én gang; ikke gjenta det.
3. **Én representasjon av pipeline-state, ikke to.** Ikke bygg BÅDE en per-rad mini-stepper OG en
   separat full-størrelse stepper-seksjon for «gjeldende todo» — den andre representasjonen drifter
   stille ut av synk og blir en løgn i UI-et. Mini-steppen i kø-tabellen er nok.
4. **Live tall, ingen plassholdere.** KPI-boksene (Totalt/I kø/Aktiv/Merget/Venter) og
   hendelsesloggens siste rad skal alltid reflektere faktisk kø-state ved redeploy-tidspunktet —
   tell på nytt, ikke inkrementer en gjettet verdi.
5. **Scratchpad, ikke repo** (gjentatt fra over — det viktigste bruddet å unngå): artifact-fila
   skal ALDRI committes/pushes til `{{BASE_BRANCH}}`. Den er et forgjengelig menneske-vindu, ikke
   delt state.

## 2. Claim + pre-løs lessons-tema

Sett `claimed_by: <din-sesjon>` i todo-fila. Grep `tasks/lessons.md` for 1–3 tema relevant for todoens domene (gyldige tema: {{LESSONS_TOPICS}}).

**Claim-release:** I ENHVER stopp-sti senere (teknisk risiko, blocked, failed, merge-konflikt) → sett `claimed_by: null` tilbake før du stopper, så todoen ikke lekker ut av køen.

## 3. Dispatch planner

Velg et **canary-mål** workeren ikke kan gjette: en fil+linje som ikke er en invariant og ikke gjentas i prompten (f.eks. `{{CANARY_FILE}}` linje N — varier N per dispatch). Noter den faktiske teksten selv (`sed -n 'Np' {{CANARY_FILE}}`).

`Agent`: `subagent_type: {{PROJECT_NAME}}-planner`. Prompt:
> TODO <nr> (`tasks/todos/todo-<nr>-<slug>.md`). Relevante lessons-tema: <liste>. Canary: returner de første 8 ordene på linje <N> i `{{CANARY_FILE}}`. Følg charteret ditt. Returner plan-rapport som JSON.

**Planner-tiering (eier-aktivert, betinget):** for en LAVRISIKO-todo — ingen migrasjon/RLS, ingen
provider-/sync-flate, ingen metrics-/beregningsflate, ingen secrets/env, i praksis ren UI/CSS/copy/
registry — kan planneren dispatches med Agent-parameteren `model: "{{MODEL_IMPLEMENTER}}"`
(per-kall-override; agent-definisjonen forblir dyp modell som default). Reviewer (§4) er
OBLIGATORISK uansett tier og skal re-verifisere alle verifikasjonsutsagn. Er du i tvil om
risikoklassen → dyp modell. Bokfør faktisk brukt planner-tier i run-log-radens modellkolonne
(f.eks. `planner=Sonnet5(light)`), aldri aliaset alene.

Verifiser at `canary` matcher den faktiske teksten du noterte. Mismatch → re-dispatch eller eskalér (workeren leste sannsynligvis ikke filene). Koordinatoren (du) setter `plan:`-stien fra rapportens `plan_path` i todo-frontmatteren — workeren rører den ikke.

**Hent planfil til delt state + rydd worktree (obligatorisk, atomisk kjede — ikke et hoppbart steg):**

Planner-workeren skriver planfilen i SIN EGEN isolerte worktree og kan ikke selv gjøre den synlig
for reviewer (dens `git push` lander på sin egen branch, aldri på `{{BASE_BRANCH}}`). Kjør DENNE
HELE blokken i ÉTT bash-kall (variablene må overleve fra oppslag til rydding) FØR §4-dispatch, og
igjen etter hver revisjonsrunde (§4 under) før re-review:

```bash
branch="<branch fra plan-rapporten>"
plan_path="<plan_path fra plan-rapporten>"
wt_path=$(git worktree list --porcelain \
  | awk -v b="refs/heads/$branch" '/^worktree /{w=$2} /^branch /{if($2==b){print w; exit}}')

if [ -z "$wt_path" ]; then
  echo "ADVARSEL: fant ingen worktree for branch $branch — sjekk at branch-navnet matcher rapportens felt" >&2
elif cp "$wt_path/$plan_path" "$plan_path" && \
     test -f "$plan_path" && \
     git add "$plan_path" && \
     git commit -m "plan: todo-<nr> <slug>" && \
     git push origin HEAD:{{BASE_BRANCH}} && \
     git log -1 --oneline -- "$plan_path"; then
  locked=$(git worktree list --porcelain \
    | awk '/^worktree /{w=$2; lk=0} /^locked/{lk=1} w=="'"$wt_path"'" && lk{print "yes"; exit}')
  if [ "$locked" != "yes" ]; then
    dirty=$(git -C "$wt_path" status --porcelain 2>/dev/null)
    if [ -z "$dirty" ]; then
      if git worktree remove "$wt_path" --force 2>/dev/null; then
        git branch -d "$branch" 2>/dev/null || git branch -D "$branch" 2>/dev/null
      else
        echo "ADVARSEL: git worktree remove feilet for $wt_path" >&2
      fi
    else
      # Planfilen selv er ALLTID untracked i planner-worktreet (planneren committer aldri) —
      # whitelist den før dirty-vurderingen, ellers er denne rydde-grenen død kode (lesson 2026-07-20):
      dirty_uten_plan=$(printf '%s' "$dirty" | grep -v "^?? $plan_path")
      if [ -z "$dirty_uten_plan" ]; then
        if git worktree remove "$wt_path" --force 2>/dev/null; then
          git branch -d "$branch" 2>/dev/null || git branch -D "$branch" 2>/dev/null
        fi
      else
        echo "ADVARSEL: $wt_path har ucommittede endringer UTOVER planfilen — sletter ikke, §A5b-sweepen tar den senere" >&2
      fi
    fi
  else
    echo "ADVARSEL: $wt_path er locked — sletter ikke, §A5b-sweepen tar den senere" >&2
  fi
else
  echo "ADVARSEL: plan-kopi-kjeden feilet et sted — IKKE dispatch reviewer. Feilsøk (typisk: wt_path pekte feil, eller push feilet) før du prøver igjen." >&2
fi
```

**Forutsetning for at denne ryddingen er trygg:** revisjonsrunder for planneren (gaten i §4 under)
skal ALLTID bruke en fersk `Agent`-dispatch, ALDRI `SendMessage`-gjenopptakelse av forrige
planner-instans — se presisering i §4s gate. Samme regel som §5a/§6 allerede forutsetter for
implementer-/fix-mode-runder («et helt NYTT worktree per dispatch»), nå eksplisitt for planneren
også (praksis har avveket fra den underforståtte lesningen minst én gang i live-drift: en cwd-drift-bug
ved SendMessage-gjenopptakelse — se `tasks/lessons/workflow-process.md` 2026-07-10).

## 4. Dispatch reviewer + gate

`Agent`: `subagent_type: {{PROJECT_NAME}}-reviewer`. Prompt:
> TODO <nr>. Plan: `<plan_path>`. Relevante lessons-tema: <liste>. Følg charteret ditt. Returner review-rapport som JSON.

**Konsolideringsgate (før du velger fold eller planner-revisjon) — OBLIGATORISK.**

1. **Terskelen.** Mål `wc -l <plan_path>` FØR du håndterer en no-go OG PÅ NYTT etter at
   folden/revisjonen er skrevet (målt maks delta per runde kan overstige 400 linjer i én runde). **≥ 400 linjer OG planen har minst én tidligere review-/fold-runde ⇒ planen skal KONSOLIDERES**, ikke foldes/revideres videre. På et førsteutkast finnes ingen lag å konsolidere — der gjelder planner-charterets output-budsjett. «Minst én tidligere runde» er MEKANISK og sesjonsuavhengig (koordinator-overlevering nullstiller kontekst-tellere): §4-rundetelleren > 0 ELLER `git log --oneline -- <plan_path>` viser ≥2 commits (commit-listen overteller heller enn underteller — riktig feilretning for en gate; §4-telleren er FASIT når den finnes). Passerer fila terskelen ETTER runden, konsolideres den i samme omgang, før neste dispatch (verifiserings-review på fold-grenen, planner-revisjon på den andre) — fyrer terskelen først etter folden, kommer konsolideringen i TILLEGG til folden; regnskapet er uendret (verifiseringsrunden teller).
2. **HVORFOR** (suksesskriterium): en review-runde legger til lag og fjerner ingen, så dokumentet degraderer monotont uten et motgrep.
3. **Hvorfor linjeantall og ikke et annotasjonstall:** annotasjonsmarkører skrives inkonsistent — linjeantall er det eneste som er målbart ved beslutningen. Én linje, ingen tabell.
4. **Hva konsolidering ER:** skriv planen om til gjeldende sannhet — én versjon av hver påstand, ingen «r1 sa X, r2 rettet til Y». Behold begrunnelser som er lastbærende for implementeringen, OG hvert bevisst avvist funn som én linje («**Vurdert og forkastet**: X — fordi Y») — en avvisnings-begrunnelse er lastbærende for neste reviewer; strykes den, reises funnet på nytt og runden gaten skulle spare brennes likevel. Review-historikken ellers flyttes til én kort seksjon nederst eller strykes (run-log + PR-body bærer den). Rundens nye funn foldes inn som del av omskrivingen.
5. **Hva konsolidering IKKE er:** **ikke en ny planner-dispatch** (planneren mangler review-konteksten; ved kontekstpress kan koordinatoren overlate selve omskrivingen til en **fersk sub-agent** MED funn-inventaret K1 — ansvaret for K1–K3 forblir koordinatorens); ikke en anledning til å endre scope. **Ingen ny beslutning** tas — det er en omskriving, ikke en re-planlegging.
6. **Hvem, og hva den erstatter:** koordinatoren konsoliderer. Konsolideringen erstatter folden, ikke den obligatoriske verifiserings-review-runden — den kjøres som normalt, og dispatch-prompten sier eksplisitt at planen er konsolidert og vedlegger funn-inventaret (K1). Konsolideringen selv er ikke en revisjonsrunde — den erstatter folden. Den obligatoriske verifiserings-review-runden etterpå **teller mot 2-runders-grensen**, som ved en vanlig fold (aldri dobbelt-telling, aldri gratis runde).
7. **Planner-revisjons-grenen:** går settet til planner-revisjon (ett funn utenfor fold-kriteriene), konsoliderer koordinatoren FØRST, og dispatcher deretter planneren mot den konsoliderte fila.
8. **Verifisering av konsolideringen** (bygger på E1/E2 i fold-etterkontrollen lenger ned i §4 — konsolidering er selv en fold-operasjon, og et tapt funn er verre enn annotasjons-støy):
   - **K1 — funn-inventar FØR omskriving.** List hvert review-funn fra ALLE runder (kilder: review-rapportenes `findings[]` i kontekst + fold-notatene i `git log --format='%s%n%b' -- <plan>`), og merk hvert funn `innfoldet` eller `bevisst avvist`. Inventaret skrives ned før den konsoliderte teksten erstatter originalen.
   - **K2 — per-funn-bekreftelse mot den NYE teksten,** med E1-snutten (samme seksjonsdeling, samme forventede retning analyse ≥1 / steg-liste ≥1). Gjenfinning kreves for BEGGE klasser fra K1 (innfoldede funn i planteksten; avviste som sin «Vurdert og forkastet»-linje). Et funn som ikke gjenfinnes, er tapt — da er konsolideringen ikke ferdig. Funn uten steg-konsekvens navngis skriftlig, som i E1.
   - **K3 — aggregat-sveip + lengde.** Kjør E2-sveipen på den konsoliderte fila: en omskriving er den mest aggregat-farlige operasjonen som finnes, fordi hver telling kan ha mistet det den teller. Og: en konsolidering som gjør fila LENGRE er ikke en konsolidering — skriv `wc -l` før/etter i fold-notatet (på planner-revisjons-grenen: i commit-meldingen for den konsoliderte planfila), og begrunn en økning eksplisitt.
9. **Utgangen** (en gate uten utgang blir rutet rundt): velger koordinatoren likevel å folde en plan som har passert terskelen, skrives begrunnelsen i fold-notatet (på planner-revisjons-grenen: i commit-meldingen for den konsoliderte planfila) («konsolidering utsatt fordi …»), slik at avviket er synlig i commit-loggen. Stillhet er ikke en lovlig utgang.

Gate på `verdict`:
- `"no-go"` (≥1 BLOKKERENDE) → send funnene tilbake til planner via en **FERSK** `Agent`-dispatch (§3, revisjons-runde — ALDRI `SendMessage`-gjenopptakelse av forrige planner-instans; forrige instans sitt worktree er allerede ryddet, se §3s rydde-steg) — men kjør **Konsolideringsgaten** over FØR du velger gren. **Hold en eksplisitt teller** («revisjonsrunde X/2») i kontekst. Etter **2** runder uten `go` → ⚠️ eskalér til mennesket, release claim.
- `"go"` → fortsett.

**Fold-føringer som dikterer UI-tekst:** si INTENSJONEN (hva hintet/teksten skal formidle), ikke
ordrett copy — implementeren verifiserer utførbarhet mot faktisk UI-tilstand (316-F1: en foreskrevet
ordrett instruksjon refererte en handling som ikke fantes).

**Koordinator-fold-unntaket (ved no-go):** Hvis ALLE no-go-funnene oppfyller BEGGE kriterier —
(a) fiksen er FULLT foreskrevet av revieweren (konkret tekst/beslutning, ingen ny research
nødvendig) og (b) fiksen implementerer en allerede LÅST beslutning (eier-bekreftet eller
plan-etablert invariant) — KAN koordinatoren folde funnene inn i planfilen selv i stedet for
planner-re-dispatch (sparer ~150k tokens + én runde-trip per observert tilfelle). Da er en
VERIFISERINGS-review-runde OBLIGATORISK: dispatch reviewer på nytt med eksplisitt oppdrag om å
verifisere at foldene er komplette og korrekte (runden teller mot 2-runders-grensen). Er ETT
funn utenfor kriteriene (krever skjønn/research/nye valg) → planner-revisjon som normalt for
HELE settet. Dokumentér valget i commit-meldingen («koordinator-fold begrunnet: …»).

**Etterkontroll av folden — OBLIGATORISK, ikke råd.** Tre målte feilformer fra live-drift: folden
traff analysen men ikke steg-listen, aggregat-påstander ble stale av folden, og én foldet
reviewer-FAKTA-påstand var usann. Alle tre postene under kjøres for HVER fold — ikke bare den
koordinatoren tror er relevant.

- **E1 — per-funn-verifisering med forventet RETNING.** Beviser at hvert foldet funn faktisk landet
  i **steg-listen**, ikke bare i analysen — et grep-treff beviser tilstedeværelse, ikke korrekt
  instruksjon. Global `grep -c '<funn>'` er UTILSTREKKELIG: treff i analysen maskerer at
  steg-listen mangler dem. Et funn som landet ett sted er **ikke** foldet; et funn uten
  steg-konsekvens må navngis skriftlig — stillhet teller som manglende fold.

  ```bash
  # plan         = full sti til planfila
  # frase        = strengen folden FAKTISK skrev inn i steg-punktet (reviewerens funn-ID duger ikke —
  #                bruk samme streng mot begge seksjonene)
  # gammel_frase = formuleringen funnet skulle fjerne (forventning 0 i steg-listen)
  plan="tasks/plans/todo-<nr>-<slug>.md"
  frase="<frasen folden skrev inn>"
  gammel_frase="<formuleringen som skal være borte>"

  anker=$(LC_ALL=C /usr/bin/grep -nE '^#{1,4} *[0-9.]* *Steg' "$plan")
  antall=$(printf '%s\n' "$anker" | LC_ALL=C /usr/bin/grep -c '^[0-9]')
  siste_num=$(printf '%s\n' "$anker" | tail -1 | cut -d: -f1)
  siste_tekst=$(printf '%s\n' "$anker" | tail -1 | cut -d: -f2-)
  # neste_seksjon = første `## `-overskrift ETTER ankeret (tom => ingen, halen er bundet av EOF)
  neste_seksjon=$(LC_ALL=C /usr/bin/grep -nE '^## ' "$plan" | LC_ALL=C /usr/bin/awk -F: -v n="$siste_num" '$1>n{print $1; exit}')

  steg=""
  if [ -z "$anker" ]; then
    echo "STOPP: ingen steg-anker i $plan — fall ALDRI stille tilbake til «hele fila er én seksjon»." >&2
  elif ! printf '%s\n' "$siste_tekst" | LC_ALL=C /usr/bin/grep -qE '^#{1,4} *[0-9.]* *Steg *$'; then
    echo "STOPP: $antall ankertreff, siste (linje $siste_num) er ikke en ren steg-overskrift — velg skillelinje manuelt, skriv linjenummer + begrunnelse i fold-notatet, kjør så tellingene mot det manuelle skillet." >&2
  elif [ -n "$neste_seksjon" ]; then
    echo "STOPP: en \`## \`-overskrift finnes ETTER steg-ankeret (linje $siste_num, neste på linje $neste_seksjon) — halen er ubundet (kan inneholde fold-notater/verifiseringsseksjoner ETTER selve steg-listen). Velg sluttlinje manuelt, skriv linjenummer + begrunnelse i fold-notatet, kjør så tellingene mot det manuelle skillet." >&2
  else
    steg=$(sed -n "${siste_num},\$p" "$plan")
  fi

  if [ -z "$steg" ]; then
    : # STOPP-meldingen over er alt skrevet — tellingene kjører ALDRI uten et gyldig skille.
  else
    analyse=$(sed -n "1,$((siste_num-1))p" "$plan")
    echo "analyse:     $(printf '%s' "$analyse" | LC_ALL=C /usr/bin/grep -cF "$frase")   (forventning ≥1)"
    echo "steg-liste:  $(printf '%s' "$steg"    | LC_ALL=C /usr/bin/grep -cF "$frase")   (forventning ≥1)"
    echo "gammel form: $(printf '%s' "$steg"    | LC_ALL=C /usr/bin/grep -cF "$gammel_frase")   (forventning 0)"
  fi
  ```

  Er folden rent steg-teknisk (ingen ny begrunnelse hører hjemme i analysen) er `analyse`-treff på
  0 akseptabelt — men da skal fold-notatet si det eksplisitt, med begrunnelse, ikke bare stå som et
  stille avvik fra forventningen ≥1 over.

- **E2 — aggregat-sveip, substantiv-uavhengig.** Kjøres mot HELE planfila (ikke bare det foldede
  avsnittet) — den literale strengen under, ordrett og kopierbar. `$plan` settes på nytt i DETTE
  Bash-kallet: agent-Bash-kall deler ikke shell-state med E1s kall, og en unset `$plan` gir stille
  treff-tall 0 (exit 0) i stedet for en feil:

  ```bash
  plan="tasks/plans/todo-<nr>-<slug>.md"
  [ -f "$plan" ] || { echo "STOPP: plan-stien er ikke satt/finnes ikke" >&2; }
  LC_ALL=C /usr/bin/grep -nioE '(^|[^A-Za-zÆØÅæøå-])([0-9]+|en|ei|et|én|éi|ett|to|tre|fire|fem|seks|sju|syv|åtte|ni|ti|elleve|tolv|tretten|fjorten|femten|seksten|sytten|atten|nitten|tjue|begge)[ -][A-Za-zÆØÅæøå]+' "$plan"
  ```

  Vis treffene som `linje:treff` (formen over) — det er linjen som inspiseres per treff, ikke et
  aggregattall som avgjør noe alene. Et rått antall (samme kommando med `| wc -l` lagt til) kan tas
  med som en rask oversikt, men aldri i stedet for å lese linjene.

  Ingen substantiv-liste finnes bevisst — en hvitliste feiler stille (missed «To nye
  **oppføringer**»-saken). `-i` under `LC_ALL=C` case-folder IKKE Æ/Ø/Å: store norske tallord
  (`Én`, `Éi`, `Åtte`) fanges ikke. **Sveipen er et GULV, ikke en garanti:** den er linje- og
  adjacency-basert, så en tallpåstand brutt av linjeskift eller `**`-utheving (`**FIRE** filer`)
  fanges IKKE. `git diff -- "$plan"` brukes til **prioritering** av treffene (skjæringen mellom
  sveipen og det folden faktisk rørte er farligst), aldri som filter — en skjæring kan også misse
  stille. I fold-notatet står RELASJONEN («den substantiv-uavhengige formen fanger de kjente
  sakene; en hvitliste fanget færre») — råtallene hører i PR-body, ikke i runbook-teksten, fordi de
  drifter med hver ny fold.

- **E3 — reviewer-påstander om FAKTA måles FØR de foldes.** Utvider den etablerte regelen for
  foreskrevne fixtures/vakter til foreskrevne TALL og mekanisme-påstander (målt: tre runder, tre
  ulike gale tall for samme måling — den foldede var på vei inn i kode). En reviewer-påstand om et
  tall, en linje eller en mekanisme foldes ALDRI uprøvd; koordinatoren re-kjører målingen selv først.

Folden er ikke ferdig før **alle postene i denne blokka** er kjørt og utfallet er skrevet ned.

Ved `technical_risk.flagged` (plan- eller review-rapport) → ⚠️ STOPP, release claim, rapporter risikoen, vent på menneskets go.

## 5. Dispatch implementer

**Re-grep lessons FØR dispatch (ship-nå #2):** grep `tasks/lessons.md` for planens faktiske
filstier/moduler (ikke bare todo-temaene fra §2) — en søsken-todo merget TIDLIGERE I SAMME SESJON
kan ha etterlatt en fersk lesson som §2-claimet ikke så. Ta relevante treff inn i dispatch-prompten.

`Agent`: `subagent_type: {{PROJECT_NAME}}-implementer`. Prompt:
> TODO <nr>. Plan: `<plan_path>`. Relevante lessons-tema: <liste>. Følg charteret ditt. Returner ferdig-rapport som JSON.

`status: "failed"|"blocked"` → ⚠️ STOPP, release claim, rapporter.

**Sekvensiell dispatch-splitting av brede planer:**
implementer-kost skalerer med ANTALL FLATER/FILER × testkrav-tetthet — ikke med todo-
«vanskelighet» (loopens to dyreste dispatcher, 433k/373k tokens, var begge brede sveip).
Når planen (eller plan-rapportens leveranse-splitt-vurdering, se planner-charteret) tilsier det,
KAN koordinatoren dele én plans implementering i SEKVENSIELLE dispatcher mot samme plan:
dispatch 2 får dispatch 1s PR/branch som fundament (oppgi branch-navnet i prompten), hver
dispatch får eget scope-avsnitt («implementér KUN steg A–C»), og hver PR går gjennom §5a/§5b
separat. Dette er en vurdering, ikke en regel — små/sammenhengende planer dispatches fortsatt
som én.

**Parallell-modus (flere todos i flukt samtidig — eier-opt-in, r17-formalisert):** når eier har
bedt om parallelle agenter, gjelder tre konvensjoner i tillegg til runbookens serielle regler:
1. **Lane-erklæring i HVER dispatch-prompt:** navngi todoens lane («du eier `<stier>`; rør IKKE
   `<søsken-todoens stier>`») så workers ikke «hjelpsomt» krysser inn i en søsken-flate.
2. **Krysssjekk-gate FØR parallell implementer-dispatch (backlog #7):** sammenlign «Filer som
   berøres»-listene på tvers av de godkjente planene. Overlapp på SAMME fil → dispatch dem
   SEKVENSIELT (den andre starter fra fersk `{{BASE_BRANCH}}` etter førstes merge); kun disjunkte
   flater kjører samtidig. Additive kollisjoner i delte typer/viewdata-filer telles som overlapp.
3. **Delt state forblir seriell:** §6-skrivinger (lessons/arkiv/run-log/merge) gjøres alltid én
   om gangen av koordinatoren selv, uansett hvor mange workers som kjører — og A5b-sweep utsettes
   mens egne agenter lever (se loop-health-check A5b).

## 5a. PR-opprettelse (worker først, koordinator som fallback)

**Historikk:** batch 4–5-æraens maler forbød workers å forsøke `gh pr create`
(«GitHub access is not enabled»-403). Empirisk probe 2026-07-12 viste at worker-sandboxer HAR
full gh-tilgang (innlogget, scopes repo/workflow; 271-workeren opprettet PR #322 selv) — de
gamle «mangler tilgang»-rapportene var arvede antakelser fra malene, ikke faktiske 403-er.
Regelen er derfor snudd:

**Implementeren forsøker `gh pr create` selv** (mot `{{BASE_BRANCH}}`) etter push. Lykkes det →
`pr_url` settes i ferdig-rapporten. Feiler det (miljøvariasjon forekommer) → IKKE feilsøk;
push branchen, sett `pr_url: null` + `branch` i rapporten, og koordinatoren oppretter PR-en:
1. `git fetch origin <branch>` — hent branchen.
2. Verifiser diffen er ren og bygger på ferskeste `{{BASE_BRANCH}}`: `git diff origin/{{BASE_BRANCH}}...origin/<branch> --stat`.
3. Opprett PR-en (GitHub-verktøyet ditt, `--base {{BASE_BRANCH}}`), med tittel/body basert på ferdig-rapportens `summary`/`deviations`.
4. Fortsett til §5b med PR-URL-en.

Har ferdig-rapporten `pr_url` satt: bruk den, ikke opprett en duplikat-PR.

**Navngitte redningspraksiser:**
- **Worktree-rescue:** dør/drepes en implementer ETTER at koden er skrevet i worktreet men FØR
  push/rapport: koordinatoren verifiserer arbeidet i worktreet selv (type-check + relevante
  tester), committer og pusher branchen derfra, og sender den gjennom NORMAL §5b-kode-review —
  arbeid forkastes ikke fordi rapporten uteble, men det slipper heller aldri forbi reviewen.
  **⚠️ Unntak uten skjønn — rescue ALDRI en verifikator-worktree.** Et worktree som inneholder
  markørfila `.verifier-worktree` (eller står på en `verify-*`-branch) inneholder per definisjon
  BEVISST INNSATTE feil: verifikatoren muterer produksjonskode for å bevise at vakter går røde.
  Innholdet forkastes ALLTID, uansett hvor ferdig det ser ut.
- **To-fase-implementer med migrasjons-pauseprotokoll:** todos med DB-migrasjon kjøres i to
  faser: implementeren SKRIVER migrasjonsfilene (uten å appliere), rapporterer og PAUSER;
  koordinatoren applierer mot {{DEV_ENV_ID}} med bevis (list_migrations før/etter + advisors),
  og gjenopptar implementeren (eller fortsetter selv) for resten. En worker applierer ALDRI
  migrasjoner selv (Tier-1-invariant).

**Rydd implementer-worktreet UMIDDELBART etter PR-opprettelse** (ikke vent til §6-merge). Implementerens jobb er ferdig i det øyeblikket branchen er pushet og PR-en opprettet — worktreet trengs ikke lenger, og en eventuell senere fix-mode-runde får uansett et helt NYTT worktree (`isolation: worktree` per dispatch). Å la det gamle worktreet stå åpent med branchen checked out blokkerer en fix-mode-dispatch fra `git checkout -b <samme-branch-navn>` («already used by worktree») — samme kollisjonsklasse som andre worktree-navnekollisjoner. Bruk samme rydde-mønster som §6 (verifiser ikke-locked + `git status --porcelain` er tom i worktreet FØR `git worktree remove --force`), men la selve feature-branchen (`git branch`) stå urørt til etter merge — kun worktreet fjernes her.

**Agent-opprettede lokale brancher er repo-GLOBALE og overlever worktree-fjerning.** Fix-mode- og
kode-review-agenter etterlater `fix/*`- og `pr-*`-brancher i det delte branch-registeret selv når
worktreet deres fjernes. Slett dem som del av post-dispatch-ryddingen etter at innholdet er
merget/bekreftet (`git branch -D fix/... pr-...`) — for squash-merge-repoer verifiseres «merget»
med tre-diff (`git diff --quiet origin/{{BASE_BRANCH}} <branch>`), IKKE `--is-ancestor` (aldri sann
for squash-mergede tips). Helsesjekkens A5b-sweep er backstop, ikke primærmekanisme.

## 5b. Uavhengig kode-review

### Probe (obligatorisk FØR review-dispatch)

Før du dispatcher selve reviewen, kjør en triviell probe for å verifisere at `{{PROJECT_NAME}}-code-reviewer` er lastet i denne sesjonen:

`Agent`: `subagent_type: {{PROJECT_NAME}}-code-reviewer`, prompt: «Svar kun: {"ok": true}. Ikke synk, ikke les filer.»

- Får du `{"ok": true}` → fortsett til review-dispatch.
- «Agent type not found» (eller manglende `ok`) → ⚠️ STOPP, release claim, eskalér til mennesket: «§5b krever en koordinator-sesjon startet ETTER at `.claude/agents/{{PROJECT_NAME}}-code-reviewer.md` ble merget til `{{BASE_BRANCH}}`; start en fersk sesjon».

### Review-dispatch

`Agent`: `subagent_type: {{PROJECT_NAME}}-code-reviewer`. Prompt:
> TODO <nr>. PR: `<pr_url>` (fra ferdig-rapporten). branch: `<branch>`. base_sha: `<base_sha>`. Relevante lessons-tema: <liste>. Følg charteret ditt. Returner code_review-rapport som JSON.

`branch` + `base_sha` er påkrevd i tillegg til PR-URL-en: de er det tech-armene som er spesifisert
med **branch-dispatch** (uavhengighetskrav) får, i stedet for PR-referansen.

### Verifikator-armen — diff-settene koordinatoren kan etterprøve

Er en verifikator-arm konfigurert i `tech_review_agents`, beregner kode-revieweren to sett fra
diffen. Koordinatoren kan kjøre samme beregning selv når rapporten skal falsifiseres:

```
GUARD_SET = {diff-filer som matcher **/*.guard.test.ts(x)}
          ∪ {diff-filer som matcher **/*-parity.test.ts(x)}
          ∪ {testfiler i diffen som gjør kildeskann (readFileSync|readdirSync|globSync)}
          ∪ {testfiler der diffen legger til en maskinlesbar @guard-tag i docblocken}
          ∪ {testfiler planen eksplisitt deklarerer som vakt/tripwire/mutasjonsprøve}

UI_SET    = diff ∩ (katalogene til layout-smokens flate-registry
                    ∪ globale stil-/layout-filer
                    ∪ filer disse faktisk importerer — avgrenset import-vandring, maks 3 nivå)
```

**Trigger er filnavn-familie + `@guard`-tag + plan-deklarasjon — aldri nøkkelord i vilkårlig
testtekst.** En tekstlig vakt-detektor er upålitelig som gate (falske positiver på
«never»/«aldri»-kommentarer og `toHaveLength(1)`).

Begge sett tomme ⇒ armen dispatches ikke, og kode-revieweren SKAL skrive det eksplisitt i `notes`.

### Verifikator-rapportens sju mekaniske sjekker (kjøres FØR funnene tas for gitt)

Alle leser `code_review.tech_arm_reports[]`. Uten det feltet kan ingen av dem kjøres:

0. **`tech_arm_reports[]` finnes og inneholder verifikator-armen** med `status`, og ved
   `status: "kjørt"` en `report` med `report_type: "verification"`. Mangler feltet ⇒ BLOKKERENDE.
1. ingen `mutation.diff` inneholder `.test.`/`__tests__/`
2. hver `mutation.class` er i enum (`insert-mechanism` er IKKE en lovlig verdi), og klassens
   formkrav stemmer med diffens `+`/`-`-linjetelling
3. `red[]` er ikke-tom for hvert `RØD-BEVIST`; `restored_green` og `worktree_clean` er `true`
4. `pairs_proven + unprovable + not_covered === pairs_total`
5. **kjør én sitert `site_inventory.command` på nytt** og sammenlign `count`. Avviker den, er hele
   matrisen ugyldig — ikke bare det ene paret
6. `new_names` er tom, ELLER `class === "revert-hunk"` og hvert navn gjenfinnes i PR-diffens
   `-`-linjer; og `mutation.diff`s sti + hunk inneholder `site`
7. `claim_reads` gjenfinnes ordrett i vaktfila på `head_sha`, ≥1 identifikator fra `claim_reads`
   forekommer i `mutation.diff`s endrede linjer, og `drift_category` er lovlig for `class`

Brudd på én av dem ⇒ armens grønt er ugyldig, behandles som BLOKKERENDE («gaten beviste ikke det
den påstår»). Krysssjekk dessuten `base_sha`/`head_sha` mot PR-en — én kommando, og den avslører
en verifikator som jobbet på feil tilstand.

**⚪-regelen:** par med `verdict: "UBEVISBAR"` skrives ALDRI som ✅ i noen oppsummering — de får ⚪.
Severity er VIKTIG, så §5b-revise-gaten fyrer og implementeren må håndtere dem. Aldri en stille
dispensasjon. Godtas en innsnevret vakt-påstand, SKAL innsnevringen pinnes som MÅLT kommentar i
vaktfila og gjentas i PR-beskrivelsen — ellers er «snevre i runde 1, være grønn i runde 2» en
gratis vei ut.

### Riving og migrasjon — tre ekstra gater

Gjelder når en PR **sletter eller erstatter en brukervendt flate** (ruter, sider, komponenter som
bæres over til et nytt sted). Klassen er farlig fordi **fravær ikke har noen feilmelding**: en
manglende komponent kaster ikke, logger ikke og bryter ingen test — den oppdages først når noen
leter etter noe som ikke er der.

**G1 — dekningslista skal genereres, ikke skrives.** Har prosjektet et dekningsdiff-verktøy
(fjernede filer vs. erstatningsflate): kjør det og bruk output som råmateriale. Maskinen produserer
kandidatene, mennesket dømmer. En ufullstendig maskinell liste kan ikke *stille utelate* noe; en
håndskrevet kan. Har prosjektet ikke et slikt verktøy: bygg dekningslista manuelt, men eksplisitt
merket som HÅNDSKREVET (lavere tillitsnivå) i PR-body-en.

Tre krav til bruken der verktøyet finnes:
1. **Implementeren** kjører den i §5 og limer outputen i PR-body-en.
2. **Revieweren** kjører **samme** kommando i §5b — det er G3s mekaniske grunnlag, ikke en gjentakelse.
3. Outputen limes **sammen med** en `NOT_DETECTABLE_BY_DIFF`-seksjon, ikke bare kandidatlista. Uten
   blindfelt-lista gjenoppstår «hevder mer enn mekanismen bærer» i selve PR-body-en — et slikt
   verktøy ser typisk ikke CSS, ikke høyde/layout, og ikke interpolert tekst i template-literaler.

**G2 — varianttvang.** Har erstatningsflaten grener (uke/måned, desktop/mobil, rolle-varianter), skal
**hver gren** verifiseres — ikke bare den som utløste arbeidet. «Additivt før riving» er ikke nok
hvis det additive steget var ufullstendig for én variant.

**G3 — falsifiser eier-sammendraget i BEGGE retninger.** Gi revieweren dette som navngitt oppdrag:
(a) står alt som faktisk forsvinner på lista (uttømmende), og (b) er alt på lista faktisk borte
(ingen over-oppføring)? Begge feilretninger er skadelige — underdriving gir uinformert godkjenning,
overdriving får eier til å tro noe er verre enn det er og undergraver tilliten til lista neste gang.
**Koordinatoren bør verifisere de omstridte påstandene selv mot koden** framfor å delegere.

**Billig tilleggsgrep:** for hver hovedfunksjon den slettede flaten hadde, still spørsmålet
«hvor lever dette etterpå?». Det er ofte den faktiske detektoren når planen og reviewrundene ikke
fanger et tapt lag.

Grep-sveiper ved riving må dessuten dekke **både URL-form** (`/rute`) **og filsti-form**
(`utover)/rute/page`) — sistnevnte fanger tester som leser de slettede filene som kildekode — og
scopes til mer enn `app/`+`components/`+`lib/`.

### Gate (revise-gate på severity, ikke kun på verdict)

Les `code_review`-rapporten:

- Inneholder rapporten **≥1 BLOKKERENDE eller ≥1 VIKTIG** → **revise-gate**: send funnene tilbake til implementeren via fix-mode-dispatch (se fix-mode-mal under). **Hold en eksplisitt teller** («kode-review-runde X/2», samme mønster som §4). Etter **2** runder uten at revise-gaten er tom → ⚠️ eskalér til mennesket, release claim.
- **Unntak — `KOORDINATOR-HANDLING`-poster teller ikke.** Poster merket `KOORDINATOR-HANDLING:` i
  `notes` (videreført fra en tech-arms `coordinator_actions[]`) er ikke implementer-handlbare:
  «par-tak truffet», «armen uteble», «feil worktree», «prompt-brudd». De teller **ikke** mot
  revise-gaten og bruker **ikke** en runde. Koordinatoren utfører handlingen selv FØR §6 — typisk
  ved å re-dispatche armen for de gjenstående parene, eller dispatche den direkte når den uteble.
  Denne klassen er hele grunnen til at feltet finnes: uten den brenner en død arm en revise-runde
  på en implementer som ikke kan gjøre noe med den.
- Kun MINDRE eller ingen funn (`verdict = "go"`, revise-gate ikke trigget) → fortsett til §6.
- Teknisk risiko som dukker opp i rapporten → ⚠️ STOPP, release claim, rapporter (samme som §4-gaten).

**NB:** `verdict = "no-go"` trigges kun ved ≥1 BLOKKERENDE (identisk med plan-review). Revise-gaten er strengere — den trigges også ved ≥1 VIKTIG selv om `verdict = "go"`. Koordinatoren leser severity-arrayet direkte, ikke kun `verdict`.

### Fix-mode-dispatch-mal (revise-runde)

`Agent`: `subagent_type: {{PROJECT_NAME}}-implementer`. Prompt:

> FIX-MODE for TODO `<nr>`. Du har ALLEREDE implementert denne og laget PR `<pr_url>` på branch `<branch>`. IKKE re-implementer og IKKE kjør `todo-execute.md` på nytt. Gjør KUN dette: (1) `git fetch origin <branch> && git checkout <branch>` — **hvis dette feiler med «already used by worktree»** (branchen fortsatt levende i et annet, ikke-ryddet worktree): opprett i stedet en LOKAL branch med et annet navn tracket mot origin-tippen (`git checkout -b fix/todo-<nr>-round<N> origin/<branch>`), gjør fiksene der, og push med EKSPLISITT refspec (`git push origin fix/todo-<nr>-round<N>:<branch>`) for å oppdatere den faktiske PR-branchen uten navnekollisjon; (2) `git fetch origin {{BASE_BRANCH}} && git merge origin/{{BASE_BRANCH}}` for å bygge på ferskeste delt state før re-push; (3) rett UTELUKKENDE disse kode-review-funnene: `<liste med severity + file:line + issue + fix>`; (4) kjør `{{CMD_BUILD}}` + `{{CMD_TYPE_CHECK}}` + relevante tester på nytt; (5) push til samme PR (via vanlig `git push` ELLER refspec-varianten over — IKKE ny PR, IKKE ny `gh pr create`); (6) returner oppdatert ferdig-rapport. Rør ingenting utenom de oppgitte funnene.

## 6. Skriv delt state SERIELT (kun koordinator)

Fra ferdig-rapporten, `status: "implemented"`:
1. **Lessons:** for hver `lessons[]`, legg Pattern/Sjekkliste/Kilder i `tasks/lessons/<topic>.md` + én-linjes bullet i `tasks/lessons.md`. Konsolider om 2+ dekker samme mønster.
2. **Bugs:** `bugs_new[]` → `tasks/bugs.md`; `bugs_closed[]` → `tasks/bugs_archive.md` (opprett fila hvis den ikke finnes).
3. **Arkiver todo:** flytt til `tasks/todo_archive.md` (format: se eksisterende oppføringer). Slett `tasks/todos/todo-<nr>-<slug>.md`. Flytt planfil → `tasks/plans/archive/`.
4. **Merge:** `gh pr merge <pr> --squash --delete-branch` — ALDRI `{{PROD_BRANCH}}` (base er satt ved PR-oppretting, ikke ved merge-kommandoen; `--base`-flagget finnes ikke i `gh pr merge`). Squash matcher repoets merge-historikk; `--delete-branch` rydder remote+lokal branch automatisk. **Forutsetning (backlog #1, anvendt uten friksjon siden r17):** implementer-worktreet er ALLEREDE fjernet i §5a — verifiser med `git worktree list` at ingen worktree holder PR-branchen FØR merge, ellers feiler branch-slettingen. Verifiser base FØR merge: `gh pr view <pr> --json baseRefName -q .baseRefName` → `{{BASE_BRANCH}}`. Merge-konflikt → ⚠️ STOPP, release claim, rapporter.

   **CI-sjekk FØR merge (obligatorisk, ikke bare deployment-status):** hent BÅDE commit-status OG check-runs — `gh pr checks <pr>` (eller tilsvarende `get_check_runs`) dekker separate GitHub Actions-sjekker (f.eks. en `verify`-workflow med tester/type/lint) som en ren deployment-status-sjekk (f.eks. Vercel) IKKE fanger opp. En rød sjekk der:
   - Hent job-loggen og bekreft om feilen er en KJENT, allerede logget pre-eksisterende feil (grep testnavn/assertion mot `tasks/bugs.md`) → dokumenter i merge-beslutningen, merge likevel.
   - Ny/ukjent feil → ⚠️ STOPP, release claim, rapporter — ikke merge en reell regresjon.
   Hopp aldri over denne sjekken «fordi Vercel er grønn» — de er uavhengige signaler.

   **Todo-nr-kollisjonssjekk FØR merge (TO gater — hver dekker en tilstand den andre
   strukturelt ikke ser):**

   - **(a)** kjør `sh scripts/check-todo-nr-collisions.sh` i dev-arbeidstreet. Dekker
     koordinatorens EGNE ucommitterte §6.3/§6b/§7-endringer (arkivering/bug-triage/nummer-
     reservasjon som ennå ikke er pushet) — den eneste tilstanden (b) aldri kan se, fordi
     (b) kun leser committede refs.
   - **(b)** kjør `sh scripts/check-todo-nr-premerge.sh <branch>` (bygger
     `git merge-tree`-resultatet av en fersk `origin/{{BASE_BRANCH}}` og PR-branchen,
     materialiserer `tasks/`-treet derfra, og kjører (a)-scriptet mot DET). Dekker PR-ens
     **innkommende** nr mot en fersk base — noe (a) strukturelt ikke ser, siden (a) kun ser
     dev-arbeidstreet ELLER én ref om gangen, aldri hva de to blir SAMMEN. Branch-utledning:
     ```bash
     br=$(gh pr view <pr> --json headRefName -q .headRefName)
     sh scripts/check-todo-nr-premerge.sh "$br"
     ```
     Exit-kontrakt: `0` ingen kollisjon — **står det en WARN om fetch-svikt på stderr, er
     basen muligens foreldet og 0 er DA IKKE grønt**; les WARN-linja før du stoler på
     exit-koden · `1` BLOKKERENDE kollisjon → ⚠️ STOPP, IKKE merge
     — følg renummererings-oppskriften i **§8** (git mv + oppdater `nr`/`order`/`deps`/
     kryssreferanser, «sist inn flytter»-regelen), re-kjør (b), prøv igjen · `2` intern feil
     (ukjent ref / git for gammel VED OPPSTART / uventet `merge-tree`-exit — typisk
     ubeslektede historier (ingen felles merge-base) eller et utilgjengelig objekt, IKKE en
     for gammel git siden versjonen alt er verifisert / `tasks/` mangler i treet) →
     ⚠️ STOPP, les ALDRI som grønt, eskalér · `3` merge-konflikt → ⚠️ STOPP, samme
     merge-konflikt-pause som over; sjekken ble ikke kjørt. **En konfliktsti under
     `tasks/todos/` med SAMME nr+slug på begge sider ER en nr-kollisjon** (add/add på
     identisk sti, ulikt innhold) — følg renummererings-oppskriften i §8, ikke bare
     merge-konflikt-pausen. Presisering: identisk fil lagt til på begge sider merges REN og
     er per definisjon ikke en kollisjon — exit 3 er ikke garantert for enhver
     dobbeltopprettelse, kun for ULIKT innhold på samme sti.

   Gate (b) ser KUN committet+pushet tilstand; ucommitterte delt-state-endringer i
   dev-arbeidstreet dekkes av gate (a). De to er et TILLEGG til hverandre, aldri en
   erstatning: exit 2/1 fra (b) stopper uansett hva (a) sa.

   **«Krymper — lukker ikke» + kjøretidspunkt:** gate (b) er den ENESTE gaten som ser
   PR-ens innkommende nr mot en fersk base — men den KRYMPER, LUKKER IKKE, TOCTOU-vinduet:
   den leser `origin/{{BASE_BRANCH}}` på kjøretidspunktet, så vinduet flyttes fra «siden
   branchen ble skåret» til «siden gaten kjørte». Kjør (b) som **SISTE handling før
   `gh pr merge`** — ingen steg imellom; endres `{{BASE_BRANCH}}` i mellomtiden (en annen
   sesjons merge), kjør (b) på nytt. Gate (a) dekker koordinatorens egne ucommitterte
   delt-state-endringer, som (b) ikke ser.

   **Branch-protection «require branches up to date» vurdert og forkastet:** ville lukket
   vinduet helt, men koster at HVER åpen PR må oppdateres med fersk base + full CI-runde per
   parallell merge — i et repo der eier bevisst kjører mange parallelle koordinatorer er det
   en merge-seriellisering av hele flyten. Ikke-blokkerende, ligger i §6g-eier-
   beslutningskøen, default = ikke aktivert.

   `todo-nr-guard`-CI-jobben ser PR-ens merge-commit på CI-**tidspunktet** og er backstop for
   NESTE PR — den fanger IKKE et race mot en `{{BASE_BRANCH}}` som avanserer ETTER PR-ens
   siste grønne CI-kjøring (GitHub re-kjører ikke en allerede-grønn PR automatisk uten
   branch-protection «require branches up to date»). Gate (b) kjøres derfor lokalt: den
   trenger to FERSKE refs (base + branch) som CI-kjøringen ikke har på merge-tidspunktet.

   **Worktree-rydding etter merge** (gjelder ALLE agenter som jobbet med denne todoen — planner, reviewer, implementer, evt. fix-mode-runder, code-reviewer — ikke kun implementerens branch; se `git worktree list` for fullstendig liste. Erstatt `<branch>` med hver enkelt branch):
   ```bash
   wt_path=$(git worktree list --porcelain \
     | awk -v b="refs/heads/<branch>" '/^worktree /{w=$2} /^branch /{if($2==b){print w; exit}}')
   if [ -n "$wt_path" ]; then
     locked=$(git worktree list --porcelain \
       | awk '/^worktree /{w=$2; lk=0} /^locked/{lk=1} w=="'"$wt_path"'" && lk{print "yes"; exit}')
     if [ "$locked" != "yes" ]; then
       dirty=$(git -C "$wt_path" status --porcelain 2>/dev/null)
       if [ -z "$dirty" ]; then
         if git worktree remove "$wt_path" --force 2>/dev/null; then
           git branch -d <branch> 2>/dev/null || git branch -D <branch> 2>/dev/null
         else
           echo "ADVARSEL: git worktree remove feilet for $wt_path" >&2
         fi
       else
         echo "ADVARSEL: $wt_path har ucommittede endringer — sletter ikke, eskalér manuelt" >&2
       fi
     fi
   fi
   ```
   *Kommentar:* awk bruker streng-match (`$2==b`) — trygt for branch-navn med `/`. `git branch -d`
   kjøres KUN etter vellykket `worktree remove` (exit 0). Locked-deteksjon er alltid dynamisk.
5. **Append til run-log:** les telemetrien fra (a) ferdig-rapportens `todo_nr`, `slug`, `pr_url`; (b) egne kontekst-tellere (§4-revisjonsrunder, §5b-kode-review-runder); (c) Modeller-tabellen i `docs/orchestration-loop.md` (planner/reviewer/implementer/code-reviewer); (d) `verification.e2e_skipped` og `verification.playwright_available` fra ferdig-rapporten — map til `degradation`-kolonnen per format-spec i `run-log.md`: `e2e_skipped=true` → `e2e_skipped`; ellers `-`. Default `-`. Append én linje til `docs/superpowers/loop/run-log.md` etter format-spec-en i samme fil. Workers rører ALDRI run-log.md — de returnerer telemetrien som rapport-data, koordinatoren appender.
6. **OBLIGATORISK pre-commit-sjekk (primærvernet — hooken i `.githooks/pre-commit` er kun backstop):**
   kjør `git status --short` UMIDDELBART FØR du committer delt-state-endringene, og inspiser
   output linje for linje. Uventede filer (spesielt utenfor `tasks/`/`docs/`/`.claude/`/
   `v2-agent-orchestrator/`/`.gitignore`) betyr at en parallell sesjons `git add -A` har lekket
   inn i den delte `.git/index` (TOCTOU-vindu mellom en tidligere sjekk og nå — se
   `tasks/lessons/workflow-process.md` 2026-07-12). Av-stage/tilbakestill dem (`git restore
   --staged <fil>`) FØR du committer — commit ALDRI blindt på antakelsen om at indeksen
   fortsatt kun inneholder dine egne endringer.
   **265-gjenopprettingsoppskrift** (hvis noe likevel lekker inn i en commit — enten fordi
   sjekken ble hoppet over, eller hooken ble bypasset med `--no-verify`): (a) verifiser det
   lekkede innholdet mot kilde-branchen (`git log --oneline -- <fil>` / `git diff` mot
   feature-branchens PR) for å bekrefte hva som faktisk lekket; (b) gjenopprett riktig innhold
   på `{{BASE_BRANCH}}` — `git checkout <parent-commit> -- <filer>` (fjern det lekkede) eller
   `git rm <filer>` hvis de ikke skal finnes der i det hele tatt; (c) commit reverten separat
   med en tydelig melding («revert: fjern lekket <fil> fra feil commit»); (d) la det lekkede
   innholdet lande via sin ORDINÆRE PR i stedet, ikke gjeninnfør det direkte.
   Commit delt-state-endringene på `{{BASE_BRANCH}}`, så `git push origin {{BASE_BRANCH}}`.

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

### Etter §6c

- Grønn helsesjekk → fortsett normalt (til grooming eller neste todo).
- Rød helsesjekk (regresjon eller infra-feil) → ⚠️ PAUSEPUNKT: eskalér til mennesket med detaljer,
  sett `pause_event=helsesjekk-rød` i health-raden, release evt. aktiv claim og stopp loopen.

## 6f. Loop-selvevaluering (betinget, kun koordinator, hver {{LOOP_EVAL_INTERVAL}}. merge)

**Egen teller, uavhengig av §6c-helsesjekkens teller.** Formålet er ikke prosjekt-kodekvalitet (det er §6c) — det er LOOPENS EGEN ytelse: tid, token, sikkerhet, prosess-friksjon.

**Teller-invariant:** kun `outcome=merged` telles — `outcome=hotfix`-rader (se
`docs/hotfix-runbook.md`) er per konstruksjon usynlige for denne telleren og for §6c.

Tell rader med `outcome=merged` etter den *siste* raden med `outcome=loop-eval` i run-log (samme mønster som §6c):

```bash
awk '
  /\| loop-eval \|/ { count=0; next }
  /\| merged \|/ { count++ }
  END { print count }
' docs/superpowers/loop/run-log.md
```

Count ≥ {{LOOP_EVAL_INTERVAL}} → kjør denne evalueringen NÅ (før neste dispatch):

1. **Samle data** for todoene siden forrige `loop-eval`-rad: tid (run-log-tidsstempler, delta mellom merges), token (summer `subagent_tokens` fra hver dispatch-rapport i denne sesjonens kontekst — planner/reviewer/implementer/kode-reviewer, inkl. revisjons-/fix-mode-runder), sikkerhet (security_findings på tvers av batchen, migrasjoner/RLS-endringer, ev. falske positiver fra reviewere), prosess-friksjon (PR-opprettelses-feil, planner-committ-glipp, stanset-uten-rapport-hendelser, revisjonsrunder, CI-avvik).
2. **Skriv en rapport** til `docs/superpowers/loop/evaluations/eval-<dato>-<todo-range>.md` — struktur: tid, token, sikkerhet, friksjon, implementerte endringer, anbefaling videre, **åpne eier-beslutninger** (drenér beslutningskøen fra §6g: list hvert buntet ikke-blokkerende punkt med anbefalt default, slik at eier kan svare på alle i én omgang).
3. **Implementer trygge optimaliseringer direkte** — men KUN prosess-/mal-endringer i `v2-agent-orchestrator/templates/` + `loop.config.yaml` etterfulgt av `/setup`. **ALDRI** app-kode, ALDRI noe som treffer en pause-trigger-kategori ({{PAUSE_TRIGGERS}}) uten eiers go. Er en optimalisering usikker eller berører faktisk produktkode/-arkitektur → foreslå den i rapporten i stedet for å implementere den, og la mennesket avgjøre.
4. Append en rad til run-log: `outcome=loop-eval`, `slug=loop-self-eval`, `pr=-`, `health_payload=-`, med lenke til rapportfilen i `notes`-feltet (gjenbruk `health_payload`-kolonnens format løst — se eksisterende `loop-eval`-rader for presedens etter første runde).
5. Commit rapporten + evt. malendringer + run-log-raden sammen, push til `{{BASE_BRANCH}}`.

Denne evalueringen er ALDRI en pause-trigger i seg selv — den kjøres og fullføres, deretter fortsetter loopen normalt.

## 6g. Eier-beslutningskø + konservativ-default-protokoll

Skill mellom to klasser eier-beslutninger — de behandles ULIKT:

**BLOKKERENDE (spør umiddelbart med AskUserQuestion og VENT — som før):** irreversible
handlinger, samtykke-/personvern-scope, datasletting, migrasjon/RLS-endringer utover planen,
publisering av dristige påstander uten forsvarlig default, alt som treffer en
pause-trigger-kategori ({{PAUSE_TRIGGERS}}).

**IKKE-BLOKKERENDE (buntes — IKKE enkeltavbrudd):** reversible valg med en forsvarlig default —
tekst/kosmetikk, terskelverdier som lett justeres, navnevalg, «A eller B der begge er trygge».
Disse samles i en `## Eier-beslutningskø`-seksjon nederst i run-log (append-only, koordinator
er eneste skriver) med format: `- [åpen] <dato> todo-<nr>: <spørsmål> — valgt default: <X>
(reversibelt: <hvordan>)`. Køen presenteres SAMLET i neste batch-/eval-rapport (§6f) eller i én
buntet AskUserQuestion når ≥3 punkter ligger åpne. Ved eier-svar: marker raden `[avgjort]`.

**Konservativ-default-protokollen (265-presedensen, nå regel):** ved AskUserQuestion-infra-feil
×3 PÅ RAD, eller når eier er utilgjengelig og punktet er ikke-blokkerende: velg det
konservative/ærlige alternativet (det som er lettest å reversere og aldri overdriver en påstand),
merk det eksplisitt som reversibelt + flagget i beslutningskøen, og fortsett. Rapportér valget i
neste rapport. Protokollen gjelder ALDRI for den blokkerende klassen — der ventes det, uansett.

## 7. Grooming-modus (kø tom)

Kjør §6c-helsesjekk FØR grooming-forslag (se §6c over).

Ingen kvalifisert todo → IKKE stopp tomt. Foreslå inntil **3** nye todos/bugs som UTKAST med `status: deferred` + `tags: [forslag]`, basert på backlog/arkiv/observasjoner. Auto-implementer ALDRI selvgenerert arbeid. Etter 3 forslag: STOPP og rapporter til mennesket for triage. (Exit-kriterium hindrer uendelig grooming.)

**Forslag-konvensjon:** Hvert grooming-forslag opprettes med disse to feltene i frontmatteren:
```yaml
status: deferred
tags: [forslag]
```
Kombinasjonen er dobbel gating: `status: deferred` holder forslaget ute av §1-køen (som kun plukker `status: open`), og `tags: [forslag]` holder det ute selv om noen ved uhell flipper statusen uten å fjerne taggen.

**Triage (gjøres av mennesket):** Et forslag godkjennes ved å flippe `status: deferred → open` OG fjerne `forslag`-taggen (`tags: []`). Begge endringer er nødvendige — kun én av dem er ikke tilstrekkelig for å gjøre forslaget kvalifisert (`elig=YES`). Avviste forslag beholder `status: deferred` og kan slettes eller beholdes som referanse.

**Nummer-reservasjon ved todo-opprettelse:** se **§8** for hvordan `nr` velges/reserveres, hva
som teller som reservert, og renummererings-oppskriften (nyttig i det tidskritiske
exit-1-øyeblikket rett før merge — §6.4).

## 8. Todo-nummer: reservasjon, kollisjon og renummerering

Racet ved *valg* av `nr` kan ikke lukkes uten atomisk reservasjon. §6.4 (gate (b),
`check-todo-nr-premerge.sh`) evaluerer merge-RESULTATET og fanger den andre siden av en
kollisjon rett før merge — men KRYMPER, LUKKER IKKE, TOCTOU-vinduet (se §6.4).

**Reservasjon teller FØRST når** minimal frontmatter (tittel + `nr` + status) er committet
**og pushet** til `{{BASE_BRANCH}}`. Todos som fødes inne i en feature-PR er IKKE reservert —
det bæres i stedet av §6.4s gate (b).

Velg `nr` for en ny todo/forslag via `sh scripts/check-todo-nr-collisions.sh --next` (mot en
**fersk** `origin/{{BASE_BRANCH}}`, ikke en lokal branch som kan ligge bak). Reserver deretter
nummeret ved å committe OG PUSHE en minimal todo-fil med kun frontmatteren til
`{{BASE_BRANCH}}` FØR resten av innholdet skrives — dette krymper vinduet en annen sesjon kan
rekke å velge samme `nr` i, men eliminerer det ikke (kun en ekte atomisk reservasjon eller
ikke-sekvensielle IDer ville gjort det).

**Retningsregel: «sist inn flytter».** Ved kollisjon renummererer den PR-en som ennå ikke har
merget; den allerede mergede serien står urørt. Uten regelen kan begge sesjoner begynne
renummereringen samtidig.

**Renummererings-oppskrift** (trigges av §6.4s gate (b) exit 1, eller exit 3 med en
konfliktsti under `tasks/todos/` som er en reell nr-kollisjon — se §6.4):
1. Nye nr med `--next` mot fersk `origin/{{BASE_BRANCH}}`; for en epic tas alle N samtidig.
2. `git mv` filnavn + oppdater `nr`, `order`, `deps`.
3. Prosa: `git grep -niE 'todo-0*<gammelt-nr>([^0-9]|$)' -- tasks docs` — klassifiser **hvert**
   treff. Guarden validerer kun `nr`-unikhet og er `exit 0` mens hver prosareferanse peker på
   feil todo.
4. Bare-tall-referanser (`438–443`) fanges IKKE av grep — les de flyttede filene manuelt
   (`git diff --name-only`). Dette er en sjekkliste, ikke en vakt.
5. Re-kjør `sh scripts/check-todo-nr-premerge.sh <branch>` (§6.4s gate (b)) før nytt
   merge-forsøk.

## Pausepunkter (alltid eskalér + release claim)

- Teknisk risiko flagget (§4) eller truffet (§5/§6)
- Brainstorm-påkrevd todo (hoppet over i §1)
- Reviewer no-go som ikke konvergerer etter 2 runder (§4)
- Kode-reviewer revise-gate som ikke konvergerer etter 2 runder (§5b)
- §5b-probe feiler («Agent type not found») → fersk koordinator-sesjon kreves
- Merge-konflikt (§6.4)
- `git`/working-tree ikke ren (§0)
- `canary`-mismatch som ikke løses (§3)
- Helsesjekk rød (§6c) — regresjon eller infra-feil i integrert `{{BASE_BRANCH}}`
