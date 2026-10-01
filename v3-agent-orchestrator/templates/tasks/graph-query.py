#!/usr/bin/env python3
# GENERERT av /setup fra loop.config.yaml — IKKE rediger her.
# Endre loop.config.yaml og kjør /setup på nytt.
"""graph-query.py — oppslag mot kantgrafen fra graph-build.py.

Bruk:
    python3 tasks/graph-query.py --file components/AddRecipeModal.tsx
    python3 tasks/graph-query.py --todo 168
    python3 tasks/graph-query.py --file <sti> --json     # maskinlesbart {"edges": [...]}
    python3 tasks/graph-query.py --file <sti> --graph <lagret-graf.json>   # feilsoking

Bygger grafen ved a kalle graph-build.py som subprosess (ingen delt kode — kebab-case-navn er
ikke importerbare, og sti-oppløsning skjer mot grafens egne fil-noder, se resolve_file_node()).
Grafen lagres aldri av dette skriptet; --graph er kun for a kjore mot et lagret oyeblikksbilde.

Traversal-kontrakt (normativ, ikke en illustrasjon):
    --file <sti>   Lag 1 = INNKOMMENDE kanter til file:<sti>.
                   Lag 2 = ett hopp UTGAENDE fra hver returnerte todo:/bug:-node i lag 1.
    --todo <nr>    Lag 1 = UTGAENDE og INNKOMMENDE kanter pa todo:<nr>.
                   Lag 2 = ett hopp UTGAENDE fra hver returnerte bug:-node i lag 1
                   (ALDRI via deps-mal — se runbok-notatet i planen).

Mekanisme 4 (fail-soft-kontrakten i graph-build.py ma ikke bli usynlig her): byggerens stderr
videresendes alltid, returncode sjekkes FOR json.loads, og stats.missing_sources gir en
ADVARSEL pa stderr (exit forblir 0 — dette er en advarsel, ikke en feil).
"""
import argparse
import json
import os
import re
import subprocess
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def norm_id(raw):
    """Speiler graph-build.py sin norm_id() — bevisst duplisert (B2: kebab-case er ikke
    importerbart), men holdt til tre linjer nyttekode slik at avviket er billig a oppdage."""
    s = raw.strip()
    if len(s) > 1 and s[-1] == "s" and s[-2].isdigit():
        s = s[:-1]
    m = re.match(r"0*(\d+)(.*)$", s)
    if m:
        digits, suffix = m.group(1), m.group(2)
        s = (digits or "0") + suffix
    return s


def load_graph(graph_path):
    if graph_path:
        try:
            with open(graph_path, "r", encoding="utf-8") as fh:
                return json.load(fh)
        except (OSError, json.JSONDecodeError) as exc:
            sys.exit(f"FEIL: kunne ikke lese lagret graf {graph_path}: {exc}")

    builder = os.path.join(SCRIPT_DIR, "graph-build.py")
    r = subprocess.run(["python3", builder], capture_output=True, text=True)
    # Mekanisme 4: byggerens diagnostikk skal ALDRI forsvinne stille bak --json-fangsten.
    if r.stderr:
        sys.stderr.write(r.stderr)
    if r.returncode != 0:
        sys.exit(r.returncode)
    try:
        graph = json.loads(r.stdout)
    except json.JSONDecodeError as exc:
        sys.exit(f"FEIL: graph-build.py ga ugyldig JSON: {exc}")
    missing = graph.get("stats", {}).get("missing_sources") or []
    if missing:
        sys.stderr.write(
            f"ADVARSEL: {len(missing)} kilder manglet — grafen er ufullstendig: "
            + ", ".join(missing)
            + "\n"
        )
    return graph


def resolve_file_node(graph, arg):
    """3.6 — sti-oppløsning mot grafens EGNE fil-noder, ingen delt kode med byggeren."""
    file_nodes = graph.get("nodes", {}).get("file", [])
    direct = f"file:{arg}"
    if direct in file_nodes:
        return direct
    suffix = "/" + arg
    candidates = [n for n in file_nodes if n.endswith(suffix)]
    if len(candidates) == 1:
        return candidates[0]
    if len(candidates) > 1:
        sys.stderr.write(f"FEIL: tvetydig filsti '{arg}' — flere kandidater:\n")
        for c in sorted(candidates):
            sys.stderr.write(f"  {c}\n")
        sys.exit(1)
    sys.stderr.write(
        f"FEIL: ingen fil-node matcher '{arg}' — ukjent sti, eller fila har ingen kanter i grafen\n"
    )
    sys.exit(1)


