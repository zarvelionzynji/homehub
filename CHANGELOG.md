# Changelog

All significant changes to the HomeHub project are recorded in this file.

## [v1.2.0] - 2026-07-11

### Added
- **i18n Internationalization (EN/ID)**: Lightweight dictionary-based translation system for English and Indonesian. No Flask-Babel or .po/.mo files required. Includes:
  - **Core engine** (`app/i18n.py`) — `I18n` class, `_()` helper, locale detection via session/cookie/browser Accept-Language.
  - **300+ translations** — all 17 UI templates, flash messages in 9 blueprints, weather data, and WMO weather codes.
  - **Language switcher** — EN/ID toggle in the header, always visible before and after login.
  - **Weather widget i18n** — translated weather codes, labels, and relative time in JS via JSON injection.
- **Navbar order cross-device sync**: Navbar order is now saved to the server (`app_setting` table) and automatically restored across devices. Client fetches via `GET /settings/navbar-order/<user>` with localStorage fallback.

### Fixed
- **Nested quote syntax error** in `quick_links.html` — Jinja2 `_("...")` inside `onsubmit` fixed with `{% set %}`
- **Nested quote syntax error** in `index.html` — `_("Today's Forecast")` fixed with `{% set %}`
- **Mobile header compact** — single-row header on mobile: Menu, EN/ID, welcome, user dropdown with proportional sizing
- **Welcome message comma spacing** — fixed `Welcome,User!` to `Welcome, User!`
- **Recurring page heading mobile** — headings reduced on mobile (`text-xl md:text-3xl`)

## [v1.1.0] - 2026-07-06

### Added
- **Re-download Media**: "Redownload" button on completed media items. Uses saved URL, format (MP4/MP3), and quality from the original download. Old files are automatically deleted after a successful re-download.
- **Format preservation**: `download_format` and `download_quality` columns on the Media model to persist download options for re-downloads.
- **Mobile-optimized media card**: Cleaner card layout with format badge (MP4/MP3), icon-only buttons on mobile, and a subtle trash icon for delete.

### Fixed
- **NameError on re-download**: Nested `worker()` function was inaccessible from `redownload_media()` route. Extracted to module level as `_download_worker()`.
- **Redownload stuck on retry**: Old status chip was not cleared after error, preventing re-download fetch requests from being sent.

## [v1.0.8] - 2026-07-01

### Security
- **AI Agent generic auth error**: Returns generic "Unauthorized" error for all AI agent authentication failures (no longer reveals whether the token is configured or invalid).
- **File path traversal validation**: Added `_safe_basename()` validation on all media and PDF serve routes to prevent path traversal.

### Changed
- **SQLite WAL mode + connection pooling**: Enabled Write-Ahead Logging (WAL) for better concurrent performance. Pool config: timeout 15s, pool_size 5, max_overflow 10, pool_pre_ping for stale connection detection.
- **python-dateutil for date arithmetic**: Recurring chores now use `python-dateutil` (relativedelta) for accurate date calculations, with fallback to manual logic if the library is unavailable.

### Fixed
- **Infinite loop protection (recurring expense)**: Added safety check in `_generate_recurring_entries_until` to prevent infinite loops if `next_date()` does not advance the date. Error logged.
- **Expense month/year validation**: Added parameter validation on expense routes to prevent crashes with extreme values (y must be 1900-2100, m must be 1-12).
- **Expense settings logging**: Added logging on expense settings load failure (previously silent).

## [v1.0.7] - 2026-07-01

### Fixed
- **Media/PDF preview not found when file is missing**: Media downloader and PDF viewer now check file existence on disk before presenting Preview/Download links. If the file was deleted or the media folder moved, the backend returns 404 cleanly, the API returns a `file_exists` flag, and the UI shows "Not available (deleted)" instead of broken links. Delete button remains available so users can clean up database entries.
- **Preview link still opens new tab 404 even when marked "Not available"**: Fixed async race condition in the frontend click handler — `preventDefault()` is now called synchronously before `await fetch(HEAD)`, preventing navigation to 404. If the file is valid, `window.open()` is called manually.
- **Raw HTML "Not available" rendered as text**: Fixed `replaceWith()` creating a TextNode — now uses `outerHTML()` so HTML elements render correctly.
- **Add Redownload button for missing media**: Added "Redownload" button that appears when media is not found on disk. Clicking fills the download form with the original video URL and scrolls to the form for easy re-download.
- **Initial page load validation**: Media marked as downloaded (filepath in DB) but missing on disk is now automatically detected on page load, not just after polling.

## [v1.0.6] - 2026-06-26

