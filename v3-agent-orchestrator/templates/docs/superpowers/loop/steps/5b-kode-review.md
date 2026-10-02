<!--
  GENERERT av /setup fra loop.config.yaml — IKKE rediger her.
  Endre loop.config.yaml og kjør /setup på nytt.
-->

# 5b. Uavhengig kode-review

→ Kjerne: `coordinator-runbook.md` § 5b · Begrunnelser: `runbook-hvorfor.md` § 5b

### Minne-gate (før dispatch)

Endrer PR-diffen `.claude/agent-memory/` (`gh pr diff <n> --name-only | grep -c '^.claude/agent-memory/'` ≥ 1),
SKAL ferdig-rapporten ha `memory_check` med grep-kommando og output per ny linje (implementer-charteret
§ Rollehukommelse). Mangler feltet, send implementeren tilbake med SendMessage FØR kode-review.
En kopi i minnet ga en ekstra runde tre ganger i én release i opphavsprosjektet.

<!-- mekanisk-kandidat: Minne-gate — gh pr diff --name-only mot .claude/agent-memory/ + memory_check i rapporten (mangler) -->

### Probe (dekket av preflight — én gang per sesjon)

Agent-registeret er sesjonsglobalt og snapshottes ved sesjonsstart (se «Forutsetning» øverst i kjernen `coordinator-runbook.md`) — det endres
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

- Inneholder rapporten **≥1 BLOKKERENDE eller ≥1 VIKTIG** → **revise-gate**: send funnene tilbake til implementeren via fix-mode-dispatch (se fix-mode-mal under). Når fix-rapporten kommer tilbake: kjør **Gate F** (under) FØR du dispatcher kode-review r(N+1) — rød gate F ⇒ mekanisk retur, ingen ny review. **Hold en eksplisitt teller** («kode-review-runde N», samme mønster som §4). **Nivå B1 (TODO 246/455):** ved HVER utløst revise-gate, også runde 1, kjøres `python3 tasks/measure-cost.py --brake <nr> --pr <PR-nr>` og så `decision-level.py` med `cost_over=<over>`; fra runde 2 også med `decision_logged=yes` og konvergensdata (se `coordinator-runbook.md` § Konvergensregel). Valget mellom (a) ny fix-runde, (b) merge med carry-forwards, eller (c) stopp er **nivå B1** så lenge funnene konvergerer og kostnaden er under taket. Koordinatoren velger selv (anbefalt handling), logger alle fire pliktene i § Pausepunkter, og fortsetter — mennesket kan vetoe i etterkant. Gir et nytt `fix_round`-forsøk **A0** (uten konvergens eller over kostnadstaket) → ⚠️ eskalér til mennesket, release claim. En LUKKENDE beslutning (`merge_carry`/`stop`) forblir nivå B1 uansett rundetall.


```bash
python3 tasks/decision-level.py --event revise_gate_choice --context code_review_rounds=1 --context action=fix_round --context cost_over=no
python3 tasks/decision-level.py --event revise_gate_choice --context code_review_rounds=2 --context action=fix_round --context decision_logged=yes --context blocking_prev=3 --context blocking_now=1 --context new_class=no --context content=no --context cost_over=no
```

- **Rotårsaksanalyse før eskalering (eier 2026-09-26, etter TODO 283A: 7 kode-review-runder; omformet i TODO 455).** Når konvergensregelen gir A0 på §5b, dispatches én skrivebeskyttet analyse med dyp modell (`{{PROJECT_NAME}}-planner` med `model: "{{DEEP_MODEL_ALIAS}}"`, uten skriving) som svarer på tre spørsmål: (1) hvilken feilklasse hører funnene fra r1+r2 til, (2) kan omfanget kuttes i stedet for å fikses (skip + telling, avvis formen), (3) er tilnærmingen feil (f.eks. forutsi et biblioteks feil vs. kontrollere resultatet). Svaret blir `Anbefaling:` i A-spørsmålet til mennesket. En konvergerende B1-runde trenger ingen analyse (283A-mønsteret, «hver fix-runde åpnet en ny feilklasse», er `new_class=yes` og gir A0, så analysen kjører fortsatt der). **Hvorfor:** hver fix-runde som utvidet semantikken åpnet en ny feilklasse; kuttet i r7 burde kommet ved r3. Fix-runde 3+ går i tillegg alltid med modell-override (se «Modell-eskalering fra fix-runde 3») — sjekk at `model` faktisk står i `Agent`-kallet.
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

