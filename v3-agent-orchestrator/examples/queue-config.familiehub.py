"""Eksempel: FamilieHubs tasks/queue-config.py — alle nøklene i bruk.

Øyeblikksbilde fra FamilieHub-app (dev 96f9832, 2026-10-02). Gjenskaper FamilieHubs køside med den
felles tasks/queue-status.py: markdown-utdata er identisk med den gamle prosjektspesifikke
generatoren, og HTML-siden er lik bortsett fra to forklarende setninger. Kopiert til FamilieHub er
dette prosjektets egen fil; i kit-et er den bare et eksempel og oppdateres ikke.

Mal med forklaring per nøkkel: v3-agent-orchestrator/templates/tasks/queue-config.py.
"""

TITLE = "FamilieHub-køen"
OWNER_NAME = "Tore Olav"
BASE_REF = "origin/dev"

# FamilieHub grupperer på nummer-sett og tags, ikke på `epic:`-feltet. Slå på når epic-feltet
# er fylt ut på todoene som i dag havner i «Uklassifisert».
EPIC_FROM_FIELD = False

# Hvem som kan flytte en v1.10-rad. Kan IKKE utledes: `is_pause` fanger migrasjon/prod/native,
# men ikke «krever en fysisk iPhone» eller «krever ett EAS-bygg» — og nettopp de to er grunnen
# til at fire av sju v1.10-rader ikke kan røres av loopen. Håndvedlikeholdt, som NOTES.
# Format: nr -> (eier, hva som må skje). Eier er "loop" eller "eier".
EIERSKAP = {
    "278": ("loop", "Kan claimes av loopen nå."),
    "279": ("loop", "Kan claimes av loopen nå."),
    "329": ("loop", "Dev er fritt; selve fiksen er en migrasjon på `delete_my_account()`, så prod-applyen er et pausepunkt."),
    "367": ("eier", "**Selve leveransen.** Prod-deploy → EAS-bygg → TestFlight. `/release-prod` dekker ikke den native halvdelen — null treff på EAS/TestFlight."),
    "239": ("eier", "Venter på bygget fra 367. Samme bygg låser opp 269."),
    "269": ("eier", "Venter på bygget fra 367 + en fysisk iPhone. Lukker BUG-069, 070 og 072."),
    "293": ("eier", "**Prod-sesjon.** Kjørelista er sendt (`prod-kjoreliste-2026-09-14.sql`)."),
    "108": ("eier", "Samle-backlog for native-verifisering. Tømmes på TestFlight, ikke i loopen."),
    # v1.12 (lagt inn 2026-09-22 da planene ble skrevet). Samme kriterium som over: loopen kan
    # gjøre dev-halvdelen, men radene under har et steg bare Tore Olav kan utføre.
    "374": ("eier", "**Nivå A godkjent 2026-09-22.** Loopen kan implementere etter v1.11-releasen; V12–V14 (oppstart, skrifttype og layout på enhet) er fortsatt Tore Olavs."),
    "372": ("eier", "Dev-halvdelen er loopens. V11 er prod-migrasjonen som sletter kollisjonstapere — den kjøres av Tore Olav i `/release-prod` Steg 5."),
    "384": ("eier", "Loopen kan implementere; V13 er et EAS-bygg og V14 en enhetssjekk mot dev-testfamilien."),
}

