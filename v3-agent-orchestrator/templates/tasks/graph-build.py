#!/usr/bin/env python3
# GENERERT av /setup fra loop.config.yaml — IKKE rediger her.
# Endre loop.config.yaml og kjør /setup på nytt.
"""graph-build.py — utleder en kantgraf fra tasks/-kilder og skriver JSON til stdout.

Grafen gjor kanter som allerede star skrevet i prosa (todo <-> bug <-> PR <-> fil <-> lesson)
adresserbare. Den bygges on-demand og sjekkes ALDRI inn — se .gitignore for tasks/graph.json.

Bruk:
    python3 tasks/graph-build.py              # JSON til stdout (produksjonsstien)
    python3 tasks/graph-build.py --out FIL     # skriv i tillegg til FIL — KUN feilsoking,
                                                # committes aldri. FIL tolkes relativt til
                                                # arbeidskatalogen du kjorte fra, ikke repo-roten.
    python3 tasks/graph-build.py --check-todo FIL [FIL ...]   # vakt i stedet for bygg: exit 1
                                                # nar en todo navngir en fil/bug uten files:/bugs:
    python3 tasks/graph-build.py --lint       # hygiene-tall i stedet for JSON, alltid exit 0

All diagnostikk (advarsler, feil) gar til stderr. stdout inneholder KUN JSON-objektet
{"nodes": {...}, "edges": [...], "stats": {...}}.

Kilder (seks, alle fail-soft hver for seg — mangler en kilde hopper byggeren over den og
teller det i stats.missing_sources i stedet for a kaste):
  1. Frontmatter i tasks/todos/*.md          (deps/bugs/files/lessons; lister inline eller i blokkform)
  2. tasks/lessons/<tema>/*.md + tasks/followups/*.md  (en fil = en node: TODO/BUG/fil-mentions
                                              i teksten + frontmatter-feltet kilder)
  3. tasks/todo_archive.md                    (BUG-mentions, /pull/-lenker)
  4. git-historikk                            (commit-subject "TODO n" -> rorte filer)
  5. tasks/bugs.md + tasks/bugs_archive.md    (Status-triage, fil-mentions, PR-lenker)
  6. docs/*.md, ikke rekursivt     (en H2/H3-seksjon = en doc:-node; documents-kant til
                                              hver fil seksjonen siterer, mentions til TODO/BUG)
"""
import argparse
import datetime
import glob
import json
import os
import re
import subprocess
import sys

FILE_EXTS = ("tsx", "ts", "jsx", "js", "mjs", "sql", "py", "sh", "json", "yaml", "yml")
_EXT_ALT = "|".join(FILE_EXTS)

# Backtick-sitert filsti, valgfritt etterfulgt av :linje eller :linje-linje (bindestrek/en-dash).
BACKTICK_FILE_RE = re.compile(
    r"`([A-Za-z0-9_./()\[\]-]+\.(?:" + _EXT_ALT + r"))(?::[\d,–-]+)?`"
)
# Markdown-lenkemål [tekst](sti), tolererer ett niva parentes i stien (Expo-rutegrupper: app/(app)/x.tsx).
LINK_FILE_RE = re.compile(
    r"\]\(((?:[^()\s]|\([^()\s]*\))*\.(?:" + _EXT_ALT + r"))\)"
)
# Én delt ID-fragment: sub-ID-er som 197B2 og 66c1 har siffer etter bokstav.
_TODO_ID = r"\d+[A-Za-z0-9]*"
TODO_REF_RE = re.compile(r"TODO\s+(" + _TODO_ID + r")")
# Git-commit-subjekter bruker ofte conventional-commit-scope-formen "(todo-NN)" i tillegg til
# prosa-formen "TODO NN" — case-insensitivt og med bindestrek ELLER mellomrom (M-9, funnet ved
# V1-verifisering: todo:28a/todo:116/todo:138 er kun nabare via denne bredere formen).
GIT_TODO_REF_RE = re.compile(r"TODO[ -](" + _TODO_ID + r")", re.IGNORECASE)
BUG_REF_RE = re.compile(r"BUG-(\d+)")
PR_LINK_RE = re.compile(r"/pull/(\d+)")
# Kun Status-linja: "triagert til TODO n" ELLER "kode-fikset (TODO n" — begge malte former (M10).
TRIAGE_RE = re.compile(r"(?:triagert til TODO|kode-fikset \(TODO)\s+(" + _TODO_ID + r")")


