# org-overlay-template — et org-lag oppå agent-kitet

Mal for å ta `v3-copilot-agent-orchestrator/` i bruk i en organisasjon med egne krav, **uten å endre
kitet**. Kitet er organisasjonsnøytralt og oppdateres i kit-repoet. Alt som er spesifikt for
organisasjonen, ligger i et tynt lag ved siden av og bruker kitets utvidelsespunkter.

```
<org-repo>/
├── v3-copilot-agent-orchestrator/     ← kitet, kopiert uendret (byttes ut ved oppgradering)
│   └── loop.config.yaml               ← prosjektets config (det eneste som bevares ved oppgradering)
├── org/
│   ├── AGENTS.org.md                  ← organisasjonens agentstandard, uendret
│   ├── loop.config.governance.yaml    ← organisasjonens styringsverdier
│   ├── compliance.md                  ← tolkningen av standarden, punkt for punkt, og det som må avklares
│   ├── KIT-VERSION                    ← hvilken kit-commit kopien er
│   ├── agents/                        ← organisasjonens egne tech-review-agenter
│   └── hooks/                         ← organisasjonens egne hooks
├── scripts/
│   ├── upgrade-kit.sh                 ← bytter ut kit-mappa med en ny versjon
│   ├── check-kit-upgrade.sh           ← finnes det en nyere kitversjon?
│   └── apply-org-config.sh            ← setter org-verdiene inn i loop.config.yaml
└── .github/workflows/kit-upgrade.yml  ← ukentlig sjekk; issue til eieren ved ny kitversjon
```

## Regelen som gjør oppgradering enkel

**Rediger aldri filer i `v3-copilot-agent-orchestrator/`** (bortsett fra `loop.config.yaml`). Alt
organisasjonen trenger, legges inn via kitets utvidelsespunkter:

| Behov | Utvidelsespunkt |
|---|---|
| Organisasjonens agentstandard | `governance.instructions_file: org/AGENTS.org.md` (settes inn øverst i `AGENTS.md`) |
| Godkjenning av plan og merge | `governance.human_approval: plan_and_merge` |
| Blokkerte kommandoer og stier | `governance.blocked_commands`, `governance.blocked_paths` |
| Godkjente MCP-servere | `governance.approved_mcp_servers` |
| Dataklassifisering | `governance.data_classification` |
| Egne review-agenter | `.github/agents/<navn>.agent.md` + `tech_review_agents` i config |
| Egne vakter | Egne filer i `.github/hooks/` (kitet eier bare `loop-guards.json`) |
| Prosjektets egne regler | `AGENTS.md` under instruksfila (prosjekt-eid) |

Trenger organisasjonen noe kitet ikke har et utvidelsespunkt for, foreslå det som en endring i
kit-repoet i stedet for å redigere kopien.

## Første oppsett

1. Kopier innholdet i denne mappa til roten av org-repoet.
2. Lim organisasjonens standard inn i `org/AGENTS.org.md`, uendret.
3. Fyll `org/loop.config.governance.yaml` (særlig `approved_mcp_servers` fra det godkjente registeret)
   og svar på det som kan i `org/compliance.md` §3.
4. Hent kitet: `bash scripts/upgrade-kit.sh` (kloner kit-repoet og skriver `org/KIT-VERSION`).
   Har ikke CI eller maskinen tilgang til kit-repoet, kopier mappa manuelt og skriv commiten inn i
   `org/KIT-VERSION`.
5. Lag prosjektets config: kopier `v3-copilot-agent-orchestrator/loop.config.example.yaml` til
   `v3-copilot-agent-orchestrator/loop.config.yaml`, fyll den ut, og kjør
   `bash scripts/apply-org-config.sh`.
6. Følg kitets README «Ta i bruk» fra steget som gjør `/setup` kjørbar. `/setup` setter
   organisasjonens standard inn øverst i `AGENTS.md`.

## Oppgradere kitet

`kit-upgrade`-workflowen sjekker hver mandag og tildeler deg en issue når det finnes en ny versjon
(du får e-post- og mobilvarsel). Da:

```bash
git switch -c kit-upgrade
bash scripts/upgrade-kit.sh                 # bytter ut kit-mappa, bevarer loop.config.yaml
diff <(grep -E '^[a-z_]+:' v3-copilot-agent-orchestrator/loop.config.example.yaml) \
     <(grep -E '^[a-z_]+:' v3-copilot-agent-orchestrator/loop.config.yaml)   # nye nøkler?
bash scripts/apply-org-config.sh            # org-verdiene tilbake i config
```

Kjør `/setup` i en ny Copilot-sesjon, kjør harnessene (kitets README steg 6) og lag en PR. Issuen
lukkes av seg selv ved neste sjekk etter merge.

## Hvor org-laget hører hjemme

- **Ett prosjekt:** legg det rett i prosjektets repo, som over.
- **Flere prosjekter:** ha ett sentralt «org-kit»-repo med kitet og org-laget, og la prosjektene
  kopiere fra det (pek `kit-repo` i `org/KIT-VERSION` dit i stedet for til kit-repoet). Da
  oppgraderer organisasjonen kitet ett sted.
