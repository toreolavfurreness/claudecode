# Karpathys "second brain" og lessons på tvers av prosjekter

> Research-rapport og analyse. Spørsmål: *Kan vi bygge Karpathys Obsidian
> second brain inn i hvordan vi håndterer lessons i v2 — og dermed få lessons
> på tvers av prosjekter, så vi slipper å gjøre samme feil på nytt i flere
> prosjekter?*
>
> Dato: 2026-06-21 · Status: research, ingen kodeendringer foreslått implementert ennå.
> Se **Addendum (2026-06-21)** nederst: `brain`-vaulten er besluttet/opprettet,
> og hvordan engineering-lessons passer inn som et tredje tre i `brain`.

---

## 0. TL;DR

1. **Vi har allerede bygget Karpathy-mønsteret inn i lessons — uten å kalle
   det det.** v2s `tasks/lessons.md` (indeks) + `tasks/lessons/<tema>.md`
   (detaljsider) + on-demand-lasting + lint er en nesten 1:1-implementasjon av
   Karpathys "LLM Wiki". v1 sier det til og med eksplisitt i sin README
   ("Designet er inspirert av Karpathy's LLM Wiki-mønster"). Så den første
   halvdelen av spørsmålet er i praksis *allerede gjort*.

2. **Det Karpathy-mønsteret IKKE løser er nettopp det du spør om: scope på
   tvers av prosjekter.** Karpathys wiki er én vault for ett kunnskapsdomene.
   Lessons i v1/v2 er bevisst *prosjekt-lokale* (`tasks/lessons/` i hvert
   repo). En Postgres-RLS-felle du løste i prosjekt A finnes ikke i prosjekt B.

3. **Cross-project lessons er teknisk gjennomførbart, men har én reell
   designspenning:** det bryter med v2s viktigste arkitekturprinsipp — at
   koordinatoren er *eneste skriver* av lokal state — og med repoets
   "selvstendige mapper, ingen delt `shared/`"-filosofi. Løsningen må håndtere
   en *delt, muterbar ressurs på tvers av repos* uten å gjeninnføre koblingen
   vi bevisst unngikk.

4. **Anbefaling (detaljer i §7):** En **to-lags lessons-modell** med en
   eksplisitt **promoteringsport**. Lag 1 = prosjekt-lokale lessons (som i
   dag). Lag 2 = en sentral, portabel **lessons-vault som et eget git-repo /
   Obsidian-vault**, delt på tvers av prosjekter via Claude Codes
   bruker-nivå-minne (`~/.claude`). En lesson "forfremmes" fra lokal til global
   kun når den er *portabel* (ikke prosjektspesifikk). Skriving til global skjer
   via git (append + lint), ikke via koordinatorens fil-skriving — det bevarer
   single-writer-invarianten per repo.

---

## 1. Spørsmålet, presisert

Du vil unngå å gjøre **samme feil på nytt i flere prosjekter**. I dag fanger
lessons-systemet en feil *innenfor* ett prosjekt godt, men kunnskapen er
innelåst i det repoet. Spørsmålet har derfor to deler:

- **(A) "Bygge Karpathy inn i lessons"** — er mønsteret vårt riktig modellert?
- **(B) "Lessons på tvers av prosjekter"** — hvordan deler vi den lærdommen som
  faktisk er portabel, uten å koble prosjektene unødig sammen?

Kort svar: (A) er nesten ferdig. (B) er det egentlige prosjektet.

---

## 2. Hva er Karpathys "LLM Wiki" / second brain? (primærkilde)

Kilde: Karpathys gist *"LLM Wiki"* (publisert april 2026).

**Kjerneidé:** Erstatt "spør LLM-en om igjen / kjør RAG på nytt hver gang" med
en **persistent, LLM-vedlikeholdt wiki** — *"a structured, interlinked
collection of markdown files"*. Kunnskap **kompileres én gang og holdes
oppdatert**, i stedet for å gjenutledes ved hver spørring. Wikien er *"a
persistent, compounding artifact"*.

Det berømte bildet: **"Obsidian is the IDE; the LLM is the programmer; the wiki
is the codebase."**

### Tre-lags-arkitektur

| Lag | Hva | Eier |
|---|---|---|
| **Raw sources** | Uforanderlige kilder (artikler, paper, data) | Mennesket kuraterer |
| **The wiki** | LLM-genererte summary-/entitet-/konseptsider med kryssreferanser | LLM-en eier helt |
| **The schema** | `CLAUDE.md` som definerer struktur, konvensjoner, workflows | Co-evolveres |

