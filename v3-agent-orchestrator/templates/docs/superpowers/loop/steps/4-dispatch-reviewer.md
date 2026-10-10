<!--
  GENERERT av /setup fra loop.config.yaml — IKKE rediger her.
  Endre loop.config.yaml og kjør /setup på nytt.
-->

# 4. Dispatch reviewer + gate

→ Kjerne: `coordinator-runbook.md` § 4 · Begrunnelser: `runbook-hvorfor.md` § 4

**Plan-lint FØR dispatch (N1, BINDENDE):**
```bash
python3 tasks/vblock-lint.py tasks/plans/todo-<nr>-<slug>.md --log
```
Exit 1 (HARD, i dag bare R0: mangler `## Steg` med avkrysningsbokser) ⇒ send planen tilbake til
planneren med lint-outputen, uten å dispatche revieweren. Det teller ikke som en §4-runde. Exit 0 ⇒
fortsett; SOFT-funn blokkerer ikke. Exit 2 ⇒ planfila mangler eller kan ikke leses: STOPP.
`--log` skriver raden §8c leser i `tasks/metrics/vblock-lint-log.jsonl`.

**Proporsjonalitet FØR dispatch (BINDENDE):** sammenlign plan-rapportens `planned_diff`
(linjer og filer) med budsjettet du satte i §3-dispatchen. Er linjene eller filene mer enn ~5×
budsjettet ⇒ ⚠️ pausepunkt: legg fram anslag, budsjett og plan for mennesket FØR review-rundene.
Review gjør en for stor plan grundigere, ikke mindre. Logg `pause_event=proporsjon`.

**Pre-dispatch-snapshot (§0b vakt 5, R21) — umiddelbart FØR `Agent`-blokken under. Én fil per
revisjonsrunde:**
```bash
git worktree list --porcelain > "<scratch>/wt-pre-4-plan-reviewer-<runde>.txt"
```

<!-- mekanisk-kandidat: pre-dispatch snapshot — hook som skriver git worktree list --porcelain før hver isolation: worktree-dispatch (mangler) -->

Sjekk exit-koden med det samme; ikke-null ⇒ noter paret som `snapshot-missing` (samme regel som §3).

`Agent`: `subagent_type: {{PROJECT_NAME}}-reviewer`. Prompt:
> TODO <nr>. Plan: `<plan_path>`. Relevante lessons-tema: <liste>. Følg charteret ditt. Returner review-rapport som JSON.

**Bevis-sjekk (`evidence`):** match `evidence.reviewed_head` (PRIMÆR) mot SIN EGEN kopi av planfilen — den samme planfilen du dispatchet revieweren mot. Mismatch → revieweren leste sannsynligvis feil eller utdatert plan — re-dispatch eller eskalér. `evidence.toplevel` er SVAKT/sekundært for reviewer (beviser kun cwd, ikke at riktig artefakt ble lest — reviewer skriver ingenting).

**Rydding av plan-reviewerens worktree:** koordinatoren akkumulerer **paret**
(`evidence.toplevel`, rundens `<scratch>/wt-pre-4-plan-reviewer-<runde>.txt`) fra HVER §4-runde og
kaller §0b én gang per deduplisert sti — dedupliser på STIEN og behold den FØRSTE rundens
snapshot-fil for stien (samme regel som §6 steg 4(i)) — i `go`-grenen, i
`technical_risk`-grenen og ved TERMINERING av revisjons-løkka (A0 fra konvergensregelen).
**ALDRI i no-go-grenen** som sender funnene tilbake til planneren: reviewer-agenten skal leve
videre gjennom revisjonsrunden (kontinuitet). Eies av rydde-kontrakten — utvid
DENNE regelen, ikke legg til en ny. **Hvorfor paret og ikke bare stien (R21):**
runde 2s snapshot inneholder runde 1s worktree, så et felles snapshot ville avvist runde 1s sti som
`preexisting` og gjort vakt 5 til en permanent blokkering nettopp i akkumulerings-tilfellet.
**Akkumuleringen er per DISPATCH-FORSØK, ikke per runde:** en re-dispatch etter bevis-mismatch
(`evidence.reviewed_head`) legger den forkastede revieweren sitt `evidence.toplevel` inn i lista med
SITT eget pre-snapshot, og §0b kalles for den også — ikke bare for dispatch-forsøket som til slutt
gir `go`/`no-go`.

**Konsolideringsgate (før planner-revisjonen) — OBLIGATORISK.** En review-runde legger til lag og
fjerner ingen, så en plan som revideres flere ganger degraderer monotont uten et motgrep.

1. **Terskel:** mål `wc -l <plan_path>` FØR planner-revisjonen dispatches, og PÅ NYTT når den
   reviderte planen kommer tilbake. **≥ 400 linjer OG minst én tidligere runde ⇒ konsolider** før
   neste dispatch. «Tidligere runde» er mekanisk: §4-telleren > 0 ELLER
   `git log --oneline -- <plan_path>` viser ≥ 2 commits (overteller heller enn underteller —
   riktig feilretning for en gate). Et førsteutkast har ingen lag å konsolidere.
