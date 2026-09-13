# Barcode Shopping

Scan the barcode of an item as you throw away the empty package, and it gets
added to your household's shopping list automatically. Self-hosted,
multi-platform (Android, iPhone, PC), no cloud dependency.

## Status

v1 is deployable and running. See [`plan.md`](plan.md) for the full
architecture and roadmap.

## Repo layout

- `frontend/` — Vue + Vite PWA
- `backend/` — Flask + SQLite API

## Self-hosting

### Server (Docker Compose)

```yaml
services:
  app:
    image: ghcr.io/houbou98-19/barcode-shopping:latest
    pull_policy: always
    ports:
      - "8080:5000"
    environment:
      - ADMIN_PASSWORD=${ADMIN_PASSWORD:-}
    volumes:
      - shopping_data:/data
    networks:
      - barcode-shopping
    restart: unless-stopped

networks:
  barcode-shopping:
    driver: bridge

volumes:
  shopping_data:
```

Save as `docker-compose.yml` and run:

```sh
docker compose up -d
```

The app is then available at `http://<host>:8080`. Since `pull_policy` is
`always`, later updates are just:

```sh
docker compose pull && docker compose up -d
```

(a bare restart reuses whatever image is already cached and won't pick up
a new build).

The database (SQLite) persists in the `shopping_data` named volume, so it
survives container recreation/updates.

**Admin page**: a hidden `/admin` page (no link anywhere in the regular
app) lets you reset a profile's PIN/lockout, delete a profile, or
edit/delete products. It's disabled by default; to enable it, set
`ADMIN_PASSWORD` in a `.env` file next to `docker-compose.yml` (Compose
loads it automatically):

```sh
echo "ADMIN_PASSWORD=<a strong password>" > .env
docker compose up -d
```

**Note:** don't rely on Docker's plain default `bridge` network for
port-publishing — some simplified app-install UIs (e.g. ZimaOS's manual
form) don't run full Compose semantics and default to it unless a network
is explicitly declared, and it's been observed to leave the published port
unreachable from outside the container even though the container itself is
healthy. The `networks:` block above avoids that.

**Reaching it from outside your home network**: recommended is a VPN
(e.g. [Tailscale](https://tailscale.com/)) into your home network — no
app-side configuration needed, the app just behaves as if you're always on
the home network. Direct internet exposure via a reverse proxy
(e.g. Nginx Proxy Manager) with HTTPS is also supported, but TLS,
rate limiting at the edge, and general exposure hardening are your
responsibility as the self-hoster — the app only handles what's listed in
`plan.md` §6.

**If reverse-proxying, disable response buffering for `/api/events`**: the
app pushes realtime list updates over a long-lived Server-Sent Events
connection, but nginx buffers proxied responses by default, which delays
or breaks that stream. In Nginx Proxy Manager, add this under the proxy
host's Advanced tab (adjust `proxy_pass` to your container's actual
address):

```nginx
location /api/events {
    proxy_pass http://<your-container>:5000;
    proxy_buffering off;
    proxy_cache off;
    proxy_read_timeout 3600s;
}
```

### Clients

- **Any browser (PC, Android, iPhone)**: just open `http://<host>:8080` (or
  your domain, if reverse-proxied). It's an installable PWA — Chrome/Edge on
  desktop and Android will offer an "Install app" prompt; on iPhone Safari,
  use Share → "Add to Home Screen".
- **Android app**: a debug APK is built by CI on every push
  (`.github/workflows/android-apk.yml`) and available as a workflow run
  artifact under the repo's Actions tab — no Play Store needed, just
  sideload it. After install, open Settings in the app and set **Server
  URL** to your server's address (e.g. `http://192.168.1.10:8080`) — the
  native app has no browser origin to resolve relative API calls against,
  so this is required for it specifically (optional for the PWA/web
  clients, which default to same-origin).

## License

MIT — see [`LICENSE`](LICENSE).
