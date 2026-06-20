# Markedsanalyse — app for små, uformelle private arrangementer

> Basert på web-research juni 2026 (5 parallelle søkevinkler, kryssverifisert).
> Datasvakheter er flagget eksplisitt nederst.

## TL;DR

Gapet er **reelt, men smalt og kringsatt**. Ingen norsk aktør dekker hele
kjeden *invitasjon + gjesteliste + påminnelse + spleis* for løse, uformelle
private arrangementer. De internasjonale appene som løser det (Partiful m.fl.)
mangler det viktigste for Norge: **Vipps og norsk språk**. Men gapet er
omkranset av sterke naboaktører (Spond på distribusjon, Vipps på betaling),
så en ny app må vinne på *opplevelsen rundt det uformelle arrangementet* —
ikke på betaling alene.

## Konkurranselandskapet

| Aktør | Dekker | Mangler | Målgruppe |
|---|---|---|---|
| **Facebook Arrangement / Messenger** | Invitasjon, RSVP, chat (gratis) | Pålitelig oppmøte, betaling, når ikke unge | Alle — men fallende |
| **Spond** | Invitasjon, RSVP, chat, betaling | Bygget for *faste* grupper, ikke ad-hoc | Idrett/klubb/organisert |
| **Vipps (Oppgjør + Boks)** | Regningsdeling, innsamling | Ingen invitasjon/koordinering | Privat (de facto standard) |
| **Spleis (SpareBank 1)** | Innsamling/spleis | Ikke invitasjon/RSVP | Privat + organisasjon |
| **Grapevine** | Pene digitale invitasjoner + RSVP via SMS | Betaling, chat (svensk-tilknyttet) | Privat (bursdag/fest) |
| **Velda** | "Vors/fest/nach"-arrangementer, kart | Liten/usikker drift, smal | Unge/uteliv |
| **Tifti** | Private arrangementer **med billettsalg** | Vinklet mot *å tjene penger* | Privat, monetisering |
| **Partiful (US)** | Lett RSVP, påminnelser, reaksjoner | Ingen Vipps, ingen norsk | Gen Z, internasjonalt |
| **Apple Invites** | Invitasjon, RSVP, delt album | Krever iCloud+, ingen betaling, ikke norsk | Apple-økosystem |

### Det avgjørende skillet

- **Spond** eier "den organiserte gruppen" (lag som møtes fast).
- **Vipps** eier "betalingsdelingen".
- **Facebook** eide "den åpne invitasjonen".
- **Ingen** eier "det løse, private engangsarrangementet".

De nærmeste norske konkurrentene til idéen er **Grapevine** (kun
invitasjon+RSVP, svensk-tilknyttet) og **Tifti** (dreid mot billettsalg).
Begge bør verifiseres manuelt i App Store / Google Play — driftsstatus og
brukertall er usikre.

## Hvorfor de internasjonale ikke "tar" Norge

**Partiful** er den globale vinneren: ~500 000 månedlige brukere Q1 2025
(opp ~400 % å/å), Google Play "App of the Year" 2024, ~27 mill. USD i
finansiering (a16z). Gratis, Gen Z-fokusert, SMS-/lenkebasert.

Likevel faller alle internasjonale på to punkter i Norge:

1. **Betaling:** Partiful, Evite, Hobnob, Paperless Post bruker
   Venmo / Cash App / PayPal / Stripe. **Ingen støtter Vipps** — som er hele
   poenget med å samle inn penger i Norge.
2. **Språk:** Ingen reell norsk lokalisering. Kun små verktøy (Instavites,
   EasyRSVP) har norsk, men mangler spleis.

**Apple Invites** (feb. 2025) er en trussel på sikt, men krever iCloud+ for
verten, har ingen betalingsfunksjon, og varierer per land/språk.

## Er etterspørselen reell? Facebook Events forvitrer

- **SSB Norsk mediebarometer 2024:** Facebook størst totalt (62 % daglig),
  men ~80 % daglig blant 45–55, **bare 23 % blant 13–15-åringer**.
