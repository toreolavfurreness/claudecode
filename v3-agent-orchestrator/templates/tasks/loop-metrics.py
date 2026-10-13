#!/usr/bin/env python3
"""Måling av lens-effekt og graf-treff fra run-loggen.

Kall (fra repo-rota, kun standardbibliotek, diagnostikk og `FEIL: …` på stderr):
  python3 tasks/loop-metrics.py --token FIL [FIL …]       # lens=-tokenet for én todo, fra rundenes funn-filer
  python3 tasks/loop-metrics.py [--since <iso>] [--log F] # tabellen per lens for et vindu
  python3 tasks/loop-metrics.py --graph [--since <iso>]   # presisjon og dekning for grafens fil-kanter
  python3 tasks/loop-metrics.py --self-test

--token: hver FIL er `code_review.findings[]` for én runde. Per `source_agent`, summert over filene:
  funn   = antall funn (forekomster per runde: et funn som står urettet i runde 2, telles to ganger)
  hevet  = funn der `honest_severity` finnes og er ulik `severity`. Bare hevinger revieweren selv
           melder. Mekaniske hevinger står i `floor=`.
  reelle = funn der `honest_severity` (eller `severity` når feltet mangler) er BLOKKERENDE
  regr   = funn der `regression` er true
Stdout: `lens=<agent>:<funn>/<hevet>/<reelle>/<regr>,…` alfabetisk, eller `lens=none`. Exit 1 med
tom stdout når en fil ikke kan leses, ikke er en JSON-array, eller et funn bryter kontrakten.

Vindu: uten `--since` er det `merged`-radene etter siste `health`-linje i fila (linjeposisjon, fordi
tidsstempelet har minuttoppløsning og kolliderer). Med `--since` er det tidsstempel >= verdien.
  floor            = summen av heltallet rett etter `floor=`. `none` og `n/a` teller 0.
  rounds_per_merge = summen av kolonne 8 (`code_review_rounds`) delt på `merged`, to desimaler med
                     komma. Rader med 0 runder teller med. `merged=0` gir `n/a`.
  uten_lens        = rader med `code_review_rounds` >= 1 som mangler `lens=` eller har `lens=unknown`
  utenfor_selector = merger der lensen har reelle > 0 og agentnavnet ikke er en delstreng av
                     `selector=`-verdien fram til neste `;`. `{{PROJECT_NAME}}-code-reviewer` står aldri i
                     `selector=`, så kolonnen er `-` for den. Undertelling når navnet står i fritekst
                     etter lista (`… (rls-migration-reviewer ikke triggeret …)`).

--graph: per `merged`-rad er k = målene for `file`-kanter ut fra `todo:<nr>`, p = filene i PR-en
(`gh pr view`), t = snittet. Feiler `gh` for en rad, står den som `IKKE MÅLT`, teller ikke i
summen, og exit er 1.
"""
import argparse
import json
import os
import re
import subprocess
import sys

RANK = {"MINDRE": 0, "VIKTIG": 1, "BLOKKERENDE": 2}
SYNTH = "{{PROJECT_NAME}}-code-reviewer"
RUN_LOG = "docs/superpowers/loop/run-log.md"
LENS_RE = re.compile(r"(?:^|[; ])lens=([^; ]+)")
LENS_PART_RE = re.compile(r"([a-z0-9-]+):(\d+)/(\d+)/(\d+)/(\d+)$")


def token(rounds):
    """rounds = én liste med funn per runde. Kaster ValueError ved kontraktbrudd."""
    acc = {}
    for findings in rounds:
        if not isinstance(findings, list):
            raise ValueError("ikke en JSON-array")
        for f in findings:
            if not isinstance(f, dict) or not f.get("source_agent") or f.get("severity") not in RANK:
                raise ValueError(f"funn mangler source_agent eller gyldig severity: {f!r}")
            sev = f["severity"]
            honest = f.get("honest_severity", sev)
            if honest not in RANK or RANK[honest] > RANK[sev]:
                raise ValueError(f"honest_severity utenfor enumen eller høyere enn severity: {f!r}")
            a = acc.setdefault(f["source_agent"], [0, 0, 0, 0])
            a[0] += 1
            a[1] += honest != sev
            a[2] += honest == "BLOKKERENDE"
            a[3] += f.get("regression") is True
    if not acc:
        return "lens=none"
    return "lens=" + ",".join(f"{k}:{'/'.join(map(str, v))}" for k, v in sorted(acc.items()))


