#!/usr/bin/env python3
"""Org-modus: mekaniske kontroller for organisasjonens agentregler (docs/loop/compliance.md).

  python3 tasks/compliance-check.py mcp [--file .mcp.json ...]
      Alle MCP-servere i prosjektets MCP-konfigurasjon må stå i compliance.approved_mcp_servers.
      exit 0 = alle godkjent, 1 = ikke-godkjent server funnet, 2 = kan ikke leses.
  python3 tasks/compliance-check.py paths (--pr <nr> | --plan-report <fil.json> | -)
      Ingen fil i PR-en / plan-rapportens files_touched / stdin (én sti per linje) kan treffe
      compliance.high_risk_paths. exit 0 = ingen treff, 1 = treff (avvist), 2 = kan ikke måles.
  python3 tasks/compliance-check.py hook
      preToolUse-hook (registrert i .github/hooks/loop-guards.json). Leser Copilot-payloaden på
      stdin og avviser (permissionDecision: deny) høyrisiko-kommandoer og redigering av
      høyrisiko-stier. Alt annet slipper gjennom uten utdata.
  python3 tasks/compliance-check.py --self-test

Verdiene under kompileres inn av /setup fra loop.config.yaml (compliance.*). Endre config og kjør
/setup på nytt — ikke rediger her.
"""
import fnmatch
import json
import os
import re
import subprocess
import sys

APPROVED_MCP_SERVERS = {{APPROVED_MCP_SERVERS}}
HIGH_RISK_PATHS = {{HIGH_RISK_PATHS}}

# Kommandoer som endrer infrastruktur, tilgang eller hemmeligheter. Org-standarden §4.3: høyrisiko
# avvises i org-modus, uansett hvem som ber om det. Mønstrene matcher hvert ledd i en sammensatt
# kommando (skilt med ; && || | og linjeskift).
HIGH_RISK_COMMANDS = [
    (r'\bkubectl\s+(?:\S+\s+)*?(apply|create|delete|patch|replace|scale|edit|set|annotate|label|rollout|drain|cordon|taint)\b',
     'kubectl som endrer klyngen'),
    (r'\bhelm\s+(?:\S+\s+)*?(install|upgrade|uninstall|delete|rollback)\b', 'helm som endrer klyngen'),
    (r'\b(terraform|tofu)\s+(?:\S+\s+)*?(apply|destroy|import|taint|untaint)\b', 'terraform/tofu som endrer infrastruktur'),
    (r'\b(terraform|tofu)\s+(?:\S+\s+)*?state\s+(rm|mv|push|replace-provider)\b', 'endring av terraform-state'),
    (r'\bpulumi\s+(?:\S+\s+)*?(up|destroy|import|refresh)\b', 'pulumi som endrer infrastruktur'),
    (r'\baz\s+(role|ad)\b', 'Azure IAM/RBAC'),
    (r'\baz\s+keyvault\s+(secret|key|certificate)\s+(set|delete|purge|import)\b', 'Azure Key Vault-hemmeligheter'),
    (r'\baws\s+(iam|secretsmanager|kms)\b', 'AWS IAM/hemmeligheter'),
    (r'\bgcloud\s+(?:\S+\s+)*?(iam|add-iam-policy-binding|remove-iam-policy-binding|secrets)\b', 'GCP IAM/hemmeligheter'),
    (r'\bgh\s+(secret|variable)\s+(set|delete|remove)\b', 'GitHub-hemmeligheter/variabler'),
    (r'\bgh\s+api\s+(?:\S+\s+)*?[\'"]?/?repos/[^\s]+/(collaborators|keys|actions/secrets|environments)', 'GitHub-tilgang/hemmeligheter via API'),
    (r'(^|\s)--auto-approve\b', 'automatisk godkjenning (--auto-approve)'),
]
SHELL_TOOLS = {'bash', 'run_in_terminal', 'powershell', 'shell'}
EDIT_TOOLS = {'edit', 'create', 'apply_patch', 'str_replace_editor', 'create_file',
              'replace_string_in_file', 'insert_edit_into_file', 'multi_replace_string_in_file'}


