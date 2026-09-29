#!/usr/bin/env bash
# Setter opp DENNE maskinen (192.168.30.105) til å bygge og serve robotikk.org.
# Kjør med: sudo bash deploy/setup-server.sh
set -euo pipefail

if [ "$(id -u)" -ne 0 ]; then
    echo "Må kjøres som root (sudo bash deploy/setup-server.sh)" >&2
    exit 1
fi

REPO_URL="https://github.com/1ELER26-27/robotikk.org.git"
REPO_DIR="/opt/robotikk-site"
SERVICE_USER="robotikk"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "==> Installerer pakker (git, hugo, nginx, webhook, ufw, htpasswd)"
apt-get update
apt-get install -y git hugo nginx webhook ufw apache2-utils

echo "==> Oppretter systembruker '$SERVICE_USER'"
if ! id "$SERVICE_USER" &>/dev/null; then
    useradd --system --home-dir "$REPO_DIR" --shell /usr/sbin/nologin "$SERVICE_USER"
fi
mkdir -p "$REPO_DIR"
chown "$SERVICE_USER:$SERVICE_USER" "$REPO_DIR"

echo "==> Kloner/oppdaterer repo i $REPO_DIR"
if [ ! -d "$REPO_DIR/.git" ]; then
    sudo -u "$SERVICE_USER" git clone "$REPO_URL" "$REPO_DIR"
fi
chmod +x "$REPO_DIR/deploy/deploy.sh"

echo "==> Genererer webhook-secret og hooks.json (holdes utenfor git-repoet)"
mkdir -p /etc/webhook
if [ ! -f /etc/webhook/hooks.json ]; then
    WEBHOOK_SECRET="$(openssl rand -hex 32)"
    sed "s/__WEBHOOK_SECRET__/${WEBHOOK_SECRET}/" "$REPO_DIR/deploy/hooks.json.template" > /etc/webhook/hooks.json
    chown root:"$SERVICE_USER" /etc/webhook/hooks.json
    chmod 640 /etc/webhook/hooks.json
    echo ""
    echo "############################################################"
    echo "# WEBHOOK SECRET (lim inn i GitHub repo -> Settings -> Webhooks):"
    echo "# $WEBHOOK_SECRET"
    echo "# Denne vises kun én gang her. Den ligger også i /etc/webhook/hooks.json"
    echo "############################################################"
    echo ""
else
    echo "/etc/webhook/hooks.json finnes allerede, lar den stå urørt."
fi

echo "==> Installerer systemd-tjeneste for webhook"
cp "$REPO_DIR/deploy/webhook.service" /etc/systemd/system/webhook.service
systemctl daemon-reload
systemctl enable --now webhook

echo "==> Konfigurerer lokal nginx (port 8080, Basic Auth)"
# Tom htpasswd-fil = alle avvises (fail closed) inntil en bruker legges til manuelt.
[ -f /etc/nginx/robotikk.htpasswd ] || install -m 640 -o root -g www-data /dev/null /etc/nginx/robotikk.htpasswd
cp "$REPO_DIR/deploy/robotikk-local-nginx.conf" /etc/nginx/sites-available/robotikk-local
ln -sf /etc/nginx/sites-available/robotikk-local /etc/nginx/sites-enabled/robotikk-local
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl enable --now nginx
systemctl reload nginx

echo "==> Konfigurerer ufw (SSH må tillates FØR ufw enable for å unngå innlåsing)"
# cloudflared kjører lokalt og når nginx/webhook via loopback, så 8080/9000 trenger ikke åpnes eksternt.
ufw allow 22/tcp
ufw default deny incoming
ufw default allow outgoing
ufw --force enable
ufw status verbose

echo "==> Første bygg av siden"
sudo -u "$SERVICE_USER" "$REPO_DIR/deploy/deploy.sh"

cat <<EOF

==============================================================
Ferdig på denne maskinen. Gjenstår (se PLAN.md):
  1. Lag en ekte bruker i htpasswd-filen (tom fil = alle avvises nå):
       sudo htpasswd -B /etc/nginx/robotikk.htpasswd <brukernavn>
  2. Cloudflare Tunnel Public Hostnames skal peke hit (samme maskin):
       robotikk.org        -> http://localhost:8080
       deploy.robotikk.org -> http://localhost:9000
  3. Legg webhook-secreten (over) inn i GitHub -> repo -> Settings ->
     Webhooks -> Payload URL https://deploy.robotikk.org/hooks/deploy
==============================================================
EOF
