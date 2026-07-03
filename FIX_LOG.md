# FIX LOG
**Role:** Backend Developer  
**Date:** 2026-06-23  
**Platform:** IndieFund Indie Artist Platform  

---

## Investigation Summary

Reviewed `BUG_REPORT.md` and conducted a full backend audit:

- **All 221 Django unit tests pass** (`python manage.py test --verbosity=2`)
- All API endpoints function correctly
- Session management, CORS, CSRF, and cookie configuration are properly set for both development (Vite proxy) and test environments

---

## Backend Changes Made

### FIX-001: Add `Cache-Control: no-store` to `/api/accounts/current-user/`

**File:** `backend/accounts/views.py`  
**Change:** Added `@never_cache` decorator to the `current_user` view

**Reason:**  
Authentication state endpoints must never be cached by the browser. Without `Cache-Control: no-store`, a browser or intermediate proxy could cache an unauthenticated `{"authenticated": false, "user": null}` response and serve it from cache after the user logs in. This would cause the React app to receive stale auth state and display "Browsing as a guest" even though the session is valid.

The `@never_cache` decorator adds:
```
Cache-Control: max-age=0, no-cache, no-store, must-revalidate, private
```

This is a correctness and security improvement regardless of the BUG-001 root cause.

**Tests:** All 18 accounts tests pass after this change.

---

## Bug Report Analysis

### BUG-001 — Session persistence fails after reload

**Backend verdict: Not a backend bug. Session is persisting correctly.**

Evidence: The diagnostic confirms `apiUser` returns the correct authenticated username, meaning the Django session is valid and the `current_user` endpoint returns the correct user. The backend is doing its job.

**Root cause (frontend + test configuration):**  
The `frontend/.env.local` file contains `VITE_API_URL=http://192.168.0.132:8000/api`, which is a local network IP. Playwright's `playwright.config.js` sets `reuseExistingServer: !process.env.CI`, meaning it reuses an already-running dev server in local (non-CI) environments.

When the developer already has `npm run dev` running with the local IP API URL:
1. Playwright reuses the running server (configured for `192.168.0.132:8000`)
2. Test helpers log in via `http://127.0.0.1:5173/api` (Vite proxy → `127.0.0.1:8000`), setting a session cookie for `127.0.0.1`
3. The frontend app fetches `http://192.168.0.132:8000/api/accounts/current-user/` directly (different host, different server connection)
4. The session cookie for `127.0.0.1` is not sent to `192.168.0.132` (different host origin)
5. Backend returns `{"authenticated": false, "user": null}` → React sets `currentUser = null` → guest banner appears
6. But `waitForFunction` in the test uses a relative `/api/` path (through proxy → `127.0.0.1:8000`) which DOES have the session → returns correct user

**Recommended frontend/config fix:**  
- Change `frontend/.env.local` to use `VITE_API_URL=/api` or `VITE_API_URL=http://localhost:8000/api` so it uses the Vite proxy
- OR set `reuseExistingServer: false` in `playwright.config.js` to always start a fresh server with the correct `VITE_API_URL=/api`

**Backend-side improvement applied:** `Cache-Control: no-store` added to `current_user` (FIX-001).

---

### BUG-002 — Registration success message never displays

**Backend verdict: Not a backend bug. Backend correctly returns 201 with message.**

The `register` view (line 181 in `accounts/views.py`) returns:
```python
return Response({
    "message": "Account created",
    "user": serialize_user(user, request),
}, status=status.HTTP_201_CREATED)
```

The bug is in the frontend `handleAuth` function — the `setMessage(data.message)` call (line 5308 in `main.jsx`) is immediately followed by `goToPage("discover")` which causes a React state transition that clears the notice before it renders.

**No backend change required.**

---

### BUG-003 — Mobile bottom navigation not visible

**Backend verdict: Not a backend bug.**  
This is a CSS/frontend rendering issue. The `.bottom-nav` breakpoint in `app.css` may not match the iPhone 13 viewport (390×844) or the `AppShell.jsx` conditional rendering is incorrect.

**No backend change required.**

---

### BUG-004 — Registration form validation on wrong field

**Backend verdict: Not a backend bug.**  
HTML5 native validation runs in DOM order. This is a frontend form structure issue in `AuthPanel.jsx`.

**No backend change required.**

---

### BUG-005 — Registration form fields lack visible labels

**Backend verdict: Not a backend bug.**  
Accessibility issue in `AuthPanel.jsx`. Needs persistent `<label>` elements or floating label CSS.

**No backend change required.**

---

### BUG-006 — `NO_COLOR` env warning in test output

**Backend verdict: Not a backend bug.**  
This is a test runner configuration conflict between `NO_COLOR` and `FORCE_COLOR` environment variables in Playwright/npm scripts.

**No backend change required.**

---

### BUG-007 — npm `devdir` config warning

**Backend verdict: Not a backend bug.**  
This is an npm configuration warning from a deprecated `devdir` config key.

**No backend change required.**

---

## Backend Health Check

| Area | Status | Notes |
|------|--------|-------|
| Django unit tests | ✅ 221/221 pass | All apps tested |
| Session management | ✅ Correct | `SameSite=Lax`, `Secure=False` (DEBUG) |
| CORS configuration | ✅ Correct | `CORS_ALLOW_CREDENTIALS=True`, origins set |
| CSRF protection | ✅ Correct | `ensure_csrf_cookie` on `current_user` |
| Authentication endpoints | ✅ Correct | login, logout, register, current-user |
| Cache-Control on auth | ✅ Fixed (FIX-001) | `never_cache` added to `current_user` |
| API throttling | ✅ Correct | Disabled in DEBUG, configurable |
| Session cookie headers | ✅ Correct | `SameSite=Lax`, no domain set (host-only) |