# Klynger i visningsrekkefølge. Eksplisitte nummer-sett først (de bærer skiller som ikke
# finnes i tags, f.eks. Oda fase 1 vs. fase 2/3); ellers faller `cluster_of` tilbake på
# epic-taggen i todo-fila, slik at nye todos havner riktig uten manuelt vedlikehold her.
CLUSTERS = [
    ("Oda fase 1", {"196", "196A", "196B", "197", "198", "199", "200", "390", "391", "392", "270", "272", "273", "280", "290", "310", "311", "316"}),
    ("Release-blokkerende bugs", {"267", "268", "269", "293", "295", "278", "279"}),
    ("Miljøkonfigurasjon-epic", {"262", "122", "213", "214", "215"}),
    ("Skrive-robusthet-epic", {"263", "191", "235", "236", "238"}),
    # Vareikoner slått inn 2026-09-09 (eier-besluttet): 255s egen tittel er «Handleliste: eget
    # strek-ikonsett», og ikonene lever i handleliste-raden. To etiketter for samme flate gjorde at
    # 255A og 282 rendret som ulike epics selv om de endrer samme rad.
    ("Handleliste-epic (inkl. vareikoner)",
     {"264", "152", "171", "120", "255", "255A", "255B", "282"}),
    ("Agent-epic", {"265", "248", "249"}),
    ("Veikart-epic", {"221", "222", "223", "224", "225", "226", "227", "228"}),
    ("Kalender-epic", {"127", "239", "240", "241"}),
    ("Oda fase 2 og 3", {"201", "202", "203", "204", "205", "206"}),
    # Slått sammen 2026-09-09 (eier-besluttet): «Loop-hygiene (prioritert)» og
    # «Loop self-mod + lessons» var to etiketter på samme familie, og TI loop-todos stod
    # utenfor begge — de rendret som «Uklassifisert» eller falt tilfeldig inn via EPIC_TAG_CLUSTER.
    # Én epic for orkestrering, graf og lessons. Legg NYE loop-todos inn her, ikke i en ny klynge.
    ("Loop-epic (orkestrering, graf, lessons)",
     {"96", "177", "178", "184", "186", "188", "189", "194", "194B", "207", "208", "210",
      "211", "212", "216", "219", "220", "230", "232", "234", "237", "242", "243", "244",
      "245", "251", "253", "254", "256", "257", "258", "259", "260", "266", "271", "274",
      "275", "276", "281", "291", "292", "297", "298", "299"}),
    # Nye 2026-09-09 (eier-besluttet). Funnet mekanisk: fire todos redigerer
    # app/(app)/family.tsx og lå spredt fra køplass 1 til 61, tre av dem uten epic i det hele tatt.
    ("Min Familie-epic", {"288", "289", "229", "285", "294"}),
    # 284 og 261 er begge oppskrift-skjermens EGNE funksjoner (ikke Oda-integrasjonen, som eies av
    # Oda fase 2/3). Svakere signal enn family.tsx: de deler domæne, ikke målte filer.
    ("Oppskrifter-epic", {"284", "261", "296"}),
    ("S — uten epic", { "104", "108", "147", "123", "124", "217", "218",
                       "56b", "87", "88"}),
]

# Fallback: epic-tag -> klyngenavn. Brukes når nummeret ikke står i en liste over.
EPIC_TAG_CLUSTER = {
    "oda": "Oda fase 1",
    "vareikoner": "Handleliste-epic (inkl. vareikoner)",
    "miljokonfig": "Miljøkonfigurasjon-epic",
    "skrive-robusthet": "Skrive-robusthet-epic",
    "handleliste-epic": "Handleliste-epic (inkl. vareikoner)",
    "handleliste": "Handleliste-epic (inkl. vareikoner)",
    "agent-epic": "Agent-epic",
    "veikart": "Veikart-epic",
    "release-notes": "Veikart-epic",
    "kalender": "Kalender-epic",
    "loop": "Loop-epic (orkestrering, graf, lessons)",
    "self-mod": "Loop-epic (orkestrering, graf, lessons)",
    "orkestrering": "Loop-epic (orkestrering, graf, lessons)",
    "lessons": "Loop-epic (orkestrering, graf, lessons)",
}

