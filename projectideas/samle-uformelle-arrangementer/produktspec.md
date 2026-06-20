# Produktspec — Samle

> Idéfase. Spec for å tenke klart, ikke et byggegrunnlag ennå.

## Produktprinsipp

Føles **lett, sosialt, uformelt** — ikke som administrasjon. Hvert valg
måles mot: *"Ville en 28-åring som skal lage vorspiel orket dette på 2
minutter fra mobilen?"* Hvis nei, kutt det.

## Målgruppe

- **Primær:** 23–40 år, har forlatt Facebook men lever på Instagram/Snap,
  arrangerer jevnlig uformelle sosiale ting (vors, middag, bursdag, hyttetur).
- **Arrangør-personaen** er den som i dag sukker over å koordinere i
  Messenger + Vipps + hoderegning.
- **Gjest-personaen** vil bare vite *hva, hvor, når, hvem kommer* — og helst
  ikke laste ned noe.

## De 3 kjernefunksjonene (prioritert)

### 1. Lag arrangement + del lenke — gjest trenger IKKE app ⭐ viktigst

Hele Facebook-exodus-smerten er "jeg når ikke folk". Løsning: arrangøren
lager et arrangement på <2 min, får en delbar lenke, limer den i
Messenger/SMS/Insta. Lenken åpner i nettleser. Gjest svarer ja/nei/kanskje
**uten konto, uten nedlasting**.

- Felter: tittel, dato/tid, sted (fritekst + valgfri kartlenke), beskrivelse,
  valgfritt cover-bilde/tema.
- Output: offentlig arrangementsside på egen URL + auto-generert delbar
  grafikk (se markedsføring).

### 2. Gjesteliste + RSVP + automatisk påminnelse

Pålitelig oppmøte er det Facebook gjør dårligst.

- Svaralternativer: Kommer / Kommer ikke / Kanskje (+ valgfritt "+1").
- Arrangør ser live liste og antall.
- Auto-påminnelse til de som har svart ja/kanskje (SMS eller web-push)
  dagen før. Valgfri "ikke svart"-purring.

### 3. Vipps-spleis innebygd (felleskasse)

Den norske moaten ingen internasjonal app har: "kast inn 200 kr til vorset".

- **v1:** lenk til en manuell Vipps-boks/MobilePay-nummer (ingen ekte
  integrasjon) — tester etterspørselen uten merchant-avtale.
- **v2:** ekte Vipps ePayment-integrasjon med innbygd felleskasse og oversikt
  over hvem som har betalt.

## Hva vi BEVISST dropper (anti-scope)

- **Chat.** Messenger/WhatsApp-gruppa finnes. Vi *lenker til* den, bygger den
  ikke. Å konkurrere med Messenger er bortkastet.
- **Native iOS/Android-app** (i starten). Web-first. PWA senere.
- **Billettsalg / monetisering av arrangementer** (det er Tiftis vinkel).
- **Tilbakevendende grupper / medlemskap / kontingent** (det er Spond).
- **Avansert design-/malmotor** (det er Paperless Post). Få, fine temaer.

## Kjerne-brukerflyt

```
Arrangør                                  Gjest
--------                                   -----
Åpne samle.no                              Får lenke i Messenger/SMS
→ "Lag arrangement"                        → Trykker lenke
→ Tittel/tid/sted/bilde            ──del──▶ → Ser arrangementsside (nettleser)
→ Får delbar lenke + grafikk               → Svarer Ja/Nei/Kanskje (ingen konto)
→ Ser live gjesteliste            ◀────────  → (valgfritt) navn + valgfritt +1
→ (valgfritt) start felleskasse            → Får påminnelse dagen før
→ Auto-påminnelse sendes ut
```

## Suksesskriterier (hva "fungerer" betyr)

- Arrangør lager arrangement på under 2 min, første gang, uten hjelp.
- Gjest svarer på under 15 sek uten å laste ned noe.
- Minst én arrangør inviterer til arrangement #2 (retention-signal).
- Minst én gjest blir arrangør (viral loop — se markedsføring).

## Åpne produktspørsmål

- Trenger arrangøren konto, eller holder en "magic link" til eget
  arrangement? (Mindre friksjon = bedre, men gjør gjenfinning vanskeligere.)
- SMS-påminnelser koster penger per melding — web-push er gratis men krever
  at gjest godtar varsler i nettleser. Hybrid?
- Hvordan håndtere misbruk/spam når hvem som helst kan lage offentlige sider?
