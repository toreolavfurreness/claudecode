#!/usr/bin/env python3
"""
parallel-disjoint.py: fil-disjunkt-gate for parallelle implementere
(coordinator-runbook.md §5d).

To gater, samme skript:
  - Gate P (prediktiv, FØR B claimes): A = `gh pr diff <A-pr> --name-only` (MÅLT, --a).
    B = B sin plan sitt "## Filer som berøres"-avsnitt (DEKLARERT, --plan-b).
  - Gate M (målt, FØR B sin merge): BEGGE sider er `gh pr diff --name-only` (--a og --b).

Fail-closed på tvers av begge gatene: tom liste på noen av sidene, manglende input-fil,
eller manglende "Filer"-seksjon i en plan gir alle IKKE-null exit — ALDRI stille "ok".

CLI:
  python3 tasks/parallel-disjoint.py --self-test
  python3 tasks/parallel-disjoint.py --a <fil, én sti per linje> --b <fil> [--forbid-prefix P ...]
  python3 tasks/parallel-disjoint.py --a <fil> --plan-b <planfil.md> [--forbid-prefix P ...]

Exit-koder: 0 = ok (disjunkt). 1 = ett av: overlap | empty-a | empty-b | missing-input |
missing-section | client-code | ls-files-failed (kun --plan-b-stien, git ls-files feilet).

`client-code`-utskrift navngir BEGGE sider uavhengig av hverandre (`client-code a=[...] b=[...]`,
kode-review-funn VIKTIG 1) — ALDRI kun den ene siden, selv om kun én av dem faktisk er ikke-tom.
"""
import argparse
import os
import re
import subprocess
import sys
import tempfile

VERDICT_OK = "ok"

# ---------------------------------------------------------------------------
# Normalisering (§ 1.3.1 i planen)
# ---------------------------------------------------------------------------


def normalize_path(t):
    """N1 (strip ledende './', ALDRI lstrip), N2 (strip ':<n>'/':<n>-<m>'-suffiks),
    N4 ('…/**' og '…/*' ⇒ katalog-prefiks '…/')."""
    t = re.sub(r"^\./", "", t)  # N1 — lstrip("./") ville spist punktumet i .claude/…
    t = re.sub(r":\d+(-\d+)?$", "", t)  # N2
    t = re.sub(r"/\*\*$", "/", t)  # N4
    t = re.sub(r"/\*$", "/", t)  # N4
    return t


_EXT_RE = re.compile(r"\.[A-Za-z0-9]{1,10}$")


def is_path_like(raw_token, repo_files):
    """N6 (r2, plan-review-pålegg) — forkast tokens som ikke kan være repo-stier.
    Konservativ retning (fail-open er feilretningen her): behold tokenet hvis det
    INNEHOLDER '/', ELLER har en filendelse, ELLER finnes i `git ls-files`. Forkast
    rene tall og bare identifikatorer (f.eks. bare-tallet '18', som ga en falsk
    OVERLAP mellom to ellers disjunkte planer i r1-målingen)."""
    if "/" in raw_token:
        return True
    if _EXT_RE.search(raw_token):
        return True
    if raw_token in repo_files:
        return True
    return False


def get_git_ls_files():
    """N6 avhenger av en fullstendig fil-liste. `git ls-files` er cwd-relativ (en delvis
    liste fra en underkatalog ville vært stille galt), så den kjøres alltid mot repo-roten
    via `-C <toplevel>`, aldri mot `cwd` direkte.

    Fail-closed (kode-review-funn, MINDRE 4): en tidligere versjon svelget enhver exception
    og returnerte `set()` stille — det gjør N6 fail-OPEN (færre kjente stier => et
    ekte repo-token uten '/' og uten filendelse forkastes stille i stedet for at gaten sier
    fra), i strid med docstringens "ALDRI stille ok". Returnerer i stedet `(files, error)`:
    `(set(...), None)` ved suksess, `(None, "ls-files-failed")` ved enhver feil (git ikke i
    PATH, korrupt indeks, ikke inne i et git-repo). Callers på `--plan-b`-stien MÅ behandle
    `error` som ikke-null exit — se `main()`."""
    try:
        toplevel = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        out = subprocess.run(
            ["git", "-C", toplevel, "ls-files"],
            capture_output=True,
            text=True,
            check=True,
        )
        return set(out.stdout.splitlines()), None
    except Exception:
        return None, "ls-files-failed"


