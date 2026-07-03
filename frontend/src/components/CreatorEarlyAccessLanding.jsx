import { IndieFundLogo } from "./IndieFundLogo.jsx";

export function CreatorEarlyAccessLanding({
  featuredArtists = [],
  authPanel,
  onArtistSignup,
  onHostSignup,
  onFanWaitlist,
  onFaq,
  onBrowseArtist,
}) {
  return (
    <section className="guest-landing early-access-landing">
      <IndieFundLogo className="guest-brand" />

      <header className="early-access-hero">
        <p className="eyebrow">Early access</p>
        <h1>Get listed before fans arrive</h1>
        <p className="muted guest-lead">
          IndieFund opens to fans on launch day. Artists and hosts can build pages, upload work, and list rooms now — no beta testing required.
        </p>
        <div className="action-grid guest-cta-row">
          <button className="primary" type="button" onClick={onArtistSignup}>
            Artist early signup
          </button>
          <button className="secondary" type="button" onClick={onHostSignup}>
            Host early signup
          </button>
          <button className="secondary" type="button" onClick={onFanWaitlist}>
            Join fan waitlist
          </button>
          <button className="secondary" type="button" onClick={onFaq}>
            How it works
          </button>
        </div>
      </header>

      <div className="early-access-grid">
        <article className="feature-card early-access-card">
          <p className="eyebrow">For artists</p>
          <h2>Launch your page</h2>
          <ul className="early-access-list">
            <li>Upload music and posts fans can preview before launch</li>
            <li>Set supporter tiers and merch so checkout works on day one</li>
            <li>Share your public artist link to build your list early</li>
          </ul>
          <button className="primary compact" type="button" onClick={onArtistSignup}>
            Start artist signup
          </button>
        </article>

        <article className="feature-card early-access-card">
          <p className="eyebrow">For hosts</p>
          <h2>List your room</h2>
          <ul className="early-access-list">
            <li>Add photos, availability, and pricing for your space</li>
            <li>Receive booking requests when artists plan shows</li>
            <li>Show up in local discovery as the scene fills in</li>
          </ul>
          <button className="primary compact" type="button" onClick={onHostSignup}>
            Start host signup
          </button>
        </article>

        <article className="feature-card early-access-card early-access-card--fans">
          <p className="eyebrow">For fans</p>
          <h2>Waitlist only until launch</h2>
          <p className="muted">
            Discover, Listen, Stores, and support checkout stay closed during early signup. Leave your email and we will notify you when the full fan experience opens.
          </p>
          <button className="secondary compact" type="button" onClick={onFanWaitlist}>
            Join fan waitlist
          </button>
        </article>
      </div>

      {featuredArtists.length > 0 && (
        <section className="featured-artists-row" aria-label="Featured artists">
          <p className="eyebrow">Launch artists</p>
          <div className="featured-artist-grid">
            {featuredArtists.map(artist => (
              <button
                key={artist.id}
                type="button"
                className="featured-artist-card"
                onClick={() => onBrowseArtist(artist.username)}
              >
                <strong>{artist.stage_name || artist.username}</strong>
                <span className="muted">
                  {artist.city}
                  {artist.genre ? ` • ${artist.genre}` : ""}
                </span>
              </button>
            ))}
          </div>
        </section>
      )}

      <div className="guest-auth-wrap">
        {authPanel}
      </div>
    </section>
  );
}
