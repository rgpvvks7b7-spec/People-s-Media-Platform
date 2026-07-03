import React from "react";

function FeedAvatar({ label, imageUrl }) {
  const initial = label?.[0]?.toUpperCase() || "?";
  if (imageUrl) {
    return <img className="feed-update-avatar" src={imageUrl} alt="" />;
  }
  return (
    <span className="feed-update-avatar feed-update-avatar-fallback" aria-hidden="true">
      {initial}
    </span>
  );
}

function formatFeedTimestamp(value) {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  const diffMs = Date.now() - date.getTime();
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
  if (diffHours < 1) return "Just now";
  if (diffHours < 24) return `${diffHours}h ago`;
  const diffDays = Math.floor(diffHours / 24);
  if (diffDays < 7) return `${diffDays}d ago`;
  return date.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

export function FanFeedUpdateCard({ item, onOpen, renderArtistName }) {
  const title = item.title?.trim();
  const body = item.body?.trim();

  return (
    <article className={`feed-update-card feed-update-card--${item.kind}`}>
      <button type="button" className="feed-update-card-button" onClick={() => onOpen(item)}>
        <header className="feed-update-card-head">
          <FeedAvatar label={item.stageName || item.artistUsername} imageUrl={item.heroImage} />
          <div className="feed-update-card-meta">
            <strong>{renderArtistName(item.artistUsername, { label: item.stageName })}</strong>
            <span className="feed-update-badge">{item.label}</span>
          </div>
          {item.createdAt && (
            <time className="feed-update-time" dateTime={item.createdAt}>
              {formatFeedTimestamp(item.createdAt)}
            </time>
          )}
        </header>

        <div className="feed-update-card-body">
          {title && <h3>{title}</h3>}
          {body && <p>{body}</p>}
          {!title && !body && (
            <p className="muted">New from {item.stageName || item.artistUsername}</p>
          )}
        </div>

        {item.imageUrl && (
          <div className="feed-update-media">
            <img src={item.imageUrl} alt="" loading="lazy" />
          </div>
        )}
      </button>
    </article>
  );
}
