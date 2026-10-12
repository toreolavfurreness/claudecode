# Retro: release <versjon>

**Release:** <versjon> · **Dato:** <dato> · **Hvem:** <eier>, <sesjon>

**Form:** egen sesjon med eieren, ikke en loop-agent. Ett spørsmål om gangen, hvert med tall,
lesning og spørsmål. Sesjonen skriver dette notatet (`docs/loop/retro-<versjon>.md`) og
overleveringen til koordinatoren (`coordinator-runbook.md` § Egen sesjon, ikke agent). Den skriver
ikke lessons, followups eller run-logg. Det gjør koordinatoren etterpå.

## Tallgrunnlag

```bash
python3 tasks/retro-numbers.py <versjon> --since <iso, datoen releasen ble aktiv> --until <iso>
```

Lim inn utskriften urørt under. `IKKE MÅLT` er ikke 0: tallet mangler. Et tall som hentes under
samtalen, merkes «talt i retroen» med kilde.

<utskrift>

## Måling av forrige retros endringer

Kopier tabellen fra «Måling i neste retro» i forrige notat, og fyll ut de to siste kolonnene.

| Endring | Tall | Forrige release | Mål | Målt |
|---|---|---|---|---|

En endring som ikke har flyttet tallet sitt, tas opp igjen og endres eller fjernes. Det som sto
under «Utsatt» i forrige notat, tas også opp her.

## Faste spørsmål

### 1. Leverte vi målet?

Målet ordrett, hva brukerne merker, og hvem som har tatt bygget i bruk.

### 2. `done_when` ved release

Hvor mange linjer var oppfylt da releasen gikk. Svaret føres per åpen linje: var kriteriet feil,
eller slapp vi for tidlig?

### 3. Hva kostet det, og hvor gikk pengene?

Per todo, per rolle, hovedsesjonene, og fordelingen av diffen på klasser.

### 4. Hvor mange runder trengte vi?

Median, og halen på tre eller flere: hvilke todoer, og hvorfor.

### 5. Hva måtte eieren avgjøre?

Nivå A og nivå B. `[A0]` etter slag og ventetid på eier står i tallgrunnlaget («Beslutninger»).
Tabellen fylles for hånd bare for det som står som `IKKE MÅLT` der:

| Slag | Antall |
|---|---|
| Runder (ny review- eller fix-runde) | |
| Reelle eiervalg | |
| Teknisk risiko | |
| Kvittering | |
| Måling | |

### 6. Selve prod-releasen

Tid fra start til bygget var ute, hvilke steg som stoppet, og hvilken commit bygget ble laget fra.

### 7. Hva fant vi for sent?

Antallet står i tallgrunnlaget («Bugs i perioden»). Hvem som fant dem (kode-review, full suite,
eierens test) telles for hånd.

### 8. Hva endrer vi?

Svaret føres under «Høyst tre endringer».

## Prosjektets egne spørsmål

-

## Høyst tre endringer

Per endring: merke `prosjekt` eller `kit`, hvem som gjør den, tallet den skal flytte med dagens
verdi og mål, og risiko. En kit-endring blir en issue i `claudecode` med tallet.

1.

## Utsatt

-

## Engangsoppgaver til koordinatoren

-

## Måling i neste retro

| Endring | Tall | I dag | Mål |
|---|---|---|---|
