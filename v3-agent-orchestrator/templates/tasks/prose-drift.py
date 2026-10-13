#!/usr/bin/env python3
"""Prosa-drift: er linja et `fil:NNN`-sitat peker på, endret siden sitatet ble skrevet?

Kall: python3 tasks/prose-drift.py [--self-test] [--list] [fil …]
Uten filer måles hele korpuset (se in_corpus). Med filer måles bare de, og hvert treff listes.

Hvert sitat sammenlignes mot git, aldri mot annen prosa: linja i base-commiten mot samme linjenummer
i HEAD, uten blanktegn i endene. Basen er planens Plan-SHA når den siterende fila har en, ellers
commiten som sist skrev sitatlinja (blame). Alt leses fra HEAD-commiten, ikke fra arbeidstreet.

Exit 0 når målingen er gjort, uansett antall treff. Exit 1 når selvtesten feiler. Exit 2 med årsak
på stderr når det ikke kan måles (git feiler, grunt klon, null sjekkbare sitater i korpuset). Da
skrives ingen `prosa-drift:`-linje, så «ikke målt» kan ikke leses som «0 drift».

Bindende: ingen.
Tallet er en trend til eieren, og plan-linjene er opplysning. Tre grunner:
- Et sitat er riktig i det det skrives. En gate på nye sitater kan aldri bli rød.
- De eksisterende treffene ville gjort en gate i helsesjekken rød fra første kjøring, og rød
  helsesjekk er pausepunkt.
- Reviewerne melder nesten ikke denne klassen lenger, så gevinsten ved å blokkere er liten.

Forfremmes når:
Plan-linjene kan bli en sjekk ved claim når tallet har stått i minst tre helsesjekker og eieren har
sett at de fører til omplanlegging som ellers ikke hadde skjedd. Doc-, kode- og todo-radene
forfremmes ikke før de eksisterende treffene er ryddet.
"""
import os
import re
import subprocess
import sys
import tempfile


EXT = "ts|tsx|js|jsx|mjs|py|sh|sql|md|json|yml|yaml"
# Et stiledd kan være (app) eller [id]. En innledende ( eller [ uten avslutning hører ikke til stien.
SEG = r"(?:\([\w-]+\)|\[[\w.-]+\]|[\w.@+-]+)"
CITE = re.compile(rf"(?<![\w./-])((?:{SEG}/)*(?:\[[\w.-]+\]|[\w.@+-])+\.(?:{EXT})):(\d+)")
PLAN_SHA = re.compile(r"^\*\*Plan-SHA:\*\*(.*)$", re.M)
TODO_FILE = re.compile(r"tasks/todos/todo-([^-/]+)-[^/]*\.md")
DOCS_SKIP = re.compile(r"handover|run-log|decision-log|retro|/plans/|/specs/|/releases/")
KINDS = ("doc", "kode", "plan", "todo")


def die(msg):
    print(f"prose-drift: {msg}", file=sys.stderr)
    sys.exit(2)


def git(*args, ok=(0,)):
    """Eneste vei til git. En feilet kommando stopper målingen, så et tomt svar aldri leses som «ingen»."""
    p = subprocess.run(["git", *args], capture_output=True, text=True, errors="replace")
    if p.returncode not in ok:
        die(f"git {args[0]} feilet: {p.stderr.strip()}")
    return p.stdout


def kind(path):
    if path.startswith("tasks/plans/"):
        return "plan"
    if path.startswith("tasks/todos/"):
        return "todo"
    return "doc" if path.endswith(".md") else "kode"


def in_corpus(path, todo_nrs):
    if path.startswith("tasks/plans/"):
        m = re.fullmatch(r"tasks/plans/todo-([^-/]+)-[^/]*\.md", path)
        return bool(m) and m[1] in todo_nrs
    if path.startswith("tasks/todos/"):
        return bool(TODO_FILE.fullmatch(path))
    if path.endswith(".md"):
        return (
            path == "CLAUDE.md"
            or bool(re.fullmatch(r"\.claude/(agents|commands)/[^/]+\.md", path))
            or (path.startswith("docs/") and not DOCS_SKIP.search(path))
        )
    return (
        path.endswith((".ts", ".tsx", ".py", ".sh"))
        and path != "tasks/prose-drift.py"  # selvtesten har sitater som testdata
        and not path.startswith(("supabase/migrations/", "v2-agent-orchestrator/"))
    )


_lines, _trees = {}, {}


def lines(commit, path):
    if (commit, path) not in _lines:
        _lines[commit, path] = git("show", f"{commit}:{path}").splitlines()
    return _lines[commit, path]


def tree(commit):
    if commit not in _trees:
        _trees[commit] = git("ls-tree", "-r", "--name-only", commit).splitlines()
    return _trees[commit]