- **Medietilsynet, Barn og medier 2024 (9–18 år):** Snapchat 70 %, TikTok
  58 %, Instagram 46 %. Facebook ikke blant de mest brukte.
- **Pew (USA, trendbekreftelse):** Tenåringer på Facebook falt fra 71 %
  (2014/15) til 32 % (2024).

**Hvorfor Events spesifikt svekkes:** Nettverkseffekten slår motsatt vei —
når en voksende andel ikke har/bruker konto, *ekskluderer* du folk ved å
invitere via Facebook. I tillegg upålitelig RSVP ("Interessert" ≠ kommer),
algoritmen begraver oppdateringer, og inaktive brukere ser aldri varselet.
Folk flytter til gruppechat (Messenger/WhatsApp — som i 2025/26 har rullet
ut egen Events-funksjon) og dedikerte apper.

## Betalingsbiten — mulighet OG felle

- **Vipps har ~80 % penetrasjon** (~4,4 mill. brukere, >1 mill. bruk/dag).
- Vipps dekker **allerede** regningsdeling (**Oppgjør/grupper**) og
  innsamling (**Boks**: ~1,9 % gebyr, maks 50 000 kr/år).
- **Spleis** (SpareBank 1, *ikke* Vipps — vanlig forveksling) dekker større
  innsamlinger (6,5 % totalt gebyr).

**Implikasjon:** Vi kan *ikke* vinne på "vi lar deg dele regningen" — Vipps
gjør det gratis og bedre. Men Vipps har **åpne API-er** (ePayment, Recurring,
Login) å bygge oppå. Betaling/spleis må være en *støttefunksjon* i en bredere
koordineringsopplevelse, ikke kjerneverdien. Produksjonsbruk krever
merchant-avtale (kostnad/transaksjonsgebyr) — intet gratis hobby-tier.

## Samlet gap-vurdering

**For (gapet er ekte):**
- Ingen norsk alt-i-ett for *uformelle, private engangsarrangementer*.
- Internasjonale vinnere låst ute av Vipps-mangel + språk.
- Facebook forvitrer demografisk; et reelt behov er hjemløst.
- Sterk lokal betalingsinfrastruktur (Vipps API) å bygge på.

**Mot (vær edruelig):**
- **Spond** har ~1 mill. norske brukere + "Social Groups" allerede. Største
  trussel hvis de satser på det løse private arrangementet.
- **Vipps** løser betalingsdelingen alene.
- **Tifti** sikter allerede mot norske private arrangementer.
- **Monetisering uløst selv for Partiful** — gratis party-apper tjener lite.
- **Lavfrekvent bruk** (man arrangerer sjelden) → vanskelig retention.

**Wedge (brukerens egen innsikt):** Ingen *tenker* på å bruke Spond for dette
i dag. Kategori-assosiasjonen er ledig. Det er angrepspunktet.

## Kilder (utvalg)

- SSB Norsk mediebarometer 2024 · Medietilsynet Barn og medier 2024 · Pew Research 2024
- Partiful: Wikipedia, CNBC (apr. 2025), TechCrunch · Apple Newsroom (feb. 2025)
- Vipps: developer.vippsmobilepay.com, help.vippsmobilepay.com, snl.no/Vipps · spleis.no
- Spond: stripe.com/customers/spond, spond.com/activity/social, Shifter (CEO-intervju) · Superinvite · Tifti (gust.com / innomag.no)

## Datasvakheter (vær ærlig på disse)

- Norge-spesifikke brukertall for Spond (~1 mill.), Vipps Boks/Oppgjør og
  Spleis er **avledede/uoffisielle**.
- **Velda** og **Tiftis** driftsstatus, brukertall og betalingsmodell er
  **ubekreftet** — må sjekkes direkte i app-butikkene.
- **Facebook Events-bruk i Norge er ikke direkte målt** — konklusjonen er en
  velbegrunnet slutning fra (a) lav ung Facebook-bruk + (b) internasjonale
  Events-analyser, ikke et målt tall.
