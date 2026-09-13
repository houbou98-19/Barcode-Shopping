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
- **iPhone**: installed PWA/webpage, any browser. All iOS browsers (Chrome
  included) are required by Apple to run on the WebKit engine, so there is
  no real Chromium on iPhone — the native `BarcodeDetector` API (Chromium-only)
  is unavailable there regardless of which browser app is used. To keep one
  scanning code path across every browser/platform, the frontend uses the
  [`barcode-detector`](https://www.npmjs.com/package/barcode-detector) ponyfill:
  it exposes the same `BarcodeDetector` interface everywhere, using the native
  implementation where available (desktop/Android Chrome) and a ZXing-WASM
  decoder as a transparent fallback where it isn't (iOS).
- Rationale recap: the original attempt's scanning reliability problem came
  from relying on inconsistent browser camera APIs across platforms. This
  plan solves it with a single ponyfill-backed scan path everywhere, plus a
  native ML Kit path on Android specifically for best-case reliability there.

### 4.2 Backend
- **Python + Flask**
- **SQLite** as the database — zero-config, single-file, trivial to back up
  (copy the file), sufficient for household-scale read/write volume.
- REST API, JSON.

### 4.3 Deployment
- **Docker Compose** as the primary, officially supported self-host method:
  one command spins up backend + DB + frontend.
- `docker-compose.yml` declares its own dedicated bridge network rather than
  relying on Docker's implicit default `bridge` network. Verified on a real
  deployment (ZimaOS): the default `bridge` network's port-publishing NAT
  can end up broken on a host (container healthy internally, `docker ps`
  shows the mapping, but the published port never becomes reachable
  externally) while a dedicated per-project bridge network works
  correctly — this is what `docker compose up` creates automatically by
  default anyway, we just declare it explicitly for clarity/consistency
  across install methods (some simplified app-install UIs, e.g. ZimaOS's
  manual form, don't run real compose semantics and default to plain
  `bridge` unless a network is explicitly specified).

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
  - `id` (PK)
  - `barcode` (indexed, **not unique** — some barcode ranges, e.g. GS1
    restricted circulation numbers used for deli/bakery/private-label
    goods, are only unique per-store, not globally, so two distinct
    products can legitimately share a barcode)
  - `name`
  - `category`
  - `image_path` (nullable, unused until v3 — see v3 additions below)
  - `created_at`
- `shopping_list_items`
  - `id` (PK)
  - `product_id` (FK → `products.id`)
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
  - `token_hash` (PK, SHA-256 hash of an opaque random string — not a
    decodable JWT; the raw token is only ever given to the client, never
    stored, so a leaked DB file alone can't be used to replay a session)
  - `profile_id` (FK)
  - `expires_at` (sliding 1-week expiry, refreshed on each authenticated
    use — short enough to cap exposure from a forgotten/stolen device,
    long enough that a weekly shopping cadence never sees a prompt)
- `lists`
  - `id` (PK)
  - `name`
  - `join_code` (3-digit numeric, **unique when set**; NULL for a
    profile's own personal list — structurally not joinable, rather than
    a flag to check)
  - `created_by_profile_id` (FK → profiles; only the creator can
    force-delete a shared list outright, distinct from any member simply
    leaving it)
  - `created_at`
- `list_memberships`
  - `list_id` (FK → lists)
  - `profile_id` (FK → profiles)
  - `joined_at`
  - *(composite PK on `list_id`+`profile_id`)*
- `shopping_list_items` (supersedes the v2-only `profile_id`-based private
  list from an earlier iteration of this section — superseded before ever
  shipping to end users, per #43):
  - `list_id` (FK → lists) — which list this item is on
  - `added_by_profile_id` (FK → profiles) — who added it, distinct from
    `list_id` once a list can have multiple members (#43)
  - A profile's own personal list is auto-created (and auto-joined)
    alongside the profile itself, so every profile always has somewhere
    to add items without needing a shared list first. A shared list with
    no members left (everyone left, or the last one deleted) is deleted
    along with its items — no orphaned lists linger.

### v3 additions
- `products.image_path` (nullable) added early, in the v1 schema — column
  exists from the start (unset until the photo-capture feature ships) since
  it's a one-line addition and avoids a later migration. The photo-capture
  feature itself (letting a user snap a picture of an item) is still v3
  scope: WebP thumbnail, ~100–128px, ~2–5KB, stored on disk (e.g.
  `/data/product-images/{id}.webp`, keyed by the products.id PK since
  barcode is not unique — see §5 v1).
- **Serving images**: `image_path` is an internal, server-side filesystem
  path — it is never returned by the API or exposed to the frontend as-is
  (a raw disk path means nothing to a browser, and images must not be
  bundled into the frontend build). Instead the backend serves a
  dedicated endpoint, e.g. `GET /api/products/<id>/image`, that reads the
  file from disk at request time and streams it back with the right
  content-type; the frontend always points `<img>` at that deterministic
  URL and falls back to a placeholder on 404 (no image yet). This also
  keeps image storage swappable later (local disk vs. S3-compatible
  bucket) without any frontend change.
- `ha_integrations`
  - `profile_id` (FK)
  - `ha_base_url`
  - `ha_long_lived_token`
  - `ha_todo_entity_id`

## 6. Security model (application-layer only)

Applies regardless of whether the instance sits behind a VPN or is
internet-exposed via reverse proxy — this is what the *app* must own:

- **v1**: IP-based rate limiting on write endpoints (product creation, list
  item creation); input validation/sanitization on product name/category
  (length limits, reject script/HTML injection) since the product table has
  open write with no moderation; all secrets (DB path, any external API
  keys) via environment variables, `.env.example` shipped in repo, nothing
  hardcoded/committed; debug/docs routes disabled or gated in production
  builds.
- **CORS: wildcard (`Access-Control-Allow-Origin: *` on `/api/*`), not
  restricted to a single configured origin** — revised from the original
  single-origin plan once Settings' Server URL feature (see §4.1/§7) made
  that assumption unworkable: the backend must be reachable from whatever
  origin a device points at it (the native app's local pseudo-origin, a
  browser on another device, a dev machine testing against a deployed
  server, etc.), not one fixed frontend origin. This is an acceptable
  tradeoff for v1 specifically because there is no cookie/session-based
  auth yet — wildcard CORS mainly matters for protecting *credentialed*
  cross-origin requests, and v1 has none to protect. **Revisit this when
  v2 profile sessions ship** (see v2 below) — Bearer-token auth (not
  cookies) means CORS still isn't the thing guarding those endpoints, but
  it's the natural point to reassess.
- **v2**: PIN verification with lockout (5 failed attempts → 15 min lock per
  profile); opaque session token issued on successful PIN check, sent as
  Bearer header, required on all write endpoints; sliding 1-week expiry
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
- Two-way sync (checking off in HA reflects back to the app) is v3 scope
  alongside push-only (#36) — originally deferred to avoid
  conflict-resolution complexity, revisited once push-only ships and proves
  stable.

## 8. Roadmap

| Version | Scope |
|---|---|
| v1 | Scanning (Capacitor), shared product DB, single shared list, category sorting/grouping, Flask+SQLite backend, Docker Compose deploy, baseline hardening (IP rate limit, CORS, input validation, env secrets) |
| v2 | Private per-user lists (superseded by multi-list + join codes), profiles, PIN + session tokens |
| v3 | HA push-only + two-way integration, product thumbnail images, optional live product lookup via Open Food Facts API |
| Later / optional | Per-profile rate limiting, offline scan queue + sync, k8s manifests/Helm chart, instance-wide passphrase as extra gate |

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
- **Tickets**: work is tracked as GitHub Issues on the
  [Barcode Shopping project board](https://github.com/users/houbou98-19/projects/4)
  (Todo / In Progress / Done). One issue = one feature or fix.
- **Branching model**: one feature branch per ticket
  (`feature/<issue-number>-<short-slug>`), branched from `dev`, PR'd back
  into `dev` with `Closes #<issue-number>` so the issue auto-closes on
  merge. Once `dev` is stable/tested, merge `dev` → `main`. `main` is
  always the deployable state.
- `main` is what triggers release CI/CD (below) — nothing should land there
  directly; everything flows feature branch → `dev` → `main`.

## 10. CI/CD

- **Server image** (`.github/workflows/docker-publish.yml`): builds the
  single combined Docker image (multi-stage: Vue frontend build → served as
  static files by the Flask backend under gunicorn — see §4.3) and pushes it
  to GHCR on **every push, to any branch** — not just `main`. Always tagged
  `:latest` (whatever was built most recently, regardless of branch) plus
  the commit SHA (for pinning/rollback to a specific build). This
  intentionally does not follow the feature-branch → `dev` → `main` gate:
  `:latest` is a moving "most recent build" tag for convenience, not a
  stability guarantee — pin a SHA tag manually for anything that needs to
  stay put.
  - **Versioned release tags**: a root-level `VERSION` file (e.g. `1.2.0`)
    is bumped by hand as part of the `dev` → `main` merge for a release.
    On push to `main` specifically, the workflow additionally tags the
    image `:<version>` (e.g. `:1.2.0`) and a floating `:<major>.<minor>`
    (e.g. `:1.2`) alongside `:latest`/`:sha`. This gives a stable pin
    (`:1.2`) distinct from the constantly-moving `:latest`, so a deployed
    instance (e.g. ZimaOS) can switch its image tag to `:latest` to try a
    feature branch, then back to `:1.2` to return to the last stable
    release, without hunting for a SHA. Versioning follows semver against
    the roadmap (§8): v2 completion = `1.2.0`; feature branches merged
    toward v3 bump patch/minor as needed; `1.3.0` marks v3 complete.
  - Android APK build is a separate workflow
    (`.github/workflows/android-apk.yml`, issue #9) — no `paths:`
    filtering between the two, since they build independently regardless.
- **Android APK** (`.github/workflows/android-apk.yml`): on every push, to
  any branch, builds the frontend, runs `npx cap sync android`, and
  assembles a debug APK (`./gradlew assembleDebug`) — debug-signed, so no
  release keystore/signing secrets to manage. The APK is always uploaded
  as a workflow run artifact (`gh run download`, then serve over LAN for
  phone install — the existing sideload flow for testing feature
  branches). On push to `main` specifically, it additionally reads the
  root `VERSION` file (the same one used for the Docker version tags) and
  creates a GitHub Release tagged `v<VERSION>` with the APK attached as a
  downloadable release asset and auto-generated release notes — so the
  same `dev` → `main` merge that cuts a stable Docker image tag (e.g.
  `:1.2`) also produces the matching downloadable stable APK.
- **Deployment target**: `docker-compose.yml` runs the image as a container
  on **ZimaOS**, `pull_policy: always` so a normal `docker compose pull &&
  up -d` (not a bare restart, which reuses the cached image) always grabs
  whatever `:latest` currently is. Reverse-proxied through **Nginx Proxy
  Manager** (handles TLS/domain routing at the infra layer — outside this
  app's scope per §6). SQLite persists on a named Docker volume mounted at
  `/data`.
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
- v2 profiles: generate each profile's avatar as a barcode encoding their
  name, same technique as the app favicon (ASCII code of each letter as a
  3-digit triplet, rendered as UPC-A-style bars). Placeholder generic
  barcode logo stays in the header until profiles exist.