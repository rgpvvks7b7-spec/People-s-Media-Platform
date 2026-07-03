import React from "react";

export function ArtistNameLink({
  username,
  label,
  artist,
  onOpenArtist,
  className = "artist-name-link",
  verified = false,
  stopPropagation = false,
  fallback = {},
  knownOnly = false,
}) {
  const display = label || artist?.stage_name || username;
  if (!username) {
    return <span className={className}>{display}{verified ? " ✅" : ""}</span>;
  }

  if (knownOnly && !artist) {
    return <span className={className}>{display}{verified ? " ✅" : ""}</span>;
  }

  return (
    <button
      type="button"
      className={className}
      onClick={(event) => {
        if (stopPropagation) event.stopPropagation();
        onOpenArtist?.(username, {
          ...fallback,
          ...(artist || {}),
          owner_username: username,
          stage_name: label || artist?.stage_name || username,
        });
      }}
    >
      {display}{verified ? " ✅" : ""}
    </button>
  );
}
