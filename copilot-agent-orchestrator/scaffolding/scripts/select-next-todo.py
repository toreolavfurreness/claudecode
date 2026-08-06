#!/usr/bin/env python3
"""select-next-todo.py — kø-utvelgelse for koordinatoren (docs/coordinator-runbook.md §1).

Leser tasks/todos/todo-*.md, parser frontmatter, ekskluderer det som ikke er
klart, sorterer prioritert -> order, og printer nr+slug+path for FØRSTE
kandidat som består alle filtrene. Ingen kandidat -> exit 1, tomt stdout.

Bruk (fra prosjektroten):
    python3 copilot-agent-orchestrator/scaffolding/scripts/select-next-todo.py

Filtre (i rekkefølge):
  1. status != "open"                         -> ekskludert
  2. tags inneholder "forslag" eller "utredning" -> ekskludert (se
     tasks/todos/README.md § Tagging for hvorfor)
  3. deps ikke alle "done"                    -> ekskludert (manglende fil for
     en dep-nr = antatt done/arkivert)
Sortering: priority == "prioritert" først, deretter order stigende.
"""
import glob
import re
import sys

TODOS_GLOB = "tasks/todos/todo-*.md"


def parse_frontmatter(path):
    with open(path, encoding="utf-8") as f:
        content = f.read()
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
    if not m:
        return None
    fm_text = m.group(1)
    data = {}
    for line in fm_text.splitlines():
        line = line.rstrip()
        if not line or line.lstrip().startswith("#"):
            continue
        km = re.match(r'^([A-Za-z_]+):\s*(.*)$', line)
        if not km:
            continue
        key, val = km.group(1), km.group(2).strip()
        if val.startswith("[") and val.endswith("]"):
            inner = val[1:-1].strip()
            items = [x.strip().strip('"').strip("'") for x in inner.split(",") if x.strip()]
            data[key] = items
        else:
            val = val.strip('"').strip("'")
            if val.lower() == "null":
                val = None
            data[key] = val
    return data


def dep_satisfied(dep_nr, all_status):
    dep_nr_lower = dep_nr.lower()
    for nr, status in all_status.items():
        if nr.lower() == dep_nr_lower:
            return status == "done"
    # Ingen fil funnet for denne dep-nr -> antatt done/arkivert (se README §Regler)
    return True


def main():
    files = sorted(glob.glob(TODOS_GLOB))
    todos = []
    all_status = {}
    for f in files:
        fm = parse_frontmatter(f)
        if not fm or "nr" not in fm:
            continue
        fm["_path"] = f
        todos.append(fm)
        all_status[str(fm["nr"])] = fm.get("status")

    candidates = []
    for t in todos:
        if t.get("status") != "open":
            continue
        tags = t.get("tags") or []
        if "forslag" in tags or "utredning" in tags:
            continue
        deps = t.get("deps") or []
        if not all(dep_satisfied(str(d), all_status) for d in deps):
            continue
        candidates.append(t)

    if not candidates:
        print("Ingen kandidat i køen.", file=sys.stderr)
        sys.exit(1)

    def sort_key(t):
        prioritized = 0 if t.get("priority") == "prioritert" else 1
        try:
            order = int(t.get("order") or 0)
        except ValueError:
            order = 0
        return (prioritized, order)

    candidates.sort(key=sort_key)
    chosen = candidates[0]
    print(f"nr={chosen.get('nr')} slug={chosen.get('slug')} path={chosen.get('_path')} "
          f"priority={chosen.get('priority')} order={chosen.get('order')}")


if __name__ == "__main__":
    main()