def repo_rel(path, cwd=None):
    """Sti relativt til repo-roten. Stier inne i .loop-worktrees/<navn>/ kuttes til treets egen rot,
    så en worker som redigerer infra/x.tf i sitt eget tre treffer samme regel som i hovedsjekkouten."""
    p = path.replace('\\', '/')
    if cwd and not p.startswith('/'):
        p = os.path.join(cwd, p).replace('\\', '/')
    m = re.search(r'/\.loop-worktrees/[^/]+/(.*)$', p)
    if m:
        return m.group(1)
    if p.startswith('/'):
        try:
            root = subprocess.run(['git', '-C', os.path.dirname(p) or '/', 'rev-parse', '--show-toplevel'],
                                  capture_output=True, text=True, timeout=5).stdout.strip()
        except Exception:
            root = ''
        if root and p.startswith(root + '/'):
            return p[len(root) + 1:]
        return p.lstrip('/')
    return re.sub(r'^\./', '', p)


def glob_match(rel, pattern):
    # fnmatch: `*` krysser `/`. `**/x` skal også treffe `x` i roten.
    if fnmatch.fnmatch(rel, pattern):
        return True
    return pattern.startswith('**/') and fnmatch.fnmatch(rel, pattern[3:])


def high_risk_path(rel, patterns=None):
    return [g for g in (HIGH_RISK_PATHS if patterns is None else patterns) if glob_match(rel, g)]


def high_risk_command(cmd):
    hits = []
    for seg in re.split(r'\|\||&&|;|\||\n', cmd):
        for rx, why in HIGH_RISK_COMMANDS:
            if re.search(rx, seg.strip()):
                hits.append(why)
    return sorted(set(hits))


def tool_args(payload):
    a = payload.get('toolArgs', payload.get('tool_input'))
    if isinstance(a, str):
        try:
            a = json.loads(a)
        except ValueError:
            return {'_raw': a}
    return a if isinstance(a, dict) else {}


def edit_paths(name, args):
    paths = [args.get(k) for k in ('path', 'file_path', 'filePath') if isinstance(args.get(k), str)]
    if name == 'apply_patch':
        patch = args.get('input') or args.get('patch') or args.get('_raw') or ''
        paths += re.findall(r'^\*\*\* (?:Add|Update|Delete) File: (.+)$', patch, re.M)
    return paths


def hook_decision(payload):
    """→ None (slipp gjennom) eller begrunnelse for deny."""
    name = payload.get('toolName') or payload.get('tool_name') or ''
    args = tool_args(payload)
    cwd = payload.get('cwd')
    if name in SHELL_TOOLS or name == 'Bash':
        cmd = args.get('command') or args.get('_raw') or ''
        hits = high_risk_command(cmd if isinstance(cmd, str) else '')
        if hits:
            return ('Org-modus: høyrisiko-kommando avvist (' + ', '.join(hits) + '). Endringer i '
                    'infrastruktur, IAM/RBAC og hemmeligheter gjøres ikke av agenter — '
                    'se docs/loop/compliance.md.')
    elif name in EDIT_TOOLS or name in ('Edit', 'Write', 'MultiEdit'):
        for p in edit_paths(name, args):
            rel = repo_rel(p, cwd)
            g = high_risk_path(rel)
            if g:
                return (f'Org-modus: {rel} er en høyrisiko-sti ({", ".join(g)}) og kan ikke endres av '
                        'agenter — se docs/loop/compliance.md.')
    return None


def cmd_hook():
    raw = sys.stdin.read()
    try:
        payload = json.loads(raw) if raw.strip() else {}
    except ValueError:
        payload = {}
    why = hook_decision(payload if isinstance(payload, dict) else {})
    if why:
        print(json.dumps({'permissionDecision': 'deny', 'permissionDecisionReason': why}, ensure_ascii=False))
        print(why, file=sys.stderr)
    return 0


