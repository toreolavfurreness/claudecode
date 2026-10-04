<!--
  GENERERT av /setup fra loop.config.yaml — IKKE rediger her.
  Endre loop.config.yaml og kjør /setup på nytt.
-->

# 5c. Pipelining (plan neste todo mens denne implementeres)

→ Kjerne: `coordinator-runbook.md` § 5c · Begrunnelser: `runbook-hvorfor.md` § 5c

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
`reviewed` sender B gjennom §2s `reviewed`-gren, ikke `pipelinet`-grenen, og da forsvinner
markørlinja med `pipelined_from` og de faktiske modellene. Det eneste feltet du skriver på B før
claim er `plan:`.

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
  | grep -vE '^(tasks/plans/|tasks/todos/|tasks/todo_archive\.md|tasks/lessons|tasks/followups/)' \
  | grep -vE '^docs/superpowers/loop/(run-log|retro-log|retro-triage)\.md'
```

Alle de ekskluderte er **append-only delt state** som §6 skriver på vegne av A, ikke innhold en plan
kan bli stale mot. **Unntak, gitt som ferdig alternativ filterlinje (ikke en håndredigering av
ERE-en i drift):** skal B-planen ENDRE eksisterende lessons-innhold (omstrukturere, ikke bare få
appendet en lesson av §6), bruk denne varianten av første filter for den runden:

```bash
grep -vE '^(tasks/plans/|tasks/todos/|tasks/todo_archive\.md|tasks/followups/)'
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
under (technical_risk i plan/plan-review, §4 no-go uten konvergens, canary-mismatch) kjøres UAVHENGIG av
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
