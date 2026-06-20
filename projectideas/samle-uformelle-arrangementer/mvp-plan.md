# MVP-plan — Samle

> Idéfase. Plan for *hvis/når* vi bygger en prototype i eget repo.

## Mål for MVP

Bevise den ene tingen som betyr noe: **vil folk faktisk bruke en delbar
lenke i stedet for Messenger-rot?** Alt annet er sekundært. MVP-en skal
være liten nok til å bygges på uker, ikke måneder.

## Anbefalt stack

| Lag | Valg | Hvorfor |
|---|---|---|
| Frontend | **Next.js (App Router) + React** | Web-first, server-rendret delbare sider, god OG-tag-/lenkedeling |
| Styling | **Tailwind CSS** | Rask, konsistent, mobil-først |
| Backend/DB | **Supabase** (Postgres + Auth + Storage) | Gratis tier, rask oppstart, magic-link auth innebygd |
| Hosting | **Vercel** | Null-config deploy av Next.js, gratis tier, previews |
| Påminnelser | Web-push (gratis) først; SMS via Twilio/linkmobility senere | Hold kostnad nede i validering |
| Betaling | Manuell Vipps-lenke (v1) → Vipps ePayment API (v2) | Unngå merchant-avtale til etterspørsel er bevist |

> Stack er en anbefaling, ikke låst. Next.js + Supabase + Vercel gir
> raskest vei fra null til delbar lenke med lav/ingen kostnad.

## Datamodell (skisse)

```
event
  id (uuid, pk)
  slug (unik, brukes i URL)
  host_id (fk -> user, nullable hvis magic-link-modell)
  title, description
  starts_at, location_text, location_url
  cover_image_url, theme
  collection_enabled (bool), collection_link (text)   # Vipps v1
  created_at

rsvp
  id (uuid, pk)
  event_id (fk -> event)
  guest_name
  status (enum: yes | no | maybe)
  plus_ones (int, default 0)
  contact (nullable: telefon/epost for påminnelse)
  created_at

# user-tabell kun hvis vi velger konto-modell; ellers utelates
```

## Faseplan

### Fase 0 — Validering FØR kode (gjøres nå, av bruker)
- Test Grapevine / Velda / Tifti manuelt. Hvor nær er de?
- Bekreft smerten med 15–20 i målgruppen (allerede delvis gjort i
  Messenger-grupper — utvid litt).
- Beslutt: er dette verdt en prototype? Hvis nei, stopp her.

### Fase 1 — Tynn MVP (kjernefunksjon 1 + 2)
- Lag arrangement → delbar lenke → gjesteside → RSVP uten konto.
- Live gjesteliste for arrangør.
- Auto-generert delbar grafikk (OG-image) for Instagram/Messenger.
- **Ingen** betaling, **ingen** SMS ennå (web-push valgfritt).
- Deploy på et eget domene. Del i egne vennegrupper = første brukere.

### Fase 2 — Påminnelser + spleis (lett)
- Web-push/SMS-påminnelse dagen før.
- Manuell Vipps-felleskasse-lenke på arrangementssiden.

### Fase 3 — Ekte Vipps + retention
- Vipps ePayment-integrasjon (krever merchant-avtale).
- "Lag nytt arrangement fra forrige", tilbakevendende vennegjeng.
- Vurder PWA/native først her, ikke før.

## Kostnad i valideringsfasen

- Next.js + Supabase + Vercel: **0 kr** på gratis tier opp til lav trafikk.
- Domene: ~150 kr/år.
- SMS: kun hvis aktivert — unngås i fase 1.
- Vipps merchant: utsettes til fase 3.

## Risikoer / åpne spørsmål

- **Merchant-avtale Vipps:** transaksjonsgebyr + KYC. Avklar tidlig om
  felleskasse i appen er verdt friksjonen vs. bare lenke til brukerens egen
  Vipps-boks.
- **Retention ved lavfrekvent bruk:** trenger en grunn til å komme tilbake
  (lagrede vennegjenger? "din historikk"?).
- **Spam/misbruk** på offentlige sider — minst rate-limiting + rapportering.
- **Spond-trussel:** hva hindrer Spond i å gjøre dette? Svaret bør være
  klart før vi bygger i stor skala (se markedsanalyse).
