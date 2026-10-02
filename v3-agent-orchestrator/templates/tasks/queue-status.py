#!/usr/bin/env python3
"""Genererer tasks/queue-status.md — en LESEVISNING av køen slik §1-skriptet i
coordinator-runbook.md faktisk kjører den (prioritert først, så `order`), gruppert
etter epic, med et mermaid-diagram over rekkefølge, avhengigheter og parallelle løp.
Med `--html <sti>` skrives i tillegg køsiden (artefaktet i docs/superpowers/loop/artifacts.md).

Kilden til sannhet er fortsatt én fil per todo i tasks/todos/ (frontmatter). Denne fila
er avledet og overskrives; rediger aldri queue-status.md for hånd.

Kjør fra repo-roten (koordinatoren gjør det i hver §6-hale):
    python3 tasks/queue-status.py > tasks/queue-status.md
    python3 tasks/queue-status.py --html <scratchpad>/queue-status.html > tasks/queue-status.md
    python3 tasks/queue-status.py --print-title     # tittelen vakten i artifacts.md greper etter
    python3 tasks/queue-status.py --self-test

Fila er KIT-EID og lik i alle prosjekter (`tasks/kit-drift.py` melder avvik). Releaser, mål,
done_when, epics og fremdrift leses fra tasks/releases/ via release.py. Alt prosjektspesifikt
(tittel, eierskap, notater, klynger, leverte releaser, merknader) står i den valgfrie
`tasks/queue-config.py` — se kommentarene der. Uten den, eller med den tom, virker siden.
"""
import glob
import os
import pathlib
import re
import runpy
import subprocess
import sys

# tasks/ er sys.path[0] når skriptet kjøres som fil
from release import archived, done_when as _done_when_count, fm as _release_fm, releases
from datetime import datetime

# --- Prosjektkonfig (valgfri) ------------------------------------------------------------
# tasks/queue-config.py er vanlig Python. Hver nøkkel under har en standardverdi, så en tom
# eller manglende fil gir en fungerende side. Ukjente nøkler er en skrivefeil og stopper
# generatoren (fail-closed: en feilstavet nøkkel ville ellers blitt stille ignorert).
_CFG_PATH = pathlib.Path("tasks/queue-config.py")
_DEFAULTS = {
    "TITLE": "{{PROJECT_NAME}}-køen",       # <title> og <h1>; vakten i artifacts.md greper etter den
    "OWNER_NAME": "eier",                     # navnet på eier-pillen («hvem utenom loopen»)
    "BASE_REF": "origin/{{BASE_BRANCH}}",     # ref-en hvis SHA vises i toppen
    "AGENDA": {},             # {"tittel", "hvorfor", "punkter": [(tittel, tekst)]} — avtalt agenda
    "EIERSKAP": {},           # nr -> ("loop" | "eier", hva som må skje) for rader i aktiv/levert release
    "CLUSTERS": [],           # [(epic-navn, {nr, ...})] — eksplisitte nummer-sett, i visningsrekkefølge
    "EPIC_TAG_CLUSTER": {},   # tag eller epic-slug -> epic-navn
    "EPIC_FROM_FIELD": True,  # bruk todoens `epic:`-felt når nummeret ikke står i CLUSTERS
    "NOTES": {},              # nr -> to setninger om hva todoen gjelder (rendres under raden)
    "PAUSE_TAGS": r"migrasjon|migration|prod\b|edge-function|native|secrets|rls",
    "PAUSE_TITLE": r"migrasjon|edge function|oauth|prod-|deploy|native",
    "RELEASE_TAGS": (),       # gamle release-tags fra før `release:`-feltet, f.eks. ("release-1.2.0",)
    "LEVERT": {},             # "v1.2" -> HTML-tekst for en levert release (overstyrer goal fra release-fila)
    "RELEASE_COLORS": None,   # "v1.2" -> 1|2|3 (fargespor). None = aktiv release får spor 1
    "SCOPE_NOTE": "",         # ekstra setning under «Release <x> — scope» i markdown
    "RELEASE_NOTE": "",       # ekstra HTML-setning i ingressen til release-seksjonen
    "MERKNADER": [],          # markdown-linjer (uten «- ») om rekkefølge og historikk
    "EKSTRA_MERKNADER": None, # callable(todos, sh) -> [markdown-linje], for betingede merknader
    "EKSTRA_FLAGG": [],       # [(tittel-HTML, tekst-HTML)] — ekstra varsler under «Datakvalitet»
}


def _load_config():
    if not _CFG_PATH.exists():
        return dict(_DEFAULTS)
    ns = runpy.run_path(str(_CFG_PATH))
    mine = {k: v for k, v in ns.items() if k.isupper() and not k.startswith("_")}
    unknown = sorted(set(mine) - set(_DEFAULTS))
    if unknown:
        sys.exit(f"FEIL: ukjent nøkkel i {_CFG_PATH}: {', '.join(unknown)}. "
                 f"Kjente nøkler: {', '.join(_DEFAULTS)}")
    return {**_DEFAULTS, **mine}


def _self_test():
    """Kjører generatoren i et midlertidig repo med fixture-todoer. Exit 0 = alt grønt."""
    import shutil
    import tempfile
    here = os.path.dirname(os.path.abspath(__file__))
    fails = []

    def todo(nr, **kv):
        fmx = "\n".join(f"{k}: {v}" for k, v in {"nr": f'"{nr}"', "status": "open", "priority": "normal",
                                                 "order": "100", "claimed_by": "null", **kv}.items())
        return f"---\n{fmx}\n---\n\nBrødtekst.\n"

    def run(files, *args):
        tmp = tempfile.mkdtemp()
        try:
            os.makedirs(f"{tmp}/tasks/todos")
            os.makedirs(f"{tmp}/tasks/releases")
            for f in ("release.py", "queue-status.py"):
                shutil.copy(os.path.join(here, f), f"{tmp}/tasks/{f}")
            for rel, txt in files.items():
                open(f"{tmp}/{rel}", "w", encoding="utf-8").write(txt)
            r = subprocess.run([sys.executable, "tasks/queue-status.py", *args], cwd=tmp,
                               capture_output=True, text=True)
            html = open(f"{tmp}/q.html", encoding="utf-8").read() if os.path.exists(f"{tmp}/q.html") else ""
            title = subprocess.run([sys.executable, "tasks/queue-status.py", "--print-title"], cwd=tmp,
                                   capture_output=True, text=True).stdout.strip()
            return r.returncode, r.stdout, r.stderr, html, title
        finally:
            shutil.rmtree(tmp)

    def check(name, cond):
        print(("ok   " if cond else "FEIL ") + name)
        if not cond:
            fails.append(name)

    rel = ('---\nstatus: active\ngoal: "Brukeren kan gjøre X"\ncutoff: ""\n---\n\n## done_when\n\n'
           '- [x] Første\n- [ ] Andre\n\n## Epics\n\n- `grunnmur` — bunnen\n')
    base = {
        "tasks/releases/1.2.0.md": rel,
        "tasks/todos/todo-1.md": todo("1", title='"Første"', release='"1.2.0"', epic="grunnmur", effort="S"),
        "tasks/todos/todo-2.md": todo("2", title='"Andre"', release='"1.2.0"', deps='["1"]'),
        "tasks/todos/todo-3.md": todo("3", title='"Tredje"', status="deferred", tags="[forslag]"),
        "tasks/todos/todo-4.md": todo("4", title='"Fjerde"', tags="[release-1.1.0]"),
        "tasks/todo_archive.md": ("# Arkiv\n\n## TODO 9 — Ferdig\n\n**Release:** 1.2.0\n**Epic:** grunnmur\n"
                                  "\n## TODO-7 — Bindestrek-format\n\n## TODO 6C3a — Langt suffiks\n\n## todo-8 — Små bokstaver\n"),
        "tasks/todos/todo-6.md": todo("6", title='"Sjette"', deps='["7", "6C3a", "8"]'),
    }

    # 1. Uten queue-config.py: siden virker, tittelen er standardtittelen, vaktene i artifacts.md slår til.
    rc, md, err, html, title = run(base, "--html", "q.html")
    check("uten config: exit 0", rc == 0 and not err.strip())
    check("uten config: tittel-vakten (nøyaktig én <title>)",
          title.endswith("-køen") and html.count(f"<title>{title}</title>") == 1)
    check("uten config: aktiv release-vakten (versjonen fra release.py status står i HTML-en)",
          "1.2.0" in html and "## Release 1.2.0 — scope" in md)
    check("uten config: epic fra `epic:`-feltet", 'class="epic-t">grunnmur<' in html)
    check("uten config: levert-telling fra arkivet", "1<small>levert</small>" in html)
    check("uten config: done_when 1/2", "(1/2)</summary>" in html)
    check("uten config: ingen merknader-seksjon", "## Merknader" not in md)
    check("arkiv: `## TODO-7`, `TODO 6C3a` og `## todo-8` teller som ferdige deps", "deps 7✓, 6C3a✓, 8✓" in md and "⚠ukjent" not in md)

    # 2. Full config: nøklene slår gjennom.
    cfg = "\n".join([
        'TITLE = "Testkøen"',
        'OWNER_NAME = "Kari"',
        'EIERSKAP = {"2": ("eier", "Kari må godkjenne.")}',
        'CLUSTERS = [("Klynge A", {"1", "2"})]',
        'NOTES = {"1": "Et notat om 1."}',
        'RELEASE_TAGS = ("release-1.1.0",)',
        'LEVERT = {"v1.1": "<strong>Levert 2026-01-01</strong>: første versjon."}',
        'RELEASE_COLORS = {"v1.1": 2, "v1.2": 1}',
        'MERKNADER = ["En merknad."]',
        'EKSTRA_MERKNADER = lambda todos, sh: [f"{len(todos)} todos."]',
        'EKSTRA_FLAGG = [("Et flagg", "Forklaring.")]',
        'SCOPE_NOTE = "Prod eies av Kari."',
        'RELEASE_NOTE = "Merk: noe."',
    ]) + "\n"
    rc, md, err, html, title = run({**base, "tasks/queue-config.py": cfg}, "--html", "q.html")
    check("full config: exit 0", rc == 0 and not err.strip())
    check("full config: TITLE", title == "Testkøen" and html.count("<title>Testkøen</title>") == 1)
    check("full config: eier-pill og begrunnelse", ">Kari</span>" in html and "Kari må godkjenne." in html)
    check("full config: CLUSTERS", 'class="epic-t">Klynge A<' in html)
    check("full config: NOTES", "Et notat om 1." in html)
    check("full config: LEVERT + gammel tag", "v1.1 · levert" in html and "første versjon." in html)
    check("full config: RELEASE_COLORS", ".relp.v1-1{background:var(--rel2-wash)" in html)
    check("full config: merknader", "- En merknad." in md and "- 5 todos." in md and "En merknad." in html)
    check("full config: EKSTRA_FLAGG", "<b>Et flagg</b>" in html)
    check("full config: SCOPE_NOTE og RELEASE_NOTE", "Prod eies av Kari." in md and "Merk: noe." in html)

    # 3. Feilstavet nøkkel stopper generatoren.
    rc, md, err, html, title = run({**base, "tasks/queue-config.py": "TITEL = 'x'\n"})
    check("ukjent nøkkel: exit ≠ 0 med melding", rc != 0 and "ukjent nøkkel" in err and "TITEL" in err)

    # 4. Ingen aktiv release, og en levert release-fil med `shipped:`.
    shipped = '---\nstatus: shipped\nshipped: "2026-02-03"\ngoal: "Første mål"\n---\n'
    rc, md, err, html, title = run({**base, "tasks/releases/1.2.0.md": shipped}, "--html", "q.html")
    check("ingen aktiv: exit 0", rc == 0 and not err.strip())
    check("ingen aktiv: sier det, uten aktiv-pille og tellere",
          "ingen aktiv release" in html and "hele køen er kvalifisert" in md and "todos igjen" not in html)
    check("shipped-fil: levert-bane med dato og mål",
          "v1.2 · levert" in html and "Levert 2026-02-03" in html and "Første mål" in html)

    # 5. To aktive releaser: siden rendres, og sier at bare én er lov.
    rc, md, err, html, title = run({**base, "tasks/releases/1.3.0.md": rel}, "--html", "q.html")
    check("to aktive: exit 0 og advarsel", rc == 0 and "bare én er lov" in html and "FEIL: flere aktive" in md)

    # 6. Planlagt release får egen bane.
    planned = '---\nstatus: planned\ngoal: "Neste mål"\n---\n'
    rc, md, err, html, title = run({**base, "tasks/releases/1.3.0.md": planned,
                                    "tasks/todos/todo-5.md": todo("5", title='"Femte"', release='"1.3.0"')},
                                   "--html", "q.html")
    check("planlagt: egen bane", rc == 0 and "v1.3 · planlagt" in html and "Neste mål" in html)

    print("SELF-TEST " + ("GRØNN" if not fails else f"RØD ({len(fails)} feil)"))
    return 0 if not fails else 1