def measure(files, listing):
    if git("rev-parse", "--is-shallow-repository").strip() == "true":
        die("grunt klon: blame peker på feil commit")
    ref = git("rev-parse", "HEAD").strip()
    head = set(tree(ref))
    if files:
        if set(files) - head:
            die(f"ikke sporet i {ref[:8]}: {sorted(set(files) - head)}")
        corpus = files
    else:
        nrs = {m[1] for f in head if (m := TODO_FILE.fullmatch(f))}
        corpus = sorted(f for f in head if in_corpus(f, nrs))

    cites = {}  # siterende fil -> [(linje, sitert sti, sitert linjenummer)]
    if corpus:
        out = git("grep", "-n", "-I", "-z", "-E", rf"\.({EXT}):[0-9]", ref, "--", *corpus, ok=(0, 1))
        for rec in out.split("\n"):
            if rec.count("\0") < 2:
                continue
            name, ln, text = rec.split("\0", 2)
            for m in CITE.finditer(text):
                cites.setdefault(name[len(ref) + 1:], []).append((int(ln), m[1], int(m[2])))

    drift, chk = dict.fromkeys(KINDS, 0), dict.fromkeys(KINDS, 0)
    unchk = ambig = badsha = 0
    hits, planlines = [], []
    for src in sorted(cites):
        k = kind(src)
        sha, blamed, d0, c0 = None, {}, drift[k], chk[k]
        m = PLAN_SHA.search("\n".join(lines(ref, src)))
        if m:
            h = re.fullmatch(r"\s*`?([0-9a-f]{40})`?\s*", m[1])
            if not h:
                badsha += 1
            elif not git("rev-parse", "-q", "--verify", h[1] + "^{commit}", ok=(0, 1)).strip():
                unchk += len(cites[src])
                planlines.append(f"plan {os.path.basename(src)}: Plan-SHA finnes ikke")
                continue
            else:
                sha = h[1]
        if not sha:
            # ponytail: blame gir commiten som sist rørte sitatlinja, ikke commiten sitatet ble skrevet i.
            # Skrives linja om, nullstilles basen (falsk negativ; målt: 3 av 24 hadde alt feil base).
            # Av et spenn (:687-689) sjekkes bare første linje. Oppgradering: mønster-anker i stedet
            # for linjenummer.
            want = sorted({ln for ln, _, _ in cites[src]})
            ranges = [a for ln in want for a in ("-L", f"{ln},{ln}")]
            for row in git("blame", "--porcelain", *ranges, ref, "--", src).split("\n"):
                b = re.fullmatch(r"([0-9a-f]{40}) \d+ (\d+)(?: \d+)?", row)
                if b:
                    blamed[int(b[2])] = b[1]
        for ln, tgt, n in cites[src]:
            base = sha or blamed[ln]
            cand = [tgt] if tgt in tree(base) else [f for f in tree(base) if f.endswith("/" + tgt)]
            if len(cand) > 1:
                ambig += 1
                continue
            if not cand or not 1 <= n <= len(lines(base, cand[0])):
                unchk += 1
                continue
            chk[k] += 1
            if cand[0] not in head:
                cls = "FIL_BORTE"
            elif n > len(lines(ref, cand[0])):
                cls = "FOR_KORT"
            elif lines(base, cand[0])[n - 1].strip() != lines(ref, cand[0])[n - 1].strip():
                cls = "ENDRET"
            else:
                continue
            drift[k] += 1
            hits.append(f"{cls} {src}:{ln} -> {cand[0]}:{n} base {base[:8]}")
        if sha and drift[k] > d0:
            planlines.append(f"plan {os.path.basename(src)}: {drift[k] - d0}/{chk[k] - c0} mot Plan-SHA {sha[:8]}")

    if not files and not sum(chk.values()):
        die("ingen sjekkbare sitater i korpuset")
    per = ", ".join(f"{k} {drift[k]}/{chk[k]}" for k in KINDS)
    print(
        f"prosa-drift: {sum(drift.values())}/{sum(chk.values())} ({per}); ikke sjekkbar {unchk}, "
        f"flertydig {ambig}, Plan-SHA utolkbar {badsha}; ref {ref[:8]}"
    )
    for line in planlines + (hits if listing or files else []):
        print(line)
    return 0


