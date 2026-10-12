# kit-port — holde Copilot-kitet i takt med v3

`v3-copilot-agent-orchestrator/` er en port av `v3-agent-orchestrator/` til GitHub Copilot. Når v3
endres, må endringen portes. Denne mappa inneholder det som gjør at det ikke glipper.

| Fil | Hva |
|---|---|
| `check-drift.sh` | Lister commits og filer i `v3-agent-orchestrator/` som er endret siden Copilot-kitet sist ble synket. Exit 0 = i synk, 1 = drift, 2 = kan ikke måles |
| `validate-copilot-kit.sh` | Ordvakt (ingen «Claude» i Copilot-mappa), `/setup` ende-til-ende i et testprosjekt, og alle harnesser og selvtester. Exit 0 = grønn |
| `PORT-RULES.md` | Reglene for å porte en endring: stikart, vokabular, worktree, hooks, modeller og kostnad |
| `../workflows/copilot-kit.yml` | Kjører begge skriptene i GitHub Actions |
| `../../v3-copilot-agent-orchestrator/KIT-SYNC` | `synket-mot: <sha>`: siste commit av v3 som er portert |

## Slik virker det i dag (drift-vakt)

- **PR som rører v3 eller Copilot-kitet:** `validate` må være grønn (blokkerende). `drift` viser en
  advarsel og en oppsummering hvis Copilot-kitet henger etter, men blokkerer ikke v3-arbeid.
- **Push til `main`:** `drift` holder én åpen issue, «Copilot-kitet henger etter
  v3-agent-orchestrator», oppdatert med commits og filer. Når en port-PR med oppdatert `KIT-SYNC` er
  merget, lukkes issuen automatisk.
- **Portingen gjøres manuelt:** følg arbeidsflyten øverst i `PORT-RULES.md`, eller be en agent om å
  gjøre det med `PORT-RULES.md` som instruks.

Lokalt:

```bash
bash .github/kit-port/check-drift.sh            # hva er ikke portert?
bash .github/kit-port/validate-copilot-kit.sh   # er Copilot-kitet fortsatt grønt?
```

## Muligheter for å automatisere portingen senere

Drift-vakta forteller *at* noe må portes. Neste trinn er at en agent lager port-PR-en selv. Alle tre
alternativene under bruker `PORT-RULES.md` som instruks og `validate-copilot-kit.sh` som kontroll, og
ingen av dem merger selv: en person reviewer og merger port-PR-en.

| Alternativ | Slik settes det opp | Fordeler | Ulemper |
|---|---|---|---|
| **Claude Code-routine** (planlagt) | En routine på Claude-kontoen kjører f.eks. hver natt: `check-drift.sh`, og ved drift en port etter `PORT-RULES.md` og en PR. Settes opp fra en Claude Code-økt | Ingen nøkler i repoet; kjører på eksisterende abonnement | Reagerer ikke umiddelbart (på planen, ikke på push) |
| **Claude Code GitHub Action** | En workflow-jobb som starter når `drift` finner endringer på `main`, og kjører Claude Code med `PORT-RULES.md` og diffen | Starter rett etter merge; alt synlig i Actions | Krever en Anthropic API-nøkkel som repo-secret; faktureres per kjøring |
| **Copilot cloud agent** | `drift`-jobben tildeler issuen sin til Copilot, som lager PR-en | Bruker Copilot-abonnementet | Copilot cloud agent må være slått på for repoet; agenten har brannmur og tidsgrense |

Uansett valg gjelder det samme: én port-PR per drift, `validate` grønn, `KIT-SYNC` oppdatert, og en
person merger.

## Lengre sikt: felles kjerne

Et alternativ til porting er at begge kitene genereres fra én kilde: en plattformnøytral kjerne
(runbook, stegfiler, skript) pluss et lag per plattform (agentformat, verktøynavn, hooks). I dag er
bare 29 av 119 filer identiske, og forskjellene er vevd inn i runbook-teksten, så dette krever at v3
skrives om med plattform-tokens. Det blir aktuelt hvis en tredje plattform kommer til.