**Arbeidstre-vakt (TODO 292 — BINDENDE ved `violation`).** Kjør mot samme `<scratch>/fan-in.json`
(gjelder både form A og form B), ett kall:

```bash
jq -r 'def norm: [splits("\\s+")] | map(select(length > 0)); .worktree_guard as $g | if (.dispatched // [] | length) == 0 then "none" elif $g == null then "missing" elif ($g | type) == "object" and ($g.before | type) == "string" and ($g.after | type) == "string" and ($g.before | test("[0-9a-f]{40}")) and ($g.before | norm) == ($g.after | norm) then "ok" else "violation" end' <scratch>/fan-in.json
```

Skriv `wtguard=<utskrift>` (uten `strict:`-prefiks) i `run-log.md`, i samme frittekst-felt som
`attest=`, med samme radregler som `attest=` (se «`attest=<verdi>`» under). `violation` betyr at
kode-reviewerens arbeidstre ble endret under lens-runden (eller at `worktree_guard` er misdannet),
og gjør rapporten USIGNERT: samme prosedyre
som exit 3 i avvisningstabellen under «Kontrakt-vakt (TODO 250B)» — forkast, og dispatch fersk
kode-reviewer med bruddkoden `worktree-moved` og begge strengene sitert ordrett i prompten. Teller
ikke som kode-review-runde, men mot samme tak: maks 2 re-dispatcher per §5b-runde, deretter nivå
A0; andre `violation` i samme §5b-runde ⇒ nivå A0. `missing` (lens dispatchet, feltet mangler —
f.eks. et charter fra før TODO 292 i sesjonens agent-snapshot) stopper ingenting. `none` = ingen
lens dispatchet.

**Severity-gulv (TODO 180B — BINDENDE, håndhevet i kode, IKKE `observe`):**

I motsetning til fan-in-sammenligningen over (som kun logger i `observe`), er severity-gulvet
bindende fra denne PR-en av: `rls-migration-reviewer` og `edge-function-reviewer` var
`funn→BLOKKERENDE` automatisk FØR 180B; etter 180B er det et steg NOEN må ta. Etter at
`fan_in.expected_by_selector` er fylt over, kjør (`python3` er ikke i read-only-rollenes
Bash-allowlist, `guard-reviewer-readonly.sh:689`, TODO 189 er fortsatt `open`, så dette kjøres her,
av koordinatoren, aldri av revieweren), tre separate kall — de to fetchene gjør både `{{BASE_BRANCH}}` og
PR-hodet (`<sha>`) lesbare lokalt FØR selve skriptkallet:

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
40-tegns SHA. De to fetchene over gjør både `{{BASE_BRANCH}}` og PR-hodet lesbare lokalt. Uten dem, eller uten
`--rev`, avvises hvert `floor_exempt`-merket funn mekanisk (`ref_unresolvable`/`no_rev`), og gulvet
gjelder.)

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

<!-- mekanisk-kandidat: severity-gulv, lens-utvalg og fan-in er skript (finnes: tasks/review-severity-floor.py, tasks/review-lens-select.py, tasks/review-fan-in-verify.py) -->

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
(`origin/{{BASE_BRANCH}}` og `origin/pull/<pr>/head`) er allerede kjørt i severity-gulv-blokken over — ingen
ny fetch her, kun selve diff-kommandoen:

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

Kjør deretter «Arbeidstre-vakt (TODO 292)» (over).

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

`Agent`: `subagent_type: {{PROJECT_NAME}}-implementer`, **`model` alltid eksplisitt:** `"{{IMPLEMENTER_MODEL_ALIAS}}"` i fix-runde 1–2, `"{{DEEP_MODEL_ALIAS}}"` fra fix-runde 3 (se «Modell-eskalering fra fix-runde 3»); håndhevet av `.claude/hooks/guard-fix-round-model.sh`, som leser `fix-runde <N>` i prompten. Prompt:

> FIX-MODE for TODO `<nr>`. Du har ALLEREDE implementert denne og laget PR `<pr_url>` på branch `<branch>`. IKKE re-implementer og IKKE kjør `todo-execute.md` på nytt. Gjør KUN dette: (1) `git fetch origin <branch> && git checkout <branch>` og `git fetch origin {{BASE_BRANCH}} && git merge origin/{{BASE_BRANCH}}` for å bygge på ferskeste delt state før re-push (konflikt i planfila: behold BEGGE siders fix-runde-seksjoner, aldri `--ours`/`--theirs` på hele fila); (2) rett UTELUKKENDE disse kode-review-funnene: `<liste med severity + file:line + issue + fix>`. Navngir et funn flere mekanismer, rett hver av dem og kvitter per mekanisme i rapporten — funnet er ikke lukket før alle mekanismene det navngir er rettet; (2b) **SANNHETSKRAV FOR NY TEKST (BINDENDE).** Endrer eller legger du til en brukersynlig streng eller en kodekommentar som PÅSTÅR noe om systemets tilstand eller oppførsel: før du skriver den, finn ALLE kodeveier som når linja, og skriv ordrett i ferdig-rapporten (i) hvilke skriveoperasjoner som ALLEREDE er utført når linja emitteres, og (ii) hvilke som IKKE er det. Teksten må være sann på HVER slik vei — er den sann på én gren og usann på en annen, er den en defekt, ikke en unøyaktighet. Gjelder særlig feilmeldinger i en flerstegs skrivekjede uten transaksjon («ingenting ble lagret» er usant hvis steg 1 av 3 gikk gjennom) og kommentarer skrevet i presens om invarianter som ikke lenger holder. Bruker du en delt mapper/hjelpefunksjon, sjekk også at den nye grenen ikke kaprer kallstedets egen tekst; (3) kjør `{{CMD_BUILD}}` + `{{CMD_TYPE_CHECK}}` + relevante tester på nytt; (4) **re-kjør HELE V-blokken i planen mot HEAD og lim ordrett kommando + output inn i planfilas `#### V-blokk re-kjørt mot HEAD (fix-runde <N>)`-seksjon, med hvert `**V<id>**` på egen linje ved linjestart og minst én fenced kodeblokk under hvert, og med attestasjonslinjen ORDRETT til slutt: Ingen tall arves fra en tidligere runde. Rundens lesson-kandidater skrives i samme seksjon**; (4b) kjør `tasks/gate-f.sh tasks/plans/todo-<nr>-<slug>.md <N> <F3a_ref>` og lim output-linja inn i rapporten — RØD ⇒ rett seksjonen før push; (5) `git push` til samme branch (samme PR — IKKE ny PR, IKKE ny `gh pr create`); (6) returner oppdatert ferdig-rapport. Rør ingenting utenom de oppgitte funnene (unntak: planfilas fix-runde-seksjon, jf. steg 4).

<!-- mekanisk-kandidat: commit-emnet i fix-runden bærer fix-runde <N> — commit-msg-sjekk eller gh api pulls/<nr>/commits (mangler) -->

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
**Ett kall (2026-09-27):** `tasks/gate-f.sh <scratch>/plan-<N>.md <N> <F3a_ref>` kjører F0–F4 under ordrett og gir GRØNN/RØD med årsak (test: `bash tasks/test-gate-f.sh`). Kommandoene under er definisjonen; F5 er fortsatt manuell.

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

<!-- mekanisk-kandidat: Gate F — V-blokk re-verifisert, F3a (finnes: tasks/vblock-lint.py) -->

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
`models.implementer`. **Fix-runde 3 og senere** — dispatches med prosjektets DYPE modell
(`models.reviewer`/`models.code_reviewer`-klassen i `loop.config.yaml`), ikke `models.implementer`.
Mekanismen er en per-dispatch modell-override i `Agent`-blokken; charterets `model:`-frontmatter
står uendret (den leses ved sesjonsstart, ikke per dispatch). **Mekaniske gate F-returer teller
IKKE med i fix-rundetallet** — bare review-drevne fix-runder gjør det. **Støtter ikke
dispatch-verktøyet en per-kall-override, er dette nivå A0 — eskalér til mennesket. ALDRI stille
fallback til `models.implementer`.** Logg avviket i `run-log.md` felt 9 på formen
`<rask>(r1-rN)+<dyp>(fix rN+1, modellavvik)`, og som nivå-B-entry i `decision-log.md`.

<!-- mekanisk-kandidat: fix-runde ≥3 krever dyp modell i Agent-kallet (finnes: .claude/hooks/guard-fix-round-model.sh) -->

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