def norm_id(raw):
    """En eneste vei til en todo:-node (V-7). Stripper norsk-genitiv 's' og ledende nuller,
    og gir små bokstaver (427B og 427b er samme node)."""
    s = raw.strip()
    if len(s) > 1 and s[-1] == "s" and s[-2].isdigit():
        s = s[:-1]
    m = re.match(r"0*(\d+)(.*)$", s)
    if m:
        digits, suffix = m.group(1), m.group(2)
        s = (digits or "0") + suffix
    return s.lower()


def extract_file_tokens(text):
    tokens = []
    for m in BACKTICK_FILE_RE.finditer(text):
        tokens.append(m.group(1))
    for m in LINK_FILE_RE.finditer(text):
        tokens.append(m.group(1))
    return tokens


def read(path):
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


def resolve_root():
    """ROOT utledes, aldri antatt (3.3 mekanisme 1). Returnerer (root, opprinnelig_cwd)."""
    orig_cwd = os.getcwd()
    try:
        r = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True
        )
    except FileNotFoundError:
        sys.exit("FEIL: git-kommandoen ble ikke funnet — graph-build.py krever git.")
    if r.returncode != 0 or not r.stdout.strip():
        sys.exit("FEIL: ikke i et git-repo — graph-build.py krever repo-rot.")
    return r.stdout.strip(), orig_cwd


def git_ls_files():
    r = subprocess.run(["git", "ls-files"], capture_output=True, text=True)
    if r.returncode != 0:
        return []
    return r.stdout.splitlines()


def build_file_index(all_files):
    """Kun kode/config-filer (2.5) — .md er bevisst utelatt, de er kilder, ikke mal."""
    code_files = sorted(f for f in all_files if f.rsplit(".", 1)[-1] in FILE_EXTS and "." in f)
    exact = set(code_files)
    by_base = {}
    for f in code_files:
        by_base.setdefault(f.rsplit("/", 1)[-1], []).append(f)
    return exact, by_base


def make_resolver(exact_index, by_base, stats):
    def resolve_file(token):
        token = token.strip()
        if token in exact_index:
            return token
        base = token.rsplit("/", 1)[-1]
        cands = by_base.get(base)
        if cands and len(cands) == 1:
            return cands[0]
        if cands and len(cands) > 1:
            stats["file_token_ambiguous"] += 1
            return None
        stats["file_token_unresolved"] += 1
        return None

    return resolve_file


def parse_inline_list(raw):
    """Inline-listeform (`["a", "b"]`). Blokkform leses av read_frontmatter."""
    raw = raw.strip()
    if not raw.startswith("["):
        return []
    inner = raw[1:-1] if raw.endswith("]") else raw[1:]
    items = []
    for a, b, c in re.findall(r"\"([^\"]*)\"|'([^']*)'|([^,\[\]\"'\s][^,\[\]]*)", inner):
        v = (a or b or c).strip()
        if v:
            items.append(v)
    return items


def read_frontmatter(text):
    """Returnerer (fields, body). Et listefelt blir en liste uansett form: inline (`["a", "b"]`)
    eller blokk (nøkkel på egen linje, `- sti` under). Øvrige felt er rå strenger."""
    m = re.match(r"^---\n(.*?)\n---\n?", text, re.S)
    if not m:
        return {}, text
    fields, key = {}, None
    for line in m.group(1).splitlines():
        mm = re.match(r"([A-Za-z_]+):\s*(.*)$", line)
        if mm:
            key, val = mm.group(1), mm.group(2)
            fields[key] = parse_inline_list(val) if val.lstrip().startswith("[") else val
            continue
        bm = re.match(r"\s*-\s+(.*)$", line)
        if bm and key and not (isinstance(fields[key], str) and fields[key].strip()):
            if isinstance(fields[key], str):
                fields[key] = []
            fields[key].append(bm.group(1).strip().strip("\"'"))
    return fields, text[m.end():]


