#!/usr/bin/env python3
"""split-lessons.py — migrer tema-filer til én fil per lesson (v3.1-formatet).

  python3 v3-agent-orchestrator/scripts/split-lessons.py            # tørrkjøring: viser planen
  python3 v3-agent-orchestrator/scripts/split-lessons.py --apply    # skriver filene, sletter temafilene
  python3 v3-agent-orchestrator/scripts/split-lessons.py --map react-native-web-modal=react-native-web
  python3 v3-agent-orchestrator/scripts/split-lessons.py --self-test

Kjøres fra prosjektroten. Leser `tasks/lessons/<fil>.md` med blokker på formen
`## YYYY-MM-DD — tittel` (også `## [YYYY-MM-DD] — tittel`) og skriver
`tasks/lessons/<tema>/<YYYY-MM-DD>-<slug>.md` med frontmatter (`tags`, `scope`, `kilder`).
`open-followups.md` går til `tasks/followups/` i stedet.

- Tema = filnavnet uten periode-suffiks (`workflow-process-sep2026` → `workflow-process`,
  `x-2026q3` → `x`). Sub-tema-filer (f.eks. `react-native-web-modal`) blir egne mapper, med
  mindre du slår dem sammen med `--map gammel=ny`.
- `kilder` fylles med `TODO-N` / `BUG-N` som står i blokken. `tags` blir tom: skriveprotokollen
  krever minst én emne-tag, så tagg filene etterpå (listen skrives ut).
- `## Se også`-seksjoner og tekst før første lesson er ikke lessons. De skrives ut i rapporten,
  slik at du kan flytte scope-linja til `tasks/lessons.md` og gjøre pekerne om til tagger.
- Innholdet i hver blokk flyttes ordrett. Antall blokker inn = antall filer ut, ellers exit 1.
Git-historikken er backupen: commit før `--apply`, så er `git checkout -- tasks/lessons` angring.
"""
import os, re, sys

DATE_H = re.compile(r"^## \[?(\d{4}-\d{2}-\d{2})\]?\s*[—–-]+\s*(.+?)\s*$")
PERIOD = re.compile(r"-(?:(?:jan|feb|mar|apr|mai|may|jun|jul|aug|sep|okt|oct|nov|des|dec)\d{4}|\d{4}q[1-4])$")
REFS = re.compile(r"\b(TODO|BUG)[\s-]?#?(\d+[A-Za-z]?)\b")


def slug(title):
    s = title.lower().replace("æ", "ae").replace("ø", "oe").replace("å", "aa")
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s[:60].rstrip("-") or "lesson"


def parse(text, any_h2=False):
    """→ (lessons [(dato|None, tittel, kropp)], rest [linjer som ikke er lessons]).
    any_h2: hver `## `-overskrift er en blokk (oppfølgingskøen har ikke alltid dato)."""
    lessons, rest, cur = [], [], None
    for line in text.split("\n"):
        m = DATE_H.match(line)
        if m or (any_h2 and line.startswith("## ")):
            cur = [m.group(1), m.group(2), []] if m else [None, line[3:].strip(), []]
            lessons.append(cur)
        elif line.startswith("## "):
            cur = None
            rest.append(line)
        elif cur is not None:
            cur[2].append(line)
        else:
            rest.append(line)
    out = []
    for d, t, body in lessons:
        while body and body[-1].strip() in ("", "---"):
            body.pop()
        while body and not body[0].strip():
            body.pop(0)
        out.append((d, t, "\n".join(body)))
    return out, [x for x in rest if x.strip() and x.strip() != "---"]


def render(date, title, body, followup):
    refs = []
    for kind, n in REFS.findall(title + "\n" + body):
        r = f"{kind}-{n.upper()}"
        if r not in refs:
            refs.append(r)
    head = f"kilder: [{', '.join(refs)}]\n" if followup else f"tags: []\nscope: project\nkilder: [{', '.join(refs)}]\n"
    return f"---\n{head}---\n\n# {title}\n\n{body}\n"


