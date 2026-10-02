#!/usr/bin/env python3
"""Releaser: mål, scope og fremdrift for loopen.

  python3 tasks/release.py status            den aktive releasen: fremdrift og dom
  python3 tasks/release.py scope <versjon>   todo-nr i scope, ett per linje
  python3 tasks/release.py notes <versjon>   release notes fra arkivet (markdown)
  python3 tasks/release.py --self-test

En release er fila tasks/releases/<versjon>.md (skjema: tasks/releases/README.md). Filnavnet er
versjonen. Scope er alle todoer med `release: <versjon>`, både åpne i tasks/todos/ og arkiverte i
tasks/todo_archive.md (linja `**Release:**` i arkivoppføringen).

`status` skriver fremdriften og avslutter med en DOM-linje:
  exit 0  DOM: PÅGÅR (åpne todoer i scope), eller DOM: INGEN AKTIV RELEASE
  exit 1  DOM: MÅL NÅDD eller DOM: MÅL IKKE NÅDD. Scope er tomt, og loopen stopper (§1).
  exit 2  FEIL: flere aktive releaser, eller en todo peker på en release som ikke finnes.
          En skrivefeil i `release:` ville ellers tatt todoen stille ut av scope.

Todoen med taggen `prod-release` er releasens egen prod-todo. Den eies av mennesket, telles ikke
som åpen, og loopen claimer den aldri.
"""
import glob, os, re, subprocess, sys
from datetime import date

REL_DIR, TODO_GLOB, ARCHIVE = "tasks/releases", "tasks/todos/todo-*.md", "tasks/todo_archive.md"
OPEN = ("open", "reviewed", "in_progress")


def value(raw):
    """Innholdet i "…", ellers alt før en ` #`-kommentar. Samme regel i §1 og queue-status.py, så de
    tre er enige om scope."""
    raw = raw.strip()
    q = re.match(r'"([^"]*)"', raw)
    return q.group(1) if q else re.sub(r"\s+#.*$", "", raw)


def fm(path):
    t = open(path, encoding="utf-8").read()
    m = re.search(r"^---\n(.*?)\n---", t, re.S)
    d = {"_path": path, "_body": t[m.end():] if m else t}
    for line in (m.group(1).splitlines() if m else []):
        mm = re.match(r"(\w+):\s*(.*)", line)
        if mm:
            d[mm.group(1)] = value(mm.group(2))
    return d


def releases():
    return {os.path.basename(p)[:-3]: fm(p)
            for p in glob.glob(f"{REL_DIR}/*.md") if os.path.basename(p) != "README.md"}


def todos():
    return [fm(p) for p in glob.glob(TODO_GLOB)]


def archived():
    """[(nr, tittel, release, epic, pr)] fra arkivet. Oppføringer uten Release-linje får '-'."""
    if not os.path.exists(ARCHIVE):
        return []
    text = open(ARCHIVE, encoding="utf-8").read()
    out = []
    for m in re.finditer(r"^## TODO[ -](\S+) — (.*)$", text, re.M):
        sec = text[m.end():].split("\n## ", 1)[0]
        f = lambda k: (re.search(rf"^\*\*{k}:\*\*\s*(.*)$", sec, re.M) or [None, "-"])[1].strip() or "-"
        out.append((m.group(1), m.group(2).strip(), f("Release"), f("Epic"), f("PR")))
    return out


def is_prod(d):
    return bool(re.search(r"\bprod-release\b", d.get("tags", "") or ""))


def done_when(body):
    """(avkrysset, totalt) i `## done_when`-seksjonen."""
    sec = re.split(r"^## done_when.*$", body, maxsplit=1, flags=re.M)
    if len(sec) < 2:
        return 0, 0
    sec = re.split(r"^## ", sec[1], maxsplit=1, flags=re.M)[0]
    boxes = re.findall(r"^\s*- \[([ xX])\]", sec, re.M)
    return sum(b in "xX" for b in boxes), len(boxes)


def added_on(path):
    """Datoen fila først ble committet. None = ikke i et git-repo; i dag = ikke committet ennå."""
    r = subprocess.run(["git", "log", "--diff-filter=A", "--format=%cs", "--", path],
                       capture_output=True, text=True)
    if r.returncode != 0:
        return None
    lines = r.stdout.split()
    return lines[-1] if lines else date.today().isoformat()


def scope(version):
    nrs = [d["nr"] for d in todos() if d.get("release") == version and d.get("nr")]
    return nrs + [a[0] for a in archived() if a[2] == version and a[0] not in nrs]


