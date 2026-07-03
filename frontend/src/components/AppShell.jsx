import React, { useEffect } from "react";
import { PullToRefresh } from "./PullToRefresh.jsx";
import { AccountMenu } from "./AccountMenu.jsx";
import { IndieFundLogo } from "./IndieFundLogo.jsx";

function detectPlatformIos() {
  if (typeof navigator === "undefined") return false;
  return /iPad|iPhone|iPod/.test(navigator.userAgent)
    || (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1);
}

function NavButton({ item, compact, activePage, activeTab, activeShopTab, currentUser, previewAsFan, selectedArtist }) {
  const isOwnArtistPage = Boolean(
    selectedArtist &&
    currentUser?.username === selectedArtist.owner_username &&
    !previewAsFan
  );
  const studioTabs = item.activeTabs || (item.tab ? [item.tab] : []);
  const shopTabMatches = !item.shopTab || item.shopTab === activeShopTab;
  const studioActive = item.kind === "studio"
    && isOwnArtistPage
    && studioTabs.includes(activeTab)
    && shopTabMatches;
  const pageActive = item.kind === "page" && (
    activePage === item.page
    || (item.page === "home" && isOwnArtistPage && activeTab === "listen")
  );
  const active = Boolean(item.isActive || studioActive || pageActive);

  return (
    <button
      className={active ? "app-nav-item active" : "app-nav-item"}
      onClick={item.onClick}
      title={item.label}
      aria-current={active ? "page" : undefined}
      aria-pressed={item.kind === "action" ? active : undefined}
    >
      <span className="app-nav-icon" aria-hidden="true">
        {typeof item.icon === "string" ? item.icon : item.icon}
      </span>
      <span className="app-nav-copy">
        <span>{item.label}</span>
        {!compact && item.detail && <small>{item.detail}</small>}
      </span>
    </button>
  );
}

export function AccountActions({
  activePage,
  activeProfileTab = "settings",
  cartCount = 0,
  currentUser,
  unreadCount,
  onCart,
  onLogin,
  onNotifications,
  onOpenProfileTab,
}) {
  if (!currentUser) {
    if (activePage === "profile") return null;
    return <button className="secondary" onClick={onLogin}>Log In</button>;
  }

  return (
    <>
      {!currentUser.is_host && (
        <button className="icon-action" onClick={onCart} aria-label="Store cart">
          <svg className="icon-action-glyph" viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="9" cy="21" r="1" />
            <circle cx="20" cy="21" r="1" />
            <path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6" />
          </svg>
          {cartCount > 0 && <span>{cartCount}</span>}
        </button>
      )}
      <button className="icon-action" onClick={onNotifications} aria-label="Notifications">
        <svg className="icon-action-glyph" viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" />
          <path d="M13.73 21a2 2 0 0 1-3.46 0" />
        </svg>
        {unreadCount > 0 && <span>{unreadCount}</span>}
      </button>
      <AccountMenu
        activePage={activePage}
        activeProfileTab={activeProfileTab}
        currentUser={currentUser}
        onOpenProfileTab={onOpenProfileTab}
      />
    </>
  );
}

export function AppShell({
  activePage,
  activeTab,
  activeShopTab,
  accountActions,
  artistNav,
  children,
  currentUser,
  fanNav,
  guestNav = [],
  legalFooter = null,
  mobileNav,
  onRefresh,
  pageClass = "",
  playerActive = false,
  previewAsFan,
  pullRefreshDisabled = false,
  selectedArtist,
  onHome,
  showNavigation = true,
}) {
  const navProps = { activePage, activeTab, activeShopTab, currentUser, previewAsFan, selectedArtist };

  useEffect(() => {
    document.documentElement.classList.toggle("platform-ios", detectPlatformIos());
  }, []);

  return (
    <div className={`app-shell ${showNavigation ? "" : "app-shell--no-nav"} ${playerActive ? "has-player" : ""} ${pageClass}`.trim()}>
      {showNavigation && (
        <aside className="side-nav" aria-label="Primary navigation">
          <IndieFundLogo asButton className="side-brand" type="button" onClick={onHome} />

          {currentUser && (
            <div className="side-section">
              <p>{currentUser.is_artist ? "Browse" : currentUser.is_host ? "Host" : "Fan"}</p>
              {fanNav.map(item => (
                <NavButton key={item.id} item={item} {...navProps} />
              ))}
            </div>
          )}

          {!currentUser && (
            <div className="side-section">
              <p>Explore</p>
              {(guestNav || fanNav).map(item => (
                <NavButton key={item.id} item={item} {...navProps} />
              ))}
            </div>
          )}

          {artistNav.length > 0 && (
            <div className="side-section">
              <p>Artist Studio</p>
              {artistNav.map(item => (
                <NavButton key={item.id} item={item} {...navProps} />
              ))}
            </div>
          )}

          {currentUser && (
            <div className="side-account">
              <span>{currentUser.display_name || currentUser.username}</span>
              <small>{currentUser.is_artist ? "Artist + fan account" : currentUser.is_host ? "Host account" : "Fan account"}</small>
            </div>
          )}
        </aside>
      )}

      <div className="app-content">
        <PullToRefresh disabled={pullRefreshDisabled} onRefresh={onRefresh}>
          {children}
        </PullToRefresh>
        {legalFooter}
      </div>

      {showNavigation && (
        <nav className={`bottom-nav${mobileNav.length <= 5 ? " bottom-nav--compact" : ""}`} aria-label="Mobile navigation">
          <div className="bottom-nav-track">
            {mobileNav.map(item => (
              <NavButton key={item.id} item={item} compact {...navProps} />
            ))}
          </div>
        </nav>
      )}
    </div>
  );
}
