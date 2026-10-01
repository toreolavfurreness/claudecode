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

All diagnostikk (advarsler, feil) gar til stderr. stdout inneholder KUN JSON-objektet
{"nodes": {...}, "edges": [...], "stats": {...}}.

Kilder (fem, alle fail-soft hver for seg — mangler en kilde hopper byggeren over den og
teller det i stats.missing_sources i stedet for a kaste):
  1. Frontmatter i tasks/todos/*.md          (deps/bugs/files/lessons/pr)
  2. tasks/lessons/*.md                       (TODO/BUG-mentions, fil-mentions, ## Se ogsaa)
  3. tasks/todo_archive.md                    (BUG-mentions, /pull/-lenker)
  4. git-historikk                            (commit-subject "TODO n" -> rorte filer)
  5. tasks/bugs.md + tasks/bugs_archive.md    (Status-triage, fil-mentions, PR-lenker)
"""
import argparse
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
TODO_REF_RE = re.compile(r"TODO\s+(\d+[A-Za-z]*)")
# Git-commit-subjekter bruker ofte conventional-commit-scope-formen "(todo-NN)" i tillegg til
# prosa-formen "TODO NN" — case-insensitivt og med bindestrek ELLER mellomrom (M-9, funnet ved
# V1-verifisering: todo:28a/todo:116/todo:138 er kun nabare via denne bredere formen).
GIT_TODO_REF_RE = re.compile(r"TODO[ -](\d+[A-Za-z]*)", re.IGNORECASE)
BUG_REF_RE = re.compile(r"BUG-(\d+)")
PR_LINK_RE = re.compile(r"/pull/(\d+)")
# Kun Status-linja: "triagert til TODO n" ELLER "kode-fikset (TODO n" — begge malte former (M10).
TRIAGE_RE = re.compile(r"(?:triagert til TODO|kode-fikset \(TODO)\s+(\d+[A-Za-z]?)")
# Begge dato-former: "## 2026-07-01 — ..." og "## [2026-07-02] — ..." (M14).
SEE_ALSO_LINK_RE = re.compile(r"\]\(([a-z0-9-]+)\.md\)")


def norm_id(raw):
    """En eneste vei til en todo:-node (V-7). Stripper norsk-genitiv 's' og ledende nuller."""
    s = raw.strip()
    if len(s) > 1 and s[-1] == "s" and s[-2].isdigit():
        s = s[:-1]
    m = re.match(r"0*(\d+)(.*)$", s)
    if m:
        digits, suffix = m.group(1), m.group(2)
        s = (digits or "0") + suffix
    return s


def is_inverse_guard_hit(raw):
    """True hvis en rå ID-streng bar et genitiv-'s' eller ledende null FOR normalisering."""
    s = raw.strip()
    if len(s) > 1 and s[-1] == "s" and s[-2].isdigit():
        return True
    m = re.match(r"(0+)\d", s)
    return bool(m)


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
    """Kun inline-listeform (`["a", "b"]`) er kantbærende — blokklisteform rapporteres, ikke parses."""
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
        text = read(p)
        m = re.match(r"^---\n(.*?)\n---\n?", text, re.S)
        if not m:
            continue
        block = m.group(1)
        fields = {}
        for line in block.splitlines():
            mm = re.match(r"([A-Za-z_]+):\s*(.*)$", line)
            if mm:
                fields[mm.group(1)] = mm.group(2)
        for key in ("bugs", "files", "lessons", "pr"):
            if key in fields and fields[key].strip() == "":
                stats["blocklist_form_fields"].append(f"{os.path.basename(p)}:{key}")
        nr_raw = fields.get("nr", "").strip().strip('"').strip("'")
        if not nr_raw:
            stats["todos_skipped_no_nr"] += 1
            continue
        if is_inverse_guard_hit(nr_raw):
            stats["inverse_guard_suspects"].append(f"{p}:nr={nr_raw}")
        nr = norm_id(nr_raw)
        active_nrs.add(nr)
        stats["todos_total_files"] += 1

        has_new_field = False
        for d in parse_inline_list(fields.get("deps", "")):
            add_edge(f"todo:{nr}", "deps", f"todo:{norm_id(d)}")

        bugs = parse_inline_list(fields.get("bugs", ""))
        if bugs:
            has_new_field = True
        for b in bugs:
            bid = b if b.upper().startswith("BUG-") else f"BUG-{b}"
            add_edge(f"todo:{nr}", "bug", f"bug:{bid}")

        files = parse_inline_list(fields.get("files", ""))
        if files:
            has_new_field = True
        for f in files:
            rf = resolve_file(f)
            if rf:
                add_edge(f"todo:{nr}", "file", f"file:{rf}")

        lessons = parse_inline_list(fields.get("lessons", ""))
        if lessons:
            has_new_field = True
        for th in lessons:
            add_edge(f"todo:{nr}", "lesson_theme", f"theme:{th}")

        prs = parse_inline_list(fields.get("pr", ""))
        if prs:
            has_new_field = True
        for pr in prs:
            add_edge(f"todo:{nr}", "pr", f"pr:{pr.lstrip('#')}")

        if has_new_field:
            stats["todos_with_new_fields"] += 1

    return active_nrs


def process_lessons(add_edge, resolve_file, stats):
    paths = sorted(glob.glob("tasks/lessons/*.md"))
    if not paths:
        stats["missing_sources"].append("tasks/lessons/")
        return
    theme_names = set(os.path.splitext(os.path.basename(p))[0] for p in paths)
    for p in paths:
        theme = os.path.splitext(os.path.basename(p))[0]
        text = read(p)
        lines = text.splitlines()
        for start, end, heading_text in split_h2_sections(lines):
            body = "\n".join(lines[start + 1 : end])
            if heading_text == "Se også":
                stats["nonlesson_h2"] += 1
                for lm in SEE_ALSO_LINK_RE.finditer(body):
                    other = lm.group(1)
                    if other in theme_names:
                        add_edge(f"theme:{theme}", "see_also", f"theme:{other}")
                    else:
                        stats["see_also_phantom"] += 1
                continue
            date_m = re.match(r"^\[?(\d{4}-\d{2}-\d{2})\]?", heading_text)
            if not date_m:
                stats["nonlesson_h2"] += 1
                continue
            # Rah telling av dato-matchede overskrifter (V11) — uavhengig av om overskriften
            # ender opp med noen kanter. Distinkt fra stats.node_counts.lesson (kun edge-deltakere).
            stats["lesson_nodes"] += 1
            lesson_node = f"lesson:{theme}#{heading_text}"
            for tm in TODO_REF_RE.finditer(body):
                add_edge(lesson_node, "mentions", f"todo:{norm_id(tm.group(1))}")
            for bm in BUG_REF_RE.finditer(body):
                add_edge(lesson_node, "mentions", f"bug:BUG-{bm.group(1)}")
            for token in extract_file_tokens(body):
                rf = resolve_file(token)
                if rf:
                    add_edge(lesson_node, "file", f"file:{rf}")


def process_archive(add_edge, stats):
    path = "tasks/todo_archive.md"
    if not os.path.exists(path):
        stats["missing_sources"].append(path)
        return set()
    text = read(path)
    lines = text.splitlines()
    archive_nrs = set()
    for start, end, heading_text in split_h2_sections(lines):
        hm = re.match(r"^TODO\s+(\d+[A-Za-z]*)", heading_text)
        if not hm:
            continue
        if is_inverse_guard_hit(hm.group(1)):
            stats["inverse_guard_suspects"].append(f"{path}:## TODO {hm.group(1)}")
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

    To baner, begge subject-only:
      (a) Vanlige (ikke-merge) commits: --name-only gir filene direkte.
      (b) GitHub-PR-merge-commits ("Merge pull request #N from .../todo-NN-slug"): --name-only
          uten -m gir INGEN filer (git sin standardoppforsel for merges), men PR-ens branch-navn
          bærer ofte selve TODO-referansen (ikke den underliggende commiten). Første-foreldre-
          diffen for NETTOPP denne undergruppen gir PR-ens faktiske filsett. "Sync"-merger
          ("Merge origin/dev into ...") matcher IKKE dette mønsteret og behandles fortsatt som
          tomme — en slik diff ville dratt med seg titalls urelaterte filer fra hele dev-historien.
    """
    try:
        r = subprocess.run(
            [
                "git", "log", "--grep=TODO[ -][0-9]", "-i", "-E",
                "--format=%x00%H%x1f%P%x1f%s", "--name-only", "HEAD",
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
    pr_merge_candidates = []  # (commit, first_parent, tids)
    for chunk in r.stdout.split("\x00"):
        if not chunk.strip():
            continue
        lines = chunk.splitlines()
        header = lines[0] if lines else ""
        parts = header.split("\x1f")
        if len(parts) != 3:
            continue
        commit_hash, parents, subject = parts
        parent_list = parents.split()
        files = [l for l in lines[1:] if l.strip()]
        tids = set(norm_id(m) for m in GIT_TODO_REF_RE.findall(subject))
        if not tids:
            continue
        if len(parent_list) >= 2:
            # Merge-commit: --name-only ga (korrekt) ingen filer. Kandidat for (b) kun hvis
            # subjektet er en GitHub-PR-merge, ikke en sync-merge.
            if PR_MERGE_SUBJECT_RE.match(subject):
                pr_merge_candidates.append((commit_hash, parent_list[0], tids))
            continue
        for f in files:
            if f in exact_index:
                for tid in tids:
                    add_edge(f"todo:{tid}", "file", f"file:{f}")

    for commit_hash, first_parent, tids in pr_merge_candidates:
        dr = subprocess.run(
            ["git", "diff", "--name-only", first_parent, commit_hash],
            capture_output=True,
            text=True,
        )
        if dr.returncode != 0:
            continue
        for f in dr.stdout.splitlines():
            f = f.strip()
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


def _sort_key(v):
    if isinstance(v, dict):
        if {"source", "type", "target"} <= v.keys():
            return (v["source"], v["type"], v["target"])
        return tuple(v[k] for k in sorted(v.keys()))
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
            "Skriv i tillegg til denne filen — KUN feilsoking, committes aldri. "
            "Tolkes relativt til arbeidskatalogen kommandoen ble startet fra, ikke repo-roten."
        ),
    )
    args = ap.parse_args()

    root, orig_cwd = resolve_root()
    out_path = None
    if args.out:
        out_path = args.out if os.path.isabs(args.out) else os.path.join(orig_cwd, args.out)
    os.chdir(root)

    stats = {
        "missing_sources": [],
        "blocklist_form_fields": [],
        "file_token_ambiguous": 0,
        "file_token_unresolved": 0,
        "nonlesson_h2": 0,
        "see_also_phantom": 0,
        "todos_skipped_no_nr": 0,
        "todos_total_files": 0,
        "todos_with_new_fields": 0,
        "inverse_guard_suspects": [],
        "id_collisions": [],
        "lesson_nodes": 0,
    }

    edges = set()

    def add_edge(a, t, b):
        edges.add((a, t, b))

    all_git_files = git_ls_files()
    exact_index, by_base = build_file_index(all_git_files)
    resolve_file = make_resolver(exact_index, by_base, stats)

    active_nrs = process_todos(add_edge, resolve_file, stats)
    process_lessons(add_edge, resolve_file, stats)
    archive_nrs = process_archive(add_edge, stats)
    process_git(add_edge, exact_index, stats)
    process_bugs(add_edge, resolve_file, stats)

    # Mekanisme 2 (3.3): mangler ALLE fem kilder -> hoyt exit. En kilde regnes tapt her kun
    # hvis BEGGE bug-filene manglet (kilde 5 er de to filene sammen).
    source_keys = {"tasks/todos/", "tasks/lessons/", "tasks/todo_archive.md", "git-log"}
    bugs_missing = {"tasks/bugs.md", "tasks/bugs_archive.md"}.issubset(
        set(stats["missing_sources"])
    )
    missing_set = set(stats["missing_sources"])
    if source_keys.issubset(missing_set) and bugs_missing:
        sys.exit(f"FEIL: ingen kilder funnet under {root} — kjorer du fra repo-roten?")

    # V0b (rapporteres, stopper ikke): aktiv x arkiv-kollisjon pa nr.
    stats["id_collisions"] = sorted(active_nrs & archive_nrs)

    # Noder utledes rent fra kant-deltakelse (kilde/mal), gruppert pa prefiks.
    nodes = {"todo": set(), "bug": set(), "pr": set(), "file": set(), "lesson": set(), "theme": set()}
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
    # V11: stats.lesson_nodes = RAA telling av dato-matchede H2-overskrifter (438 malt), IKKE
    # det samme som node_counts.lesson (kun de som endte opp med minst en kant).
    stats["node_counts"] = {k: len(v) for k, v in node_lists.items()}
    stats["edge_total"] = len(edge_list)
    stats["missing_sources"] = sorted(set(stats["missing_sources"]))
    stats["blocklist_form_fields"] = sorted(stats["blocklist_form_fields"])
    stats["inverse_guard_suspects"] = sorted(stats["inverse_guard_suspects"])

    out = {"nodes": node_lists, "edges": edge_list, "stats": stats}

    _assert_sorted(out)

    payload = json.dumps(out, ensure_ascii=False, sort_keys=True, indent=1) + "\n"
    sys.stdout.write(payload)
    if out_path:
        # Unngar dobbel-skriving nar --out peker pa samme underliggende fil som stdout selv
        # (f.eks. --out /dev/stdout, brukt av V2b for a bevise at stdout og --out er identiske).
        # Kun st_ino sammenlignes, IKKE full os.path.samestat(): syntetiske device-noder som
        # /dev/stdout pa macOS bærer et annet st_dev enn den underliggende fd-en sjøl om st_ino
        # (og filen) er identisk — samestat() ville da (feilaktig) sagt "ulik fil".
        same_as_stdout = False
        try:
            out_ino = os.stat(out_path).st_ino
            fd1_ino = os.fstat(sys.stdout.fileno()).st_ino
            same_as_stdout = out_ino != 0 and out_ino == fd1_ino
        except OSError:
            same_as_stdout = False
        if not same_as_stdout:
            with open(out_path, "w", encoding="utf-8") as fh:
                fh.write(payload)


if __name__ == "__main__":
    main()
