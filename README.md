# robotikk.org

Statisk skoleside (Hugo) for robotikklinja. Innhold i `content/`, oppsett i `hugo.toml`.

## Utvikling

```sh
hugo server -D
```

## Drift

Serveren (192.168.30.105) står bak brannmur uten offentlig IP. En Cloudflare Tunnel
(cloudflared) kjører lokalt på denne maskinen og ruter `robotikk.org` og
`deploy.robotikk.org` til `localhost`. Se `deploy/` for alle server-konfigurasjoner:

- `deploy/setup-server.sh` — kjøres med `sudo` på 192.168.30.105 for å sette opp alt
  (pakker, systembruker, git-klone, webhook-tjeneste, lokal nginx, ufw).
- `deploy/deploy.sh` — kjøres av webhook-tjenesten ved push (git pull + hugo build).
- `deploy/robotikk-local-nginx.conf` — lokal nginx på port 8080, med Basic Auth
  (`auth_basic` + `/etc/nginx/robotikk.htpasswd`).
- `deploy/webhook.service`, `deploy/hooks.json.template` — GitHub-webhook-lytter
  (HMAC-secret genereres lokalt av setup-server.sh, aldri committet).

Se [PLAN.md](PLAN.md) for full status og gjenstående steg.

Push til `main` trigger automatisk ombygging av siden via GitHub-webhooken.
