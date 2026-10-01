#!/usr/bin/env python3
# GENERERT av /setup fra loop.config.yaml — IKKE rediger her.
# Endre loop.config.yaml og kjør /setup på nytt.
"""review-lens-select.py — beregner hvilke tech-review-agenter en filliste
UTLØSER, som et mekanisk GULV for koordinatorens fan-in-verifisering
(TODO 180A).

Leser IKKE loop.config.yaml. Globene under (TRIGGER_GLOBS) er substituert inn
av /setup på SETUP-TID, ikke lest ved kjøring — samme kontrakt som resten av
kit-et (loop.config.yaml:2-4: "Charterne leser ALDRI denne ved runtime").
Endrer du en glob: rediger loop.config.yaml og kjør /setup på nytt, IKKE denne
fila for hånd.

TRIGGER_GLOBS er et GULV, ikke en fasit: den mekanisk sikre delmengden av
hver agents trigger-prosa (se loop.config.yaml-kommentaren og charterets
trigger:-felt). Koordinatoren bruker output slik:

    expected_by_selector ⊆ fan_in.dispatched   — brudd = under-dispatch
    fan_in.returned == fan_in.dispatched       — brudd = stille node
    fan_in.dispatched ⊆ config-navnene         — brudd = ukjent agent

Over-dispatch (kode-revieweren dispatcher bredere enn globene fordi
trigger-prosaen er bredere) er TILLATT og rapporteres — ikke en feil her.

Glob-semantikk: sammenligningen bruker Pythons fnmatch.fnmatch, der `*`
KRYSSER `/` (i motsetning til shell-globbing). "supabase/migrations/*"
betyr derfor "hva som helst under supabase/migrations/, uansett dybde" —
ikke bare direkte barn.

Bruk:
    python3 tasks/review-lens-select.py --files FIL    # én filsti per linje i FIL
    python3 tasks/review-lens-select.py --files -      # filstier fra stdin

JSON på stdout: {"triggered": ["<agent-navn>", ...], "file_count": N}.
`triggered` følger TRIGGER_GLOBS' konfig-rekkefølge (ikke set-iterasjon),
er tom liste hvis ingen fil traff noen glob, og duplikatfri.

All diagnostikk går til stderr. Uleselig input (manglende fil, lesefeil)
FEILER HØYT (exit != 0) — et tomt gulv ved feil ville vært en fail-open
sikkerhetsvakt (TODO 176s BLOKKERENDE B2-klasse / TODO 181s leftover-regex-
klasse). En TOM filliste (0 linjer — f.eks. en diff uten filer) er derimot
lovlig input og gir triggered=[] med exit 0, ikke en feil.
"""
import argparse
import fnmatch
import json
import sys

{{TECH_REVIEW_TRIGGER_GLOBS}}


def read_files(path):
    """Les filstier, én per linje, fra FIL eller stdin ("-"). Feiler høyt på
    uleselig input i stedet for å stille returnere en tom liste (R1)."""
    if path == "-":
        raw = sys.stdin.read()
    else:
        try:
            with open(path, "r", encoding="utf-8") as f:
                raw = f.read()
        except OSError as e:
            sys.exit(f"FEIL: kan ikke lese --files {path!r}: {e}")
    return [line.strip() for line in raw.splitlines() if line.strip()]


def select(files):
    """Returner agentnavn (i TRIGGER_GLOBS-rekkefølge, V5) der minst én fil
    matcher minst én av agentens globs."""
    triggered = []
    for name, globs in TRIGGER_GLOBS.items():
        if any(fnmatch.fnmatch(f, g) for f in files for g in globs):
            triggered.append(name)
    return triggered


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--files", required=True, help="Fil med én filsti per linje, eller '-' for stdin.")
    args = ap.parse_args()

    files = read_files(args.files)
    print(f"[review-lens-select] {len(files)} fil(er) lest fra {args.files!r}", file=sys.stderr)

    triggered = select(files)
    print(f"[review-lens-select] triggered: {triggered}", file=sys.stderr)

    print(json.dumps({"triggered": triggered, "file_count": len(files)}))


if __name__ == "__main__":
    main()