if "--self-test" in sys.argv:
    sys.exit(_self_test())


CFG = _load_config()
TITLE = CFG["TITLE"]
OWNER_NAME = CFG["OWNER_NAME"]
AGENDA = CFG["AGENDA"]
EIERSKAP = CFG["EIERSKAP"]
CLUSTERS = CFG["CLUSTERS"]
EPIC_TAG_CLUSTER = CFG["EPIC_TAG_CLUSTER"]
NOTES = CFG["NOTES"]
RELEASE_TAGS = tuple(CFG["RELEASE_TAGS"])

if "--print-title" in sys.argv:
    print(TITLE)
    sys.exit(0)

PAUSE_TAGS = re.compile(CFG["PAUSE_TAGS"], re.I)


def fm(path):
    """release.py sin frontmatter-parser (samme regel i §1, release.py og her) + brainstorm-flagget."""
    d = _release_fm(path)
    d["_brainstorm"] = bool(
        re.search(r"krever[^.\n]*brainstorm|brainstorm\s+f.?r\s+plan|spec\s+f.?r\s+plan", d["_body"], re.I)
    )
    return d


def as_int(v, default=9999):
    try:
        return int(v)
    except (ValueError, TypeError):
        return default


def sh(cmd):
    try:
        return subprocess.check_output(cmd, shell=True, text=True, stderr=subprocess.DEVNULL).strip()
    except subprocess.CalledProcessError:
        return "?"


todos = {}
for p in glob.glob("tasks/todos/todo-*.md"):
    d = fm(p)
    if d.get("nr"):
        todos[d["nr"]] = d


def deps_of(d):
    return re.findall(r'"([^"]+)"', d.get("deps", "") or "")


# Arkiverte todos har ingen fil i tasks/todos/ — de teller som ferdige. En dep som verken
# finnes som fil ELLER i arkivet er en SKRIVEFEIL, og skal ikke lese som ferdig: den gamle
# `f is None -> True` var fail-open og gjorde enhver typo til en grønn hake.
_ARCHIVE = pathlib.Path("tasks/todo_archive.md")
_archived = set(
    re.findall(r"TODO[\s-]+([0-9]+[0-9A-Za-z]*)", _ARCHIVE.read_text(encoding="utf-8"), re.I)
    if _ARCHIVE.exists()
    else []
)


def dep_known(nr):
    return nr in todos or nr in _archived


def dep_done(nr):
    f = todos.get(nr)
    if f is not None:
        return f.get("status") == "done"
    return nr in _archived


def lane_key(version):
    """Banenøkkel for en release-versjon: "1.15.0" -> "v1.15", "2.0.0" -> "v2.0"."""
    return "v" + version.removesuffix(".0")


def lane_sort(k):
    """Sorterer banenøkler numerisk ("v1.9" før "v1.10")."""
    return tuple(int(x) if x.isdigit() else x for x in re.findall(r"\d+|[^\d.]+", k))


# Releasene fra tasks/releases/ via release.py. Samme filter som §1: med én aktiv release er bare
# todoer med `release: <versjon>` kvalifisert. Uten aktiv release-fil gjelder hele køen.
RELS = releases()
_ACTIVE = sorted(v for v, r in RELS.items() if r.get("status") == "active")
REL = _ACTIVE[0] if len(_ACTIVE) == 1 else None
NOW = lane_key(REL) if REL else None  # banenøkkel for aktiv release, f.eks. "v1.15"
_REL_TXT = RELS[REL]["_body"] if REL else ""
REL_GOAL = RELS[REL].get("goal", "") if REL else ""
REL_DONE_WHEN = re.findall(r"^\s*- \[([ xX])\] (.+)$", _REL_TXT.split("## done_when", 1)[-1].split("\n## ", 1)[0], re.M) if REL else []
# Epicene i rekkefølgen release-fila lister dem (`- `navn` …` under ## Epics).
REL_EPICS = re.findall(r"^- `([^`]+)`", _REL_TXT.split("## Epics", 1)[-1].split("\n## ", 1)[0], re.M) if REL else []
# Leverte releaser: release-filer med `status: shipped` + de config-en beskriver i LEVERT
# (releaser fra før tasks/releases/ fantes har ingen fil).
SHIPPED = {lane_key(v): r for v, r in RELS.items() if r.get("status") == "shipped"}
SHIPPED_KEYS = sorted(set(SHIPPED) | set(CFG["LEVERT"]), key=lane_sort, reverse=True)
PLANNED_KEYS = sorted((lane_key(v) for v, r in RELS.items() if r.get("status") == "planned"), key=lane_sort)


def eligible(d):
    return (
        d.get("status") in ("open", "reviewed")
        and d.get("claimed_by", "null") in ("null", "", None)
        and not d["_brainstorm"]
        and all(dep_done(x) for x in deps_of(d))
        and not re.search(r"\bforslag\b|\bprod-release\b", d.get("tags", "") or "")
        and (REL is None or d.get("release") == REL)
    )


def cluster_of(nr, tags=""):
    """Epic-navnet en todo vises under. Første treff vinner:
    1. nummeret står i et CLUSTERS-sett (config),
    2. todoens `epic:`-felt (når EPIC_FROM_FIELD), oversatt via EPIC_TAG_CLUSTER hvis slugen står der,
    3. en tag som står i EPIC_TAG_CLUSTER,
    ellers «Uklassifisert»."""
    for name, members in CLUSTERS:
        if nr in members:
            return name
    epic = (todos.get(nr) or {}).get("epic") or ""
    if CFG["EPIC_FROM_FIELD"] and epic not in ("", "null", "-"):
        return EPIC_TAG_CLUSTER.get(epic, epic)
    for tag in re.findall(r"[\w-]+", tags or ""):
        if tag in EPIC_TAG_CLUSTER:
            return EPIC_TAG_CLUSTER[tag]
    return "Uklassifisert"


def key(d):
    return (0 if d.get("priority") == "prioritert" else 1, as_int(d.get("order")), d.get("nr"))


