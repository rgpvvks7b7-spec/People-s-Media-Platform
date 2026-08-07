import React from "react";
import { IndieFundLogo } from "./IndieFundLogo.jsx";

export function ArtistTopbar({ accountActions, backLabel = "Back to Listen", onBack }) {
  return (
    <nav className="topbar">
      <div className="topbar-brand-row">
        <IndieFundLogo className="logo" />
        <div className="auth-summary">
          {accountActions}
        </div>
      </div>
      <button className="back-button" onClick={onBack}>← {backLabel}</button>
    </nav>
  );
}

export function MainTopbar({
  accountActions,
  activePage,
  channelRail = null,
  currentUser,
  globalSearchResults,
  listenTab = "discover",
  onGlobalSearch,
  onLogin,
  onNavigate,
  onOpenSearchResult,
  searchLocation,
  searchQuery,
  setSearchLocation,
  setSearchQuery,
}) {
  const showDiscoveryFilters = activePage === "listen" && listenTab === "discover";

  return (
    <nav className="topbar">
      <div className="topbar-brand-row">
        <IndieFundLogo
          asButton
          className="logo logo-button"
          type="button"
          onClick={() => onNavigate(currentUser?.is_host ? "spaces" : "home")}
        />
        <div className="auth-summary">
          {accountActions || <button className="secondary" type="button" onClick={onLogin}>Log In</button>}
        </div>
      </div>
      {currentUser && (
        <div className="page-nav">
          {!currentUser.is_host && (
            <button type="button" className={activePage === "home" ? "nav-pill active" : "nav-pill"} onClick={() => onNavigate("home")}>Home</button>
          )}
          {!currentUser.is_artist && !currentUser.is_host && (
            <>
              <button type="button" className={activePage === "feed" ? "nav-pill active" : "nav-pill"} onClick={() => onNavigate("feed")}>Feed</button>
              <button type="button" className={activePage === "my-scene" ? "nav-pill active" : "nav-pill"} onClick={() => onNavigate("my-scene")}>Shows near me</button>
              <button type="button" className={activePage === "stores" ? "nav-pill active" : "nav-pill"} onClick={() => onNavigate("stores")}>Stores</button>
            </>
          )}
          {!currentUser.is_host && (
            <>
              <button type="button" className={activePage === "listen" ? "nav-pill active" : "nav-pill"} onClick={() => onNavigate("listen")}>Listen</button>
              <button type="button" className={activePage === "my-music" ? "nav-pill active" : "nav-pill"} onClick={() => onNavigate("my-music")}>My Playlists</button>
            </>
          )}
          {(currentUser.is_artist || currentUser.is_host) && (
            <button type="button" className={activePage === "spaces" ? "nav-pill active" : "nav-pill"} onClick={() => onNavigate("spaces")}>Spaces</button>
          )}
          <button type="button" className={activePage === "pricing" ? "nav-pill active" : "nav-pill"} onClick={() => onNavigate("pricing")}>Pricing</button>
          <button type="button" className={activePage === "faq" ? "nav-pill active" : "nav-pill"} onClick={() => onNavigate("faq")}>FAQ</button>
        </div>
      )}
      <div className="topbar-tools">
        <div className="top-search">
          <input
            value={searchQuery}
            onChange={(event) => {
              setSearchQuery(event.target.value);
              onGlobalSearch?.(event.target.value);
            }}
            placeholder="Search artists, tracks, posts"
            aria-label="Search artists, tracks, and posts"
          />
          {showDiscoveryFilters && (
            <input
              value={searchLocation}
              onChange={(event) => setSearchLocation(event.target.value)}
              placeholder="Any city"
              aria-label="Search location"
            />
          )}
        </div>
        {globalSearchResults && (globalSearchResults.artists?.length > 0 || globalSearchResults.tracks?.length > 0 || globalSearchResults.posts?.length > 0) && (
          <div className="global-search-results" role="listbox" aria-label="Search results">
            {globalSearchResults.artists?.map(artist => (
              <button type="button" key={`artist-${artist.id}`} className="global-search-item" onClick={() => onOpenSearchResult("artist", artist)}>
                Artist: {artist.stage_name || artist.username}
              </button>
            ))}
            {globalSearchResults.tracks?.map(track => (
              <button type="button" key={`track-${track.id}`} className="global-search-item" onClick={() => onOpenSearchResult("track", track)}>
                Track: {track.title}
              </button>
            ))}
            {globalSearchResults.posts?.map(post => (
              <button type="button" key={`post-${post.id}`} className="global-search-item" onClick={() => onOpenSearchResult("post", post)}>
                Post: {post.title || post.body?.slice(0, 40)}
              </button>
            ))}
          </div>
        )}
        {channelRail}
      </div>
    </nav>
  );
}
