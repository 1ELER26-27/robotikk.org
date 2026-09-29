# robotikk.org

Statisk skoleside (Hugo) for robotikklinja. Innhold i `content/`, oppsett i `hugo.toml`.

## Utvikling

```sh
hugo server -D
```

## Drift

Serveren (192.168.30.105) står bak brannmur uten offentlig IP. Trafikk kommer inn via en
Cloudflare Tunnel til en separat nginx-VM på samme Proxmox-vert, som gjør basic-auth og
reverse-proxyer videre hit. Se `deploy/` for alle server-konfigurasjoner:

- `deploy/setup-server.sh` — kjøres med `sudo` på 192.168.30.105 for å sette opp alt
  (pakker, systembruker, git-klone, webhook-tjeneste, lokal nginx, ufw).
- `deploy/deploy.sh` — kjøres av webhook-tjenesten ved push (git pull + hugo build).
- `deploy/edge-nginx-robotikk.conf` — referansekonfig for den ANDRE nginx-VM-en
  (basic auth + reverse proxy hit).
- `deploy/webhook.service`, `deploy/hooks.json.template` — GitHub-webhook-lytter
  (HMAC-secret genereres lokalt av setup-server.sh, aldri committet).

Push til `main` trigger automatisk ombygging av siden via GitHub-webhooken.