def short_title(d, n=70):
    t = d.get("title", "") or ""
    t = re.sub(r"^(Loop|Fix|TODO)\s*[:—-]\s*", "", t).replace('"', "'")
    return t if len(t) <= n else t[: n - 1] + "…"


def deps_str(d):
    ds = deps_of(d)
    if not ds:
        return ""
    parts = []
    for x in ds:
        parts.append(f"{x}✓" if dep_done(x) else (x if dep_known(x) else f"{x}⚠ukjent"))
    return " (deps " + ", ".join(parts) + ")"


PAUSE_TITLE = re.compile(CFG["PAUSE_TITLE"], re.I)


def in_release(d):
    # release_of gir None for `split` (foreldre-rad, ellers telt tre ganger) og `done` (TODO 238).
    return NOW is not None and release_of(d) == NOW


def release_of(d):
    """Banenøkkelen til releasen en todo hører til, eller None.

    Feltet `release:` går foran gamle `release-x.y.z`-tags (RELEASE_TAGS i config). `split`
    (foreldre-rad, ellers telt flere ganger) og `done` hører ikke til noen bane.
    """
    if d.get("status") in ("split", "done"):
        return None
    if d.get("release"):
        return lane_key(d["release"])
    tags = d.get("tags", "") or ""
    for rt in RELEASE_TAGS:
        if rt in tags:
            return lane_key(rt.removeprefix("release-"))
    return None


def release_hint(d):
    r = release_of(d)
    if r is None:
        return ""
    if r == NOW:
        return " 🚀"
    return " ✅" if r in SHIPPED_KEYS else f" ⟶{r}"


def release_oversikt(todos):
    """Kort blokk øverst: hvor mange todos i hver release, og hvilke."""
    buckets = {}
    for d in todos:
        r = release_of(d)
        if r:
            buckets.setdefault(r, []).append(d)
    if not buckets:
        return []
    ut = ["", "## Release-fordeling", ""]
    for r in sorted(buckets):
        rader = buckets[r]
        eff = {}
        for d in rader:
            eff[effort_of(d) or "?"] = eff.get(effort_of(d) or "?", 0) + 1
        sum_eff = ", ".join(f"{v}x{k}" for k, v in sorted(eff.items()))
        nrs = ", ".join(sorted((d.get("nr", "?") for d in rader), key=lambda x: (len(x), x)))
        ut.append(f"- **{r}** — {len(rader)} todos ({sum_eff}): {nrs}")
    ut.append("")
    ut.append(
        "Todos uten release-tag er ikke i noen planlagt release. `split`- og `done`-rader "
        "telles ikke: del-todoene bærer samme tag, og foreldre-raden ville doblet tellingen."
    )
    ut.append("")
    return ut


EFFORT_OK = ("S", "M", "L")


def effort_of(d):
    """Returnerer '', 'S'/'M'/'L', eller sammensatt '<kode>/<verifisering>' (f.eks. 'S/M').

    Den sammensatte formen skrives av koordinatoren når en plan har fått `go` i §4 — da er
    begge halvdelene målt mot en ferdig plan, ikke anslått. Ukjent form ⇒ '' (rendres som '?'),
    aldri en stille feiltolkning.
    """
    e = (d.get("effort") or "").strip().strip('"').split("#")[0].strip()
    if e in EFFORT_OK:
        return e
    parts = [x.strip() for x in e.split("/")]
    if len(parts) == 2 and all(x in EFFORT_OK for x in parts):
        return "/".join(parts)
    return ""


def effort_rank(e):
    """Tyngste halvdel styrer fargen: en S/M er ikke en S."""
    return max((EFFORT_OK.index(x) for x in e.split("/") if x in EFFORT_OK), default=-1)


def effort_md(d):
    e = effort_of(d)
    return f" · `{e}`" if e else " · `?`"


def effort_html(d):
    e = effort_of(d)
    cls = {0: "eff-s", 1: "eff-m", 2: "eff-l"}.get(effort_rank(e), "eff-x")
    title = ("kode/verifisering — målt mot ferdig plan" if "/" in e else "implementeringskost")
    return f'<span class="pill {cls}" title="{title}">{e or "?"}</span>'


def is_pause(d):
    return bool(PAUSE_TAGS.search(d.get("tags", "") or "") or PAUSE_TITLE.search(d.get("title", "") or ""))


def pause_hint(d):
    return " ⏸" if is_pause(d) else ""


now = datetime.now().strftime("%Y-%m-%d %H:%M")
BASE_REF = CFG["BASE_REF"]
dev_sha = sh(f"git rev-parse --short {BASE_REF}")
in_progress = sorted((d for d in todos.values() if d.get("status") == "in_progress"), key=key)
# Todos som HAR en planfil men ikke er claimet. Dette er IKKE "i arbeid" — noen av dem er
# deps-blokkerte, andre står bare i køen med en ferdig plan. Frontmatteren kan ikke vite hvilket
# B-spor koordinatoren faktisk kjører nå, så vi påstår det ikke.
plan_ready = sorted(
    (d for d in todos.values() if d.get("status") in ("open", "reviewed") and (d.get("plan") or "null") not in ("null", "")),
    key=key,
)
queue = sorted((d for d in todos.values() if d.get("status") in ("open", "reviewed")), key=key)
deferred = sorted((d for d in todos.values() if d.get("status") == "deferred"), key=key)

out = []
w = out.append
w("<!-- GENERERT av tasks/queue-status.py — ikke rediger for hånd. Kilden er tasks/todos/*.md. -->")
w("# Kø-status (lesevisning)")
w("")
w(f"**Generert:** {now} · **{BASE_REF}:** `{dev_sha}` · regenerer med "
  "`python3 tasks/queue-status.py > tasks/queue-status.md`")
w("")
w("Rekkefølgen under er nøyaktig den §1-skriptet i `coordinator-runbook.md` velger fra: "
  "`prioritert` først, deretter `order`. `elig` = kan claimes nå (åpen, u-claimet, alle deps arkivert, "
  "ikke `forslag`). ⏸ = tags som typisk gir et kontrakt-pausepunkt (migrasjon/RLS/Edge/prod/native/secrets).")
w("")
if AGENDA and AGENDA.get("punkter"):
    w("## \u23f0 Avtalt agenda \u2014 " + AGENDA["tittel"])
    w("")
    w("> " + AGENDA["hvorfor"])
    w("")
    for tittel, tekst in AGENDA["punkter"]:
        w(f"- **{tittel}** \u2014 {tekst}")
    w("")

if REL or len(_ACTIVE) > 1:
    _r = subprocess.run([sys.executable, "tasks/release.py", "status"], capture_output=True, text=True)
    w("## Release-mål")
    w("")
    for _linje in (_r.stdout or _r.stderr).splitlines():
        w("> " + _linje + "  ")
    w("")

for _linje in release_oversikt(list(todos.values())):
    w(_linje)

w("## I arbeid nå")
w("")
if not in_progress:
    w("- (ingenting claimet)")
for d in in_progress:
    w(f"- **TODO {d['nr']}** — {short_title(d)} — `in_progress`, claimet av `{d.get('claimed_by')}`"
      f"{', plan `' + d['plan'] + '`' if d.get('plan') not in (None, '', 'null') else ''}")
    if NOTES.get(d['nr']):
        w(f"  - {NOTES[d['nr']]}")
w("")
if plan_ready:
    w("## Plan finnes, men ikke claimet")
    w("")
    w("Disse er **ikke** i arbeid. De har en ferdig planfil — noen fra et tidligere pipelinet "
      "B-spor, noen fra en plan-review som ga `go` uten at todoen ble claimet med én gang. "
      "`venter` betyr at minst én dep fortsatt er åpen.")
    w("")
    for d in plan_ready:
        blocked = [x for x in deps_of(d) if not dep_done(x)]
        state = ("venter på " + ", ".join(blocked)) if blocked else "klar til å claimes"
        w(f"- **TODO {d['nr']}** — {short_title(d)} — {state} (`status: {d.get('status')}`): `{d.get('plan')}`")
        if NOTES.get(d['nr']):
            w(f"  - {NOTES[d['nr']]}")
    w("")
rel_md = sorted([d for d in todos.values() if in_release(d)],
                key=lambda d: (0 if d.get("priority") == "prioritert" else 1, as_int(d.get("order")), d["nr"]))
w(f"## Release {REL or '(ingen aktiv)'} — scope")
w("")
if REL:
    w(f"Scopet er feltet `release:` i todo-fila, og målet står i `tasks/releases/{REL}.md`. Samme filter som §1."
      + (" " + CFG["SCOPE_NOTE"] if CFG["SCOPE_NOTE"] else ""))
else:
    w("Ingen release i `tasks/releases/` har `status: active`, så hele køen er kvalifisert (§1).")
w("")
for d in rel_md:
    st = "deferred" if d.get("status") == "deferred" else ("elig" if eligible(d) else "venter")
    w(f"- **TODO {d['nr']}** — {short_title(d)}{pause_hint(d)}{effort_md(d)} · `{st}` · order {as_int(d.get('order'))}")