### Kjerne-workflows

- **Ingest:** Ny kilde → LLM leser, oppsummerer, oppdaterer indeks, reviderer
  relaterte sider. Én kilde berører typisk 10–15 sider.
- **Query:** LLM søker relevante sider, syntetiserer med sitater, og kan
  *arkivere* gode svar tilbake som nye sider.
- **Lint:** Periodisk helsesjekk — motsigelser, utdaterte påstander,
  foreldreløse sider (uten innlenker), manglende kryssreferanser.

### Indeks og logg

- **`index.md`:** innholdsorientert katalog, én linje per side + metadata. LLM
  oppdaterer ved hver ingest; **leser indeksen først** ved query.
- **`log.md`:** append-only kronologisk logg (`## [2026-04-02] ingest | …`),
  parsebar med enkle Unix-verktøy.

### Prinsipper Karpathy understreker

1. Mennesket kuraterer kilder og stiller spørsmål; **LLM-en gjør alt
   grunnarbeidet**. *"You're in charge of sourcing… The LLM does all the grunt
   work."*
2. Vedlikehold er ~gratis: *"LLMs don't get bored… can touch 15 files in one
   pass."*
3. Ingen gjenutledning ved hver query — syntesen finnes allerede.
4. Schema co-evolveres for ditt domene.
5. Alt er modulært/valgfritt — han foreskriver *ikke* eksakt mappestruktur.

Karpathy rammer dette inn som en realisering av Vannevar Bushs **Memex** (1945):
en personlig, aktivt kuratert kunnskapsbutikk der *koblingene* er like verdifulle
som dokumentene. Bush manglet vedlikeholds-motoren; LLM-en er den motoren.

---

## 3. Hva v2 ALLEREDE gjør (kartlegging mot Karpathy)

Dette er den viktigste innsikten i rapporten: **lessons-systemet er allerede en
Karpathy-wiki.** Kartlegging:

| Karpathy LLM-Wiki | v2 lessons | Status |
|---|---|---|
| `index.md` lest først, én linje per side | `tasks/lessons.md` (indeks, én-linjes bullets per tema) | ✅ Har det |
| Detaljsider per tema | `tasks/lessons/<tema>.md` (postgres-rls, typescript, …) | ✅ Har det |
| On-demand-lasting (ikke alt i kontekst) | "Les indeks ved oppstart, last kun relevante tema-filer" | ✅ Har det |
| LLM eier vedlikehold, mennesket kuraterer | Coordinator/implementer skriver; du godkjenner per release | ✅ Har det |
| Strukturert side-format | Pattern/Symptom + Sjekkliste fremover + `**Kilder:**` | ✅ Har det |
| `log.md` append-only | v1 har `tasks/lessons/log.md`; v2 har `open-followups.md` | 🟡 Delvis |
| Lint (motsigelser, duplikater, orphans) | v2 todo-done: "Hvis 2+ tidligere lessons dekker samme mønster: konsolider" | 🟡 Delvis (ingen egen lint-pass) |
| Kryssreferanser `[[wiki-link]]` | Obsidian-kompatibel, `[[fil]]`-syntaks dokumentert | ✅ Har det |
| Schema = `CLAUDE.md` | `CLAUDE.md` + `loop.config.yaml` (`lessons_topics`) | ✅ Har det |

**Konklusjon for del (A):** Vi trenger ikke "bygge inn" Karpathy — vi har gjort
det. De eneste reelle Karpathy-gapene som gjenstår *internt* er:

- En eksplisitt **lint-pass** som egen rutine (i dag skjer konsolidering kun
  opportunistisk i `todo-done`).
- En enhetlig **`log.md`** (v2 erstattet den med `open-followups.md`, som er en
  annen ting — carry-forward, ikke kronologisk hendelseslogg).

Begge er små, og uavhengige av cross-project-spørsmålet.

> Relevante filer: `v1-…/README.md` (Karpathy-sitatet, l.23–28),
> `v2-…/loop.config.example.yaml` (`lessons_topics`, l.88–101),
> `v2-…/templates/.claude/commands/todo-done.md` (skrive-regler, l.70–84),
> `v2-…/templates/docs/superpowers/loop/report-schema.md` (`lessons[]`, l.105–107),
> `v2-…/templates/docs/superpowers/loop/coordinator-runbook.md` (l.133).

---

## 4. Hva andre tenker (bransjelandskap 2026)

