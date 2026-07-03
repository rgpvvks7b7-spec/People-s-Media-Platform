import React, { useEffect, useState } from "react";
import { ArtistNameLink } from "./ArtistNameLink.jsx";

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

function buildCalendarUrl(show) {
  if (!show?.starts_at) return "";
  const start = new Date(show.starts_at);
  const end = show.ends_at ? new Date(show.ends_at) : new Date(start.getTime() + 2 * 60 * 60 * 1000);
  const stamp = (date) => date.toISOString().replace(/[-:]/g, "").split(".")[0] + "Z";
  const params = new URLSearchParams({
    action: "TEMPLATE",
    text: `${show.stage_name} @ ${show.venue_name}`,
    dates: `${stamp(start)}/${stamp(end)}`,
    details: show.pitch || `Live show with ${show.stage_name}`,
    location: [show.venue_name, show.venue_address, show.venue_city].filter(Boolean).join(", "),
  });
  return `https://calendar.google.com/calendar/render?${params.toString()}`;
}

function resolveShowTicket(show, products = []) {
  if (!show) return null;
  if (show.ticket?.id) return show.ticket;
  if (show.ticket_product_id) {
    return products.find(item => item.id === show.ticket_product_id) || {
      id: show.ticket_product_id,
      title: "Event ticket",
      price: show.ticket?.price || "0.00",
    };
  }
  return null;
}

function ticketPriceLabel(ticket) {
  const amount = Number(ticket?.price || 0);
  if (!Number.isFinite(amount) || amount <= 0) return "Free";
  return `$${ticket.price}`;
}

function ShowCard({ show, onOpen, onOpenArtist, onOpenArtistByUsername, onPurchaseTicket, ownedTicketProductIds = new Set() }) {
  const ticket = resolveShowTicket(show);
  const ownsTicket = show.owns_ticket || (ticket && ownedTicketProductIds.has(ticket.id));
  const soldOut = ticket?.sold_out || show.ticket_availability?.sold_out;
  const priceLabel = ticket ? ticketPriceLabel(ticket) : "";

  return (
    <article className="activity-item my-scene-card">
      <span>{show.is_supported ? "supported" : "live"}</span>
      <div>
        <strong>
          <ArtistNameLink
            username={show.artist_username}
            label={show.stage_name}
            onOpenArtist={onOpenArtistByUsername}
            stopPropagation
          />
          {" @ "}{show.venue_name}
        </strong>
        <p>
          {formatShowDate(show.starts_at)} · {show.venue_city}
          {show.bar_open ? " · bar open" : ""}
          {show.kitchen_open ? " · kitchen open" : ""}
        </p>
        {show.is_supported && <small className="support-badge">Artist you support</small>}
        {ticket && !ownsTicket && !soldOut && <small className="ticket-price-hint">Cover · {priceLabel}</small>}
        {ticket && !ownsTicket && soldOut && <small className="support-badge">Sold out</small>}
        {ownsTicket && <small className="support-badge">Ticket confirmed</small>}
      </div>
      <div className="my-scene-card-actions">
        {ticket && !ownsTicket && !soldOut && (
          <button className="primary compact" type="button" onClick={() => onPurchaseTicket(ticket, show)}>
            {Number(ticket.price) > 0 ? `Buy ticket · ${priceLabel}` : "Get free ticket"}
          </button>
        )}
        <button className="secondary compact" type="button" onClick={() => onOpen(show)}>Details</button>
        <button className="secondary compact" type="button" onClick={() => onOpenArtist(show)}>Artist</button>
      </div>
    </article>
  );
}

