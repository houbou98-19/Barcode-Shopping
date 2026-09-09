# Barcode Shopping — Project Plan

## 1. Concept

Scan the barcode of an item as you throw away the empty package, and it gets added
to your household's shopping list automatically. Self-hosted, multi-platform
(Android, iPhone, PC), no cloud dependency.

**Scope note**: this document covers architecture, local development workflow,
branching, and CI/CD for *building* this project. End-user self-hosting
instructions (how someone else deploys their own instance) belong in
`README.md`, not here.

## 2. Prior attempt (context)

An earlier attempt (~2 years old, scaffolding only, no real logic committed)
used two separate repos, `Barcode-Shopping-Web` (React + Vite) and
`Barcode-Shopping-Backend` (Python/Flask). Both were empty scaffolding with
nothing worth preserving, so this rebuild started fresh in a single monorepo,
[`Barcode-Shopping`](https://github.com/houbou98-19/Barcode-Shopping) — see
§9 for the reasoning and the resulting repo layout.

Known issue from that attempt: barcode scanning via the browser camera API was
unreliable, especially on iOS Safari. This plan addresses that directly (see §4).

## 3. Non-goals

- Not a multi-tenant SaaS. Each household runs its own isolated instance.
- No full user-auth system (no passwords, email verification, OAuth). Identity is
  handled via lightweight profiles + PIN (v2), not account infrastructure.
- No moderation workflow for the shared product database — barcode accuracy is
  trusted (private, self-hosted, small user base).
- No built-in reverse proxy / TLS / VPN setup — that's the self-hoster's
  infrastructure choice. We only document it as an option.

## 4. Architecture

### 4.1 Frontend
- **Vue + Vite**, built as a single PWA, talking to the Flask JSON API for all
  CRUD (list items, products, scans). Chosen over React (steep learning curve,
  not needed here) and over plain vanilla JS (reactivity reduces DOM-sync bugs
  as screens grow: list, scan, categories, later profiles/images/HA settings).
- **One codebase, three ways of running it:**
  - **Plain webpage (any device, Chrome/desktop/etc.)**: the Vite build served
    directly — no wrapper needed.
  - **Installable PWA (`vite-plugin-pwa`, manifest + service worker)**: gives
    a real "Install app" prompt on Android/desktop Chrome, and "Add to Home
    Screen" on iPhone Safari. Same build, zero extra platform code.
  - **Android APK via Capacitor**: the same Vue/Vite build output bundled
    *inside* the APK (assets ship on-device, not loaded from a remote URL) —
    the app shell loads instantly and only `fetch()` calls for real CRUD touch
    the server. Gets the native `@capacitor-mlkit/barcode-scanning` plugin
    (Google ML Kit) for best-case scanning reliability. Free to build and
    sideload, no Play Store needed.
- **iPhone**: Chrome webpage since safari doesnt natively support barcodedetecion.
- Rationale recap: the original attempt's scanning reliability problem came
  from relying on inconsistent browser camera APIs across platforms. This
  plan solves it natively where it's free and easy (Android), and mitigates
  it where native isn't free (iOS).

### 4.2 Backend
- **Python + Flask**
- **SQLite** as the database — zero-config, single-file, trivial to back up
  (copy the file), sufficient for household-scale read/write volume.
- REST API, JSON.

### 4.3 Deployment
- **Docker Compose** as the primary, officially supported self-host method:
  one command spins up backend + DB + frontend.

### 4.4 Network access (documented, not built)
- Recommended: VPN into home network (e.g. Tailscale/WireGuard) — zero app-side
  changes needed, app behaves as if always on home network.
- Also supported: direct internet exposure via reverse proxy (e.g. nginx) with
  HTTPS. This is the self-hoster's responsibility to configure; we only note
  it as a supported/expected deployment mode (rate limiting, TLS, fail2ban,
  etc. are the hoster's job, not app code) — except where the *app itself*
  needs to defend itself regardless of what's in front of it (see §6).

## 5. Data model

### v1
- `products`
  - `barcode` (PK)
  - `name`
  - `category`
  - `created_at`
- `shopping_list_items`
  - `id` (PK)
  - `product_id` (FK → products)
  - `quantity`
  - `checked` (bool)
  - `added_at`
  - *(single shared list — no user reference yet in v1)*

### v2 additions
- `profiles`
  - `id` (PK)
  - `name`
  - `pin_hash`
  - `failed_attempts`
  - `locked_until`
- `sessions`
  - `token` (PK, opaque random string — not a decodable JWT)
  - `profile_id` (FK)
  - `expires_at` (sliding 30-day expiry, refreshed on each authenticated use)
- `shopping_list_items` gains:
  - `profile_id` (FK → profiles) — list becomes per-user private
  - `added_by_profile_id` (FK → profiles)

### v3 additions
- `products` gains:
  - `image_path` (nullable) — WebP thumbnail, ~100–128px, ~2–5KB, stored on
    disk (e.g. `/data/product-images/{barcode}.webp}`), referenced by path,
    not stored as a DB blob.
- `ha_integrations`
  - `profile_id` (FK)
  - `ha_base_url`
  - `ha_long_lived_token`
  - `ha_todo_entity_id`

## 6. Security model (application-layer only)

Applies regardless of whether the instance sits behind a VPN or is
internet-exposed via reverse proxy — this is what the *app* must own:

- **v1**: IP-based rate limiting on write endpoints (product creation, list
  item creation); strict CORS (only the configured frontend origin, not `*`);
  input validation/sanitization on product name/category (length limits,
  reject script/HTML injection) since the product table has open write with
  no moderation; all secrets (DB path, any external API keys) via environment
  variables, `.env.example` shipped in repo, nothing hardcoded/committed;
  debug/docs routes disabled or gated in production builds.
- **v2**: PIN verification with lockout (5 failed attempts → 15 min lock per
  profile); opaque session token issued on successful PIN check, sent as
  Bearer header, required on all write endpoints; sliding 30-day expiry
  (refreshed on each successful use); per-profile rate limiting on
  scan/add-item endpoints (e.g. 30 requests/minute) as defense-in-depth on
  top of IP-based limiting.
- Explicitly **not** in app scope: TLS/certificates, reverse proxy config,
  fail2ban, VPN setup. Documented in README as the self-hoster's
  responsibility, with Tailscale suggested as the easiest safe default.

## 7. Home Assistant integration (v3)

- **Push-only** sync: app → HA. When a list item is added/checked in the app,
  the backend calls HA's `todo.*` service (REST/WebSocket API) to
  add/complete the corresponding item on the user's HA `todo` entity.
- Per-profile opt-in: each profile stores their own HA base URL, long-lived
  token, and target `todo` entity ID (see `ha_integrations` table). Not a
  hard dependency for using the app.
- Two-way sync (checking off in HA reflects back to the app) considered but
  deferred — push-only avoids conflict-resolution complexity for v1 of this
  feature.

## 8. Roadmap

| Version | Scope |
|---|---|
| v1 | Scanning (Capacitor), shared product DB, single shared list, category sorting/grouping, Flask+SQLite backend, Docker Compose deploy, baseline hardening (IP rate limit, CORS, input validation, env secrets) |
| v2 | Private per-user lists, profiles, PIN + session tokens, per-profile rate limiting |
| v3 | HA push-only integration, product thumbnail images |
| Later / optional | Offline scan queue + sync, k8s manifests/Helm chart, two-way HA sync, instance-wide passphrase as extra gate |

## 9. Git workflow

- **Single monorepo**: [`Barcode-Shopping`](https://github.com/houbou98-19/Barcode-Shopping)
  holds frontend, backend, and deployment config together, rather than
  separate `-web`/`-backend` repos as in the prior attempt. This is the
  common pattern for self-hosted apps at this scale (Immich, Paperless-ngx,
  Homebox, Actual Budget, etc.) — a monorepo keeps a paired frontend/backend
  change (e.g. an API contract update) as one atomic PR instead of a
  coordinated cross-repo dance, and independent versioning/access-control
  per component isn't needed here. CI/CD still produces separate build
  artifacts (APK, Docker image) from the one repo — see §10.
- Repo layout: `frontend/` (Vue + Vite), `backend/` (Flask + SQLite),
  `docker-compose.yml` at the root, plus `README.md`, `LICENSE`, `plan.md`.
- **Branching model**: one feature branch per feature (`feature/<name>`),
  branched from `dev`, PR'd back into `dev`. Once `dev` is stable/tested,
  merge `dev` → `main`. `main` is always the deployable state.
- `main` is what triggers release CI/CD (below) — nothing should land there
  directly; everything flows feature branch → `dev` → `main`.

## 10. CI/CD

- Trigger: push/merge to `main`.
- Two separate GitHub Actions workflows, each scoped with `paths:` filters to
  its own directory (`frontend/**` or `backend/**` + shared root config) so a
  backend-only change doesn't rebuild the APK and vice versa:
  - **Android APK**: runs the Capacitor Android build and produces a signed
    APK as a downloadable release artifact — pull it onto the phone directly,
    no Play Store involved.
  - **Server image**: builds and publishes a Docker image for the Flask
    backend (+ frontend static assets it serves for the web/PWA path).
- **Deployment target**: the published Docker image runs as a container on
  **ZimaOS**, reverse-proxied through **Nginx Proxy Manager** (handles
  TLS/domain routing at the infra layer — outside this app's scope per §6).
- iOS: no CI/CD build artifact for now, since there's no App Store/TestFlight
  distribution in this plan — the iPhone path is the installed PWA served
  directly from the running backend, so it needs no separate build step.

## 11. License

**MIT License.** Matches the requirement exactly: anyone can clone, modify,
and reuse the code (including commercially) as long as the original copyright
notice and license text are retained in copies/substantial portions — i.e.
proper credit to the original work stays attached. No further restriction is
imposed on derivatives.
- Add a standard `LICENSE` file (MIT text, your name + year) at the repo root.
- Mention it briefly in `README.md` alongside setup instructions.
- (Noted alternative if patent-grant language is ever wanted: Apache 2.0 —
  same attribution spirit, adds explicit patent terms. MIT is sufficient for
  this project's needs.)

## 12. Open items to revisit later
- Whether to bootstrap the `products` table from a public barcode API (e.g.
  Open Food Facts) to seed data and images instead of starting empty.
- Whether v1's single shared list should get a minimal "who added this" text
  field (free-text name, not a real profile) as a cheap stopgap before v2's
  full profile system — optional, not required.