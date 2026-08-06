import React, { useState } from "react";
import { ArtistNameLink } from "./ArtistNameLink.jsx";
import { TrackNameLink } from "./TrackNameLink.jsx";

export function PlaylistPickerSheet({
  track,
  playlists = [],
  onClose,
  onCreatePlaylist,
  onOpenArtist,
  onSelectPlaylist,
}) {
  const [title, setTitle] = useState("");
  const [creating, setCreating] = useState(false);

  if (!track) return null;

  async function handleCreate(event) {
    event.preventDefault();
    if (!title.trim() || creating) return;

    setCreating(true);
    try {
      await onCreatePlaylist({ title: title.trim() });
      setTitle("");
    } finally {
      setCreating(false);
    }
  }

  return (
    <div className="modal-backdrop" role="presentation" onClick={onClose}>
      <section
        className="support-sheet playlist-picker-sheet"
        role="dialog"
        aria-modal="true"
        aria-labelledby="playlist-picker-title"
        onClick={event => event.stopPropagation()}
      >
        <button className="sheet-close" onClick={onClose} aria-label="Close playlist picker">
          ×
        </button>
        <h2 id="playlist-picker-title">Add to playlist</h2>
        <p className="muted">
          Save <TrackNameLink track={track} onOpenArtist={onOpenArtist} className="track-name-link" /> by{" "}
          <ArtistNameLink username={track.artist_username} onOpenArtist={onOpenArtist} /> to one of your playlists.
        </p>

        {playlists.length > 0 ? (
          <div className="playlist-picker-list">
            {playlists.map(playlist => (
              <button
                key={playlist.id}
                className="playlist-picker-row"
                onClick={() => onSelectPlaylist(playlist.id)}
              >
                <strong>{playlist.title}</strong>
                <span>{playlist.track_count} tracks</span>
              </button>
            ))}
          </div>
        ) : (
          <div className="empty-state compact-empty">
            <p className="muted">Create your first playlist to start saving tracks.</p>
          </div>
        )}

        <form className="playlist-picker-create" onSubmit={handleCreate}>
          <label htmlFor="playlist-picker-title-input">New playlist</label>
          <div className="playlist-picker-create-row">
            <input
              id="playlist-picker-title-input"
              value={title}
              onChange={event => setTitle(event.target.value)}
              placeholder="Playlist name"
              maxLength="120"
            />
            <button className="secondary compact" type="submit" disabled={!title.trim() || creating}>
              {creating ? "Creating..." : "Create"}
            </button>
          </div>
        </form>
      </section>
    </div>
  );
}

export function ExternalLinkConfirm({
  askBeforeExternalSocial,
  link,
  onClose,
  onOpen,
  onPreferenceChange,
}) {
  if (!link) return null;

  return (
    <div className="modal-backdrop" role="presentation" onClick={onClose}>
      <section
        className="support-sheet"
        role="dialog"
        aria-modal="true"
        aria-labelledby="external-link-title"
        onClick={event => event.stopPropagation()}
      >
        <button
          className="sheet-close"
          onClick={onClose}
          aria-label="Stay on IndieFund"
        >
          ×
        </button>
        <h2 id="external-link-title">Open {link.provider}?</h2>
        <p className="muted">This opens the artist's original social post or profile in a new tab.</p>
        <label className="check-row preference-row">
          <input
            type="checkbox"
            checked={askBeforeExternalSocial}
            onChange={event => onPreferenceChange(event.target.checked)}
          />
          Always ask before opening external social links
        </label>
        <div className="sheet-actions">
          <button className="secondary" onClick={onClose}>Stay Here</button>
          <button className="primary" onClick={onOpen}>Open Link</button>
        </div>
      </section>
    </div>
  );
}

