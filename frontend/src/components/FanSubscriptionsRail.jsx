import React, { useRef } from "react";

function ChannelAvatar({ label, imageUrl }) {
  const initial = label?.[0]?.toUpperCase() || "?";
  if (imageUrl) {
    return <img className="fan-subscription-avatar" src={imageUrl} alt="" />;
  }
  return <span className="fan-subscription-avatar fan-subscription-avatar-fallback" aria-hidden="true">{initial}</span>;
}

/**
 * Horizontal rail of artists the fan supports — pick a channel to open their profile/store.
 */
export function FanSubscriptionsRail({
  channels = [],
  activeUsername = "",
  compact = false,
  onSelectAll,
  onSelectArtist,
}) {
  const railRef = useRef(null);

  if (channels.length === 0) return null;

  return (
    <section
      className={`fan-subscriptions-rail-wrap${compact ? " fan-subscriptions-rail-wrap--compact" : ""}`}
      aria-label="Artists you support"
    >
      <div className="fan-subscriptions-rail-head">
        <p className="eyebrow">Your artists</p>
        {!compact && (
          <p className="muted fan-subscriptions-rail-hint">Tap a channel to filter this page</p>
        )}
      </div>
      <div className="fan-subscriptions-rail" ref={railRef} role="list">
        <button
          type="button"
          role="listitem"
          className={`fan-subscription-chip${!activeUsername ? " active" : ""}`}
          onClick={onSelectAll}
          aria-label="IndieFund home — all artists"
          aria-current={!activeUsername ? "true" : undefined}
        >
          <span className="fan-subscription-avatar fan-subscription-avatar-all" aria-hidden="true">IF</span>
          <span className="fan-subscription-label">All</span>
        </button>
        {channels.map(channel => {
          const isActive = activeUsername === channel.username;
          return (
            <button
              type="button"
              role="listitem"
              key={channel.username}
              className={`fan-subscription-chip${isActive ? " active" : ""}`}
              onClick={() => onSelectArtist(channel)}
              aria-label={`Open ${channel.stage_name}`}
              aria-current={isActive ? "true" : undefined}
            >
              <ChannelAvatar label={channel.stage_name} imageUrl={channel.hero_image} />
              <span className="fan-subscription-label">{channel.stage_name}</span>
            </button>
          );
        })}
      </div>
    </section>
  );
}
