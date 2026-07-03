import React, { useMemo, useState } from "react";

const TARGET_TYPES = [
  { id: "track", label: "Track / release" },
  { id: "profile", label: "Artist profile" },
  { id: "post", label: "Post" },
  { id: "product", label: "Store item" },
];

function formatMoney(value) {
  const amount = Number(value || 0);
  return Number.isFinite(amount) ? amount.toFixed(2) : "0.00";
}

function formatLedgerLabel(entry) {
  const labels = {
    purchase: "Credit purchase",
    grant: "Plan credits",
    spend: "Campaign reserve",
    reward: "Discovery reward",
    refund: "Budget refund",
    redeem: "Credit redeemed",
  };
  return labels[entry.entry_type] || entry.entry_type;
}

function renderWalletLedger(entries = [], limit = 8) {
  if (!entries.length) {
    return <p className="muted">No wallet activity yet.</p>;
  }
  return (
    <ul className="promote-ledger-list">
      {entries.slice(0, limit).map(entry => (
        <li key={entry.id}>
          <div>
            <strong>{formatLedgerLabel(entry)}</strong>
            <span className="muted">{entry.description || ""}</span>
          </div>
          <span className={Number(entry.amount) >= 0 ? "ledger-credit" : "ledger-debit"}>
            {Number(entry.amount) >= 0 ? "+" : ""}${formatMoney(entry.amount)}
          </span>
        </li>
      ))}
    </ul>
  );
}

function statusLabel(status) {
  return {
    draft: "Draft",
    active: "Active",
    paused: "Paused",
    completed: "Completed",
    cancelled: "Cancelled",
  }[status] || status;
}

