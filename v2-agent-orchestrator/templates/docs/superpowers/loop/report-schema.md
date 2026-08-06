<!--
  GENERERT av /setup fra loop.config.yaml — IKKE rediger her.
  Endre loop.config.yaml og kjør /setup på nytt.
-->

# Loop-rapport-skjema

Rapportene binder koordinator og workers sammen. Hver returneres som ETT JSON-objekt i workerens siste melding (sluttmeldingen ER returverdien — ingen prosa rundt).

## Plan-rapport (planner → koordinator)

```json
{
  "report_type": "plan",
  "todo_nr": "41",
  "slug": "redirect-after-login-next-flyt",
  "branch": "feat/todo-41-redirect-after-login-next-flyt",
  "plan_path": "tasks/plans/todo-41-redirect-after-login-next-flyt.md",
  "summary": "Kort sammendrag av valgt tilnærming (1-3 setninger).",
  "files_touched": ["src/proxy.ts", "src/app/login/page.tsx"],
  "technical_risk": { "flagged": false, "kind": null, "detail": null },
  "deps_ok": true,
  "verification_criteria": ["Uinnlogget bruker på dyp lenke → /login?next=<url>"],
  "canary": "<eksakt tekst fra fil+linje koordinatoren oppga i dispatch>",
  "canary_line": "<linjenummeret planneren FAKTISK leste teksten fra>",
  "status": "reviewed",
  "notes": "Forbehold eller funn."
}
```

- `technical_risk.flagged`: `true` hvis planen krever noe under pause-triggerne. `kind` ∈ `"migration"|"rls"|"prod_push"|"secrets"` (tilpass til prosjektets pause-triggere).
- `deps_ok`: `false` → `status: "blocked"`.
- `canary_line`: linjenummeret teksten faktisk ble lest fra — gjør drift trivielt å diffe (bedt-om
  N vs. lest M); N±1 tolereres, større avvik krever koordinator-faktasjekk av planens påstander
  (drift traff 3/5 plannere i batch 15–16, alltid autentisk tekst).
- `canary`: stikkprøve på at filene faktisk ble lest. Koordinatoren oppgir et mål (fil + linje som IKKE er gjentatt i prompten); planneren returnerer den eksakte teksten. Mismatch = lesing hoppet over. NB: dette beviser at lesing *skjedde*, ikke at *alle* bootstrap-filer ble lest fullt.
- `status` ∈ `"reviewed"|"blocked"`.

## Review-rapport (reviewer → koordinator)

```json
{
  "report_type": "review",
  "todo_nr": "41",
  "plan_path": "tasks/plans/todo-41-redirect-after-login-next-flyt.md",
  "findings": [
    { "severity": "BLOKKERENDE", "ref": "Steg 3", "issue": "…", "fix": "…" },
    { "severity": "VIKTIG", "ref": "Steg 5", "issue": "…", "fix": "…" },
    { "severity": "MINDRE", "ref": "Generelt", "issue": "…", "fix": "…" }
  ],
  "verdict": "no-go",
  "notes": "Samlet vurdering."
}
```

- `severity` ∈ `"BLOKKERENDE"|"VIKTIG"|"MINDRE"`.
- `verdict` ∈ `"go"` (ingen BLOKKERENDE) | `"no-go"` (≥1 BLOKKERENDE → koordinator sender tilbake til planner, maks 2 runder).

## Kode-review-rapport (code-reviewer → koordinator)

```json
{
  "report_type": "code_review",
  "todo_nr": "41",
  "pr_url": "https://github.com/{{GITHUB_REPO}}/pull/42",
  "pr_number": "42",
  "findings": [
    { "severity": "BLOKKERENDE", "ref": "src/app/login/page.tsx:42", "issue": "…", "fix": "…" },
    { "severity": "VIKTIG", "ref": "src/lib/auth/safe-next.ts:17", "issue": "…", "fix": "…" },
    { "severity": "MINDRE", "ref": "src/components/ui/Button.tsx:5", "issue": "…", "fix": "…" }
  ],
  "tech_arm_reports": [
    { "arm": "rls-auditor", "status": "ikke utløst", "report": null },
    { "arm": "{{PROJECT_NAME}}-verifier", "status": "kjørt", "report": { "report_type": "verification", "…": "…" } }
  ],
  "tdd_check": { "required": 0, "red_commits": 0,
                 "l2_status": "ikke utløst", "pairs_replayed": 0, "reason": null },
  "verdict": "no-go",
  "notes": "Samlet vurdering av diffen. KOORDINATOR-HANDLING: par-tak truffet — re-dispatch armen for par 21–27."
}
```

