# Strategic order — Merge Phase 5 → Artist email toolkit

**Status:** Ready to execute  
**Starts after:** Product Phases 0–5 (fees → CRM → drops → parties → growth → engagement)  
**Prerequisite:** ~~Merge [PR #15](https://github.com/rgpvvks7b7-spec/People-s-Media-Platform/pull/15) (Phase 5 engagement loop)~~ — ✅ landed on `main`  
**Separate from:** [PRELAUNCH_STRATEGY.md](./PRELAUNCH_STRATEGY.md) legal Phase numbers  

**North star for this arc:** Artists who collect opted-in emails can *see* the list, *export* it (Pro), and *leave with a compliant draft* — without IndieFund becoming an ESP or sending fan email for them.

---

## Order of execution

| Step | Name | Outcome | Depends on |
|------|------|---------|------------|
| **0** | Land Phase 5 | ~~PR #15 merged to `main`~~ ✅ | — |
| **1** | Mailing list studio | Browse opted-in contacts + export nudge | Step 0 |
| **2** | Template studio | Tailored copy-paste email drafts | Step 1 |
| **3** | Moment → draft hooks | One-click draft after drop / gig / thank-you moments | Step 2 |
| **4** | CRM bridge | `mailing_list` segment → “Copy email draft” | Steps 1–2 |
| **5** | Local draw + list | City → Spaces gig → promote locals (in-app + draft) | Steps 2–3 |

Do **not** start Step 2 until Step 1 ships a real list surface (counts alone are not enough).  
Do **not** build platform-sent fan email or an ESP integration in this arc.

---

## Step 0 — Merge PR #15

**PR:** Phase 5 tip prompts, post-show loop, commission inbox, invite funnel  

**Done when:**
- [x] PR #15 merged to `main`
- [ ] Phase 5 Playwright still green on `main`

---

## Step 1 — Mailing list studio (list clarity)

Make the existing `ArtistFanContact` / `GET /api/artists/mailing-list/` surface usable.

**Ship:**
1. Artist Home / Profile: mailing list panel with contact rows (email or masked until Pro — product choice: prefer full email only when `can_export`, else username + masked)
2. Filters: all / active supporters / tips-only / recently added
3. Growth strip: size, +30d, source mix (signup / support / tip / manual)
4. **Export nudge** at 10+ opt-ins for free artists → Artist Pro upgrade (Roadmap “mailing list export nudge”)
5. Empty state: how fans opt in (support checkbox, tip, global preference)

**Out of scope:** sending email, importing CSVs, public embed signup forms.

**Primary files:** `artists/views.py` (`mailing_list`), `main.jsx` / `AccountPages.jsx`, `FanCrmPage.jsx`, Pro gate via `can_export`.

**Done when:**
- [ ] Owner can open a mailing list view and see opted-in fans
- [ ] Pro/Studio can download CSV from that view
- [ ] Free plan sees upgrade path at ≥10 contacts
- [ ] Narrow e2e: list visible + export/upgrade CTA

---

## Step 2 — Template studio (copy-paste drafts)

Help artists email *outside* IndieFund with compliant, brand-aware drafts.

**Ship:**
1. Template picker on mailing list / Fans CRM:
   - New release / drop
   - Upcoming local show
   - Thank you (support or tip)
   - “It’s been a while” re-engagement
2. Merge fields from artist profile only (stage name, city, public page URL, next gig if any) — **never** auto-BCC or inject the full fan list into a mailto body
3. Copy subject + body (plain text first; optional simple HTML without tracking pixels)
4. Footer always includes: who it’s from, why they’re receiving it (opted in on IndieFund), unsubscribe instruction
5. Short compliance note under copy button (artist agreement §8)

**Legal guardrails (product):**
- Copy/export only — IndieFund does not deliver the message
- Templates limited to releases, shows, exclusive updates
- No ad / remarketing pixels in suggested HTML (`legal/README.md`)
- No “paste imported list” flow

**Done when:**
- [ ] Artist can generate and copy at least the four template types
- [ ] Draft includes unsubscribe/compliance footer
- [ ] e2e: open template → copy succeeds (clipboard or visible textarea select-all)

---

## Step 3 — Moment → draft hooks

Wire peak artist moments to a pre-filled template (still copy-paste, still no send).

| Moment | Default template |
|--------|------------------|
| Drop / track published | New release |
| Spaces booking confirmed | Upcoming local show |
| Post-show host complete / fan review prompt window | Thank you |
| Listening party ended (host) | New release or thank you |

**Ship:** “Email your list” secondary CTA near those success toasts / panels → opens Template studio with context filled.

**Done when:**
- [ ] At least drop-publish and gig-confirmed expose the CTA
- [ ] Opening the CTA lands on a preselected template with merge fields filled

---

## Step 4 — CRM bridge

Connect Fan CRM to the toolkit without duplicating surfaces.

**Ship:**
1. `mailing_list` segment toolbar: Export CSV (Pro) · Copy email draft
2. Optional: draft personalization count (“You’ll paste this to N opted-in fans in your ESP/client”)
3. Keep broadcast as **in-app + push only** (existing) — label clearly vs email draft

**Done when:**
- [ ] From Fans → mailing_list, artist can export and/or open template studio in one click

---

## Step 5 — Local draw + list (bridge to next growth work)

Reuse the email toolkit for the existing Roadmap “local draw playbook” instead of inventing a parallel channel.

**Ship (thin slice):**
1. Guided checklist: set discovery city → request Spaces booking → promote
2. Promote step offers: in-app/push to local savers **and** “Copy local show email draft”
3. Template pre-fills venue, date, ticket/public link when available

**Done when:**
- [ ] Artist can complete the three checklist steps
- [ ] Local show draft is available when a confirmed gig exists

---

## Explicitly deferred (after this arc)

| Item | Why later |
|------|-----------|
| Platform-sent fan newsletters / ESP | Controller + deliverability + Spam Act; lawyer review first |
| Public “join my list” embed | New consent surface; not required for export+templates |
| Discovery streaks | Fan retention; not blocked by email toolkit |
| Full Pro insights expansion | Partially built; less urgent than list clarity |
| Capacitor / production deploy | P3 scale track |

---

## Success metrics

- % of Pro artists who export CSV in 30d
- % of artists with ≥1 mailing contact who open Template studio
- Template copy events (client analytics / journey optional)
- Artist Pro conversion from export nudge (10+ contacts)
- Time-to-first-export after first opt-in

---

## Execution notes for agents

1. Branch from `main` after Step 0: `cursor/<step-name>-8828`
2. Keep Playwright skill standards for any UI/e2e
3. No advertising cookies or remarketing pixels in templates
4. Prefer one PR per step; Step 5 may follow as its own PR after 2–4
5. Update this file’s checkboxes and [ROADMAP.md](./ROADMAP.md) when a step merges
