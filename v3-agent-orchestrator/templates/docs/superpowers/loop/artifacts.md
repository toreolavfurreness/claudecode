# Faste artefakter

Eneste sted i repoet der lenkene står. `/handover` og §6-halen leser herfra.
**Republiser alltid med `url`** — en publisering uten `url` lager en ny side og bryter lenken eieren har.
Har sesjonen verken lest eller publisert siden, kjør `Artifact action:"read"` på URL-en først.

Fila er prosjekt-eid (`/setup` skriver den bare hvis den mangler), men Køsiden-raden er felles for alle
prosjekter: generator- og vakt-kolonnen skal stå nøyaktig som i kit-malen. `python3 tasks/kit-drift.py`
melder avvik. Fyll inn URL-en etter første publisering; legg prosjektets egne sider til som nye rader.

| Side | URL | Generator (fra et tre med oppdatert `origin/{{BASE_BRANCH}}`) | Vakt etter generering |
|---|---|---|---|
| Køsiden | (fylles inn etter første publisering) | `python3 tasks/queue-status.py --html <scratchpad>/queue-status.html > tasks/queue-status.md` | `grep -cF "<title>$(python3 tasks/queue-status.py --print-title)</title>" <scratchpad>/queue-status.html` = 1 og `grep -c "$(python3 tasks/release.py status \| sed -n '1s/^RELEASE \([^ ]*\).*/\1/p')" <scratchpad>/queue-status.html` ≥ 1 |

HTML-filene committes ikke; de lever i scratchpad.