def edge_sort_key(e):
    return (e["source"], e["type"], e["target"])


def query_file_mode(graph, file_node):
    edges = graph["edges"]
    layer1 = sorted(
        (e for e in edges if e["target"] == file_node), key=edge_sort_key
    )
    seed_nodes = set(
        e["source"] for e in layer1 if e["source"].startswith("todo:") or e["source"].startswith("bug:")
    )
    layer2 = sorted(
        (e for e in edges if e["source"] in seed_nodes), key=edge_sort_key
    )
    return layer1, layer2


def query_todo_mode(graph, todo_node):
    edges = graph["edges"]
    layer1_out = [e for e in edges if e["source"] == todo_node]
    layer1_in = [e for e in edges if e["target"] == todo_node]
    layer1 = sorted(layer1_out + layer1_in, key=edge_sort_key)
    seed_bugs = set(e["source"] for e in layer1_in if e["source"].startswith("bug:"))
    seed_bugs |= set(e["target"] for e in layer1_out if e["target"].startswith("bug:"))
    # ALDRI via deps-mal (2.8): kun bug:-noder ekspanderes i lag 2.
    layer2 = sorted((e for e in edges if e["source"] in seed_bugs), key=edge_sort_key)
    return layer1, layer2


def suggested_lesson_themes(layer1, layer2):
    themes = set()
    for e in layer1 + layer2:
        for endpoint in (e["source"], e["target"]):
            if endpoint.startswith("lesson:"):
                theme = endpoint[len("lesson:"):].split("#", 1)[0]
                themes.add(theme)
            elif endpoint.startswith("theme:"):
                themes.add(endpoint[len("theme:"):])
    return sorted(themes)


def print_human(header, layer1, layer2):
    print(f"=== INNKOMMENDE (1 hopp) til {header} ===")
    if not layer1:
        print("    (ingen treff)")
    for e in layer1:
        print(f"    {e['source']} - {e['type']} -> {e['target']}")
    print()
    print("=== +1 HOPP fra returnerte todo:/bug:-noder ===")
    if not layer2:
        print("    (ingen treff)")
    for e in layer2:
        print(f"    {e['source']} - {e['type']} -> {e['target']}")
    print()
    themes = suggested_lesson_themes(layer1, layer2)
    if themes:
        print(f"Foreslåtte lessons-tema: {', '.join(themes)}")


def print_json(layer1, layer2):
    seen = set()
    combined = []
    for e in layer1 + layer2:
        key = (e["source"], e["type"], e["target"])
        if key not in seen:
            seen.add(key)
            combined.append(e)
    combined.sort(key=edge_sort_key)
    print(json.dumps({"edges": combined}, ensure_ascii=False, sort_keys=True, indent=1))


def main():
    ap = argparse.ArgumentParser(
        description="Oppslag mot kantgrafen (todo/bug/PR/fil/lesson). Se docstring for kontrakten."
    )
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--file", help="Repo-relativ sti eller basenavn — resolveres mot grafens fil-noder.")
    mode.add_argument("--todo", help="TODO-nr (normaliseres — genitiv-'s' og ledende nuller strippes).")
    ap.add_argument("--json", action="store_true", help="Skriv {\"edges\": [...]} i stedet for lesbar tekst.")
    ap.add_argument("--graph", help="Kjor mot et lagret graf-JSON i stedet for a bygge on-demand (feilsoking).")
    args = ap.parse_args()

    graph = load_graph(args.graph)

    if args.file:
        file_node = resolve_file_node(graph, args.file)
        layer1, layer2 = query_file_mode(graph, file_node)
        header = file_node
    else:
        todo_node = f"todo:{norm_id(args.todo)}"
        layer1, layer2 = query_todo_mode(graph, todo_node)
        header = todo_node

    if args.json:
        print_json(layer1, layer2)
    else:
        print_human(header, layer1, layer2)


if __name__ == "__main__":
    main()
