import React, { useEffect } from "react";

const ARTIST_PROFESSIONS = [
  { key: "music", label: "Music" },
  { key: "visual_art", label: "Painting / Drawing" },
  { key: "digital_art", label: "Digital Art" },
  { key: "craft", label: "Crafts" },
  { key: "writing", label: "Writing" },
  { key: "performance", label: "Performance" },
  { key: "comedy", label: "Comedian" },
  { key: "podcast", label: "Podcaster" },
  { key: "film", label: "Filmmaker / Video" },
  { key: "other", label: "Other" },
];

function Field({ id, label, children, hint }) {
  return (
    <div className="form-field">
      <label htmlFor={id}>{label}</label>
      {children}
      {hint && <p className="form-hint">{hint}</p>}
    </div>
  );
}

export function AuthPanel({
  authMode,
  currentUser,
  fanRegistrationOpen = true,
  onAuth,
  onWaitlist,
  onProfile,
  registerType,
  setAuthMode,
  setRegisterType,
}) {
  useEffect(() => {
    if (!fanRegistrationOpen && registerType === "fan") {
      setRegisterType("artist");
    }
  }, [fanRegistrationOpen, registerType, setRegisterType]);

  return (
    <section className="auth-panel">
      <div>
        <p className="eyebrow">Account</p>
        {currentUser ? (
          <>
            <h2>Signed in as {currentUser.display_name || currentUser.username}</h2>
            <p className="muted">{currentUser.username} • {currentUser.user_type}</p>
            {currentUser.email_verification_required && (
              <p className="notice-inline">Verify your email to unlock purchases and payouts.</p>
            )}
          </>
        ) : (
          <>
            <h2>
              {authMode === "waitlist"
                ? "Join the fan waitlist"
                : authMode === "register"
                  ? "Create your account"
                  : "Log in"}
            </h2>
            <p className="muted">
              {authMode === "waitlist"
                ? "Fans open at public launch. Leave your email and we will notify you when Discover, Listen, and support go live."
                : fanRegistrationOpen
                  ? "Use a fan account to support artists, an artist account to manage your page, or a host account to list a room."
                  : "Early signup is open for artists and hosts. Fans can join the waitlist until launch."}
            </p>
          </>
        )}
      </div>

      {currentUser ? (
        <button className="secondary" onClick={onProfile}>Open Profile</button>
      ) : authMode === "waitlist" ? (
        <form className="auth-form" onSubmit={onWaitlist}>
          <div className="auth-toggle">
            <button type="button" className="tab" onClick={() => setAuthMode("login")}>
              Log in
            </button>
            <button type="button" className="tab" onClick={() => setAuthMode("register")}>
              Artist / host signup
            </button>
            <button type="button" className="tab active" onClick={() => setAuthMode("waitlist")}>
              Fan waitlist
            </button>
          </div>

          <Field id="waitlist-email" label="Email address">
            <input id="waitlist-email" name="email" type="email" required autoComplete="email" />
          </Field>
          <Field id="waitlist-city" label="City or region" hint="Optional — helps us prioritize your local launch scene.">
            <input id="waitlist-city" name="city" autoComplete="address-level2" />
          </Field>
          <Field id="waitlist-genres" label="Favorite genres" hint="Optional — shapes launch recommendations for you.">
            <input id="waitlist-genres" name="favorite_genres" />
          </Field>

          <label className="check-row preference-row" htmlFor="waitlist-terms-accepted">
            <input id="waitlist-terms-accepted" name="terms_accepted" type="checkbox" value="true" />
            I agree to the Privacy Policy and want launch updates by email.
          </label>

          <button className="primary" type="submit">
            Join waitlist
          </button>
        </form>
      ) : (
        <form className="auth-form" onSubmit={onAuth}>
          <div className="auth-toggle">
            <button
              type="button"
              className={authMode === "login" ? "tab active" : "tab"}
              onClick={() => setAuthMode("login")}
            >
              Login
            </button>
            <button
              type="button"
              className={authMode === "register" ? "tab active" : "tab"}
              onClick={() => setAuthMode("register")}
            >
              Register
            </button>
            {!fanRegistrationOpen ? (
              <button type="button" className="tab" onClick={() => setAuthMode("waitlist")}>
                Fan waitlist
              </button>
            ) : null}
          </div>

          <Field id="auth-username" label="Username">
            <input id="auth-username" name="username" required autoComplete="username" />
          </Field>
          <Field id="auth-password" label="Password">
            <input id="auth-password" name="password" type="password" required minLength={8} autoComplete={authMode === "register" ? "new-password" : "current-password"} />
          </Field>

          {authMode === "register" && (
            <>
              <Field id="auth-display-name" label="Display name">
                <input id="auth-display-name" name="display_name" required />
              </Field>
              <Field id="auth-email" label="Email address">
                <input id="auth-email" name="email" type="email" required autoComplete="email" />
              </Field>
              <Field id="auth-user-type" label="Account type">
                <select id="auth-user-type" name="user_type" value={registerType} onChange={(event) => setRegisterType(event.target.value)}>
                  {fanRegistrationOpen ? <option value="fan">Fan</option> : null}
                  <option value="artist">Artist</option>
                  <option value="host">Host</option>
                </select>
              </Field>

              {registerType === "fan" && (
                <>
                  <Field id="auth-favorite-genres" label="Favorite genres" hint="These shape Discovery ranking and local artist matches.">
                    <input id="auth-favorite-genres" name="favorite_genres" required />
                  </Field>
                  <Field id="auth-discovery-location" label="City or region">
                    <input id="auth-discovery-location" name="discovery_location" required />
                  </Field>
                  <label className="check-row preference-row">
                    <input name="share_email_with_supported_artists" type="checkbox" value="true" />
                    Share my email with artists I support so they can send me updates about releases, shows, and exclusive content.
                  </label>
                </>
              )}

              {registerType === "artist" && (
                <>
                  <Field id="auth-stage-name" label="Stage name">
                    <input id="auth-stage-name" name="stage_name" required />
                  </Field>
                  <div className="profession-picker">
                    <span className="field-label">Creative work</span>
                    <div className="profession-grid">
                      {ARTIST_PROFESSIONS.map(profession => (
                        <label className="check-row" key={profession.key}>
                          <input
                            name="professions"
                            type="checkbox"
                            value={profession.key}
                            defaultChecked={profession.key === "music"}
                          />
                          {profession.label}
                        </label>
                      ))}
                    </div>
                  </div>
                  <Field id="auth-genre" label="Artist genre">
                    <input id="auth-genre" name="genre" required />
                  </Field>
                  <Field id="auth-city" label="Artist city">
                    <input id="auth-city" name="city" required />
                  </Field>
                  <Field id="auth-influences" label="Artist influences">
                    <input id="auth-influences" name="influences" />
                  </Field>
                  <Field id="auth-artist-story" label="Short artist story" hint="Complete profiles rank better and make your page easier for fans to trust.">
                    <textarea id="auth-artist-story" name="artist_story" rows={3} />
                  </Field>
                </>
              )}

              {registerType === "host" && (
                <Field id="auth-venue-city" label="Venue city" hint="After signup, open Spaces to add your first room and manage bookings.">
                  <input id="auth-venue-city" name="discovery_location" required />
                </Field>
              )}

              <label className="check-row preference-row" htmlFor="auth-terms-accepted">
                <input id="auth-terms-accepted" name="terms_accepted" type="checkbox" value="true" />
                I agree to the Terms of Service and Privacy Policy.
              </label>
            </>
          )}

          <button className="primary" type="submit">
            {authMode === "register" ? "Create Account" : "Log In"}
          </button>
        </form>
      )}
    </section>
  );
}
