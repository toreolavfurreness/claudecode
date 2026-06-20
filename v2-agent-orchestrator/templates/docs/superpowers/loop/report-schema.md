<!--
  GENERERT av /setup fra loop.config.yaml — IKKE rediger her.
  Endre loop.config.yaml og kjør /setup på nytt.
-->

# Loop-rapport-skjema

Tre rapporter binder koordinator og workers sammen. Hver returneres som ETT JSON-objekt i workerens siste melding (sluttmeldingen ER returverdien — ingen prosa rundt).

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
  "status": "reviewed",
  "notes": "Forbehold eller funn."
}
```

- `technical_risk.flagged`: `true` hvis planen krever noe under pause-triggerne. `kind` ∈ `"migration"|"rls"|"prod_push"|"secrets"` (tilpass til prosjektets pause-triggere).
- `deps_ok`: `false` → `status: "blocked"`.
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
  "verdict": "no-go",
  "notes": "Samlet vurdering av diffen."
}
```

- `findings[]`-objektet har **identisk shape** som plan-review-rapportens `findings[]` (`severity`/`ref`/`issue`/`fix`); for kode-review er `ref` = `file:line`. Ingen omdøping av feltene.
- `severity` ∈ `"BLOKKERENDE"|"VIKTIG"|"MINDRE"`. Severity-mapping fra tech-review-agenter er definert per agent i `loop.config` (`tech_review_agents[].severity_map`).
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
    "security_findings": [], "review_findings": []
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
- Implementeren skriver `lessons`/`bugs_*` som DATA. Den skriver ALDRI til `tasks/lessons*`, `tasks/bugs.md` eller `tasks/todo_archive.md`, og rører ikke todo-frontmatteren — det gjør koordinatoren.
