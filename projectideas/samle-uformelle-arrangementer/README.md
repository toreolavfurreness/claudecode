# Samle — app for små, uformelle private arrangementer

> **Arbeidstittel:** "Samle" (ikke endelig — se [04-navn-og-merkevare.md](04-navn-og-merkevare.md))
> **Status:** Brainstorming / idéfase. Ingenting bygget ennå.
> **Sist oppdatert:** 2026-06-20

## Pitch i én setning

En lett, norsk web-app for å invitere til og koordinere små uformelle
private arrangementer — vorspiel, bursdager, vennemiddager, hytteturer,
utdrikningslag — der gjesten svarer via en delbar lenke uten å laste ned
noe, og spleising skjer med Vipps.

## Hvorfor nå?

Facebook "Arrangement" forvitrer (særlig blant under 40), men ingen norsk
aktør har tatt over for det løse, private arrangementet. Folk lapper i dag
sammen **Messenger + Vipps + regneark**. Spond eier den *organiserte*
gruppen (idrettslag), Vipps eier *betalingsdelingen*, Facebook eide den
*åpne invitasjonen* — men ingen eier engangs-vennegjeng-arrangementet.

Reell signalvalidering fra brukeren selv (juni 2026): siste vorspiel-invitasjon
ble sendt med teksten *"siden ingen er på facebook lenger, så må jeg sende
invitasjon i messenger, vi kommer tilbake til detaljene."* Flere
Messenger-grupper flagger dette som et reelt hull.

## Dokumenter i denne mappen

| Fil | Innhold |
|---|---|
| [00-markedsanalyse.md](00-markedsanalyse.md) | Konkurrentkartlegging, gap-vurdering, etterspørsel, kilder |
| [01-produktspec.md](01-produktspec.md) | Kjernefunksjoner, brukerflyt, hva vi bevisst dropper |
| [02-mvp-plan.md](02-mvp-plan.md) | Teknisk stack, datamodell, faseplan, åpne spørsmål |
| [03-markedsforing-instagram.md](03-markedsforing-instagram.md) | Vekststrategi, invitasjon-som-markedsføring-loopen |
| [04-navn-og-merkevare.md](04-navn-og-merkevare.md) | Navneforslag, posisjonering, tone |

## Den strategiske kjernen (les denne hvis du bare leser én ting)

Spond er en *mental kategori-feil* for dette bruket — ingen åpner Spond for
å lage et vorspiel. Vi konkurrerer derfor **ikke på funksjoner mot Spond**,
men på *kontekst og følelse*: produktet skal føles lett, sosialt og
uformelt (Partiful-vibe), ikke som administrasjon (Spond-vibe). Det styrer
alle produktvalg.

## Beslutninger tatt så langt

- **Web-first, ikke native app.** Kravet "gjest slipper å laste ned noe"
  er uforenlig med native-først. Mobiloptimalisert web + delbar lenke.
- **3 kjernefunksjoner**, ikke flere (se produktspec).
- **Chat droppes** — vi lenker til eksisterende Messenger/WhatsApp-gruppe.
- **Instagram som funnel**, der invitasjonen selv er markedsføringen.

## Neste steg (ikke gjort ennå)

1. Bruker tester Grapevine / Velda / Tifti manuelt for å se hvor nær de er.
2. Avgjøre om/når vi bygger en ekte prototype (eget repo).
3. Validere monetiseringsvinkling før noe bygges i stor skala.