- `findings[]`-objektet har **identisk shape** som plan-review-rapportens `findings[]` (`severity`/`ref`/`issue`/`fix`); for kode-review er `ref` = `file:line`. Ingen omdøping av feltene.
- **`tech_arm_reports[]` er PÅKREVD** (én post per konfigurert tech-arm) og bærer armens rapport
  **ORDRETT og uendret** i `report`. `status` ∈ `"kjørt"|"ikke utløst"|"uteble"|"ikke lastet"`;
  `report: null` for alt annet enn `"kjørt"`.
  **Hvorfor feltet finnes:** innfoldingen i `findings[]` har kun `{severity, ref, issue, fix}` og
  har derfor ingen plass til armens maskinsjekkbare felter (siterte kommandoer, tellinger,
  mutasjons-klasser). Uten `tech_arm_reports[]` kan koordinatoren ikke etterprøve armens påstander
  — armen ville da vært en rutine som gjør mindre enn den ser ut til. Mangler feltet for en arm
  som VAR dispatchet: behandle armens grønt som ugyldig (BLOKKERENDE).
  De to kanalene er komplementære: `findings[]` er det §5b-**gaten** leser, `tech_arm_reports[]`
  er det koordinatorens **mekaniske sjekker** leser.
- **`KOORDINATOR-HANDLING:`-markøren i `notes`:** poster fra en arms `coordinator_actions[]` er
  ikke implementer-handlbare og ligger derfor UTENFOR `findings[]`. De teller ikke mot §5b-revise-
  gaten og bruker ikke en runde; koordinatoren utfører dem før §6.
- `severity` ∈ `"BLOKKERENDE"|"VIKTIG"|"MINDRE"`. Severity-mapping fra tech-review-agenter er definert per agent i `loop.config` (`tech_review_agents[].severity_map`).
- **`tdd_check` er PÅKREVD.** Bærer de MÅLTE tallene fra kode-reviewerens rødt-før-grønt-sjekk
  (TDD-orden): `required` = antall `TDD-STEG` i planen, `red_commits` = antall `test(red):`-commits
  funnet i PR-en, `l2_status` ∈ `"kjørt"|"ikke kjørt"|"ikke utløst"`, `pairs_replayed` = antall par
  faktisk replayet (L2, maks 3), `reason` = MÅLT degraderingsgrunn (`null` når `l2_status: "kjørt"`).
  Bindingsregel for `l2_status` — de tre verdiene er ikke utskiftbare: `"ikke utløst"` =
  `required = 0` / ingen røde commits (det dominerende tilfellet — L2 har ingenting å replaye);
  `"ikke kjørt"` = degradert MED sitert `reason` (oppskriften i L2 ble forsøkt og feilet);
  `"kjørt"` = ≥1 par faktisk replayet. Strukturert felt, ikke prosa — så «hvor mange PR-er kjørte
  L2 faktisk?» er tellbart i ettertid. Erstatter IKKE verifikator-armens mutasjons-gate (se `v1`/`v2`
  under) — de to beviser ulike ting (orden vs. falsifiserbarhet per kallsted i dag). Mangler feltet:
  behandle rapportens TDD-sjekk som ugyldig (samme konsekvensregel som `tech_arm_reports[]` over).
- `verdict` ∈ `"go"` (ingen BLOKKERENDE) | `"no-go"` (≥1 BLOKKERENDE). Identisk terskel som plan-review.
- `verification.review_findings` i ferdig-rapporten er implementerens **selvgransking** (§5 / `/todo-finish-worker` steg 5). `code_review.findings[]` er den **uavhengige §5b-reviewen** og er en separat rapport. Disse er to distinkte kilder.