export function SupportConfirmSheet({
  artist,
  demoMode = true,
  emailShareChecked = false,
  onEmailShareChange,
  onCancel,
  onConfirm,
  onTierChange,
  professionLabel = "Music",
  selectedTierId = "",
  tiers = [],
}) {
  if (!artist) return null;
  const selectedTier = tiers.find(tier => String(tier.id) === String(selectedTierId));
  const monthlyAmount = selectedTier?.monthly_amount || "1.00";
  const artistShare = selectedTier?.artist_share || "0.90";
  const platformFee = selectedTier?.platform_fee || "0.10";

  return (
    <div className="modal-backdrop" role="presentation" onClick={onCancel}>
      <section
        className="support-sheet"
        role="dialog"
        aria-modal="true"
        aria-labelledby="support-sheet-title"
        onClick={event => event.stopPropagation()}
      >
        <button
          className="sheet-close"
          onClick={onCancel}
          aria-label="Cancel support"
        >
          ×
        </button>
        <div className="sheet-dollar">$</div>
        <h2 id="support-sheet-title">Support {artist.stage_name}'s {professionLabel}?</h2>
        <p className="muted">Start monthly support for this creative profile. Supporting one profile does not unlock the artist's other profiles.</p>
        {demoMode && (
          <p className="demo-payment-note">Beta mode: this activates demo support locally. Real billing starts when Stripe is configured.</p>
        )}
        {tiers.length > 0 && (
          <div className="tier-picker-list">
            <label>Choose support tier</label>
            <select value={selectedTierId} onChange={event => onTierChange(event.target.value)}>
              <option value="">$1 Supporter</option>
              {tiers.map(tier => (
                <option key={tier.id} value={tier.id}>
                  {tier.name} - ${tier.monthly_amount}/month
                </option>
              ))}
            </select>
            {selectedTier?.benefits && <p className="muted">{selectedTier.benefits}</p>}
          </div>
        )}
        {onEmailShareChange && (
          <label className="check-row preference-row">
            <input
              type="checkbox"
              checked={emailShareChecked}
              onChange={event => onEmailShareChange(event.target.checked)}
            />
            Share my email with this artist
          </label>
        )}
        <div className="support-breakdown">
          <span>Monthly total</span>
          <strong>${monthlyAmount}</strong>
          <span>Artist share</span>
          <strong>${artistShare}</strong>
          <span>Platform share</span>
          <strong>${platformFee}</strong>
        </div>
        <div className="sheet-actions">
          <button className="secondary" onClick={onCancel}>Cancel</button>
          <button className="primary" onClick={onConfirm}>Confirm support</button>
        </div>
      </section>
    </div>
  );
}

const SIGNUP_GATE_COPY = {
  follow: {
    title: name => (name ? `Follow ${name} for free` : "Follow artists for free"),
    body: "Create a free fan account to follow artists, build your feed, and hear about drops, shows and listening parties first.",
  },
  discover: {
    title: () => "Make discovery yours",
    body: "Create a free fan account so discovery learns your taste and keeps surfacing artists you'll actually love.",
  },
  support: {
    title: name => (name ? `Support ${name} directly` : "Support artists directly"),
    body: "Create a free fan account to support artists from $1/month or send tips — the vast majority of every dollar goes straight to the artist.",
  },
  engage: {
    title: () => "Join the conversation",
    body: "Create a free fan account to like posts, comment, and be part of the artist's scene.",
  },
  shop: {
    title: name => (name ? `Buy directly from ${name}` : "Buy directly from artists"),
    body: "Create a free fan account to buy music, merch and tickets directly — artists keep more than on any big platform.",
  },
  tickets: {
    title: () => "See shows near you",
    body: "Create a free fan account to browse local gigs, buy tickets, and check in at the door.",
  },
  default: {
    title: () => "Create your free fan account",
    body: "Follow artists, unlock full tracks, buy direct, and join live listening parties — free, no ads, no tracking.",
  },
};