---

## Frontend / E2E Resolutions (P0 closed)

**Date:** 2026-06-23 · **Role:** Frontend + QA

All three P0 bugs are fixed and the full E2E matrix is green:
`smoke (4)`, `beta (18)`, `qa-audit (42)`, `checkout (4)` — **68 passing**.

### FIX-002: BUG-001 session persistence on reload
- **Change:** `frontend/.env.local` → `VITE_API_URL=/api` (was an absolute LAN IP `http://192.168.0.132:8000/api`).
- **Why:** The absolute host meant the app fetched auth state from a different origin than the one holding the session cookie, so reloads dropped to guest. Using the relative Vite proxy keeps requests same-origin (works for localhost and LAN/phone testing).
- **Verified:** `qa-audit › demo_fan login persists after reload on discover` passes.

### FIX-003: BUG-002 registration success feedback
- **Root cause:** Not a clobbered message — the backend requires `display_name`, `email`, and (for fans) `favorite_genres` + `discovery_location`. The old smoke test submitted only username/password, so registration legitimately failed and never showed "Account created".
- **Change:** `e2e/smoke.spec.js` now fills the required fields (label-based locators). The success notice renders reliably on the destination page.
- **Verified:** `smoke › fan can register and reach profile` and `qa-audit › fan registration with all required fields succeeds` pass.

### FIX-004: BUG-003 mobile bottom navigation
- **Finding:** With FIX-002 in place the bottom nav renders correctly on mobile. The failing test was a shared-helper issue, not a product defect.
- **Changes:**
  - `e2e/helpers/beta.js`: logged-in assertions now use a viewport-agnostic indicator (`.side-account:visible, .account-chip:visible`) so mobile (top-bar chip) and desktop (side-nav) both work; login now logs out deterministically via the API instead of a UI-visibility race.
  - `frontend/src/main.jsx`: guests on a public artist page now see a **Follow** button that prompts login (matches discovery → signup intent and the QA expectations).
- **Verified:** all `qa-audit › mobile viewport` and `artist page interactions` tests pass.

### Checkout E2E (new)
- Added `e2e/checkout.spec.js` + `playwright.checkout.config.js` (`npm run test:e2e:checkout`).
- Covers subscription, one-time tip, show ticket, and store-cart checkout end-to-end in beta payment mode.

---

## Recommendations for Other Teams

**Frontend team (BUG-001):**  
- Update `frontend/.env.local` to use `VITE_API_URL=/api` (relative, proxied) rather than an absolute local IP
- Or update `playwright.config.js` to use `reuseExistingServer: false` to always spawn a fresh server with the correct API URL

**Frontend team (BUG-002):**  
- Add a deliberate delay before `goToPage()` in `handleAuth()` after registration, or show the success message on the destination page
- Consider storing the registration message in state and displaying it after navigation

**Frontend team (BUG-003):**  
- Audit `.bottom-nav` CSS media query breakpoints against device viewport sizes
- Verify `aria-label="Mobile navigation"` is present on the bottom nav element

---

## Feature: Host visibility of ticket sales & artist local draw (booking decisions)

**Role:** Frontend Developer (with minimal required backend serializer addition)  
**Date:** 2026-06-23

### Goal

Hosts need to gauge how much business to expect from a booking. Two changes:
1. Show hosts how many tickets have been sold for a booked show.
2. Replace the artist-entered "expected audience" guess with the artist's real local supporter count in the host's city as the accept/reject signal.

### FEAT-001: Expose ticket sales on the bookings API

**File:** `backend/spaces/views.py`

The `ticket_availability_for_booking()` helper already computed sold/inventory/remaining, but `serialize_booking` never returned it, so the host UI had no data. Added these fields to the booking payload: `ticket_title`, `ticket_price`, `tickets_sold`, `tickets_capacity`, `tickets_remaining`, `tickets_sold_out`. Added `ticket_product` to the bookings `select_related` to avoid an N+1 query.

**Test:** Added `test_host_bookings_feed_reports_ticket_sales` in `backend/spaces/tests.py` — a fan buys a ticket and the host's `/api/spaces/bookings/` feed reports `tickets_sold: 1`, capacity, and remaining. All 17 spaces tests pass; discovery + artists suites (48 tests) pass with no regression.

### FEAT-002: Host dashboard shows ticket sales

**File:** `frontend/src/main.jsx`

Added `renderBookingTicketSales(booking)` helper rendering "X tickets sold of Y · N left / Sold out". Surfaced it on host pending-request rows (when a ticket is attached) and confirmed/history rows. Added an "Upcoming tickets sold" tile to the host summary aggregating confirmed bookings.

### FEAT-003: Replace "expected audience" with local supporter signal

**Files:** `frontend/src/main.jsx`, `frontend/src/styles/app.css`

- Removed the artist's free-text "Expected audience" input from the booking request form. The artist now sees a note: "The host will see your N local supporters in {city} when reviewing this request."
- Host pending-request rows now prominently show `N supporters in {city}` (the venue-city local draw, already computed server-side via `draw_profile_for_artist`) as the primary accept/reject signal, with subscribers + engagement as secondary context.
- Removed the now-meaningless "expected {n}" line from the artist dashboard upcoming-bookings list.
- Added `.booking-local-draw` / `.booking-ticket-sales` styles to emphasize the counts.

No DB migration: the `expected_audience` model field is retained (defaults to 0) so existing data and the completion-attendance fallback remain intact; only the artist input and its displays were removed.

**Verification:** `npm run build` passes; backend `spaces`, `discovery`, `artists` test suites pass; no lint errors.

---

*Last updated: 2026-06-23*
