#!/usr/bin/env python3
"""Kadens-gate for §6c: er helsesjekken forfalt?

  python3 tasks/loop-cadence.py [run-log]     (standard: docs/superpowers/loop/run-log.md)
  python3 tasks/loop-cadence.py --self-test

Teller `merged`-rader etter siste `health`-rad, SORTERT PÅ TIDSSTEMPEL. Run-loggen står ikke
alltid i tidsrekkefølge (parallelle implementere, re-kjørte §6-haler), så en teller som nullstiller
på «siste health-rad i fila» kan nullstille på en eldre rad.
Exit 0 = ikke forfalt. Exit 1 = forfalt: kjør §6c før neste dispatch. Exit 2 = fant ikke run-loggen.

Hvorfor en gate og ikke en huskeregel: målt i opphavsprosjektet kom helsesjekkene etter 44, 13, 11,
9 og 7 merger med intervall 5. Glipper §6c, kjører heller ikke §8b/§8c.
"""
import re, sys

INTERVAL = int("{{HEALTH_CHECK_INTERVAL}}")
ROW = re.compile(r"^\|?\s*(\d{4}-\d{2}-\d{2}T\d{2}:\d{2})\s*\|")


def merges_since_health(text):
    rows = []
    for line in text.splitlines():
        if not ROW.match(line):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) >= 4:
            rows.append((cells[0], cells[3]))
    last = max((ts for ts, out in rows if out == "health"), default="")
    return sum(1 for ts, out in rows if out == "merged" and ts > last)


def self_test():
    log = ("2026-09-01T10:00 | 1 | a | merged | - |\n"
           "2026-09-02T10:00 | - | loop-health-check | health | - |\n"
           "2026-09-03T10:00 | 2 | b | merged | - |\n"
           "| 2026-09-04T10:00 | 3 | c | merged | - |\n"          # rad med ledende |
           "2026-09-01T12:00 | - | loop-health-check | health | - |\n"  # eldre health-rad lenger ned
           "| `timestamp` | streng | ISO | kilde |\n")             # spec-rad, ikke en runde
    checks = [
        (merges_since_health(log) == 2, "teller fra nyeste health-rad, ikke siste i fila"),
        (merges_since_health("2026-09-01T10:00 | 1 | a | merged | - |\n") == 1, "ingen health-rad: tell alt"),
        (merges_since_health("") == 0, "tom logg"),
    ]
    for ok, msg in checks:
        print(("PASS " if ok else "FAIL ") + msg)
    return 0 if all(ok for ok, _ in checks) else 1


def main(argv):
    if "--self-test" in argv:
        return self_test()
    path = argv[0] if argv else "docs/superpowers/loop/run-log.md"
    try:
        text = open(path, encoding="utf-8").read()
    except OSError as e:
        print(f"FEIL: {e}", file=sys.stderr)
        return 2
    n = merges_since_health(text)
    print(f"STATUS health={n}/{INTERVAL}")
    if n >= INTERVAL:
        print(f"FORFALT §6c helsesjekk: {n} merger siden siste health-rad (intervall {INTERVAL})")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
