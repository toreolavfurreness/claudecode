# Navnekonvensjoner — <PROSJEKTNAVN>

> Denne filen er obligatorisk lesning før enhver oppgave som oppretter
> eller endrer navngitte elementer (filer, komponenter, tabeller, ruter, brancher osv.).
>
> **Tilpass:** Erstatt eksempler i hver tabell med konvensjoner som passer prosjektets stack.
> Slett seksjoner som ikke gjelder (f.eks. "Ruter" hvis prosjektet ikke har frontend-ruter).

---

## 1. Overordnet prinsipp

- All kode, filnavn og databaseobjekter er på **engelsk**
- All UI-tekst (det brukeren ser) er på **brukerens språk** (f.eks. norsk)
- Dette skillet er absolutt og skal aldri brytes uten eksplisitt bekreftelse

> Dersom prosjektet ikke har UI: konvensjonen forenkles til "alt på engelsk".

---

## 2. Filnavn

| Type | Konvensjon | Eksempler |
|------|-----------|-----------|
| Komponenter / klasser | PascalCase | `<eksempel>` |
| Funksjoner / hjelpere | camelCase eller snake_case (velg én) | `<eksempel>` |
| Konstanter-filer | camelCase | `<eksempel>` |
| Typer (egen fil) | PascalCase med suffiks | `<eksempel>` |
| Tester | Samme navn som fil under test, med `.spec` / `.test` / `_test` | `<eksempel>` |

---

## 3. Ruter / endepunkter *(slett hvis ikke relevant)*

- Konvensjon: `<f.eks. kebab-case, engelsk>`
- Dynamiske parametere: `<f.eks. [id], :id>`
- Gruppering: `<f.eks. (auth), v1/>`

**Begrunnelse:** *(forklar valget kort — gjør det lett for fremtidige bidragsytere å vite hvorfor)*

---

## 4. Variabler og funksjoner

- camelCase eller snake_case — **velg én konvensjon for prosjektet og hold den**
- Ingen forkortelser med mindre de er allment kjent (`url`, `id`, `api` er OK; egendefinerte forkortelser er ikke OK)
- Beskrivende navn > korte navn

---

## 5. Komponenter / klasser *(tilpass til språk)*

- PascalCase
- Filnavnet matcher klassenavnet

---

## 6. Konstanter

- `SCREAMING_SNAKE_CASE` for virkelig uforanderlige verdier — f.eks. `MAX_RETRIES`, `DEFAULT_TIMEOUT_MS`
- camelCase for konstante objekter som brukes som konfigurasjon

---

## 7. Typer / interfaces *(slett hvis ikke typet språk)*

- PascalCase
- Ikke bruk `I`-prefiks på interfaces
- Typer for props/parametere: `<KlasseNavn>Props` eller tilsvarende

---

## 8. Booleans

- Prefikses med `is`, `has`, `should`, `can` — f.eks. `isLoading`, `hasError`, `shouldShowModal`, `canEdit`

---

## 9. Event handlers / callbacks *(slett hvis ikke relevant)*

- Prefikses med `handle` i implementasjonen, `on` i prop/parameter
- Eksempel: `handleSubmit` (intern), `onSubmit` (prop)

---

## 10. Database

| Element | Konvensjon | Eksempler |
|---------|-----------|-----------|
| Tabellnavn | snake_case, flertall, engelsk | `<eksempel>` |
| Kolonnenavn | snake_case, engelsk | `<eksempel>` |
| Primærnøkkel | `id` (UUID eller serial — velg) | |
| Foreign keys | `<tabell_i_entall>_id` | `user_id`, `order_id` |
| Timestamps | `created_at`, `updated_at` | |
| Boolean-kolonner | `is_*`, `has_*` | `is_completed` |
| Indekser | `idx_<tabell>_<kolonne(er)>` | `idx_users_email` |
| Unique constraints | `<tabell>_<kolonne>_unique` | |
| Tilgangsregler / RLS | Beskrivende engelsk setning, splitt per operasjon | |
| Enum-typer | snake_case med `_type` / `_status` | `order_status` |

