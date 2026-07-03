import React from "react";

export function LiveTab({
  cameraDevices,
  cameraStatus,
  enableLiveCamera,
  isLive,
  isOwner,
  liveChatMessage,
  liveChatMessages,
  livePreviewRef,
  onCloseLiveForm,
  onSendLiveChatMessage,
  onStartLiveSession,
  onStopLiveSession,
  renderArtistName,
  selectedCameraId,
  setLiveChatMessage,
  setSelectedCameraId,
  setShowLiveForm,
  showLiveForm,
}) {
  return (
    <>
      <div className="tab-title-row">
        <h2>Lives</h2>
        {isOwner && (
          <button className="small-action" onClick={() => setShowLiveForm(true)}>
            + Start Live
          </button>
        )}
      </div>

      {isOwner && showLiveForm && (
        <section className="live-room-layout">
          <form className="store-form live-setup-form">
            <div className="live-title-row">
              <h3>Create Live Event</h3>
              {isLive && <span className="live-status">Live</span>}
            </div>

            <label>Title</label>
            <input name="live_title" placeholder="Beat Making Session" />

            <label>Description</label>
            <textarea name="live_description" placeholder="What is this live about?" />

            <section className="camera-panel">
              <div className="camera-panel-head">
                <div>
                  <label>Camera</label>
                  <p className="muted">Enable camera preview before starting the live room.</p>
                </div>
                <button type="button" className="secondary compact" onClick={() => enableLiveCamera()}>
                  Enable Camera
                </button>
              </div>

              <video className="live-preview" ref={livePreviewRef} autoPlay muted playsInline></video>

              {cameraDevices.length > 0 && (
                <>
                  <label>Camera source</label>
                  <select
                    value={selectedCameraId}
                    onChange={(event) => {
                      setSelectedCameraId(event.target.value);
                      enableLiveCamera(event.target.value);
                    }}
                  >
                    {cameraDevices.map((device, index) => (
                      <option key={device.deviceId} value={device.deviceId}>
                        {device.label || `Camera ${index + 1}`}
                      </option>
                    ))}
                  </select>
                </>
              )}

              {cameraStatus && <p className="muted">{cameraStatus}</p>}
            </section>

            <label>Public Preview</label>
            <select name="live_access_mode" defaultValue="preview_30">
              <option value="supporters">Subscribers Only</option>
              <option value="preview_10">10 Minutes</option>
              <option value="preview_30">30 Minutes</option>
              <option value="preview_60">60 Minutes</option>
              <option value="public">Entire Stream Public</option>
            </select>

            <div className="action-grid">
              <button
                type="button"
                className={isLive ? "danger-action" : "primary"}
                onClick={isLive ? onStopLiveSession : onStartLiveSession}
              >
                {isLive ? "Stop Live" : "Go Live"}
              </button>

              <button
                type="button"
                className="secondary"
                onClick={onCloseLiveForm}
              >
                Cancel
              </button>
            </div>
          </form>

          <aside className="live-chat-panel">
            <div className="live-chat-head">
              <div>
                <p className="eyebrow">Live chat</p>
                <h3>Audience feed</h3>
              </div>
              <span>{liveChatMessages.length}</span>
            </div>

            <div className="live-chat-list">
              {liveChatMessages.map(chat => (
                <article className="live-chat-bubble" key={chat.id}>
                  <div className="live-chat-avatar">{chat.name?.[0]?.toUpperCase()}</div>
                  <div>
                    <div className="live-chat-meta">
                      <strong>
                        {renderArtistName
                          ? renderArtistName(chat.name, { knownOnly: true })
                          : chat.name}
                      </strong>
                      <span>{chat.role}</span>
                    </div>
                    <p>{chat.body}</p>
                  </div>
                </article>
              ))}
            </div>

            <form className="live-chat-form" onSubmit={onSendLiveChatMessage}>
              <input
                value={liveChatMessage}
                onChange={(event) => setLiveChatMessage(event.target.value)}
                placeholder="Send a chat message"
              />
              <button className="secondary compact" type="submit">Send</button>
            </form>
          </aside>
        </section>
      )}

      {!showLiveForm && (
        <div className="empty-state">
          <h3>No live events.</h3>
          <p>
            Create livestreams, listening parties, Q&As,
            beat sessions and supporter events.
          </p>
        </div>
      )}
    </>
  );
}
