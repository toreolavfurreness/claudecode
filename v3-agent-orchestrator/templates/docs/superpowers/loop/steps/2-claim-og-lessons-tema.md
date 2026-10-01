<!--
  GENERERT av /setup fra loop.config.yaml — IKKE rediger her.
  Endre loop.config.yaml og kjør /setup på nytt.
-->

# 2. Claim + pre-løs lessons-tema

→ Kjerne: `coordinator-runbook.md` § 2 · Begrunnelser: `runbook-hvorfor.md` § 2

Sett `claimed_by: <din-sesjon>` i todo-fila.

**Pipelinet plan? Hopp §3/§4.** Er `plan:` satt på todoen OG planfila bærer en `**Status:**`-linje
som starter med `pipelinet` — se §5c, «Gjenopptakelse i §2»: §3 og §4 er allerede kjørt i en
tidligere runde og hoppes, etter ferskhets-gaten i §5c. Dette er **IKKE** fast-path (§2b):
`models` skal bære de faktiske planner-/reviewer-modellene fra markørlinja og `plan_review_rounds`
det faktiske tallet — aldri `skipped`/`0`.

**Graf-oppslag (før du velger tema):**
```bash
python3 tasks/graph-query.py --todo <nr>
python3 tasks/graph-query.py --file <sti>     # for hver fil todoen navngir
```
Gir todoens `deps`/`bugs`/`files`/`pr`, hvilke bugs som er **triagert til** den (og hvilke som bare
**omtaler** den), hvilke lessons som nevner den, og — per fil — hvilke todos som har rørt den,
hvilke bugs som bor der, og hvilke lessons som peker dit. Bruk `Foreslåtte lessons-tema`-linja i
outputen som **utgangspunkt** for tema-valget, ikke som fasit.

Grafen bygges on-demand (under ett sekund), skrives til stdout og **lagres aldri**. Det finnes ingen
`tasks/graph.json` å holde fersk — dukker en slik fil opp lokalt, er den et feilsøkings-artefakt
fra `--out` og skal ikke committes.

Gir grafen ingen treff **eller feiler kommandoen** (traceback, ikke-null exit) — fortsett med
`grep tasks/lessons.md`. **Dette steget skal aldri stoppe en runde.**

Velg 1–3 tema relevant for todoens domene ut fra scope-katalogen i `tasks/lessons.md` (gyldige tema: `ls tasks/lessons/`).

**Claim-release:** I ENHVER stopp-sti senere (teknisk risiko, blocked, failed, merge-konflikt) → sett `claimed_by: null` tilbake før du stopper, så todoen ikke lekker ut av køen.
