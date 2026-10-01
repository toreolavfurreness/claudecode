<!--
  GENERERT av /setup fra loop.config.yaml — IKKE rediger her.
  Endre loop.config.yaml og kjør /setup på nytt.
-->

# 6d. Worktree-sweep (hver syklus, kun koordinator)

→ Kjerne: `coordinator-runbook.md` § 6d · Begrunnelser: `runbook-hvorfor.md` § 6d

**Selve kjøringen skjer i §6 steg 4b, IKKE her** (fix-runde 1, B1) — denne seksjonen beskriver
HVORFOR mekanismen finnes og HVA den gjør; §6 steg 4b eier NÅR den kjøres. Tidligere sto det her
at kallet skjedde «etter §6b», som i praksis betydde etter at §6 steg 5 allerede hadde skrevet
raden — en rad kan ikke få `wtsweep=` ettermontert. Ett steg, ingen skjønn: `$WTSWEEP`-verdien
fanget i §6 steg 4b skrives inn i DENNE syklusens §6-rad i run-log.md, som en del av selve
rad-skrivingen i steg 5 — ikke som en etterfølgende redigering. Hentes ordrett fra sweepens egen
oppsummeringslinje, ikke anslått.

**Gaten (§6c, Del A) er token-basert, ikke tidsstempel-basert** (fix-runde 2, B1). Den leser
INNHOLDET i siste §6-rad i run-log.md og krever at raden bærer et `wtsweep=<n>/<n>`-token. Grunnen
til at et tidsstempel-sammenligning ble forkastet i fix-runde 1: selv med riktig rekkefølge
(steg 4b FØR steg 5) kan steg 5 skrive raden i et SENERE minutt enn sweepens egen `ts`, som by
construction gjør sweepens tidsstempel eldre enn radens — falskt RØDT på en sweep som faktisk
kjørte i samme syklus. Et innholds-sjekk er immun mot denne racen fordi den ikke sammenligner
tidspunkter i det hele tatt.

**Radfilteret er POSITIVT, IKKE et negativt helse-unntak** (fix-runde 3, mikro — retter en påstand
som tidligere sto her og feilaktig hevdet «samme skille som §6c Trigger 2»: Trigger 2 sin
`awk`-teller bruker BEGGE literalene `| health |` og `| merged |` sammen i én tilstandsmaskin, mens
gaten her bruker KUN `| merged |` alene, positivt). Kolonne 4 i run-log.md har flere verdier enn
`merged`/`health`: målt på dev er fordelingen `merged` 113, `paused` 20, `health` 19, `resumed` 5,
`housekeeping` 1. Et negativt filter (`grep -v health`) ville latt en `paused`/`resumed`/
`housekeeping`-rad telle som «siste §6-rad» og gitt falskt RØDT, siden disse radtypene ikke
nødvendigvis bærer `wtsweep=`. Gaten leter derfor etter siste rad med literalen `| merged |` og
ignorerer alt annet (health, paused, resumed, housekeeping) uansett hvor de står i loggen.

**Sweepen er ikke en svakere §0b.** Den har et annet kriterium, valgt fordi det er billig å
verifisere og umulig å ta feil av: et tre fjernes kun når **ingenting i det kan gå tapt**.

1. HEAD finnes på en remote branch (`git branch -r --contains`) ⇒ ingen commit kan gå tapt. Er
   dette IKKE tilfelle (typisk squash-merge, der HEAD-committen selv aldri lander på `{{BASE_BRANCH}}`), eller
   er treet skittent: `tasks/worktree-landed.sh` avgjør INNHOLDSMESSIG om alt som ikke er
   committet trygt likevel finnes i `{{BASE_BRANCH}}` (samme sti, omdøpt/arkivert, eller flyttet — se fila for
   klassene). Kun et rc 0 fra den (LANDED) tillater fjerning; alt annet ⇒ BEHOLD. Filer den melder
   `LANDED-MOVED` reddes til `.claude/worktree-rescue/<ts>/` og verifiseres byte-for-byte FØR
   treet fjernes.
2. Ingen ÅPEN PR bærer denne worktreens HEAD — verken via branch-NAVN eller commit-ancestry mot en
   åpen PRs `headRefOid` (en implementer som fortsetter på et lokalt `fix-…-local`-navn er vanlig
   praksis og må ikke miste vernet fordi navnet ikke matcher PR-branchen).
3. En lås som peker på en LEVENDE pid respekteres. En foreldreløs lås (pid borte, typisk etter
   maskin-restart) er ikke et vern — den er søppel fra en død agent. Låsen kan også SLIPPES mens
   agenten fortsatt lever (målt) — den er en bonus, ikke et liveness-signal.
4. Treet er ikke rørt de siste `AGE_MIN` minutter (default 1440) — vern mot en levende, TENKENDE
   agent uten skriving og uten lås. Målt 62 og 218 minutter uten skriving i to levende trær samme
   dag — en lavere terskel ville IKKE beskyttet dem.

   **Unntak — navngitt kjøring (§6 steg 4b, TODO 401):** trær som navngis der, tilhører agenter
   som har returnert; aldersvakten hoppes over for dem. Alle andre vakter gjelder uendret.
5. Enhver kommandofeil underveis (status, `gh`, `git branch -r`, `find`) ⇒ BEHOLD, aldri stille
   videre som om svaret var «ingen treff».

Rescue-katalogen er gitignorert. Se på den kun hvis noe faktisk mangler; commit derfra bare det som
viser seg å være ekte arbeid. Ved tvil: `--dry-run` rapporterer uten å røre noe.

**Innkalling er mekanisk, ikke prosa (TODO 380).** `/loop-health-check` Del A kjører
`./tasks/worktree-sweep.sh --gate`, som leser siste ikke-helse-§6-rad i run-log.md og feiler
RØDT (§8b kjøres ikke) hvis den raden mangler `wtsweep=<n>/<n>`-tokenet eller bærer et
feil-formet ett (`wtsweep=feilet:…`) — se §6 steg 4b/5 for hvorfor det er nettopp raden, ikke en
tidsstempel-sammenligning, som avgjør (fix-runde 2, B1). `tasks/metrics/worktree-sweep-log.jsonl`
er ren diagnostikk og leses ikke av gaten. `/todo-done` steg 13b kjører KUN `--dry-run` + `--gate`
— den sletter aldri selv; gaten er mekanismen som gjør en uteblitt sweep synlig, ikke steg 13b.

**Docker prunes aldri automatisk, og sweepen rapporterer det ikke lenger (TODO 401)** — `docker
info` hang ~50 min mot en hengende daemon (tørrkjøring 2026-09-25) og holdt sweepen etter at
vurderingen var ferdig; macOS har ingen `timeout`, og `perl -e 'alarm …'` stopper ikke
docker-CLI-en (målt). En kjørende harness-container eier volumet sitt. Er `disk_ledig=` lav, kjør
`docker system df` for hånd; viser den `Containers=0B`, er `docker volume prune -f` trygt.
Postgres-
imaget deklarerer `VOLUME /var/lib/postgresql/data`, så hver container uten navngitt volum lager et
anonymt et; ryddes containeren aldri (daemon hang, disk full, agent avbrutt), blir volumet stående.
Målt 2026-09-09: 465 anonyme volumer, 18,7 GB. Dette er en selvforsterkende sløyfe — full disk gir
hengende daemon gir uryddede containere gir fullere disk — så les tallet, ikke bare hopp over det.
