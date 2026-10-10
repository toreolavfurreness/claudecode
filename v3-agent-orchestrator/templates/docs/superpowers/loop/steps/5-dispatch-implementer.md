<!--
  GENERERT av /setup fra loop.config.yaml — IKKE rediger her.
  Endre loop.config.yaml og kjør /setup på nytt.
-->

# 5. Dispatch implementer

→ Kjerne: `coordinator-runbook.md` § 5 · Begrunnelser: `runbook-hvorfor.md` § 5

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

<!-- mekanisk-kandidat: pre-dispatch snapshot — hook som skriver git worktree list --porcelain før hver isolation: worktree-dispatch (mangler) -->

Sjekk exit-koden med det samme; ikke-null ⇒ noter paret som `snapshot-missing`.

Noter `F3a_ref` = F3a-kommandoen (gate F, §5b) kjørt mot planfila du nå dispatcher; bær tallet i
kontekst sammen med `<N>`-telleren.

`Agent`: `subagent_type: {{PROJECT_NAME}}-implementer`, **`model: "{{IMPLEMENTER_MODEL_ALIAS}}"` (alltid eksplisitt — håndhevet av `.claude/hooks/guard-fix-round-model.sh`; frontmatter alene holder ikke, et utdatert sesjons-snapshot kan kjøre en annen modell)**. Prompt:
> TODO <nr>. Plan: `<plan_path>`. Relevante lessons-tema: <liste>.
> **Plan-review-funn å innarbeide (verdict=go, ikke-blokkerende):** <severity + ref + issue + fix> (`ref` er her et **plansteg**, f.eks. «Steg 3» — ikke `file:line`, jf. `report-schema.md:51–53`).
> Følg charteret ditt. Returner ferdig-rapport som JSON.

**Utelatelsesregel:** funn-linjen utelates **helt** (ikke skrevet som «ingen funn») ved **fast-path** (§2b — §4 er da aldri kjørt) og ved `verdict: "go"` uten VIKTIG/MINDRE-funn.

`status: "failed"|"blocked"` → ⚠️ STOPP, release claim, rapporter.

`status: "plan_invalid"` → planen holdt ikke. Ikke en stopp-sti; claimet beholdes.
1. Sjekk at `notes` navngir den brustne antakelsen OG det målte funnet. Mangler ett av dem, be
   implementeren om det først — ellers bretter neste plan den samme antakelsen inn på nytt.
2. Sett `plan:` i todo-frontmatteren tilbake til tom, og kjør §3 → §4 → §5 på nytt. Lim funnet
   ORDRETT inn i den nye §3-dispatchen («planen antok X; implementeren målte Y»).
3. **Andre `plan_invalid` på SAMME todo ⇒ ⚠️ STOPP og eskalér** med begge funnene. To planer som
   begge brister betyr at todoen er feil skåret.
Rydd implementer-worktreen etter §0b som ved en vanlig rapport.

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
revise-gate som ender i A0 eller stopp, merge-konflikt eller sesjonsdød nås §6 ALDRI. Implementer-
worktreene **BEHOLDES** da bevisst — de kan bære ucommittet arbeid, og mennesket eskaleres til
uansett. Koordinatoren LISTER de akkumulerte stiene i pause-rapporten. Ryddes av mennesket, TODO
245 — aldri av loopen.
