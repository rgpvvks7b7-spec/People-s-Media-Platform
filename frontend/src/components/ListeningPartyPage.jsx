import React, { useCallback, useEffect, useRef, useState } from "react";

const POLL_INTERVAL_MS = 4000;

export function ListeningPartyPage({
  apiFetch,
  currentUser,
  focusSessionId,
  onClearFocusSession,
  onOpenArtist,
  onRequireAccount,
}) {
  const [sessions, setSessions] = useState([]);
  const [sessionsLoaded, setSessionsLoaded] = useState(false);
  const [party, setParty] = useState(null);
  const [streamUrl, setStreamUrl] = useState(null);
  const [messages, setMessages] = useState([]);
  const [chatInput, setChatInput] = useState("");
  const [chatError, setChatError] = useState("");
  const lastMessageIdRef = useRef(0);
  const activeSessionIdRef = useRef(null);
  const chatListRef = useRef(null);

  const loadSessions = useCallback(async () => {
    const res = await apiFetch("/live/");
    const data = await res.json();
    if (res.ok) setSessions(data.results || []);
    setSessionsLoaded(true);
  }, [apiFetch]);

  useEffect(() => {
    loadSessions();
  }, [loadSessions]);

  const pollParty = useCallback(async (sessionId, { reset = false } = {}) => {
    const after = reset ? 0 : lastMessageIdRef.current;
    const res = await apiFetch(`/live/${sessionId}/?after=${after}`);
    if (!res.ok) return;
    const data = await res.json();
    if (activeSessionIdRef.current !== sessionId) return;

    setParty(data);
    // Keep the first stream URL: tokens rotate on every poll and swapping the
    // audio src would restart playback.
    setStreamUrl(previous => previous || data.stream_url);
    if (data.messages?.length) {
      lastMessageIdRef.current = data.messages[data.messages.length - 1].id;
      setMessages(previous => (reset ? data.messages : [...previous, ...data.messages]));
    } else if (reset) {
      setMessages([]);
    }
  }, [apiFetch]);

  const joinParty = useCallback((sessionId) => {
    activeSessionIdRef.current = sessionId;
    lastMessageIdRef.current = 0;
    setParty(null);
    setStreamUrl(null);
    setMessages([]);
    setChatError("");
    pollParty(sessionId, { reset: true });
  }, [pollParty]);

  function leaveParty() {
    activeSessionIdRef.current = null;
    setParty(null);
    setStreamUrl(null);
    setMessages([]);
    setChatError("");
    if (onClearFocusSession) onClearFocusSession();
    loadSessions();
  }

  useEffect(() => {
    if (focusSessionId) joinParty(focusSessionId);
  }, [focusSessionId, joinParty]);

  useEffect(() => {
    if (!party?.id || !party.is_live) return undefined;
    const timer = setInterval(() => pollParty(party.id), POLL_INTERVAL_MS);
    return () => clearInterval(timer);
  }, [party?.id, party?.is_live, pollParty]);

  useEffect(() => {
    if (chatListRef.current) {
      chatListRef.current.scrollTop = chatListRef.current.scrollHeight;
    }
  }, [messages.length]);

  async function sendChat(event) {
    event.preventDefault();
    const body = chatInput.trim();
    if (!body || !party?.id) return;

    const res = await apiFetch(`/live/${party.id}/chat/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ body }),
    });
    const data = await res.json();
    if (!res.ok) {
      setChatError(data.error || "Unable to send message.");
      return;
    }
    setChatError("");
    setChatInput("");
    lastMessageIdRef.current = data.message.id;
    setMessages(previous => [...previous, data.message]);
  }

  async function endParty() {
    if (!party?.id) return;
    const res = await apiFetch(`/live/${party.id}/stop/`, { method: "POST" });
    if (res.ok) pollParty(party.id, { reset: false });
  }

  function accessLabel(session) {
    return session.access_mode === "supporters" ? "Supporters only" : "Open party";
  }

  if (party) {
    const gate = !party.viewer_can_join;
    return (
      <section className="listening-party-room">
        <button className="secondary compact" type="button" onClick={leaveParty}>
          ← All parties
        </button>

        <header className="listening-party-head">
          <p className="eyebrow">{party.is_live ? "Live listening party" : "Party ended"}</p>
          <h1>{party.title}</h1>
          <p className="muted">
            Hosted by{" "}
            <button className="link-button" type="button" onClick={() => onOpenArtist(party.artist_username)}>
              {party.artist_display}
            </button>
            {party.track ? <> · Featuring “{party.track.title}”</> : null}
          </p>
        </header>

        <div className="listening-party-layout">
          <div className="listening-party-stage">
            {party.track?.cover_art && (
              <img className="listening-party-cover" src={party.track.cover_art} alt={`Cover art for ${party.track.title}`} />
            )}

            {!party.is_live && (
              <div className="empty-state">
                <h3>This party has ended.</h3>
                <p>Follow the artist to catch the next one.</p>
              </div>
            )}

            {party.is_live && gate && party.join_requirement === "account" && (
              <div className="listening-party-gate">
                <h3>Listen along with a free account</h3>
                <p>Create a free fan account to hear the full track and join the chat.</p>
                <button className="primary" type="button" onClick={onRequireAccount}>
                  Create free account
                </button>
              </div>
            )}

            {party.is_live && gate && party.join_requirement === "supporter" && (
              <div className="listening-party-gate">
                <h3>Supporters only</h3>
                <p>This party is reserved for supporters of {party.artist_display}.</p>
                <button className="primary" type="button" onClick={() => onOpenArtist(party.artist_username)}>
                  Support {party.artist_display}
                </button>
              </div>
            )}

            {party.is_live && !gate && streamUrl && (
              <div className="listening-party-player">
                <p className="muted">Full track unlocked for this party — press play and listen along.</p>
                <audio controls autoPlay src={streamUrl} aria-label={party.track ? `Play ${party.track.title}` : "Party audio"} />
              </div>
            )}

            {party.is_live && !gate && !streamUrl && (
              <p className="muted">The host hasn’t attached a track — hang out in the chat.</p>
            )}

            {party.is_host && party.is_live && (
              <button className="danger-action" type="button" onClick={endParty}>
                End party
              </button>
            )}
          </div>

          <aside className="live-chat-panel">
            <div className="live-chat-head">
              <div>
                <p className="eyebrow">Party chat</p>
                <h3>Room feed</h3>
              </div>
              <span>{messages.length}</span>
            </div>

            <div className="live-chat-list" ref={chatListRef}>
              {messages.length === 0 && <p className="muted">No messages yet. Say hi.</p>}
              {messages.map(message => (
                <article className="live-chat-bubble" key={message.id}>
                  <div className="live-chat-avatar">{message.author_display?.[0]?.toUpperCase()}</div>
                  <div>
                    <div className="live-chat-meta">
                      <strong>{message.author_display}</strong>
                      <span>{message.author_role}</span>
                    </div>
                    <p>{message.body}</p>
                  </div>
                </article>
              ))}
            </div>

            {chatError && <p className="form-error">{chatError}</p>}

            {currentUser && !gate ? (
              <form className="live-chat-form" onSubmit={sendChat}>
                <input
                  value={chatInput}
                  onChange={(event) => setChatInput(event.target.value)}
                  placeholder="Send a chat message"
                  aria-label="Chat message"
                />
                <button className="secondary compact" type="submit">Send</button>
              </form>
            ) : (
              <p className="muted">
                {currentUser ? "Supporters can chat in this party." : "Log in to join the chat."}
              </p>
            )}
          </aside>
        </div>
      </section>
    );
  }

  return (
    <section className="listening-party-page">
      <header className="listening-party-head">
        <p className="eyebrow">Live</p>
        <h1>Listening parties</h1>
        <p className="muted">
          Hear new tracks with the artist and other fans, live. Tracks unlock for everyone in the room while the party is on.
        </p>
      </header>

      {!sessionsLoaded && <p className="muted">Loading live parties…</p>}

      {sessionsLoaded && sessions.length === 0 && (
        <div className="empty-state">
          <h3>No one is live right now.</h3>
          <p>Follow artists to get notified the moment they start a listening party.</p>
        </div>
      )}

      <div className="listening-party-grid">
        {sessions.map(session => (
          <article className="listening-party-card" key={session.id}>
            <div className="listening-party-card-body">
              <p className="eyebrow live-indicator">● Live now</p>
              <h3>{session.title}</h3>
              <p className="muted">
                {session.artist_display}
                {session.track ? <> · “{session.track.title}”</> : null}
              </p>
              <span className="status-pill">{accessLabel(session)}</span>
            </div>
            <button className="primary" type="button" onClick={() => joinParty(session.id)}>
              Join party
            </button>
          </article>
        ))}
      </div>
    </section>
  );
}
