#!/usr/bin/env bash
# Setter organisasjonens governance-blokk (org/loop.config.governance.yaml) inn i prosjektets
# loop.config.yaml. Erstatter en eksisterende governance-blokk; resten av fila røres ikke.
#
#   bash scripts/apply-org-config.sh [sti/til/loop.config.yaml]
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
CFG="${1:-v3-copilot-agent-orchestrator/loop.config.yaml}"
ORG=org/loop.config.governance.yaml
[ -f "$CFG" ] || { echo "FEIL: $CFG finnes ikke (kopier loop.config.example.yaml dit først)"; exit 1; }
python3 - "$CFG" "$ORG" <<'PY'
import re, sys
cfg, org = sys.argv[1], sys.argv[2]
text = open(cfg, encoding="utf-8").read()
block = "".join(l for l in open(org, encoding="utf-8") if not l.startswith("#")).strip("\n") + "\n"
# Fjern eksisterende governance-blokk (fra «governance:» til neste toppnivånøkkel eller kommentarseksjon).
pat = re.compile(r"^governance:\n(?:(?:[ \t].*)?\n)*", re.M)
if pat.search(text):
    text = pat.sub(lambda m: block, text, count=1)
else:
    text = text.rstrip("\n") + "\n\n# --- Styring (fra org/loop.config.governance.yaml) ---\n" + block
open(cfg, "w", encoding="utf-8").write(text)
print(f"OK: governance-blokken i {cfg} er satt fra {org}")
PY