export function MyScenePage({
  apiFetch,
  currentUser,
  initialShowId = "",
  fanChannelUsername = "",
  onGoToProfile,
  onOpenArtistByUsername,
  onOpenArtistFromGig,
  onPurchaseTicket,
  ownedTicketProductIds = new Set(),
  products = [],
  refreshSignal = 0,
}) {
  const [sceneData, setSceneData] = useState({
    location: "",
    all_shows: [],
    supported_shows: [],
    counts: { all: 0, supported: 0 },
    needs_location: false,
  });
  const [activeTab, setActiveTab] = useState("supported");
  const [selectedShow, setSelectedShow] = useState(null);
  const [showLoadError, setShowLoadError] = useState("");
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [checkInOpen, setCheckInOpen] = useState(false);
  const [stubCodeInput, setStubCodeInput] = useState("");
  const [checkInError, setCheckInError] = useState("");
  const [checkInSaving, setCheckInSaving] = useState(false);
  const [searchLocation, setSearchLocation] = useState(currentUser?.discovery_location || "");
  const [appliedLocation, setAppliedLocation] = useState(currentUser?.discovery_location || "");

  const shows = (activeTab === "supported" ? sceneData.supported_shows : sceneData.all_shows)
    .filter(show => !fanChannelUsername || show.artist_username === fanChannelUsername);
  const ticketProduct = resolveShowTicket(selectedShow, products);
  const ownsSelectedTicket = selectedShow?.owns_ticket || (ticketProduct && ownedTicketProductIds.has(ticketProduct.id));
  const ticketSoldOut = ticketProduct?.sold_out || selectedShow?.ticket_availability?.sold_out;
  const ticketPrice = ticketProduct ? ticketPriceLabel(ticketProduct) : "";

  useEffect(() => {
    const profileLocation = currentUser?.discovery_location || "";
    if (!currentUser) return;
    setSearchLocation(profileLocation);
    setAppliedLocation(current => current.trim() || profileLocation);
  }, [currentUser?.id, currentUser?.discovery_location]);

  useEffect(() => {
    let cancelled = false;

    async function loadScene() {
      setLoading(true);
      setLoadError("");
      try {
        const query = appliedLocation.trim()
          ? `?location=${encodeURIComponent(appliedLocation.trim())}`
          : "";
        const res = await apiFetch(`/discovery/my-scene/${query}`);
        if (!res.ok) {
          const data = await res.json().catch(() => ({}));
          throw new Error(data.error || "Could not load your scene.");
        }
        const data = await res.json();
        if (!cancelled) setSceneData(data);
      } catch (error) {
        if (!cancelled) setLoadError(error.message || "Could not load your scene.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    if (currentUser) loadScene();
    return () => {
      cancelled = true;
    };
  }, [apiFetch, appliedLocation, currentUser, refreshSignal]);

  useEffect(() => {
    if (!initialShowId || !currentUser) return;
    let cancelled = false;

    async function openInitialShow() {
      setShowLoadError("");
      const res = await apiFetch(`/discovery/shows/${initialShowId}/`);
      if (cancelled) return;
      if (!res.ok) {
        setShowLoadError("That show is no longer available.");
        return;
      }
      const data = await res.json();
      if (data?.show) setSelectedShow(data.show);
    }

    openInitialShow();
    return () => {
      cancelled = true;
    };
  }, [apiFetch, currentUser, initialShowId]);

  function closeShowDetails() {
    setSelectedShow(null);
    setCheckInOpen(false);
    setStubCodeInput("");
    setCheckInError("");
  }

  async function submitCheckIn(event) {
    event.preventDefault();
    if (!selectedShow?.booking_id) return;
    const stubCode = stubCodeInput.trim();
    if (!stubCode) {
      setCheckInError("Enter the code staff gave you at the door.");
      return;
    }
    setCheckInSaving(true);
    setCheckInError("");
    try {
      const res = await apiFetch(`/spaces/bookings/${selectedShow.booking_id}/check-in/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ stub_code: stubCode }),
      });
      const data = await res.json();
      if (!res.ok) {
        setCheckInError(data.error || "Check-in failed.");
        return;
      }
      setSelectedShow(prev => prev ? { ...prev, checked_in: true, can_check_in: false } : prev);
      setCheckInOpen(false);
      setStubCodeInput("");
    } catch {
      setCheckInError("Check-in failed.");
    } finally {
      setCheckInSaving(false);
    }
  }

  async function openShow(show) {
    setSelectedShow(show);
    const res = await apiFetch(`/discovery/shows/${show.booking_id}/`);
    if (res.ok) {
      const data = await res.json();
      if (data?.show) setSelectedShow(data.show);
    }
  }

  function applyLocation(event) {
    event.preventDefault();
    setAppliedLocation(searchLocation.trim());
  }

  if (!currentUser) {
    return (
      <section className="space-panel">
        <h2>My Scene</h2>
        <p className="muted">Sign in to see local shows from artists you support.</p>
        <button className="primary" type="button" onClick={onGoToProfile}>Sign up or log in</button>
      </section>
    );
  }

  return (
    <div className="my-scene-page">
      <section className="section-head tab-title-row">
        <div>
          <p className="eyebrow">IndieFund | My Scene</p>
          <h2>Local shows near you</h2>
          <p className="muted">
            {appliedLocation
              ? `Showing gigs in ${appliedLocation}. At the door, staff will give you a code — tap I'm here to check in.`
              : "Set your city to see confirmed gigs nearby."}
          </p>
        </div>
        <button className="secondary compact" type="button" onClick={onGoToProfile}>Update location</button>
      </section>

      <form className="discovery-filter-row" onSubmit={applyLocation}>
        <input
          value={searchLocation}
          onChange={event => setSearchLocation(event.target.value)}
          placeholder="City or neighborhood"
          aria-label="Search location"
        />
        <button className="primary compact" type="submit">Search</button>
      </form>

      <div className="tab-row">
        <button
          className={activeTab === "supported" ? "tab active" : "tab"}
          type="button"
          onClick={() => setActiveTab("supported")}
        >
          Artists you support ({sceneData.counts.supported})
        </button>
        <button
          className={activeTab === "all" ? "tab active" : "tab"}
          type="button"
          onClick={() => setActiveTab("all")}
        >
          All nearby ({sceneData.counts.all})
        </button>
      </div>

      {loading && <p className="muted">Loading shows…</p>}
      {loadError && <p className="form-error">{loadError}</p>}
      {showLoadError && <p className="form-error">{showLoadError}</p>}
      {!loading && !loadError && sceneData.needs_location && (
        <p className="muted">Add a discovery location in your profile to see local shows.</p>
      )}
      {!loading && !loadError && !sceneData.needs_location && shows.length === 0 && (
        <p className="muted">No confirmed shows in {appliedLocation || "your area"} yet.</p>
      )}

      <div className="activity-list">
        {shows.map(show => (
          <ShowCard
            key={show.booking_id}
            show={show}
            onOpen={openShow}
            onOpenArtist={onOpenArtistFromGig}
            onOpenArtistByUsername={onOpenArtistByUsername}
            onPurchaseTicket={onPurchaseTicket}
            ownedTicketProductIds={ownedTicketProductIds}
          />
        ))}
      </div>

      {selectedShow && (
        <div className="modal-backdrop" role="presentation" onClick={closeShowDetails}>
          <div className="support-sheet my-scene-detail-sheet" role="dialog" aria-modal="true" onClick={event => event.stopPropagation()}>
            <button className="sheet-close" type="button" onClick={closeShowDetails} aria-label="Close show details">×</button>
            <div className="tab-title-row">
              <div>
                <p className="eyebrow">Show details</p>
                <h3>
                  <ArtistNameLink
                    username={selectedShow.artist_username}
                    label={selectedShow.stage_name}
                    onOpenArtist={onOpenArtistByUsername}
                  />
                  {" @ "}{selectedShow.venue_name}
                </h3>
                <p>{formatShowDate(selectedShow.starts_at)} · {selectedShow.venue_city}</p>
              </div>
              <button className="secondary compact" type="button" onClick={closeShowDetails}>Close</button>
            </div>

            {selectedShow.has_ended && <p className="support-badge">This show has ended.</p>}
            {selectedShow.is_supported && <p className="support-badge">You support this artist</p>}
            {selectedShow.venue_address && <p><strong>Address:</strong> {selectedShow.venue_address}</p>}
            {selectedShow.host_business_name && <p><strong>Host:</strong> {selectedShow.host_business_name}</p>}
            {selectedShow.drink_minimum && <p><strong>Drink minimum:</strong> {selectedShow.drink_minimum}</p>}
            {selectedShow.last_call && <p><strong>Last call:</strong> {selectedShow.last_call}</p>}
            {selectedShow.pitch && <p>{selectedShow.pitch}</p>}
            {selectedShow.ticket_availability?.remaining != null && (
              <p className="muted form-hint">{selectedShow.ticket_availability.remaining} tickets left</p>
            )}

            <div className="my-scene-detail-actions">
              {selectedShow.has_ended ? (
                <p className="muted form-hint">
                  {ownsSelectedTicket ? "Thanks for coming — this show has wrapped." : "Tickets are closed for this show."}
                </p>
              ) : ticketProduct && !ownsSelectedTicket && !ticketSoldOut ? (
                <button className="primary" type="button" onClick={() => onPurchaseTicket(ticketProduct, selectedShow)}>
                  {Number(ticketProduct.price) > 0 ? `Buy ticket · ${ticketPrice}` : "Get free ticket"}
                </button>
              ) : ticketProduct && ticketSoldOut && !ownsSelectedTicket ? (
                <p className="support-badge">This show is sold out.</p>
              ) : ownsSelectedTicket ? (
                <>
                  <p className="support-badge">You have a ticket for this show.</p>
                  {selectedShow.checked_in ? (
                    <p className="muted form-hint">You are checked in. Enjoy the show.</p>
                  ) : selectedShow.can_check_in ? (
                    <button className="primary" type="button" onClick={() => setCheckInOpen(true)}>
                      I'm here
                    </button>
                  ) : (
                    <p className="muted form-hint">Check in opens when you arrive — staff will give you a code at the door.</p>
                  )}
                </>
              ) : (
                <p className="muted form-hint">Ticket details will appear once this show is confirmed.</p>
              )}
              <a className="secondary" href={buildCalendarUrl(selectedShow)} target="_blank" rel="noreferrer">Add to Google Calendar</a>
              <button className="secondary" type="button" onClick={() => onOpenArtistFromGig(selectedShow)}>View artist</button>
            </div>
          </div>
        </div>
      )}

      {checkInOpen && selectedShow && (
        <div className="modal-backdrop" role="presentation" onClick={() => setCheckInOpen(false)}>
          <form
            className="modal-panel check-in-modal"
            role="dialog"
            aria-labelledby="check-in-title"
            aria-modal="true"
            onClick={(event) => event.stopPropagation()}
            onSubmit={submitCheckIn}
          >
            <div className="tab-title-row">
              <div>
                <p className="eyebrow">At the door</p>
                <h3 id="check-in-title">I'm here</h3>
                <p className="muted">Enter the code door staff gave you to check in.</p>
              </div>
              <button className="secondary compact" type="button" onClick={() => setCheckInOpen(false)}>Close</button>
            </div>
            <label htmlFor="stub-code-input">Door code</label>
            <input
              id="stub-code-input"
              value={stubCodeInput}
              onChange={(event) => setStubCodeInput(event.target.value.toUpperCase().replace(/[^A-Z0-9]/g, ""))}
              placeholder="6-character code"
              autoComplete="off"
              spellCheck={false}
              maxLength={12}
            />
            {checkInError && <p className="form-error" role="alert">{checkInError}</p>}
            <button className="primary" type="submit" disabled={checkInSaving}>
              {checkInSaving ? "Checking in…" : "Check in"}
            </button>
          </form>
        </div>
      )}
    </div>
  );
}
