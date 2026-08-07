import React, { useEffect, useMemo, useState } from "react";
import { buildEmailTemplate, listEmailTemplates } from "../lib/emailTemplates.js";

const FILTERS = [
  { id: "all", label: "All" },
  { id: "supporters", label: "Active supporters" },
  { id: "tips", label: "Tippers" },
  { id: "recent", label: "Added recently" },
];

const SOURCE_LABELS = {
  signup_opt_in: "Signup",
  support_prompt: "Support / tip",
  manual: "Manual",
};

function formatDate(value) {
  if (!value) return "—";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return "—";
  return parsed.toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" });
}

/**
 * Artist mailing list studio: browse opted-in contacts, copy email drafts,
 * and run the thin local-draw checklist. IndieFund does not send email.
 */
export function MailingListStudio({
  apiFetch,
  currentUser,
  initialTemplate = "new_release",
  initialContext = {},
  onExportCsv,
  onUpgradePlan,
  onOpenProfile,
  onOpenSpaces,
  onBroadcastLocal,
  origin = "",
}) {
  const [filter, setFilter] = useState("all");
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [templateId, setTemplateId] = useState(initialTemplate || "new_release");
  const [copyStatus, setCopyStatus] = useState("");

  useEffect(() => {
    setTemplateId(initialTemplate || "new_release");
  }, [initialTemplate]);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      setLoadError("");
      try {
        const res = await apiFetch(`/artists/mailing-list/?filter=${encodeURIComponent(filter)}`);
        const payload = await res.json();
        if (cancelled) return;
        if (!res.ok) {
          setLoadError(payload.error || "Could not load your mailing list.");
          setData(null);
        } else {
          setData(payload);
        }
      } catch {
        if (!cancelled) {
          setLoadError("Could not load your mailing list.");
          setData(null);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, [apiFetch, filter]);

  const templateContext = useMemo(() => {
    const base = data?.template_context || {};
    const publicPath = base.public_url || `/?artist=${currentUser?.username || ""}`;
    const publicUrl = publicPath.startsWith("http") ? publicPath : `${origin}${publicPath}`;
    const gig = base.next_gig;
    return {
      stageName: initialContext.stageName || base.stage_name || currentUser?.display_name || currentUser?.username,
      city: initialContext.city || gig?.city || base.city || "",
      publicUrl: initialContext.publicUrl || publicUrl,
      trackTitle: initialContext.trackTitle || "",
      venueName: initialContext.venueName || gig?.venue_name || "",
      showDate: initialContext.showDate || (gig?.starts_at ? formatDate(gig.starts_at) : ""),
      ticketUrl: initialContext.ticketUrl || (gig?.public_url ? `${origin}${gig.public_url}` : publicUrl),
    };
  }, [data, currentUser, initialContext, origin]);

  const draft = useMemo(
    () => buildEmailTemplate(templateId, templateContext),
    [templateId, templateContext],
  );

  const count = data?.count || 0;
  const canExport = Boolean(data?.can_export);
  const exportNudge = Boolean(data?.export_nudge);
  const sourceMix = data?.source_mix || {};
  const ctx = data?.template_context || {};

  async function copyDraft() {
    const text = `Subject: ${draft.subject}\n\n${draft.body}`;
    try {
      await navigator.clipboard.writeText(text);
      setCopyStatus("Draft copied — paste it into your email app or ESP.");
    } catch {
      setCopyStatus("Select the draft below and copy it manually.");
    }
  }

  return (
    <div className="mailing-list-studio">
      <header className="section-head tab-title-row">
        <div>
          <p className="eyebrow">Artist toolkit</p>
          <h2>Mailing list</h2>
          <p className="muted">
            Opted-in contacts only. Export or copy a draft — IndieFund does not send fan email for you.
          </p>
        </div>
        <div className="action-grid">
          {canExport ? (
            <button className="primary compact" type="button" onClick={onExportCsv}>
              Export CSV
            </button>
          ) : (
            <button className="secondary compact" type="button" onClick={() => onUpgradePlan?.("pro")}>
              Upgrade for CSV
            </button>
          )}
        </div>
      </header>

      <section className="artist-stat-panel mailing-list-growth" aria-label="Mailing list growth">
        <div className="artist-stat-grid">
          <div className="artist-stat-item">
            <p className="eyebrow">Contacts</p>
            <strong className="artist-stat-value">{count}</strong>
            <p className="artist-stat-detail">+{data?.added_last_30d || 0} in 30 days</p>
          </div>
          <div className="artist-stat-item">
            <p className="eyebrow">This month</p>
            <strong className="artist-stat-value">{data?.added_this_month || 0}</strong>
            <p className="artist-stat-detail">New opt-ins</p>
          </div>
          <div className="artist-stat-item">
            <p className="eyebrow">Sources</p>
            <strong className="artist-stat-value">
              {(sourceMix.signup_opt_in || 0) + (sourceMix.support_prompt || 0) + (sourceMix.manual || 0)}
            </strong>
            <p className="artist-stat-detail">
              {SOURCE_LABELS.signup_opt_in} {sourceMix.signup_opt_in || 0}
              {" · "}
              {SOURCE_LABELS.support_prompt} {sourceMix.support_prompt || 0}
              {" · "}
              {SOURCE_LABELS.manual} {sourceMix.manual || 0}
            </p>
          </div>
        </div>
      </section>

      {exportNudge && (
        <section className="feature-card mailing-export-nudge">
          <p className="eyebrow">Artist Pro</p>
          <h3>You have {count} opted-in contacts</h3>
          <p className="muted">
            Upgrade to export your CSV and email fans from your own inbox or ESP.
          </p>
          <button className="primary compact" type="button" onClick={() => onUpgradePlan?.("pro")}>
            Unlock CSV export
          </button>
        </section>
      )}

      <section className="feature-card email-template-studio" aria-labelledby="email-template-heading">
        <div className="tab-title-row">
          <div>
            <p className="eyebrow">Copy-paste drafts</p>
            <h3 id="email-template-heading">Email template studio</h3>
            <p className="muted">
              Tailored drafts for your voice. You send them outside IndieFund.
            </p>
          </div>
        </div>
        <div className="email-template-picker" role="tablist" aria-label="Email templates">
          {listEmailTemplates().map(item => (
            <button
              key={item.id}
              type="button"
              role="tab"
              aria-selected={templateId === item.id}
              className={templateId === item.id ? "primary compact" : "secondary compact"}
              onClick={() => setTemplateId(item.id)}
            >
              {item.label}
            </button>
          ))}
        </div>
        <label htmlFor="email-draft-subject">Subject</label>
        <input id="email-draft-subject" readOnly value={draft.subject} />
        <label htmlFor="email-draft-body">Body</label>
        <textarea id="email-draft-body" readOnly rows={14} value={draft.body} />
        <p className="muted form-hint">
          Use only for fans who opted in. Honour unsubscribe requests (Artist Agreement §8).
          No tracking pixels.
        </p>
        <div className="action-grid">
          <button className="primary" type="button" onClick={copyDraft}>
            Copy draft
          </button>
        </div>
        {copyStatus ? <p className="muted" role="status">{copyStatus}</p> : null}
      </section>

      <section className="feature-card local-draw-playbook" aria-labelledby="local-draw-heading">
        <p className="eyebrow">Local growth</p>
        <h3 id="local-draw-heading">Local draw playbook</h3>
        <p className="muted">Set your city, book a room, then promote locals — in-app and by email draft.</p>
        <ol className="local-draw-steps">
          <li className={ctx.profile_city_set ? "is-done" : ""}>
            <strong>Set your city</strong>
            <p className="muted">{ctx.city ? ctx.city : "Add your city in Profile so local fans match."}</p>
            {!ctx.profile_city_set && (
              <button className="secondary compact" type="button" onClick={onOpenProfile}>
                Update city
              </button>
            )}
          </li>
          <li className={ctx.has_upcoming_gig ? "is-done" : ""}>
            <strong>Book a Spaces gig</strong>
            <p className="muted">
              {ctx.has_upcoming_gig
                ? `${ctx.next_gig?.venue_name || "Venue"} · ${formatDate(ctx.next_gig?.starts_at)}`
                : "Request a confirmed room near you."}
            </p>
            {!ctx.has_upcoming_gig && (
              <button className="secondary compact" type="button" onClick={onOpenSpaces}>
                Browse Spaces
              </button>
            )}
          </li>
          <li>
            <strong>Promote to locals</strong>
            <p className="muted">
              {ctx.local_mailing_contacts || 0} local mailing contacts
              {" · "}
              {ctx.local_supporters || 0} local supporters
            </p>
            <div className="action-grid">
              <button
                className="secondary compact"
                type="button"
                onClick={() => {
                  setTemplateId("local_show");
                  setCopyStatus("Local show template selected — copy when ready.");
                }}
              >
                Copy local show email draft
              </button>
              {onBroadcastLocal && (
                <button className="secondary compact" type="button" onClick={onBroadcastLocal}>
                  Message fans in-app
                </button>
              )}
            </div>
          </li>
        </ol>
      </section>

      <section className="mailing-list-contacts" aria-labelledby="mailing-contacts-heading">
        <div className="tab-title-row">
          <div>
            <h3 id="mailing-contacts-heading">Opted-in contacts</h3>
            <p className="muted">
              {canExport ? "Full emails shown for export-ready plans." : "Emails masked until Artist Pro."}
            </p>
          </div>
        </div>
        <div className="fan-crm-segments" role="tablist" aria-label="Mailing list filters">
          {FILTERS.map(item => (
            <button
              key={item.id}
              type="button"
              role="tab"
              aria-selected={filter === item.id}
              className={filter === item.id ? "primary compact" : "secondary compact"}
              onClick={() => setFilter(item.id)}
            >
              {item.label}
              {filter === item.id && data?.filtered_count != null ? ` · ${data.filtered_count}` : ""}
            </button>
          ))}
        </div>

        {loading && <p className="muted">Loading contacts…</p>}
        {loadError && <p className="form-error">{loadError}</p>}
        {!loading && !loadError && count === 0 && (
          <div className="empty-state">
            <h3>No emails shared yet</h3>
            <p className="muted">
              Fans opt in at signup, when they support or tip you, or in Profile → Email sharing.
            </p>
          </div>
        )}
        {!loading && !loadError && count > 0 && (data?.results || []).length === 0 && (
          <p className="muted">No contacts match this filter.</p>
        )}
        {!loading && (data?.results || []).length > 0 && (
          <table className="fan-crm-table">
            <thead>
              <tr>
                <th scope="col">Fan</th>
                <th scope="col">Email</th>
                <th scope="col">Tier</th>
                <th scope="col">Source</th>
                <th scope="col">Added</th>
              </tr>
            </thead>
            <tbody>
              {data.results.map(row => (
                <tr key={row.id || row.fan_id}>
                  <td>
                    <strong>@{row.fan_username}</strong>
                    <p className="muted">{row.location || "—"}</p>
                  </td>
                  <td>{row.email || row.masked_email}</td>
                  <td>{row.support_tier || (row.active_subscription ? "Supporter" : "—")}</td>
                  <td>{SOURCE_LABELS[row.source] || row.source || "—"}</td>
                  <td>{formatDate(row.date_added)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
}