def _fixture_ls_files_failure():
    """F-EXT-8 (kode-review-funn, MINDRE 4) — beviser at get_git_ls_files() faktisk
    fail-closed'er utenfor et git-repo, i stedet for å anta det fra kildelesning."""
    cwd = os.getcwd()
    tmpdir = tempfile.mkdtemp()
    try:
        os.chdir(tmpdir)
        return get_git_ls_files()
    finally:
        os.chdir(cwd)
        try:
            os.rmdir(tmpdir)
        except OSError:
            pass


# ---------------------------------------------------------------------------
# Uttrekk fra planfil (§ 1.3.1)
# ---------------------------------------------------------------------------

_HEADING_RE = re.compile(r"^(#{2,4})\s+(?:\d+\.\s*)?Filer\b", re.I)
_ANY_HEADING_RE = re.compile(r"^(#{1,6})\s+")
_TOKEN_RE = re.compile(r"`([^`]*)`")


def extract_tokens_from_plan_text(text):
    """Finn FØRSTE '## Filer'-aktige overskrift der linja IKKE inneholder 'IKKE'.
    Seksjonen løper til neste overskrift med nivå <= treffets nivå (bevisst
    over-inkluderende — se § 1.3.1). Returnerer None hvis ingen slik overskrift
    finnes (⇒ missing-section)."""
    lines = text.splitlines()
    start = None
    level = None
    for i, line in enumerate(lines):
        m = _HEADING_RE.match(line)
        if m and "IKKE" not in line:
            start = i
            level = len(m.group(1))
            break
    if start is None:
        return None
    end = len(lines)
    for j in range(start + 1, len(lines)):
        m = _ANY_HEADING_RE.match(lines[j])
        if m and len(m.group(1)) <= level:
            end = j
            break
    body = "\n".join(lines[start:end])
    return _TOKEN_RE.findall(body)


def tokens_to_pathlist(tokens, repo_files):
    out = []
    for t in tokens:
        if not t or " " in t:
            continue  # spec: "tokens UTEN mellomrom"
        if t.startswith("/") or t.startswith("~"):
            continue  # N3
        if not is_path_like(t, repo_files):
            continue  # N6
        out.append(normalize_path(t))
    return out


def extract_plan_b_list(plan_path, repo_files):
    if not os.path.exists(plan_path):
        return "missing-input", None
    text = open(plan_path, encoding="utf-8").read()
    tokens = extract_tokens_from_plan_text(text)
    if tokens is None:
        return "missing-section", None
    return None, tokens_to_pathlist(tokens, repo_files)


# ---------------------------------------------------------------------------
# Kjernegate
# ---------------------------------------------------------------------------


def dedup_casefold(lst):
    seen = set()
    out = []
    for x in lst:
        k = x.casefold()
        if k in seen:
            continue
        seen.add(k)
        out.append(x)
    return out


def path_overlap(a, b):
    af, bf = a.casefold(), b.casefold()
    if af == bf:
        return True
    if bf.startswith(af.rstrip("/") + "/"):
        return True
    if af.startswith(bf.rstrip("/") + "/"):
        return True
    return False


def find_overlaps(a_list, b_list):
    hits = []
    for a in a_list:
        for b in b_list:
            if path_overlap(a, b):
                hits.append((a, b))
    return hits


def find_forbidden(lst, forbid_prefixes):
    """Returnerer ALLE elementer i `lst` som treffer et forbudt prefiks (ikke bare det
    første) — `evaluate()` kaller denne separat for A og B (kode-review-funn, VIKTIG 1)
    slik at BEGGE sider rapporteres uavhengig av hverandre, i stedet for at én side sin
    `or`-kortslutning skjuler den andre. Case-folder begge sider (kode-review-funn,
    MINDRE 3) — macOS/APFS er case-insensitivt, og B-siden ved `--plan-b` er ofte
    menneskeskrevet prosa som ikke nødvendigvis matcher git sin faktiske stavemåte."""
    hits = []
    for x in lst:
        xf = x.casefold()
        for p in forbid_prefixes:
            pp = p.rstrip("/").casefold()
            if xf == pp or xf.startswith(pp + "/"):
                hits.append(x)
                break
    return hits


