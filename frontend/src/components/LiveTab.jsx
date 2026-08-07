import React from "react";

export function LiveTab({
  activeLiveSession,
  isLive,
  isOwner,
  myTracks,
  onCloseLiveForm,
  onOpenPartyRoom,
  onStartLiveSession,
  onStopLiveSession,
  setShowLiveForm,
  showLiveForm,
}) {
  return (
    <>
      <div className="tab-title-row">
        <h2>Listening parties</h2>
        {isOwner && !isLive && (
          <button className="small-action" onClick={() => setShowLiveForm(true)}>
            + Start party
          </button>
        )}
      </div>

      {isOwner && isLive && activeLiveSession && (
        <section className="listening-party-stage">
          <div className="live-title-row">
            <h3>{activeLiveSession.title}</h3>
            <span className="live-status">Live</span>
          </div>
          <p className="muted">
            {activeLiveSession.track
              ? `Playing “${activeLiveSession.track.title}” for everyone in the room.`
              : "Chat-only session — attach a track next time to premiere it live."}
          </p>
          <div className="action-grid">
            <button type="button" className="primary" onClick={onOpenPartyRoom}>
              Open party room
            </button>
            <button type="button" className="danger-action" onClick={onStopLiveSession}>
              End party
            </button>
          </div>
        </section>
      )}

      {isOwner && showLiveForm && !isLive && (
        <form className="store-form live-setup-form">
          <div className="live-title-row">
            <h3>Start a listening party</h3>
          </div>

          <label htmlFor="live-party-title">Title</label>
          <input id="live-party-title" name="live_title" placeholder="First listen: new single" />

          <label htmlFor="live-party-description">Description</label>
          <textarea id="live-party-description" name="live_description" placeholder="What are we listening to?" />

          <label htmlFor="live-party-track">Featured track</label>
          <select id="live-party-track" name="live_track_id" defaultValue="">
            <option value="">No track — chat only</option>
            {(myTracks || []).map(track => (
              <option key={track.id} value={track.id}>{track.title}</option>
            ))}
          </select>
          <p className="muted">
            The full track unlocks for everyone in the room while the party is live — even if it’s normally supporter-only.
          </p>

          <label htmlFor="live-party-access">Who can join</label>
          <select id="live-party-access" name="live_access_mode" defaultValue="public">
            <option value="public">Anyone with a free account</option>
            <option value="supporters">Supporters only</option>
          </select>

          <div className="action-grid">
            <button type="button" className="primary" onClick={onStartLiveSession}>
              Go live
            </button>
            <button type="button" className="secondary" onClick={onCloseLiveForm}>
              Cancel
            </button>
          </div>
        </form>
      )}

      {!showLiveForm && !isLive && (
        <div className="empty-state">
          <h3>No live parties.</h3>
          <p>
            Host listening parties, first listens, Q&As and supporter
            hangouts — audio and chat, no camera needed.
          </p>
        </div>
      )}
    </>
  );
}