# Håndvedlikeholdt, som CLUSTERS: to setninger per todo om hva den gjelder.
# Legg inn nye todos her når de opprettes — mangler nummeret, rendres ingen linje.
NOTES = {
    "196B": "Edge Function oda-mcp: selve OAuth-koblingen mot Oda (link/unlink) pluss token-refresh. **Nå eligible** — 196A er applyet mot dev og arkivert 2026-09-10, `oda_link_sessions` finnes og Steg 9b-gaten står `all_ok = true`. Prod-porten er Tore Olavs: de tre migrasjonene må applyes på prod FØR denne koden når main/EAS.",
    "270": "Retter tre prober i 196A-verifiseringsharnessen som er vakuøse: de står grønne selv med ødelagt CASCADE, med kolonne-grants til anon/authenticated, og med halve app_config-kommentaren borte. Uten dette er «Steg 9 dry-run grønn» en gate som ikke måler noe, så den blokkerer hele dev-applyen.",
    "316": "Steg 9b-gaten ser ikke `request.jwt.claims` / `request.jwt.claim.role` — nettopp de GUC-ene Supabases auth.uid()/auth.role() leser, så en persistert default kan forfalske RLS i hele prosjektet uten at gaten reagerer. Dev-baselinen som manglet i TODO 280 er nå målt til 0 i begge kataloger, så utvidelsen kan gjøres uten å allowliste eksisterende tilstand. Fra CF-280-16; søstertodo til 311 på samme filpar.",
    "197": "«Vår butikk»-innstilling i appen pluss UI-et for å koble familien til Oda. Legger også inn et provider-lag, så senere butikker kan kobles på uten å endre skjermene.",
    "198": "To Edge Functions: match_items som oversetter handlelistevarer til Oda-produkter i to trinn, og push_cart som legger dem i kurven. Dette er motoren bak «Send til Oda».",
    "390": "Oppfølging fra v1.11: lengdetak på varenavn (rotårsaken til CF-198A2b-1) og «Koble til på nytt» i Innstillinger når Oda-tilgangen er borte. Venter på 199, som kan dekke relink-delen.",
    "391": "Server-kontrakten for klare varer i Send til Oda-arket: produktnavn og byttbare kandidater også for auto/confirmed. 199 venter på denne.",
    "392": "Oda som valgbar butikk i Vår butikk, skjuling av Kassalapp-priser for Oda-familier og en Oda-statusrad (spec B3, § 4.3).",
    "199": "Selve «Send til Oda»-knappen med bekreftelses-sheet og kvittering etterpå. Siste brikke som gjør fase 1 brukbar ende-til-ende.",
    "200": "Avklaringer som må tas med Oda direkte, og registrering av prod-OAuth-klienten. Prod-delen utføres av Tore Olav selv.",
    "267": "SSRF-hull (BUG-111): isPrivateHost klassifiserer IP-adressen før den kanoniseres, så desimal-, oktal-, hex- og IPv6-mappede former slipper forbi. Todoen kanoniserer først, og validerer i tillegg mellomliggende redirect-hopp — i dag holder det å svare 302 mot cloud-metadata for å omgå kontrollen.",
    "268": "BUG-119: i to komponenter dekker en KeyboardAvoidingView hele backdroppen, så trykk utenfor kortet ikke lukker arket. Én-linjes fiks (pointerEvents box-none) i samme mønster som BUG-100.",
    "269": "Tre bugs (069, 070, 100) er allerede kodefikset og ligger på dev, men kan bare lukkes ved å verifiseres på ekte enhet. Siden release er det eneste som får koden ut på enheten, bryter denne todoen vranglåsen med en EAS-build direkte fra dev.",
    "184": "Worker-worktrees kan ikke kjøre full e2e-suite fordi env-allowlisten er for smal. Det gjør at hver implementer rapporterer e2e_blocked i stedet for et ekte resultat.",
    "194B": "Rydder opp i ~25 gamle worktrees og legger inn telling av dem i helsesjekken. Uten det vokser .claude/worktrees/ ubegrenset og holder branches låst.",
    "207": "Rulle ut rolle-spesifikt agent-minne til de seks resterende subagentene; i dag har bare implementeren det. Minnet er forbruksvare og skal peke til lessons, aldri kopiere dem.",
    "208": "Produsent-siden av kunnskapsgrafen: få rapportfeltene faktisk skrevet inn, og presisere nodetypene. Flere andre todos (212, 242) venter på denne.",
    "232": "tasks/lessons/react-native-web.md har passert splitt-terskelen (56 lessons, 513 linjer) og må deles. Ren omplassering — ingen lesson-tekst skal endres.",
    "251": "Samme for tasks/lessons/migrations.md (52 lessons, 484 linjer). Begge splittene må oppdatere indeksen og alle «Se også»-pekere i samme PR.",
    "221": "«Hva er nytt»-side som viser release-historikken fra release_notes-tabellen. Grunnmuren fire andre veikart-todos bygger på.",
    "222": "Migrasjon for roadmap_items med RLS: planlagte punkter, ideer og kjente feil. Datamodellen bak «Veikart»-siden.",
    "241": "Kalenderhendelser forsvinner eller blir stående igjen fordi hentevinduet er låst til 30 dager. Rammer brukere med avtaler lenger fram i tid.",
    "152": "Duplikatvakt i handlelistens legg-til-ark, og gjenoppliving av allerede avkryssede varer i stedet for å lage en ny rad. Fjerner den vanligste kilden til rot i lista.",
    "249": "Oppgradere @anthropic-ai/sdk i alle Edge Functions og rette prompt-formatet for Haiku 4.5. Blokkerer Agent-epicen (248).",
    "255A": "Første halvdel av vareikon-pipelinen: generator og vektorisering, fra manifest til ferdige SVG-er. Gir handlelista og ukemenyen ekte ikoner i stedet for emoji.",
    "261": "Bildeimport av oppskrift støtter i dag bare ett bilde; mange oppskrifter går over to sider. Utvider importen til flere bilder per import.",
    "271": "tasks/lessons/workflow-process-sep2026.md er på 1315 linjer / 111 lessons, mot en terskel på ~400/50 — klart verst av tema-filene, og den eneste over terskel uten egen todo. Kronologisk periode-splitt; ren omplassering der ingen lesson-tekst skal endres.",
    "203B": "Skilt ut fra 203: selve innholdsimporten (ingredienser og fremgangsmåte) fra en Oda-oppskrift, etter at søket i 203 har funnet den.",
    "229": "Skostørrelse som felt på profilen. Liten, selvstendig Min Familie-rad.",
    "313": "Ingrediensarket mangler safe-area i bunnen — innhold havner under hjemme-indikatoren på iPhone. Plan godkjent 2026-09-22.",
    "372": "`normalizeShoppingName` mangler Unicode-NFC, så «blåbær» skrevet på to måter ikke matcher. Krever en datamigrasjon som sletter kollisjonstapere; prod-applyen (V11) er Tore Olavs. Plan godkjent 2026-09-22.",
    "373": "Lukkeknapper under 44×44 og manglende safe-area i handleliste-arkene — avvik mot Apples HIG. Plan godkjent 2026-09-22 etter to review-runder.",
    "374": "Nunito og Nunito Sans lastes aldri på iOS native, så alle `fontFamily`-deklarasjonene er no-ops og appen rendrer systemfonten. Krever `expo-font`-plugin i `app.json` — nivå A. Plan r3 skrevet 2026-09-22.",
    "384": "`preview-dev` arver EAS-miljøet «production» og reddes bare av to linjer i `eas.json`. Planen gir hver profil eksplisitt `environment` og en vakt i `app.config.js` som stopper bygget ved feil Supabase-ref. Plan godkjent 2026-09-22.",
    "201": "F3: send en hel ukemeny til Oda-kurven i én operasjon, ikke vare for vare. Bygger på match_items/push_cart fra 198 og venter derfor på at 199 er ferdig.",
    "202": "F4: velg leveringstid, legg den i familiekalenderen, og følg ordrestatus i appen. Gjør Oda-integrasjonen til noe familien ser i hverdagen, ikke bare en kurv som sendes.",
    "203": "F6a: søk i Odas oppskriftskatalog fra oppskriftsimporten. Den av fase 2-todoene som avblokkeres først, siden den kun venter på 196B og ikke på hele fase 1-kjeden.",
    "204": "F6b: legg ingrediensene fra en Oda-oppskrift rett i kurven via recipe_id, uten å gå veien om tekstmatching. Forutsetter oppskriftssøket i 203.",
    "205": "F5 (fase 3): påfyll — faste varer familien alltid trenger foreslås inn i handlelisten automatisk. Krever handlelistekjeden fra 199.",
    "206": "F6c (fase 3): la KI-ukemenyen bygge på ekte Oda-oppskrifter i stedet for frie forslag. Siste steg i Oda-sporet, og avhenger av oppskriftssøket i 203.",
    "266": "Tre strukturelle defekter i loop-helsesjekkens D4-steg, funnet 2026-09-07: den ser ikke decision-log-entries skrevet i gammelt format, den sammenligner A- og B-valg som om de var samme mengde, og A-regexen bommer på formen som faktisk brukes.",
}

