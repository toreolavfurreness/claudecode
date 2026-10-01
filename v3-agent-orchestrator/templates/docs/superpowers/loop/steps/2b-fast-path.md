<!--
  GENERERT av /setup fra loop.config.yaml — IKKE rediger her.
  Endre loop.config.yaml og kjør /setup på nytt.
-->

# 2b. Fast-path (hopp §3/§4 → rett til §5)

→ Kjerne: `coordinator-runbook.md` § 2b · Begrunnelser: `runbook-hvorfor.md` § 2b

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
