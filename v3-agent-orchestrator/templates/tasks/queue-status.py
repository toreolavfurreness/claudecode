#!/usr/bin/env python3
"""Genererer tasks/queue-status.md — en LESEVISNING av køen slik §1-skriptet i
coordinator-runbook.md faktisk kjører den (prioritert først, så `order`), med et
mermaid-diagram over avhengighetene.

Kilden til sannhet er fortsatt én fil per todo i tasks/todos/ (frontmatter). Denne fila
er avledet og overskrives; rediger aldri queue-status.md for hånd.

Kjør fra repo-roten (koordinatoren kan gjøre det i §6-halen):
    python3 tasks/queue-status.py > tasks/queue-status.md

Grupperingen er «neste i køen / venter på deps / pågår / utenfor aktiv release / utsatt». Med en
aktiv release (tasks/releases/) står fremdriften fra `tasks/release.py status` øverst.
"""
import glob
import os
import pathlib
import re
import subprocess
import sys
from datetime import datetime


def fm(path):
    t = open(path, encoding="utf-8").read()
    m = re.search(r"^---\n(.*?)\n---", t, re.S)
    d = {}
    if m:
        for line in m.group(1).splitlines():
            mm = re.match(r"(\w+):\s*(.*)", line)
            if mm:
                # Innholdet i "…", ellers alt før en ` #`-kommentar (samme regel som release.py).
                v = mm.group(2).strip()
                q = re.match(r'"([^"]*)"', v)
                d[mm.group(1)] = q.group(1) if q else re.sub(r"\s+#.*$", "", v)
    body = t[m.end():] if m else t
    d["_brainstorm"] = bool(
        re.search(r"krever[^.\n]*brainstorm|brainstorm\s+f.?r\s+plan|spec\s+f.?r\s+plan", body, re.I)
    )
    d["_path"] = path
    return d


def as_int(v, default=9999):
    try:
        return int(v)
    except (ValueError, TypeError):
        return default


todos = {}
for p in glob.glob("tasks/todos/todo-*.md"):
    d = fm(p)
    if d.get("nr"):
        todos[d["nr"]] = d


# Samme release-filter som §1: bare todoer i den aktive releasen er kvalifisert.
_active = [p for p in glob.glob("tasks/releases/*.md")
           if os.path.basename(p) != "README.md" and fm(p).get("status") == "active"]
REL = os.path.basename(_active[0])[:-3] if len(_active) == 1 else None


def deps_of(d):
    return re.findall(r'"([^"]+)"', d.get("deps", "") or "")


# Arkiverte todos har ingen fil i tasks/todos/ — de teller som ferdige. En dep som verken
# finnes som fil ELLER i arkivet er en SKRIVEFEIL, og skal ikke lese som ferdig (fail-closed).
_ARCHIVE = pathlib.Path("tasks/todo_archive.md")
_archived = set(
    re.findall(r"TODO\s+([0-9]+[A-Za-z]?)", _ARCHIVE.read_text(encoding="utf-8"))
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


def eligible(d):
    return (
        d.get("status") in ("open", "reviewed")
        and d.get("claimed_by", "null") in ("null", "", None)
        and not d["_brainstorm"]
        and all(dep_done(x) for x in deps_of(d))
        and not re.search(r"\bforslag\b|\bprod-release\b", d.get("tags", "") or "")
        and (REL is None or d.get("release") == REL)
    )


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
    parts = [f"{x}✓" if dep_done(x) else (x if dep_known(x) else f"{x}⚠ukjent") for x in ds]
    return " (deps " + ", ".join(parts) + ")"


def group_of(d):
    s = d.get("status")
    if s == "in_progress" or d.get("claimed_by", "null") not in ("null", "", None):
        return "Pågår"
    if eligible(d):
        return "Neste i køen"
    if s in ("open", "reviewed") and REL and d.get("release") != REL:
        return "Utenfor aktiv release"
    if s in ("open", "reviewed"):
        return "Venter (deps, brainstorm, forslag eller prod-release)"
    if s == "deferred":
        return "Utsatt"
    return None  # done/split vises ikke


GROUPS = ["Pågår", "Neste i køen", "Venter (deps, brainstorm, forslag eller prod-release)", "Utenfor aktiv release", "Utsatt"]

out = [
    "<!-- GENERERT av tasks/queue-status.py — IKKE rediger for hånd. -->",
    f"# Køstatus — {datetime.now().strftime('%Y-%m-%d %H:%M')}",
    "",
    f"{len(todos)} todo-filer. Rekkefølge = §1: `priority: prioritert` først, så `order`.",
    "",
]
if REL or len(_active) > 1:
    _r = subprocess.run([sys.executable, "tasks/release.py", "status"], capture_output=True, text=True)
    out += ["> " + line for line in (_r.stdout or _r.stderr).splitlines()] + [""]
live = sorted((d for d in todos.values() if group_of(d)), key=key)
for g in GROUPS:
    rows = [d for d in live if group_of(d) == g]
    if not rows:
        continue
    out += [f"## {g} ({len(rows)})", ""]
    for i, d in enumerate(rows, 1):
        prio = " ⭐" if d.get("priority") == "prioritert" else ""
        eff = f" `{d['effort']}`" if d.get("effort") else ""
        out.append(f"{i}. **{d['nr']}** {short_title(d)}{eff}{prio}{deps_str(d)}")
    out.append("")

# Avhengighetsgraf over ikke-ferdige todos som har eller er en dep.
edges = [(x, d["nr"]) for d in live for x in deps_of(d) if not dep_done(x)]
if edges:
    out += ["## Avhengigheter", "", "```mermaid", "graph LR"]
    for a, b in edges:
        out.append(f'  T{re.sub(r"[^0-9A-Za-z]", "_", a)}["{a}"] --> T{re.sub(r"[^0-9A-Za-z]", "_", b)}["{b}"]')
    out += ["```", ""]

sys.stdout.write("\n".join(out) + "\n")
