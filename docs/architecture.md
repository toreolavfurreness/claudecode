# Arkitektur

> Skjelett. Erstatt `<PLACEHOLDER>`-merker og fyll inn faktiske detaljer ved oppstart av prosjektet.

## Prosjektkontekst

`<En til tre setninger om hva prosjektet er, hvem som bruker det, og hvilket problem det løser.>`

## Tech stack

| Lag | Teknologi |
|-----|-----------|
| Frontend | `<f.eks. Next.js / SvelteKit / React Native / ingen>` |
| Backend | `<f.eks. Node + Hono / Go / Edge Functions / ingen>` |
| Database | `<f.eks. PostgreSQL / SQLite / ingen>` |
| Auth | `<f.eks. NextAuth / Supabase Auth / Clerk / egen>` |
| Hosting | `<f.eks. Vercel / Fly / egen Docker>` |
| Kildekode | `<git-url>` |
| CI/CD | `<f.eks. GitHub Actions / Vercel auto-deploy>` |

## Miljøer

`<Beskriv miljøskillet hvis prosjektet har flere. Hvis bare ett miljø — slett denne seksjonen.>`

| Miljø | Branch | Hva brukes det til | Database / ressurser |
|-------|--------|---------------------|----------------------|
| Production | `main` | `<f.eks. ekte brukere>` | `<ressurs-id>` |
| Preview / Dev | alle andre | `<f.eks. lokal utvikling, PR-previews>` | `<ressurs-id>` |

**Konsekvenser av miljøskillet** *(beskriv konkret, ikke generelt):*
- `<f.eks. migrasjoner testes mot dev først, deretter merges dev → main>`
- `<f.eks. secrets er separate per prosjekt>`
- `<f.eks. backup-strategi>`

> **Tips:** Dokumenter eksplisitt hvordan du bekrefter at du jobber mot riktig miljø før migrasjoner eller deploys. Dette er en av de vanligste kildene til datatap.

## Branching-modell

Se `## Branching-regler` i `CLAUDE.md`. Kort: feature-branches lages fra `<base-branch>`, alle PR-er har `<base-branch>` som base, `main` røres kun ved planlagte releaser.

## Mappestruktur

```
<beskriv prosjektets faktiske mappestruktur — kun nivåer som er meningsfulle>

/src eller /app             — `<beskrivelse>`
/components eller /modules  — `<beskrivelse>`
/lib eller /pkg             — `<beskrivelse>`
/docs                       — design-system.md, architecture.md, data-model.md, naming-conventions.md
/tasks                      — todo.md, lessons.md, bugs.md, backlog.md, plans/, sessions/
```

## Routing-konvensjoner *(slett hvis ikke relevant)*

`<Beskriv hvordan ruter er organisert — f.eks. file-based routing, manifest-based, e.l.>`

## Datalagringsarkitektur

Se [data-model.md](./data-model.md) for fullstendig skjema, tabelloversikt, relasjoner og tilgangsregler.

## Andre viktige arkitektur-beslutninger

`<Legg til seksjoner for ting som ikke er åpenbare fra koden — f.eks. caching-strategi,
kø-bruk, feature flags, AI-integrasjoner, eksterne API-er, tredjeparts SDK-er.
Hver seksjon: hva, hvorfor, hvor det er implementert.>`
