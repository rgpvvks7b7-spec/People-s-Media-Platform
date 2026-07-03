import React from "react";
import { ArtistNameLink } from "./ArtistNameLink.jsx";
import { ArtistThemeSettings } from "./ArtistThemeSettings.jsx";
import { ProfileAccountNav } from "./ProfileAccountNav.jsx";
import { ProfileSettingsView } from "./ProfileSettingsView.jsx";

const NOTIFICATION_TYPE_LABELS = {
  post: "Post",
  music: "Music",
  store: "Store",
  live: "Live",
  comment: "Comment",
  supporter: "Supporter",
  gig: "Gig",
  purchase: "Purchase",
  promotion: "Promotion",
  system: "System",
};

function notificationBadgeLabel(item) {
  const label = NOTIFICATION_TYPE_LABELS[item.type] || "Update";
  return item.read ? label : `New ${label.toLowerCase()}`;
}

function renderNotificationTitle(item, onOpenArtist) {
  if (item.artistUsername && item.action && onOpenArtist) {
    return (
      <>
        <ArtistNameLink username={item.artistUsername} onOpenArtist={onOpenArtist} stopPropagation />
        {" "}{item.action}
      </>
    );
  }
  return item.headline || item.title;
}

function renderNotificationDetail(item, onOpenArtist) {
  if (item.detailArtistUsername && item.detailSuffix && onOpenArtist) {
    return (
      <>
        <ArtistNameLink username={item.detailArtistUsername} onOpenArtist={onOpenArtist} stopPropagation />
        {" "}{item.detailSuffix}
      </>
    );
  }
  return item.detail;
}

export function NotificationsPage({
  currentUser,
  notifications,
  notificationData,
  onClearAll,
  onClearNotification,
  onDiscover,
  onMarkRead,
  onOpenArtistByUsername,
  onOpenNotification,
}) {
  return (
    <>
      <section className="section-head">
        <div>
          <p className="eyebrow">Notifications</p>
          <h2>Updates</h2>
        </div>
        <div>
          <p>{currentUser?.is_artist ? "Supporter, comment and engagement updates for your hybrid account." : "New activity from saved and supported artists."}</p>
          {currentUser && notifications.length > 0 && (
            <div className="notification-actions">
              <button className="secondary compact" type="button" onClick={onClearAll}>
                Clear all
              </button>
              {notificationData.unread_count > 0 && (
                <button className="secondary compact" type="button" onClick={onMarkRead}>
                  Mark all read
                </button>
              )}
            </div>
          )}
        </div>
      </section>

      {!currentUser && (
        <div className="empty-state">
          <h3>Log in to view notifications.</h3>
          <p>Notifications are built from your saved artists, supported artists and account activity.</p>
        </div>
      )}

      {currentUser && notifications.length === 0 && (
        <div className="empty-state">
          <h3>No notifications yet.</h3>
          <p>Save artists, support artists, post content or comment to start building your activity stream.</p>
          <button className="secondary" onClick={onDiscover}>Open Listen</button>
        </div>
      )}

      {currentUser && notifications.length > 0 && (
        <section className="notification-list">
          {notifications.map(item => (
            <article
              className={`notification-row${item.read ? "" : " unread"}`}
              key={item.id}
            >
              <button
                type="button"
                className="notification-row-main"
                onClick={() => onOpenNotification?.(item)}
              >
                <span>{notificationBadgeLabel(item)}</span>
                <div>
                  <strong>{renderNotificationTitle(item, onOpenArtistByUsername)}</strong>
                  <p>{renderNotificationDetail(item, onOpenArtistByUsername)}</p>
                </div>
              </button>
              <button
                type="button"
                className="notification-row-clear"
                aria-label="Clear notification"
                onClick={() => onClearNotification?.(item)}
              >
                ×
              </button>
            </article>
          ))}
        </section>
      )}
    </>
  );
}