**Revise-gate (§5b) vs. `verdict` — viktig skille:**

```
verdict = "no-go"  ⟺  minst én BLOKKERENDE  (samme som plan-review og §4)
revise-gate (§5b)  ⟺  minst én BLOKKERENDE ELLER minst én VIKTIG  (= Critical/Important)

→ Rapport med 0 BLOKKERENDE + 1 VIKTIG: verdict = "go", men revise-gate trigges (1 runde tilbake til implementer).
→ Rapport med 0 BLOKKERENDE + 0 VIKTIG (kun MINDRE / ingen funn): verdict = "go", revise-gate trigges ikke → merge.
```

`verdict` alene er ikke revise-gaten. Koordinatorens §5b-gate leser severity-arrayet direkte og sender tilbake til implementer ved ≥1 BLOKKERENDE **eller** ≥1 VIKTIG. MINDRE-funn blokkerer verken `verdict` eller revise-gaten.

## Verifikasjons-rapport (verifikator-arm → code-reviewer → koordinator)

Gjelder prosjekter som har konfigurert en verifikator-arm i `tech_review_agents`. Rapporten dømmer
**falsifiserbarhet** — kan vaktene i diffen i det hele tatt gå røde? — ikke design.

```json
{
  "report_type": "verification",
  "todo_nr": "41", "branch": "…", "base_sha": "…", "head_sha": "…",
  "sources_used": ["git diff <base_sha>...origin/<branch>", "grep -rn …", "<test-runner> …"],
  "v1": {
    "status": "kjørt|ikke utløst|ikke kjørt (<grunn>)",
    "guards": [{
      "guard": "<fil>::<testnavn ordrett>",
      "claim": "<vaktens EGEN påstand, sitert>",
      "site_inventory": { "command": "grep -rn \"<Symbol\" --include=*.tsx app components",
                          "count": 4, "raw": "<rå output, maks 40 linjer>" }
    }],
    "pairs": [{
      "guard": "…", "site": "…",
      "verdict": "RØD-BEVIST|UBEVISBAR|IKKE DEKKET",
      "guarded_code_in_pr_diff": true,
      "claim_reads": "<ordrett uttrykk vakten leser, sitert fra vaktfila>",
      "drift_category": "verdi|eksistens|struktur|geometri",
      "mutation": {
        "class": "revert-hunk|flip-branch|flip-operator|swap-literal|swap-argument|drop-step",
        "pre": "…", "post": "…", "diff": "<git diff -U0, nøyaktig én hunk>", "new_names": []
      },
      "red": ["<testnavn ORDRETT fra runneren>"], "green_siblings": ["…"],
      "restored_green": true, "reason": null, "narrowing_proposal": null
    }],
    "pairs_total": 0, "pairs_proven": 0, "unprovable": 0, "not_covered": 0,
    "worktree_clean": true, "mutations_run": 0, "test_invocations": 0, "elapsed_ms": 0
  },
  "v2": {
    "status": "kjørt|ikke utløst (utenfor registryet)|ikke kjørt (V1 blokkerte)|ikke kjørt (<grunn>)",
    "exit_code": 0, "runs": 1,
    "new_red": [], "known_red_missing": [], "vacuous": [],
    "coverage": { "changed_ui_files": [], "reachable_from_surfaces": [], "unreachable": [] }
  },
  "findings": [{ "severity": "BLOKKERENDE|VIKTIG|MINDRE", "ref": "<fil:linje>", "issue": "…", "fix": "…" }],
  "coordinator_actions": [{ "kind": "cap_hit|arm_uteble|feil_worktree|prompt_brudd",
                            "detail": "…", "action": "re-dispatch armen for par 21–27" }],
  "notes": "…"
}
```

- **Enheten er (vakt × beskyttet kallsted)**, ikke (vakt). En vakt er trivielt falsifiserbar per
  vakt; hullet er først synlig per kallsted.
