<!--
  GENERERT av /setup fra loop.config.yaml — IKKE rediger her.
  Endre loop.config.yaml og kjør /setup på nytt.
-->

# 5d. Parallelle implementere (fil-disjunkt-gate — TODO 233)

→ Kjerne: `coordinator-runbook.md` § 5d · Begrunnelser: `runbook-hvorfor.md` § 5d

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
  --plan-b tasks/plans/todo-<B>-<slug>.md
```

`ok` (exit 0) ⇒ fortsett. `overlap` / `empty-a` / `empty-b` / `missing-section`
(exit 1) ⇒ ingen parallellitet denne runden; B beholder planen sin og claimes normalt via §1 i en
SENERE runde (samme fail-safe-retning som §5cs ferskhets-gate). Klientkode (`app/`, `components/`, `lib/`) er tillatt på begge sider: egen port
og e2e-låsen fra TODO 184 serialiserer e2e-kjøringene, og regelen «B etter A, begge med klientkode»
under dekker samspillet som felles filer ikke viser.

**Gate M sin fail-retning er «drop til serielt», ikke pausepunkt.** Ikke-tomt snitt i gate M betyr
at **parallelliteten ikke lenger er gyldig** — typisk fordi A sin §5b-fix-runde lovlig utvidet A sin
diff etter at gate P sa ja — IKKE at gaten er defekt. Riktig respons er å degradere til den
serielle stien.

**Gate M (i) — inkrementelt varsel, etter HVER A-fix-runde.** B har ennå ikke nødvendigvis en egen
PR, så B-siden er den samme DEKLARERTE plan-listen gate P allerede leste:

```bash
gh pr diff <A-pr> --name-only > <scratch>/gate-m-a-<runde>.txt
python3 tasks/parallel-disjoint.py --a <scratch>/gate-m-a-<runde>.txt \
  --plan-b tasks/plans/todo-<B>-<slug>.md
```

Et rødt `overlap`/`empty-a`/`empty-b`-utfall her er kun et TIDLIG varsel (koordinatoren kan bestille
B sin re-synk tidligere); det er den BINDENDE formen (ii) under som faktisk styrer
merge-rekkefølgen for B.

**Gate M (ii) — bindende, FØR merge av B:**

```bash
gh pr diff <A-pr> --name-only > <scratch>/gate-m-a-<runde>.txt
gh pr diff <B-pr> --name-only > <scratch>/gate-m-b-<runde>.txt
python3 tasks/parallel-disjoint.py --a <scratch>/gate-m-a-<runde>.txt --b <scratch>/gate-m-b-<runde>.txt
```

- `ok` ⇒ videre til MERGEABLE-sjekken (§6).
- **`overlap`/`empty-a`/`empty-b` ⇒ DROP TIL SERIELT** (ikke pausepunkt): B settes til
  `stadium: serialized`, og B-implementeren dispatches i fix-mode-stien
  `todo-finish-worker.md:46–47` (`git fetch origin {{BASE_BRANCH}} && git merge origin/{{BASE_BRANCH}}`) + re-kjøring av
  verifiseringssettet (`npm run build:web`, `npx tsc --noEmit`, `npm run format:check`,
  `npm run test:unit`) + push. **Ny kode-review-runde kreves KUN hvis merge-en måtte
  konfliktløses** — en ren merge endrer ingen linje B har skrevet, og §5b sitt trigger-sett er
  «nye commits som endrer B sin diff». Måles: rapporterte merge-en konflikt? ja ⇒ §5b `r_{n+1}`;
  nei ⇒ rett til MERGEABLE-sjekken.
- **B etter A, begge med klientkode (TODO 184-oppfølging, 2026-10-02).** Rører BÅDE A sin og B sin
  PR-diff `app/`, `components/` eller `lib/` (`grep -E '^(app|components|lib)/'` på de to
  `gh pr diff --name-only`-listene over), kan B bryte mot A uten felles fil, for eksempel når A
  endrer en hook B bruker. CI kjører ingen e2e, så B synker mot base som i `overlap`-grenen og
  kjører steg 2 og 2a på nytt under e2e-låsen før merge. Faktisk utfall i ny ferdig-rapport;
  rødt ⇒ §5b-fix-runde, ikke merge.
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
[gate M (i) varsel etter hver A-fix-runde] →
snapshot par4 → PAR 4 [code-rev(A) r2 (hvis) + code-rev(B) r1] → … →
A go ⇒ §6(A): delt state + merge A (KUN A sin rad til §0b) → dev-CI-differensial #1 →
B go ⇒ GATE M (ii) (bindende) → [overlap/empty-a/empty-b ⇒ drop til serielt: B synker mot dev + re-verifiserer. Begge med klientkode ⇒ B synker + steg 2/2a på nytt] →
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
- **e2e:** steg 2 og 2a kjøres som normalt når egen diff rører `app/`, `components/` eller `lib/`,
  med egen port og e2e-låsen fra `todo-finish-worker.md` steg 2 (TODO 184). Låsen serialiserer
  kjøringene, så de delte testbrukerne brukes aldri samtidig (lukker CF-233-1).

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
CF-233-6 (`tasks/followups/`) for driftsbeviset dette venter på.