def status():
    rels, ts = releases(), todos()
    errors = [f"FEIL: TODO {d.get('nr', '?')} har `release: {d['release']}`, men "
              f"{REL_DIR}/{d['release']}.md finnes ikke"
              for d in ts if d.get("release") and d["release"] not in rels]
    active = sorted(v for v, r in rels.items() if r.get("status") == "active")
    if len(active) > 1:
        errors.append(f"FEIL: flere aktive releaser ({', '.join(active)}). Bare én kan være `active`.")
    if errors:
        return 2, errors
    if not active:
        return 0, ["DOM: INGEN AKTIV RELEASE"]
    v, rel = active[0], rels[active[0]]
    mine = [d for d in ts if d.get("release") == v]
    prod = [d for d in mine if is_prod(d)]
    work = [d for d in mine if not is_prod(d)]
    arch = [a for a in archived() if a[2] == v]
    open_ = [d for d in work if d.get("status") in OPEN]
    done = len(arch) + sum(d.get("status") == "done" for d in work)
    total = len(open_) + done
    ok, n = done_when(rel["_body"])
    out = [f"RELEASE {v} — mål: {rel.get('goal') or '(mangler goal)'}",
           f"scope {done}/{total} ferdige · åpne {len(open_)} · done_when {ok}/{n} · "
           f"cut-off {rel.get('cutoff') or '-'}"]
    epics = {}
    for d in work:
        if d.get("epic") and d.get("status") != "split":
            e = epics.setdefault(d["epic"], [0, 0]); e[1] += 1; e[0] += d.get("status") == "done"
    for a in arch:
        if a[3] != "-":
            e = epics.setdefault(a[3], [0, 0]); e[1] += 1; e[0] += 1
    if epics:
        out.append(" · ".join(f"epic {k} {a}/{b}" for k, (a, b) in sorted(epics.items())))
    out.append(f"prod-release: {', '.join('TODO ' + d['nr'] for d in prod) or '-'}")
    if not prod:
        out.append(f"ADVARSEL: ingen todo med `release: {v}` og taggen `prod-release`. Opprett den "
                   "(eier: mennesket), så loopen vet hvem som tar releasen til prod.")
    if n == 0:
        out.append("ADVARSEL: `## done_when` mangler eller er tom. Målet kan aldri meldes nådd.")
    for d in work:
        if d.get("status") == "deferred":
            out.append(f"ADVARSEL: TODO {d['nr']} er utsatt, men står i scope. Flytt den til en annen "
                       "release eller fjern `release:`.")
    cut = rel.get("cutoff", "")
    if re.match(r"\d{4}-\d{2}-\d{2}$", cut):
        for d in open_:
            when = d.get("release_blocker") != "true" and added_on(d["_path"])
            if when and when > cut:
                out.append(f"ADVARSEL: TODO {d['nr']} kom inn i scope {when}, etter cut-off {cut}, uten "
                           "`release_blocker: true`. Flytt den til neste release, eller merk den "
                           "som blokkerende med én linje begrunnelse.")
    if open_:
        return 0, out + ["DOM: PÅGÅR"]
    if n and ok == n:
        who = ", ".join("TODO " + d["nr"] for d in prod) or "prod-release-todoen (mangler)"
        return 1, out + [f"DOM: MÅL NÅDD — klar for prod: {who}"]
    return 1, out + [f"DOM: MÅL IKKE NÅDD — scope er tomt, done_when {ok}/{n}"]


def notes(version):
    rel = releases().get(version)
    if rel is None:
        return 2, [f"FEIL: {REL_DIR}/{version}.md finnes ikke"]
    by_epic = {}
    for nr, title, r, epic, pr in archived():
        if r == version:
            by_epic.setdefault(epic, []).append(f"- {title} (TODO {nr}" + (f", PR {pr})" if pr != "-" else ")"))
    out = [f"# Release {version}", "", f"**Mål:** {rel.get('goal') or '-'}", ""]
    for epic in sorted(by_epic, key=lambda e: (e == "-", e)):
        out += [f"## {'Øvrig' if epic == '-' else epic}", ""] + by_epic[epic] + [""]
    return 0, out