- `pairs_proven + unprovable + not_covered` MÅ være lik `pairs_total`, og `pairs_total` MÅ være
  forankret i `site_inventory` — ellers er tellingen sirkulær (agenten utleder da både telleren og
  det som telles).
- `verdict: "UBEVISBAR"` krever både `reason` (MÅLT, ikke antatt) og `narrowing_proposal`. Slike
  par skrives ALDRI som ✅ — de får ⚪, og severity er VIKTIG (§5b-revise-gaten fyrer).
- `findings[]` folder kode-revieweren inn i `code_review.findings[]`.
  **`coordinator_actions[]` gjør den IKKE** — de er ikke implementer-handlbare, gjengis i `notes`
  bak `KOORDINATOR-HANDLING:`, og utføres av koordinatoren før §6.
- Hele rapporten bæres ordrett videre i `code_review.tech_arm_reports[]`. Koordinatoren kjører
  mekaniske sjekker på feltene — se runbokens §5b.
- `sources_used[]` er **selvrapportert** og beviser ikke fravær av lesing. Den reelle garantien er
  at prompten ikke inneholdt PR-referansen, og at hvert kallsted er re-utledbart via den siterte
  `site_inventory.command`-en.

## Ferdig-rapport (implementer → koordinator)

```json
{
  "report_type": "done",
  "todo_nr": "41",
  "slug": "redirect-after-login-next-flyt",
  "branch": "feat/todo-41-redirect-after-login-next-flyt",
  "pr_url": "<gh pr-url mot {{BASE_BRANCH}}>",
  "status": "implemented",
  "verification": {
    "build_green": true, "type_check_green": true, "tests_passed": true,
    "playwright_available": true, "e2e_skipped": false,
    "security_findings": [], "review_findings": [],
    "tdd": { "required_steps": 1,
             "pairs": [{ "step": "Steg 3", "red_commit": "<sha>", "test": "<fil> :: <testnavn>",
                        "failure": "<ordrett feillinje>", "green_commit": "<sha>" }],
             "deviations": [{ "step": "Steg 5", "reason": "<målt grunn>" }] }
  },
  "lessons": [
    { "topic": "workflow-process", "pattern": "…", "checklist": "…", "sources": "TODO 41" }
  ],
  "bugs_closed": [],
  "bugs_new": [],
  "deviations": "ingen",
  "notes": "Fritekst til koordinatoren."
}
```

- `status` ∈ `"implemented"|"blocked"|"failed"`.
- `topic` MÅ være ett av: {{LESSONS_TOPICS}}.
- `security_findings`/`review_findings`: kun KRITISK/HØY/Important som IKKE ble fikset (tom = alt fikset).
- `playwright_available`: `true` hvis e2e-verktøyet var tilgjengelig under verifisering; `false` hvis det manglet.
- `e2e_skipped`: `true` hvis E2E ble hoppet over (pga. manglende e2e-verktøy eller eksplisitt beslutning); `false` hvis E2E ble kjørt. Koordinatoren mapper disse to feltene til `degradation`-kolonnen i run-log: `e2e_skipped=true` → `e2e_skipped`; ellers `-` (for dette feltet).
- `verification.tdd`: `required_steps` = antall `TDD-STEG` i planen (ikke implementerens eget
  skjønn), og `deviations[]` = merkede steg uten rødt-par, med målt grunn — tomt felt betyr «ingen»,
  manglende felt betyr «ikke gjort». Ingen `TDD-STEG` i planen ⇒
  `{"required_steps": 0, "pairs": [], "deviations": []}` — fravær skal være skrevet, ikke utledet av
  stillhet. Hele `verification.tdd`-blokken limes ordrett inn i PR-bodyen (feltet er ellers
  skrive-bare — ingen leser ferdig-rapporten i §5b-dispatchen).
- Implementeren skriver `lessons`/`bugs_*` som DATA. Den skriver ALDRI til `tasks/lessons*`, `tasks/bugs.md` eller `tasks/todo_archive.md`, og rører ikke todo-frontmatteren — det gjør koordinatoren.
