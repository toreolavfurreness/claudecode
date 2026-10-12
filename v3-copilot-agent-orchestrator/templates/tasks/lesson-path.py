#!/usr/bin/env python3
"""Filsti for en ny lesson, etter skrive-protokollen i tasks/lessons.md (brukes av /lesson-new).

  python3 tasks/lesson-path.py <tema> "<tittel>" [--date YYYY-MM-DD] [--new-tema]
      skriver tasks/lessons/<tema>/<dato>-<slug>.md; finnes navnet, får det -2, -3 …
      Exit 2 hvis temaet ikke finnes (uten --new-tema) eller er ugyldig.
  python3 tasks/lesson-path.py --tags [<tema>]
      eksisterende tagger med antall, flest først — gjenbruk før du finner på nye
  python3 tasks/lesson-path.py --self-test

Slug-algoritmen er den samme som `scripts/split-lessons.py` bruker, så nye filnavn følger de gamle.
"""
import datetime
import re
import sys
import tempfile
import unicodedata
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent / "lessons"


def slug(s):
    s = s.lower().replace("æ", "ae").replace("ø", "oe").replace("å", "aa")
    s = "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s[:60].rstrip("-") or "x"


def lesson_path(root, tema, title, date, new_tema=False):
    if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", tema):
        raise ValueError(f"tema må være kebab-case: {tema!r}")
    d = root / tema
    if not d.is_dir() and not new_tema:
        known = ", ".join(sorted(p.name for p in root.iterdir() if p.is_dir()))
        raise ValueError(f"tema {tema!r} finnes ikke (finnes: {known}). Ny mappe: --new-tema")
    base = f"{date}-{slug(title)}"
    p, n = d / f"{base}.md", 2
    while p.exists():
        p, n = d / f"{base}-{n}.md", n + 1
    return p


def tags(root, tema=None):
    c = Counter()
    for f in root.glob(f"{tema or '*'}/*.md"):
        for line in f.read_text(encoding="utf-8").splitlines():
            if line.startswith("tags:"):
                c.update(t.strip() for t in line[5:].strip(" []").split(",") if t.strip())
                break
    return c


def self_test():
    ok = True

    def check(name, got, want):
        nonlocal ok
        good = got == want
        ok &= good
        print(f"{'ok ' if good else 'RØD'}  {name}" + ("" if good else f": fikk {got!r}, ventet {want!r}"))

    check("æøå og tegn", slug("Æøå: `x.is_selected` — NULL!"), "aeoeaa-x-is-selected-null")
    check("maks 60, ingen hengende -", len(slug("a" * 59 + " b")) <= 60 and not slug("a" * 59 + " b").endswith("-"), True)
    check("tom tittel", slug("—"), "x")
    with tempfile.TemporaryDirectory() as t:
        root = Path(t)
        (root / "rls").mkdir()
        p1 = lesson_path(root, "rls", "Samme tittel", "2026-10-02")
        check("første navn", p1.name, "2026-10-02-samme-tittel.md")
        p1.write_text("---\ntags: [a, b]\n---\n", encoding="utf-8")
        p2 = lesson_path(root, "rls", "Samme tittel", "2026-10-02")
        check("kollisjon gir -2", p2.name, "2026-10-02-samme-tittel-2.md")
        p2.write_text("---\ntags: [a]\n---\n", encoding="utf-8")
        check("kollisjon gir -3", lesson_path(root, "rls", "Samme tittel", "2026-10-02").name, "2026-10-02-samme-tittel-3.md")
        check("tag-telling", tags(root)["a"], 2)
        for bad in ("finnes-ikke", "Store_Bokstaver"):
            try:
                lesson_path(root, bad, "x", "2026-10-02")
                check(f"avviser {bad}", "ingen feil", "ValueError")
            except ValueError:
                check(f"avviser {bad}", "ValueError", "ValueError")
        check("--new-tema", lesson_path(root, "nytt-tema", "x", "2026-10-02", True).parent.name, "nytt-tema")
    return 0 if ok else 1


def main(argv):
    if argv[:1] == ["--self-test"]:
        return self_test()
    if argv[:1] == ["--tags"]:
        for tag, n in tags(ROOT, argv[1] if len(argv) > 1 else None).most_common():
            print(f"{n:5} {tag}")
        return 0
    new_tema = "--new-tema" in argv
    argv = [a for a in argv if a != "--new-tema"]
    date = datetime.date.today().isoformat()
    if "--date" in argv:
        i = argv.index("--date")
        date = argv[i + 1]
        argv = argv[:i] + argv[i + 2:]
    if len(argv) != 2 or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date):
        print(__doc__, file=sys.stderr)
        return 2
    try:
        p = lesson_path(ROOT, argv[0], argv[1], date, new_tema)
    except ValueError as e:
        print(f"FEIL: {e}", file=sys.stderr)
        return 2
    print(p.relative_to(ROOT.parent.parent))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