w("")
w(f"**{len(rel_md)} todos i scope.**")
w("")
w("## Køen slik §1 kjører den")
w("")
n = 0
cur = None
first_normal = True
for d in queue:
    if d.get("status") not in ("open", "reviewed") or d in in_progress:
        continue
    if d.get("priority") != "prioritert" and first_normal:
        w("")
        w("> Her slutter `prioritert`. Resten er `normal`.")
        w("")
        first_normal = False
        cur = None
    c = cluster_of(d["nr"], d.get("tags", ""))
    if c != cur:
        w("")
        w(f"**{c}**")
        w("")
        cur = c
    n += 1
    flag = "elig" if eligible(d) else "venter"
    pipe = " — *plan skrevet*" if d in plan_ready else ""
    w(f"{n}. TODO {d['nr']} — {short_title(d)}{deps_str(d)}{pause_hint(d)}{release_hint(d)}{effort_md(d)} · `{flag}` · order {as_int(d.get('order'))}{pipe}")
    if NOTES.get(d['nr']):
        w(f"   - {NOTES[d['nr']]}")
w("")
w("## Deferred (ikke i køen)")
w("")
prop = [d["nr"] for d in deferred if re.search(r"\bforslag\b", d.get("tags", "") or "")]
rest = [d["nr"] for d in deferred if d["nr"] not in prop]
w(f"- U-triagerte grooming-forslag (`tags: [forslag]`): {', '.join(prop) or '—'}")
w(f"- Bevisst utsatt: {', '.join(rest) or '—'}")
w("")
w("## Diagram — rekkefølge, avhengigheter og parallelle løp")
w("")
w("Klyngene kjøres i køens rekkefølge (ovenfra og ned). Piler inne i en klynge er `deps`; "
  "todos uten pil mellom seg kan gå i vilkårlig rekkefølge innenfor klyngen. "
  "Stiplet = pausepunkt-kandidat (menneskets go).")
w("")
w("```mermaid")
w("flowchart TB")
open_nrs = {d["nr"] for d in queue}
cluster_order = []
for d in queue:
    if d in in_progress:
        continue
    c = cluster_of(d["nr"], d.get("tags", ""))
    if c not in cluster_order:
        cluster_order.append(c)
cid = {c: f"C{i}" for i, c in enumerate(cluster_order)}
for c in cluster_order:
    w(f'  subgraph {cid[c]}["{c}"]')
    w("    direction TB")
    for d in queue:
        if d in in_progress or cluster_of(d["nr"], d.get("tags", "")) != c:
            continue
        label = f"{d['nr']}"
        w(f'    T{d["nr"]}["{label} {short_title(d, 34)}"]')
    w("  end")
for d in queue:
    if d in in_progress:
        continue
    for x in deps_of(d):
        if x in open_nrs:
            w(f"  T{x} --> T{d['nr']}")
for a, b in zip(cluster_order, cluster_order[1:]):
    w(f"  {cid[a]} ==> {cid[b]}")
for d in queue:
    if d in in_progress:
        continue
    if is_pause(d):
        w(f"  style T{d['nr']} stroke-dasharray: 5 5")
for d in in_progress:
    w(f'  A{d["nr"]}(["I arbeid: {d["nr"]} {short_title(d, 30)}"]):::now')
if in_progress and cluster_order:
    w(f"  A{in_progress[0]['nr']} ==> {cid[cluster_order[0]]}")
w("  classDef now fill:#ffe8a3,stroke:#b8860b")
w("```")
w("")
w("### Parallelle løp i én loop-runde (§5c pipelining, `max_in_flight: 1`)")
w("")
w("```mermaid")
w("flowchart TB")
w('  subgraph P1["Par 1 (samtidig)"]')
w('    I["implementer(A)"]')
w('    PL["planner(B)"]')
w("  end")
w('  subgraph P2["Par 2 (samtidig)"]')
w('    CR["kode-reviewer(A)"]')
w('    PR["plan-reviewer(B)"]')
w("  end")
w('  V["koordinator: e2e V-rader(A) + plan-commit(B)"]')
w('  M["§6 merge(A) → A := B"]')
w("  I --> V --> CR")
w("  PL --> V --> PR")
w("  CR --> M")
w("  PR --> M")
w('  M -. "fix-runde(A) ∥ revisjonsrunde(B) pares likt" .-> P1')
w("```")
w("")
# Prosjektets egne merknader (config). Seksjonen utelates når det ikke finnes noen.
_merk = list(CFG["MERKNADER"])
if CFG["EKSTRA_MERKNADER"]:
    _merk += list(CFG["EKSTRA_MERKNADER"](todos, sh))
if _merk:
    w("## Merknader")
    w("")
    for _m in _merk:
        w("- " + _m)
sys.stdout.write("\n".join(out) + "\n")


