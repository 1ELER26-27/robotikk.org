# Visuell spesifikasjon for robotikk.org

Dette dokumentet er den normative visuelle kontrakten for robotikk.org. Nye sider og komponenter skal følge den. Ved konflikt vinner denne spesifikasjonen og de globale CSS-tokenene foran lokal styling.

## Uttrykk

Robotikk.org skal oppleves som et rolig, praktisk og presist verktøy for elever og lærere. Uttrykket skal støtte scanning, sammenligning og gjentatt bruk. Det skal ikke ligne en reklameside eller en tilfeldig AI-generert demo.

- Lys, luftig og høy kontrast som standard.
- Teknisk, men vennlig: marineblå tekst, teal som handling/fokus og varm gul som sparsom aksent.
- Flate, tydelige paneler og kort. Maksimal border-radius er 4px.
- Ingen lilla standardpalett, glassmorfisme, dekorative blobs eller tekst oppå urolige bakgrunner.
- Visuell pynt skal aldri konkurrere med modulnavn, funksjon, status eller handlinger.

## Globale regler

- Bruk `--ink` på `--paper` eller `--panel`; bruk aldri mørk tekst på mørk bakgrunn.
- Bruk `--on-accent` på `--accent` og `--on-dark` på `--ink`.
- Vanlig tekst skal minst oppfylle WCAG AA-kontrast 4.5:1. Stor tekst skal minst oppfylle 3:1.
- Alle interaktive elementer skal ha synlig `:focus-visible`.
- Ikke kommuniser status med farge alene; bruk tekst, ikon eller attributt i tillegg.
- Bruk norsk språk, konkrete handlingsverb og korte etiketter.
- Ikke bruk tekst i en knapp når et kjent ikon alene er tydelig; ukjente ikoner skal ha tooltip/tilgjengelig navn.
- Bilder skal ha meningsfull alt-tekst. Dekorative bilder skal ha tom alt-tekst.
- Tekst skal kunne brytes uten å overlappe eller presse layouten ut av viewporten.
- Bruk responsiv CSS med stabile dimensjoner for kort, bilder, knapper og QR-koder.

## Typografi og layout

- Bruk en lesbar sans-serif fra systemet inntil en egen font er valgt.
- Brødtekst: normal størrelse, linjehøyde rundt 1.5.
- Overskrifter skal følge semantisk rekkefølge og ikke hoppe nivå.
- Maksimal innholdsbredde er rundt 70rem; tekstblokker bør være kortere enn 50rem.
- Bruk luft og grupperinger fremfor tunge rammer.
- Mobil er en fullverdig visning, ikke bare en krympet desktopside.

## Komponenter

- Lenker: teal/marineblå, understrek ved hover/fokus.
- Knapper: tydelig bakgrunn, tekst med kontrollert kontrast, minst 44px høy trykkflate.
- Skjema: synlig label over hvert felt, valideringsfeil nær feltet og aldri bare placeholder som label.
- Kort: én tydelig tittel, kort beskrivelse, metadata og én primær handling.
- Tagger: korte og sekundære; de skal ikke være eneste kilde til betydning.
- Tabeller/specifikasjoner: stabile kolonner på desktop og lesbar stabling på mobil.
- QR: hvit bakgrunn, fri marg rundt koden og alternativ tekst/URL ved siden av.
- Hylleetiketter: høy kontrast, enkel tekst, modul-ID først og utskriftsstil uten navigasjon.

## Interaksjon

- Søk og filtre skal gi treffantall, tomtilstand og fungere med tastatur.
- Offentlig katalog skal kunne leses uten JavaScript; JavaScript forbedrer søk/filter.
- Lasting, feil, tomtilstand og suksess skal ha tydelige tekstbeskjeder.
- Bekreft destruktive handlinger og vis hvem handlingen gjelder.
- Innloggede funksjoner skal skille mellom elev- og lærerhandlinger visuelt og semantisk.

## Før publisering

1. Test lys bakgrunn, mørk tekst, lenker, knapper og fokus med tastatur.
2. Test 320px bredde og stor desktopbredde.
3. Kontroller at ingen tekst eller kontroller overlapper.
4. Kontroller alle bilder, alt-tekster, QR-koder og utskriftsvisning.
5. Test med JavaScript deaktivert der innholdet skal være lesbart.
6. Kontroller kontrast med et verktøy før nye farger tas i bruk.
7. Kjør Hugo-build og se på den faktiske genererte siden, ikke bare templaten.

## Endringsregel

Nye farger, skygger, radius, typografiskala eller komponentmønstre skal først legges til som globale tokens eller dokumenteres her. Unngå inline-styling og lokale unntak. Når en komponent trenger et unntak, skal årsaken være tydelig og tilgjengelighetstesten gjentas.