def evaluate(a_raw, b_raw, forbid_prefixes=None):
    """a_raw/b_raw: rå tokens/stier (IKKE nødvendigvis normalisert ennå). Returnerer
    (verdict, exit_code, detail). `detail` for `client-code` er `{"a": [...], "b": [...]}`
    (kode-review-funn, VIKTIG 1) — ALDRI en `or`-kortslutning mellom sidene: en tidligere
    versjon evaluerte `find_forbidden(a_list, ...) or find_forbidden(b_list, ...)`, som
    aldri beregnet B sitt treff når A allerede hadde ett (fail-OPEN for B sitt spor —
    e2e-kravet under gate M ville da aldri blitt håndhevet for B)."""
    forbid_prefixes = forbid_prefixes or []
    a_norm = [normalize_path(x) for x in a_raw if x is not None and x.strip() != ""]
    b_norm = [normalize_path(x) for x in b_raw if x is not None and x.strip() != ""]
    a_list = dedup_casefold(a_norm)
    b_list = dedup_casefold(b_norm)
    if not a_list:
        return "empty-a", 1, []
    if not b_list:
        return "empty-b", 1, []
    if forbid_prefixes:
        a_hits = find_forbidden(a_list, forbid_prefixes)
        b_hits = find_forbidden(b_list, forbid_prefixes)
        if a_hits or b_hits:
            return "client-code", 1, {"a": a_hits, "b": b_hits}
    hits = find_overlaps(a_list, b_list)
    if hits:
        return "overlap", 1, hits
    return VERDICT_OK, 0, []


def load_list_from_file(path):
    if not os.path.exists(path):
        return "missing-input", None
    with open(path, encoding="utf-8") as f:
        return None, [line.rstrip("\n") for line in f]


# ---------------------------------------------------------------------------
# --self-test — F1–F11 + F-EXT-1–10 (se § 9.1 i planen for hele fixture-listen)
# ---------------------------------------------------------------------------


def _mk_plan(body):
    fd, path = tempfile.mkstemp(suffix=".md")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(body)
    return path


