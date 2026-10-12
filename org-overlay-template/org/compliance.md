# Slik oppfyller loopen organisasjonens agentstandard

Organisasjonens standard (`org/AGENTS.org.md`) står øverst i prosjektets `AGENTS.md` og går foran
alt annet. Kitets mekanismer for styring er beskrevet i `docs/loop/governance.md`. Denne fila er
organisasjonens del: hvordan standarden er tolket, hvilke kitmekanismer som oppfyller hvilket
punkt, og hva som må avklares. Den eies av organisasjonen, ikke av kitet.

> Paragrafhenvisningene under følger utkastet «Agents.md» (DEVOPS). Oppdater dem når standarden
> vedtas.

## 1. Tolkningen av menneske-i-loopen (standarden §4)

Standarden krever menneskelig godkjenning for alle skriveoperasjoner (commit, push, PR, branch,
filendringer, endrende CLI-kommandoer). Loopen oppfyller dette slik:

- Agentene skriver bare i egne git-worktrees på egne branches. Det kan forkastes uten spor i felles
  kode.
- Eieren godkjenner **planen** før koding (standarden §4.2 fase A → B) og **mergen** før noe når
  felles kode eller delt state committes (`governance.human_approval: plan_and_merge`).
- Spørsmålene er faste, og bare et klart «Ja», «Godkjent» eller «Kjør» er godkjenning.

**Må bekreftes av organisasjonen:** at skriving i en isolert worktree og branch, push av den branchen
og en PR som venter på godkjenning, er innenfor §4.1. Godtas ikke det, kan loopen ikke kjøres
autonomt. Da skal VS Code stå i «Request approval», og hver handling godkjennes.

## 2. Standarden punkt for punkt

| Standarden | Loopen | Kitmekanisme |
|---|---|---|
| §0 Gyldighet og prioritet | Standarden står øverst i `AGENTS.md` og går foran kitets regler | `governance.instructions_file` |
| §0 Foretrekk read-only | Reviewer, code-reviewer og scout har ikke `edit` | Agentenes `tools`, `scripts/readonly-check.sh` |
| §1 Hemmeligheter, eksfiltrering, omgå tilgang/logging | Faste regler; endringer i vakter er nivå A | `docs/loop/governance.md` §4 |
| §1 Produksjon | Aldri prod-branch eller prod-miljø | `guard-main-merge.sh`, `environments.prod_id` |
| §1 og §3 Bare registrerte MCP-servere | `/run-loop` stopper ved ukjent server | `governance.approved_mcp_servers` |
| §2 Dataklassifisering og -minimering | Klassen vises for agentene; strengere data er pausepunkt | `governance.data_classification`, governance.md §4 og §7 |
| §4.1 og §4.2 Menneske-i-loopen, to faser | Godkjenning av plan og merge | `governance.human_approval: plan_and_merge` |
| §4.3 Høy risiko (IaC, IAM/RBAC, hemmeligheter) | Avvises: hook, plan- og PR-sjekk | `governance.blocked_commands`, `governance.blocked_paths` |
| Auto-godkjenning i agentverktøy | Kitet slår det aldri på; `--auto-approve` blokkeres | `blocked_commands: default` |

## 3. Må avklares med organisasjonen

Skriv svarene inn her når de foreligger:

1. Godtas tolkningen i §1 (godkjenning av plan og merge; agenter skriver fritt bare i isolerte
   worktrees og branches)?
2. Hvor er sikkerhetsretningslinjene og den offentlige lista over godkjente MCP-servere? (Fyll
   `approved_mcp_servers` i `org/loop.config.governance.yaml` fra den.)
3. Hvor er prosjektets dataklassifisering bekreftet?
4. Hvilken rutine gjelder når en bruker ber om noe som bryter §1 (hvem varsles, hvordan)?
5. Skal høy risiko alltid avvises (slik loopen gjør), eller godkjennes i to trinn?
