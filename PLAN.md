# Plan: robotikk.org via Cloudflare Tunnel

## Status — rammeverket er i praksis ferdig ✅
- [x] Webserver (192.168.30.105): pakker, `robotikk`-bruker, lokal nginx :8080, webhook :9000, ufw.
- [x] Repo opprettet og pushet: https://github.com/1ELER26-27/robotikk.org
- [x] Cloudflare Tunnel installert og kjører **på webserveren selv** (se "Arkitekturendring" under).
- [x] Cloudflare Public Hostnames satt opp: `robotikk.org` → `localhost:8080`, `deploy.robotikk.org` → `localhost:9000`.
- [x] Basic Auth aktivert (bruker `elev` opprettet i htpasswd) — **bekreftet fungerende fra internett** 🎉
- [x] ufw strammet inn — kun port 22 (SSH) åpen eksternt.
- [ ] **Gjenstår:** legg webhook-secret inn i GitHub repo → Settings → Webhooks (se pkt. 1 under)
- [ ] **Gjenstår:** test hele deploy-kjeden (push → automatisk ombygging)
- [ ] Valgfritt: opprydding/herding (se "Gjenstående steg" pkt. 2-4)

## Gjenstående steg (neste økt)

### 1. Koble GitHub-webhooken til deploy-endepunktet
```sh
sudo cat /etc/webhook/hooks.json   # finn verdien i "secret"-feltet
```
Gå til [github.com/1ELER26-27/robotikk.org/settings/hooks](https://github.com/1ELER26-27/robotikk.org/settings/hooks) → **Add webhook**:
- Payload URL: `https://deploy.robotikk.org/hooks/deploy`
- Content type: `application/json`
- Secret: verdien fra kommandoen over
- Events: kun **push**

### 2. Test hele kjeden
Gjør en liten endring i en fil under `content/`, commit + push til `main`. Sjekk at siden
oppdaterer seg automatisk (kan ta noen sekunder). Feilsøk med:
```sh
sudo journalctl -u webhook -f
```

### 3. Valgfri opprydding
- Vurder å slette den gamle, døde tunnelen `robotikk` (id `405db25f-4fa2-4a8d-91b3-61ec78806e5c`)
  i Cloudflare-dashboardet — bekreft først at `bambulab.robotikk.org` ikke bruker den (den
  dekkes av wildcard `*.robotikk.org`, så bør være trygt).
- Legg gjerne til flere brukere i htpasswd om flere enn `elev` skal ha tilgang:
  `sudo htpasswd -B /etc/nginx/robotikk.htpasswd <nytt-brukernavn>`.

### 4. Valgfri herding (ikke kritisk, men anbefalt før produksjon i klasserommet)
- fail2ban for gjentatte feilede Basic Auth-forsøk.
- SSH kun med nøkkel (`PasswordAuthentication no` i `/etc/ssh/sshd_config`).
- `unattended-upgrades` for automatiske sikkerhetsoppdateringer.

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

## Historikk / merknader
> **Om gammel tunnel:** Det finnes en gammel, død tunnel kalt `robotikk` fra tidligere
> (tunnel-id `405db25f-4fa2-4a8d-91b3-61ec78806e5c`). Den er bevisst IKKE migrert/rørt —
> vi opprettet en ny, separat tunnel i stedet, for å unngå enhver risiko for
> `bambulab.robotikk.org`. Kan slettes senere, se "Gjenstående steg" pkt. 3 øverst i filen.

## Beslutninger / Scope
- Kun robotikk.org nå; nye skoleprosjekter kan legges til som nye Public Hostnames i samme tunnel senere.
- Cloudflare Access (Zero Trust identity) valgt bort til fordel for enkel nginx Basic Auth.
- Nginx Proxy Manager (192.168.30.101:81) er bevisst IKKE brukt til dette prosjektet.

