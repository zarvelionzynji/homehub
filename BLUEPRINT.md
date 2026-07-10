# HomeHub Project Blueprint

**Version:** v1.2.0  
**Last Updated:** 2026-07-11

This document maps the architecture and main modules of the HomeHub project, helping developers understand the overall feature structure.

## System Architecture
HomeHub is built on the following technology stack:
- **Backend**: Python (Flask), using `Flask-SQLAlchemy` for database interaction.
- **Database**: SQLite (stored in `data/app.db`).
- **Frontend**: Vanilla JavaScript, Tailwind CSS (built via `npm run build:css`), HTML + Jinja2 Templates. Recently updated with high-standard UI/UX refactoring (A11y, 44px touch targets, GPU-friendly transitions, reduced-motion, Font Awesome icon standardization).
- **Deployment**: Docker / Docker Compose & Github Actions (GHCR).

## Feature Modules

### 1. Core
- **Config Loader**: `app/config.py` — Loads main configuration from `config.yml`. Manages feature toggles and `family_members`.
- **Database Models**: `app/models.py` — Stores table schemas for Notes, Chores, Shopping, Expenses, etc.
- **Main Dashboard**: `app/blueprints/dashboard.py` — Web control center that aggregates widgets like calendar, who's home, and personal status.

### 2. Family Functionality Modules
- **Shopping List**: Located at `app/blueprints/shopping.py`. Similar to Chores, but specifically tracks grocery items with category tags and purchase history.
- **Quick Links**: Located at `app/blueprints/quick_links.py`. Interactive bookmark manager with drag-and-drop (Sortable.js), SVG CDN icons, and auto-favicon. Links and categories are flexibly ordered (`order_index` stored in SQLite) and displayed on the main dashboard as a mini Heimdall/Homarr-style grid.
- **Expense Tracker**: Located at `app/blueprints/expenses.py`. Tracks expenses with monthly/yearly filters, plus paid/unpaid billing for recurring bills. Has a dedicated management page for recurring rules at `/expenses/recurring` with safe Edit Strategies to protect payment history.
- **Shared Notes & Cloud**: Manages a shared file storage directory and sticky notes.
- **Calendar Reminders**: Manages one-time and recurring schedule reminders.
- **Media Downloader & PDFs**: Located at `app/blueprints/media_pdfs.py`. Video/audio download utility using `yt-dlp` and PDF converter. Tightly integrated with PWA via **Web Share Target API**, allowing mobile users to share download links directly to HomeHub. Includes **file existence validation** — backend checks disk before serving files, API returns `file_exists` flag, UI shows "Not available" status if the file is missing.
   - **Re-download**: "Redownload" button on completed media items, using saved format/quality options. Old files auto-deleted on successful re-download. Powered by `_download_worker()` (module-level function) and `_build_ytdlp_cmd()` to avoid code duplication between `media()` and `redownload_media()` routes.
   - **PWA Web Share Target** — Key feature allowing Android users to share links (e.g., from YouTube) directly to Media Downloader via OS share sheet. Powered by manifest `share_target` and a dedicated Service Worker fetch handler for `/media/share`.

### 2a. PWA Configuration (Progressive Web App)
HomeHub PWA is configured through two dynamic endpoints in `app/blueprints/__init__.py`:
- **`/manifest.webmanifest`** — Dynamic JSON manifest including: `name`, `short_name`, `icons` (192x192 + 512x512 with `purpose: "any maskable"`), `display: standalone`, `display_override`, `share_target` for Web Share Target API, `categories`, `description`, and `launch_handler`.
- **`/sw.js`** — Service Worker with offline-first strategy: network-first for navigation, stale-while-revalidate for static assets, bypass cache for `/api/*` and `/media/share`. PWA icons pre-cached on install.

### Share Target Infrastructure Requirements
1. **HTTPS** — Web Share Target API only works in secure context. Server must be accessed via HTTPS.
2. **Maskable icons** — Android 12+ requires icons with `purpose: "maskable"` for adaptive icons.
3. **Full install** — PWA must be installed via the Chrome install prompt (not just "Add to Home screen").

### HTTPS Setup Guide
HTTPS access can be configured via:
- **Caddy** (auto SSL): Add a Caddy service to compose.yml with `homehub.domain.com { reverse_proxy homehub:5000 }`.
- **Nginx + certbot**: Reverse proxy with SSL termination.
- **Tailscale Funnel**: Automatic HTTPS cert via `*.ts.net` — install Tailscale on server + Android, access via `https://<machine>.ts.net:5000`.

### 3. External API Extensions
- **AI Agent Integration (Universal Router)**: `app/blueprints/ai_agent.py` — Provides a "no-UI" interface for third-party AI assistants via `POST /api/ai/execute` and schema documentation via `GET /api/ai/schema`. This module allows AI agents to manage home status, read/modify Shared Notes, Chores, Shopping List, Quick Links, Settings (`config.yml`), and the Expense Tracker module with Base64 receipt upload support.
- **RESTful Config API**: `app/blueprints/config_api.py` — Allows external systems to modify application preferences and manage accounts in `config.yml` programmatically without breaking the file's comment structure.
- **Security**: All extension API routes are strictly protected using the `Authorization: Bearer <ai_agent_token>` mechanism.

### 4. Internationalization (i18n)
- **Core Engine**: `app/i18n.py` — Lightweight dictionary-based translation system without Flask-Babel. Supports EN (English) and ID (Indonesian) with automatic locale detection via session, cookie, or browser Accept-Language header.
- **`_()` Function**: Available in all Jinja2 templates (`{{ _('text') }}`) and Python blueprints (`from ..i18n import _`).
- **Language Switcher**: EN/ID toggle in the application header, route `/lang/<code>` for persistent language changes.
- **Weather i18n**: Weather data translations (WMO codes, labels, relative time) injected into JavaScript via `<script id="weatherI18n">` JSON.
- **Navbar Order Sync**: Navbar order stored in the database (`app_setting`) and restored across devices via `GET /settings/navbar-order/<user>`.

## Directory Structure
```text
homehub/
├── app/
│   ├── blueprints/       # Controller folder for each feature
│   ├── __init__.py       # Factory pattern for Flask setup
│   ├── config.py         # YAML Parser
│   └── models.py         # SQLAlchemy Schema
├── data/                 # Local SQLite database storage
├── static/               # Frontend assets (CSS/JS)
├── templates/            # HTML templates
├── CHANGELOG.md          # Feature release log
├── BLUEPRINT.md          # This document
└── config.yml            # Application settings center
```