def run_self_test():
    results = []

    def check(name, got, expected, rule):
        ok = got == expected
        results.append((name, ok, got, expected, rule))

    # F1–F11 — kjøres direkte mot evaluate()
    v, c, _ = evaluate(["docs/x.md"], ["tasks/y.md"])
    check("F1", v, "ok", "snitt tomt")

    v, c, _ = evaluate(["docs/x.md"], ["docs/x.md"])
    check("F2", v, "overlap", "eksakt likhet")

    v, c, _ = evaluate([], ["tasks/y.md"])
    check("F3", v, "empty-a", "fail-closed, FØR snitt")

    v, c, _ = evaluate(["docs/x.md"], [])
    check("F4", v, "empty-b", "fail-closed, FØR snitt")

    verdict, _ = load_list_from_file("/tmp/__parallel_disjoint_does_not_exist__.md")
    check("F5", verdict, "missing-input", "fail-closed, FØR parsing")

    v, c, _ = evaluate(["./lib/x.ts"], ["lib/x.ts"])
    check("F6", v, "overlap", "normalisering av './'")

    v, c, _ = evaluate(["lib/"], ["lib/domain/x.ts"])
    check("F7", v, "overlap", "prefiks-med-'/'-grense")

    v, c, _ = evaluate(["docs/Foo.md"], ["docs/foo.md"])
    check("F8", v, "overlap", "case-folding (macOS)")

    v, c, _ = evaluate(["docs/x.md", "docs/x.md"], ["tasks/y.md"])
    check("F9", v, "ok", "dedup gir ikke falsk overlapp")

    v, c, _ = evaluate(["docs/x.md", "", "  "], ["tasks/y.md"])
    check("F10", v, "ok", "blanke linjer ignoreres")

    v, c, _ = evaluate(["docs/x.md"], ["lib/z.ts"], forbid_prefixes=["app/", "components/", "lib/"])
    check("F11", v, "client-code", "forbudt prefiks (§ 2.2 (C))")

    # F-EXT-9 (kode-review-funn, VIKTIG 1) — BEGGE sider har klientkode, BEGGE navngis
    # uavhengig av hverandre (aldri en or-kortslutning som skjuler B når A allerede traff)
    v, c, detail = evaluate(
        ["docs/a.md", "lib/aside.ts"],
        ["tasks/b.md", "components/bside.tsx"],
        forbid_prefixes=["app/", "components/", "lib/"],
    )
    check(
        "F-EXT-9",
        (v, detail),
        ("client-code", {"a": ["lib/aside.ts"], "b": ["components/bside.tsx"]}),
        "client-code navngir BEGGE sider uavhengig (VIKTIG 1)",
    )

    # F-EXT-10 (kode-review-funn, MINDRE 3) — case-fold i find_forbidden: B-siden er
    # menneskeskrevet med annen staving ('Lib/') enn forbid-prefikset ('lib/')
    v, c, _ = evaluate(["docs/x.md"], ["Lib/domain/x.ts"], forbid_prefixes=["lib/"])
    check("F-EXT-10", v, "client-code", "case-fold i find_forbidden (MINDRE 3)")

    # F-EXT-8 (kode-review-funn, MINDRE 4) — get_git_ls_files() fail-closed utenfor et git-repo
    ls_files, ls_err = _fixture_ls_files_failure()
    check(
        "F-EXT-8",
        (ls_files, ls_err),
        (None, "ls-files-failed"),
        "get_git_ls_files() fail-closed (ikke stille set())",
    )

    repo_files, repo_err = get_git_ls_files()
    if repo_err:
        # Self-test kjøres normalt inne i et git-repo; en feil her er uventet, men
        # self-testen skal ikke krasje for det — resten av fixturene rammes ikke, siden
        # ingen av dem er avhengige av at et bart, ikke-sti-formet token faktisk finnes
        # i git ls-files (de har alle '/' eller en filendelse).
        repo_files = set()

    # F-EXT-1 — punktum i .claude/… bevart
    p = _mk_plan("## Filer som berøres\n\n- `.claude/agents/x.md`\n")
    err, lst = extract_plan_b_list(p, repo_files)
    os.unlink(p)
    check("F-EXT-1", (err, lst), (None, [".claude/agents/x.md"]), "N1 (re.sub, ikke lstrip)")

    # F-EXT-2 — linjenummer-suffiks strippet, matcher A=[docs/PORTING.md]
    p = _mk_plan("## Filer som berøres\n\n- `docs/PORTING.md:126`\n")
    err, lst = extract_plan_b_list(p, repo_files)
    os.unlink(p)
    v, c, _ = evaluate(["docs/PORTING.md"], lst or [])
    check("F-EXT-2", v, "overlap", "N2 (linjenummer-suffiks strippet)")

    # F-EXT-3 — '/setup' forkastet, 'docs/x.md' beholdt, A=[docs/y.md] ⇒ ok
    p = _mk_plan("## Filer som berøres\n\n- `/setup`\n- `docs/x.md`\n")
    err, lst = extract_plan_b_list(p, repo_files)
    os.unlink(p)
    v, c, _ = evaluate(["docs/y.md"], lst or [])
    check("F-EXT-3", (lst, v), (["docs/x.md"], "ok"), "N3")

    # F-EXT-4 — '/**'⇒katalog-prefiks, overlapper med fil under katalogen
    p = _mk_plan("## Filer som berøres\n\n- `.claude/agent-memory/**`\n")
    err, lst = extract_plan_b_list(p, repo_files)
    os.unlink(p)
    v, c, _ = evaluate([".claude/agent-memory/impl/MEMORY.md"], lst or [])
    check("F-EXT-4", v, "overlap", "N4 + prefiks-regelen (F7)")

    # F-EXT-5 — overskrift NUMMERERT + underseksjon 'IKKE' inkluderes i kroppen
    p = _mk_plan(
        "## 4. Filer som berøres\n\n"
        "- `docs/a.md`\n\n"
        "### Filer som IKKE røres\n\n"
        "- `docs/b.md`\n\n"
        "## 5. Neste seksjon\n\n- `docs/c.md`\n"
    )
    err, lst = extract_plan_b_list(p, repo_files)
    os.unlink(p)
    check(
        "F-EXT-5",
        (err, sorted(lst or [])),
        (None, ["docs/a.md", "docs/b.md"]),
        "overskrifts-match: IKKE-treff hoppes som START, underseksjon inkludert i kroppen",
    )

    # F-EXT-6 — ingen 'Filer'-overskrift i det hele tatt
    p = _mk_plan("## Sammendrag\n\nIngen filseksjon her.\n")
    err, lst = extract_plan_b_list(p, repo_files)
    os.unlink(p)
    check("F-EXT-6", err, "missing-section", "fail-closed, FØR snitt")

    # F-EXT-7 (r2, plan-review-pålegg) — bart tall-token forkastes av N6, ekte sti beholdes
    p = _mk_plan("## Filer som berøres\n\n- `18`\n- `docs/x.md`\n")
    err, lst = extract_plan_b_list(p, repo_files)
    os.unlink(p)
    check("F-EXT-7", (err, lst), (None, ["docs/x.md"]), "N6 (forkast bare tall/identifikatorer uten sti-form)")

    n_pass = sum(1 for r in results if r[1])
    n_total = len(results)
    print(f"parallel-disjoint.py --self-test: {n_pass}/{n_total} fixturer grønne")
    for name, ok, got, expected, rule in results:
        status = "OK" if ok else "FEIL"
        print(f"  [{status}] {name} ({rule}): fikk={got!r} forventet={expected!r}")
    return 0 if n_pass == n_total else 1


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--a", help="fil med A sine stier, én per linje (f.eks. gh pr diff --name-only)")
    ap.add_argument("--b", help="fil med B sine stier, én per linje")
    ap.add_argument("--plan-b", help="B sin planfil — uttrekk '## Filer som berøres' i stedet for --b")
    ap.add_argument(
        "--forbid-prefix",
        action="append",
        default=[],
        help="forby ethvert innslag under dette sti-prefikset (gjentakbar); § 2.2 (C)",
    )
    args = ap.parse_args(argv)

    if args.self_test:
        return run_self_test()

    if not args.a:
        print("FEIL: --a er påkrevd (utenom --self-test)", file=sys.stderr)
        return 1
    err, a_list = load_list_from_file(args.a)
    if err:
        print(err)
        return 1

    if args.plan_b:
        repo_files, repo_err = get_git_ls_files()
        if repo_err:
            # Fail-closed (kode-review-funn, MINDRE 4): git ls-files feilet — behandle
            # det som en egen, navngitt exit i stedet for stille å fortsette med set().
            print(repo_err)
            return 1
        err, b_list = extract_plan_b_list(args.plan_b, repo_files)
        if err:
            print(err)
            return 1
    elif args.b:
        err, b_list = load_list_from_file(args.b)
        if err:
            print(err)
            return 1
    else:
        print("FEIL: enten --b eller --plan-b er påkrevd (utenom --self-test)", file=sys.stderr)
        return 1

    verdict, code, detail = evaluate(a_list, b_list, forbid_prefixes=args.forbid_prefix)
    if verdict == "overlap":
        preview = detail[:10]
        print(f"{verdict}({len(detail)}) {preview}")
    elif verdict == "client-code":
        # Begge sider navngis eksplisitt (kode-review-funn, VIKTIG 1) — aldri kun ÉN
        # side, selv om kun én er ikke-tom.
        print(f"{verdict} a={detail['a']} b={detail['b']}")
    else:
        print(verdict)
    return code


if __name__ == "__main__":
    sys.exit(main())
