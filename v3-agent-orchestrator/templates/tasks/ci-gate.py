#!/usr/bin/env python3
# GENERERT av /setup fra loop.config.yaml — IKKE rediger her.
# Endre loop.config.yaml og kjør /setup på nytt.
"""ci-gate.py — CI-gaten før merge (coordinator-runbook §6 steg 0, TODO 216).

  python3 tasks/ci-gate.py <pr-nummer> [--timeout-s N]
  python3 tasks/ci-gate.py --self-test

Pinner PR-ens head-SHA (REST) og poller workflow-kjøringer, check-runs og
commit-statuser for NETTOPP den SHA-en til dommen er endelig eller taket nås.
stdout linje 1: ci=<green|red|cancelled|pending|missing|error> (run-log-tokenet,
kopieres ordrett), linje 2: sha=<head-sha>, deretter én linje per sjekk som ikke er
grønn. Exit 0 KUN ved ci=green; 1 = ikke grønn; 2 = bruks-/API-feil (ci=error).
Merge med `-f sha=<sha>` fra linje 2, så dommen ikke kan gli til en nyere commit.
Standardtaket 540 s holder hele kallet under Bash-verktøyets tak på 600 s.
Forutsetter minst én GitHub Actions-workflow på PR-er (ellers alltid ci=missing).
"""
import argparse, json, subprocess, sys, time

OK = {"success", "neutral", "skipped"}
REPO = "repos/{owner}/{repo}/"  # gh fyller inn owner/repo fra git-remoten
POLL_S = 20


def gh(path):
    r = subprocess.run(["gh", "api", path], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"gh api {path}: {r.stderr.strip()[:200]}")
    return json.loads(r.stdout)


def classify(runs, checks, statuses):
    """runs = workflow_runs, checks = check_runs, statuses = combined-status.statuses
    for ÉN SHA. Returnerer (dom, [(navn, status, konklusjon, url)] som ikke er grønne)."""
    newest = {}
    for r in runs:  # nyeste kjøring per workflow-fil — en overkjørt kjøring teller ikke
        if r["path"] not in newest or r["id"] > newest[r["path"]]["id"]:
            newest[r["path"]] = r
    items = [("workflow " + r["name"], r["status"], r["conclusion"], r.get("html_url")) for r in newest.values()]
    items += [(c["name"], c["status"], c["conclusion"], c.get("html_url")) for c in checks]
    for s in statuses:  # commit-status: pending | success | failure | error
        done = s["state"] != "pending"
        items.append(("status " + s["context"], "completed" if done else "pending",
                      s["state"] if done else None, s.get("target_url")))
    done = [i for i in items if i[1] == "completed"]
    red = [i for i in done if i[2] not in OK and i[2] != "cancelled"]
    if red:
        return "red", red
    cancelled = [i for i in done if i[2] == "cancelled"]
    if cancelled:
        return "cancelled", cancelled
    if not newest:  # ingen workflow-kjøring for SHA-en ennå: aldri tomt-grønt
        return "missing", []
    pending = [i for i in items if i[1] != "completed"]
    if pending:
        return "pending", pending
    return "green", []


def gate(pr, timeout_s):
    sha = gh(REPO + "pulls/" + pr)["head"]["sha"]  # feiler hardt: uten head-SHA finnes ingen dom
    deadline = time.time() + timeout_s
    fails = 0
    while True:
        try:
            runs = gh(REPO + "actions/runs?per_page=100&head_sha=" + sha)["workflow_runs"]
            checks = gh(REPO + "commits/" + sha + "/check-runs?per_page=100")["check_runs"]
            statuses = gh(REPO + "commits/" + sha + "/status")["statuses"]
        except RuntimeError:
            fails += 1
            # ponytail: tåler 2 gh-feil på rad og bare før taket, uten backoff; lengre GitHub-utfall ⇒ ci=error
            if fails > 2 or time.time() >= deadline:
                raise
            time.sleep(POLL_S)
            continue
        fails = 0
        verdict, bad = classify(runs, checks, statuses)
        if verdict not in ("pending", "missing") or time.time() >= deadline:
            return verdict, sha, bad
        time.sleep(POLL_S)


def R(path, rid, status, conclusion):
    return {"path": path, "id": rid, "name": "CI", "status": status, "conclusion": conclusion}


def C(name, status, conclusion):
    return {"name": name, "status": status, "conclusion": conclusion}


def S(context, state):
    return {"context": context, "state": state}


def P(status, conclusion):  # ett poll-svar (runs, checks, statuses) med én workflow-kjøring
    return [{"workflow_runs": [R(CI, 1, status, conclusion)]}, {"check_runs": []}, {"statuses": []}]