export function SignupGateSheet({ gate, onCancel, onLogin, onSignup }) {
  if (!gate) return null;
  const copy = SIGNUP_GATE_COPY[gate.type] || SIGNUP_GATE_COPY.default;

  return (
    <div className="modal-backdrop" role="presentation" onClick={onCancel}>
      <section
        className="support-sheet signup-gate-sheet"
        role="dialog"
        aria-modal="true"
        aria-labelledby="signup-gate-title"
        onClick={event => event.stopPropagation()}
      >
        <button className="sheet-close" onClick={onCancel} aria-label="Not now">
          ×
        </button>
        <h2 id="signup-gate-title">{copy.title(gate.artistName)}</h2>
        <p className="muted">{copy.body}</p>
        <p className="signup-gate-promise">Free forever · No ads · We pick up where you left off</p>
        <div className="sheet-actions signup-gate-actions">
          <button className="primary" onClick={onSignup}>Create free fan account</button>
          <button className="secondary" onClick={onLogin}>I already have an account</button>
        </div>
      </section>
    </div>
  );
}

export function ProductTypePicker({ onClose, onSelect, filter }) {
  const allCategories = [
    {
      id: "music",
      title: "Music Store",
      types: [
        { id: "digital_download", label: "Digital Music" },
        { id: "vinyl", label: "Vinyl" },
        { id: "cassette", label: "Cassette" },
        { id: "beat", label: "Beat" },
        { id: "event_ticket", label: "Event Ticket" },
      ],
    },
    {
      id: "merch",
      title: "Merch Store",
      types: [
        { id: "merch", label: "Physical Merch" },
      ],
    },
    {
      id: "perks",
      title: "Supporter Perks",
      types: [
        { id: "membership_merch", label: "Subscriber Reward" },
      ],
    },
    {
      id: "pod",
      title: "Print on Demand",
      types: [
        { id: "gelato_pod", label: "Gelato POD" },
        { id: "printify_pod", label: "Printify POD" },
        { id: "printful_pod", label: "Printful POD" },
      ],
    },
    {
      id: "integrations",
      title: "Integrations",
      types: [
        { id: "shopify_store", label: "Shopify Store" },
        { id: "fourthwall_store", label: "Fourthwall" },
        { id: "bandcamp_store", label: "Bandcamp" },
        { id: "external_fulfillment", label: "External Link" },
      ],
    },
  ];

  const categories = filter 
    ? allCategories.filter(cat => filter.includes(cat.id))
    : allCategories;

  const isMusicOnly = filter?.includes("music") && !filter?.includes("merch");

  return (
    <div className="modal-backdrop" role="presentation" onClick={onClose}>
      <section
        className="support-sheet type-picker-sheet"
        role="dialog"
        aria-modal="true"
        onClick={event => event.stopPropagation()}
      >
        <button className="sheet-close" onClick={onClose}>×</button>
        <h2>Add to {isMusicOnly ? "Music Store" : "Merch Store"}</h2>
        <p className="muted">Choose how you want to sell or deliver content.</p>

        <div className="type-picker-grid">
          {categories.map(cat => (
            <div key={cat.title} className="store-category-section">
              <h4>{cat.title}</h4>
              <div className="store-button-list">
                {cat.types.map(type => (
                  <button
                    key={type.id}
                    className="secondary"
                    onClick={() => onSelect(type.id)}
                  >
                    {type.label}
                  </button>
                ))}
              </div>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}

export function PreviewBeforeShareSheet({ onClose, onPreview }) {
  return (
    <div className="modal-backdrop" role="presentation" onClick={onClose}>
      <section
        className="support-sheet preview-before-share-sheet"
        role="dialog"
        aria-modal="true"
        aria-labelledby="preview-before-share-title"
        onClick={event => event.stopPropagation()}
      >
        <button className="sheet-close" type="button" onClick={onClose} aria-label="Close">
          ×
        </button>
        <p className="eyebrow">Before you share</p>
        <h2 id="preview-before-share-title">Preview your page as a fan</h2>
        <p className="muted">
          Walk through your public artist page the way supporters will see it — then copy your invite link with confidence.
        </p>
        <div className="sheet-actions">
          <button className="secondary" type="button" onClick={onClose}>Not yet</button>
          <button className="primary" type="button" onClick={onPreview}>Preview as fan</button>
        </div>
      </section>
    </div>
  );
}