def self_test():
    import tempfile
    cwd, fails = os.getcwd(), 0

    def w(path, text):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        open(path, "w", encoding="utf-8").write(text)

    def todo(nr, st, rel=None, tags="[]", extra=""):
        r = f'release: "{rel}"\n' if rel else ""
        w(f"tasks/todos/todo-{nr}-x.md", f'---\nnr: "{nr}"\nstatus: {st}\ntags: {tags}\n{r}{extra}---\nTekst.\n')

    def rel(v, st, boxes="- [x] a\n- [x] b\n", cutoff=""):
        w(f"{REL_DIR}/{v}.md", f'---\nstatus: {st}\ngoal: "Mål {v}"\ncutoff: "{cutoff}"\n---\n'
                               f"## done_when\n{boxes}\n## Epics\n- [ ] ikke en done_when-boks\n")

    def check(name, want_code, want_text, fn=status):
        nonlocal fails
        code, lines = fn()
        ok = code == want_code and any(want_text in l for l in lines)
        fails += not ok
        print(("PASS " if ok else "FAIL ") + name + ("" if ok else f" → exit {code}: {lines}"))

    with tempfile.TemporaryDirectory() as tmp:
        os.chdir(tmp)
        try:
            check("ingen release → INGEN AKTIV, exit 0", 0, "INGEN AKTIV")
            w(f"{REL_DIR}/0.1.0.md", '---\nstatus: active   # planned | active | shipped\ngoal: "Mål #1"\n---\n')
            todo("7", "open", extra='release: "0.1.0"   # kommentar\n')
            check("inline-kommentarer: status og release leses uten kommentaren", 0, "mål: Mål #1")
            check("inline-kommentarer: todoen er i scope", 0, "åpne 1 ")
            os.remove(f"{REL_DIR}/0.1.0.md"); os.remove("tasks/todos/todo-7-x.md")
            rel("1.0.0", "active"); todo("1", "open", "1.0.0", extra='epic: "deling"\n')
            todo("2", "open", "1.0.0", tags="[prod-release]"); todo("3", "open")
            check("åpen todo i scope → PÅGÅR, exit 0", 0, "DOM: PÅGÅR")
            check("prod-release-todoen teller ikke som åpen", 0, "åpne 1 ")
            todo("1", "done", "1.0.0", extra='epic: "deling"\n')
            w(ARCHIVE, "## TODO 0 — Arkivert sak\n**Release:** 1.0.0\n**Epic:** deling\n**PR:** #7\n\n"
                       "## TODO 9 — Annen release\n**Release:** 0.9.0\n")
            check("scope tomt + alle done_when → MÅL NÅDD med prod-todo, exit 1", 1, "klar for prod: TODO 2")
            check("arkivert todo teller som ferdig, epic-boks teller ikke", 1, "scope 2/2 ferdige · åpne 0 · done_when 2/2")
            check("epic summeres fra fil og arkiv", 1, "epic deling 2/2")
            rel("1.0.0", "active", boxes="- [x] a\n- [ ] b\n")
            check("scope tomt + done_when 1/2 → MÅL IKKE NÅDD, exit 1", 1, "MÅL IKKE NÅDD")
            check("notes lister arkivert todo under epic", 0, "- Arkivert sak (TODO 0, PR #7)", lambda: notes("1.0.0"))
            check("scope gir fil + arkiv", 0, "0", lambda: (0, scope("1.0.0")))
            todo("4", "open", "1.0.1")
            check("ukjent release på todo → FEIL, exit 2", 2, "1.0.1.md finnes ikke")
            os.remove("tasks/todos/todo-4-x.md"); rel("2.0.0", "active")
            check("to aktive releaser → FEIL, exit 2", 2, "flere aktive")
            os.remove(f"{REL_DIR}/2.0.0.md")
            subprocess.run(["git", "init", "-q"], check=True)   # ekte tilfelle: repo med commits, ny fil
            subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q",
                            "--allow-empty", "-m", "init"], check=True)
            rel("1.0.0", "active", cutoff="2000-01-01"); todo("5", "open", "1.0.0")
            check("ny todo etter cut-off uten release_blocker → ADVARSEL", 0, "TODO 5 kom inn i scope")
            todo("5", "open", "1.0.0", extra="release_blocker: true\n")
            code, lines = status()
            ok = not any("TODO 5 kom inn" in l for l in lines)
            fails += not ok
            print(("PASS " if ok else "FAIL ") + "release_blocker: true slipper gjennom cut-off")
        finally:
            os.chdir(cwd)
    return 1 if fails else 0


def main(argv):
    if "--self-test" in argv:
        return self_test()
    cmd = argv[0] if argv else "status"
    if cmd == "status":
        code, lines = status()
    elif cmd in ("scope", "notes") and len(argv) == 2:
        code, lines = (0, scope(argv[1])) if cmd == "scope" else notes(argv[1])
    else:
        print(__doc__, file=sys.stderr)
        return 2
    print("\n".join(lines))
    return code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