# Releaser fra før `release:`-feltet (v1.15) var en tag på todoen.
RELEASE_TAGS = ("release-1.10.0", "release-1.11.0", "release-1.12.0", "release-1.13.0", "release-1.14.0", "release-1.15.0")

# Leverte releaser. De har ingen fil i tasks/releases/, så teksten står her.
LEVERT = {
    "v1.14": ("<strong>Prod-release 2026-10-01</strong> (#1068, <code>7b8290d9</code>): skoleukeplanen fra PDF "
              "via gjennomgang til kalender, gjøremål og «I dag», kontaktenes bursdager, brukerhjelp og "
              "cron-vakten. Push-bryterne slås på tidligst 7 døgn etter D-7."),
    "v1.13": ("<strong>Prod-release 2026-09-27</strong> (#1026, <code>55cc1027</code>): kalender med "
              "ICS-abonnement og robusthet, nye vareikoner, mengder som legges sammen og vekt-anslag, "
              "Oda leveringstid, faste varer, lærte varevalg og KI-ukesmeny med Oda-oppskrifter. "
              "Web på Vercel og TestFlight build 38 (1.13.0) mot prod."),
    "v1.12": ("<strong>Prod-release 2026-09-25</strong> (#984): Oda fase 2 — ukesmeny og oppskrifter til "
              "Oda-kurven, Oda-oppskrifter i kokeboka, utsolgt-alternativer — kompakt og raskere handleliste, "
              "profilbilde, skostørrelse og Nunito på iOS. Det som ikke rakk, bærer <code>release-1.13.0</code>."),
    "v1.11": ("<strong>Prod-releasen gikk ut 2026-09-24</strong> (#956, <code>babdd5e1</code>): "
              "Oda-handel — koble til Oda, send handlelisten til Oda-kurven, favorittbutikk og "
              "Kassalapp-priser. Web på Vercel og TestFlight build 33 (1.11.0) mot prod. "
              "Scopet er lukket — det som ikke rakk, bærer nå <code>release-1.12.0</code>."),
    "v1.10": ("<strong>Web-releasen gikk ut 2026-09-14.</strong> "
              "Den native halvdelen (EAS-bygg og TestFlight) fulgte etter."),
}

