#!/usr/bin/env python3
"""Drift-vakt: melder når et prosjekt har gått bort fra kit-malen i filer som skal være like overalt.

  python3 tasks/kit-drift.py                 sammenlign mot v3-agent-orchestrator/templates/
  python3 tasks/kit-drift.py --kit <dir>     sammenlign mot en annen templates-mappe (f.eks. en fersk
                                             klone av kit-repoet, for å se om prosjektet ligger bak)
  python3 tasks/kit-drift.py --diff          skriv også selve diffen
  python3 tasks/kit-drift.py --self-test

Det som sjekkes:
  - KIT_FILES: fila skal være malen med substitusjons-tokens byttet ut (slik /setup skriver den). Token-
    verdiene leses ut av prosjektfila selv, så vakten trenger ikke loop.config.yaml.
  - KIT_ROWS: én rad i en prosjekt-eid tabell der bestemte kolonner skal stå som i malen
    (Køsiden-raden i artifacts.md: generator og vakt; URL-en er prosjektets).

Prosjektspesifikt innhold hører hjemme i tasks/queue-config.py, ikke i queue-status.py.

Exit 0 = ingen avvik · 1 = avvik (AVVIK-linjer) · 2 = fant ikke kit-malen.
"""
import difflib
import os
import re
import sys

KIT_FILES = ["tasks/queue-status.py"]
# (fil, verdien i første kolonne, kolonnene som skal være like — 0-basert)
KIT_ROWS = [("docs/superpowers/loop/artifacts.md", "Køsiden", (2, 3))]

TOKEN = re.compile(r"\{\{[A-Z0-9_]+\}\}")


def learn_tokens(tpl_lines, proj_lines):
    """Token-verdiene prosjektet ble generert med, lest ut av linjer der malen har et token."""
    values = {}
    proj_set = set(proj_lines)
    for t in tpl_lines:
        toks = TOKEN.findall(t)
        if not toks or all(x in values for x in toks):
            continue
        parts = TOKEN.split(t)
        rx = "".join(re.escape(p) + ("(.*?)" if i < len(toks) else "") for i, p in enumerate(parts))
        rx = re.compile("^" + rx + "$")
        for p in proj_set:
            m = rx.match(p)
            if m:
                for tok, val in zip(toks, m.groups()):
                    values.setdefault(tok, val)
                break
    return values


def render(text, values):
    for k, v in values.items():
        text = text.replace(k, v)
    return text


def check_file(rel, kit, show_diff):
    tpl_path = os.path.join(kit, rel)
    if not os.path.exists(tpl_path):
        return [f"AVVIK {rel}: finnes ikke i kit-malen ({tpl_path})"]
    if not os.path.exists(rel):
        return [f"AVVIK {rel}: mangler i prosjektet. Kjør /setup."]
    tpl = open(tpl_path, encoding="utf-8").read()
    proj = open(rel, encoding="utf-8").read()
    want = render(tpl, learn_tokens(tpl.splitlines(), proj.splitlines()))
    if want == proj:
        return [f"OK    {rel}"]
    d = list(difflib.unified_diff(want.splitlines(), proj.splitlines(),
                                  f"kit/{rel}", rel, lineterm="", n=1))
    plus = sum(1 for x in d if x.startswith("+") and not x.startswith("+++"))
    minus = sum(1 for x in d if x.startswith("-") and not x.startswith("---"))
    out = [f"AVVIK {rel}: +{plus}/−{minus} linjer mot {tpl_path}. Kjør /setup for å ta inn malen; "
           "flytt prosjektspesifikke endringer til tasks/queue-config.py."]
    if show_diff:
        out += d
    return out


def table_row(path, first):
    for line in open(path, encoding="utf-8"):
        if line.startswith("|"):
            cells = [c.strip() for c in re.split(r"(?<!\\)\|", line.strip())[1:-1]]
            if cells and cells[0] == first:
                return cells
    return None


def check_row(rel, first, cols, kit):
    tpl_path = os.path.join(kit, rel)
    if not os.path.exists(tpl_path) or table_row(tpl_path, first) is None:
        return [f"AVVIK {rel}: kit-malen har ingen «{first}»-rad ({tpl_path})"]
    if not os.path.exists(rel):
        return [f"AVVIK {rel}: mangler i prosjektet. Kjør /setup."]
    want, have = table_row(tpl_path, first), table_row(rel, first)
    if have is None:
        return [f"AVVIK {rel}: mangler «{first}»-raden. Kopier den fra {tpl_path} og fyll inn URL-en."]
    bad = [i for i in cols if i >= len(have) or have[i] != want[i]]
    if not bad:
        return [f"OK    {rel} («{first}»-raden)"]
    return [f"AVVIK {rel}: «{first}»-raden avviker fra malen i kolonne {', '.join(str(i + 1) for i in bad)}. "
            f"Forventet: {' | '.join(want[i] for i in bad)}"]