Du ba meg sjekke om andre har tenkt samme tanke. Det har de — på to nivåer.

### 4.1 Karpathy-community: implementasjoner av mønsteret

Flere repos implementerer LLM-Wiki/second-brain, men **så å si alle er
single-vault / personlig kunnskap**, ikke cross-project engineering-lessons:

- **NicholasSpisak/second-brain** — "LLM-maintained personal knowledge base for
  Obsidian. Based on Karpathy's LLM Wiki pattern."
- **Ar9av/obsidian-wiki** — "Framework for AI agents to build and maintain a
  digital brain through Obsidian."
- **shannhk/llm-wikid** — "Clone, run Claude Code, start building your second
  brain."
- **eugeniughelbur/obsidian-second-brain** — mest interessant for oss:
  *cross-CLI* skill (Claude Code, Codex, Gemini, OpenCode), 43 kommandoer,
  inkl. `/obsidian-architect` som **dokumenterer en kodebase** inn i vaulten.
  Dette er nærmest "engineering second brain", men fortsatt én vault.
- **ScrapingArt/Karpathy-LLM-Wiki-Stack** — "build-ready reference" for
  Obsidian + Claude Code.

**Læring:** Karpathy-leiren har løst *vault-mekanikken* (ingest/lint/index)
veldig bra, men behandler vaulten som *personlig kunnskap fra lesestoff* — ikke
som *delt prosedyreminne fra kodearbeid på tvers av repos*. Det er vår vri.

### 4.2 Agent-memory-leiren: de tenker eksplisitt cross-project

Den andre leiren (agent-memory-rammeverk) treffer kjernen i spørsmålet ditt
mer direkte:

- **Episodisk / semantisk / prosedural** er blitt standard-scopene i 2026. For
  kodeagenter er det vi kaller "lessons" nettopp **prosedural memory**: *"learned
  workflows, coding patterns, tool-use habits, review conventions."*
- **Delt team-/profil-minne:** *"With a shared profile across a team, the agent
  knows what other members have already learned… stop making mistakes that have
  already been corrected."* — det er presis formulering av målet ditt, bare på
  team- i stedet for prosjekt-akse.
- **`agents.md`/compound engineering:** *"every time the AI hits a wall or
  requires a manual correction, the agents.md file is updated"* — samme loop som
  vår lessons-skriving.
- **Den viktige begrensningen** (verdt å være ærlig om): *"Memory helps the agent
  avoid known mistakes… but it doesn't help with the unknown."* Cross-project
  lessons hjelper mot **gjentakelse**, ikke mot nye, ukjente feil.
- **Rammeverk** (Mem0, Zep/Graphiti, LangMem, Letta/MemGPT) løser dette med
  vektor-/graf-/self-editing-minne. For oss er det **overkill og feil
  abstraksjonsnivå**: markdown-i-git er allerede revisjonérbart, menneske-lesbart,
  diff-bart og Obsidian-kompatibelt. Vi vil ikke bytte det mot en vektordatabase.

### 4.3 Den native mekanismen vi allerede har: Claude Codes minnehierarki

Claude Code har **bruker-nivå-minne** `~/.claude/CLAUDE.md` som *"applies to all
projects… loaded in every project on your machine"*, med presedens der
prosjekt-nivå vinner over bruker-nivå. Dette er den innebygde, gratis kanalen
for cross-project kunnskap — og den vi bør bygge på i stedet for å finne opp en
ny.

---

## 5. Kjerneproblemet: hvorfor cross-project lessons ikke er trivielt

Tre konkrete spenninger vi må løse — ikke vis dem bort:

**(1) Portabilitet — den vanskeligste.** De fleste lessons er
*prosjektspesifikke* ("vår auth-tabell har en quirk"). Bare et delsett er
*portabelt* ("Supabase RLS-policies evalueres ikke for `service_role` — gjelder
ethvert Supabase-prosjekt"). Hvis vi deler *alt*, forurenser vi hvert nytt
prosjekt med irrelevant støy og blåser opp kontekst. **Vi trenger en
portabilitets-avgjørelse**, og den må tas av noen/noe som forstår forskjellen.

**(2) Single-writer-invarianten.** v2s mest bevisste valg er at *koordinatoren
er eneste skriver* av delt state, for å unngå race conditions mellom parallelle
workers. Et globalt lessons-lager er en **delt muterbar ressurs på tvers av
prosjekter** — flere prosjekter (potensielt samtidig) vil skrive til det. Det
gjeninnfører nettopp samtidighetsproblemet single-writer ble laget for å fjerne,
men nå på et nivå over enkeltrepoet.

**(3) Repoets "ingen delt `shared/`"-filosofi.** README, l.70–76: duplisering
foretrekkes fremfor en delt mappe som "binder versjonene sammen". Et globalt
lessons-lager er per definisjon en delt avhengighet. Det kan være riktig
avveiing her (kunnskap *skal* deles, til forskjell fra kode), men vi gjør det
med åpne øyne og holder koblingen løs (les-tungt, append-skriving, eget repo).

---

## 6. Arkitekturalternativer (med tradeoffs)

| # | Tilnærming | + | − |
|---|---|---|---|
| **A** | **Sentral lessons-vault som eget git-repo**, lenket inn i hvert prosjekt (git submodule eller symlink → `tasks/lessons/global/`) | Versjonert, Obsidian-vault, gjenbrukbar; eksplisitt grense lokal/global | Submodule = detached-HEAD-feller; symlink ikke portabelt mellom maskiner |
| **B** | **Bruker-nivå `~/.claude`** peker på sentral vault-sti; lessons-indeks lastes via bruker-minne | Native Claude Code-mekanikk; null nytt maskineri; presedens håndtert | Maskin-lokalt med mindre vaulten selv er git-synket; ikke team-delt av seg selv |
| **C** | **To-lags med promoteringsport** (lokal `tasks/lessons/` + global vault; eksplisitt "promote" av portable lessons) | Løser portabilitet direkte; lokal støy holdes ute av global; bevarer single-writer per repo | Krever en avgjørelses-regel + en skrive-sti til global |
| **D** | **MCP-server / søkeverktøy over sentral vault** | Skalerer til mange lessons; query on-demand uten å laste alt | Nytt infrastruktur-ledd; bryter "bare markdown i git"-enkelheten |

A og B er *transport*-mekanismer. C er *policy*-en som gjør delingen nyttig
i stedet for støyende. D er en *skala*-optimalisering vi sannsynligvis ikke
trenger før den globale vaulten er stor.

---

## 7. Anbefaling: to-lags lessons med promoteringsport

Kombiner **C (policy) + B/A (transport)**. Konkret skisse:

### 7.1 To lag

- **Lokalt lag (uendret):** `tasks/lessons.md` + `tasks/lessons/<tema>.md` i
  hvert prosjekt. Prosjektspesifikk kunnskap blir værende her. Koordinatoren er
  fortsatt eneste skriver — invariant bevart.
- **Globalt lag (nytt):** en **sentral Obsidian-vault som eget git-repo**, f.eks.
  `claude-lessons-global/`, med *samme* Karpathy-struktur (`lessons.md`-indeks +
  `<tema>.md` + en faktisk `log.md`). Delt inn i hvert prosjekt via Claude Codes
  bruker-minne (`~/.claude/CLAUDE.md` peker på vaultens indeks) — alternativt
  git submodule for team-deling.

### 7.2 Promoteringsporten (kjernen)

Utvid `lessons[]`-skjemaet i done-report med et **`scope`**-felt:
`scope: "project"` (default) eller `scope: "global"`. Implementeren foreslår
scope; **et eksplisitt steg i `todo-done` avgjør portabilitet** med en enkel
test:

> *"Ville denne lærdommen vært sann i et helt annet prosjekt med samme stack?
> Hvis ja → global. Hvis den nevner navn/tabeller/filer spesifikke for dette
> repoet → lokal."*

Kun `scope: global`-lessons forfremmes. Forfremming = append til den globale
vaulten + commit/push. Fordi global-skriving går via **git append**, ikke via
koordinatorens delte-state-skriving, unngår vi single-writer-bruddet: hvert
prosjekt committer sin egen lesson; git merger; lint rydder.

### 7.3 Lesing — uten kontekst-blås

Følg Karpathy-disiplinen vi allerede har: **last den globale `lessons.md`-indeksen
ved oppstart** (én linje per global lesson), og hent kun relevante globale
tema-filer on-demand. Indeksen er liten og vokser sakte; detaljene lastes bare
ved treff. Dette er nøyaktig grunnen til at wiki-strukturen finnes — den skalerer
til cross-project uten å sprenge kontekst.

### 7.4 Lint på global

Legg til en periodisk **lint-pass på den globale vaulten** (Karpathy-steget vi
mangler): dedupliser, slå sammen motsigelser, fang orphans. Dette er der den
virkelige verdien akkumuleres — global vault uten lint råtner raskere enn lokal,
fordi flere prosjekter dytter inn overlappende lessons.

### 7.5 Hvorfor dette passer repoets filosofi

- "Ingen delt `shared/`" handlet om å ikke koble *v1 og v2 kode* sammen.
  Kunnskap er motsatt: den *skal* deles. Vi holder koblingen løs ved at global
  vault er et **eget repo** (ikke en `shared/`-mappe inni template-repoet) og at
  prosjekter kun **leser indeks + appender**, aldri redigerer hverandres lokale state.
- Single-writer bevares per repo; global samtidighet håndteres av git, som er
  bygget for nettopp det.

---

## 8. Risikoer og åpne spørsmål

- **Portabilitets-feilklassifisering:** for aggressiv promotering → global vault
  full av prosjekt-støy. Mitigering: konservativ default (`project`), lint som
  flytter feilplasserte lessons ned igjen.
- **Stack-divergens:** en "portabel" Supabase-lesson kan bli utdatert når
  Supabase endrer seg. Mitigering: `**Kilder:**` + dato per lesson (har vi
  allerede), lint som flagger stale.
- **Team vs maskin-lokalt:** `~/.claude` er maskin-lokalt. For ekte team-deling
  må global vault være et synket git-repo (alt. A submodule). Avklar scope:
  *deg på tvers av dine prosjekter* vs *team på tvers av repos*.
- **Tema-taksonomi-drift:** `lessons_topics` er per-prosjekt i `loop.config.yaml`.
  Global vault trenger sin egen, stabile tema-liste — ellers spriker temaene.
- **Den ærlige begrensningen:** dette eliminerer *gjentatte kjente* feil, ikke
  nye. Selg det som det er.

---

## 9. Neste steg (hvis vi går videre)

1. Beslutt scope: **deg-på-tvers-av-prosjekter** (B, `~/.claude` + git-synket
   vault) eller **team** (A, submodule). Dette styrer transportvalget.
2. Spec'e `scope`-feltet i `report-schema.md` og promoteringssteget i
   `todo-done.md`.
3. Opprette `claude-lessons-global`-vault med Karpathy-struktur + `log.md` +
   lint-rutine.
4. Pilot: kjør to prosjekter mot samme global vault i noen uker, mål hvor mange
   lessons som faktisk er portable (validerer om gevinsten er reell før vi
   bygger maskineri).

---

## Addendum (2026-06-21): `brain`-repoet er besluttet og designet

Etter at rapporten ble skrevet kom det frem at den globale vaulten **allerede
finnes**: et privat repo `toreolavfurreness/brain` (lokalt `~/brain`), satt opp
som en Karpathy LLM-Wiki. Det bekrefter transport-valget i §6/§7 (Option A:
eget git-repo, ikke en delt `shared/`-mappe). To presiseringer følger.

### A1. `brain` er designet som *semantisk* wiki — lessons er *prosedural*

`brain` slik den er designet løser et **beslektet, men annet** problem enn det
opprinnelige cross-project-lessons-spørsmålet:

| | `brain` (slik designet) | Cross-project lessons (denne rapporten) |
|---|---|---|
| Minnetype | **Semantisk** — kunnskap fra lesestoff | **Prosedural** — lærdom fra kodearbeid |
| Inntak | Mennesket limer URL/snippet i `raw/inbox.md` → `/ingest` | v2-koordinator/implementer emitter lesson som data |
| Karpathy-fase | Full: `raw/` → diskuter → `wiki/` | Hopper over `raw/` — ankommer ferdig-strukturert |
| Form | `wiki/entities|concepts|sources|syntheses` | Pattern / Sjekkliste fremover / `**Kilder:**` |

`brain`s nåværende struktur (`raw/` + `wiki/`) er en lese-kunnskap-wiki.
Engineering-lessons er prosedural memory og har en annen generator (kodeagenten,
ikke et menneske som klipper artikler).

### A2. Anbefaling: ett `brain`-repo, et tredje tre — ikke to repos

Brukeren ønsket eksplisitt "én wiki for alt på tvers, ikke splittet per
prosjekt". Det er riktig instinkt. Løs det med et **tredje toppnivå-tre** i
`brain`, ved siden av `raw/` og `wiki/`:

```
brain/
├── raw/          ← ingest-kilder (uendret; mates av /ingest)
├── wiki/         ← semantisk kunnskap (uendret; mates av /ingest)
└── lessons/      ← NY: prosedural engineering-kunnskap
    ├── index.md          (eller egen seksjon i topp-index.md)
    ├── postgres-rls.md
    ├── typescript.md
    └── ...
```

- `wiki/` mates av mennesket via `/ingest`.
- `lessons/` mates av `claudecode`-v2 via **promoteringsbroen** (§7.2): bare
  `scope: global`-lessons forfremmes hit; prosjektspesifikke blir i repoets egen
  `tasks/lessons/`. Disse går rett i `lessons/` + `index.md` + `log.md` — ingen
  `raw/`-runde, fordi de allerede er strukturert.
- Samme `CLAUDE.md`-schema, samme `index.md`, samme `log.md`, samme
  Obsidian-vault. **Én hjerne, to inntak.**

### A3. Hvordan v2-prosjekter leser `brain/lessons/`

Brukerens besluttede mekanisme passer rett inn: `claude --add-dir ~/brain/wiki`
(utvid til `~/brain/lessons`), eller en `/brain`-kommando som leser `index.md`.
Følg Karpathy-disiplinen (§7.3): last **indeksen** ved oppstart, hent tema-filer
on-demand.

### A4. Justert neste steg (erstatter §9 der det avviker)

1. Legg `lessons/`-treet + en lessons-seksjon i `index.md`/`CLAUDE.md` til
   `brain` (kjør helst Claude Code i en sesjon scopet til `brain`).
2. Beslutt en **stabil tema-taksonomi** for `brain/lessons/` (jf. risiko i §8 om
   taksonomi-drift) — uavhengig av per-prosjekt `loop.config.yaml`.
3. Spec'e `scope`-feltet i `report-schema.md` + promoteringssteget i
   `todo-done.md` (skriver til `~/brain/lessons/` via git append).
4. Pilot: kjør to v2-prosjekter mot `brain/lessons/`, mål portabilitets-andel.

> Status `brain` (fra brukerens oppsummering): konsept besluttet, mappestruktur
> + filer generert (template-zip), `~/brain` + GitHub-repo opprettet. Gjenstår:
> pakke ut template, første push, åpne som Obsidian-vault, `/wiki-start`. Disse
> stegene er uavhengige av lessons-integrasjonen over.

---

## 10. Kilder

**Primær (Karpathy):**
- [Karpathy — "LLM Wiki" (gist)](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)

**Community-implementasjoner av mønsteret:**
- [NicholasSpisak/second-brain](https://github.com/NicholasSpisak/second-brain)
- [Ar9av/obsidian-wiki](https://github.com/ar9av/obsidian-wiki)
- [shannhk/llm-wikid](https://github.com/shannhk/llm-wikid)
- [eugeniughelbur/obsidian-second-brain (cross-CLI)](https://github.com/eugeniughelbur/obsidian-second-brain)
- [ScrapingArt/Karpathy-LLM-Wiki-Stack](https://github.com/ScrapingArt/Karpathy-LLM-Wiki-Stack)

**Forklaringer / breakdowns:**
- [MindStudio — What is Karpathy's LLM Wiki](https://www.mindstudio.ai/blog/andrej-karpathy-llm-wiki-knowledge-base-claude-code)
- [aimaker — How I took Karpathy's LLM Wiki into Obsidian](https://aimaker.substack.com/p/llm-wiki-obsidian-knowledge-base-andrej-karphaty)
- [Reliability Whisperer — Knowledge as "compiled code"](https://reliabilitywhisperer.substack.com/p/the-andrej-karpathy-llm-wiki-idea)

**Agent-memory / cross-project:**
- [Hindsight — How agent memory reduces repetition and rework](https://hindsight.vectorize.io/guides/2026/04/23/guide-how-agent-memory-reduces-repetition-and-rework)
- [Stormy AI — Mastering agents.md for long-term memory](https://stormy.ai/blog/mastering-agents-md-ai-coding-memory)
- [mem0 — State of AI Agent Memory 2026](https://mem0.ai/blog/state-of-ai-agent-memory-2026)
- [Cloudflare — Introducing Agent Memory](https://blog.cloudflare.com/introducing-agent-memory/)
- [Vectorize — Best AI agent memory systems 2026](https://vectorize.io/articles/best-ai-agent-memory-systems)

**Claude Code minnehierarki:**
- [Claude Code Docs — Memory](https://code.claude.com/docs/en/memory)
- [Git — Submodules](https://git-scm.com/book/en/v2/Git-Tools-Submodules)