# Fargesporene slik siden hadde dem (v1.10–v1.12 farget, senere releaser nøytrale).
RELEASE_COLORS = {"v1.10": 1, "v1.11": 2, "v1.12": 3}

SCOPE_NOTE = "Prod-applyen av migrasjoner er Tore Olavs port foran `main` og EAS-bygg."
RELEASE_NOTE = "Merk: <code>release-notes</code> er et <em>tema</em> (in-app «Hva er nytt»-side), ikke en release-tag."

EKSTRA_FLAGG = [
    ("<code>release-notes</code> er ikke en release",
     "Fire todos (221, 224, 225, 226) bærer taggen <code>release-notes</code>. Den er et produkt-tema — "
     "in-app «Hva er nytt»-siden — og ser ut som en release-tag uten å være det. De teller derfor som "
     "«uten release-tag» her, som er riktig."),
]

MERKNADER = [
    'Oda fase 2 og 3 (201–206) ble flyttet til `order` 2000–2040 (2026-09-08, etter eiers ønske) og ligger nå foran både loop-selvmod (2150–2175) og Veikart-epicen (2210). Merk: rekkefølgen gjør dem IKKE kjørbare tidligere — alle seks er deps-gatet bak Oda fase 1 (203 venter på 196B; 201/202/205 på 199). Den avgjør hva loopen tar FATT PÅ når fase 1 lander.',
    '200 (Avklaring med Oda + prod-OAuth-klient) ligger fortsatt på `order` 2510, altså BAK fase 2 og 3, selv om den er fase 1-arbeid og gater prod-klienten. Den er `elig` nå, men krever at Tore Olav kontakter Oda — den flyttes ikke automatisk.',
    '267 ble planlagt 2026-09-08 som pipelinet B, men planner-rapporten flagget `technical_risk` (Edge Function-deploy, A8). Runbook §5c dropper da B ut av pipelinen FØR planen committes, så den ble stående `open`/`elig` med `plan: null`. **Claimet som A 2026-09-10** etter at Tore Olav ga eksplisitt go for dev-deploy. Prod-deploy er IKKE gitt — den hører til v1.10-releasen og utføres av ham selv. Se `decision-log.md` 2026-09-08 08:35.',
    '**Denne oversikten viste tidligere ikke todos med `status: reviewed`.** Filteret sjekket kun `status == "open"`, så en todo med godkjent plan — nøyaktig den som er klarest til å claimes — var usynlig i både markdown og artifact. Rettet 2026-09-08. TODO 188 (guard-main-merge parser, `prioritert`, ingen deps, plan siden 2026-09-07) hadde ligget i det hullet.',
    '272 og 273 ble opprettet 2026-09-08 fra TODO 270s kode-review r4 og r5. Begge er harde deps på 196A Steg 9b, som derfor har `deps: ["195B", "270", "272", "273"]`. **273 er ferdig og arkivert 2026-09-08 kveld** (PR #572): tekst-nåbarhets-proben ble forkastet og erstattet av en katalogbasert allowlist. **272 er merget og arkivert 2026-09-09** (PR #589, `65ba7daa`) etter fire fix-runder; alle fire predikat-ledd er identitetsbundet og harnessen gikk 27 → 39 scenarier. Ingen av de to er lenger en sperre. Se `decision-log.md` 2026-09-08 12:05, 14:20 og 21:09.',
    "**288/289 er eier-besluttet foran Oda fase 1** (order 1955/1956, 2026-09-08, fra pilottester Lars' tilbakemelding, PR #576/#582). 288 fikser BUG-123 (fødselsdato valgt i iOS-spinneren lagres ikke — stille datatap i en opprettelsesflyt). **Merk:** 288s egen fix-retning punkt 1 krever at hypotesen verifiseres på TestFlight FØR koding, så den kan ikke lukkes uten ekte enhet — samme vranglås som TODO 269 finnes for å bryte. 284 (Kokeboka) er lagt inn på 1963, foran kurv-flyten 197/198/199.",
    '283, 286 og 287 kom inn fra samme triage som `deferred + forslag` og er derfor usynlige for køen til de triageres — 286 er en rettighetsavklaring som gater innholdet i 284.',
    '268 ble claimet som A foran 272/273 selv om de har lavere `order`, fordi 268s plan var ferdig plan-reviewet og kunne implementeres med null latens. 273 planlegges parallelt som pipelinet B og claimes rett etter — 196A venter uansett på begge, så ingen release-kritisk sti taper tid.',
    '212 og 232 ligger etter 185 fordi de er `normal`; de er små og henger på 208/185.',
    '238 (recipes-skriverobusthet) ble triagert og **splittet i 238A/238B 2026-09-10** (B2). **238A er merget og arkivert** (PR #629, `80fda616`) etter fem fix-runder og fire kode-review-runder. **238B er nå eligible** — den bærer tre pausepunkter: to A7 (dev-apply, T-fil-kjøring) og en release-blokkerende port 0, der migrasjonene MÅ være applyet på prod av Tore Olav FØR main-merge og FØR et EAS-bygg som inneholder koden. Planfila deles av begge og arkiveres først når del B er ferdig.',
]


def EKSTRA_MERKNADER(todos, sh):
    """Startbetingelser som §1 ikke sjekker mekanisk (koordinatoren sjekker ved claim)."""
    if "233" not in todos or todos["233"].get("status") != "open":
        return []
    pf = sh("grep -c 'pipelined_from=' docs/superpowers/loop/run-log.md")
    if pf in ("0", "?"):
        return ["**233 hoppes over ved claim** til trinn 1 er kjørt i drift: startbetingelsen er minst én "
                "`pipelined_from=`-rad i `run-log.md` (i dag: 0 — begge pipelinede B-er hittil ble droppet før claim). "
                "Neste `elig` tas i stedet."]
    return [f"233-startbetingelsen er oppfylt ({pf} `pipelined_from=`-rad(er) i `run-log.md`)."]