def _list(fields, key):
    v = fields.get(key)
    return v if isinstance(v, list) else []


def split_h2_sections(lines):
    """Returnerer [(start_idx, end_idx, heading_text)] for hver '## '-overskrift i lines."""
    idxs = [i for i, l in enumerate(lines) if l.startswith("## ")]
    idxs.append(len(lines))
    out = []
    for k in range(len(idxs) - 1):
        start, end = idxs[k], idxs[k + 1]
        out.append((start, end, lines[start][3:].strip()))
    return out


def process_todos(add_edge, resolve_file, stats):
    paths = sorted(glob.glob("tasks/todos/todo-*.md"))
    if not paths:
        stats["missing_sources"].append("tasks/todos/")
        return set()
    active_nrs = set()
    for p in paths:
        fields, _body = read_frontmatter(read(p))
        if not fields:
            continue
        nr_raw = fields.get("nr", "")
        nr_raw = nr_raw.strip().strip('"').strip("'") if isinstance(nr_raw, str) else ""
        if not nr_raw:
            stats["todos_skipped_no_nr"] += 1
            continue
        nr = norm_id(nr_raw)
        active_nrs.add(nr)
        stats["todos_total_files"] += 1

        for d in _list(fields, "deps"):
            add_edge(f"todo:{nr}", "deps", f"todo:{norm_id(d)}")
        for b in _list(fields, "bugs"):
            bid = b if b.upper().startswith("BUG-") else f"BUG-{b}"
            add_edge(f"todo:{nr}", "bug", f"bug:{bid}")
        for f in _list(fields, "files"):
            rf = resolve_file(f)
            if rf:
                add_edge(f"todo:{nr}", "file", f"file:{rf}")
        for th in _list(fields, "lessons"):
            add_edge(f"todo:{nr}", "lesson_theme", f"theme:{th}")

    return active_nrs


def check_todos(paths, orig_cwd, resolve_file):
    """--check-todo: vakt for nye todo-filer. Returnerer exit-koden.

    Beviser at en utelatelse er bevisst, ikke at lista er sann: `files: []` og `bugs: []`
    passerer alltid, og R1 ser bare det resolve_file løser (kode-/config-fil i backticks
    eller som lenkemål, entydig basenavn)."""
    red = False
    for arg in paths:
        try:
            fields, body = read_frontmatter(read(arg if os.path.isabs(arg) else os.path.join(orig_cwd, arg)))
        except OSError as exc:
            sys.stderr.write(f"FEIL: kan ikke lese {arg}: {exc}\n")
            return 2
        named = sorted({rf for rf in map(resolve_file, extract_file_tokens(body)) if rf})
        bugs = sorted({f"BUG-{n}" for n in BUG_REF_RE.findall(body)})
        msgs = []
        if "files" not in fields and named:
            msgs.append(
                f"files mangler — brødteksten navngir {len(named)} fil(er), f.eks. {named[0]}. "
                "Skriv files: [...] eller files: []."
            )
        if "bugs" not in fields and bugs:
            msgs.append(
                f"bugs mangler — brødteksten navngir {len(bugs)} bug(s), f.eks. {bugs[0]}. "
                "Skriv bugs: [...] eller bugs: []."
            )
        if "pr" in fields:
            msgs.append("feltet pr er strøket")
        for msg in msgs:
            red = True
            sys.stderr.write(f"{arg}: {msg}\n")
    return 1 if red else 0