def mcp_servers(files):
    found, unreadable = {}, []
    for f in files:
        if not os.path.exists(f):
            continue
        try:
            doc = json.load(open(f, encoding='utf-8'))
        except (OSError, ValueError) as e:
            unreadable.append(f'{f}: {e}')
            continue
        servers = doc.get('mcpServers') or doc.get('servers') or {}
        for name in servers if isinstance(servers, dict) else []:
            found.setdefault(name, []).append(f)
    return found, unreadable


def cmd_mcp(argv):
    files = [argv[i + 1] for i, a in enumerate(argv) if a == '--file' and i + 1 < len(argv)] \
        or ['.mcp.json', '.vscode/mcp.json']
    found, unreadable = mcp_servers(files)
    if unreadable:
        print('IKKE MÅLT: ' + '; '.join(unreadable))
        return 2
    bad = {n: f for n, f in found.items() if n not in APPROVED_MCP_SERVERS}
    if bad:
        for n, f in sorted(bad.items()):
            print(f'IKKE GODKJENT: MCP-server «{n}» ({", ".join(f)}) står ikke i compliance.approved_mcp_servers')
        return 1
    print(f'OK: {len(found)} MCP-server(e), alle godkjent' if found else 'OK: ingen MCP-servere konfigurert')
    return 0


def cmd_paths(argv):
    if '--pr' in argv:
        nr = argv[argv.index('--pr') + 1]
        r = subprocess.run(['gh', 'pr', 'diff', nr, '--name-only'], capture_output=True, text=True)
        if r.returncode != 0:
            print(f'IKKE MÅLT: gh pr diff {nr} feilet: {r.stderr.strip()}')
            return 2
        files = r.stdout.split()
    elif '--plan-report' in argv:
        try:
            rep = json.load(open(argv[argv.index('--plan-report') + 1], encoding='utf-8'))
        except (OSError, ValueError, IndexError) as e:
            print(f'IKKE MÅLT: {e}')
            return 2
        files = rep.get('files_touched')
        if not isinstance(files, list):
            print('IKKE MÅLT: plan-rapporten mangler files_touched')
            return 2
    elif '-' in argv:
        files = [l.strip() for l in sys.stdin if l.strip()]
    else:
        print(__doc__)
        return 2
    hits = [(f, high_risk_path(repo_rel(f))) for f in files]
    hits = [(f, g) for f, g in hits if g]
    if hits:
        for f, g in hits:
            print(f'AVVIST: {f} treffer høyrisiko-sti {", ".join(g)}')
        return 1
    print(f'OK: {len(files)} fil(er), ingen høyrisiko-stier')
    return 0


