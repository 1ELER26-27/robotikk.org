# Plan: robotikk.org via Cloudflare Tunnel

## Status
- [x] Fase 3 — webserver (192.168.30.105): pakker, `robotikk`-bruker, lokal nginx :8080, webhook :9000, ufw. Kjørt via `deploy/setup-server.sh`, verifisert OK.
- [x] Fase 4 (delvis) — repo opprettet og pushet: https://github.com/1ELER26-27/robotikk.org
- [ ] Fase 1 — Cloudflare Tunnel + DNS (på nginx-VM-en, ikke gjort ennå)
- [ ] Fase 2 — edge-nginx + Basic Auth (på nginx-VM-en, ikke gjort ennå)
- [ ] Fase 4 (resten) — legg webhook-secret inn i GitHub repo settings
- [ ] Fase 5 — verifisering fra internett + herding

## Kontekst
- Domene robotikk.org, DNS/Cloudflare finnes allerede.
- Denne maskinen (hostname `webserver`, 192.168.30.105/23) = Ubuntu 24.04.5 LTS LXC-container på Proxmox (192.168.30.101).
- Egen nginx kjører på en ANNEN VM/container på samme Proxmox-vert (ikke denne maskinen).
- Ingen offentlig IP / brannmur blokkerer innkommende trafikk.

## Bekreftede valg
1. Eksponering: **Cloudflare Tunnel** (cloudflared) — ingen porter åpnes i brannmuren.
2. Autentisering foran siden: **Nginx Basic Auth** (htpasswd, brukernavn+passord).
3. Innhold: **Statisk nettside (Hugo)**.
4. Utrulling fra GitHub: **Webhook + pull-script** (adnanh/webhook), ikke self-hosted runner.
5. Reverse proxy: bruk **eksisterende nginx-VM** på Proxmox-verten (ikke denne containeren).
6. GitHub-repo: offentlig, i organisasjonen https://github.com/1ELER26-27/ (`robotikk.org`-repoet).
7. Deploy-hook skilles ut på eget hostname `deploy.robotikk.org`, beskyttet med GitHub sin HMAC-signatur i stedet for basic auth.

## Arkitektur
```
Internet -> Cloudflare (DNS proxied, TLS) -> Cloudflare Tunnel (cloudflared på nginx-VM)
   -> nginx (nginx-VM)
        - robotikk.org        : auth_basic (htpasswd) -> proxy_pass http://192.168.30.105:8080
        - deploy.robotikk.org : (ingen basic auth)      -> proxy_pass http://192.168.30.105:9000
   -> webserver LXC (192.168.30.105, denne maskinen) [FERDIG]
        - lokal nginx :8080 serverer bygget Hugo-output (kun LAN, ingen auth nødvendig)
        - webhook :9000 (adnanh/webhook) verifiserer GitHub HMAC-secret, kjører deploy.sh
        - deploy.sh: git pull i /opt/robotikk-site -> hugo build til temp-dir -> atomisk mv -> reload nginx
```

## Gjenstående steg

### Fase 1 – Cloudflare Tunnel + DNS

> **Merk:** Det finnes en gammel, død tunnel kalt `robotikk` fra tidligere (tunnel-id
> `405db25f-4fa2-4a8d-91b3-61ec78806e5c`, koblet til en server som ikke finnes lenger).
> Cloudflare tilbyr å "migrere" denne, men det er **irreversibelt** og vi vet ikke om den
> inneholder ingress-regler for `bambulab.robotikk.org` (som er i aktiv bruk og IKKE skal
> røres). Beslutning: la den gamle tunnelen ligge urørt, opprett en **ny, separat** tunnel
> for dette prosjektet i stedet. Den gamle kan evt. slettes senere når det er bekreftet at
> ingenting bruker den.

**A. I Cloudflare dashboard:**
1. Logg inn på Cloudflare, velg robotikk.org-kontoen.
2. Åpne "Zero Trust". Fullfør onboarding første gang (velg et team-navn) — gratisplan holder.
3. Zero Trust → Networks → Tunnels → "Create a tunnel" → connector-type "Cloudflared" → navn: `robotikk-classroom` → Save. (IKKE trykk "Configure"/"Start migration" på den gamle `robotikk`-tunnelen.)
4. Noter install-kommandoen med token som vises (brukes i steg B2).
5. Under "Public Hostnames", legg til:
   - `robotikk.org` → HTTP → `localhost:80`
   - `deploy.robotikk.org` → HTTP → `192.168.30.105:9000`
6. Lagre. Bekreft under DNS-fanen at CNAME for begge peker til `<tunnel-id>.cfargotunnel.com` (proxied).

**B. På nginx-VM-en (sudo):**
1. Installer cloudflared fra Cloudflares apt-repo (`pkg.cloudflare.com`).
2. Kjør install-kommandoen fra A4 (`cloudflared service install <TOKEN>`).
3. `systemctl status cloudflared` → "active (running)".
4. Bekreft "Healthy"/"Connected" i dashboardet.

**C. Delvis test:** `curl -I https://robotikk.org` fra utenfor LAN → forvent 502/503 (ikke DNS-feil/timeout).

### Fase 2 – nginx reverse proxy + Basic Auth (på nginx-VM)
1. `htpasswd -c -B /etc/nginx/robotikk.htpasswd <brukernavn>`.
2. Kopiér [deploy/edge-nginx-robotikk.conf](deploy/edge-nginx-robotikk.conf) dit som utgangspunkt.
3. `nginx -t && systemctl reload nginx`.

### Fase 4 – GitHub-integrasjon (resten)
1. Hent webhook-secret på webserveren: `sudo cat /etc/webhook/hooks.json`.
2. Repo → Settings → Webhooks: Payload URL `https://deploy.robotikk.org/hooks/deploy`, secret = verdien over, content type `application/json`, kun `push`-event.
3. Push til main, bekreft webhook-loggen og at siden oppdateres.

### Fase 5 – Verifisering og herding
1. `curl -I https://robotikk.org` uten credentials → forvent 401; med `-u bruker:passord` → 200.
2. Test deploy-hook med feil HMAC-secret → forvent avvisning.
3. `ufw status verbose` på 192.168.30.105 → kun port 22 + 8080/9000 (LAN) åpne. (Allerede verifisert OK.)
4. Valgfritt: fail2ban, SSH kun med nøkkel, unattended-upgrades.

## Beslutninger / Scope
- Kun robotikk.org nå; arkitekturen gjør det enkelt å legge til flere skoleprosjekter senere.
- Cloudflare Access (Zero Trust identity) valgt bort til fordel for enkel nginx Basic Auth.
- Intern trafikk (nginx-VM <-> 192.168.30.105) går ukryptert på LAN — akseptabelt for klasserom, ikke i scope å legge til intern TLS nå.