2. **Hva konsolidering ER:** skriv planen om til gjeldende sannhet — én versjon av hver påstand,
   ingen «r1 sa X, r2 rettet til Y». Behold begrunnelser som bærer implementeringen, og hvert
   bevisst avvist funn som én linje («**Vurdert og forkastet**: X — fordi Y»); strykes avvisningen,
   reiser neste reviewer funnet på nytt. Øvrig review-historikk strykes (run-log og PR-body bærer
   den).
3. **Hva den IKKE er:** ingen ny beslutning, ingen scope-endring, ingen ny planner-dispatch.
   Koordinatoren konsoliderer selv, eller gir omskrivingen til en fersk sub-agent MED
   funn-inventaret (K1) — ansvaret for K1–K3 er koordinatorens. Konsolideringen er ikke en
   revisjonsrunde og teller ikke mot 2-runders-grensen.
4. **Verifisering:**
   - **K1 — funn-inventar FØR omskriving:** hvert review-funn fra ALLE runder (review-rapportenes
     `findings[]` + `git log --format='%s%n%b' -- <plan_path>`), merket `innfoldet` eller
     `bevisst avvist`.
   - **K2 — gjenfinn hvert K1-funn i den NYE teksten** (innfoldet i planteksten, avvist som sin
     «Vurdert og forkastet»-linje). Et funn som ikke gjenfinnes er tapt — da er konsolideringen ikke
     ferdig.
   - **K3 — lengde:** skriv `wc -l` før/etter i commit-meldingen. En konsolidering som gjør fila
     lengre er ikke en konsolidering — begrunn økningen eksplisitt.
5. **Utgangen:** velger du å revidere videre uten å konsolidere en plan over terskelen, skriv
   «konsolidering utsatt fordi …» i commit-meldingen. Stillhet er ikke en lovlig utgang.

Gate på `verdict`:
- `"no-go"` (≥1 BLOKKERENDE) → kjør **Konsolideringsgaten** over, og send så funnene tilbake til planner (§3, revisjons-runde) mot den (ev. konsoliderte) fila. **Hold en eksplisitt teller** («revisjonsrunde N») i kontekst. Ved HVER no-go, også runde 1: kjør `python3 tasks/measure-cost.py --brake <nr>` og så `decision-level.py` med `cost_over=<over>`, fra runde 2 også med konvergensdata (se `coordinator-runbook.md` § Konvergensregel). B7 → ny revisjonsrunde. A0 → ⚠️ eskalér til mennesket, release claim.


```bash
python3 tasks/decision-level.py --event plan_review_choice --context plan_review_rounds=1 --context action=revise --context cost_over=no
python3 tasks/decision-level.py --event plan_review_choice --context plan_review_rounds=2 --context action=revise --context blocking_prev=2 --context blocking_now=1 --context new_class=no --context content=no --context cost_over=no
```

- `"go"` → fortsett; VIKTIG/MINDRE-funn (ikke-blokkerende) bæres videre til §5-dispatchen.
  **Re-mål `effort` her (BINDENDE).** Et `go` betyr at oppgaven er kjent: skriv den målte
  størrelsen inn i todoens `effort` på den sammensatte formen `<kode>/<verifisering>`
  (`tasks/todos/README.md`), og behold det opprinnelige anslaget i brødteksten («opprettet som
  `S`»). Kilden er plan-rapporten — planneren skal oppgi begge halvdelene, og revieweren har
  allerede etterprøvd tallene planen kaller målt. Gjør det ALDRI i `no-go`-grenen: da er
  størrelsen nettopp det som ikke er avklart. Avviker den målte størrelsen fra anslaget med mer
  enn ett hakk i noen av halvdelene, skriv én linje om det i decision-log — det er
  kalibreringsdata, ikke støy.

Ved `technical_risk.flagged` (plan- eller review-rapport) → ⚠️ STOPP, release claim, rapporter risikoen, vent på menneskets go — **med mindre** `python3 tasks/decision-level.py --event technical_risk --context source=planner --context kind=<kind> --context executable_gate=<yes|no>` klassifiserer hendelsen som **nivå B5** (KUN plan-rapportens `technical_risk`, `kind ∈ {docs_selfmod, hook_selfmod}` og `executable_gate = true`; se § Pausepunkter under). En `technical_risk` flagget av REVIEWEREN er alltid nivå A, uansett innhold — reviewer-rapporten bærer ikke `kind`/`executable_gate` (`report-schema.md`).

> **Pipelinet B?** «Release claim» gjelder ALLTID den claimede todoen. Er dette en pipelinet,
> u-claimet B (§5c), har den ingen claim å frigi — B droppes ut av pipelinen og A fortsetter
> uendret. Se §5c, «Pausepunkt-samspill: B-sporet pauser mens A er sunn».
