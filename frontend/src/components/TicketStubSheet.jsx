import React, { useMemo, useState } from "react";

function TicketStubGlyph({ className = "ticket-stub-icon-button-glyph" }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      aria-hidden="true"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.75"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M4 7.5h16a1.5 1.5 0 0 1 1.5 1.5v1.2a1.2 1.2 0 0 0 0 2.4V16.5A1.5 1.5 0 0 1 20 18H4a1.5 1.5 0 0 1-1.5-1.5v-1.2a1.2 1.2 0 0 0 0-2.4V9A1.5 1.5 0 0 1 4 7.5z" />
      <path d="M9 7.5v9" strokeDasharray="2.5 2.5" />
      <path d="M13.5 11h3" />
      <path d="M13.5 14h2" />
    </svg>
  );
}

export function TicketStubNavIcon() {
  return <TicketStubGlyph className="app-nav-ticket-stub-glyph" />;
}

export function TicketStubIconButton({ onClick }) {
  return (
    <button
      className="ticket-stub-icon-button"
      type="button"
      onClick={onClick}
      aria-label="Ticket stub — generate door codes"
    >
      <TicketStubGlyph />
      <span>Ticket stub</span>
    </button>
  );
}

function formatShowDate(value) {
  if (!value) return "";
  return new Date(value).toLocaleString(undefined, {
    weekday: "short",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

/**
 * Host sheet to generate door codes for staff to hand to guests.
 */
export function TicketStubSheet({ open, onClose, bookings = [], apiFetch, onMessage }) {
  const [generatingId, setGeneratingId] = useState(null);
  const [activeStubs, setActiveStubs] = useState({});

  const ticketedShows = useMemo(
    () => bookings.filter(
      booking => booking.status === "confirmed" && booking.ticket_product_id
    ),
    [bookings],
  );

  if (!open) return null;

  async function generateStub(bookingId) {
    setGeneratingId(bookingId);
    try {
      const res = await apiFetch(`/spaces/bookings/${bookingId}/ticket-stub/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({}),
      });
      const data = await res.json();
      if (!res.ok) {
        onMessage?.(data.error || "Could not generate ticket stub.");
        return;
      }
      setActiveStubs(prev => ({
        ...prev,
        [bookingId]: {
          stub_code: data.stub_code,
          stubs_issued: data.stubs_issued,
          stubs_redeemed: data.stubs_redeemed,
        },
      }));
      onMessage?.("Ticket stub ready — tell the guest this code at the door.");
    } catch {
      onMessage?.("Could not generate ticket stub.");
    } finally {
      setGeneratingId(null);
    }
  }

  return (
    <div className="modal-backdrop" role="presentation" onClick={onClose}>
      <div
        className="modal-panel ticket-stub-sheet"
        role="dialog"
        aria-labelledby="ticket-stub-title"
        aria-modal="true"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="tab-title-row">
          <div>
            <p className="eyebrow">Door staff</p>
            <h3 id="ticket-stub-title">Ticket stub</h3>
            <p className="muted">
              Generate a code for each guest at the door. They enter it in the app when they tap I'm here.
            </p>
          </div>
          <button className="secondary compact" type="button" onClick={onClose}>Close</button>
        </div>

        {ticketedShows.length === 0 && (
          <p className="muted">No confirmed ticketed shows yet.</p>
        )}

        <div className="ticket-stub-list">
          {ticketedShows.map(booking => {
            const active = activeStubs[booking.id];
            return (
              <article className="ticket-stub-row" key={booking.id}>
                <div>
                  <strong>{booking.artist_name || booking.artist_username}</strong>
                  <p className="muted">
                    {booking.listing?.name} · {formatShowDate(booking.starts_at)}
                  </p>
                  <p className="muted form-hint">
                    {booking.tickets_sold || 0} sold · {booking.stubs_redeemed ?? active?.stubs_redeemed ?? 0} checked in
                  </p>
                </div>
                <div className="ticket-stub-row-actions">
                  {active?.stub_code ? (
                    <div className="ticket-stub-code-panel">
                      <p className="eyebrow">Give guest this code</p>
                      <p className="ticket-stub-code" aria-label="Ticket stub code">{active.stub_code}</p>
                    </div>
                  ) : null}
                  <button
                    className="primary compact"
                    type="button"
                    disabled={generatingId === booking.id}
                    onClick={() => generateStub(booking.id)}
                  >
                    {generatingId === booking.id ? "Generating…" : active?.stub_code ? "New code" : "Generate code"}
                  </button>
                </div>
              </article>
            );
          })}
        </div>
      </div>
    </div>
  );
}
