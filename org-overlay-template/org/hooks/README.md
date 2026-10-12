# Organisasjonens egne hooks

Copilot laster alle `.github/hooks/*.json`. Kitet eier bare `.github/hooks/loop-guards.json`; legg
organisasjonens hooks i egne filer, f.eks. `.github/hooks/org-guards.json`, med skriptene ved siden
av. `/setup` rører dem aldri.

Format (versjon 1), se også `v3-copilot-agent-orchestrator/examples/hooks/`:

```json
{ "version": 1,
  "hooks": { "preToolUse": [ { "type": "command", "bash": "bash org/hooks/<skript>.sh", "cwd": ".", "timeoutSec": 30 } ] } }
```

Et `preToolUse`-skript blokkerer ved å skrive
`{"permissionDecision":"deny","permissionDecisionReason":"…"}` på stdout.
