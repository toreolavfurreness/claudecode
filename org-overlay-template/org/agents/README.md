# Organisasjonens egne agenter

Legg tech-review-agenter som organisasjonen krever her (f.eks. en sikkerhetsreviewer som sjekker mot
organisasjonens sikkerhetsretningslinjer), som `<navn>.agent.md`. Utgangspunkt:
`v3-copilot-agent-orchestrator/examples/tech-review-agents/`.

Ta dem i bruk i et prosjekt:
1. Kopier fila til `.github/agents/<navn>.agent.md`.
2. Registrer agenten under `tech_review_agents` i `loop.config.yaml` (navn, trigger, `trigger_globs`,
   `severity_floor`).
3. Kjør `/setup`. Agenten må ikke ha `edit` i `tools`; `/setup` stopper ellers.
