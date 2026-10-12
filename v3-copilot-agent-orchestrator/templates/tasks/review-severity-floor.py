#!/usr/bin/env python3
# GENERERT av /setup fra loop.config.yaml — IKKE rediger her.
# Endre loop.config.yaml og kjør /setup på nytt.
"""review-severity-floor.py — håndhever severity_floor per tech-review-agent
i kode, som et MEKANISK GULV på synthesizerens (kode-reviewerens) egne
severity-vurderinger.

Leser IKKE loop.config.yaml. SEVERITY_FLOORS og FLOOR_EXEMPTIONS under er
substituert inn av /setup på SETUP-TID, ikke lest ved kjøring — samme
kontrakt som tasks/review-lens-select.py og resten av kit-et
(loop.config.yaml:2-4: "Charterne leser ALDRI denne ved runtime"). Endrer du
et gulv eller et gulvunntak: rediger loop.config.yaml og kjør /setup på nytt,
IKKE denne fila for hånd.

Synthesizeren (kode-revieweren) setter severity på ALLE funn ut fra hele
diff-konteksten — IKKE fra lensens eget ordvalg (lensene leverer severity-frie
observasjoner, se report-schema.md). Dette skriptet håndhever at synthesizeren
aldri kan la et funn fra en gulvet lens ende opp LAVERE enn agentens gulv.
Hevingen er max(severity, floor) — ALDRI tilordning: et BLOKKERENDE funn fra
en agent med gulv VIKTIG skal forbli BLOKKERENDE.

PAUSEPUNKT er et RUTINGS-gulv, ikke en severity-rang. Det finnes ikke i
funn-enumen (BLOKKERENDE|VIKTIG|MINDRE), hever/senker ALDRI severity — funn
fra en PAUSEPUNKT-gulvet agent havner i `pausepunkt[]` med severity urørt, og
koordinatoren bærer dem inn i PR-ens manuelle verifiseringssjekkliste og
run-log.md felt 11 (`pausepunkt=<agent>:<antall>`).

Et gulv på `null` betyr «intet gulv» — funnet er fullt underlagt
synthesizerens skjønn og passerer uendret.

Gulvunntak. Et funn kan bære `"floor_exempt": "comment_doc_wording"`
(satt av synthesizeren, se report-schema.md og code-reviewer-charteret). Dette
skriptet avgjør mekanisk, første treff vinner:
  - ugyldig markørverdi (ikke i VALID_EXEMPT_CLASSES) → `violations[]` (exit 1,
    usignert rapport) — IKKE en krasj, og IKKE en stille nedgradering
  - agenten mangler klassen i FLOOR_EXEMPTIONS → `agent_not_exempt_eligible`
  - `--rev` mangler → `no_rev`
  - `check_ref(repo, rev, ref)` returnerer en `reason` (`ref_unparseable` |
    `ref_unresolvable` | `ref_not_comment_or_docs`) → den reason-en
  - ellers (referansen peker på kommentarlinje(r) eller en .md-fil under docs/)
    → godtatt: funnet havner i `exempt[]` og beholder sin severity uendret
Et avvist funn (noen av de fire reason-verdiene) går videre gjennom den
vanlige gulvlogikken som om `floor_exempt` ikke var satt — unntaket senker
ALDRI severity, og skriptet SER ALDRI rettelsen: koordinatoren leser
`issue`/`fix` mot hovedkriteriet (eneste kontroll av selve funnet), og fra
r≥2 sjekker diffen mot forrige rundes verifiserte sha at FORRIGE fix-runde
bare endret ordlyd i ref-fila — rettelsen av DETTE unntatte funnet
verifiseres aldri (coordinator-runbook.md §5b «Gulvunntak for ordlyd»).

Bruk:
    python3 tasks/review-severity-floor.py --findings FIL [--rev SHA] [--repo DIR]
    python3 tasks/review-severity-floor.py --findings -    # JSON-array fra stdin

`--rev` og `--repo` er valgfrie og brukes KUN til å slå opp `ref`-linjer for
`floor_exempt`-merkede funn (`--repo` default: repo-roten, kun til tester og
diagnose — står ikke i runbooken). Uten `--rev` avvises ethvert merket funn
med reason `no_rev` og går gjennom normalt gulv.

Input: JSON-array av funn. Hvert funn MÅ ha `source_agent` (ett av
SEVERITY_FLOORS' nøkler, eller synthesizeren selv) og `severity`
(BLOKKERENDE|VIKTIG|MINDRE). Andre felt (`ref`, `issue`, `fix`, …) leses ikke
av dette skriptet og kreves ikke her — de valideres av report-schema.md.
Unntak: et `floor_exempt`-merket funns `ref` LESES av `check_ref` for å
avgjøre unntaket.

JSON på stdout:
    {
      "findings":         [...],  // samme array, med severity hevet der gulvet krever det
      "raised":           [{"ref": ..., "source_agent": ..., "from": ..., "to": ...}, ...],
      "pausepunkt":       [...],  // funn fra PAUSEPUNKT-gulvede agenter, severity urørt
      "violations":       [...],  // kontraktbrudd — se under
      "exempt":           [...],  // godtatte floor_exempt-funn (severity uendret)
      "exempt_rejected":  [...]   // avviste floor_exempt-funn, med reason
    }

FEILER HØYT (exit != 0), ALDRI fail-open, på ett eller flere av:
  - uleselig input (manglende fil, ugyldig JSON, ikke en array)
  - et funn uten `source_agent`
  - `source_agent` utenfor SEVERITY_FLOORS.keys() ∪ {SYNTHESIZER}
  - `severity` utenfor BLOKKERENDE|VIKTIG|MINDRE
  - `floor_exempt` satt til noe annet enn `"comment_doc_wording"` eller `null`
Ved disse feilklassene skrives likevel full JSON (inkl. `violations`)
til stdout FØR exit, slik at koordinatoren ser nøyaktig hvilke funn som
brøt kontrakten — men exit-koden er alltid != 0 når `violations` er ikke-tom.
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

{{TECH_REVIEW_SEVERITY_FLOORS}}
{{TECH_REVIEW_FLOOR_EXEMPTIONS}}

SYNTHESIZER = "{{PROJECT_NAME}}-code-reviewer"
VALID_AGENTS = set(SEVERITY_FLOORS.keys()) | {SYNTHESIZER}

# Rekkefølge for max(severity, floor) — kun de tre funn-severity-verdiene.
# PAUSEPUNKT og None (intet gulv) håndteres separat, IKKE via denne ordningen.
SEVERITY_ORDER = {"MINDRE": 0, "VIKTIG": 1, "BLOKKERENDE": 2}

# --- Gulvunntak -------------------------------------------------
VALID_EXEMPT_CLASSES = ("comment_doc_wording",)
REF_RE = re.compile(r"(?P<path>[^\s:]+):(?P<start>[1-9][0-9]*)(?:-(?P<end>[1-9][0-9]*))?")
REV_RE = re.compile(r"[0-9a-f]{40}")
SQL_EXTS = (".sql",)
TSJS_EXTS = (".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs")
REGULAR_MODES = ("100644", "100755")


def valid_marker(value):
    return isinstance(value, str) and value in VALID_EXEMPT_CLASSES


def exempt_eligible(agent, cls):
    return cls in FLOOR_EXEMPTIONS.get(agent, [])


def read_file_at_rev(repo, rev, path):
    """Linjene i `path` ved `rev`, eller None (ugyldig rev, ingen/flere entries,
    ikke blob, ikke regulær mode, ikke UTF-8, NUL)."""
    if not isinstance(rev, str) or not REV_RE.fullmatch(rev):
        return None
    r = subprocess.run(["git", "-C", str(repo), "--literal-pathspecs", "ls-tree", "-z", rev, "--", path],
                       capture_output=True)
    if r.returncode != 0 or not r.stdout:
        return None
    entries = [e for e in r.stdout.split(b"\0") if e]
    if len(entries) != 1:
        return None
    meta, _, epath = entries[0].partition(b"\t")
    parts = meta.split(b" ")
    if len(parts) != 3 or epath != path.encode("utf-8"):
        return None
    mode, otype, oid = (x.decode() for x in parts)
    if otype != "blob" or mode not in REGULAR_MODES:
        return None
    b = subprocess.run(["git", "-C", str(repo), "cat-file", "blob", oid], capture_output=True)
    if b.returncode != 0:
        return None
    try:
        text = b.stdout.decode("utf-8")
    except UnicodeDecodeError:
        return None
    if "\x00" in text:
        return None
    lines = text.split("\n")
    return lines[:-1] if text.endswith("\n") else lines


def is_comment_line(path, text):
    s = text.strip()
    if path.endswith(SQL_EXTS):
        return s.startswith("--")
    if path.endswith(TSJS_EXTS):
        if s.startswith("//"):
            return True
        if s.startswith("/*") or s.startswith("*"):
            return "*/" not in s or s.split("*/", 1)[1].strip() == ""
        return False
    return False


def check_ref(repo, rev, ref):
    """None = godtatt; ellers "ref_unparseable" | "ref_unresolvable" | "ref_not_comment_or_docs".
    docs/-unntaket er avgrenset til `.md`-filer under docs/ (ikke f.eks. PDF-er
    eller bilder) — «ordlyd i en .md-fil under docs/» leser vi som tekstlig
    dokumentasjon."""
    if not isinstance(ref, str):
        return "ref_unparseable"
    m = REF_RE.fullmatch(ref)
    if not m:
        return "ref_unparseable"
    path = m.group("path")
    start = int(m.group("start"))
    end = int(m.group("end") or start)
    if path.startswith("/") or any(seg in ("", ".", "..") for seg in path.split("/")) or end < start:
        return "ref_unparseable"
    lines = read_file_at_rev(repo, rev, path)
    if lines is None or end > len(lines):
        return "ref_unresolvable"
    if path.startswith("docs/") and path.endswith(".md"):
        return None
    if all(is_comment_line(path, lines[i - 1]) for i in range(start, end + 1)):
        return None
    return "ref_not_comment_or_docs"


def read_findings(path):
    """Les JSON-array fra FIL eller stdin ("-"). Feiler høyt på uleselig
    input i stedet for å stille returnere en tom liste (samme prinsipp som
    review-lens-select.py R1)."""
    if path == "-":
        raw = sys.stdin.read()
    else:
        try:
            with open(path, "r", encoding="utf-8") as f:
                raw = f.read()
        except OSError as e:
            sys.exit(f"FEIL: kan ikke lese --findings {path!r}: {e}")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        sys.exit(f"FEIL: --findings er ikke gyldig JSON: {e}")
    if not isinstance(data, list):
        sys.exit("FEIL: --findings må være en JSON-array av funn.")
    return data


def process(findings, rev=None, repo=None):
    """Håndhev severity_floor per funn. Returnerer output-dict-en. Muterer
    ALDRI input-listen — hevede funn er kopier."""
    out_findings = []
    raised = []
    pausepunkt = []
    violations = []
    exempt = []
    exempt_rejected = []

    for finding in findings:
        ref = finding.get("ref", "<uten ref>") if isinstance(finding, dict) else "<ugyldig funn>"

        if not isinstance(finding, dict):
            violations.append({"ref": ref, "issue": "funn er ikke et JSON-objekt"})
            continue

        if "source_agent" not in finding:
            violations.append({"ref": ref, "issue": "source_agent mangler"})
            continue
        agent = finding["source_agent"]
        if agent not in VALID_AGENTS:
            violations.append({"ref": ref, "issue": f"ukjent source_agent: {agent!r}"})
            continue

        severity = finding.get("severity")
        if severity not in SEVERITY_ORDER:
            violations.append({"ref": ref, "issue": f"ugyldig severity: {severity!r}"})
            continue

        # Gulvet for denne agenten. SYNTHESIZER er aldri en nøkkel i
        # SEVERITY_FLOORS (kun tech-review-agentene har gulv) — .get() gir
        # riktig "intet gulv"-oppførsel for begge tilfellene (ukjent nøkkel
        # OG en agent med eksplisitt null-gulv i config).
        floor = SEVERITY_FLOORS.get(agent)

        if "floor_exempt" in finding and finding["floor_exempt"] is not None:
            marker = finding["floor_exempt"]
            if not valid_marker(marker):
                violations.append({"ref": ref, "issue": f"ugyldig floor_exempt: {marker!r}"})
                continue
            if not exempt_eligible(agent, marker):
                reason = "agent_not_exempt_eligible"
            elif rev is None:
                reason = "no_rev"
            else:
                reason = check_ref(repo, rev, finding.get("ref"))
            if reason is None:
                exempt.append({"ref": ref, "source_agent": agent, "severity": severity, "floor": floor})
                out_findings.append(finding)
                continue
            exempt_rejected.append({"ref": ref, "source_agent": agent, "severity": severity, "reason": reason})

        if floor is None:
            # intet gulv — funnet passerer uendret.
            out_findings.append(finding)
            continue

        if floor == "PAUSEPUNKT":
            pausepunkt.append(finding)
            out_findings.append(finding)
            continue

        if floor in SEVERITY_ORDER:
            new_severity = floor if SEVERITY_ORDER[floor] > SEVERITY_ORDER[severity] else severity
            if new_severity != severity:
                raised.append({"ref": ref, "source_agent": agent, "from": severity, "to": new_severity})
                finding = {**finding, "severity": new_severity}
            out_findings.append(finding)
            continue

        # floor er verken None, "PAUSEPUNKT" eller et gyldig severity-nivå —
        # korrupt/ukjent gulv i SEVERITY_FLOORS (config-drift). Fail høyt i
        # stedet for å stille behandle det som "intet gulv".
        violations.append({"ref": ref, "issue": f"ukjent severity_floor for {agent!r}: {floor!r}"})

    return {
        "findings": out_findings,
        "raised": raised,
        "pausepunkt": pausepunkt,
        "violations": violations,
        "exempt": exempt,
        "exempt_rejected": exempt_rejected,
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--findings", required=True, help="Fil med JSON-array av funn, eller '-' for stdin.")
    ap.add_argument("--rev", help="40-tegns SHA — brukes til å slå opp ref for floor_exempt-merkede funn.")
    ap.add_argument("--repo", default=str(Path(__file__).resolve().parents[1]),
                    help="Repo-rot for --rev-oppslag (default: denne fila sin repo-rot).")
    args = ap.parse_args()

    findings = read_findings(args.findings)
    print(f"[review-severity-floor] {len(findings)} funn lest fra {args.findings!r}", file=sys.stderr)

    result = process(findings, args.rev, args.repo)
    print(
        f"[review-severity-floor] hevet: {len(result['raised'])}, "
        f"pausepunkt: {len(result['pausepunkt'])}, "
        f"kontraktbrudd: {len(result['violations'])}, "
        f"unntak: {len(result['exempt'])}, "
        f"unntak avvist: {len(result['exempt_rejected'])}",
        file=sys.stderr,
    )

    print(json.dumps(result))

    if result["violations"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