### Fixed
- **PWA Web Share Target not appearing in Android share sheet**: Fixed three critical issues preventing PWA from registering as a share target:
    1. **Maskable icons** — Added `purpose: "any maskable"` on PNG icons and removed SVG icons (unreliable on Android Chrome).
    2. **`display_override`** — Added `["standalone", "minimal-ui", "browser"]` for consistent display mode across all Android versions.
    3. **Cache-Control** — Added `no-cache` on manifest response so the browser always fetches the latest config.
- **`short_name` without unicode** — Replaced `'…'` (U+2026) with plain ASCII truncation to avoid Android launcher issues.
- **Template `shared_url` bug** — Fixed `templates/media.html` reading `request.args.get('shared_url')` instead of the already-processed `shared_url` template variable (URL not auto-filled from share target).
- **Service Worker pre-cache & share target** — Added PWA icons to precache list and bypassed cache for `/media/share` route so share navigation is always fresh.
- **405 Method Not Allowed on Download** — Form in `/media/share` had no `action`, POSTing to current URL which only accepts GET. Added `action="/media"` to the form.

### Required Infra
- **HTTPS** — Web Share Target API only works in secure context. PWA must be served over HTTPS (Caddy/Nginx reverse proxy or Tailscale Funnel). See BLUEPRINT.md for guidance.

## [v1.0.5] - 2026-06-26

### Added
- **PWA Web Share Target API**: Integrated Web Share Target API into the HomeHub PWA. Android users (and compatible desktops) can now use the OS "Share" feature (e.g., from YouTube or TikTok) to share video links directly to the HomeHub app.
- **Media Pre-fill**: Shared links now open the Media Downloader page and auto-fill the URL input field. Users can review the URL, select format (MP4/MP3), and quality before clicking Download.

## [v1.0.4] - 2026-06-23

### Added
- **AI Attachment Support (Base64)**: AI agent endpoint (`POST /api/ai/execute`) now supports Base64 receipt/payment proof uploads for expense entries. Added `attachment_base64` and `attachment_filename` function parameters that are automatically processed, compressed with Pillow, and persisted.

### Changed
- **AI Attachment Metadata**: Read-data responses (`get_expenses` and `get_recurring_expenses`) now include `has_attachment` (boolean) and `attachment_path` (string) fields.

### Fixed
- **AI Attachment Validation**: Added strict validation for expense attachments: (1) Invalid base64 rejected with "Invalid base64 string" error, (2) `attachment_base64` and `attachment_filename` must be paired, rejected with "Both attachment_base64 and attachment_filename are required if one is provided".
- **Attachment Semantics**: Documented semantic differences in schema: individual expense = per-transaction payment proof, recurring expense = contract/subscription proof (template, not copied to generated entries).
- **Expense Delete Confirm**: Fixed UX bug where single and bulk delete confirmation dialogs did not appear due to local function scope conflict (ReferenceError) in inline handlers. Confirm dialog now appears correctly before deletion.

## [v1.0.3] - 2026-06-22

### Fixed
- **Quick Links Edit Modal Centering**: Fixed Edit Quick Link Modal appearing in the top-left corner on desktop and top on mobile. By removing the default `flex` class from the HTML declaration (leaving only `hidden`), dynamic JavaScript class changes (`classList.add('flex')` and `classList.remove('hidden')`) now center the modal precisely both vertically and horizontally across all viewport sizes.
- **Expense Editing & Navigation Flow**:
  - Removed edit/delete access restrictions for individual expenses in both backend (`expenses.py`) and frontend (`expenses.html`), allowing all authorized family members (not just the creator/admin) to edit or delete. This is critical for recurring expense entries created by an admin that need to be marked 'Paid' or have payment proof attached by other family members.
  - Made "Entries This Month" sidebar rows clickable. Clicking an expense row now auto-focuses the calendar date and opens the detail panel on the left, simplifying edit/delete access from the monthly summary.

## [v1.0.2] - 2026-06-22

### Changed
- **Premium UI/UX Refactoring**: Completed 4 phases of high-standard UI/UX refactoring (ui-ux-expert + ui-ux-pro-max) covering accessibility, visual consistency, mobile optimization, smooth transitions, and dark mode completeness.
- **A11y (Accessibility) Improvements**: Added bound `<label>` tags for all missing form inputs (User Switcher, status forms, notes input, user selection modal). Added visual companion icons for "Who is Home" status pills so they don't rely on color alone. Added premium `:focus-visible` ring styling on keyboard-navigable interactive elements.
- **Mobile & Touch Optimization**: Increased touch targets (minimum 44x44px tap size) for all scope filter buttons, reminder category filters, calendar month navigation, and calendar day cells. Added interactive backdrop overlay on mobile sidebar so it can be closed by tapping outside.
- **Async Interaction State**: Prevented double-submit on AJAX actions (Who is Home update/clear and Personal Status save) by adding `disabled` state and spinner animation on buttons during requests.
- **Dark Mode Completion**: Fixed contrast gaps and hardcoded colors on the initial user selection modal, expense tab menu, and Quick Links management background to blend perfectly in dark data-theme mode.
- **Micro-Animations & Motion**: Replaced generic `all` transitions with GPU-friendly specific properties for cards and sidebar links. Applied premium hover lift effect (`translateY(-2px)`) on dashboard cards. Respects system reduced-motion preference via `@media (prefers-reduced-motion: reduce)`.
- **Icon Standardization**: Removed unicode emoji `🧾 ◀ ▶ ✕ ✎` across all layouts and replaced with consistent Font Awesome icons (chevron, trash-can, pen, receipt).
- **Heading Hierarchy Fixes**: Restructured heading hierarchy (`h2` to `h1`) on Shopping List, Chores, Recipe Book, and Quick Links sub-pages to comply with SEO best practices.
- **Script & Layout Consolidation**: Cleaned up `<script>` tag placement within `<body>` boundaries and consolidated `.btn` styles into `static/input.css` (removed duplicate inline styles).