def main(argv):
    kit = argv[argv.index("--kit") + 1] if "--kit" in argv else "v3-agent-orchestrator/templates"
    if not os.path.isdir(kit):
        print(f"UKJENT: fant ikke kit-malen i {kit}. Oppgi den med --kit <templates-mappe>.")
        return 2
    lines = []
    for rel in KIT_FILES:
        lines += check_file(rel, kit, "--diff" in argv)
    for rel, first, cols in KIT_ROWS:
        lines += check_row(rel, first, cols, kit)
    print("\n".join(lines))
    return 1 if any(x.startswith("AVVIK") for x in lines) else 0


def self_test():
    import shutil
    import subprocess
    import tempfile
    fails = []
    me = os.path.abspath(__file__)

    def check(name, cond):
        print(("ok   " if cond else "FEIL ") + name)
        if not cond:
            fails.append(name)

    # Tokenene bygges her, så /setup ikke bytter dem ut i denne fila.
    proj_tok, base_tok = "{" * 2 + "PROJECT_NAME" + "}" * 2, "{" * 2 + "BASE_BRANCH" + "}" * 2
    tpl_py = f'TITLE = "{proj_tok}-køen"\nREF = "origin/{base_tok}"\nprint(1)\n'
    tpl_md = (f"| Side | URL | Generator (`origin/{base_tok}`) | Vakt |\n|---|---|---|---|\n"
              "| Køsiden | (fylles inn) | `gen > x` | `grep -c a \\| wc` = 1 |\n")
    proj_py = 'TITLE = "demo-køen"\nREF = "origin/dev"\nprint(1)\n'
    proj_md = ("| Side | URL | Generator (`origin/dev`) | Vakt |\n|---|---|---|---|\n"
               "| Køsiden | https://claude.ai/artifact/x | `gen > x` | `grep -c a \\| wc` = 1 |\n"
               "| Egen side | https://claude.ai/artifact/y | `annet` | `x` |\n")

    def run(py=proj_py, md=proj_md, kit=True):
        tmp = tempfile.mkdtemp()
        try:
            if kit:
                for rel, txt in (("tasks/queue-status.py", tpl_py),
                                 ("docs/superpowers/loop/artifacts.md", tpl_md)):
                    p = os.path.join(tmp, "v3-agent-orchestrator/templates", rel)
                    os.makedirs(os.path.dirname(p), exist_ok=True)
                    open(p, "w", encoding="utf-8").write(txt)
            for rel, txt in (("tasks/queue-status.py", py), ("docs/superpowers/loop/artifacts.md", md)):
                if txt is not None:
                    os.makedirs(os.path.join(tmp, os.path.dirname(rel)), exist_ok=True)
                    open(os.path.join(tmp, rel), "w", encoding="utf-8").write(txt)
            r = subprocess.run([sys.executable, me], cwd=tmp, capture_output=True, text=True)
            return r.returncode, r.stdout
        finally:
            shutil.rmtree(tmp)

    rc, out = run()
    check("lik malen (tokens utfylt, egen URL og egne rader): exit 0", rc == 0 and "AVVIK" not in out)
    rc, out = run(py=proj_py.replace("print(1)", "print(2)"))
    check("endret linje: exit 1 med +1/−1", rc == 1 and "AVVIK tasks/queue-status.py: +1/−1" in out)
    rc, out = run(py=None)
    check("manglende fil: exit 1", rc == 1 and "mangler i prosjektet" in out)
    rc, out = run(md=proj_md.replace("`gen > x`", "`gen > y`"))
    check("Køsiden-raden med annen generator: exit 1", rc == 1 and "kolonne 3" in out)
    rc, out = run(md=proj_md.replace("| Køsiden |", "| Kø |"))
    check("Køsiden-raden mangler: exit 1", rc == 1 and "mangler «Køsiden»-raden" in out)
    rc, out = run(kit=False)
    check("uten kit-mal: exit 2", rc == 2 and "UKJENT" in out)

    print("SELF-TEST " + ("GRØNN" if not fails else f"RØD ({len(fails)} feil)"))
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(self_test() if "--self-test" in sys.argv else main(sys.argv[1:]))