---

## 11. Migrasjoner

- Filnavn: `<timestamp>_<beskrivelse_snake_case>.sql` (eller verktøyets standard)
- Beskrivelse er engelsk og imperativ — f.eks. `add_users_table`
- En logisk endring per migrasjon
- Splitt skjema-endringer og policy-endringer i separate migrasjoner

---

## 12. Eksterne tjenester *(slett seksjoner som ikke gjelder)*

### Functions / handlers
- Mappenavn / funksjonsnavn: kebab-case, engelsk — f.eks. `send-email`, `process-payment`
- Navnet skal være et verb eller en handling
- Inngangsfil: `index.<ext>`

### Storage / buckets
- Bucket-navn: kebab-case, engelsk — f.eks. `user-uploads`
- Filnavn i bucket: `<entitet_id>/<timestamp>-<slug>.<ext>`

### Queues / topics
- Navn: kebab-case, engelsk — f.eks. `order-events`

---

## 13. Env-variabler

- `SCREAMING_SNAKE_CASE`
- Klientside (eksponert i bygget): bruk verktøyets prefiks (f.eks. `NEXT_PUBLIC_`, `VITE_`, `EXPO_PUBLIC_`)
- Server / secrets: uten klient-prefiks
- Aldri lagre i kode — alltid i `.env` (lokalt) eller hosting-leverandørens secrets-store

---

## 14. Git

### Branches

| Type | Prefiks | Eksempel |
|------|---------|----------|
| Claude Code-arbeid | `claude/` | `claude/refactor-auth` |
| Nye funksjoner | `feature/` | `feature/import-data` |
| Bugfikser | `fix/` | `fix/bug-003-auth-header` |
| Dokumentasjon | `docs/` | `docs/cleanup-2026-04` |
| Release | `release/` | `release/2026-05-01` |

Alle branch-navn: kebab-case, engelsk.

### Commit-meldinger

Conventional Commits-stil — `<type>: <beskrivelse>`:

- `feat: add user export endpoint`
- `fix: correct timezone handling in scheduler`
- `docs: add naming conventions`
- `refactor: split auth module`

Imperativ form: "add", "fix", "remove" — ikke "added" eller "adding".

### PR-titler

Samme format som commit-meldinger.

---

## 15. Oppgavefiler

- Innhold på brukerens språk (beskrivelser, samtaler)
- Strukturelle prefikser på engelsk:
  - `TODO-<NNN>`: aktive oppgaver i `tasks/todo.md`
  - `BUG-<NNN>`: bugs i `tasks/bugs.md`
  - `FEAT-<NNN>`: backlog-funksjoner i `tasks/backlog.md`
- Numrene er fortløpende og gjenbrukes ikke

---

## 16. Tester

- Testfiler: konvensjon for prosjektets språk (`.spec.ts`, `_test.go`, `test_*.py`)
- Test-IDer i UI-komponenter: `<f.eks. kebab-case, engelsk>` — f.eks. `data-testid="submit-button"`
- Beskrivelser i `describe`/`it` (eller tilsvarende): engelsk, naturlig språk

---

## 17. UI-tekst *(slett hvis ikke UI)*

- Alltid på brukerens språk
- Gjelder: knappetekst, overskrifter, tomtilstander, feilmeldinger, modaler, varsler, placeholder-tekst

Eksempel:

```
// Filnavn og variabler: engelsk
<Button onPress={handleSubmit}>
  // UI-tekst: brukerens språk
  <Text>Send inn</Text>
</Button>
```

---

## 18. Unntak og avvik

Avvik fra disse konvensjonene skal kun skje etter eksplisitt bekreftelse fra prosjekteier.

Eventuelle avvik dokumenteres i denne seksjonen med:
- Hva avviket er
- Hvorfor det er gjort
- Dato

*(Tom ved start. Append nye avvik under denne linjen.)*