def plan(root, mapping):
    ldir = os.path.join(root, "tasks", "lessons")
    files = sorted(f for f in os.listdir(ldir) if f.endswith(".md") and os.path.isfile(os.path.join(ldir, f)))
    writes, notes, n_in = {}, [], 0
    for f in files:
        name = f[:-3]
        followup = name == "open-followups"
        theme = mapping.get(name, PERIOD.sub("", name))
        lessons, rest = parse(open(os.path.join(ldir, f), encoding="utf-8").read(), any_h2=followup)
        n_in += len(lessons)
        if rest:
            notes.append((f, rest))
        for d, t, body in lessons:
            base = os.path.join(root, "tasks", "followups" if followup else os.path.join("lessons", theme))
            stem = f"{d}-{slug(t)}" if d else slug(t)
            p, k = os.path.join(base, stem + ".md"), 2
            while p in writes or os.path.exists(p):
                p, k = os.path.join(base, f"{stem}-{k}.md"), k + 1
            writes[p] = render(d, t, body, followup)
    return files, writes, notes, n_in


def main(argv):
    if "--self-test" in argv:
        return self_test()
    mapping = dict(a.split("=", 1) for a in argv[argv.index("--map") + 1:argv.index("--map") + 2]) if "--map" in argv else {}
    files, writes, notes, n_in = plan(os.getcwd(), mapping)
    for p in sorted(writes):
        print(("SKRIV " if "--apply" in argv else "PLAN  ") + os.path.relpath(p))
    for f, rest in notes:
        print(f"\nIKKE LESSONS i {f} (flytt scope til tasks/lessons.md, gjør Se også-pekere om til tagger):")
        for x in rest:
            print("   " + x)
    print(f"\n{n_in} lesson-blokker inn, {len(writes)} filer ut, {len(files)} temafiler.")
    if n_in != len(writes):
        print("FEIL: antallet stemmer ikke — ingenting skrevet.")
        return 1
    if "--apply" in argv:
        for p, body in writes.items():
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "w", encoding="utf-8") as fh:
                fh.write(body)
        for f in files:
            os.remove(os.path.join("tasks", "lessons", f))
        print("Skrevet. Neste: tagg filene (minst én emne-tag hver) og fyll tema-scope i tasks/lessons.md.")
    else:
        print("Tørrkjøring — kjør med --apply for å skrive.")
    return 0


def self_test():
    import tempfile
    d = tempfile.mkdtemp()
    os.makedirs(os.path.join(d, "tasks", "lessons"))
    open(os.path.join(d, "tasks", "lessons", "workflow-process-sep2026.md"), "w").write(
        "# Lessons — workflow\n\n**Scope:** prosess\n\n---\n\n"
        "## 2026-09-01 — Første: ÆØÅ i tittel\n\n**Problem:** x (TODO 41, BUG-029)\n### Under\nmer\n\n---\n\n"
        "## [2026-09-02] — Andre\n\n**Problem:** y TODO 41\n\n## Se også\n\n- peker\n")
    open(os.path.join(d, "tasks", "lessons", "open-followups.md"), "w").write(
        "# Åpne\n\n## 2026-09-03 — Følg opp\n\n**Trigger:** TODO 7\n\n## CF-12 — uten dato\n\n- punkt\n")
    _, writes, notes, n_in = plan(d, {})
    rel = {os.path.relpath(p, d): b for p, b in writes.items()}
    checks = [
        (n_in == 4 and len(rel) == 4, "4 blokker inn = 4 filer ut"),
        ("tasks/followups/cf-12-uten-dato.md" in rel, "oppfølging uten dato får slug-navn"),
        ("tasks/lessons/workflow-process/2026-09-01-foerste-aeoeaa-i-tittel.md" in rel, "periode-suffiks fjernet + slug"),
        ("tasks/lessons/workflow-process/2026-09-02-andre.md" in rel, "klammeparentes-dato"),
        ("tasks/followups/2026-09-03-foelg-opp.md" in rel, "open-followups → tasks/followups/"),
        ("kilder: [TODO-41, BUG-029]" in rel.get("tasks/lessons/workflow-process/2026-09-01-foerste-aeoeaa-i-tittel.md", ""), "kilder hentet"),
        ("### Under\nmer\n" in rel.get("tasks/lessons/workflow-process/2026-09-01-foerste-aeoeaa-i-tittel.md", ""), "kropp ordrett, uten skilletegn"),
        ("- peker" not in rel.get("tasks/lessons/workflow-process/2026-09-02-andre.md", "x"), "Se også er ikke lesson-kropp"),
        (any("## Se også" in x for _, r in notes for x in r), "Se også rapporteres"),
        ("tags:" not in rel.get("tasks/followups/2026-09-03-foelg-opp.md", "tags:"), "oppfølging uten tags"),
    ]
    fails = [m for ok, m in checks if not ok]
    for ok, m in checks:
        print(("PASS " if ok else "FAIL ") + m)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