def self_test():
    me = os.path.abspath(__file__)
    env = {**os.environ, "GIT_CEILING_DIRECTORIES": tempfile.gettempdir()}
    fails = []

    def sh(cwd, *cmd):
        return subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True)

    def g(cwd, *a):
        p = sh(cwd, "git", "-c", "user.name=t", "-c", "user.email=t@t", "-c", "commit.gpgsign=false", *a)
        assert p.returncode == 0, p.stderr
        return p.stdout.strip()

    def w(cwd, path, text):
        os.makedirs(os.path.dirname(os.path.join(cwd, path)), exist_ok=True)
        with open(os.path.join(cwd, path), "w") as f:
            f.write(text)

    def check(name, want, got):
        if want == got:
            print(f"PASS {name}")
        else:
            print(f"FAIL {name}: ventet {want!r}, fikk {got!r}")
            fails.append(name)

    with tempfile.TemporaryDirectory() as tmp:
        # c1: målfiler og sitater. c2: målfilene endres. c3: planer som siterer med Plan-SHA = c1.
        r = os.path.join(tmp, "r")
        os.mkdir(r)
        g(r, "init", "-q")
        five = "".join(f"l{i}\n" for i in range(1, 6))
        for t in "abcde":
            w(r, f"src/t{t}.ts", five)
            w(r, f"{t}.md", f"se src/t{t}.ts:3\n")
        w(r, "x/dup.ts", five)
        w(r, "y/dup.ts", five)
        w(r, "f.md", "se src/finnes-ikke.ts:3\n")
        w(r, "g.md", "se dup.ts:3\n")
        g(r, "add", "-A")
        g(r, "commit", "-qm", "c1")
        c1 = g(r, "rev-parse", "HEAD")
        w(r, "src/tb.ts", "ny\n" + five)
        w(r, "src/tc.ts", five.replace("l3", "   l3  "))
        w(r, "src/td.ts", "l1\nl2\n")
        os.remove(os.path.join(r, "src/te.ts"))
        g(r, "add", "-A")
        g(r, "commit", "-qm", "c2")
        w(r, "tasks/plans/h.md", f"**Plan-SHA:** {c1}\nse src/tb.ts:3\n")
        w(r, "tasks/plans/l.md", f"**Plan-SHA:** `{c1}`\nse src/tb.ts:3\n")
        w(r, "tasks/plans/m.md", f"**Plan-SHA:** {'deadbeef' * 5}\nse src/tb.ts:3\n")
        w(r, "tasks/plans/n.md", "**Plan-SHA:** abc123\nse src/tb.ts:3\n")
        g(r, "add", "-A")
        g(r, "commit", "-qm", "c3")
        p = sh(r, sys.executable, me, "--list", *[f"{t}.md" for t in "abcdefg"],
               *[f"tasks/plans/{t}.md" for t in "hlmn"])
        out = p.stdout.splitlines()
        head1 = out[0] if out else ""

        norepo = os.path.join(tmp, "norepo")
        os.mkdir(norepo)
        pi = sh(norepo, sys.executable, me)
        e = os.path.join(tmp, "empty")
        os.mkdir(e)
        g(e, "init", "-q")
        pk = sh(e, sys.executable, me)
        w(e, "CLAUDE.md", "ingen sitater\n")
        g(e, "add", "-A")
        g(e, "commit", "-qm", "c1")
        pj = sh(e, sys.executable, me)

    def cls(src):
        return next((ln.split()[0] for ln in out if f" {src}:" in ln), "ok")

    def git_died(q):  # exit 2 fra git-hjelperen, ikke fra null-sjekkbare-vakten, og ingen tall-linje
        return (q.returncode, q.stderr.startswith("prose-drift: git ") and "ingen sjekkbare" not in q.stderr,
                "prosa-drift:" in q.stdout)

    check("a uendret", "ok", cls("a.md"))
    check("b linje satt inn over", "ENDRET", cls("b.md"))
    check("c bare innrykk", "ok", cls("c.md"))
    check("d kortet", "FOR_KORT", cls("d.md"))
    check("e slettet", "FIL_BORTE", cls("e.md"))
    # «ikke sjekkbar 2»: f.md, og det ene sitatet i m.md (Plan-SHA finnes ikke)
    check("f sti finnes aldri", ("ok", True), (cls("f.md"), "ikke sjekkbar 2," in head1))
    check("g flertydig", ("ok", True), (cls("g.md"), "flertydig 1," in head1))
    check("h Plan-SHA som base", ("ENDRET", True),
          (cls("tasks/plans/h.md"), f"plan h.md: 1/1 mot Plan-SHA {c1[:8]}" in out))
    check("i utenfor git-repo", (2, True, False), git_died(pi))
    check("j null sjekkbare", (2, True, False),
          (pj.returncode, "ingen sjekkbare" in pj.stderr, "prosa-drift:" in pj.stdout))
    check("k repo uten commit", (2, True, False), git_died(pk))
    check("l Plan-SHA i backticks", "ENDRET", cls("tasks/plans/l.md"))
    check("m Plan-SHA finnes ikke", (0, True, "ok"),
          (p.returncode, "plan m.md: Plan-SHA finnes ikke" in out, cls("tasks/plans/m.md")))
    check("n Plan-SHA utolkbar", True, "Plan-SHA utolkbar 1;" in head1)
    return 1 if fails else 0


def main(argv):
    flags = {a for a in argv if a.startswith("-")}
    if flags - {"--self-test", "--list"}:
        die(f"ukjent flagg: {sorted(flags - {'--self-test', '--list'})}")
    if "--self-test" in flags:
        return self_test()
    return measure([a for a in argv if not a.startswith("-")], "--list" in flags)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
