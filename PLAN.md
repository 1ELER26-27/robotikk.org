# Plan: robotikk.org via Cloudflare Tunnel

## Status
- [x] Fase 3 — webserver (192.168.30.105): pakker, `robotikk`-bruker, lokal nginx :8080, webhook :9000, ufw. Kjørt via `deploy/setup-server.sh`, verifisert OK.
- [x] Fase 4 (delvis) — repo opprettet og pushet: https://github.com/1ELER26-27/robotikk.org
- [x] Cloudflare Tunnel installert — men **på webserveren selv**, ikke på en egen nginx-VM (se "Arkitekturendring" under).
- [ ] Basic Auth på lokal nginx (htpasswd-fil + `auth_basic` lagt til i config, må aktiveres med ekte bruker)
- [ ] Cloudflare Public Hostnames peke til `localhost:8080` / `localhost:9000`
- [ ] Fase 4 (resten) — legg webhook-secret inn i GitHub repo settings
- [ ] Fase 5 — verifisering fra internett + herding

## Arkitekturendring (viktig!)
Opprinnelig plan brukte en egen nginx-VM (Nginx Proxy Manager på 192.168.30.101:81) som
reverse-proxy + Basic Auth-lag foran webserveren. Cloudflared ble i praksis installert
**direkte på webserveren** (192.168.30.105), og brukeren bekreftet at NPM-instansen på
192.168.30.101 ikke skal brukes til dette prosjektet i det hele tatt (den har andre formål,
bl.a. `bambulab.robotikk.org` som ikke skal røres).

**Konsekvens:** alt kjører nå på én maskin — enklere, færre bevegelige deler:
- `cloudflared` (her) kobler ut til Cloudflare og ruter både `robotikk.org` og
  `deploy.robotikk.org` til `localhost`.
- Lokal nginx på port 8080 gjør **selv** Basic Auth (ikke lenger et eget edge-lag).
- Port 8080/9000 trenger ikke lenger åpnes for LAN i ufw — kun loopback-trafikk fra
  cloudflared treffer dem.

## Kontekst
- Domene robotikk.org, DNS/Cloudflare finnes allerede.
- Denne maskinen (hostname `webserver`, 192.168.30.105/23) = Ubuntu 24.04.5 LTS LXC-container på Proxmox (192.168.30.101).
- Nginx Proxy Manager finnes på 192.168.30.101:81, men brukes IKKE i dette prosjektet.
- Ingen offentlig IP / brannmur blokkerer innkommende trafikk.

## Bekreftede valg
1. Eksponering: **Cloudflare Tunnel** (cloudflared), kjører på webserveren selv.
2. Autentisering foran siden: **Nginx Basic Auth** (htpasswd, brukernavn+passord), på lokal nginx.
3. Innhold: **Statisk nettside (Hugo)**.
4. Utrulling fra GitHub: **Webhook + pull-script** (adnanh/webhook), ikke self-hosted runner.
5. Reverse proxy: **ingen egen VM** — nginx kjører lokalt på webserveren.
6. GitHub-repo: offentlig, i organisasjonen https://github.com/1ELER26-27/ (`robotikk.org`-repoet).
7. Deploy-hook skilles ut på eget hostname `deploy.robotikk.org`, beskyttet med GitHub sin HMAC-signatur i stedet for basic auth.

## Arkitektur
```
Internet -> Cloudflare (DNS proxied, TLS) -> Cloudflare Tunnel (cloudflared, på webserveren)
   -> webserver LXC (192.168.30.105, denne maskinen) [alt kjører her]
        - lokal nginx :8080 : auth_basic (htpasswd) + serverer bygget Hugo-output
        - webhook :9000 (adnanh/webhook) verifiserer GitHub HMAC-secret, kjører deploy.sh
        - deploy.sh: git pull i /opt/robotikk-site -> hugo build til temp-dir -> atomisk mv -> reload nginx
```

## Gjenstående steg

> **Merk om gammel tunnel:** Det finnes en gammel, død tunnel kalt `robotikk` fra tidligere
> (tunnel-id `405db25f-4fa2-4a8d-91b3-61ec78806e5c`). Den er bevisst IKKE migrert/rørt —
> vi opprettet en ny, separat tunnel (`robotikk-classroom`) i stedet, for å unngå enhver
> risiko for `bambulab.robotikk.org`.

### 1. Cloudflare Public Hostnames (dashboard)
Siden cloudflared kjører lokalt, skal begge hostnames peke til `localhost`:
- `robotikk.org` → HTTP → `localhost:8080`
- `deploy.robotikk.org` → HTTP → `localhost:9000`

### 2. Basic Auth (på webserveren)
```sh
sudo htpasswd -B /etc/nginx/robotikk.htpasswd <brukernavn>
```
(skriv passordet direkte i terminalen når det spørres om det — del det ikke med noen andre)

Config-filen (`deploy/robotikk-local-nginx.conf`) har allerede `auth_basic` lagt til og er
installert av `setup-server.sh`. En tom htpasswd-fil betyr at ALLE avvises (fail closed)
inntil en ekte bruker er lagt til med kommandoen over.

### 3. ufw — fjern nå unødvendige LAN-regler
```sh
sudo ufw status verbose   # sjekk om 8080/9000 fortsatt er åpnet for LAN fra tidligere forsøk
sudo ufw delete allow from 192.168.30.0/23 to any port 8080,9000 proto tcp 2>/dev/null || true
sudo ufw delete allow from 192.168.30.0/23 to any port 8080 proto tcp 2>/dev/null || true
sudo ufw status verbose   # skal nå kun vise port 22 åpen
```

### 4. GitHub-integrasjon (resten)
1. Hent webhook-secret på webserveren: `sudo cat /etc/webhook/hooks.json`.
2. Repo → Settings → Webhooks: Payload URL `https://deploy.robotikk.org/hooks/deploy`, secret = verdien over, content type `application/json`, kun `push`-event.
3. Push til main, bekreft webhook-loggen og at siden oppdateres.

### 5. Verifisering og herding
1. `curl -I https://robotikk.org` uten credentials → forvent 401; med `-u bruker:passord` → 200.
2. Test deploy-hook med feil HMAC-secret → forvent avvisning.
3. `ufw status verbose` på 192.168.30.105 → kun port 22 åpen.
4. Valgfritt: fail2ban, SSH kun med nøkkel, unattended-upgrades.

## Beslutninger / Scope
- Kun robotikk.org nå; nye skoleprosjekter kan legges til som nye Public Hostnames i samme tunnel senere.
- Cloudflare Access (Zero Trust identity) valgt bort til fordel for enkel nginx Basic Auth.
- Nginx Proxy Manager (192.168.30.101:81) er bevisst IKKE brukt til dette prosjektet.

