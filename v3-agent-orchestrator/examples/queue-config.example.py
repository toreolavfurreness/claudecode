"""Eksempel: tasks/queue-config.py med alle nøklene i bruk.

Tallene og tekstene er oppdiktet. Kopier det du trenger til prosjektets egen tasks/queue-config.py.
"""

TITLE = "Eksempel-køen"
OWNER_NAME = "Kari"
BASE_REF = "origin/dev"

# Slå av når køen grupperes på nummer-sett og tags, ikke på todoens `epic:`-felt.
EPIC_FROM_FIELD = False

# Avtalt agenda øverst på siden.
AGENDA = {
    "tittel": "Ukens gjennomgang",
    "hvorfor": "Tre todoer venter på et valg fra eieren.",
    "punkter": [("Rekkefølge", "Skal 14 gå foran 12?")],
}

# Hvem som kan flytte en rad i en aktiv eller levert release.
EIERSKAP = {
    "12": ("eier", "Prod-migrasjonen kjøres av eieren i release-steget."),
    "14": ("loop", "Venter på at 12 er ferdig."),
}

# Eksplisitte nummer-sett, i visningsrekkefølge. Vinner over tags og `epic:`.
CLUSTERS = [
    ("Innlogging", {"12", "13"}),
    ("Varsler", {"14"}),
]

# Tag eller epic-slug -> epic-navn.
EPIC_TAG_CLUSTER = {"varsler": "Varsler", "auth": "Innlogging"}

# To setninger om hva todoen gjelder. Rendres under raden.
NOTES = {"12": "Flytter sesjonen til en ny tabell. Krever migrasjon."}

# Regex for tags og titler som gir pausepunkt-merke.
PAUSE_TAGS = r"migrasjon|prod\b|secrets"
PAUSE_TITLE = r"migrasjon|deploy"

# Gamle release-tags fra før `release:`-feltet.
RELEASE_TAGS = ("release-1.1.0",)

# Tekst for en levert release. Overstyrer `goal` fra release-fila.
LEVERT = {"v1.1": "<strong>Levert 2026-01-01</strong>: første versjon."}

# Fargespor per release (1, 2 eller 3).
RELEASE_COLORS = {"v1.1": 2, "v1.2": 1}

SCOPE_NOTE = "Prod-migrasjoner kjøres av eieren."
RELEASE_NOTE = "Merk: <code>varsler</code> er et tema, ikke en release."

# Ekstra varsler under «Datakvalitet».
EKSTRA_FLAGG = [("Et flagg", "Forklaring på hva som må ryddes.")]

# Markdown-linjer om rekkefølge og historikk.
MERKNADER = ["12 går foran 14 fordi 14 leser den nye tabellen."]

# Betingede merknader: callable(todos, sh) -> [markdown-linje].
EKSTRA_MERKNADER = lambda todos, sh: [f"{len(todos)} åpne todos."]