def process_notes(add_edge, resolve_file, stats, base, prefix):
    """En fil = en node. Node-ID: <prefix>:<sti under base, uten .md>.

    Kanter: TODO/BUG/fil-mentions i teksten etter frontmatter (tittel inkludert), pluss
    frontmatter-feltet `kilder` (`TODO-NN`/`BUG-NNN`). `tags` gir bevisst ingen kanter."""
    paths = sorted(glob.glob(f"{base}/**/*.md", recursive=True))
    for p in paths:
        text = read(p)
        refs = []
        m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
        if m:
            text = text[m.end():]
            for line in m.group(1).splitlines():
                if line.startswith("kilder:"):
                    refs = parse_inline_list(line.split(":", 1)[1])
        node = f"{prefix}:{os.path.relpath(p, base)[:-3]}"
        stats[f"{prefix}_nodes"] += 1
        for tm in TODO_REF_RE.finditer(text):
            add_edge(node, "mentions", f"todo:{norm_id(tm.group(1))}")
        for bm in BUG_REF_RE.finditer(text):
            add_edge(node, "mentions", f"bug:BUG-{bm.group(1)}")
        for ref in refs:
            kind, _, num = ref.partition("-")
            if kind == "TODO" and num:
                add_edge(node, "mentions", f"todo:{norm_id(num)}")
            elif kind == "BUG" and num:
                add_edge(node, "mentions", f"bug:{ref}")
        for token in extract_file_tokens(text):
            rf = resolve_file(token)
            if rf:
                add_edge(node, "file", f"file:{rf}")
    return paths


def process_archive(add_edge, stats):
    path = "tasks/todo_archive.md"
    if not os.path.exists(path):
        stats["missing_sources"].append(path)
        return set()
    text = read(path)
    lines = text.splitlines()
    archive_nrs = set()
    for start, end, heading_text in split_h2_sections(lines):
        hm = re.match(r"^TODO\s+(" + _TODO_ID + r")", heading_text)
        if not hm:
            continue
        nr = norm_id(hm.group(1))
        archive_nrs.add(nr)
        entry_text = "\n".join(lines[start:end])
        seen_bugs = set()
        for bm in BUG_REF_RE.finditer(entry_text):
            bid = f"BUG-{bm.group(1)}"
            if bid not in seen_bugs:
                seen_bugs.add(bid)
                add_edge(f"todo:{nr}", "bug", f"bug:{bid}")
        seen_prs = set()
        for pm in PR_LINK_RE.finditer(entry_text):
            prn = pm.group(1)
            if prn not in seen_prs:
                seen_prs.add(prn)
                add_edge(f"todo:{nr}", "pr", f"pr:{prn}")
    return archive_nrs


PR_MERGE_SUBJECT_RE = re.compile(r"^Merge pull request #\d+ from ")


