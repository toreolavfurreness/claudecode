"""Prosjektdelen av køsiden. tasks/queue-status.py (kit-eid, lik i alle prosjekter) leser denne fila.

PROSJEKT-EID: /setup skriver fila bare hvis den mangler, og rører den aldri igjen.

Alle nøkler er valgfrie. En tom fil gir en fungerende side: releaser, mål, done_when, epics og
fremdrift leses fra tasks/releases/ og todoenes `release:`/`epic:`. En nøkkel som ikke står i lista
under stopper generatoren (en feilstavet nøkkel ville ellers blitt ignorert uten at noen merket det).
Egne hjelpenavn må derfor begynne med `_` eller være små bokstaver.

Fjern `#` foran det du vil bruke. Eksempel med alle nøklene i bruk:
v3-agent-orchestrator/examples/queue-config.familiehub.py.
"""

# Tittelen på siden (<title> og <h1>). Vakten i docs/superpowers/loop/artifacts.md greper etter den.
# TITLE = "{{PROJECT_NAME}}-køen"

# Navnet på pillen for rader bare eieren kan flytte (se EIERSKAP).
# OWNER_NAME = "eier"

# Ref-en hvis SHA står øverst på siden.
# BASE_REF = "origin/{{BASE_BRANCH}}"

# Hvem som kan flytte en rad i en aktiv eller levert release. Kan ikke utledes: «krever en fysisk
# telefon» eller «krever et app-bygg» står ikke i frontmatter. nr -> ("loop" | "eier", hva som må skje).
# EIERSKAP = {
#     "42": ("eier", "Prod-migrasjonen kjøres av eieren i release-steget."),
# }

# Epic-gruppering. Uten nøklene under grupperes køen på todoens `epic:`-felt.
# CLUSTERS = [                          # eksplisitte nummer-sett, i visningsrekkefølge (vinner over alt)
#     ("Innlogging-epic", {"12", "13", "17"}),
# ]
# EPIC_TAG_CLUSTER = {"auth": "Innlogging-epic"}   # tag eller epic-slug -> epic-navn
# EPIC_FROM_FIELD = True                # False = ignorer `epic:`-feltet, bruk bare CLUSTERS og tags

# To setninger per todo om hva den gjelder. Rendres under raden i både markdown og HTML.
# NOTES = {
#     "12": "Bytter passord-innlogging til magisk lenke. Krever ny e-postmal.",
# }

# Regexene som merker en rad som pausepunkt-kandidat (tags og tittel).
# PAUSE_TAGS = r"migrasjon|migration|prod\b|edge-function|native|secrets|rls"
# PAUSE_TITLE = r"migrasjon|edge function|oauth|prod-|deploy|native"

# Releaser fra før `release:`-feltet fantes, da releasen var en tag på todoen.
# RELEASE_TAGS = ("release-1.2.0", "release-1.3.0")

# Leverte releaser. En release-fil med `status: shipped` (og gjerne `shipped: "ÅÅÅÅ-MM-DD"`) gir en
# levert-bane av seg selv. Her: tekst som overstyrer den, eller releaser som ikke har en fil.
# LEVERT = {
#     "v1.3": "<strong>Prod-release 2026-09-01</strong>: invitasjoner og tilganger.",
# }

# Fargespor (1–3) per release. Standard: aktiv release spor 1, planlagte spor 2.
# RELEASE_COLORS = {"v1.3": 2, "v1.4": 1}

# Ekstra tekst: under «Release <x> — scope» (markdown) og i ingressen til release-seksjonen (HTML).
# SCOPE_NOTE = "Prod-migrasjonene kjøres av eieren før main."
# RELEASE_NOTE = "Merk: taggen <code>release-notes</code> er et tema, ikke en release."

# Merknader om rekkefølge og historikk (markdown, én linje hver).
# MERKNADER = [
#     "17 ligger bak 13 fordi den deler skjermen med 13s refaktor.",
# ]

# Betingede merknader: kalles med (todos, sh), returnerer en liste markdown-linjer.
# def EKSTRA_MERKNADER(todos, sh):
#     return []

# Ekstra varsler under «Datakvalitet»: [(tittel-HTML, tekst-HTML)].
# EKSTRA_FLAGG = []
