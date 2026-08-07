import React, { useEffect, useState } from "react";

const SEGMENT_LABELS = {
  all: "All fans",
  supporters: "Supporters",
  followers: "Followers",
  ticket_buyers: "Ticket buyers",
  mailing_list: "Mailing list",
};

const SEGMENT_ORDER = ["all", "supporters", "followers", "ticket_buyers", "mailing_list"];

function formatDate(value) {
  if (!value) return "—";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return "—";
  return parsed.toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" });
}

function segmentBadges(row) {
  return (row.segments || []).map(segment => (
    <span className="support-badge" key={`${row.fan_id}-${segment}`}>{SEGMENT_LABELS[segment] || segment}</span>
  ));
}

export function FanCrmPage({ apiFetch }) {
  const [segment, setSegment] = useState("all");
  const [fans, setFans] = useState([]);
  const [counts, setCounts] = useState({});
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [composerOpen, setComposerOpen] = useState(false);
  const [sending, setSending] = useState(false);
  const [sendResult, setSendResult] = useState("");

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      setLoadError("");
      try {
        const res = await apiFetch(`/artists/fans/?segment=${segment}`);
        const data = await res.json();
        if (cancelled) return;
        if (!res.ok) {
          setLoadError(data.error || "Could not load your fans.");
        } else {
          setFans(data.results || []);
          setCounts(data.counts || {});
        }
      } catch {
        if (!cancelled) setLoadError("Could not load your fans.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, [apiFetch, segment]);

  async function sendBroadcast(event) {
    event.preventDefault();
    const form = new FormData(event.target);
    const payload = {
      title: (form.get("title") || "").trim(),
      body: (form.get("body") || "").trim(),
      segment: form.get("segment") || "all",
    };
    setSending(true);
    setSendResult("");
    try {
      const res = await apiFetch("/artists/fans/broadcast/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (!res.ok) {
        setSendResult(data.error || "Message could not be sent.");
      } else {
        setSendResult(`Sent to ${data.sent} ${data.sent === 1 ? "fan" : "fans"}.`);
        event.target.reset();
        setComposerOpen(false);
      }
    } catch {
      setSendResult("Message could not be sent.");
    } finally {
      setSending(false);
    }
  }

  return (
    <section className="fan-crm-page">
      <header className="section-head tab-title-row">
        <div>
          <p className="eyebrow">Your fans</p>
          <h2>Fans</h2>
          <p className="muted">
            Every relationship in one place — who supports you, who follows you, and who shows up.
          </p>
        </div>
        <button className="primary compact" type="button" onClick={() => setComposerOpen(open => !open)}>
          {composerOpen ? "Close composer" : "Message fans"}
        </button>
      </header>

      {sendResult && <p className="muted" role="status">{sendResult}</p>}

      {composerOpen && (
        <section className="feature-card">
          <h3>Message your fans</h3>
          <p className="muted form-hint">
            Delivered as an in-app and push notification. One broadcast per 24 hours — make it count.
          </p>
          <form className="fan-crm-composer" onSubmit={sendBroadcast}>
            <label htmlFor="fan-broadcast-segment">Send to</label>
            <select id="fan-broadcast-segment" name="segment" defaultValue={segment}>
              {SEGMENT_ORDER.map(name => (
                <option key={name} value={name}>
                  {SEGMENT_LABELS[name]}{counts[name] != null ? ` (${counts[name]})` : ""}
                </option>
              ))}
            </select>
            <label htmlFor="fan-broadcast-title">Title</label>
            <input id="fan-broadcast-title" name="title" maxLength={120} required placeholder="New single out Friday" />
            <label htmlFor="fan-broadcast-body">Message</label>
            <textarea
              id="fan-broadcast-body"
              name="body"
              maxLength={1000}
              required
              placeholder="Tell your fans what's happening and what to do next."
            ></textarea>
            <button className="primary compact" type="submit" disabled={sending}>
              {sending ? "Sending…" : "Send message"}
            </button>
          </form>
        </section>
      )}

      <div className="fan-crm-segments" role="tablist" aria-label="Fan segments">
        {SEGMENT_ORDER.map(name => (
          <button
            key={name}
            type="button"
            role="tab"
            aria-selected={segment === name}
            className={segment === name ? "primary compact" : "secondary compact"}
            onClick={() => setSegment(name)}
          >
            {SEGMENT_LABELS[name]}{counts[name] != null ? ` · ${counts[name]}` : ""}
          </button>
        ))}
      </div>

      {loading ? (
        <p className="muted">Loading your fans…</p>
      ) : loadError ? (
        <p className="muted">{loadError}</p>
      ) : !fans.length ? (
        <section className="empty-state">
          <h3>No fans in this segment yet.</h3>
          <p className="muted">
            Share your page and post consistently — every follow, tip, and ticket shows up here.
          </p>
        </section>
      ) : (
        <table className="fan-crm-table">
          <thead>
            <tr>
              <th scope="col">Fan</th>
              <th scope="col">Segments</th>
              <th scope="col">Monthly</th>
              <th scope="col">Lifetime spend</th>
              <th scope="col">Supporter since</th>
              <th scope="col">Last active</th>
            </tr>
          </thead>
          <tbody>
            {fans.map(row => (
              <tr key={row.fan_id}>
                <td>
                  <strong>{row.display_name}</strong>
                  <p className="muted">
                    @{row.fan_username}
                    {row.location ? ` · ${row.location}` : ""}
                  </p>
                </td>
                <td>{segmentBadges(row)}</td>
                <td>{row.is_supporter ? `$${row.monthly_amount}/mo` : "—"}</td>
                <td>${row.lifetime_spend}</td>
                <td>{formatDate(row.supporter_since)}</td>
                <td>{formatDate(row.last_active)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}