def parse_lens(line):
    """None = mangler, `unknown` eller uleselig (alt regnes som umålt). {} = `lens=none`."""
    m = LENS_RE.search(line)
    if not m or m.group(1) == "none":
        return {} if m else None
    out = {}
    for part in m.group(1).split(","):
        pm = LENS_PART_RE.match(part)
        if not pm:
            return None
        out[pm.group(1)] = [int(x) for x in pm.groups()[1:]]
    return out


def window(lines, since=None):
    """Returnerer (since-etikett, merged-rader som kolonnelister med hele linja sist)."""
    rows, label = [], since or "start"
    for line in lines:
        cols = line.rstrip("\n").split(" | ")
        if len(cols) < 8:
            continue
        if cols[3] == "health" and not since:
            rows, label = [], "health:" + cols[0]
        elif cols[3] == "merged" and (not since or cols[0] >= since):
            rows.append(cols + [line])
    return label, rows


def table(label, rows):
    merged = len(rows)
    floor = rounds = uten = 0
    agents = {}  # navn -> [merger, funn, hevet, reelle, regr, utenfor_selector]
    for cols in rows:
        line = cols[-1]
        m = re.match(r"\d+", cols[7])
        r = int(m.group()) if m else 0
        rounds += r
        fm = re.search(r"floor=(\d+)", line)
        floor += int(fm.group(1)) if fm else 0
        lens = parse_lens(line)
        if lens is None:
            uten += r >= 1
            continue
        sm = re.search(r"selector=([^;]*)", line)
        selector = sm.group(1) if sm else ""
        for name, (funn, hevet, reelle, regr) in lens.items():
            a = agents.setdefault(name, [0] * 6)
            a[0] += 1
            a[1] += funn
            a[2] += hevet
            a[3] += reelle
            a[4] += regr
            # ponytail: delstreng-treff, så parentesformer treffer. Undertelling når navnet står i
            # fritekst etter lista. Splitt på komma og stripp parentes hvis det viser seg i tallene.
            a[5] += reelle > 0 and name not in selector
    rpm = f"{rounds / merged:.2f}".replace(".", ",") if merged else "n/a"
    out = [
        f"vindu: since={label} merged={merged} uten_lens={uten} floor={floor} rounds_per_merge={rpm}",
        "| lens | merger | funn | hevet | reelle | regresjoner | utenfor_selector |",
        "|---|---|---|---|---|---|---|",
    ]
    for name, a in sorted(agents.items()):
        last = "-" if name == SYNTH else a[5]
        out.append(f"| {name} | {a[0]} | {a[1]} | {a[2]} | {a[3]} | {a[4]} | {last} |")
    tot = [sum(a[i] for a in agents.values()) for i in range(6)]
    out.append(f"sum: lens={tot[2]}/{tot[1]};real_block={tot[3]};rounds_per_merge={rpm}")
    return "\n".join(out)


def graph_score(k, p):
    """(t, k, p) for kant-mål k og PR-filer p."""
    k, p = set(k), set(p)
    return len(k & p), len(k), len(p)


