import React from "react";

export function TrackNameLink({
  track,
  onOpenArtist,
  className = "track-name-link",
  stopPropagation = false,
  fallback = {},
}) {
  const title = track?.title || "Untitled";
  const username = track?.artist_username || track?.author_username;

  if (!username || !onOpenArtist) {
    return <span className={className}>{title}</span>;
  }

  return (
    <button
      type="button"
      className={className}
      onClick={(event) => {
        if (stopPropagation) event.stopPropagation();
        onOpenArtist?.(username, {
          ...fallback,
          stage_name: fallback.stage_name || track.stage_name || track.artist_stage_name,
        });
      }}
    >
      {title}
    </button>
  );
}
