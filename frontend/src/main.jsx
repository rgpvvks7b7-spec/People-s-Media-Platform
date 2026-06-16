import React, { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import "./styles/app.css";

const API = "http://localhost:8000/api";

if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("/sw.js").catch(() => {});
  });
}

function getCookie(name) {
  return document.cookie
    .split("; ")
    .find(row => row.startsWith(`${name}=`))
    ?.split("=")[1];
}

function apiFetch(path, options = {}) {
  const headers = options.headers ? { ...options.headers } : {};
  const method = options.method || "GET";

  if (!["GET", "HEAD", "OPTIONS"].includes(method.toUpperCase())) {
    const csrfToken = getCookie("csrftoken");
    if (csrfToken) headers["X-CSRFToken"] = csrfToken;
  }

  return fetch(`${API}${path}`, {
    credentials: "include",
    ...options,
    headers,
  });
}

function App() {
  const [activePage, setActivePage] = useState("home");
  const [artists, setArtists] = useState([]);
  const [discoveryArtists, setDiscoveryArtists] = useState([]);
  const [discoveryMeta, setDiscoveryMeta] = useState({ skipped_count: 0, count: 0 });
  const [savedArtists, setSavedArtists] = useState([]);
  const [music, setMusic] = useState([]);
  const [posts, setPosts] = useState([]);
  const [products, setProducts] = useState([]);
  const [followStats, setFollowStats] = useState({});
  const [storeFormType, setStoreFormType] = useState(null);
  const [showPostForm, setShowPostForm] = useState(false);
  const [showMusicForm, setShowMusicForm] = useState(false);
  const [showLiveForm, setShowLiveForm] = useState(false);
  const [previewAsFan, setPreviewAsFan] = useState(false);
  const [showEditProfile, setShowEditProfile] = useState(false);
  const [subData, setSubData] = useState({ subscriptions: [], fan_totals: {}, artist_totals: {} });
  const [message, setMessage] = useState("");
  const [selectedArtist, setSelectedArtist] = useState(null);
  const [activeTab, setActiveTab] = useState("music");
  const [currentUser, setCurrentUser] = useState(null);
  const [authMode, setAuthMode] = useState("login");
  const [registerType, setRegisterType] = useState("fan");
  const [searchLocation, setSearchLocation] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [savedSearchQuery, setSavedSearchQuery] = useState("");
  const [savedGenreFilter, setSavedGenreFilter] = useState("");
  const [reviewIndex, setReviewIndex] = useState(0);
  const [swipeStartX, setSwipeStartX] = useState(null);
  const [swipeDeltaX, setSwipeDeltaX] = useState(0);
  const [lastSkippedArtist, setLastSkippedArtist] = useState(null);
  const [lastReviewAction, setLastReviewAction] = useState(null);
  const [expandedWhyArtistId, setExpandedWhyArtistId] = useState(null);
  const [skipUndoDismissed, setSkipUndoDismissed] = useState(
    () => window.localStorage.getItem("hideSkipUndoPrompt") === "true"
  );

  function loadData() {
    apiFetch("/artists/").then(r => r.json()).then(setArtists);
    apiFetch("/media/").then(r => r.json()).then(setMusic);
    apiFetch("/posts/").then(r => r.json()).then(setPosts);
    apiFetch("/marketplace/").then(r => r.json()).then(setProducts);
    apiFetch("/artists/follow-stats/").then(r => r.json()).then(setFollowStats);
    apiFetch("/subscriptions/").then(r => r.json()).then(setSubData);
  }

  function loadDiscovery(options = {}) {
    const params = new URLSearchParams();
    if (searchQuery.trim()) params.set("q", searchQuery.trim());
    if (searchLocation.trim()) params.set("location", searchLocation.trim());
    if (options.backfill) params.set("backfill", "true");

    const queryString = params.toString();
    return apiFetch(`/discovery/artists/${queryString ? `?${queryString}` : ""}`)
      .then(r => r.json())
      .then(data => {
        setDiscoveryArtists(data.results || []);
        setDiscoveryMeta({
          skipped_count: data.skipped_count || 0,
          count: data.count || 0,
        });
      });
  }

  function loadSavedArtists() {
    apiFetch("/discovery/saved-artists/")
      .then(r => r.json())
      .then(data => setSavedArtists(data.results || []));
  }

  async function loadCurrentUser() {
    const res = await apiFetch("/accounts/current-user/");
    const data = await res.json();
    setCurrentUser(data.user);
    setSearchLocation(data.user?.discovery_location || "");
  }

  useEffect(() => {
    loadCurrentUser();
    loadData();

    const params = new URLSearchParams(window.location.search);
    const supportStatus = params.get("support");

    if (supportStatus === "success") {
      setMessage("Payment started. Your supporter access will unlock after Stripe confirms the subscription.");
      window.history.replaceState({}, "", window.location.pathname);
    }

    if (supportStatus === "cancelled") {
      setMessage("Checkout cancelled. You were not charged.");
      window.history.replaceState({}, "", window.location.pathname);
    }
  }, []);

  useEffect(() => {
    const timeoutId = window.setTimeout(loadDiscovery, 150);
    return () => window.clearTimeout(timeoutId);
  }, [searchQuery, searchLocation, currentUser?.id]);

  useEffect(() => {
    loadSavedArtists();
  }, [currentUser?.id]);

  function isSupporting(username) {
    return subData.subscriptions?.some(sub => sub.artist === username && sub.fan_id === currentUser?.id && sub.active);
  }


  async function followArtist(username) {
    if (!currentUser) {
      setMessage("Log in before following artists.");
      return;
    }

    const artist = artists.find(
      a => a.owner_username === username
    );

    if (!artist) return;

    await apiFetch("/artists/follow/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        artist_id: artist.owner_id
      })
    });

    loadData();
  }

  async function toggleDiscoveryFollow(artist) {
    if (!currentUser) {
      setMessage("Log in before following artists.");
      return;
    }

    const endpoint = artist.viewer_following ? "/artists/unfollow/" : "/artists/follow/";
    const res = await apiFetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ artist_id: artist.owner_id }),
    });
    const data = await res.json();

    if (!res.ok) {
      setMessage(data.error || "Unable to update follow.");
      return;
    }

    setMessage(artist.viewer_following ? `Unfollowed ${artist.stage_name}.` : `Following ${artist.stage_name}.`);
    loadData();
    loadDiscovery({ backfill: true });
    loadSavedArtists();
  }


  async function supportArtist(username) {
    if (!currentUser) {
      setMessage("Log in before supporting artists.");
      return;
    }

    const artist = artists.find(a => a.owner_username === username);
    if (!artist) return;

    const res = await apiFetch("/subscriptions/checkout/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ artist_id: artist.owner_id, monthly_amount: "1.00", billing_date: new Date().getDate() }),
    });
    const data = await res.json();

    if (!res.ok) {
      setMessage(data.error || "Unable to start checkout.");
      return;
    }

    if (data.checkout_url) {
      window.location.href = data.checkout_url;
      return;
    }

    setMessage(data.message || "Checkout started.");
  }

  async function sendDiscoverySignal(artist, signalType) {
    if (!currentUser) {
      setMessage("Log in before personalizing discovery.");
      return;
    }

    const res = await apiFetch("/discovery/signal/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        artist_id: artist.owner_id,
        signal_type: signalType,
      }),
    });
    const data = await res.json();

    if (!res.ok) {
      setMessage(data.error || "Unable to save discovery signal.");
      return;
    }

    const labels = {
      save: "Saved. Discovery will keep this artist in mind.",
      skip: "Skipped. This artist will be hidden from your recommendations.",
      more_like_this: "Got it. Discovery will look for more artists like this.",
    };

    setMessage(labels[signalType] || data.message || "Discovery updated.");
    if (activePage === "discover") {
      setLastReviewAction({ artist, signalType });
    }
    if (signalType === "skip") {
      if (!skipUndoDismissed) {
        setLastSkippedArtist(artist);
      }
      setDiscoveryArtists(currentArtists => currentArtists.filter(item => item.owner_id !== artist.owner_id));
    }
    if (activePage === "discover" && signalType !== "skip") {
      advanceReview();
    }
    loadDiscovery({ backfill: signalType === "skip" });
    loadSavedArtists();
  }

  async function undoLastReviewAction() {
    if (!lastReviewAction) return;

    const res = await apiFetch("/discovery/undo-signal/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        artist_id: lastReviewAction.artist.owner_id,
        signal_type: lastReviewAction.signalType,
      }),
    });
    const data = await res.json();

    if (!res.ok) {
      setMessage(data.error || "Unable to undo last action.");
      return;
    }

    setMessage(`Undid ${lastReviewAction.signalType.replaceAll("_", " ")} for ${lastReviewAction.artist.stage_name}.`);
    setLastReviewAction(null);
    setLastSkippedArtist(null);
    loadDiscovery({ backfill: true });
    loadSavedArtists();
  }

  async function removeSavedArtist(artist) {
    if (!currentUser) return;

    const res = await apiFetch("/discovery/remove-saved/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ artist_id: artist.owner_id }),
    });
    const data = await res.json();

    if (!res.ok) {
      setMessage(data.error || "Unable to remove saved artist.");
      return;
    }

    setMessage(`${artist.stage_name} removed from saved artists.`);
    loadDiscovery({ backfill: true });
    loadSavedArtists();
  }

  async function undoLastSkip() {
    if (!lastSkippedArtist) return;

    const res = await apiFetch("/discovery/undo-skip/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ artist_id: lastSkippedArtist.owner_id }),
    });
    const data = await res.json();

    if (!res.ok) {
      setMessage(data.error || "Unable to undo skip.");
      return;
    }

    setMessage(`${lastSkippedArtist.stage_name} is back in discovery.`);
    setLastSkippedArtist(null);
    loadDiscovery({ backfill: true });
  }

  function dismissSkipUndoPrompt(permanent = false) {
    if (permanent) {
      window.localStorage.setItem("hideSkipUndoPrompt", "true");
      setSkipUndoDismissed(true);
    }
    setLastSkippedArtist(null);
  }

  async function resetSkippedArtists() {
    if (!currentUser) return;

    const res = await apiFetch("/discovery/reset-skips/", { method: "POST" });
    const data = await res.json();

    if (!res.ok) {
      setMessage(data.error || "Unable to reset skipped artists.");
      return;
    }

    setMessage(data.message || "Skipped artists reset.");
    loadDiscovery({ backfill: true });
  }

  function showAllArtists() {
    setSearchQuery("");
    setSearchLocation("");
    loadDiscovery({ backfill: true });
  }

  async function manageSupport(username) {
    if (!currentUser) {
      setMessage("Log in before managing support.");
      return;
    }

    const artist = artists.find(a => a.owner_username === username);
    if (!artist) return;

    const res = await apiFetch("/subscriptions/billing-portal/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ artist_id: artist.owner_id }),
    });
    const data = await res.json();

    if (!res.ok) {
      setMessage(data.error || "Unable to open subscription management.");
      return;
    }

    if (data.portal_url) {
      window.location.href = data.portal_url;
    }
  }



  async function createPost(event) {
    event.preventDefault();

    const form = event.target;
    const formData = new FormData(form);

    const res = await apiFetch("/posts/create/", {
      method: "POST",
      body: formData,
    });

    const data = await res.json();
    setMessage(data.message || data.error || "Post saved.");
    setShowPostForm(false);
    loadData();
  }

  async function togglePostLike(postId) {
    if (!currentUser) {
      setMessage("Log in before liking posts.");
      return;
    }

    const res = await apiFetch(`/posts/${postId}/toggle-like/`, {
      method: "POST",
    });
    const data = await res.json();
    setMessage(data.message || data.error || "Updated.");
    loadData();
  }

  async function createComment(event, postId) {
    event.preventDefault();

    if (!currentUser) {
      setMessage("Log in before commenting.");
      return;
    }

    const form = event.target;
    const formData = new FormData(form);

    const res = await apiFetch(`/posts/${postId}/comment/`, {
      method: "POST",
      body: formData,
    });
    const data = await res.json();

    if (res.ok) {
      form.reset();
    }

    setMessage(data.message || data.error || "Comment saved.");
    loadData();
  }

  async function createProduct(event) {
    event.preventDefault();

    const form = event.target;
    const formData = new FormData(form);

    formData.append("product_type", storeFormType);

    const res = await apiFetch("/marketplace/create/", {
      method: "POST",
      body: formData,
    });

    const data = await res.json();
    setMessage(data.message || data.error || "Product saved.");
    setStoreFormType(null);
    loadData();
  }

  function productTypeLabel(type) {
    if (type === "merch") return "Merch";
    if (type === "beat") return "Beat";
    if (type === "sample_pack") return "Sample Pack";
    if (type === "acapella") return "Acapella";
    return type;
  }


  async function uploadTrack(event) {
    event.preventDefault();

    const form = event.target;
    const formData = new FormData(form);

    const res = await apiFetch("/media/create/", {
      method: "POST",
      body: formData,
    });

    const data = await res.json();

    setMessage(data.message || data.error || "Track uploaded.");
    setShowMusicForm(false);
    loadData();
  }


  async function updateArtistProfile(event) {
    event.preventDefault();

    const form = event.target;
    const formData = new FormData(form);

    const res = await apiFetch("/artists/update-profile/", {
      method: "POST",
      body: formData,
    });

    const data = await res.json();

    setMessage(data.message || data.error || "Profile updated.");
    setShowEditProfile(false);
    loadData();

    setSelectedArtist({
      ...selectedArtist,
      stage_name: formData.get("stage_name"),
      genre: formData.get("genre"),
      city: formData.get("city"),
      artist_story: formData.get("artist_story"),
      influences: formData.get("influences"),
    });
  }


  async function savePageBuilder(event) {
    event.preventDefault();

    const form = event.target;
    const formData = new FormData();

    formData.append("show_music", form.show_music.checked ? "true" : "false");
    formData.append("show_posts", form.show_posts.checked ? "true" : "false");
    formData.append("show_store", form.show_store.checked ? "true" : "false");
    formData.append("show_lives", form.show_lives.checked ? "true" : "false");
    formData.append("show_about", form.show_about.checked ? "true" : "false");

    const res = await apiFetch("/artists/update-page-builder/", {
      method: "POST",
      body: formData,
    });

    const data = await res.json();

    setMessage(data.message || data.error || "Page layout updated.");

    setSelectedArtist({
      ...selectedArtist,
      show_music: form.show_music.checked,
      show_posts: form.show_posts.checked,
      show_store: form.show_store.checked,
      show_lives: form.show_lives.checked,
      show_about: form.show_about.checked,
    });

    loadData();
  }

  function openArtist(artist) {
    setSelectedArtist(artist);
    setActiveTab("music");
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function goToPage(page) {
    setActivePage(page);
    setSelectedArtist(null);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  async function handleAuth(event) {
    event.preventDefault();

    const form = event.target;
    const formData = new FormData(form);
    const payload = Object.fromEntries(formData.entries());
    const endpoint = authMode === "register" ? "/accounts/register/" : "/accounts/login/";

    if (!getCookie("csrftoken")) {
      await apiFetch("/accounts/current-user/");
    }

    const res = await apiFetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await res.json();

    if (!res.ok) {
      setMessage(data.error || "Authentication failed.");
      return;
    }

    setCurrentUser(data.user);
    setMessage(data.message || "Signed in.");
    form.reset();
    loadData();
    loadDiscovery();
    loadSavedArtists();

    if (data.user?.is_artist) {
      const artistListRes = await apiFetch("/artists/");
      const artistList = await artistListRes.json();
      setArtists(artistList);
      const artist = artistList.find(a => a.owner_username === data.user.username);
      if (artist) {
        openArtist(artist);
        setActiveTab("dashboard");
      }
    } else {
      setSelectedArtist(null);
      setSearchLocation(data.user?.discovery_location || "");
      setActivePage("discover");
    }
  }

  async function handleLogout() {
    const res = await apiFetch("/accounts/logout/", { method: "POST" });
    const data = await res.json();
    setCurrentUser(null);
    setSavedArtists([]);
    setMessage(data.message || "Logged out.");
    setSelectedArtist(null);
    loadData();
    loadDiscovery();
  }

  const artistTracks = selectedArtist
    ? music.filter(track => track.artist_username === selectedArtist.owner_username)
    : [];

  const artistPosts = selectedArtist
    ? posts.filter(post => post.author_username === selectedArtist.owner_username)
    : [];

  const artistProducts = selectedArtist
    ? products.filter(product => product.artist_username === selectedArtist.owner_username)
    : [];

  const fanTotal = currentUser ? subData.fan_totals?.[currentUser.username] || "0.00" : "0.00";
  const filteredArtists = discoveryArtists;
  const savedGenres = [...new Set(savedArtists.map(artist => artist.genre).filter(Boolean))].sort();
  const filteredSavedArtists = savedArtists.filter(artist => {
    const query = savedSearchQuery.trim().toLowerCase();
    const queryMatch = query
      ? [artist.stage_name, artist.owner_username, artist.genre, artist.city]
          .some(value => value?.toLowerCase().includes(query))
      : true;
    const genreMatch = savedGenreFilter ? artist.genre === savedGenreFilter : true;
    return queryMatch && genreMatch;
  });
  const reviewArtist = filteredArtists[reviewIndex] || filteredArtists[0];

  useEffect(() => {
    setReviewIndex(0);
  }, [searchQuery, searchLocation, currentUser?.id]);

  function advanceReview() {
    setReviewIndex(current => {
      if (filteredArtists.length <= 1) return 0;
      return Math.min(current + 1, filteredArtists.length - 1);
    });
  }

  function finishSwipe(endX) {
    if (swipeStartX === null || !reviewArtist) return;

    const delta = endX - swipeStartX;
    setSwipeStartX(null);
    setSwipeDeltaX(0);

    if (Math.abs(delta) < 80) return;

    if (delta < 0) {
      sendDiscoverySignal(reviewArtist, "skip");
      return;
    }

    sendDiscoverySignal(reviewArtist, "save");
  }

  function updateSwipe(currentX) {
    if (swipeStartX === null) return;
    const delta = currentX - swipeStartX;
    setSwipeDeltaX(Math.max(-160, Math.min(160, delta)));
  }

  function renderDiscoveryArtistCard(artist, compact = false) {
    const supporting = isSupporting(artist.owner_username);
    const artistTrack = music.find(track => track.artist_username === artist.owner_username);

    return (
      <article className={compact ? "artist-card compact-card" : "artist-card"} key={artist.id}>
        <div className="artist-banner" onClick={() => openArtist(artist)}></div>
        <div className="artist-body">
          <div className="artist-card-content">
            <div className="avatar" onClick={() => openArtist(artist)}>{artist.stage_name?.[0]?.toUpperCase()}</div>
            <div className="artist-row-head">
              <div>
                <h3 onClick={() => openArtist(artist)} className="click-title">{artist.stage_name} {artist.is_verified ? "✅" : ""}</h3>
                <p className="muted">{artist.genre} • {artist.city}</p>
              </div>
              <div className="artist-row-primary">
                <button
                  className="secondary small-pill"
                  onClick={() => toggleDiscoveryFollow(artist)}
                >
                  {artist.viewer_following ? "Following" : "Follow"}
                </button>
                <button
                  className={supporting ? "supporting small-pill" : "primary small-pill"}
                  onClick={() => supporting ? manageSupport(artist.owner_username) : supportArtist(artist.owner_username)}
                >
                  {supporting ? "Managing" : "Support $1"}
                </button>
              </div>
            </div>

            {artistTrack && (
              <div className="card-track">
                <div>
                  <strong>{artistTrack.title}</strong>
                  <p className="muted">{artistTrack.genre} • {artistTrack.bpm || "No"} BPM</p>
                </div>
                {artistTrack.audio_file ? (
                  <audio controls preload="none" src={artistTrack.audio_file}></audio>
                ) : (
                  <p className="muted">{artistTrack.access_message || "Supporters only"}</p>
                )}
              </div>
            )}

            <div className="discovery-meta">
              <span>Score {artist.discovery_score}</span>
              {artist.signals && <span>{artist.signals.tracks} tracks</span>}
              {artist.signals && <span>{artist.signals.supporters} supporters</span>}
            </div>
            <button
              className="why-button"
              onClick={() => setExpandedWhyArtistId(expandedWhyArtistId === artist.id ? null : artist.id)}
            >
              Why this artist?
            </button>
            {expandedWhyArtistId === artist.id && (
              <div className="why-panel">
                {["genre", "location", "similarity", "activity", "community"].map(category => {
                  const reason = artist.discovery_reasons?.find(item => item.category === category);
                  const labels = {
                    genre: "Genre match",
                    location: "Location match",
                    similarity: "Similar artist signal",
                    activity: "Activity signal",
                    community: "Supporter/follower signal",
                  };

                  return (
                    <div className="why-row" key={`${artist.id}-${category}`}>
                      <strong>{labels[category]}</strong>
                      <span>{reason ? `${reason.detail} (+${reason.points})` : "No signal for this artist yet."}</span>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          <div className="artist-card-actions">
            <div className="discovery-actions">
              <button
                className={artist.viewer_signal === "save" ? "signal-button active" : "signal-button"}
                onClick={() => artist.viewer_signal === "save" ? removeSavedArtist(artist) : sendDiscoverySignal(artist, "save")}
              >
                {artist.viewer_signal === "save" ? "Unsave" : "Save"}
              </button>
              <button
                className={artist.viewer_signal === "more_like_this" ? "signal-button active" : "signal-button"}
                onClick={() => sendDiscoverySignal(artist, "more_like_this")}
              >
                More like this
              </button>
              <button
                className="signal-button"
                onClick={() => sendDiscoverySignal(artist, "skip")}
              >
                Skip
              </button>
            </div>
          </div>
        </div>
      </article>
    );
  }

  function renderSavedArtistRow(artist) {
    const supporting = isSupporting(artist.owner_username);
    const artistTrack = music.find(track => track.artist_username === artist.owner_username);

    return (
      <article className="saved-row" key={artist.id}>
        <div className="saved-identity">
          {artistTrack?.cover_art ? (
            <img className="saved-cover" src={artistTrack.cover_art} alt={artistTrack.title} onClick={() => openArtist(artist)} />
          ) : (
            <div className="saved-avatar" onClick={() => openArtist(artist)}>{artist.stage_name?.[0]?.toUpperCase()}</div>
          )}
          <div>
            <h3 className="click-title" onClick={() => openArtist(artist)}>{artist.stage_name} {artist.is_verified ? "✅" : ""}</h3>
            <p className="muted">{artist.genre} • {artist.city}</p>
            <div className="saved-status">
              <span>{supporting ? "Supporting" : "Not supporting"}</span>
              {artist.viewer_following && <span>Following</span>}
            </div>
          </div>
        </div>

        <div className="saved-preview">
          {artistTrack ? (
            <>
              <strong>{artistTrack.title}</strong>
              {artistTrack.audio_file ? (
                <audio controls preload="none" src={artistTrack.audio_file}></audio>
              ) : (
                <p className="muted">{artistTrack.access_message || "Supporters only"}</p>
              )}
            </>
          ) : (
            <p className="muted">No preview track yet.</p>
          )}
        </div>

        <div className="saved-actions">
          <button className="secondary small-pill" onClick={() => toggleDiscoveryFollow(artist)}>
            {artist.viewer_following ? "Unfollow" : "Follow"}
          </button>
          <button
            className={supporting ? "supporting small-pill" : "primary small-pill"}
            onClick={() => supporting ? manageSupport(artist.owner_username) : supportArtist(artist.owner_username)}
          >
            {supporting ? "Manage" : "Support $1"}
          </button>
          <button className="secondary small-pill" onClick={() => removeSavedArtist(artist)}>
            Remove
          </button>
        </div>
      </article>
    );
  }

  function renderReviewArtist() {
    if (!reviewArtist) {
      return (
        <div className="empty-state full-span">
          <h3>No artists to review.</h3>
          <p>Clear filters or reset skipped artists to bring more recommendations into review mode.</p>
        </div>
      );
    }

    const artist = reviewArtist;
    const supporting = isSupporting(artist.owner_username);
    const artistTrack = music.find(track => track.artist_username === artist.owner_username);

    return (
      <section className="review-mode">
        <div
          className="review-panel"
          style={{
            transform: `translateX(${swipeDeltaX}px) rotate(${swipeDeltaX / 24}deg)`,
          }}
          onPointerDown={(event) => setSwipeStartX(event.clientX)}
          onPointerMove={(event) => updateSwipe(event.clientX)}
          onPointerUp={(event) => finishSwipe(event.clientX)}
          onPointerCancel={() => {
            setSwipeStartX(null);
            setSwipeDeltaX(0);
          }}
        >
          <div className="review-hero">
            {artistTrack?.cover_art ? (
              <img className="review-cover" src={artistTrack.cover_art} alt={artistTrack.title} onClick={() => openArtist(artist)} />
            ) : (
              <div className="review-avatar" onClick={() => openArtist(artist)}>{artist.stage_name?.[0]?.toUpperCase()}</div>
            )}
            <div>
              <p className="eyebrow">Artist {Math.min(reviewIndex + 1, filteredArtists.length)} of {filteredArtists.length}</p>
              <h3 onClick={() => openArtist(artist)} className="click-title">{artist.stage_name} {artist.is_verified ? "✅" : ""}</h3>
              <p className="muted">{artist.genre} • {artist.city}</p>
            </div>
          </div>

          <div className={swipeDeltaX > 24 ? "swipe-label save-label visible" : "swipe-label save-label"}>Save</div>
          <div className={swipeDeltaX < -24 ? "swipe-label skip-label visible" : "swipe-label skip-label"}>Skip for now</div>

          <div className="review-main">
            <div>
              <p className="review-story">{artist.artist_story}</p>
              <p className="tag">Influences: {artist.influences}</p>

              {artistTrack && (
                <div className="review-track">
                  <div>
                    <p className="eyebrow">Preview track</p>
                    <strong>{artistTrack.title}</strong>
                    <p className="muted">{artistTrack.genre} • {artistTrack.bpm || "No"} BPM</p>
                  </div>
                  {artistTrack.audio_file ? (
                    <audio controls preload="none" src={artistTrack.audio_file}></audio>
                  ) : (
                    <p className="muted">{artistTrack.access_message || "Supporters only"}</p>
                  )}
                </div>
              )}
            </div>

            <div className="review-signals">
              <div className="discovery-meta compact-meta">
                <span>Score {artist.discovery_score}</span>
                {artist.signals && <span>{artist.signals.tracks} tracks</span>}
                {artist.signals && <span>{artist.signals.supporters} supporters</span>}
              </div>
              {artist.discovery_reasons?.length > 0 && (
                <div className="reason-list compact-reasons">
                  {artist.discovery_reasons.slice(0, 4).map(reason => (
                    <span key={`${artist.id}-${reason.label}`}>{reason.label}</span>
                  ))}
                </div>
              )}
              <button
                className="why-button"
                onClick={() => setExpandedWhyArtistId(expandedWhyArtistId === artist.id ? null : artist.id)}
              >
                Why this artist?
              </button>
            </div>
          </div>

          {expandedWhyArtistId === artist.id && (
            <div className="why-panel review-why">
              {["genre", "location", "similarity", "activity", "community"].map(category => {
                const reason = artist.discovery_reasons?.find(item => item.category === category);
                const labels = {
                  genre: "Genre match",
                  location: "Location match",
                  similarity: "Similar artist signal",
                  activity: "Activity signal",
                  community: "Supporter/follower signal",
                };

                return (
                  <div className="why-row" key={`${artist.id}-${category}`}>
                    <strong>{labels[category]}</strong>
                    <span>{reason ? `${reason.detail} (+${reason.points})` : "No signal for this artist yet."}</span>
                  </div>
                );
              })}
            </div>
          )}

          <div className="review-primary-actions">
            <button className="secondary" onClick={() => toggleDiscoveryFollow(artist)}>
              {artist.viewer_following ? "Following - Unfollow" : "Follow Artist"}
            </button>
            <button
              className={supporting ? "supporting review-support" : "primary"}
              onClick={() => supporting ? manageSupport(artist.owner_username) : supportArtist(artist.owner_username)}
            >
              {supporting ? "Managing support" : "Support Artist - $1/month"}
            </button>
          </div>
        </div>

        <div className="review-controls">
          <button className="secondary" onClick={() => sendDiscoverySignal(reviewArtist, "skip")}>
            Skip for now
          </button>
          <button className="primary" onClick={() => sendDiscoverySignal(reviewArtist, "save")}>
            Save
          </button>
          <button className="secondary" onClick={() => sendDiscoverySignal(reviewArtist, "more_like_this")}>
            More like this
          </button>
          <button className="secondary" onClick={advanceReview}>
            Next artist
          </button>
          <button className="secondary" onClick={undoLastReviewAction} disabled={!lastReviewAction}>
            Undo previous
          </button>
        </div>
        <p className="muted review-note">
          Swipe left to skip for now. Swipe right to save. Skip is not a dislike.
        </p>
      </section>
    );
  }

  const authPanel = (
    <section className="auth-panel">
      <div>
        <p className="eyebrow">Account</p>
        {currentUser ? (
          <>
            <h2>Signed in as {currentUser.display_name || currentUser.username}</h2>
            <p className="muted">{currentUser.username} • {currentUser.user_type}</p>
          </>
        ) : (
          <>
            <h2>{authMode === "register" ? "Create your account" : "Log in"}</h2>
            <p className="muted">Use a fan account to support artists or an artist account to manage your page.</p>
          </>
        )}
      </div>

      {currentUser ? (
        <button className="secondary" onClick={handleLogout}>Log Out</button>
      ) : (
        <form className="auth-form" onSubmit={handleAuth}>
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
          </div>

          <input name="username" placeholder="Username" required />
          <input name="password" type="password" placeholder="Password" required />

          {authMode === "register" && (
            <>
              <input name="display_name" placeholder="Display name" />
              <select name="user_type" value={registerType} onChange={(event) => setRegisterType(event.target.value)}>
                <option value="fan">Fan</option>
                <option value="artist">Artist</option>
              </select>

              {registerType === "fan" && (
                <>
                  <input name="favorite_genres" placeholder="Favorite genres" />
                  <input name="discovery_location" placeholder="Search location" />
                </>
              )}

              {registerType === "artist" && (
                <>
                  <input name="stage_name" placeholder="Stage name" />
                  <input name="genre" placeholder="Artist genre" />
                  <input name="city" placeholder="Artist city" />
                  <input name="influences" placeholder="Artist influences" />
                  <textarea name="artist_story" placeholder="Short artist story"></textarea>
                </>
              )}
            </>
          )}

          <button className="primary" type="submit">
            {authMode === "register" ? "Create Account" : "Log In"}
          </button>
        </form>
      )}
    </section>
  );

  if (selectedArtist) {
    const supporting = isSupporting(selectedArtist.owner_username);
    const selectedDiscoveryRecord = [...discoveryArtists, ...savedArtists]
      .find(artist => artist.owner_id === selectedArtist.owner_id);
    const followingSelected = Boolean(selectedDiscoveryRecord?.viewer_following);
    const selectedSaved = savedArtists.some(artist => artist.owner_id === selectedArtist.owner_id);
    const profilePreviewTrack = music.find(track => track.artist_username === selectedArtist.owner_username);

    const realOwner =
      currentUser?.username === selectedArtist.owner_username;

    const isOwner = realOwner && !previewAsFan;
    const earnings = subData.artist_totals?.[selectedArtist.owner_username] || "0.00";
    const supporterCount = subData.subscriptions?.filter(sub => sub.artist === selectedArtist.owner_username).length || 0;
    const visibleTabs = [
      selectedArtist.show_music && "music",
      selectedArtist.show_posts && "posts",
      selectedArtist.show_store && "store",
      selectedArtist.show_lives && "lives",
      isOwner && "dashboard",
      isOwner && "settings",
      selectedArtist.show_about && "about",
    ].filter(Boolean);
    const currentTab = visibleTabs.includes(activeTab) ? activeTab : visibleTabs[0];

    return (
      <main>
        <nav className="topbar">
          <button className="back-button" onClick={() => goToPage("discover")}>← Back to Discover</button>
          <div className="logo">INDIE<span>FUND</span></div>
          <div className="auth-summary">
            {currentUser ? (
              <>
                <span>{currentUser.display_name || currentUser.username}</span>
                <button className="secondary" onClick={handleLogout}>Log Out</button>
              </>
            ) : (
              <button className="secondary" onClick={() => setSelectedArtist(null)}>Log In</button>
            )}
          </div>
        </nav>

        {message && <div className="notice">{message}</div>}

        <section className="profile-hero">
          <div className="profile-banner"></div>
          <div className="profile-info">
            <div className="profile-avatar">{selectedArtist.stage_name?.[0]?.toUpperCase()}</div>
            <div>
              <h1>{selectedArtist.stage_name} {selectedArtist.is_verified ? "✅" : ""}</h1>
              <p className="muted">{selectedArtist.genre} • {selectedArtist.city}</p>
              <p>{selectedArtist.artist_story}</p>
            </div>
            <div className="profile-actions">
              <button
                className="secondary"
                onClick={() => toggleDiscoveryFollow(selectedDiscoveryRecord || selectedArtist)}
              >
                {followingSelected ? "Following" : "Follow"}
              </button>
              <button
                className={selectedSaved ? "secondary" : "secondary"}
                onClick={() => selectedSaved ? removeSavedArtist(selectedDiscoveryRecord || selectedArtist) : sendDiscoverySignal(selectedDiscoveryRecord || selectedArtist, "save")}
              >
                {selectedSaved ? "Saved" : "Save"}
              </button>
              <button
                className={supporting ? "supporting" : "primary"}
                onClick={() => supporting ? manageSupport(selectedArtist.owner_username) : supportArtist(selectedArtist.owner_username)}
              >
                {supporting ? "Managing support" : "Support $1/month"}
              </button>
            </div>
          </div>

          {profilePreviewTrack && (
            <div className="profile-preview">
              {profilePreviewTrack.cover_art ? (
                <img src={profilePreviewTrack.cover_art} alt={profilePreviewTrack.title} />
              ) : (
                <div className="cover-placeholder"></div>
              )}
              <div>
                <p className="eyebrow">Featured track</p>
                <h3>{profilePreviewTrack.title}</h3>
                <p className="muted">{profilePreviewTrack.genre} • {profilePreviewTrack.bpm || "No"} BPM</p>
                {profilePreviewTrack.audio_file ? (
                  <audio controls preload="none" src={profilePreviewTrack.audio_file}></audio>
                ) : (
                  <p className="muted">{profilePreviewTrack.access_message || "Supporters only"}</p>
                )}
              </div>
            </div>
          )}

          <div className="stats-row">
            <div><strong>{supporterCount}</strong><span>Supporters</span></div>
            <div><strong>${earnings}</strong><span>Monthly artist revenue</span></div>
            <div><strong>90%</strong><span>Artist share</span></div>
          </div>
        </section>

        <section className="tabs">
          {visibleTabs.map(tab => (
            <button
              key={tab}
              className={currentTab === tab ? "tab active" : "tab"}
              onClick={() => setActiveTab(tab)}
            >
              {tab}
            </button>
          ))}
        </section>

        <section className="tab-panel">
          {!currentTab && (
            <div className="empty-state">
              <h3>No public sections.</h3>
              <p>This artist has not made any page sections public yet.</p>
            </div>
          )}

          {currentTab === "music" && (
            <>
              <div className="tab-title-row">
                <h2>Music</h2>
                {isOwner && (
                  <button className="small-action" onClick={() => setShowMusicForm(true)}>
                    + Upload Track
                  </button>
                )}
              </div>

              {isOwner && showMusicForm && (
                <form className="store-form" onSubmit={uploadTrack}>
                  <h3>Upload Track</h3>

                  <label>Title</label>
                  <input name="title" required placeholder="Track title" />

                  <label>Genre</label>
                  <input name="genre" placeholder="Hip Hop" />

                  <label>BPM</label>
                  <input name="bpm" type="number" placeholder="98" />

                  <label>Cover Art</label>
                  <input name="cover_art" type="file" accept="image/*" />

                  <label>Audio File</label>
                  <input name="audio_file" type="file" accept="audio/*" />

                  <label className="check-row">
                    <input name="is_downloadable" type="checkbox" value="true" />
                    Allow download
                  </label>

                  <label className="check-row">
                    <input name="is_subscriber_only" type="checkbox" value="true" />
                    Supporter only track
                  </label>

                  <div className="action-grid">
                    <button className="primary" type="submit">Publish Track</button>
                    <button className="secondary" type="button" onClick={() => setShowMusicForm(false)}>Cancel</button>
                  </div>
                </form>
              )}

              <div className="product-grid">
                {artistTracks.length === 0 && (
                  <div className="empty-state full-span">
                    <h3>No music yet.</h3>
                    <p>{isOwner ? "Upload your first track to start building your music page." : "This artist has not uploaded public music yet."}</p>
                  </div>
                )}

                {artistTracks.map(track => (
                  <article className="product-card" key={track.id}>
                    {track.cover_art && <img src={track.cover_art} alt={track.title} />}
                    {track.is_subscriber_only && (
                      <div className="post-badges"><span>Supporter only</span></div>
                    )}
                    <h3>{track.title}</h3>
                    <p>{track.genre} • {track.bpm} BPM</p>
                    {track.audio_file ? (
                      <audio controls src={track.audio_file}></audio>
                    ) : track.is_subscriber_only && (
                      <p className="muted">{track.access_message || "Supporters only"}</p>
                    )}
                  </article>
                ))}
              </div>
            </>
          )}

          {currentTab === "posts" && (
            <>
              <div className="tab-title-row">
                <h2>Posts</h2>
                {isOwner && (
                  <button className="small-action" onClick={() => setShowPostForm(true)}>
                    + Create Post
                  </button>
                )}
              </div>

              {isOwner && showPostForm && (
                <form className="store-form" onSubmit={createPost}>
                  <h3>Create Post</h3>

                  <label>Post type</label>
                  <select name="post_type" defaultValue="text">
                    <option value="text">Text</option>
                    <option value="music">Music</option>
                    <option value="story">Story</option>
                    <option value="live">Live</option>
                  </select>

                  <label>Title</label>
                  <input name="title" placeholder="Post title" />

                  <label>Body</label>
                  <textarea name="body" placeholder="Write your post..." />

                  <label>Attach file</label>
                  <input name="file" type="file" />

                  <label>Comment access</label>
                  <select name="comment_mode" defaultValue="account_default">
                    <option value="account_default">Use artist default</option>
                    <option value="anyone">Anyone</option>
                    <option value="followers_subscribers">Followers + Supporters</option>
                    <option value="subscribers_only">Supporters only</option>
                  </select>

                  <label className="check-row">
                    <input name="is_subscriber_only" type="checkbox" value="true" />
                    Supporter only post
                  </label>

                  <div className="action-grid">
                    <button className="primary" type="submit">Publish Post</button>
                    <button className="secondary" type="button" onClick={() => setShowPostForm(false)}>Cancel</button>
                  </div>
                </form>
              )}

              {artistPosts.length === 0 && !showPostForm && (
                <div className="empty-state">
                  <h3>No posts yet.</h3>
                  <p>{isOwner ? "Create your first update, story, announcement or supporter-only post." : "This artist has not posted yet."}</p>
                </div>
              )}

              <div className="post-list">
                {artistPosts.map(post => (
                  <article className="post-card" key={post.id}>
                    <div className="post-top">
                      <strong>{post.author_username}</strong>
                      <span>{post.post_type}</span>
                    </div>
                    <div className="post-badges">
                      {post.is_subscriber_only && <span>Supporter only</span>}
                      {post.effective_comment_mode && <span>Comments: {post.effective_comment_mode.replaceAll("_", " ")}</span>}
                    </div>
                    <h3>{post.title}</h3>
                    <p>{post.body}</p>
                    <div className="post-actions">
                      <button
                        className={post.liked_by_current_user ? "supporting compact" : "secondary compact"}
                        onClick={() => togglePostLike(post.id)}
                      >
                        {post.liked_by_current_user ? "Unlike" : "Like"} ({post.likes_count})
                      </button>
                      <span className="muted">{post.comments_count} comments</span>
                    </div>

                    <div className="comments-list">
                      {post.comments?.map(comment => (
                        <div className="comment-item" key={comment.id}>
                          <strong>{comment.author_username}</strong>
                          <p>{comment.body}</p>
                        </div>
                      ))}
                    </div>

                    {post.can_comment ? (
                      <form className="comment-form" onSubmit={(event) => createComment(event, post.id)}>
                        <input name="body" placeholder="Write a comment..." required />
                        <button className="secondary compact" type="submit">Comment</button>
                      </form>
                    ) : (
                      <p className="muted">{post.comment_block_reason || "Comments are restricted."}</p>
                    )}
                  </article>
                ))}
              </div>
            </>
          )}

          {currentTab === "store" && (
            <div>
              <div className="tab-title-row">
                <h2>Store</h2>
                {isOwner && <button className="small-action" onClick={() => setStoreFormType("merch")}>+ Add Product</button>}
              </div>

              {isOwner && (
                <div className="action-grid store-buttons">
                  <button className="primary" onClick={() => setStoreFormType("merch")}>+ Add Merch</button>
                  <button className="secondary" onClick={() => setStoreFormType("beat")}>+ Add Beat</button>
                  <button className="secondary" onClick={() => setStoreFormType("sample_pack")}>+ Add Sample Pack</button>
                  <button className="secondary" onClick={() => setStoreFormType("acapella")}>+ Add Acapella</button>
                </div>
              )}

              {storeFormType && (
                <form className="store-form" onSubmit={createProduct}>
                  <h3>Add {productTypeLabel(storeFormType)}</h3>

                  <label>Title</label>
                  <input name="title" required placeholder="Product title" />

                  <label>Description</label>
                  <textarea name="description" placeholder="What is this product?" />

                  <label>Price</label>
                  <input name="price" type="number" step="0.01" defaultValue="1.00" />

                  <label>Cover image</label>
                  <input name="image" type="file" accept="image/*" />

                  {storeFormType !== "merch" && (
                    <>
                      <label>Preview audio</label>
                      <input name="preview_audio" type="file" accept="audio/*" />

                      <label>Product file</label>
                      <input name="product_file" type="file" accept=".zip,audio/*" />

                      <label>BPM</label>
                      <input name="bpm" type="number" placeholder="98" />

                      <label>Key</label>
                      <input name="music_key" placeholder="A minor" />

                      <label>License type</label>
                      <input name="license_type" placeholder="Non-exclusive / Exclusive / Royalty-free" />
                    </>
                  )}

                  {storeFormType === "merch" && (
                    <>
                      <label>Sizes</label>
                      <input name="sizes" placeholder="S,M,L,XL" />

                      <label>Stock quantity</label>
                      <input name="stock_quantity" type="number" defaultValue="0" />

                      <label className="check-row">
                        <input name="shipping_required" type="checkbox" value="true" />
                        Shipping required
                      </label>
                    </>
                  )}

                  <label className="check-row">
                    <input name="is_supporter_only" type="checkbox" value="true" />
                    Supporter only
                  </label>

                  <div className="action-grid">
                    <button className="primary" type="submit">Save Product</button>
                    <button className="secondary" type="button" onClick={() => setStoreFormType(null)}>Cancel</button>
                  </div>
                </form>
              )}

              {artistProducts.length === 0 && !storeFormType && (
                <div className="empty-state">
                  <h3>No products yet.</h3>
                  <p>{isOwner ? "Add merch, beats, sample packs, acapellas or digital downloads directly to your artist store." : "This artist has not added products yet."}</p>
                </div>
              )}

              {artistProducts.length > 0 && (
                <div className="product-grid">
                  {artistProducts.map(product => (
                    <article className="product-card" key={product.id}>
                      {product.image && <img src={product.image} alt={product.title} />}
                      <div>
                        <p className="eyebrow">{productTypeLabel(product.product_type)}</p>
                        {product.is_supporter_only && (
                          <div className="post-badges"><span>Supporter only</span></div>
                        )}
                        <h3>{product.title}</h3>
                        <p>{product.description}</p>
                        <strong>${product.price}</strong>
                        {product.preview_audio && <audio controls src={product.preview_audio}></audio>}
                        {product.product_file && <p className="muted">Download file uploaded ✅</p>}
                        {!product.can_access && <p className="muted">{product.access_message || "Supporters only"}</p>}
                      </div>
                    </article>
                  ))}
                </div>
              )}
            </div>
          )}

          {currentTab === "lives" && (
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
                <form className="store-form">
                  <h3>Create Live Event</h3>

                  <label>Title</label>
                  <input placeholder="Beat Making Session" />

                  <label>Description</label>
                  <textarea placeholder="What is this live about?" />

                  <label>Public Preview</label>
                  <select defaultValue="30">
                    <option value="0">Subscribers Only</option>
                    <option value="10">10 Minutes</option>
                    <option value="30">30 Minutes</option>
                    <option value="60">60 Minutes</option>
                    <option value="999">Entire Stream Public</option>
                  </select>

                  <div className="action-grid">
                    <button type="button" className="primary">
                      Go Live
                    </button>

                    <button
                      type="button"
                      className="secondary"
                      onClick={() => setShowLiveForm(false)}
                    >
                      Cancel
                    </button>
                  </div>
                </form>
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
          )}

          
          {currentTab === "dashboard" && (
            <>
              <h2>Dashboard</h2>

              {artistTracks.length === 0 && artistPosts.length === 0 && artistProducts.length === 0 && (
                <div className="empty-state">
                  <h3>Set up your artist page.</h3>
                  <p>Upload your first track, create a post, or add a product to start building your page.</p>
                  <div className="action-grid">
                    <button className="secondary" onClick={() => setActiveTab("music")}>Upload first track</button>
                    <button className="secondary" onClick={() => setActiveTab("posts")}>Create first post</button>
                    <button className="secondary" onClick={() => setActiveTab("store")}>Add first product</button>
                  </div>
                </div>
              )}

              <div className="stats-row">
                <div className="feature-card">
                  <h3>Subscribers</h3>
                  <p>{supporterCount}</p>
                </div>

                <div className="feature-card">
                  <h3>Monthly Revenue</h3>
                  <p>${earnings}</p>
                </div>

                <div className="feature-card">
                  <h3>Tracks</h3>
                  <p>{artistTracks.length}</p>
                </div>

                <div className="feature-card">
                  <h3>Products</h3>
                  <p>{artistProducts.length}</p>
                </div>
              </div>
            </>
          )}

          {currentTab === "settings" && (
            <>
              <h2>Artist Settings</h2>

              {showEditProfile && (
                <form className="store-form" onSubmit={updateArtistProfile}>
                  <h3>Edit Profile</h3>

                  <label>Stage Name</label>
                  <input name="stage_name" defaultValue={selectedArtist.stage_name} />

                  <label>Genre</label>
                  <input name="genre" defaultValue={selectedArtist.genre} />

                  <label>City</label>
                  <input name="city" defaultValue={selectedArtist.city} />

                  <label>Bio</label>
                  <textarea name="artist_story" defaultValue={selectedArtist.artist_story}></textarea>

                  <label>Influences</label>
                  <input name="influences" defaultValue={selectedArtist.influences} />

                  <div className="action-grid">
                    <button className="primary" type="submit">Save Profile</button>
                    <button className="secondary" type="button" onClick={() => setShowEditProfile(false)}>Cancel</button>
                  </div>
                </form>
              )}



              <div className="feature-grid">

                <div className="feature-card">
                  <h3>Profile</h3>

                  <p><strong>Stage Name:</strong> {selectedArtist.stage_name}</p>
                  <p><strong>Genre:</strong> {selectedArtist.genre}</p>
                  <p><strong>City:</strong> {selectedArtist.city}</p>

                  <button className="primary" onClick={() => setShowEditProfile(true)}>
                    Edit Profile
                  </button>
                </div>

                <div className="feature-card">
                  <h3>Page Builder</h3>

                  <form onSubmit={savePageBuilder} className="settings-form">
                    <label className="check-row">
                      <input name="show_music" type="checkbox" defaultChecked={selectedArtist.show_music} />
                      Show Music
                    </label>

                    <label className="check-row">
                      <input name="show_posts" type="checkbox" defaultChecked={selectedArtist.show_posts} />
                      Show Posts
                    </label>

                    <label className="check-row">
                      <input name="show_store" type="checkbox" defaultChecked={selectedArtist.show_store} />
                      Show Store
                    </label>

                    <label className="check-row">
                      <input name="show_lives" type="checkbox" defaultChecked={selectedArtist.show_lives} />
                      Show Lives
                    </label>

                    <label className="check-row">
                      <input name="show_about" type="checkbox" defaultChecked={selectedArtist.show_about} />
                      Show About
                    </label>

                    <button className="secondary" type="submit">
                      Save Layout
                    </button>
                  </form>
                </div>

                <div className="feature-card">
                  <h3>Preview</h3>

                  <p>See exactly what fans see.</p>

                  <button
                    className="secondary"
                    onClick={() => setPreviewAsFan(!previewAsFan)}
                  >
                    {previewAsFan ? "Return to Artist View" : "Preview As Fan"}
                  </button>
                </div>

              </div>
            </>
          )}

{currentTab === "about" && (
            <div>
              <h2>About</h2>
              <p>{selectedArtist.artist_story}</p>
              <p><strong>Influences:</strong> {selectedArtist.influences}</p>
              <p><strong>Support model:</strong> $1/month minimum. Artist receives $0.90. Platform receives $0.10.</p>
            </div>
          )}
        </section>
      </main>
    );
  }

  return (
    <main className={`page-${activePage}`}>
      <nav className="topbar">
        <button className="logo logo-button" onClick={() => goToPage("home")}>INDIE<span>FUND</span></button>
        <div className="page-nav">
          <button className={activePage === "home" ? "nav-pill active" : "nav-pill"} onClick={() => goToPage("home")}>Home</button>
          <button className={activePage === "discover" ? "nav-pill active" : "nav-pill"} onClick={() => goToPage("discover")}>Discovery</button>
          <button className={activePage === "saved" ? "nav-pill active" : "nav-pill"} onClick={() => goToPage("saved")}>Saved</button>
          <button className={activePage === "music" ? "nav-pill active" : "nav-pill"} onClick={() => goToPage("music")}>Music</button>
        </div>
        {activePage === "discover" && (
          <div className="top-search">
            <input
              value={searchQuery}
              onChange={(event) => setSearchQuery(event.target.value)}
              placeholder="Search"
              aria-label="Search"
            />
            <input
              value={searchLocation}
              onChange={(event) => setSearchLocation(event.target.value)}
              placeholder="Any city"
              aria-label="Search location"
            />
          </div>
        )}
        <div className="auth-summary">
          {currentUser ? (
            <>
              <span>{currentUser.display_name || currentUser.username}</span>
              <button className="secondary" onClick={handleLogout}>Log Out</button>
            </>
          ) : (
            <button className="secondary" onClick={() => setAuthMode("login")}>Log In</button>
          )}
        </div>
      </nav>

      {!currentUser && authPanel}

      {message && <div className="notice">{message}</div>}

      {lastSkippedArtist && !skipUndoDismissed && (
        <section className="undo-panel">
          <div>
            <strong>Skipped {lastSkippedArtist.stage_name}.</strong>
            <p className="muted">You can undo this once if it was a mistake.</p>
          </div>
          <div className="undo-actions">
            <button className="primary" onClick={undoLastSkip}>Undo</button>
            <button className="secondary" onClick={() => dismissSkipUndoPrompt(false)}>Dismiss</button>
            <button className="secondary" onClick={() => dismissSkipUndoPrompt(true)}>Don't ask again</button>
          </div>
        </section>
      )}

      {activePage === "home" && (
        <>
          <section className="hero">
            <div className="hero-content">
              <p className="eyebrow">Independent artist support platform</p>
              <h1>Fans fund the artists they actually believe in.</h1>
              <p className="hero-sub">Direct artist-to-fan support, music, merch, lives and community without fake stream culture.</p>
              <div className="hero-actions">
                <button className="primary" onClick={() => goToPage("discover")}>Open Discovery</button>
                <button className="secondary" onClick={() => goToPage("music")}>Latest Music</button>
                {!currentUser && <button className="secondary" onClick={() => setAuthMode("register")}>Join</button>}
              </div>
            </div>

            <div className="hero-card">
              <h3>Your Monthly Support</h3>
              <div className="big-money">${fanTotal}</div>
              <p>{currentUser ? `${currentUser.username} currently supports artists directly.` : "Log in to track your direct artist support."}</p>
              <div className="split"><span>Artist keeps 90%</span><span>Platform 10%</span></div>
            </div>
          </section>

          <section className="feature-grid home-links">
            <button className="feature-card page-link" onClick={() => goToPage("discover")}>
              <p className="eyebrow">Discovery</p>
              <h3>Recommended Artists</h3>
              <p>Find artists ranked from your taste, location, saves, skips, follows and support.</p>
            </button>
            <button className="feature-card page-link" onClick={() => goToPage("music")}>
              <p className="eyebrow">Latest drops</p>
              <h3>Music</h3>
              <p>Browse new uploads and supporter-only tracks in a separate music page.</p>
            </button>
            <button className="feature-card page-link" onClick={() => goToPage("saved")}>
              <p className="eyebrow">Library</p>
              <h3>Saved Artists</h3>
              <p>Manage artists you want to revisit without sorting through the discovery feed.</p>
            </button>
          </section>
        </>
      )}

      {activePage === "discover" && (
        <>
          <section id="discover" className="section-head discovery-head">
            <div>
              <p className="eyebrow">Discovery</p>
              <h2>Recommended Artists</h2>
            </div>
            <p>{currentUser ? "Ranked from your genres, location, follows and support." : "Ranked by activity, identity and early community signals."}</p>
          </section>

          {filteredArtists.length === 0 ? (
            <div className="empty-state full-span">
              <h3>No artists to review.</h3>
              <p>
                {discoveryMeta.skipped_count > 0
                  ? "Your skipped artists are hidden. Reset skips or clear your search filters to bring recommendations back."
                  : searchLocation || searchQuery
                    ? "Try changing or clearing your search filters."
                    : "Register as an artist to create the first artist page."}
              </p>
              <div className="action-grid empty-actions">
                {(searchLocation || searchQuery) && (
                  <button className="secondary" onClick={() => { setSearchQuery(""); setSearchLocation(""); }}>
                    Clear Search
                  </button>
                )}
                <button className="secondary" onClick={showAllArtists}>
                  Show All Artists
                </button>
                {discoveryMeta.skipped_count > 0 && (
                  <button className="secondary" onClick={resetSkippedArtists}>
                    Reset Skipped Artists
                  </button>
                )}
              </div>
            </div>
          ) : renderReviewArtist()}
        </>
      )}

      {activePage === "saved" && (
        <>
          <section className="section-head saved-head">
            <div><p className="eyebrow">Library</p><h2>Saved Artists</h2></div>
            <p>{currentUser ? "Artists you marked to revisit." : "Log in to save and manage artists."}</p>
          </section>

          {currentUser && (
            <section className="saved-toolbar">
              <input
                value={savedSearchQuery}
                onChange={(event) => setSavedSearchQuery(event.target.value)}
                placeholder="Search saved artists"
                aria-label="Search saved artists"
              />
              <select
                value={savedGenreFilter}
                onChange={(event) => setSavedGenreFilter(event.target.value)}
                aria-label="Filter saved artists by genre"
              >
                <option value="">All genres</option>
                {savedGenres.map(genre => (
                  <option key={genre} value={genre}>{genre}</option>
                ))}
              </select>
            </section>
          )}

          <section className="saved-library">
            {!currentUser && (
              <div className="empty-state full-span">
                <h3>Log in to view saved artists.</h3>
                <p>Your saved artist library is tied to your fan account.</p>
              </div>
            )}
            {currentUser && savedArtists.length === 0 && (
              <div className="empty-state full-span">
                <h3>No saved artists yet.</h3>
                <p>Open Discovery and press Save on artists you want to revisit.</p>
                <button className="secondary" onClick={() => goToPage("discover")}>Open Discovery</button>
              </div>
            )}
            {currentUser && savedArtists.length > 0 && filteredSavedArtists.length === 0 && (
              <div className="empty-state full-span">
                <h3>No saved artists match those filters.</h3>
                <button className="secondary" onClick={() => { setSavedSearchQuery(""); setSavedGenreFilter(""); }}>Clear Filters</button>
              </div>
            )}
            {currentUser && filteredSavedArtists.map(renderSavedArtistRow)}
          </section>
        </>
      )}

      {activePage === "music" && (
        <>
          <section id="music" className="section-head"><div><p className="eyebrow">Latest drops</p><h2>Music</h2></div></section>

          <section className="music-grid">
            {music.length === 0 && (
              <div className="empty-state full-span">
                <h3>No music uploaded yet.</h3>
                <p>Artist accounts can upload their first track from their artist page.</p>
              </div>
            )}

            {music.map(track => (
              <article className="music-card" key={track.id}>
                {track.cover_art ? <img src={track.cover_art} alt={track.title} /> : <div className="cover-placeholder"></div>}
                <div>
                  {track.is_subscriber_only && (
                    <div className="post-badges"><span>Supporter only</span></div>
                  )}
                  <h3>{track.title}</h3>
                  <p className="muted">{track.artist_username} • {track.genre} • {track.bpm} BPM</p>
                  {track.audio_file ? (
                    <audio controls src={track.audio_file}></audio>
                  ) : track.is_subscriber_only && (
                    <p className="muted">{track.access_message || "Supporters only"}</p>
                  )}
                </div>
              </article>
            ))}
          </section>
        </>
      )}

      </main>
  );
}

createRoot(document.getElementById("root")).render(<App />);
