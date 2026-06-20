# Oppstart-prompt — fersk TindraFit-sesjon

Lim teksten under inn som første melding i den nye sesjonen (tindrafit som
hovedrepo, claudecode lagt til som referanse).

---

```text
Dette er oppstart av TindraFit — et auto-oppdatert treningsdashboard.
Hovedrepo er tindrafit. Jeg har også lagt til repoet `claudecode` som
referanse — der ligger hele prosjektplanen og en arbeidsprosess-mal.

STEG 0 — PRECHECK (kjør aller først, før alt annet):
Verifiser at nødvendige MCP-servere er tilgjengelige OG autentisert. Rapporter
en kort status-tabell (OK / mangler) for hver. Hvis noe mangler eller feiler:
STOPP og si fra til meg før du går videre — ikke prøv å jobbe rundt det.
- Chirona (Garmin): kall mcp__Chirona__conversation-initialisation-critical-
  instructions, deretter mcp__Chirona__get-connected-data-sources. Bekreft at
  Garmin (og ev. Hevy) faktisk er tilkoblet — ikke bare at serveren svarer.
- Strava: kall mcp__Strava__health og mcp__Strava__get_athlete_profile
  (bekrefter at OAuth faktisk virker, ikke bare at verktøyet finnes).
- Supabase: kall mcp__Supabase__list_projects (bekreft at TindraFit-prosjektet
  er synlig).
- Vercel: kall mcp__Vercel__list_projects (bekreft TindraFit-prosjektet).
- GitHub: bekreft tilgang til tindrafit-repoet.
Hvis Chirona eller Strava mangler: påpek at datakvalitets-auditen (Fase 0.5)
ikke kan kjøres før de er på plass, og spør meg om jeg vil koble dem til først.

STEG 1–3 — LES OG OPPSUMMER (ikke kod ennå):
1. Les alle dokumentene i claudecode: projectideas/tindrafit/
   (README, kickoff, beslutninger, datakilder, datamodell, arkitektur,
   dashboard, assistent, faseplan, apne-sporsmal).
2. Les claudecode sin arbeidsprosess-mal: CLAUDE.md, docs/workflow.md,
   docs/naming-conventions.md, tasks/ (lessons, todo) og .claude/agents/.
3. Oppsummer tilbake til meg: prosjektets mål, de låste beslutningene
   (særlig separert utholdenhet/styrke + readiness, Garmin/Chirona primær med
   Strava i tre roller, TRIMP), og hva som gjenstår å avklare.

DERETTER, presenter en plan for to spor (vent på min bekreftelse før koding):

SPOR B — v2 arbeidsprosess (gjør FØRST):
- Sett opp arbeidsprosess-rammeverket friskt i tindrafit, basert på malen i
  claudecode: CLAUDE.md (ekte TindraFit-verdier, ingen placeholders),
  docs/naming-conventions.md, docs/workflow.md, tasks/todo.md + tasks/lessons/,
  og relevante agenter.
- Spør meg hva «v2» konkret skal forbedre fra v1 (token-budsjett-regler,
  lessons-struktur, egne TindraFit-agenter) — ikke gjett.

SPOR A — scaffolde appen (følg faseplan.md):
- Fase 0/0.5 først: koble repo + Supabase + Vercel, og kjør DATAKVALITETS-
  AUDITEN i Fase 0.5: les gjennom et representativt utvalg ekte økter via
  Chirona/Garmin og verifiser HR-streams, maxHR/soner, søvn/HRV-dekning,
  tidssoner, dubletter, og om Garmins Training Load/Readiness overlever Terra-
  normaliseringen. Skriv en kort kvalitetsrapport og oppdater datakilder.md/
  beslutninger.md ut fra funnene. Dette avgjør om Strava må hentes fra dag én.
- Bygg deretter Fase 1 (skjema + skall) → Fase 2 (innhenting) → Fase 3 (analyse).

PRINSIPPER (fra beslutninger.md):
- Utholdenhet og styrke holdes adskilt — ingen felles lastenhet. Forening kun
  på readiness-laget (HRV/søvn/puls/følelse).
- Kildene bak ett provider-grensesnitt (Garmin/Chirona primær; Strava
  fallback + frittstående + berikelse for gear/segmenter).
- Svar alltid på norsk. Enkelhet først, kirurgiske endringer, spør ved tvil.

Start med STEG 0 (precheck) nå.
```