CI, Q, D, V = ".github/workflows/ci.yml", "Typecheck", "Deno", "Vercel"
FIXTURES = [
    ("all-green", [R(CI, 1, "completed", "success")], [C(Q, "completed", "success"), C(D, "completed", "success")], [S(V, "success")], "green"),
    ("check-failure", [R(CI, 1, "completed", "failure")], [C(Q, "completed", "failure"), C(D, "completed", "success")], [S(V, "success")], "red"),
    ("run-failure-no-checks-yet", [R(CI, 1, "completed", "failure")], [], [], "red"),
    ("vercel-only-no-workflow", [], [C("Vercel Preview Comments", "completed", "success")], [S(V, "success")], "missing"),
    ("empty", [], [], [], "missing"),
    ("cancelled", [R(CI, 1, "completed", "cancelled")], [C(Q, "completed", "cancelled")], [S(V, "success")], "cancelled"),
    ("red-beats-cancelled", [R(CI, 1, "completed", "failure")], [C(Q, "completed", "failure"), C(D, "completed", "cancelled")], [], "red"),
    ("run-in-progress", [R(CI, 1, "in_progress", None)], [C(Q, "in_progress", None)], [S(V, "success")], "pending"),
    ("status-pending", [R(CI, 1, "completed", "success")], [C(Q, "completed", "success")], [S(V, "pending")], "pending"),
    ("status-error", [R(CI, 1, "completed", "success")], [C(Q, "completed", "success")], [S(V, "error")], "red"),
    ("neutral-skipped", [R(CI, 1, "completed", "success")], [C(Q, "completed", "neutral"), C(D, "completed", "skipped")], [], "green"),
    ("superseded-run", [R(CI, 2, "completed", "success"), R(CI, 1, "completed", "cancelled")], [C(Q, "completed", "success")], [], "green"),
    ("completed-without-conclusion", [R(CI, 1, "completed", "success")], [C(Q, "completed", None)], [], "red"),
    ("timed-out", [R(CI, 1, "completed", "timed_out")], [C(Q, "completed", "timed_out")], [], "red"),
]
HEAD, ERR = {"head": {"sha": "f00"}}, RuntimeError("gh api: HTTP 502")
GATE_FIXTURES = [  # gate() mot falsk gh og POLL_S=0: (navn, timeout_s, svar i kallrekkefølge, forventet)
    ("gate-pending-2errors-green", 60, [HEAD, *P("in_progress", None), ERR, ERR, *P("completed", "success")], "green"),
    ("gate-error-after-deadline", 0, [HEAD, ERR], "RuntimeError"),
]


def fake_gh(answers):
    def f(path):  # svarer i kallrekkefølge; et Exception-svar kastes
        a = answers.pop(0)
        if isinstance(a, Exception):
            raise a
        return a
    return f


def self_test():
    global gh, POLL_S
    got = [(name, classify(runs, checks, statuses)[0], want) for name, runs, checks, statuses, want in FIXTURES]
    POLL_S = 0
    for name, timeout_s, answers, want in GATE_FIXTURES:
        gh = fake_gh(list(answers))
        try:
            verdict = gate("1", timeout_s)[0]
        except Exception as e:  # unntaket ER dommen her, så en mutant gir en FAIL-linje, ikke et krasj
            verdict = type(e).__name__
        got.append((name, verdict, want))
    fails = 0
    for name, verdict, want in got:
        ok = verdict == want
        fails += not ok
        print(f"{'PASS' if ok else 'FAIL'} {name}: forventet {want}, fikk {verdict}")
    print(f"ci-gate --self-test: {len(got) - fails}/{len(got)}")
    return 0 if fails == 0 else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pr", nargs="?")
    # ponytail: fast tak 540 s < Bash-verktøyets 600 s; 95 av 100 CI-kjøringer tok ≤ 218 s. Tregere CI ⇒ ci=pending
    ap.add_argument("--timeout-s", type=int, default=540)
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        return self_test()
    if not (a.pr or "").isdigit():
        print("ci=error\nbruk: ci-gate.py <pr-nummer> [--timeout-s N] | --self-test")
        return 2
    try:
        verdict, sha, bad = gate(a.pr, a.timeout_s)
    except Exception as e:  # et krasj skal aldri se ut som exit 1 (= ikke grønn)
        print(f"ci=error\n{type(e).__name__}: {e}")
        return 2
    print(f"ci={verdict}\nsha={sha}")
    for name, status, conclusion, url in bad:
        print(f"  {name}: {status}/{conclusion} {url or ''}")
    return 0 if verdict == "green" else 1


if __name__ == "__main__":
    sys.exit(main())
