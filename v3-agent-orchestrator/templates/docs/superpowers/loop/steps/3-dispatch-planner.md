<!--
  GENERERT av /setup fra loop.config.yaml — IKKE rediger her.
  Endre loop.config.yaml og kjør /setup på nytt.
-->

# 3. Dispatch planner

→ Kjerne: `coordinator-runbook.md` § 3 · Begrunnelser: `runbook-hvorfor.md` § 3

**Proporsjonalitetsport — tre målinger FØR dispatch (BINDENDE, ~1 minutt).** Skriv svarene inn i
dispatchen. De fanger den dyreste feilklassen: en liten todo som vokser til en stor leveranse
fordi hver runde legger til lag og ingen fjerner noen.
1. **Finnes løsningen allerede?** Ett `grep` på todoens sentrale begrep. Finnes den, oppgi
   `sti:linje` — «kopier denne formen» er en annen instruks enn «design en løsning».
2. **Hva er kjernen, i linjer og filer?** Skriv anslaget ned før du dispatcher. Det er et
   referansepunkt å måle avviket mot, ikke et løfte.
3. **Sett et budsjett** (linjer og filer). §4 stopper før review hvis planen sprenger det med mer
   enn ~5×.
Målt i et annet prosjekt med samme loop: en todo med 4 linjers kjerne ble 828 linjer i 13 filer og
1,23 M tokens med alle gater grønne. Planen nådde aldri konsolideringsterskelen, og løsningen fantes
ett `grep` unna.

Velg et **canary-mål** workeren ikke kan gjette: en fil+linje som ikke er en invariant og ikke gjentas i prompten (f.eks. `{{CANARY_FILE}}` linje N — varier N per dispatch). Noter den faktiske teksten selv (`sed -n 'Np' {{CANARY_FILE}}`).

**Pre-dispatch-snapshot (§0b vakt 5, R21) — umiddelbart FØR `Agent`-blokken under:**
```bash
git worktree list --porcelain > "<scratch>/wt-pre-3-planner-<runde>.txt"
```

<!-- mekanisk-kandidat: pre-dispatch snapshot — hook som skriver git worktree list --porcelain før hver isolation: worktree-dispatch (mangler) -->

Sjekk exit-koden fra DENNE kommandoen med det samme: ikke-null exit ⇒ dispatchen fortsetter uendret
(worktreen skal ikke droppes fordi et snapshot feilet), men noter paret som `snapshot-missing` — §0b
vil da selv gi ADVARSEL (`snapshot-missing`) og INGEN rydding for nettopp dette paret, i stedet for å
stille anta at et tomt/manglende snapshot betyr «ren». Én fil per dispatch — gjenbruk ALDRI én fil på
tvers av dispatches (se §0b, R21).

`Agent`: `subagent_type: {{PROJECT_NAME}}-planner`. Prompt:
> TODO <nr> (`tasks/todos/todo-<nr>-<slug>.md`). Relevante lessons-tema: <liste>. Eksisterende løsning: <`sti:linje` eller «ingen funnet»>. Kjerne-anslag: <linjer>/<filer>. Budsjett: <linjer>/<filer>. Release-mål: <`goal` fra den aktive releasen, eller «ingen aktiv release»> — planen tjener målet, og arbeid utover todoen blir funn i rapporten, ikke steg. Canary: tell til linje <N> i `{{CANARY_FILE}}` og returner BÅDE linjenummeret du landet på OG de første 8 ordene på den linja. Følg charteret ditt. Returner plan-rapport som JSON.

Verifiser `canary` mot den faktiske teksten du noterte. Riktig tekst og riktig nummer → OK. Teksten
er ekte, men fra en annen linje enn <N> (nummeret workeren oppga stemmer med teksten) → telle-drift,
ikke manglende lesing: noter det, ingen re-dispatch. Teksten finnes ikke på linja workeren oppga →
re-dispatch eller eskalér (workeren leste sannsynligvis ikke filene). Målt: 2 av 3 plannere returnerte
ekte tekst fra ±2–4 linjer feil, og uten nummeret så det ut som manglende lesing. Koordinatoren (du) setter `plan:`-stien fra rapportens `plan_path` i todo-frontmatteren — workeren rører den ikke.

<!-- mekanisk-kandidat: canary i rapporten matcher fila — sammenlign med sed -n Np (mangler) -->

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