def process_git(add_edge, exact_index, stats):
    """Kilde 4 — git. Subject, ALDRI body (2.6 punkt 0): --grep matcher hele meldingen for a
    velge kandidat-commits (billig forhandsfilter), men ID-ene hentes utelukkende fra %s.

    Ett git-kall. --diff-merges=first-parent gir filene mot første forelder også for merger:
      (a) Vanlige (ikke-merge) commits: filene brukes direkte.
      (b) GitHub-PR-merge-commits ("Merge pull request #N from .../todo-NN-slug"): PR-ens
          branch-navn bærer ofte selve TODO-referansen, og første-foreldre-diffen er PR-ens
          faktiske filsett. "Sync"-merger ("Merge origin/{{BASE_BRANCH}} into ...") matcher IKKE dette
          mønsteret og hoppes over — en slik diff ville dratt med seg titalls urelaterte filer
          fra hele dev-historien.
    """
    try:
        r = subprocess.run(
            [
                "git", "log", "--grep=TODO[ -][0-9]", "-i", "-E",
                "--format=%x00%H%x1f%P%x1f%s", "--name-only",
                "--diff-merges=first-parent", "HEAD",
            ],
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        stats["missing_sources"].append("git-log")
        return
    if r.returncode != 0:
        stats["missing_sources"].append("git-log")
        return
    for chunk in r.stdout.split("\x00"):
        if not chunk.strip():
            continue
        lines = chunk.splitlines()
        header = lines[0] if lines else ""
        parts = header.split("\x1f")
        if len(parts) != 3:
            continue
        _commit_hash, parents, subject = parts
        files = [l for l in lines[1:] if l.strip()]
        tids = set(norm_id(m) for m in GIT_TODO_REF_RE.findall(subject))
        if not tids:
            continue
        # Merge-commit: bare GitHub-PR-merger brukes, ikke sync-merger.
        if len(parents.split()) >= 2 and not PR_MERGE_SUBJECT_RE.match(subject):
            continue
        for f in files:
            if f in exact_index:
                for tid in tids:
                    add_edge(f"todo:{tid}", "file", f"file:{f}")


def process_bugs(add_edge, resolve_file, stats):
    for path in ("tasks/bugs.md", "tasks/bugs_archive.md"):
        if not os.path.exists(path):
            stats["missing_sources"].append(path)
            continue
        text = read(path)
        lines = text.splitlines()
        starts = [i for i, l in enumerate(lines) if l.startswith("## BUG-")]
        for start in starts:
            end = len(lines)
            for j in range(start + 1, len(lines)):
                # Seksjon avsluttes ved neste '## '-overskrift ELLER en '^---$'-linje (2.7b).
                if lines[j].startswith("## ") or lines[j].strip() == "---":
                    end = j
                    break
            hm = re.match(r"^## BUG-(\d+)", lines[start])
            if not hm:
                continue
            bug_id = f"BUG-{hm.group(1)}"
            body_lines = lines[start + 1 : end]
            status_idx = next(
                (j for j, l in enumerate(body_lines) if l.startswith("**Status:**")), None
            )
            status_line = body_lines[status_idx] if status_idx is not None else ""
            rest_text = "\n".join(
                l for j, l in enumerate(body_lines) if j != status_idx
            )
            triaged_ids = set()
            for tm in TRIAGE_RE.finditer(status_line):
                tid = norm_id(tm.group(1))
                triaged_ids.add(tid)
                add_edge(f"bug:{bug_id}", "triaged_to", f"todo:{tid}")
            mention_ids = set()
            for tm in TODO_REF_RE.finditer(rest_text):
                tid = norm_id(tm.group(1))
                if tid not in triaged_ids:
                    mention_ids.add(tid)
            for tid in mention_ids:
                add_edge(f"bug:{bug_id}", "mentions", f"todo:{tid}")
            full_body_text = "\n".join(body_lines)
            for token in extract_file_tokens(full_body_text):
                rf = resolve_file(token)
                if rf:
                    add_edge(f"bug:{bug_id}", "file", f"file:{rf}")
            for pm in PR_LINK_RE.finditer(full_body_text):
                add_edge(f"bug:{bug_id}", "pr", f"pr:{pm.group(1)}")


def process_docs(add_edge, resolve_file):
    """Kilde 6. Node: doc:<sti>#<overskrift>, én per H2/H3 utenfor kodegjerder.
    En tom eller manglende docs/ er ikke en manglende kilde (kit-prosjekter uten docs/)."""
    for p in sorted(glob.glob("docs/*.md")):
        node, in_fence = None, False
        for line in read(p).splitlines():
            if line.lstrip().startswith("```"):
                in_fence = not in_fence
            hm = None if in_fence else re.match(r"#{2,3} +(.*)", line)
            if hm:
                node = f"doc:{p}#{hm.group(1).strip()}"
            # ponytail: tekst før første H2/H3 gir ingen node. Legg til doc:<sti># hvis ingressen bærer stier.
            if node is None:
                continue
            for token in extract_file_tokens(line):
                rf = resolve_file(token)
                if rf:
                    add_edge(node, "documents", f"file:{rf}")
            for tm in TODO_REF_RE.finditer(line):
                add_edge(node, "mentions", f"todo:{norm_id(tm.group(1))}")
            for bm in BUG_REF_RE.finditer(line):
                add_edge(node, "mentions", f"bug:BUG-{bm.group(1)}")


def lint(edges, followup_paths, active_nrs, archive_nrs):
    """--lint: første linje er hygiene=-linja, detaljlinjer under. Alltid exit 0."""
    # ponytail: en oppfølgingsfil som nevner en aktiv todo i forbifarten, regnes som eid.
    owned = {s for s, t, tgt in edges if t == "mentions" and tgt.startswith("todo:") and tgt[5:] in active_nrs}
    # Over fillista, ikke nodene: en fil uten kanter er ikke en node, men er en orphan.
    orphans = sum(f"followup:{os.path.relpath(p, 'tasks/followups')[:-3]}" not in owned for p in followup_paths)
    dangling = sorted((s, tgt) for s, t, tgt in edges if t == "deps" and tgt[5:] not in active_nrs | archive_nrs)
    # --no-renames: ellers står en omdøpt fil som R og mangler add-dato.
    r = subprocess.run(
        ["git", "log", "--diff-filter=A", "--no-renames", "--format=%x00%as", "--name-only", "--", "tasks/todos"],
        capture_output=True,
        text=True,
    )
    stale = None  # git feilet (f.eks. repo uten commits) -> n/a, aldri 0
    if r.returncode == 0:
        added = {}
        for chunk in r.stdout.split("\x00"):
            lines = [l for l in chunk.splitlines() if l]
            for f in lines[1:]:
                added[f] = lines[0]  # nyeste først, så eldste add-commit vinner
        limit = (datetime.date.today() - datetime.timedelta(days=14)).isoformat()
        stale = []
        for p in sorted(glob.glob("tasks/todos/todo-*.md")):
            fields, _body = read_frontmatter(read(p))
            if "forslag" not in _list(fields, "tags") or added.get(p, limit) >= limit:
                continue  # usporet fil har ingen add-dato og telles ikke
            if str(fields.get("status", "")).strip().strip("\"'") != "deferred":
                continue
            stale.append((p, added[p]))
    n = "n/a" if stale is None else len(stale)
    print(f"hygiene=cf_orphans:{orphans},deps_dangling:{len(dangling)},forslag_stale:{n}")
    for s, tgt in dangling:
        print(f"deps_dangling {s} -> {tgt}")
    for p, day in stale or []:
        print(f"forslag_stale {p} {day}")
    return 0


def _sort_key(v):
    if isinstance(v, dict):
        if {"source", "type", "target"} <= v.keys():
            return (v["source"], v["type"], v["target"])
    return v


def _assert_sorted(o, path="$"):
    """V2c — selv-sjekk pa sortering. Fanger en delliste bygget i oppdagelsesrekkefolge og
    aldri sortert, en klasse PYTHONHASHSEED-variasjon alene ikke kan avdekke."""
    if isinstance(o, list):
        keys = [_sort_key(v) for v in o]
        assert keys == sorted(keys), f"usortert liste i output: {path}"
        for i, v in enumerate(o):
            _assert_sorted(v, f"{path}[{i}]")
    elif isinstance(o, dict):
        for k, v in sorted(o.items()):
            _assert_sorted(v, f"{path}.{k}")


def main():
    ap = argparse.ArgumentParser(
        description="Utleder kantgrafen fra tasks/-kilder. Skriver JSON til stdout."
    )
    ap.add_argument(
        "--out",
        help=(
            "Skriv i tillegg til denne filen — KUN feilsøking, committes aldri. "
            "Tolkes relativt til arbeidskatalogen kommandoen ble startet fra, ikke repo-roten."
        ),
    )
    ap.add_argument(
        "--check-todo",
        nargs="+",
        metavar="FIL",
        help=(
            "Vakt i stedet for bygg: exit 1 når en todo-fil navngir en fil eller en bug i "
            "brødteksten uten files:/bugs: i frontmatteren, eller har det strøkne feltet pr."
        ),
    )
    ap.add_argument(
        "--lint",
        action="store_true",
        help="Hygiene-tall i stedet for bygg: oppfølginger uten aktiv todo, deps mot ukjent nr, gamle forslag.",
    )
    args = ap.parse_args()

    root, orig_cwd = resolve_root()
    out_path = None
    if args.out:
        out_path = args.out if os.path.isabs(args.out) else os.path.join(orig_cwd, args.out)
    os.chdir(root)

    stats = {
        "missing_sources": [],
        "file_token_ambiguous": 0,
        "file_token_unresolved": 0,
        "todos_skipped_no_nr": 0,
        "todos_total_files": 0,
        "id_collisions": [],
        "lesson_nodes": 0,
        "followup_nodes": 0,
    }

    edges = set()

    def add_edge(a, t, b):
        edges.add((a, t, b))

    all_git_files = git_ls_files()
    exact_index, by_base = build_file_index(all_git_files)
    resolve_file = make_resolver(exact_index, by_base, stats)

    if args.check_todo:
        sys.exit(check_todos(args.check_todo, orig_cwd, resolve_file))

    active_nrs = process_todos(add_edge, resolve_file, stats)
    if not process_notes(add_edge, resolve_file, stats, "tasks/lessons", "lesson"):
        stats["missing_sources"].append("tasks/lessons/")
    # ponytail: en tom tasks/followups/ er en gyldig tilstand (ingen apne oppfolginger), ikke en manglende kilde.
    followup_paths = process_notes(add_edge, resolve_file, stats, "tasks/followups", "followup")
    archive_nrs = process_archive(add_edge, stats)
    process_git(add_edge, exact_index, stats)
    process_bugs(add_edge, resolve_file, stats)
    process_docs(add_edge, resolve_file)

    # Mekanisme 2 (3.3): mangler ALLE fem kilder -> hoyt exit. En kilde regnes tapt her kun
    # hvis BEGGE bug-filene manglet (kilde 5 er de to filene sammen).
    source_keys = {"tasks/todos/", "tasks/lessons/", "tasks/todo_archive.md", "git-log"}
    bugs_missing = {"tasks/bugs.md", "tasks/bugs_archive.md"}.issubset(
        set(stats["missing_sources"])
    )
    missing_set = set(stats["missing_sources"])
    if source_keys.issubset(missing_set) and bugs_missing:
        sys.exit(f"FEIL: ingen kilder funnet under {root} — kjører du fra repo-roten?")

    if args.lint:
        sys.exit(lint(edges, followup_paths, active_nrs, archive_nrs))

    # V0b (rapporteres, stopper ikke): aktiv x arkiv-kollisjon pa nr.
    stats["id_collisions"] = sorted(active_nrs & archive_nrs)

    # Noder utledes rent fra kant-deltakelse (kilde/mal), gruppert pa prefiks.
    nodes = {"todo": set(), "bug": set(), "pr": set(), "file": set(), "doc": set(), "lesson": set(), "followup": set(), "theme": set()}
    for s, _t, tgt in edges:
        for endpoint in (s, tgt):
            prefix, _, _rest = endpoint.partition(":")
            if prefix in nodes:
                nodes[prefix].add(endpoint)

    node_lists = {k: sorted(v) for k, v in sorted(nodes.items())}
    edge_list = sorted(
        ({"source": s, "type": t, "target": tgt} for (s, t, tgt) in edges),
        key=lambda e: (e["source"], e["type"], e["target"]),
    )

    edge_type_counts = {}
    for e in edge_list:
        edge_type_counts[e["type"]] = edge_type_counts.get(e["type"], 0) + 1
    stats["edge_type_counts"] = dict(sorted(edge_type_counts.items()))
    # V11: stats.lesson_nodes/followup_nodes = RAA telling av filer, IKKE det samme som
    # node_counts.lesson/followup (kun de som endte opp med minst en kant).
    stats["node_counts"] = {k: len(v) for k, v in node_lists.items()}
    stats["edge_total"] = len(edge_list)
    stats["missing_sources"] = sorted(set(stats["missing_sources"]))

    out = {"nodes": node_lists, "edges": edge_list, "stats": stats}

    _assert_sorted(out)

    payload = json.dumps(out, ensure_ascii=False, sort_keys=True, indent=1) + "\n"
    sys.stdout.write(payload)
    if out_path:
        with open(out_path, "w", encoding="utf-8") as fh:
            fh.write(payload)


if __name__ == "__main__":
    main()