# ---------------------------------------------------------------------------
# HTML-utgang (valgfri): `python3 tasks/queue-status.py --html <sti>` skriver i
# tillegg en selvstendig HTML-side med samme innhold (lesbar i claude.ai-appen på
# iOS via Artifact). Ren avledning av dataene over — ingen egen sannhet.
# ---------------------------------------------------------------------------
if "--html" in sys.argv:
    import html as _h
    import json as _json

    hpath = sys.argv[sys.argv.index("--html") + 1]

    def inl(s):
        """Minimal markdown-inline → HTML: `kode`, **fet**."""
        s = _h.escape(s)
        s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
        s = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", s)
        return s

    def deps_html(d):
        ds = deps_of(d)
        if not ds:
            return ""
        parts = [
            f'{x}<span class="done">✓</span>' if dep_done(x)
            else (x if dep_known(x) else f'{x}<span class="warn">⚠ukjent</span>')
            for x in ds
        ]
        return '<span class="deps">deps ' + ", ".join(parts) + "</span>"

    def slug(s):
        s = s.lower()
        s = (s.replace("æ", "ae").replace("ø", "o").replace("å", "a"))
        return re.sub(r"[^a-z0-9]+", "-", s).strip("-") or "x"

    # --- Tilstand: ÉN funksjon, brukt overalt. Fire verdier, ingen femte. ---
    def state_of(d):
        if d in in_progress:
            return "arbeid"
        if d.get("status") == "deferred":
            return "utsatt"
        return "klar" if eligible(d) else "venter"

    STATE_LABEL = {"arbeid": "i arbeid", "klar": "kan claimes", "venter": "venter", "utsatt": "utsatt"}

    def state_pill(d):
        s = state_of(d)
        return f'<span class="pill st-{s}">{STATE_LABEL[s]}</span>'

    def plan_state(d):
        """Plan-status for en todo: godkjent (status reviewed), utkast (plan finnes, ikke godkjent)
        eller ingen. Leses av banen for aktiv release — der er nettopp plan-status det som skiller radene."""
        har_plan = (d.get("plan") or "null") not in ("null", "", None)
        if not har_plan:
            return "ingen"
        return "godkjent" if d.get("status") == "reviewed" else "utkast"

    PLAN_PILL = {"godkjent": ("st-klar", "plan godkjent"),
                 "utkast": ("st-venter", "plan til godkjenning"),
                 "ingen": ("st-utsatt", "ingen plan")}

    def plan_html(d):
        cls, label = PLAN_PILL[plan_state(d)]
        return f'<span class="pill {cls}" title="plan-status">{label}</span>'

    def rel_of(d):
        return release_of(d) or "ingen"

    # Alt som ikke er arkivert eller en foreldre-rad. Dette er populasjonen hele siden teller.
    levende = [d for d in todos.values() if d.get("status") not in ("done", "split")]

    # ---------------- Release-baner ----------------
    lanes = {}
    for d in levende:
        lanes.setdefault(rel_of(d), []).append(d)
    for k in lanes:
        lanes[k].sort(key=key)
    # Alle kjente releaser (filer, gamle tags, LEVERT og det todoene peker på) — filterknappene.
    ALL_KEYS = sorted(
        ({lane_key(v) for v in RELS} | {lane_key(t.removeprefix("release-")) for t in RELEASE_TAGS}
         | set(CFG["LEVERT"]) | set(lanes)) - {"ingen"}, key=lane_sort)
    # Fargespor per release (1–3). Standard: aktiv release spor 1, planlagte spor 2.
    if CFG["RELEASE_COLORS"] is not None:
        REL_COLORS = dict(CFG["RELEASE_COLORS"])
    else:
        REL_COLORS = {k: 2 for k in PLANNED_KEYS}
        if NOW:
            REL_COLORS[NOW] = 1
    REL_CSS = "\n".join(
        f".row.{slug(k)}{{box-shadow:inset 3px 0 0 var(--rel{n})}}\n"
        f".relp.{slug(k)}{{background:var(--rel{n}-wash);color:var(--rel{n})}}"
        for k, n in sorted(REL_COLORS.items(), key=lambda kv: lane_sort(kv[0])))

    # ---------------- Epics ----------------
    epics = {}
    for d in levende:
        c = cluster_of(d["nr"], d.get("tags", ""))
        epics.setdefault(c, []).append(d)
    for v in epics.values():
        v.sort(key=key)
    # Rekkefølge: epics med arbeid i aktiv release først, så størst først, «Uklassifisert» sist.
    def epic_rank(item):
        name, mem = item
        i_aktiv = any(rel_of(x) == NOW for x in mem)
        return (0 if i_aktiv else 1, 1 if name == "Uklassifisert" else 0, -len(mem), name)
    epic_order = sorted(epics.items(), key=epic_rank)

    # ---------------- Datakvalitet: felter §1 ikke forstår ----------------
    PRI_KJENT = ("normal", "prioritert")
    pri_avvik = [d for d in levende if (d.get("priority") or "").strip().strip('"') not in PRI_KJENT]
    uten_effort = [d for d in levende if not effort_of(d)]
    forslag = [d for d in levende if re.search(r"\bforslag\b", d.get("tags", "") or "")]
    uklassifisert = epics.get("Uklassifisert", [])

    h = []
    a = h.append
    a(f"<title>{_h.escape(TITLE)}</title>")
    a('<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap">')
    a("""<style>
:root{
  --bg:#F6F7F4;--surface:#FFFFFF;--sunk:#EFF1EC;--ink:#1D2320;--muted:#5E6862;--faint:#8A948D;
  --line:#D9DED8;--line-soft:#E7EAE4;--accent:#0F6E6E;--accent-ink:#0B5252;--accent-wash:#E2EFEE;
  --klar-bg:#E3F2E9;--klar-ink:#1F7F4F;
  --venter-bg:#F7EED3;--venter-ink:#7A5200;
  --utsatt-bg:#E9EBE7;--utsatt-ink:#6B7369;
  --arbeid-bg:#FFF3D1;--arbeid-ink:#8A6100;
  --pause-bg:#F4E0DA;--pause-ink:#8A3B2E;
  --rel1:#0F6E6E;--rel1-wash:#E2EFEE;--rel2:#5B4B9E;--rel2-wash:#EAE6F7;--rel3:#6B7A8F;--rel3-wash:#E8EBEF;
  --eier:#A8541F;--eier-wash:#F8E9DC;--on-accent:#FFFFFF;
}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){
  --bg:#14181A;--surface:#1C2124;--sunk:#191E20;--ink:#E4E8E3;--muted:#9AA59D;--faint:#6F7A73;
  --line:#2E3538;--line-soft:#242A2D;--accent:#4FB3B0;--accent-ink:#7FD1CE;--accent-wash:#17302F;
  --klar-bg:#1B3327;--klar-ink:#6FCB95;
  --venter-bg:#3A2F12;--venter-ink:#E4B95A;
  --utsatt-bg:#242A26;--utsatt-ink:#8D978F;
  --arbeid-bg:#3A3118;--arbeid-ink:#E8C46B;
  --pause-bg:#3B221D;--pause-ink:#E5917F;
  --rel1:#4FB3B0;--rel1-wash:#17302F;--rel2:#B3A6EA;--rel2-wash:#262039;--rel3:#9BAAB9;--rel3-wash:#222A30;
  --eier:#E0A472;--eier-wash:#332217;--on-accent:#10201F;
}}
:root[data-theme="dark"]{
  --bg:#14181A;--surface:#1C2124;--sunk:#191E20;--ink:#E4E8E3;--muted:#9AA59D;--faint:#6F7A73;
  --line:#2E3538;--line-soft:#242A2D;--accent:#4FB3B0;--accent-ink:#7FD1CE;--accent-wash:#17302F;
  --klar-bg:#1B3327;--klar-ink:#6FCB95;
  --venter-bg:#3A2F12;--venter-ink:#E4B95A;
  --utsatt-bg:#242A26;--utsatt-ink:#8D978F;
  --arbeid-bg:#3A3118;--arbeid-ink:#E8C46B;
  --pause-bg:#3B221D;--pause-ink:#E5917F;
  --rel1:#4FB3B0;--rel1-wash:#17302F;--rel2:#B3A6EA;--rel2-wash:#262039;--rel3:#9BAAB9;--rel3-wash:#222A30;
  --eier:#E0A472;--eier-wash:#332217;--on-accent:#10201F;
}
*{box-sizing:border-box}
body{background:var(--bg);color:var(--ink);font:15px/1.5 "IBM Plex Sans",system-ui,-apple-system,sans-serif;margin:0}
main{max-width:1040px;margin:0 auto;padding:26px 18px 72px}
.mono,code{font-family:"IBM Plex Mono",ui-monospace,Menlo,monospace}
code{font-size:.9em;background:var(--sunk);border:1px solid var(--line-soft);border-radius:4px;padding:0 4px}
a{color:var(--accent-ink)}
h1{font-size:27px;font-weight:600;letter-spacing:-.015em;margin:0;text-wrap:balance}
.meta{color:var(--muted);font-size:12.5px;display:flex;flex-wrap:wrap;gap:4px 16px;margin-top:7px}
.eyebrow{font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.09em;color:var(--faint);margin:0 0 10px}
h2{font-size:19px;font-weight:600;letter-spacing:-.01em;margin:0 0 3px;text-wrap:balance}
section{margin-top:38px}
.sub{color:var(--muted);font-size:13.5px;max-width:66ch;margin:0 0 16px;line-height:1.55}

/* ---------- Release-baner ---------- */
.lanes{display:grid;grid-template-columns:1fr;gap:14px}
.lane{background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:15px 16px;display:flex;flex-direction:column;gap:12px}
.lane-now{border-color:var(--rel3);box-shadow:inset 3px 0 0 var(--rel3)}
.lane-side{display:grid;gap:14px;align-content:start}
.lane-head{display:flex;align-items:baseline;justify-content:space-between;gap:10px}
.lane-tag{font:600 12px/1 "IBM Plex Mono",monospace;letter-spacing:.04em;padding:4px 8px;border-radius:5px}
.r-now{background:var(--rel3-wash);color:var(--rel3)}
.r-ingen{background:var(--sunk);color:var(--muted)}
.lane-name{font-size:13px;color:var(--muted)}
.lane-n{font:600 25px/1 "IBM Plex Mono",monospace;font-variant-numeric:tabular-nums}
.lane-n small{font:400 12px/1 "IBM Plex Sans",sans-serif;color:var(--muted);margin-left:5px}
.owner-h{display:flex;align-items:center;gap:7px;font-size:11.5px;font-weight:600;text-transform:uppercase;letter-spacing:.07em;color:var(--muted);margin:2px 0 0}
.owner-h::after{content:"";flex:1;height:1px;background:var(--line-soft)}
.dot{width:7px;height:7px;border-radius:50%;flex:none}
.dot-loop{background:var(--accent)}.dot-eier{background:var(--eier)}
.orow{display:grid;grid-template-columns:2.9em 1fr;gap:2px 10px;padding:7px 0;border-top:1px solid var(--line-soft)}
.orow:first-of-type{border-top:0}
.orow .nr{font:600 13px/1.45 "IBM Plex Mono",monospace;color:var(--muted)}
.orow .ti{font-size:13.5px;line-height:1.45}
.orow .wy{grid-column:2;font-size:12.5px;color:var(--muted);line-height:1.5}
.orow .pills{grid-column:2;display:flex;flex-wrap:wrap;gap:5px;margin-top:3px}
.lane-list{display:flex;flex-wrap:wrap;gap:5px}
.chipnr{font:500 12px/1 "IBM Plex Mono",monospace;background:var(--sunk);border:1px solid var(--line-soft);border-radius:5px;padding:4px 6px;color:var(--muted)}
/* Release-bane i full bredde under to-kolonne-rutenettet. To spalter når det er plass —
   en lang rad i én spalte blir en liste man ikke leser, og i sidekolonnen var radene
   bare nummer-chips uten tittel. Brukes av planlagte releaser. */
.lane-next{margin-top:14px;border-color:var(--rel3);box-shadow:inset 3px 0 0 var(--rel3)}
.lane-done{margin-top:14px;border-color:var(--line);box-shadow:inset 3px 0 0 var(--faint);background:var(--sunk)}
.orows-1{display:grid;gap:0}
.wave-h{margin-top:8px}
.wave-n{font:600 11px/1 "IBM Plex Mono",monospace;background:var(--rel3-wash);color:var(--rel3);border-radius:4px;padding:3px 6px;letter-spacing:0}
.seq{font:500 12px/1 "IBM Plex Mono",monospace;color:var(--faint);margin-right:2px}
.pill.eierp{background:var(--eier-wash);color:var(--eier)}
details.goal{margin-top:4px}
details.goal h4{font-size:13.5px;color:var(--ink);margin:14px 0 4px}
details.goal p{margin:6px 0;max-width:82ch}
.goal-tbl{overflow-x:auto}
.goal-tbl table{border-collapse:collapse;font-size:12.5px;width:100%}
.goal-tbl th,.goal-tbl td{border-top:1px solid var(--line-soft);padding:6px 8px;text-align:left;vertical-align:top}
.goal-tbl th{color:var(--ink);font-weight:600}
.lane-tag.levert{background:var(--klar-bg);color:var(--klar-ink)}
.orows-2{display:grid;grid-template-columns:1fr 1fr;gap:0 26px;align-content:start}
.orows-2 .orow{min-width:0}
.orows-2 .ti{overflow-wrap:anywhere}
@media (max-width:760px){.orows-2{grid-template-columns:1fr}}

/* ---------- Epics ---------- */
.epics{display:grid;grid-template-columns:repeat(auto-fill,minmax(232px,1fr));gap:10px}
.epic{background:var(--surface);border:1px solid var(--line);border-radius:9px;padding:12px 13px;display:flex;flex-direction:column;gap:9px;text-align:left;font:inherit;color:inherit;cursor:pointer}
.epic:hover{border-color:var(--accent)}
.epic[aria-pressed="true"]{border-color:var(--accent);background:var(--accent-wash)}
.epic:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.epic-t{font-size:13.5px;font-weight:600;line-height:1.35;text-wrap:balance}
.epic-n{font:600 12px/1 "IBM Plex Mono",monospace;color:var(--muted);font-variant-numeric:tabular-nums}
.bar{display:flex;height:6px;border-radius:3px;overflow:hidden;background:var(--sunk)}
.bar i{display:block}
.bar .b-klar{background:var(--klar-ink)}.bar .b-venter{background:var(--venter-ink)}
.bar .b-utsatt{background:var(--utsatt-ink)}.bar .b-arbeid{background:var(--arbeid-ink)}
.epic-f{display:flex;flex-wrap:wrap;gap:4px;font-size:11.5px;color:var(--muted)}

/* ---------- Filter ---------- */
.filters{position:sticky;top:0;z-index:5;background:var(--bg);border-bottom:1px solid var(--line);
  padding:10px 0;margin:0 0 14px;display:flex;flex-wrap:wrap;gap:8px 14px;align-items:center}
.fgroup{display:flex;gap:5px;align-items:center;flex-wrap:wrap}
.flabel{font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.07em;color:var(--faint)}
.chip{font:500 12.5px/1 "IBM Plex Sans",sans-serif;background:var(--surface);border:1px solid var(--line);
  border-radius:999px;padding:6px 11px;color:var(--muted);cursor:pointer}
.chip:hover{border-color:var(--accent)}
.chip[aria-pressed="true"]{background:var(--accent);border-color:var(--accent);color:var(--on-accent)}
.chip:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.chip .c{font-family:"IBM Plex Mono",monospace;font-size:11px;opacity:.75;margin-left:5px}
#q{font:400 13px/1 "IBM Plex Sans",sans-serif;background:var(--surface);border:1px solid var(--line);
  border-radius:999px;padding:7px 12px;color:var(--ink);min-width:150px}
#q:focus-visible{outline:2px solid var(--accent);outline-offset:1px}
.count{font-size:12.5px;color:var(--muted);margin-left:auto;font-variant-numeric:tabular-nums}

/* ---------- Kø-rader ---------- */
.rows{display:grid;gap:5px}
.row{display:grid;grid-template-columns:2.6em 3.4em 1fr auto;gap:1px 11px;align-items:baseline;
  background:var(--surface);border:1px solid var(--line);border-radius:7px;padding:9px 11px}
.row[hidden]{display:none}
.row .pos{font:400 12px/1.5 "IBM Plex Mono",monospace;color:var(--faint);text-align:right;font-variant-numeric:tabular-nums}
.row .nr{font:600 13px/1.5 "IBM Plex Mono",monospace}
.row .t{min-width:0;font-size:14px;line-height:1.45}
.row .r{display:flex;gap:5px;align-items:center;flex-wrap:wrap;justify-content:flex-end}
.row .ep{grid-column:3;font-size:11.5px;color:var(--faint);margin-top:2px}
.deps{font-size:12px;color:var(--muted);margin-left:6px;white-space:nowrap}
.row .note{grid-column:3/-1;font-size:12.5px;line-height:1.5;color:var(--muted);margin-top:5px;max-width:78ch}
.done{color:var(--klar-ink)}.warn{color:var(--pause-ink);font-weight:600}
.order{font:400 11px/1 "IBM Plex Mono",monospace;color:var(--faint)}
.empty{padding:26px 12px;text-align:center;color:var(--muted);font-size:13.5px;
  border:1px dashed var(--line);border-radius:8px}
.empty[hidden]{display:none}

/* ---------- Pills ---------- */
.pill{display:inline-block;font-size:11px;font-weight:500;letter-spacing:.015em;padding:2px 8px;border-radius:999px;line-height:1.65;white-space:nowrap}
.st-klar{background:var(--klar-bg);color:var(--klar-ink)}
.st-venter{background:var(--venter-bg);color:var(--venter-ink)}
.st-utsatt{background:var(--utsatt-bg);color:var(--utsatt-ink)}
.st-arbeid{background:var(--arbeid-bg);color:var(--arbeid-ink);font-weight:600}
.pause{background:var(--pause-bg);color:var(--pause-ink)}
.pipe{background:var(--accent-wash);color:var(--accent-ink)}
.relp{font:600 10.5px/1.65 "IBM Plex Mono",monospace;padding:2px 7px}
/*REL_CSS*/
.pill.eff-s,.pill.eff-m,.pill.eff-l,.pill.eff-x{min-width:1.5em;text-align:center;font-weight:600;
  background:transparent;border:1px solid var(--line);color:var(--muted);font-family:"IBM Plex Mono",monospace;font-size:10.5px}
.pill.eff-s{color:var(--klar-ink);border-color:var(--klar-ink)}
.pill.eff-m{color:var(--venter-ink);border-color:var(--venter-ink)}
.pill.eff-l{color:var(--pause-ink);border-color:var(--pause-ink)}
.pill.eff-x{opacity:.55}

/* ---------- Varsler ---------- */
.flags{display:grid;gap:9px}
.flag{background:var(--surface);border:1px solid var(--line);border-left:3px solid var(--pause-ink);
  border-radius:0 7px 7px 0;padding:11px 13px}
.flag b{font-size:13.5px}
.flag p{margin:4px 0 0;font-size:12.5px;color:var(--muted);line-height:1.55;max-width:80ch}

/* ---------- Detaljer ---------- */
details{background:var(--surface);border:1px solid var(--line);border-radius:8px;margin-top:9px}
summary{cursor:pointer;padding:11px 13px;font-size:13.5px;font-weight:600;list-style:none;display:flex;gap:8px;align-items:center}
summary::-webkit-details-marker{display:none}
summary::before{content:"›";font-family:"IBM Plex Mono",monospace;color:var(--muted);transition:transform .15s}
details[open] summary::before{transform:rotate(90deg)}
summary:focus-visible{outline:2px solid var(--accent);outline-offset:-2px}
.dbody{padding:0 13px 13px;font-size:13px;line-height:1.6;color:var(--muted)}
.dbody ul{margin:0;padding-left:19px}.dbody li{margin:7px 0;max-width:82ch}
.dbody strong{color:var(--ink)}
.diag{overflow-x:auto;background:var(--sunk);border:1px solid var(--line-soft);border-radius:6px;padding:11px;margin-top:9px}
pre.mermaid{margin:0;font-family:"IBM Plex Mono",monospace;font-size:11.5px}
@media (prefers-reduced-motion:reduce){*{transition:none!important;animation:none!important}}
@media (max-width:760px){
  .lanes{grid-template-columns:1fr}
  .row{grid-template-columns:2.4em 3.2em 1fr}
  .row .r{grid-column:2/4;justify-content:flex-start;margin-top:4px}
  .row .ep,.row .note{grid-column:2/4}
  .filters{gap:7px 10px}
  .count{margin-left:0;width:100%}
}
</style>""".replace("/*REL_CSS*/", REL_CSS))

    a("<main>")
    a(f"<h1>{_h.escape(TITLE)}</h1>")
    a(f'<div class="meta"><span>Generert {_h.escape(now)}</span>'
      f'<span>{_h.escape(BASE_REF)} <span class="mono">{_h.escape(dev_sha)}</span></span>'
      f'<span>{len(levende)} levende todos</span>'
      f'<span>Kilde: <span class="mono">tasks/todos/*.md</span></span></div>')

    # ============================ 1. RELEASE-BANER ============================
    a("<section>")
    a('<p class="eyebrow">Release-versjoner</p>')
    a("<h2>Hva hører til hvilken release</h2>")
    a('<p class="sub">Release er feltet <code>release:</code> i todoens frontmatter'
      + (' (eldre todoer: en <code>release-x.y.z</code>-tag)' if RELEASE_TAGS else '')
      + ', med mål og epics i <code>tasks/releases/</code>. '
      f'Bare {sum(len(v) for k, v in lanes.items() if k != "ingen")} av {len(levende)} todos har en — resten er kø uten planlagt slipp.'
      + (' ' + CFG["RELEASE_NOTE"] if CFG["RELEASE_NOTE"] else '') + '</p>')
    a('<div class="lanes">')

    # -- Aktiv release øverst (hero). En levert release skal ikke stå øverst og se ut som ukens arbeid.
    nx2 = lanes.get(NOW, []) if NOW else []
    n_levert = sum(1 for a in archived() if a[2] == REL)  # arkivoppføringens **Release:**-linje, samme kilde som release.py
    n_klar = sum(1 for d in nx2 if state_of(d) == "klar")
    n_venter = sum(1 for d in nx2 if state_of(d) == "venter")
    n_arbeid = sum(1 for d in nx2 if state_of(d) == "arbeid")
    n_plan = sum(1 for d in nx2 if plan_state(d) == "godkjent")
    n_utkast = sum(1 for d in nx2 if plan_state(d) == "utkast")
    n_uplan = sum(1 for d in nx2 if plan_state(d) == "ingen")
    a('<article class="lane lane-now">')
    if NOW:
        a(f'<div class="lane-head"><span class="lane-tag r-now">{NOW}</span>'
          '<span class="pill st-arbeid">aktiv</span>'
          f'<span><span class="lane-n">{len(nx2)}<small>todos igjen</small></span> '
          f'<span class="lane-n">{n_levert}<small>levert</small></span></span></div>')
    else:
        a('<div class="lane-head"><span class="lane-tag r-now">ingen aktiv release</span></div>')
    bits = []
    if n_klar:
        bits.append(f"<strong>{n_klar}</strong> kan claimes nå")
    if n_venter:
        bits.append(f"{n_venter} venter på deps")
    if n_arbeid:
        bits.append(f"{n_arbeid} i arbeid")
    bits.append(f"{n_plan} har godkjent plan · {n_utkast} til godkjenning · {n_uplan} uten plan")
    if REL:
        a('<div class="lane-name">' + (f"<strong>{inl(REL_GOAL)}</strong> · " if REL_GOAL else "")
          + " · ".join(bits) + ". Rekkefølgen under er epicene i release-fila, sortert på <code>order</code> innenfor hver. "
          f"Mål, done_when og eierpunkter står i <code>tasks/releases/{REL}.md</code>.</div>")
    else:
        a('<div class="lane-name">Ingen release i <code>tasks/releases/</code> har <code>status: active</code>'
          + (f" ({len(_ACTIVE)} er satt til <code>active</code>, bare én er lov — se <code>release.py status</code>)" if len(_ACTIVE) > 1 else "")
          + ". Hele køen er kvalifisert.</div>")
    # Rekkefølgen er EPICENE i release-fila (todos i rekkefølgen de vil bli gjennomført i).
    # En todo i scope uten kjent `epic:` havner i «Uten epic».
    by_nr = {d["nr"]: d for d in nx2}
    plassert = set()
    seq = 0
    bolger = [(str(i), e, [d["nr"] for d in nx2 if d.get("epic") == e]) for i, e in enumerate(REL_EPICS)]
    for bnr, bnavn, nrs in bolger + [("?", "Uten epic", [d["nr"] for d in nx2 if d.get("epic") not in REL_EPICS])]:
        rader = [by_nr[n] for n in nrs if n in by_nr]
        if not rader:
            continue
        a(f'<div class="owner-h wave-h"><span class="wave-n">{_h.escape(bnr)}</span>{_h.escape(bnavn)} ({len(rader)})</div>')
        a('<div class="orows-1">')
        for d in rader:
            seq += 1
            plassert.add(d["nr"])
            eier, why = EIERSKAP.get(d["nr"], ("loop", ""))
            a(f'<div class="orow"><span class="nr">{d["nr"]}</span>'
              f'<span class="ti"><span class="seq">{seq}.</span> {inl(short_title(d, 96))}{deps_html(d)}</span>'
              f'<span class="pills">{state_pill(d)}{plan_html(d)}{effort_html(d)}'
              + ('<span class="pill pause">pausepunkt</span>' if is_pause(d) else "")
              + (f'<span class="pill eierp">{_h.escape(OWNER_NAME)}</span>' if eier == "eier" else "")
              + "</span>"
              + (f'<span class="wy">{inl(why)}</span>' if why else "") + "</div>")
        a("</div>")
    # Målet vi jobber etter — ordrett fra planfila, så det aldri finnes to versjoner.
    if REL_DONE_WHEN:
        a(f'<details class="goal"><summary>done_when for {NOW} ({sum(1 for x, _ in REL_DONE_WHEN if x != " ")}/{len(REL_DONE_WHEN)})</summary>'
          '<div class="dbody"><ul>' + "".join(f"<li>{'✅' if x != ' ' else '☐'} {inl(t)}</li>" for x, t in REL_DONE_WHEN)
          + "</ul></div></details>")
    a("</article>")

    a("</div>")

    # -- planlagte releaser (status: planned) under den aktive, eldste først.
    for k in PLANNED_KEYS:
        lk = lanes.get(k, [])
        goal = next((r.get("goal", "") for v, r in RELS.items() if lane_key(v) == k), "")
        a('<article class="lane lane-next">')
        a(f'<div class="lane-head"><span class="lane-tag r-now">{k} · planlagt</span>'
          f'<span class="lane-n">{len(lk)}<small>todos</small></span></div>')
        if goal:
            a(f'<div class="lane-name"><strong>{inl(goal)}</strong></div>')
        if lk:
            a('<div class="orows-2">')
            for d in lk:
                a(f'<div class="orow"><span class="nr">{d["nr"]}</span>'
                  f'<span class="ti">{inl(short_title(d, 74))}</span>'
                  f'<span class="pills">{state_pill(d)}{plan_html(d)}{effort_html(d)}</span></div>')
            a("</div>")
        a("</article>")

    # -- leverte releaser nederst, nyeste først. Står igjen som historikk, ikke som arbeid.
    #    Teksten er LEVERT[k] fra config, ellers `shipped:`-datoen og `goal` fra release-fila.
    def levert_tekst(k):
        if k in CFG["LEVERT"]:
            return CFG["LEVERT"][k]
        r = SHIPPED.get(k, {})
        dato = r.get("shipped", "")
        return (f"<strong>Levert{' ' + _h.escape(dato) if dato else ''}</strong>"
                + (f": {inl(r['goal'])}" if r.get("goal") else "."))

    for k in SHIPPED_KEYS:
        tekst = levert_tekst(k)
        lk = lanes.get(k, [])
        a('<article class="lane lane-done">')
        a(f'<div class="lane-head"><span class="lane-tag levert">{k} · levert</span>'
          f'<span class="lane-n">{len(lk)}<small>åpne todos</small></span></div>')
        a(f'<div class="lane-name">{tekst}</div>')
        if lk:
            a('<div class="orows-2">')
            for d in lk:
                why = EIERSKAP.get(d["nr"], ("loop", ""))[1]
                a(f'<div class="orow"><span class="nr">{d["nr"]}</span>'
                  f'<span class="ti">{inl(short_title(d, 74))}</span>'
                  f'<span class="pills">{state_pill(d)}{effort_html(d)}</span>'
                  + (f'<span class="wy">{inl(why)}</span>' if why else "") + "</div>")
            a("</div>")
        a("</article>")
    # -- uten release-tag: ALLTID nederst, under de leverte (eier 2026-09-27).
    for k in ("ingen",):
        navn = "Uten release-tag"
        mem = lanes.get(k, [])
        a('<article class="lane">')
        a(f'<div class="lane-head"><span class="lane-tag r-{slug(k)}">{_h.escape(k)}</span>'
          f'<span class="lane-n">{len(mem)}<small>todos</small></span></div>')
        a(f'<div class="lane-name">{_h.escape(navn)}</div>')
        klar = sum(1 for d in mem if state_of(d) == "klar")
        ut = sum(1 for d in mem if state_of(d) == "utsatt")
        a(f'<div class="lane-name">{klar} kan claimes nå · {ut} utsatt · '
          f'{len(forslag)} u-triagerte <code>forslag</code>. Ingen av dem er lovet noen bruker.</div>')
        a("</article>")
    a("</section>")

    # ============================ 2. EPICS ============================
    a("<section>")
    a('<p class="eyebrow">Epics</p>')
    a("<h2>Køen gruppert i arbeidsflater</h2>")
    a('<p class="sub">En epic er en flate flere todos deler — samme skjerm, samme Edge Function, samme kontrakt. '
      + ('Tilhørigheten kommer fra et nummer-sett i <code>tasks/queue-config.py</code>, ellers fra todoens <code>epic:</code>-felt eller en epic-tag. '
         if CFG["EPIC_FROM_FIELD"] else
         'Tilhørigheten kommer fra et nummer-sett i <code>tasks/queue-config.py</code>, ellers fra epic-taggen. ')
      + 
      '<strong>Trykk på et kort for å filtrere køen under.</strong> Stripa viser fordelingen: '
      '<span class="pill st-klar">kan claimes</span> <span class="pill st-venter">venter på deps</span> '
      '<span class="pill st-utsatt">utsatt</span>.</p>')
    a('<div class="epics">')
    for name, mem in epic_order:
        cnt = {"klar": 0, "venter": 0, "utsatt": 0, "arbeid": 0}
        for d in mem:
            cnt[state_of(d)] += 1
        tot = len(mem) or 1
        rels = sorted({rel_of(d) for d in mem} - {"ingen"})
        a(f'<button class="epic" type="button" data-epic="{slug(name)}" aria-pressed="false">')
        a(f'<span class="epic-t">{_h.escape(name)}</span>')
        a('<span class="bar">' + "".join(
            f'<i class="b-{s}" style="width:{cnt[s]/tot*100:.1f}%"></i>'
            for s in ("arbeid", "klar", "venter", "utsatt") if cnt[s]) + "</span>")
        f = [f'<span class="epic-n">{len(mem)} todos</span>']
        if cnt["klar"]:
            f.append(f'<span class="pill st-klar">{cnt["klar"]} klar</span>')
        if cnt["arbeid"]:
            f.append(f'<span class="pill st-arbeid">{cnt["arbeid"]} i arbeid</span>')
        for r in rels:
            f.append(f'<span class="pill relp {slug(r)}">{r}</span>')
        a('<span class="epic-f">' + "".join(f) + "</span>")
        a("</button>")
    a("</div></section>")

    # ============================ 3. KØEN ============================
    synlige = [d for d in levende if d.get("status") in ("open", "reviewed", "in_progress")]
    synlige.sort(key=key)
    pos = {d["nr"]: i + 1 for i, d in enumerate(synlige)}
    alle_rader = synlige + [d for d in levende if d.get("status") == "deferred"]

    n_klar = sum(1 for d in synlige if state_of(d) == "klar")

    a("<section>")
    a('<p class="eyebrow">Køen</p>')
    a("<h2>Rekkefølgen §1 faktisk velger fra</h2>")
    a('<p class="sub"><code>prioritert</code> først, deretter <code>order</code>. '
      'Nummeret helt til venstre er køplassen — den endrer seg <em>ikke</em> når du filtrerer, '
      'så du ser alltid hvor langt ned i køen en rad egentlig ligger. '
      '<span class="pill pause">pausepunkt</span> = tags som krever menneskets go (migrasjon, RLS, Edge, prod, native, secrets).</p>')

    a('<div class="filters">')
    a('<div class="fgroup"><span class="flabel">Release</span>')
    a('<button class="chip" type="button" data-f="rel" data-v="all" aria-pressed="true">Alle</button>')
    for k in ALL_KEYS + ["ingen"]:
        c = sum(1 for d in alle_rader if rel_of(d) == k)
        lbl = "uten tag" if k == "ingen" else k
        a(f'<button class="chip" type="button" data-f="rel" data-v="{k}" aria-pressed="false">{lbl}<span class="c">{c}</span></button>')
    a("</div>")
    a('<div class="fgroup"><span class="flabel">Tilstand</span>')
    a(f'<button class="chip" type="button" data-f="st" data-v="queue" aria-pressed="true">I køen<span class="c">{len(synlige)}</span></button>')
    a(f'<button class="chip" type="button" data-f="st" data-v="klar" aria-pressed="false">Kan claimes<span class="c">{n_klar}</span></button>')
    a(f'<button class="chip" type="button" data-f="st" data-v="all" aria-pressed="false">Alle inkl. utsatt<span class="c">{len(alle_rader)}</span></button>')
    a("</div>")
    a('<input id="q" type="search" placeholder="Søk i tittel eller nr" aria-label="Søk i køen">')
    a('<span class="count" id="cnt"></span>')
    a("</div>")

    a('<div class="rows" id="rows">')
    for d in alle_rader:
        r = rel_of(d)
        st = state_of(d)
        ep = cluster_of(d["nr"], d.get("tags", ""))
        note = NOTES.get(d["nr"])
        badges = [effort_html(d), state_pill(d)]
        if r != "ingen":
            badges.append(f'<span class="pill relp {slug(r)}">{r}</span>')
        if is_pause(d):
            badges.append('<span class="pill pause">pausepunkt</span>')
        if d in plan_ready:
            badges.append('<span class="pill pipe">plan skrevet</span>')
        p = pos.get(d["nr"])
        a(f'<div class="row {slug(r) if r != "ingen" else ""}" data-rel="{r}" data-st="{st}" '
          f'data-epic="{slug(ep)}" data-q="{_h.escape((d["nr"] + " " + (d.get("title") or "")).lower())}">')
        a(f'<span class="pos">{p if p else "—"}</span><span class="nr">{d["nr"]}</span>')
        a(f'<span class="t">{inl(short_title(d, 110))}{deps_html(d)}</span>')
        a(f'<span class="r">{"".join(badges)}<span class="order">order {as_int(d.get("order"))}</span></span>')
        a(f'<span class="ep">{_h.escape(ep)}</span>')
        if note:
            a(f'<span class="note">{inl(note)}</span>')
        a("</div>")
    a("</div>")
    a('<div class="empty" id="empty" hidden>Ingen todos matcher filteret. Nullstill med «Alle» + «I køen».</div>')
    a("</section>")

    # ============================ 4. VARSLER ============================
    a("<section>")
    a('<p class="eyebrow">Datakvalitet</p>')
    a("<h2>Felter køen ikke kan lese</h2>")
    a('<p class="sub">Denne oversikten er bare så presis som frontmatteren. Under står avvikene som '
      'faktisk endrer hvordan §1 sorterer, eller som gjør et tall her mindre verdt enn det ser ut.</p>')
    a('<div class="flags">')
    if pri_avvik:
        lst = ", ".join(f'{d["nr"]} (<code>{_h.escape((d.get("priority") or "").strip())}</code>)' for d in sorted(pri_avvik, key=key))
        a(f'<div class="flag"><b>{len(pri_avvik)} todos har en <code>priority</code> §1 ikke kjenner</b>'
          f'<p>§1 skiller kun på <code>prioritert</code> mot alt annet. '
          f'<code>høy</code>, <code>high</code> og <code>low</code> sorteres derfor som <code>normal</code> — '
          f'de ser prioriterte ut i fila, men ligger i praksis i normal-bunken. Gjelder: {lst}.</p></div>')
    if uten_effort:
        a(f'<div class="flag"><b>{len(uten_effort)} av {len(levende)} todos mangler <code>effort</code></b>'
          f'<p>De rendres som <span class="pill eff-x">?</span>. Enhver sum av gjenstående arbeid på denne '
          f'siden dekker altså bare {len(levende)-len(uten_effort)} rader — bruk den som retning, ikke som estimat.</p></div>')
    if uklassifisert:
        a(f'<div class="flag"><b>{len(uklassifisert)} todos faller utenfor alle epics</b>'
          + ('<p>De havner i «Uklassifisert» fordi de mangler <code>epic:</code>, nummeret ikke står i noe klynge-sett og taggene ikke '
             if CFG["EPIC_FROM_FIELD"] else
             '<p>De havner i «Uklassifisert» fordi nummeret ikke står i noe klynge-sett og taggene ikke ')
          + 'treffer <code>EPIC_TAG_CLUSTER</code>. De er ikke mindre viktige — de er bare ugrupperte.</p></div>')
    for _tittel, _tekst in CFG["EKSTRA_FLAGG"]:
        a(f'<div class="flag"><b>{_tittel}</b><p>{_tekst}</p></div>')
    a("</div></section>")

    # ============================ 5. DETALJER ============================
    def block(after_header):
        i = out.index(after_header)
        j = out.index("```mermaid", i)
        k = out.index("```", j + 1)
        return "\n".join(out[j + 1:k])

    a("<section>")
    a('<p class="eyebrow">Bakgrunn</p>')
    a("<h2>Agenda, diagrammer og merknader</h2>")
    a('<p class="sub">Lang tekst som hører til køen, men som ikke skal stå i veien for den. Åpne det du trenger.</p>')

    if AGENDA and AGENDA.get("punkter"):
        a("<details><summary>⏰ Avtalt agenda — " + _h.escape(AGENDA["tittel"]) + f' ({len(AGENDA["punkter"])} punkter)</summary>')
        a('<div class="dbody"><p>' + inl(AGENDA["hvorfor"]) + "</p><ul>")
        for tittel, tekst in AGENDA["punkter"]:
            a("<li><strong>" + _h.escape(tittel) + "</strong> — " + inl(tekst) + "</li>")
        a("</ul></div></details>")

    a("<details><summary>Diagram — rekkefølge, avhengigheter og parallelle løp</summary>")
    a('<div class="dbody"><p>Klyngene kjøres ovenfra og ned. Piler inne i en klynge er <code>deps</code>; '
      "todos uten pil kan gå i vilkårlig rekkefølge. Stiplet = pausepunkt-kandidat.</p>")
    a('<div class="diag"><pre class="mermaid">' + _h.escape(block("## Diagram — rekkefølge, avhengigheter og parallelle løp")) + "</pre></div>")
    a("<p>Parallelle løp i én loop-runde (§5c pipelining):</p>")
    a('<div class="diag"><pre class="mermaid">' + _h.escape(block("### Parallelle løp i én loop-runde (§5c pipelining, `max_in_flight: 1`)")) + "</pre></div>")
    a("</div></details>")

    if _merk:
        a(f"<details><summary>Merknader om rekkefølge og historikk ({len(_merk)})</summary>")
        a('<div class="dbody"><ul>')
        for line in _merk:
            a("<li>" + inl(line) + "</li>")
        a("</ul></div></details>")

    a(f"<details><summary>Utsatt, ikke i køen ({len(deferred)})</summary>")
    a('<div class="dbody"><ul>')
    a(f"<li><strong>U-triagerte grooming-forslag</strong> (<code>tags: [forslag]</code>): {', '.join(prop) or '—'}</li>")
    a(f"<li><strong>Bevisst utsatt:</strong> {', '.join(rest) or '—'}</li>")
    a("</ul></div></details>")
    a("</section>")

    # ============================ FILTER-JS ============================
    a("""<script>
(function(){
  var rows=[].slice.call(document.querySelectorAll('.row'));
  var f={rel:'all',st:'queue',epic:null,q:''};
  var cnt=document.getElementById('cnt'), empty=document.getElementById('empty');
  function apply(){
    var n=0;
    rows.forEach(function(r){
      var ok=true;
      if(f.rel!=='all' && r.dataset.rel!==f.rel) ok=false;
      if(f.st==='queue' && r.dataset.st==='utsatt') ok=false;
      if(f.st==='klar' && r.dataset.st!=='klar') ok=false;
      if(f.epic && r.dataset.epic!==f.epic) ok=false;
      if(f.q && r.dataset.q.indexOf(f.q)===-1) ok=false;
      r.hidden=!ok; if(ok) n++;
    });
    cnt.textContent=n+' av '+rows.length+' rader';
    empty.hidden=n>0;
  }
  document.querySelectorAll('.chip').forEach(function(b){
    b.addEventListener('click',function(){
      var k=b.dataset.f;
      document.querySelectorAll('.chip[data-f="'+k+'"]').forEach(function(o){o.setAttribute('aria-pressed','false');});
      b.setAttribute('aria-pressed','true');
      f[k]=b.dataset.v; apply();
    });
  });
  document.querySelectorAll('.epic').forEach(function(b){
    b.addEventListener('click',function(){
      var on=b.getAttribute('aria-pressed')==='true';
      document.querySelectorAll('.epic').forEach(function(o){o.setAttribute('aria-pressed','false');});
      if(on){ f.epic=null; }
      else { b.setAttribute('aria-pressed','true'); f.epic=b.dataset.epic;
             document.querySelector('.filters').scrollIntoView({block:'start'}); }
      apply();
    });
  });
  var q=document.getElementById('q');
  q.addEventListener('input',function(){ f.q=q.value.trim().toLowerCase(); apply(); });
  apply();
})();
</script>""")

    a("</main>")
    open(hpath, "w", encoding="utf-8").write("\n".join(h) + "\n")
