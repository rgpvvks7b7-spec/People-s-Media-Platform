import React, { useMemo, useState } from "react";
import { ArtistNameLink } from "./ArtistNameLink.jsx";
import { ProfileSettingsNav } from "./ProfileSettingsNav.jsx";
import { getSettingsSectionsForUser } from "../lib/profileSettings.js";

function renderWalletLedger(entries = [], limit = 6) {
  if (!entries.length) return null;
  return (
    <ul className="promote-ledger-list compact">
      {entries.slice(0, limit).map(entry => (
        <li key={entry.id}>
          <div>
            <strong>{entry.entry_type}</strong>
            <span className="muted">{entry.description || ""}</span>
          </div>
          <span className={Number(entry.amount) >= 0 ? "ledger-credit" : "ledger-debit"}>
            {Number(entry.amount) >= 0 ? "+" : ""}${Number(entry.amount || 0).toFixed(2)}
          </span>
        </li>
      ))}
    </ul>
  );
}

function formatTicketWhen(ticket) {
  if (!ticket?.show?.starts_at) return "";
  return new Date(ticket.show.starts_at).toLocaleString(undefined, {
    weekday: "short",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

function TicketStubCard({ ticket, onOpenArtistByUsername, onOpenTicketShow }) {
  const venue = ticket.show?.venue_name || "Venue";
  const when = formatTicketWhen(ticket);
  return (
    <article className="fan-ticket-stub-card">
      <div className="fan-ticket-stub-card-main">
        <p className="eyebrow">Show stub</p>
        <strong>{ticket.product_title}</strong>
        <span>
          <ArtistNameLink
            username={ticket.artist_username}
            label={ticket.stage_name}
            onOpenArtist={onOpenArtistByUsername}
            stopPropagation
          />
          {` @ ${venue}`}
        </span>
        {when ? <span className="muted">{when}</span> : null}
        {ticket.show?.stub_code ? (
          <p className="ticket-door-code-inline">Stub code <strong>{ticket.show.stub_code}</strong></p>
        ) : (
          <p className="ticket-door-code-inline">Checked in at the door</p>
        )}
      </div>
      {ticket.show?.booking_id ? (
        <button
          className="secondary compact"
          type="button"
          onClick={() => onOpenTicketShow?.(ticket.show.booking_id)}
        >
          View show
        </button>
      ) : null}
    </article>
  );
}

export function ProfileSettingsView({
  activeSection,
  askBeforeExternalSocial,
  betaFeedbackSummary,
  currentUser,
  fanEmailSharing,
  fanTotal,
  hideSocialEmbeds,
  myPurchases,
  mySubscriptions,
  myTickets,
  onBetaFeedback,
  onFanEmailSharingChange,
  onManageSupport,
  onOpenArtistByUsername,
  onOpenMyMusic,
  onOpenTicketShow,
  onRefreshBetaSummary,
  onResolveBetaFeedback,
  onSaveDiscoveryLocation,
  onSaveDiscoveryPreferences,
  onSaved,
  onSaveHostProfile,
  onSectionChange,
  onSetAskBeforeExternalSocial,
  onSetGlobalEmailSharing,
  onSetHideSocialEmbeds,
  promotionWallet,
  pushEnabled,
  pushSupported,
  onEnablePush,
  onDisablePush,
  savedCount,
  spaceHostProfile,
  supportedCount,
}) {
  const sections = getSettingsSectionsForUser(currentUser);

  const [ticketTab, setTicketTab] = useState("upcoming");
  const ticketGroups = useMemo(() => {
    const upcoming = [];
    const attended = [];
    const past = [];
    for (const ticket of myTickets || []) {
      const status = ticket.collection_status
        || ticket.show?.collection_status
        || (ticket.checked_in ? "attended" : "upcoming");
      if (status === "attended") attended.push(ticket);
      else if (status === "past") past.push(ticket);
      else upcoming.push(ticket);
    }
    return { upcoming, attended, past };
  }, [myTickets]);

  function renderSection() {
    switch (activeSection) {
      case "tickets": {
        const activeTickets = ticketTab === "collection"
          ? [...ticketGroups.attended, ...ticketGroups.past]
          : ticketGroups.upcoming;
        return (
          <div className="feature-card profile-settings-panel-card">
            <p className="eyebrow">My tickets</p>
            <h3>
              {ticketTab === "collection"
                ? (ticketGroups.attended.length
                  ? `${ticketGroups.attended.length} in your collection`
                  : "No stubs yet")
                : (ticketGroups.upcoming.length
                  ? `${ticketGroups.upcoming.length} upcoming`
                  : "No tickets yet")}
            </h3>
            <div className="my-tickets-tabs" role="tablist" aria-label="Ticket views">
              <button
                type="button"
                role="tab"
                aria-selected={ticketTab === "upcoming"}
                className={ticketTab === "upcoming" ? "secondary compact is-active" : "secondary compact"}
                onClick={() => setTicketTab("upcoming")}
              >
                Upcoming
              </button>
              <button
                type="button"
                role="tab"
                aria-selected={ticketTab === "collection"}
                className={ticketTab === "collection" ? "secondary compact is-active" : "secondary compact"}
                onClick={() => setTicketTab("collection")}
              >
                Collection
              </button>
            </div>
            {activeTickets.length === 0 ? (
              <p className="muted">
                {ticketTab === "collection"
                  ? "Shows you check in to become stubs in your collection."
                  : "Buy tickets from Shows near me when artists play local venues."}
              </p>
            ) : ticketTab === "collection" ? (
              <div className="fan-ticket-stub-list" aria-label="Show stub collection">
                {ticketGroups.attended.map(ticket => (
                  <TicketStubCard
                    key={`stub-${ticket.product_id}`}
                    ticket={ticket}
                    onOpenArtistByUsername={onOpenArtistByUsername}
                    onOpenTicketShow={onOpenTicketShow}
                  />
                ))}
                {ticketGroups.past.length > 0 && (
                  <>
                    <p className="muted form-hint">Past tickets without door check-in</p>
                    {ticketGroups.past.map(ticket => (
                      <div className="library-row" key={`past-${ticket.product_id}`}>
                        <div>
                          <strong>{ticket.product_title}</strong>
                          <span className="muted">
                            <ArtistNameLink
                              username={ticket.artist_username}
                              label={ticket.stage_name}
                              onOpenArtist={onOpenArtistByUsername}
                              stopPropagation
                            />
                            {ticket.show?.venue_name ? ` @ ${ticket.show.venue_name}` : ""}
                            {ticket.show?.starts_at ? ` · ${formatTicketWhen(ticket)}` : ""}
                          </span>
                        </div>
                      </div>
                    ))}
                  </>
                )}
              </div>
            ) : (
              <div className="my-tickets-list">
                {ticketGroups.upcoming.map(ticket => (
                  <button
                    type="button"
                    key={ticket.product_id}
                    className="my-ticket-row"
                    onClick={() => ticket.show?.booking_id && onOpenTicketShow?.(ticket.show.booking_id)}
                  >
                    <strong>{ticket.product_title}</strong>
                    <span>
                      <ArtistNameLink
                        username={ticket.artist_username}
                        label={ticket.stage_name}
                        onOpenArtist={onOpenArtistByUsername}
                        stopPropagation
                      />
                      {ticket.show?.venue_name ? ` @ ${ticket.show.venue_name}` : ""}
                      {ticket.show?.starts_at ? ` · ${formatTicketWhen(ticket)}` : ""}
                    </span>
                    <span>${ticket.amount} · Confirmed</span>
                    <span className="ticket-door-code-inline">Tap I'm here at the venue to check in</span>
                  </button>
                ))}
              </div>
            )}
            {!myTickets.length && (
              <button className="secondary compact" type="button" onClick={() => onOpenTicketShow?.()}>Open Shows near me</button>
            )}
          </div>
        );
      }

      case "library":
        return (
          <div className="feature-card profile-settings-panel-card library-support-card">
            <p className="eyebrow">Library & support</p>
            <h3>Your subscriptions & purchases</h3>
            <div className="library-section">
              <div className="library-section-head">
                <strong>Artists you support</strong>
                <span className="muted">
                  {currentUser?.subscription_count ?? mySubscriptions.length}
                  {" of "}
                  {currentUser?.subscription_limit || 50}
                  {" slots"}
                </span>
              </div>
              {mySubscriptions.length === 0 ? (
                <p className="muted">You aren't supporting any artists yet. Support unlocks subscriber-only content.</p>
              ) : (
                <div className="library-list">
                  {mySubscriptions.map(sub => (
                    <div className="library-row" key={sub.id}>
                      <div>
                        <strong>
                          <ArtistNameLink username={sub.artist} onOpenArtist={onOpenArtistByUsername} stopPropagation />
                        </strong>
                        <span className="muted">
                          {sub.tier_name || "Supporter"} · {sub.profession_label || "Music"} · ${sub.monthly_amount}/mo
                        </span>
                      </div>
                      <button className="secondary compact" type="button" onClick={() => onManageSupport?.(sub.artist, sub.profession)}>
                        Manage
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
            <div className="library-section">
              <div className="library-section-head">
                <strong>Purchases</strong>
                <span className="muted">{myPurchases.length} item{myPurchases.length === 1 ? "" : "s"}</span>
              </div>
              {myPurchases.length === 0 ? (
                <p className="muted">Merch, music, and tickets you buy will appear here.</p>
              ) : (
                <div className="library-list">
                  {myPurchases.map(item => (
                    <div className="library-row" key={item.product_id}>
                      <div>
                        <strong>{item.product_title}</strong>
                        <span className="muted">
                          <ArtistNameLink
                            username={item.artist_username}
                            label={item.stage_name}
                            onOpenArtist={onOpenArtistByUsername}
                            stopPropagation
                          />
                          {item.purchased_at ? ` · ${new Date(item.purchased_at).toLocaleDateString()}` : ""}
                        </span>
                      </div>
                      <span>${item.amount}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
            {onOpenMyMusic && (
              <button className="secondary compact" type="button" onClick={onOpenMyMusic}>Open My Playlists</button>
            )}
          </div>
        );

      case "activity":
        return (
          <div className="feature-card profile-settings-panel-card">
            <p className="eyebrow">Fan activity</p>
            <h3>${fanTotal}</h3>
            <p>
              Supporting {supportedCount} artist{supportedCount === 1 ? "" : "s"} • {savedCount} saved artist{savedCount === 1 ? "" : "s"}.
            </p>
            <button className="secondary compact" onClick={onSaved}>View Saved Artists</button>
          </div>
        );

      case "credits":
        return (
          <div className="feature-card profile-settings-panel-card discovery-credits-card">
            <p className="eyebrow">Discovery credits</p>
            <h3>${Number(promotionWallet?.balance || 0).toFixed(2)}</h3>
            <p className="muted">
              Earn credits by engaging with promoted releases in Discovery — listens, saves, feedback, and shares.
              Redeem them on tips and store purchases. Up to ${promotionWallet?.rewards_remaining_today || promotionWallet?.fan_reward_daily_cap || "1.00"} left to earn today.
            </p>
            {promotionWallet?.tagline && <p className="discovery-credits-tagline">{promotionWallet.tagline}</p>}
            {renderWalletLedger(promotionWallet?.entries || [])}
          </div>
        );

      case "email":
        return (
          <div className="feature-card profile-settings-panel-card">
            <p className="eyebrow">Artist email updates</p>
            <h3>Email sharing</h3>
            <label className="check-row preference-row">
              <input
                type="checkbox"
                checked={Boolean(currentUser.share_email_with_supported_artists)}
                onChange={event => onSetGlobalEmailSharing(event.target.checked)}
              />
              Share my email with artists I support so they can send me updates about releases, shows, and exclusive content.
            </label>
            <p className="muted">
              Turning this off revokes current email access for artists. You can also revoke individual artists below.
            </p>
            {fanEmailSharing.length > 0 && (
              <div className="email-sharing-list">
                {fanEmailSharing.map(item => (
                  <div className="email-sharing-row" key={item.artist_id}>
                    <span>{item.artist_name}</span>
                    <button className="secondary compact" onClick={() => onFanEmailSharingChange(item.artist_id, !item.email_shared)}>
                      {item.email_shared ? "Revoke" : "Share"}
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        );

      case "discovery":
        return (
          <div className="feature-card profile-settings-panel-card">
            <p className="eyebrow">Discovery</p>
            <h3>Your discovery controls</h3>
            <p className="muted">Shape how promoted releases and emerging artists appear while you swipe.</p>
            <label className="check-row preference-row">
              <input
                type="checkbox"
                checked={Boolean(currentUser.discovery_prefer_emerging)}
                onChange={event => onSaveDiscoveryPreferences?.({ discovery_prefer_emerging: event.target.checked })}
              />
              Prioritize emerging artists in Discovery
            </label>
            <label className="check-row preference-row">
              <input
                type="checkbox"
                checked={Boolean(currentUser.discovery_fewer_promoted)}
                onChange={event => onSaveDiscoveryPreferences?.({ discovery_fewer_promoted: event.target.checked })}
              />
              Show fewer promoted posts
            </label>
            <label className="check-row preference-row">
              <input
                type="checkbox"
                checked={Boolean(currentUser.discovery_promoted_genres_only)}
                onChange={event => onSaveDiscoveryPreferences?.({ discovery_promoted_genres_only: event.target.checked })}
              />
              Only show promoted music in genres I follow
            </label>
          </div>
        );

      case "gigs":
        return (
          <div className="feature-card profile-settings-panel-card">
            <p className="eyebrow">Local gigs</p>
            <h3>Your city</h3>
            <p className="muted">Scenes uses this to surface shows in your area.</p>
            <form
              className="discovery-location-form"
              onSubmit={(event) => {
                event.preventDefault();
                onSaveDiscoveryLocation?.(event.target.discovery_location.value.trim());
              }}
            >
              <input
                name="discovery_location"
                defaultValue={currentUser.discovery_location || ""}
                placeholder="e.g. Melbourne"
                aria-label="Discovery city"
              />
              <button className="secondary compact" type="submit">Save city</button>
            </form>
          </div>
        );

      case "push":
        return (
          <div className="feature-card profile-settings-panel-card">
            <p className="eyebrow">Browser alerts</p>
            <h3>Push notifications</h3>
            <p className="muted">
              {pushSupported
                ? "Get gig alerts, purchase receipts, and supporter updates even when IndieFund is in the background."
                : "This browser does not support web push."}
            </p>
            {pushSupported && (
              <div className="action-grid">
                {!pushEnabled ? (
                  <button className="primary compact" type="button" onClick={onEnablePush}>Enable push</button>
                ) : (
                  <button className="secondary compact" type="button" onClick={onDisablePush}>Disable push</button>
                )}
              </div>
            )}
          </div>
        );

      case "social":
        return (
          <div className="feature-card profile-settings-panel-card">
            <p className="eyebrow">Social content</p>
            <h3>External link preferences</h3>
            <label className="check-row preference-row">
              <input
                type="checkbox"
                checked={askBeforeExternalSocial}
                onChange={event => onSetAskBeforeExternalSocial(event.target.checked)}
              />
              Always ask before opening external social links
            </label>
            <label className="check-row preference-row">
              <input
                type="checkbox"
                checked={hideSocialEmbeds}
                onChange={event => onSetHideSocialEmbeds(event.target.checked)}
              />
              Hide Instagram and TikTok posts on artist profiles
            </label>
          </div>
        );

      case "host":
        return (
          <form
            className="feature-card profile-settings-panel-card host-profile-settings"
            key={spaceHostProfile?.id || "host-profile-new"}
            onSubmit={onSaveHostProfile}
          >
            <p className="eyebrow">Host profile</p>
            <h3>Venue contact details</h3>
            <p className="muted">Used on your space listings and booking requests.</p>
            <div className="two-column-form">
              <input name="business_name" placeholder="Business name" defaultValue={spaceHostProfile?.business_name || currentUser.display_name || ""} required />
              <input name="contact_email" type="email" placeholder="Contact email" defaultValue={spaceHostProfile?.contact_email || currentUser.email || ""} />
              <input name="phone" placeholder="Phone" defaultValue={spaceHostProfile?.phone || ""} />
              <input name="address" placeholder="Address" defaultValue={spaceHostProfile?.address || ""} />
              <input name="city" placeholder="City" defaultValue={spaceHostProfile?.city || ""} />
            </div>
            <button className="primary compact" type="submit">Save Host Profile</button>
          </form>
        );

      case "beta":
      default:
        return (
          <>
            {currentUser.user_type === "admin" && betaFeedbackSummary && (
              <div className="feature-card profile-settings-panel-card beta-summary-card">
                <div className="section-head compact">
                  <div>
                    <p className="eyebrow">Beta loop</p>
                    <h3>Feedback results</h3>
                  </div>
                  <button className="secondary compact" type="button" onClick={onRefreshBetaSummary}>Refresh</button>
                </div>
                <p className="muted">
                  {betaFeedbackSummary.total_feedback} submissions • {betaFeedbackSummary.submitters}/{betaFeedbackSummary.beta_testers} testers ({betaFeedbackSummary.participation_rate}%) • {betaFeedbackSummary.unresolved_count} open
                </p>
              </div>
            )}
            <form className="feature-card profile-settings-panel-card beta-feedback-card" onSubmit={onBetaFeedback}>
              <p className="eyebrow">Beta</p>
              <h3>{currentUser.is_beta_tester ? "Report beta feedback" : "Join beta feedback"}</h3>
              {currentUser.beta_notes && <p>{currentUser.beta_notes}</p>}
              <div className="beta-task-list">
                <span>1. Complete account setup</span>
                <span>2. Save or support one artist</span>
                <span>3. Report the first confusing step</span>
              </div>
              <select name="category" defaultValue="navigation">
                <option value="setup">Account setup</option>
                <option value="navigation">Navigation</option>
                <option value="content">Content and posting</option>
                <option value="payments">Payments and support</option>
                <option value="other">Other</option>
              </select>
              <select name="severity" defaultValue="medium">
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
                <option value="blocker">Blocker</option>
              </select>
              <input name="summary" placeholder="What needs work?" required />
              <textarea name="details" placeholder="What happened, and what did you expect?"></textarea>
              <input name="path" type="hidden" value={window.location.pathname + window.location.search} readOnly />
              <button className="primary compact" type="submit">Send Feedback</button>
            </form>
          </>
        );
    }
  }

  return (
    <div className="profile-settings-layout">
      <ProfileSettingsNav activeSection={activeSection} onChange={onSectionChange} sections={sections} />
      <div className="profile-settings-panel">{renderSection()}</div>
    </div>
  );
}