export function PromotePage({
  currentUser,
  music = [],
  posts = [],
  products = [],
  wallet = null,
  campaigns = [],
  genres = [],
  targetingSuggestions = null,
  onSearchTargetArtists,
  onLoadTargetingSuggestions,
  artistProfile = null,
  onBuyCredits,
  onCreateCampaign,
  onCampaignAction,
  onUpgradePlan,
}) {
  const [targetType, setTargetType] = useState("track");
  const [targetId, setTargetId] = useState("");
  const [budget, setBudget] = useState("25");
  const [targetGenres, setTargetGenres] = useState("");
  const [targetLocation, setTargetLocation] = useState(artistProfile?.city || currentUser?.discovery_location || "");
  const [selectedArtistIds, setSelectedArtistIds] = useState([]);
  const [artistSearch, setArtistSearch] = useState("");
  const [artistSearchResults, setArtistSearchResults] = useState([]);
  const [creditAmount, setCreditAmount] = useState("25");
  const [busy, setBusy] = useState(false);

  const maxSimilarArtists = targetingSuggestions?.max_similar_artists || 5;
  const suggestedArtists = targetingSuggestions?.similar_artists || [];

  const selectedArtists = useMemo(() => {
    const byId = new Map(suggestedArtists.map(item => [item.owner_id, item]));
    for (const item of artistSearchResults) {
      byId.set(item.owner_id, item);
    }
    return selectedArtistIds
      .map(id => byId.get(id))
      .filter(Boolean);
  }, [selectedArtistIds, suggestedArtists, artistSearchResults]);

  function toggleSimilarArtist(artistId) {
    setSelectedArtistIds(current => {
      if (current.includes(artistId)) {
        return current.filter(id => id !== artistId);
      }
      if (current.length >= maxSimilarArtists) {
        return current;
      }
      return [...current, artistId];
    });
  }

  async function applySuggestedTargeting() {
    let suggestions = targetingSuggestions;
    if (!suggestions) {
      suggestions = await onLoadTargetingSuggestions?.(targetType === "track" ? targetId : null);
    }
    if (!suggestions) return;
    if (suggestions.target_genres) {
      setTargetGenres(suggestions.target_genres);
    }
    if (suggestions.target_location) {
      setTargetLocation(suggestions.target_location);
    }
    if (suggestions.suggested_artist_ids?.length) {
      setSelectedArtistIds(suggestions.suggested_artist_ids.slice(0, maxSimilarArtists));
    }
  }

  async function handleArtistSearch(query) {
    setArtistSearch(query);
    if (!query || query.trim().length < 2) {
      setArtistSearchResults([]);
      return;
    }
    const results = await onSearchTargetArtists?.(query.trim());
    setArtistSearchResults(results || []);
  }

  const myTracks = useMemo(
    () => music.filter(track => track.artist_username === currentUser?.username),
    [music, currentUser?.username],
  );
  const myPosts = useMemo(
    () => posts.filter(post => post.author_username === currentUser?.username),
    [posts, currentUser?.username],
  );
  const myProducts = useMemo(
    () => products.filter(product => product.artist === currentUser?.username || product.artist_username === currentUser?.username),
    [products, currentUser?.username],
  );

  const targetOptions = useMemo(() => {
    if (targetType === "track") {
      return myTracks.map(track => ({ id: String(track.id), label: track.title }));
    }
    if (targetType === "post") {
      return myPosts.map(post => ({ id: String(post.id), label: post.title || "Untitled post" }));
    }
    if (targetType === "product") {
      return myProducts.map(product => ({ id: String(product.id), label: product.title }));
    }
    if (targetType === "profile") {
      return [{ id: String(currentUser?.id || ""), label: artistProfile?.stage_name || currentUser?.username || "My profile" }];
    }
    return [];
  }, [targetType, myTracks, myPosts, myProducts, currentUser, artistProfile]);

  async function handleBuyCredits(event) {
    event.preventDefault();
    setBusy(true);
    try {
      await onBuyCredits?.(creditAmount);
    } finally {
      setBusy(false);
    }
  }

  async function handleCreateCampaign(event) {
    event.preventDefault();
    const resolvedTargetId = targetType === "profile"
      ? currentUser?.id
      : targetId;
    if (!resolvedTargetId) return;
    setBusy(true);
    try {
      await onCreateCampaign?.({
        target_type: targetType,
        target_id: resolvedTargetId,
        budget,
        target_genres: targetGenres,
        target_location: targetLocation,
        target_artist_ids: selectedArtistIds,
      });
    } finally {
      setBusy(false);
    }
  }

  async function handleCampaignAction(campaignId, action) {
    setBusy(true);
    try {
      await onCampaignAction?.(campaignId, action);
    } finally {
      setBusy(false);
    }
  }

  if (!currentUser?.is_artist) {
    return (
      <div className="empty-state">
        <h3>Artist account required</h3>
        <p>Discovery promotions are available to artists who want to reach new fans.</p>
      </div>
    );
  }

  const balance = wallet?.balance || "0.00";
  const maxBudget = wallet?.max_budget || "100.00";
  const tagline = wallet?.tagline || `No artist can spend more than $${maxBudget} on a campaign. The audience decides what spreads next.`;
  const cooldownDays = wallet?.invariants?.cooldown_days || 3;

  return (
    <>
      <section className="section-head">
        <div>
          <p className="eyebrow">Discovery Ads</p>
          <h2>Promote your release</h2>
        </div>
        <p>
          {tagline}
        </p>
      </section>

      <section className="promote-grid">
        <div className="feature-card promote-wallet-card">
          <p className="eyebrow">Promotion wallet</p>
          <h3>${formatMoney(balance)}</h3>
          <p className="muted">
            Budget is reserved when a campaign launches. You are only charged for real fan engagement; unused budget returns if you cancel.
          </p>
          {currentUser.artist_plan === "studio" && (
            <p className="promote-studio-note">Studio plan includes $25/month in promotion credits.</p>
          )}
          {currentUser.artist_plan !== "studio" && onUpgradePlan && (
            <button className="secondary compact" type="button" onClick={() => onUpgradePlan("studio")}>
              Try Studio (demo) for monthly credits
            </button>
          )}
          <form className="promote-inline-form" onSubmit={handleBuyCredits}>
            <input
              type="number"
              min="5"
              max="100"
              step="1"
              value={creditAmount}
              onChange={event => setCreditAmount(event.target.value)}
              placeholder="Amount"
            />
            <button className="primary compact" type="submit" disabled={busy}>Add credits</button>
          </form>
          <div className="promote-ledger-wrap">
            <p className="eyebrow">Recent activity</p>
            {renderWalletLedger(wallet?.entries || [])}
          </div>
        </div>

        <div className="feature-card promote-rules-card">
          <p className="eyebrow">Fair discovery rules</p>
          <ul className="promote-rules-list">
            <li>Max ${maxBudget} per campaign</li>
            <li>Up to {wallet?.max_active || 4} active campaigns</li>
            <li>{cooldownDays}-day cooldown after each campaign finishes</li>
            <li>No bidding wars — fan response decides reach</li>
            <li>Charged on full listens, saves, follows, shares, purchases, positive feedback</li>
          </ul>
        </div>
      </section>

      <section className="feature-card promote-create-card">
        <div className="tab-title-row">
          <div>
            <p className="eyebrow">New campaign</p>
            <h3>Reach fans who do not know you yet</h3>
          </div>
        </div>
        <form className="promote-form" onSubmit={handleCreateCampaign}>
          <div className="promote-targeting-actions">
            <button className="secondary compact" type="button" disabled={busy} onClick={applySuggestedTargeting}>
              Suggest targeting
            </button>
            <p className="muted">Uses your genre, city, and artists your fans also support.</p>
          </div>

          <label>
            Promote
            <select value={targetType} onChange={event => { setTargetType(event.target.value); setTargetId(""); }}>
              {TARGET_TYPES.map(item => (
                <option key={item.id} value={item.id}>{item.label}</option>
              ))}
            </select>
          </label>

          {targetType !== "profile" && (
            <label>
              Item
              <select value={targetId} onChange={event => setTargetId(event.target.value)} required>
                <option value="">Choose…</option>
                {targetOptions.map(item => (
                  <option key={item.id} value={item.id}>{item.label}</option>
                ))}
              </select>
            </label>
          )}

          <label>
            Campaign budget (max ${maxBudget})
            <input
              type="number"
              min="5"
              max={maxBudget}
              step="1"
              value={budget}
              onChange={event => setBudget(event.target.value)}
              required
            />
          </label>

          <label>
            Target genres
            <input
              value={targetGenres}
              onChange={event => setTargetGenres(event.target.value)}
              placeholder="hip-hop, boom-bap, electronic"
              list="promote-genre-suggestions"
            />
            <datalist id="promote-genre-suggestions">
              {genres.map(genre => (
                <option key={genre.slug} value={genre.name} />
              ))}
            </datalist>
          </label>

          <label>
            Target city (optional)
            <input
              value={targetLocation}
              onChange={event => setTargetLocation(event.target.value)}
              placeholder="Melbourne"
            />
          </label>

          <div className="promote-similar-artists">
            <div className="promote-similar-head">
              <span>Reach fans who support similar artists</span>
              <span className="muted">{selectedArtistIds.length}/{maxSimilarArtists} selected</span>
            </div>
            {suggestedArtists.length > 0 ? (
              <div className="promote-similar-grid">
                {suggestedArtists.map(artist => {
                  const selected = selectedArtistIds.includes(artist.owner_id);
                  return (
                    <button
                      key={artist.owner_id}
                      type="button"
                      className={`promote-similar-chip${selected ? " is-selected" : ""}`}
                      disabled={!selected && selectedArtistIds.length >= maxSimilarArtists}
                      onClick={() => toggleSimilarArtist(artist.owner_id)}
                    >
                      <strong>{artist.stage_name}</strong>
                      <span>{artist.reason || artist.genre || "Suggested"}</span>
                    </button>
                  );
                })}
              </div>
            ) : (
              <p className="muted">Suggestions appear once you have fans or shared-genre peers on the platform.</p>
            )}

            <label>
              Search artists
              <input
                value={artistSearch}
                onChange={event => handleArtistSearch(event.target.value)}
                placeholder="Search by name or genre"
              />
            </label>
            {artistSearchResults.length > 0 && (
              <div className="promote-similar-grid">
                {artistSearchResults.map(artist => {
                  const selected = selectedArtistIds.includes(artist.owner_id);
                  return (
                    <button
                      key={`search-${artist.owner_id}`}
                      type="button"
                      className={`promote-similar-chip${selected ? " is-selected" : ""}`}
                      disabled={!selected && selectedArtistIds.length >= maxSimilarArtists}
                      onClick={() => toggleSimilarArtist(artist.owner_id)}
                    >
                      <strong>{artist.stage_name}</strong>
                      <span>{artist.genre || "Artist"}</span>
                    </button>
                  );
                })}
              </div>
            )}

            {selectedArtists.length > 0 && (
              <p className="muted">
                Targeting fans who follow or support {selectedArtists.map(item => item.stage_name).join(", ")}.
              </p>
            )}
          </div>

          <button className="primary" type="submit" disabled={busy || targetOptions.length === 0}>
            Launch campaign
          </button>
        </form>
      </section>

      <section className="home-activity">
        <div className="tab-title-row">
          <div>
            <p className="eyebrow">Your campaigns</p>
            <h3>Performance</h3>
          </div>
        </div>

        {campaigns.length === 0 ? (
          <div className="empty-state compact-empty">
            <h3>No campaigns yet.</h3>
            <p>Promote a track to reach fans who match your genre and location.</p>
          </div>
        ) : (
          <div className="promote-campaign-list">
            {campaigns.map(campaign => (
              <article className="feature-card promote-campaign-card" key={campaign.id}>
                <div className="promote-campaign-head">
                  <div>
                    <span className={`promote-status promote-status-${campaign.status}`}>{statusLabel(campaign.status)}</span>
                    <h4>{campaign.title || `${campaign.target_type} #${campaign.target_id}`}</h4>
                    <p className="muted">
                      ${formatMoney(campaign.spent)} spent · ${formatMoney(campaign.remaining_budget)} left · score {campaign.discovery_score || 0}
                      {campaign.target_artists?.length > 0 && (
                        <> · fans of {campaign.target_artists.map(item => item.stage_name).join(", ")}</>
                      )}
                      {campaign.status === "draft" && campaign.shortfall && (
                        <> · needs ${formatMoney(campaign.shortfall)} more</>
                      )}
                    </p>
                  </div>
                  <div className="promote-campaign-actions">
                    {campaign.status === "draft" && (
                      <button
                        className="primary compact"
                        type="button"
                        disabled={busy}
                        onClick={() => handleCampaignAction(campaign.id, "launch")}
                      >
                        Launch now
                      </button>
                    )}
                    {campaign.status === "active" && (
                      <button className="secondary compact" type="button" disabled={busy} onClick={() => handleCampaignAction(campaign.id, "pause")}>Pause</button>
                    )}
                    {campaign.status === "paused" && (
                      <button className="secondary compact" type="button" disabled={busy} onClick={() => handleCampaignAction(campaign.id, "resume")}>Resume</button>
                    )}
                    {["active", "paused", "draft"].includes(campaign.status) && (
                      <button className="secondary compact" type="button" disabled={busy} onClick={() => handleCampaignAction(campaign.id, "cancel")}>Cancel</button>
                    )}
                  </div>
                </div>

                {campaign.analytics && (
                  <div className="promote-analytics-grid">
                    <div><strong>{campaign.analytics.impressions || 0}</strong><span>Impressions</span></div>
                    <div><strong>{campaign.analytics.full_listens || 0}</strong><span>Full listens</span></div>
                    <div><strong>{campaign.analytics.saves || 0}</strong><span>Saves</span></div>
                    <div><strong>{campaign.analytics.follows || 0}</strong><span>Follows</span></div>
                    <div><strong>{campaign.analytics.purchases || 0}</strong><span>Purchases</span></div>
                    <div><strong>{campaign.analytics.cost_per_follower ? `$${campaign.analytics.cost_per_follower}` : "—"}</strong><span>Cost / follow</span></div>
                  </div>
                )}
              </article>
            ))}
          </div>
        )}
      </section>
    </>
  );
}
