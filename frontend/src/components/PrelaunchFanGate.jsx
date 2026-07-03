export function PrelaunchFanGate({ onArtistSignup, onHostSignup, onFanWaitlist, onHome }) {
  return (
    <section className="prelaunch-fan-gate feature-card">
      <p className="eyebrow">Coming soon</p>
      <h2>Fan features open at launch</h2>
      <p className="muted">
        Discover, Listen, Stores, and support checkout are closed while artists and hosts get listed.
        Public artist pages stay open for early previews.
      </p>
      <div className="action-grid">
        <button type="button" className="primary" onClick={onFanWaitlist}>
          Join fan waitlist
        </button>
        <button type="button" className="secondary" onClick={onArtistSignup}>
          Artist early signup
        </button>
        <button type="button" className="secondary" onClick={onHostSignup}>
          Host early signup
        </button>
        <button type="button" className="secondary" onClick={onHome}>
          Back to home
        </button>
      </div>
    </section>
  );
}