## [v1.0.1] - 2026-06-21

### Added
- **Dedicated Recurring Expenses Page**: Recurring bill management and global expense settings moved from pop-up modal to a dedicated page (`/expenses/recurring`) with tab navigation (Recurring Rules & General Settings) for a roomier, cleaner layout.
- **Edit Strategy for Recurring Rules**: Three safe edit strategies when modifying recurring rules (*Apply from effective date*, *Split rule*, *Rewrite all*) to prevent loss of historical bill records.
- **Grouped Expense Sidebar**: Expense list in the calendar sidebar grouped by type (recurring with blue badge, manual with gray badge) with smart bulk-delete checkboxes per group.
- **Drag & Drop Quick Links**: Added Sortable.js ordering on the Manage Quick Links page. Links and categories can now be drag-and-drop reordered with persistent storage in the database (added `quick_link_category` table and `order_index` column).
- **Quick Links (Dashboard Bookmark)**: New feature for storing quick-access bookmarks (like a mini Heimdall/Homarr). Supports intelligent icon management (SVG CDN or Favicon) with vertical/horizontal grid category grouping on the main dashboard. Includes Feature Toggle (can be disabled in `config.yml`) and full CRUD by AI assistant via `edit_quick_link` action, etc.
- **Delete Actions for AI Router**: AI can now delete notes, chores, and shopping items via `delete_note`, `delete_chore`, and `delete_shopping_item` actions.
- **AI Universal Router Expansion**: Added AI assistant functions to read/manipulate `config.yml` (Config API) and manipulate Notes, Chores, and Shopping List via `POST /api/ai/execute`.
- **AI Agent Universal Router**: Single API Endpoint (`/api/ai/execute`) allowing third-party AI assistants to interact with the entire HomeHub database and system centrally.
- **Auto-Schema AI**: Endpoint (`/api/ai/schema`) returning OpenAI-compatible JSON schema format for easier AI tool configuration.
- **Paid/Unpaid Status (Expenses)**: `is_paid` column on expenses with visual Paid/Unpaid indicators in Expense Tracker and calendar.
- **Monthly Bill Horizon**: Recurring bills are now proactively generated through the end of the current month for easier financial planning.

### Changed
- **UI/UX Dark Mode Enhancements**: Improved dark mode support for the Recurring Expenses page by converting static CSS to Tailwind utility classes (e.g., `dark:bg-gray-800`).
- **Bug Fix (Early Payment Tracking)**: Fixed recurring bill payment detection on the dashboard to properly detect early payments within the same month (previously failed if payment was made more than 20 days early).
- **API (AI Agent Validations)**: Fixed several validation gaps in AI assistant API routes, including blocking negative amounts, limiting year input (2000-2100), ensuring start date does not exceed end date on recurring bills, requiring payer name, and fixing hard-delete consistency logic for recurring rules.
- **Bug Fix (Overlap Layout)**: Fixed overlapping elements between long expense titles and badge labels in the sidebar by applying flex constraints (`shrink-0` and `min-w-0`).
- **Bug Fix (UnboundLocalError)**: Fixed Internal Server Error 500 on the dashboard (specifically the Reminder widget) caused by Python `timedelta` local variable shadowing.
- **Bug Fix (Dashboard Clock)**: Fixed the live clock on the home page not respecting the 24-hour format setting (`reminders.time_format`) in `config.yml`. The main clock and welcome card now detect the time format correctly and tick every second without page reload.
- **Bug Fix (AI Tags Array)**: Fixed an issue where sending `tags` as a JSON Array from the AI agent caused save failure in SQLite. Array input is now automatically normalized to a comma-separated string before database insertion.
- `config.yml` now supports `ai_agent_token` for external API authentication.
- Monthly expense totals on the dashboard and Expense Tracker now only count expenses with "Paid" status.