def self_test():
    global APPROVED_MCP_SERVERS, HIGH_RISK_PATHS
    APPROVED_MCP_SERVERS, HIGH_RISK_PATHS = ['github'], ['infra/**', '**/*.tf', '.github/workflows/**']
    cases = [
        ('kubectl apply', {'toolName': 'bash', 'toolArgs': json.dumps({'command': 'kubectl apply -f x.yaml'})}, True),
        ('kubectl get', {'toolName': 'bash', 'toolArgs': {'command': 'kubectl get pods -n x'}}, False),
        ('kubectl -n ns delete', {'toolName': 'bash', 'toolArgs': {'command': 'kubectl -n prod delete pod a'}}, True),
        ('helm upgrade i kjede', {'toolName': 'bash', 'toolArgs': {'command': 'cd x && helm upgrade r c'}}, True),
        ('helm template', {'toolName': 'bash', 'toolArgs': {'command': 'helm template r c'}}, False),
        ('terraform plan', {'toolName': 'bash', 'toolArgs': {'command': 'terraform plan'}}, False),
        ('terraform apply', {'toolName': 'bash', 'toolArgs': {'command': 'terraform -chdir=infra apply'}}, True),
        ('--auto-approve', {'toolName': 'bash', 'toolArgs': {'command': 'tool deploy --auto-approve'}}, True),
        ('az role', {'toolName': 'run_in_terminal', 'toolArgs': {'command': 'az role assignment create'}}, True),
        ('gh secret set', {'toolName': 'bash', 'toolArgs': {'command': 'gh secret set TOKEN'}}, True),
        ('gh pr create', {'toolName': 'bash', 'toolArgs': {'command': 'gh pr create --base dev'}}, False),
        ('git commit', {'toolName': 'bash', 'toolArgs': {'command': 'git commit -m x'}}, False),
        ('edit infra', {'toolName': 'edit', 'toolArgs': {'path': 'infra/main.bicep'}}, True),
        ('edit .tf i rot', {'toolName': 'create', 'toolArgs': {'path': 'main.tf'}}, True),
        ('edit workflow i worktree', {'toolName': 'edit', 'cwd': '/r',
                                      'toolArgs': {'path': '/r/.loop-worktrees/implementer-7/.github/workflows/ci.yml'}}, True),
        ('edit app', {'toolName': 'edit', 'toolArgs': {'path': 'src/app.ts'}}, False),
        ('apply_patch infra', {'toolName': 'apply_patch', 'toolArgs': {'input': '*** Begin Patch\n*** Update File: infra/a.tf\n'}}, True),
        ('view infra (lesing)', {'toolName': 'view', 'toolArgs': {'path': 'infra/main.tf'}}, False),
        ('snake_case-payload', {'tool_name': 'Bash', 'tool_input': {'command': 'helm install a b'}}, True),
        ('ugyldig toolArgs', {'toolName': 'bash', 'toolArgs': '{ikke json'}, False),
    ]
    fails = 0
    for name, payload, want in cases:
        got = hook_decision(payload) is not None
        if got != want:
            fails += 1
            print(f'FEIL {name}: forventet {"deny" if want else "allow"}')
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        ok = os.path.join(d, 'ok.json'); json.dump({'mcpServers': {'github': {}}}, open(ok, 'w'))
        bad = os.path.join(d, 'bad.json'); json.dump({'servers': {'github': {}, 'random': {}}}, open(bad, 'w'))
        broken = os.path.join(d, 'broken.json'); open(broken, 'w').write('{')
        for name, argv, want in [('mcp godkjent', ['--file', ok], 0), ('mcp ukjent server', ['--file', bad], 1),
                                 ('mcp ugyldig json', ['--file', broken], 2),
                                 ('mcp ingen fil', ['--file', os.path.join(d, 'mangler.json')], 0)]:
            sys.stdout, saved = open(os.devnull, 'w'), sys.stdout
            try:
                got = cmd_mcp(argv)
            finally:
                sys.stdout = saved
            if got != want:
                fails += 1
                print(f'FEIL {name}: exit {got}, forventet {want}')
        rep = os.path.join(d, 'plan.json'); json.dump({'files_touched': ['src/a.ts', 'infra/k8s.yaml']}, open(rep, 'w'))
        sys.stdout, saved = open(os.devnull, 'w'), sys.stdout
        try:
            got = cmd_paths(['--plan-report', rep])
        finally:
            sys.stdout = saved
        if got != 1:
            fails += 1
            print(f'FEIL plan-rapport med infra/: exit {got}, forventet 1')
    total = len(cases) + 5
    print(f'compliance-check --self-test: {total - fails}/{total}')
    return 1 if fails else 0


def main(argv):
    if '--self-test' in argv:
        return self_test()
    if not argv:
        print(__doc__)
        return 2
    sub, rest = argv[0], argv[1:]
    if sub == 'hook':
        return cmd_hook()
    if sub == 'mcp':
        return cmd_mcp(rest)
    if sub == 'paths':
        return cmd_paths(rest)
    print(__doc__)
    return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
