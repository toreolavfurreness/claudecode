# Rapport-skjema

Rapportene binder koordinator og workers sammen. In-session roller (planner, reviewer,
code-reviewer) returnerer rapporten som SISTE melding i `task`-kallet. Barnesesjon-roller
(implementer, verifier) sender rapporten til koordinator-sesjonen med `send_session_message`
når de er ferdig eller blokkert — koordinatoren mottar den som en cross-session-melding.

I begge tilfeller: rapporten er ETT JSON-objekt, ingen prosa rundt.

## Plan-rapport (planner → koordinator)

```json
{
  "report_type": "plan",
  "todo_nr": "41",
  "slug": "redirect-after-login-next-flyt",
  "branch_suggestion": "feat/todo-41-redirect-after-login-next-flyt",
  "plan_body": "## Analyse\n...\n## Filer som berøres\n...\n## Steg\n- [ ] Steg 1: ...",
  "summary": "Kort sammendrag av valgt tilnærming (1-3 setninger).",
  "files_touched": ["src/proxy.ts", "src/app/login/page.tsx"],
  "technical_risk": { "flagged": false, "kind": null, "detail": null },
  "deps_ok": true,
  "verification_criteria": ["Uinnlogget bruker på dyp lenke → /login?next=<url>"],
  "canary": "<eksakt tekst fra fil+linje koordinatoren oppga>",
  "canary_line": "<linjenummeret faktisk lest>",
  "status": "reviewed",
  "notes": "Forbehold eller funn."
}
```

- `plan_body`: selve plan-teksten. **Koordinatoren** (eneste skriver til delt state) skriver
  dette til `tasks/plans/todo-<nr>-<slug>.md` — planneren skriver ALDRI filen selv (avvik fra
  kilden, se `docs/PORTING-DECISIONS.md` §2).
- `technical_risk.flagged`: `true` hvis planen krever noe under pause-triggerne.
- `deps_ok: false` → `status: "blocked"`.
- `canary`/`canary_line`: bevis på fil-lesing (koordinatoren oppgir et mål ikke gjentatt i
  prompten). Mismatch = lesing sannsynligvis hoppet over.

## Review-rapport (reviewer → koordinator)

```json
{
  "report_type": "review",
  "todo_nr": "41",
  "findings": [
    { "severity": "BLOKKERENDE", "ref": "Steg 3", "issue": "…", "fix": "…" },
    { "severity": "VIKTIG", "ref": "Steg 5", "issue": "…", "fix": "…" },
    { "severity": "MINDRE", "ref": "Generelt", "issue": "…", "fix": "…" }
  ],
  "verdict": "no-go",
  "notes": "Samlet vurdering."
}
```

`severity` ∈ `BLOKKERENDE|VIKTIG|MINDRE`. `verdict` ∈ `go` (ingen BLOKKERENDE) | `no-go`
(≥1 BLOKKERENDE → koordinator sender tilbake til planner, maks 2 runder).

## Ferdig-rapport (implementer → koordinator, via send_session_message)

```json
{
  "report_type": "done",
  "todo_nr": "41",
  "session_id": "<barnesesjonens id>",
  "branch": "feat/todo-41-redirect-after-login-next-flyt",
  "pr_url": "https://github.com/{{GITHUB_REPO}}/pull/42",
  "verification": {
    "build": "green",
    "type_check": "green",
    "test": "green (24 passed | 0 skipped)",
    "playwright_available": false,
    "e2e_skipped": true,
    "review_findings": [],
    "security_findings": [],
    "tdd": { "required_steps": 0, "pairs": [], "deviations": [] }
  },
  "status": "done",
  "lessons": [
    { "topic": "database", "problem": "…", "solution": "…", "avoid": "…" }
  ],
  "notes": "Forbehold."
}
```

- `status` ∈ `done|blocked`. `blocked` = todoen traff en pause-trigger — koordinatoren
  eskalerer til mennesket, arkiverer IKKE sesjonen automatisk før eieren har sett den.
  Eksakt testtall alltid, aldri estimat/avrunding.
- `lessons[]`: DATA, ikke en fil-skriving. Koordinatoren dispatcher selv (eller skriver selv)
  til `tasks/lessons/<topic>.md` + `index.md` + `log.md` basert på dette feltet — implementeren
  skriver aldri disse filene selv (single-writer-disiplin, se rolle-instruksjonen).

## Kode-review-rapport (code-reviewer → koordinator)

```json
{
  "report_type": "code_review",
  "todo_nr": "41",
  "pr_url": "https://github.com/{{GITHUB_REPO}}/pull/42",
  "findings": [
    { "severity": "BLOKKERENDE", "ref": "src/app/login/page.tsx:42", "issue": "…", "fix": "…" }
  ],
  "tech_arm_reports": [
    { "arm": "security-reviewer", "status": "ikke utløst", "report": null }
  ],
  "verdict": "no-go",
  "notes": "Samlet vurdering."
}
```

`tech_arm_reports[]`: én post per konfigurert tech-arm, `status` ∈
`kjørt|ikke utløst|uteble|ikke lastet`. `report: null` for alt annet enn `kjørt`.

## Verification-rapport (verifier → koordinator, via send_session_message — kun hvis tech-arm konfigurert)

```json
{
  "report_type": "verification",
  "todo_nr": "41",
  "guard_checks": [
    { "guard": "safe-next redirect validation", "call_site": "src/lib/auth/safe-next.ts:17",
      "mutation": "invertert if-betingelse", "outcome": "red", "conclusion": "falsifiserbar" }
  ],
  "status": "kjørt",
  "notes": "Samlet vurdering av falsifiserbarhet."
}
```