export function ProfilePage({
  askBeforeExternalSocial,
  authPanel,
  currentUser,
  fanTotal,
  hideSocialEmbeds,
  mailingList = null,
  onBetaFeedback,
  betaFeedbackSummary = null,
  onRefreshBetaSummary,
  onResolveBetaFeedback,
  onExportMailingList,
  onFanEmailSharingChange,
  onLogout,
  onUploadProfileMedia,
  onOpenPageSettings,
  onOpenThemeSettings,
  onOpenPublicPage,
  onOpenArtistByUsername,
  onProfileTabChange,
  profileTab = "settings",
  settingsSection = "library",
  onSettingsSectionChange,
  themeSettings = null,
  themePreview = null,
  onThemePreviewChange,
  onSaved,
  onSetAskBeforeExternalSocial,
  onSetGlobalEmailSharing,
  onSaveDiscoveryLocation,
  onSaveDiscoveryPreferences,
  onSetHideSocialEmbeds,
  fanEmailSharing = [],
  savedCount = 0,
  myTickets = [],
  myPurchases = [],
  mySubscriptions = [],
  onManageSupport,
  onOpenMyMusic,
  onOpenTicketShow,
  spaceHostProfile = null,
  onSaveHostProfile,
  studioSnapshot = null,
  supportedCount = 0,
  artistTrustStatus = null,
  onOpenTrustSettings,
  pushEnabled = false,
  pushSupported = false,
  onEnablePush,
  onDisablePush,
  promotionWallet = null,
}) {
  const accountLabel = currentUser?.is_artist
    ? "artist + fan"
    : currentUser?.is_host
      ? "host"
      : "fan";

  return (
    <>
      <section className="section-head section-head--profile">
        <div className="section-head-main">
          <p className="eyebrow">Account</p>
          <h2>
            {currentUser
              ? (currentUser.is_artist || currentUser.is_host ? "Profile & settings" : "Profile")
              : "Log in or create account"}
          </h2>
          <p>
            {currentUser?.is_artist
              ? "Your account, page settings, and fan activity in one place."
              : currentUser?.is_host
                ? "Manage your venue contact details and account preferences."
                : "Manage your fan account and direct artist support."}
          </p>
        </div>
        {currentUser && onProfileTabChange && (
          <ProfileAccountNav
            activeTab={profileTab}
            showThemes={Boolean(currentUser)}
            onChange={onProfileTabChange}
          />
        )}
      </section>

      {!currentUser && authPanel}

      {currentUser && (
        <section className="profile-dashboard fan-profile-shell">
          {profileTab === "profile" && (
            <div className="feature-card profile-identity-card profile-identity-card--full">
              <div
                className="profile-cover"
                style={currentUser.cover_image ? { backgroundImage: `url(${currentUser.cover_image})` } : undefined}
              >
                {onUploadProfileMedia && (
                  <label className="profile-cover-upload">
                    {currentUser.cover_image ? "Change cover" : "Add cover photo"}
                    <input
                      type="file"
                      accept="image/*"
                      hidden
                      onChange={event => {
                        const file = event.target.files?.[0];
                        event.target.value = "";
                        onUploadProfileMedia("cover_image", file);
                      }}
                    />
                  </label>
                )}
              </div>
              <div className="profile-identity-body">
                <div className="profile-identity-avatar">
                  {currentUser.avatar ? (
                    <img src={currentUser.avatar} alt={currentUser.display_name || currentUser.username} />
                  ) : (
                    <span>{(currentUser.display_name || currentUser.username)?.[0]?.toUpperCase()}</span>
                  )}
                  {onUploadProfileMedia && (
                    <label className="profile-avatar-upload" aria-label="Upload profile photo">
                      +
                      <input
                        type="file"
                        accept="image/*"
                        hidden
                        onChange={event => {
                          const file = event.target.files?.[0];
                          event.target.value = "";
                          onUploadProfileMedia("avatar", file);
                        }}
                      />
                    </label>
                  )}
                </div>
                <div className="profile-identity-meta">
                  <p className="eyebrow">Signed in</p>
                  <h3>{currentUser.display_name || currentUser.username}</h3>
                  <p>{currentUser.username} • {accountLabel}</p>
                  <button className="secondary compact" onClick={onLogout}>Log Out</button>
                </div>
              </div>
            </div>
          )}

          {profileTab === "profile" && currentUser.is_artist && artistTrustStatus && !artistTrustStatus.profile_completion?.complete && (
            <div className="feature-card profile-trust-card">
              <p className="eyebrow">Profile trust</p>
              <h3>
                {artistTrustStatus.profile_completion.completed_count}/{artistTrustStatus.profile_completion.required_count} complete
              </h3>
              <p className="muted">
                {artistTrustStatus.upload_limit_message || "Complete these items so fans and venues trust your page."}
              </p>
              <div className="beta-task-list">
                {(artistTrustStatus.profile_completion.missing || []).map(item => (
                  <span key={item.key}>{item.label}</span>
                ))}
              </div>
              <button className="secondary compact" type="button" onClick={onOpenTrustSettings}>Open page settings</button>
            </div>
          )}

          {profileTab === "profile" && currentUser.is_artist && studioSnapshot && (
            <>
              <div className="feature-card profile-page-card">
                <p className="eyebrow">Your public page</p>
                <h3>
                  {onOpenArtistByUsername ? (
                    <ArtistNameLink
                      username={studioSnapshot.artist.owner_username || currentUser.username}
                      label={studioSnapshot.artist.stage_name}
                      onOpenArtist={onOpenArtistByUsername}
                      className="artist-name-link click-title"
                    />
                  ) : studioSnapshot.artist.stage_name}
                </h3>
                <p className="muted">
                  {studioSnapshot.supporterCount} supporters • ${studioSnapshot.earnings}/mo revenue • ${studioSnapshot.tipTotal} in tips
                </p>
                <div className="action-grid">
                  <button className="primary compact" onClick={onOpenPublicPage}>View public page</button>
                  <button className="secondary compact" onClick={onOpenPageSettings}>Page settings</button>
                  {onOpenThemeSettings && (
                    <button className="secondary compact" type="button" onClick={onOpenThemeSettings}>Themes</button>
                  )}
                </div>
                <p className="muted profile-page-note">
                  Public page theme is what fans see on your link. Studio theme is only visible to you while editing.
                </p>
              </div>

              <div className="feature-card">
                <p className="eyebrow">Published</p>
                <h3>{studioSnapshot.tracks.length + studioSnapshot.posts.length + studioSnapshot.products.length}</h3>
                <p>
                  {studioSnapshot.tracks.length} tracks, {studioSnapshot.posts.length} posts, {studioSnapshot.products.length} store items on your {studioSnapshot.professionLabel.toLowerCase()} page.
                </p>
              </div>

              <div className="feature-card">
                <p className="eyebrow">Mailing list</p>
                <h3>{mailingList?.count || 0} contacts</h3>
                <p>+{mailingList?.added_this_month || 0} this month from opted-in supporters.</p>
                {mailingList?.can_export ? (
                  <button className="secondary compact" onClick={onExportMailingList}>Export CSV</button>
                ) : (
                  <p className="muted">Artist Pro unlocks CSV export.</p>
                )}
              </div>
            </>
          )}

          {profileTab === "profile" && !currentUser.is_artist && !currentUser.is_host && (
            <div className="feature-card">
              <p className="eyebrow">Your profile</p>
              <h3>{currentUser.display_name || currentUser.username}</h3>
              <p className="muted">
                Update your photo and cover above. Tickets, library, and preferences live under Settings. Colours live under Themes.
              </p>
              {currentUser.favorite_genres && (
                <p><strong>Genres:</strong> {currentUser.favorite_genres}</p>
              )}
              {currentUser.discovery_location && (
                <p><strong>City:</strong> {currentUser.discovery_location}</p>
              )}
            </div>
          )}

          {profileTab === "settings" && onSettingsSectionChange && (
            <ProfileSettingsView
              activeSection={settingsSection}
              askBeforeExternalSocial={askBeforeExternalSocial}
              betaFeedbackSummary={betaFeedbackSummary}
              currentUser={currentUser}
              fanEmailSharing={fanEmailSharing}
              fanTotal={fanTotal}
              hideSocialEmbeds={hideSocialEmbeds}
              myPurchases={myPurchases}
              mySubscriptions={mySubscriptions}
              myTickets={myTickets}
              onBetaFeedback={onBetaFeedback}
              onFanEmailSharingChange={onFanEmailSharingChange}
              onManageSupport={onManageSupport}
              onOpenArtistByUsername={onOpenArtistByUsername}
              onOpenMyMusic={onOpenMyMusic}
              onOpenTicketShow={onOpenTicketShow}
              onRefreshBetaSummary={onRefreshBetaSummary}
              onResolveBetaFeedback={onResolveBetaFeedback}
              onSaveDiscoveryLocation={onSaveDiscoveryLocation}
              onSaveDiscoveryPreferences={onSaveDiscoveryPreferences}
              onSaved={onSaved}
              onSaveHostProfile={onSaveHostProfile}
              onSectionChange={onSettingsSectionChange}
              onSetAskBeforeExternalSocial={onSetAskBeforeExternalSocial}
              onSetGlobalEmailSharing={onSetGlobalEmailSharing}
              onSetHideSocialEmbeds={onSetHideSocialEmbeds}
              promotionWallet={promotionWallet}
              pushEnabled={pushEnabled}
              pushSupported={pushSupported}
              onEnablePush={onEnablePush}
              onDisablePush={onDisablePush}
              savedCount={savedCount}
              spaceHostProfile={spaceHostProfile}
              supportedCount={supportedCount}
            />
          )}

          {profileTab === "themes" && themeSettings && (
            <ArtistThemeSettings
              key={`${themeSettings.variant}-${themeSettings.themeName}-${themeSettings.studioThemeName || ""}`}
              activePreviewTarget={themePreview?.target || null}
              variant={themeSettings.variant || "artist"}
              themeName={themeSettings.themeName}
              studioThemeName={themeSettings.studioThemeName}
              onPreviewChange={onThemePreviewChange}
              onSave={themeSettings.onSave}
            />
          )}
        </section>
      )}
    </>
  );
}
