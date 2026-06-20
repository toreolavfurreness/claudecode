# Kickoff — første sesjon i TindraFit-repoet

> Kjøreplan for sesjonen som starter med **tindrafit** som hovedrepo og
> **claudecode** lagt til som referanse. To spor parallelt:
> **(A) scaffolde appen** og **(B) sette opp v2 av arbeidsprosessen.**

## Forutsetning
- Hovedrepo: `tindrafit` (GitHub-repo, Supabase- og Vercel-prosjekt opprettet).
- Referanse: `claudecode` lagt til sesjonen — herfra hentes plan + prosessmal.
- Les først: `projectideas/tindrafit/` (README, datamodell, datakilder,
  arkitektur, dashboard, assistent, faseplan, **beslutninger**).

## Spor A — Scaffolde appen (følg faseplan.md)
1. **Fase 0:** kopier plandokumentene inn i tindrafit som `docs/`-grunnlag.
2. **Fase 1:** Supabase-skjema fra `datamodell.md`.
   - Husk: `athletes.max_hr` + `athletes.hvilepuls_baseline` (TRIMP avhenger av dem).
   - RLS på `athlete_id` fra start.
3. Next.js-skall + PWA på Vercel, Supabase Auth.
4. Deretter Fase 2 (innhenting) → Fase 3 (analyse) → Fase 4 (assistent).

## Spor B — v2 arbeidsprosess (overført fra claudecode)
Ta med rammeverket og forbedre det. Komponenter å gjenskape i tindrafit:
- `CLAUDE.md` — fyll inn ekte TindraFit-verdier (ingen `<PLACEHOLDER>` igjen).
- `docs/`: `workflow.md`, `naming-conventions.md`, `architecture.md`,
  `data-model.md`, `design-system.md`.
- `tasks/`: `todo.md`, `backlog.md`, `bugs.md`, `lessons/` (index, log + temaer),
  `plans/`, `sessions/`.
- `.claude/agents/`: `reviewer`, `plan-reviewer`, `lessons-writer`.
- Slash-kommando-filer: `start`, `todo-plan`, `todo-execute`, `todo-done`,
  `endsession`, `status`.

### v2-forbedringer — AVKLAR I NY SESJON (ikke gjett)
Disse er kandidater, ikke besluttet. Brukeren bør velge:
- Skal lessons-wikien beholdes som-er, eller forenkles?
- Token-budsjett-reglene fra v1 CLAUDE.md — behold, justere, fjerne?
- Egne agenter for TindraFit (f.eks. «data-sync-reviewer», «trenings-domene»)?
- Skal `naming-conventions.md` utvides med DB-/MCP-spesifikke regler?

## Rekkefølge-anbefaling
Gjør **Spor B først** (CLAUDE.md + naming-conventions + todo), slik at appbygging
i Spor A skjer under et ferdig prosessrammeverk — ikke omvendt.

## Viktige beslutninger som allerede er låst (se beslutninger.md)
- TRIMP som belastningsbase (beregnes, ikke hentes — se datakilder.md).
- Hevy via Chirona for ekte styrkevolum senere.
- Generell form som sesongmål. Recharts, Vercel Cron, RLS, aggregat-only til AI.