def read_log(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return fh.readlines()
    except OSError as exc:
        sys.exit(f"FEIL: kan ikke lese {path}: {exc}")


def run_graph(rows):
    builder = os.path.join(os.path.dirname(os.path.abspath(__file__)), "graph-build.py")
    r = subprocess.run(["python3", builder], capture_output=True, text=True)
    sys.stderr.write(r.stderr)
    if r.returncode != 0:
        sys.exit("FEIL: graph-build.py feilet")
    edges = json.loads(r.stdout)["edges"]
    tot, n, failed = [0, 0, 0], 0, False
    for cols in rows:
        nr = cols[1]
        pm = re.search(r"(?:#|/pull/)(\d+)", cols[5])
        if pm:
            # ponytail: gh gir de 100 første filene. Bruk `gh api --paginate` hvis en PR er større.
            g = subprocess.run(
                ["gh", "pr", "view", pm.group(1), "--json", "files", "--jq", ".files[].path"],
                capture_output=True,
                text=True,
            )
            err = None if g.returncode == 0 else (g.stderr.strip().splitlines() or ["gh feilet"])[0]
        else:
            err = "ingen PR i raden"
        pr = pm.group(1) if pm else cols[5]
        if err:
            failed = True
            print(f"todo={nr} pr={pr} IKKE MÅLT: {err}")
            continue
        # ponytail: nr.lower() i stedet for graph-build sin norm_id; importer den hvis en ID med
        # ledende nuller dukker opp
        src = "todo:" + nr.lower()
        k = [e["target"][5:] for e in edges if e["source"] == src and e["type"] == "file"]
        t, kn, pn = graph_score(k, g.stdout.splitlines())
        print(f"todo={nr} pr={pr} precision={t}/{kn} coverage={t}/{pn}")
        tot = [tot[0] + t, tot[1] + kn, tot[2] + pn]
        n += 1
    print(f"sum: graph_precision={tot[0]}/{tot[1]};graph_coverage={tot[0]}/{tot[2]};n={n}")
    return 1 if failed else 0


def self_test():
    n = 0

    def eq(got, want):
        nonlocal n
        assert got == want, f"\n fikk:   {got!r}\n ventet: {want!r}"
        n += 1

    B, V, M = "BLOKKERENDE", "VIKTIG", "MINDRE"
    r1 = [{"severity": B, "honest_severity": M, "source_agent": "b"}, {"severity": V, "source_agent": "a"}]
    r2 = [{"severity": B, "honest_severity": B, "source_agent": "b", "regression": True}]
    eq(token([r1, r2]), "lens=a:1/0/0/0,b:2/1/1/1")  # to runder summert, lik honest er ikke hevet
    eq(token([[], []]), "lens=none")
    for bad in ({"severity": B}, {"source_agent": "a"}, {"severity": V, "honest_severity": B, "source_agent": "a"},
                {"severity": V, "honest_severity": "x", "source_agent": "a"}):
        try:
            token([[bad]])
            raise AssertionError(f"godtok {bad!r}")
        except ValueError:
            n += 1
    try:
        token([{"findings": []}])
        raise AssertionError("godtok et objekt")
    except ValueError:
        n += 1

    def row(ts, kind, rounds, tail):
        return f"{ts} | 1 | s | {kind} | - | #1 | 1 | {rounds} | M | - | - | {tail}\n"

    log = [
        row("T10:00", "merged", 1, "selector=x; floor=4; lens=x:9/9/9/9"),
        row("T10:00", "health", 0, "sha=y"),
        row("T10:00", "merged", 2, "selector=y,x(koordinator-pålagt); floor=1 viol=0; lens=x:2/1/1/0,y:1/0/0/1"),
        row("T10:01", "merged", 1, "selector=ingen (x ikke triggeret); floor=none; lens=x:1/0/1/0,z:1/0/1/0"),
        row("T10:02", "merged", 1, "selector=none; floor=0"),
        row("T10:03", "merged", 0, "selector=none"),
        row("T10:04", "merged", 3, "selector=x; lens=unknown"),
        row("T10:05", "failed", 5, "lens=x:1/1/1/1"),
    ]
    label, rows = window(log)
    eq(label, "health:T10:00")
    eq(len(rows), 5)  # raden i samme minutt foran helseraden er ute
    eq(
        table(label, rows).split("\n"),
        [
            "vindu: since=health:T10:00 merged=5 uten_lens=2 floor=1 rounds_per_merge=1,40",
            "| lens | merger | funn | hevet | reelle | regresjoner | utenfor_selector |",
            "|---|---|---|---|---|---|---|",
            "| x | 2 | 3 | 1 | 2 | 0 | 0 |",  # parentesform treffer, fritekst gir undertelling
            "| y | 1 | 1 | 0 | 0 | 1 | 0 |",
            "| z | 1 | 1 | 0 | 1 | 0 | 1 |",
            "sum: lens=1/5;real_block=3;rounds_per_merge=1,40",
        ],
    )
    label, rows = window(log, "T10:00")
    eq((label, len(rows)), ("T10:00", 6))
    eq(table(*window(log, "T99")).split("\n")[0], "vindu: since=T99 merged=0 uten_lens=0 floor=0 rounds_per_merge=n/a")
    eq(table(*window([row("T1", "merged", 1, f"lens={SYNTH}:1/0/1/0")])).split("\n")[3], f"| {SYNTH} | 1 | 1 | 0 | 1 | 0 | - |")
    eq(window(log[2:])[0], "start")
    eq(graph_score([], ["a.ts"]), (0, 0, 1))
    eq(graph_score(["a.ts", "b.ts"], ["a.ts", "c.md", "d.md"]), (1, 2, 3))
    print(f"self-test: OK ({n} asserts)")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--token", nargs="+", metavar="FIL")
    ap.add_argument("--since", metavar="ISO")
    ap.add_argument("--log", default=RUN_LOG, metavar="FIL")
    ap.add_argument("--graph", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return self_test()
    if args.token:
        rounds = []
        for path in args.token:
            try:
                with open(path, encoding="utf-8") as fh:
                    rounds.append(json.load(fh))
                token(rounds[-1:])
            except (OSError, ValueError) as exc:
                sys.exit(f"FEIL: kan ikke lese {path}: {exc}")
        return print(token(rounds))
    label, rows = window(read_log(args.log), args.since)
    if args.graph:
        sys.exit(run_graph(rows))
    print(table(label, rows))


if __name__ == "__main__":
    main()
