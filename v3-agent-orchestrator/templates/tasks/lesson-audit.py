#!/usr/bin/env python3
"""Fakta per lesson til en konsolideringsrunde (tasks/lessons.md § Konsoliderings-protokoll).

  python3 tasks/lesson-audit.py                 én linje per tema, så handlingslinja
  python3 tasks/lesson-audit.py --tema <tema>   én linje per lesson i temaet, så temalinja
  python3 tasks/lesson-audit.py --self-test

Skriptet måler og foreslår. Det endrer aldri en lesson: eieren godkjenner før noe arkiveres.
Exit 0 for måling, 2 ved ukjent tema eller feil bruk, 1 ved rød selvtest.
"""
import collections
import importlib.util
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LESSONS = "tasks/lessons/"
THRESHOLD = 10  # arkiv-kandidater i ett tema før helsesjekken (A5i) sier fra
BULK = 20  # en commit som rører flere lesson-filer enn dette, er en migrering og teller ikke som «rørt»
PLACEHOLDER = ("<", ">", "*", "{", "}", "$", "…", "...")
SKIP_PREFIX = ("/", "~/", "node_modules/", "dist/", "tasks/todos/")


def load(name):
    spec = importlib.util.spec_from_file_location(name.replace("-", "_"), ROOT / "tasks" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# Gamle pekere: bare filnavn på tema-monolittene, med eller uten periode.
OLD_POINTER = re.compile(
    "(?:" + "|".join(sorted(p.name for p in (ROOT / LESSONS).iterdir() if p.is_dir())) + r")(?:-[a-z0-9]+)?\.md|open-followups\.md"
)
EXTS = "|".join(load("graph-build").FILE_EXTS + ("md",))
REF_RE = re.compile(rf"`([^`\s]+?\.(?:{EXTS}))(?::(\d+)(?:-(\d+))?)?`")


def tails(tracked):
    """Alle haler av sporede stier: «a/b/c.ts» gir a/b/c.ts, b/c.ts og c.ts."""
    return {"/".join(p[i:]) for t in tracked for p in [t.split("/")] for i in range(len(p))}


def ref_state(tok, hi, tracked, tail_set, nlines):
    """None = ikke en referanse, ellers 'levende' eller 'død'. Første regel som treffer."""
    if any(c in tok for c in PLACEHOLDER):  # plassholder eller glob
        return None
    if tok.startswith(SKIP_PREFIX) or re.fullmatch(r"tasks/lessons/[^/]+\.md", tok) or OLD_POINTER.fullmatch(tok):
        return None  # se § Gamle pekere
    archived = tok.startswith("tasks/plans/") and "tasks/plans/archive/" + tok.rsplit("/", 1)[-1] in tracked
    # ponytail: en gitignorert fil og en pakkeintern sti uten node_modules/-prefiks blir døde.
    # Utfallet er et forslag som eieren godkjenner; legg til unntak her hvis støyen blir stor.
    alive = archived or tok in tail_set
    if tok in tracked and hi > nlines(tok):  # linjenummer forbi slutten av fila
        alive = False
    return "levende" if alive else "død"


def refs(text, tracked, tail_set, nlines):
    """[(referanse som skrevet, tilstand)]. En død linjereferanse får «>linjetall» bak seg."""
    out = []
    for m in REF_RE.finditer(text):
        tok, hi = m.group(1).removeprefix("./"), int(m.group(3) or m.group(2) or 0)
        state = ref_state(tok, hi, tracked, tail_set, nlines)
        if state:
            over = f">{nlines(tok)}" if state == "død" and tok in tracked else ""
            out.append((m.group(0).strip("`") + over, state))
    return out


def fm_list(text, key):
    """Verdiene i frontmatter-linja «key: [a, b]». Tom liste uten frontmatter."""
    head = text.split("\n---", 1)[0] if text.startswith("---") else ""
    m = re.search(rf"^{key}: \[(.*)\]", head, re.M)
    return [v.strip() for v in m.group(1).split(",") if v.strip()] if m else []


def last_touched(log):
    """{lesson-sti: dato} fra «git log --format=@%cs --name-only» (nyeste først), uten bulk-commits."""
    out = {}
    for block in log.split("@")[1:]:
        date, *files = [ln for ln in block.splitlines() if ln]
        files = [f for f in files if f.startswith(LESSONS)]
        if len(files) <= BULK:
            for f in files:
                out.setdefault(f, date)
    return out


def sist(path, touched):
    return touched.get(path) or path.rsplit("/", 1)[-1][:10]


def cite_counts(texts):
    """{«<tema>/<filnavn uten .md>»: antall filer utenfor tasks/lessons/ som nevner lesson-stien}.
    ponytail: teller bare den nye stiformen, ikke «lesson <dato>, «tittel»» eller gamle tema-fil-pekere."""
    n = collections.Counter()
    for path, text in texts.items():
        if not path.startswith(LESSONS):
            n.update(set(re.findall(r"tasks/lessons/([a-z0-9-]+/[a-z0-9-]+)", text)))
    return n


def gate_of(subject, compiled, gates):
    """(klasse, gate) etter første treff i lesson-classes.py sin COMPILED. ('-', '-') uten klasse."""
    for k, _, rx in compiled:
        if rx.search(subject):
            g = gates.get(k, "")
            return k, "delvis" if g.startswith("delvis") else "nei" if not g or g.startswith("ikke gatebar") else "ja"
    return "-", "-"


def clusters(tagsets):
    """{lesson: 'a+b'} for lessons som deler et identisk tagg-sett på minst to tagger med en annen."""
    keys = {name: "+".join(sorted(set(tags))) for name, tags in tagsets.items() if len(set(tags)) >= 2}
    seen = collections.Counter(keys.values())
    return {name: k for name, k in keys.items() if seen[k] >= 2}


def kandidat(n_refs, n_dead, sitert, kilder):
    """GLEMSELSREGELEN. Eneste sted den står. Endres den, blir S10 rød."""
    return n_refs >= 1 and n_dead == n_refs and sitert == 0 and kilder <= 1


def action_line(per_tema):
    tema, k = max(per_tema.items(), key=lambda kv: kv[1], default=("", 0))
    if k >= THRESHOLD:
        return (f"KONSOLIDERING: {tema} har {k} arkiv-kandidater (terskel {THRESHOLD}). "
                "Se tasks/lessons.md § Konsoliderings-protokoll.")
    return f"Ingen tema over terskelen ({THRESHOLD})."


def self_test():
    ok = True

    def check(name, got, want):
        nonlocal ok
        good = got == want
        ok &= good
        print(f"{'ok ' if good else 'RØD'}  {name}" + ("" if good else f": fikk {got!r}, ventet {want!r}"))

    tracked = {"lib/a.ts", "lib/actions/search.ts", "tasks/plans/archive/x.md"}
    ts, nl = tails(tracked), lambda p: 10

    def state(tok):
        return ref_state(tok, 0, tracked, ts, nl)

    check("S1 eksakt sporet sti", state("lib/a.ts"), "levende")
    check("S2 usporet sti", state("lib/borte.ts"), "død")
    check("S3 hale av sporet sti", state("actions/search.ts"), "levende")
    check("S4 ukjent filnavn", state("borte.ts"), "død")
    skipped = ("`node_modules/x.js` `/manifest.json` `tasks/lessons/workflow-process-sep2026.md` "
               "`tasks/todos/todo-1-a.md` `supabase/migrations/*.sql` `.claude/agent-memory/<agent>/MEMORY.md`")
    check("S5 ikke referanser", len(refs(skipped, tracked, ts, nl)), 0)
    check("S6 linjenummer", refs("`lib/a.ts:5` `lib/a.ts:9-12`", tracked, ts, nl),
          [("lib/a.ts:5", "levende"), ("lib/a.ts:9-12>10", "død")])
    fm = "---\ntags: [x]\nkilder: [%s]\n---\n# T\n"
    check("S7 kilder", [len(fm_list(t, "kilder")) for t in (fm % "", fm % "TODO-1", fm % "TODO-1, BUG-2, TODO-3", "# T\n")],
          [0, 1, 3, 0])
    a, b = LESSONS + "t/2026-01-01-a.md", LESSONS + "t/2026-01-02-b.md"
    bulk = "\n".join([a, b] + [f"{LESSONS}t/l{i}.md" for i in range(19)])
    touched = last_touched(f"@2026-10-01\n{bulk}\n\n@2026-09-01\n{a}\n")
    check("S8 bulk-commit utelates", [sist(a, touched), sist(b, touched)], ["2026-09-01", "2026-01-02"])
    cite = "se tasks/lessons/t/2026-01-01-a.md"
    check("S9 sitert", cite_counts({"docs/x.md": cite + " og " + cite, "CLAUDE.md": cite, b: cite})["t/2026-01-01-a"], 2)
    check("S10 glemselsregelen",
          ["ja" if kandidat(*c) else "nei" for c in ((2, 2, 0, 1), (2, 1, 0, 1), (2, 2, 1, 1), (2, 2, 0, 2), (0, 0, 0, 1))],
          ["ja", "nei", "nei", "nei", "nei"])
    check("S11 tagg-klynger", clusters({"1": ["a", "b"], "2": ["b", "a"], "3": ["a"], "4": ["a"]}), {"1": "a+b", "2": "a+b"})
    comp = [(k, "", re.compile(k)) for k in ("reell", "halv", "ugatebar", "tom")]
    gates = {"reell": "hook x", "halv": "delvis: y", "ugatebar": "ikke gatebar: z", "tom": ""}
    check("S12 gate", [gate_of(s, comp, gates)[1] for s in ("reell", "halv", "ugatebar", "tom", "annet")],
          ["ja", "delvis", "nei", "nei", "-"])
    check("S13 handlingslinja", [action_line({"a": 3, "b": n})[:14] for n in (9, 10)], ["Ingen tema ove", "KONSOLIDERING:"])
    check("S14 planpeker via arkivet", [state("tasks/plans/x.md"), state("tasks/plans/y.md")], ["levende", "død"])
    check("S15 hjemmekatalog og ./", refs("`~/.claude/x.json` `./lib/a.ts` `./lib/borte.ts`", tracked, ts, nl),
          [("./lib/a.ts", "levende"), ("./lib/borte.ts", "død")])
    check("S16 gamle pekere uten sti", [state(t) for t in ("migrations.md", "workflow-process-jun2026.md", "open-followups.md", "borte.md")],
          [None, None, None, "død"])
    return 0 if ok else 1


def git(*args):
    return subprocess.run(("git", "-c", "core.quotepath=off") + args, cwd=ROOT, capture_output=True, text=True, check=True).stdout


def main(argv):
    if argv == ["--self-test"]:
        return self_test()
    temas = sorted(p.name for p in (ROOT / LESSONS).iterdir() if p.is_dir())
    only = argv[1] if len(argv) == 2 and argv[0] == "--tema" else None
    if (argv and not only) or (only and only not in temas):
        print(__doc__ if not only else f"FEIL: tema {only!r} finnes ikke (finnes: {', '.join(temas)})", file=sys.stderr)
        return 2
    tracked = set(git("ls-files", "-z").split("\0")) - {""}
    tail_set = tails(tracked)
    texts = {}
    for p in tracked:
        try:
            texts[p] = (ROOT / p).read_text(errors="ignore")
        except OSError:  # slettet i arbeidstreet, eller en lenke uten mål
            pass

    def nlines(p):  # 0 linjer for en sporet fil som ikke lar seg lese
        return len(texts.get(p, "").splitlines())

    cited = cite_counts(texts)
    touched = last_touched(git("log", "--format=@%cs", "--name-only", "--", LESSONS))
    lc = load("lesson-classes")
    per_tema = {}
    for tema in [only] if only else temas:
        files = {p.name: p.read_text(encoding="utf-8") for p in sorted((ROOT / LESSONS / tema).glob("*.md"))}
        klynge = clusters({n: fm_list(t, "tags") for n, t in files.items()})
        n_dead = n_kand = 0
        for name, text in files.items():
            found = refs(text, tracked, tail_set, nlines)
            dead = list(dict.fromkeys(r for r, s in found if s == "død"))
            n_dead_refs = sum(s == "død" for _, s in found)
            kilder, sitert = len(fm_list(text, "kilder")), cited[f"{tema}/{name[:-3]}"]
            kand = kandidat(len(found), n_dead_refs, sitert, kilder)
            n_dead += bool(dead)
            n_kand += kand
            if only:
                title = re.search(r"^# (.+)$", text, re.M)
                subject = " ".join([title.group(1) if title else ""] + re.findall(r"^\*\*Problem:\*\*(.*)$", text, re.M))
                klasse, gate = gate_of(subject, lc.COMPILED, lc.GATES)
                print("\t".join([name, f"kilder={kilder}", f"sitert={sitert}", f"sist={sist(LESSONS + tema + '/' + name, touched)}",
                                 f"klasse={klasse}", f"gate={gate}", f"klynge={klynge.get(name, '-')}",
                                 f"dode={','.join(dead) or '-'}", f"kandidat={'ja' if kand else 'nei'}"]))
        per_tema[tema] = n_kand
        print(f"{tema}: {len(files)} lessons, {n_dead} med død referanse, {n_kand} arkiv-kandidater, "
              f"{len(set(klynge.values()))} tagg-klynger")
    if not only:
        print(action_line(per_tema))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
