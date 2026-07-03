import React, { useEffect, useRef, useState } from "react";

const DURATION_OPTIONS = [15, 30, 45];
const REEL_FADE_MS = 900;

/**
 * Hero banner: fans get a looping reel-style visual that crossfades to the cover photo.
 */
export function ArtistVisitorBanner({
  artistId,
  profession,
  bannerUrl,
  bannerDurationSeconds = 30,
  fallbackCoverImage,
  isOwner = false,
  isSaving = false,
  onSaveVisitorBanner,
}) {
  const videoRef = useRef(null);
  const fileInputRef = useRef(null);
  const [duration, setDuration] = useState(bannerDurationSeconds);
  const [reelPhase, setReelPhase] = useState("idle");

  useEffect(() => {
    setDuration(bannerDurationSeconds);
  }, [bannerDurationSeconds]);

  useEffect(() => {
    if (!bannerUrl) {
      setReelPhase("idle");
      return undefined;
    }

    if (isOwner) {
      setReelPhase("playing");
      return undefined;
    }

    setReelPhase("playing");
    const durationMs = Math.max(1, Number(bannerDurationSeconds) || 30) * 1000;
    const fadeTimer = window.setTimeout(() => setReelPhase("fading"), durationMs);

    return () => window.clearTimeout(fadeTimer);
  }, [artistId, profession, bannerUrl, bannerDurationSeconds, isOwner]);

  useEffect(() => {
    if (reelPhase !== "playing" || !videoRef.current) {
      return undefined;
    }

    const video = videoRef.current;
    const startPlayback = () => {
      video.currentTime = 0;
      const playPromise = video.play();
      if (playPromise?.catch) {
        playPromise.catch(() => setReelPhase("done"));
      }
    };

    if (video.readyState >= 2) {
      startPlayback();
    } else {
      video.addEventListener("loadeddata", startPlayback, { once: true });
      return () => video.removeEventListener("loadeddata", startPlayback);
    }

    return undefined;
  }, [reelPhase, bannerUrl]);

  useEffect(() => {
    if (reelPhase !== "fading") return undefined;
    const doneTimer = window.setTimeout(() => setReelPhase("done"), REEL_FADE_MS + 80);
    return () => window.clearTimeout(doneTimer);
  }, [reelPhase]);

  function handleVideoFadeEnd(event) {
    if (event.propertyName !== "opacity" || reelPhase !== "fading") return;
    setReelPhase("done");
  }

  function handleFileChange(event) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file || !onSaveVisitorBanner) return;
    onSaveVisitorBanner({ file, durationSeconds: duration });
  }

  function handleDurationChange(event) {
    const nextDuration = Number(event.target.value);
    setDuration(nextDuration);
    if (bannerUrl && onSaveVisitorBanner) {
      onSaveVisitorBanner({ durationSeconds: nextDuration });
    }
  }

  const showReelVideo = Boolean(
    bannerUrl && (isOwner || reelPhase === "playing" || reelPhase === "fading")
  );
  const bannerStyle = fallbackCoverImage
    ? { backgroundImage: `url(${fallbackCoverImage})` }
    : undefined;

  return (
    <div
      className={[
        "profile-banner",
        showReelVideo ? "profile-banner--video-active" : "",
        reelPhase === "fading" ? "profile-banner--reel-fading" : "",
        reelPhase === "done" ? "profile-banner--reel-done" : "",
        isOwner ? "profile-banner--owner" : "",
      ].filter(Boolean).join(" ")}
      style={bannerStyle}
    >
      {showReelVideo ? (
        <video
          ref={videoRef}
          className="profile-banner-video"
          src={bannerUrl}
          autoPlay
          muted
          playsInline
          loop
          preload="auto"
          disablePictureInPicture
          aria-label="Artist welcome visual"
          onTransitionEnd={handleVideoFadeEnd}
        />
      ) : null}

      {isOwner && (
        <div className="profile-banner-owner-panel">
          <input
            ref={fileInputRef}
            type="file"
            accept="video/mp4,video/quicktime,video/webm,.mp4,.mov,.webm"
            className="visually-hidden"
            onChange={handleFileChange}
          />

          {!bannerUrl ? (
            <>
              <p className="profile-banner-owner-label">Visitor welcome visual</p>
              <p className="profile-banner-owner-hint">Fans see a looping reel here when they open your page.</p>
              <button
                type="button"
                className="primary compact"
                disabled={isSaving}
                onClick={() => fileInputRef.current?.click()}
              >
                Upload visitor welcome visual
              </button>
              <label className="profile-banner-owner-duration">
                <span>Plays for</span>
                <select
                  value={String(duration)}
                  disabled={isSaving}
                  onChange={handleDurationChange}
                  aria-label="How long fans see the visual"
                >
                  {DURATION_OPTIONS.map(option => (
                    <option key={option} value={option}>{option} seconds</option>
                  ))}
                </select>
              </label>
            </>
          ) : (
            <>
              <p className="profile-banner-owner-label">Visitor welcome visual</p>
              <p className="profile-banner-owner-hint">
                Loops like a reel for {duration} seconds, then fades to your cover photo.
              </p>
              <div className="profile-banner-owner-actions">
                <label className="profile-banner-owner-duration">
                  <span>Duration</span>
                  <select
                    value={String(duration)}
                    disabled={isSaving}
                    onChange={handleDurationChange}
                    aria-label="How long fans see the visual"
                  >
                    {DURATION_OPTIONS.map(option => (
                      <option key={option} value={option}>{option}s</option>
                    ))}
                  </select>
                </label>
                <button
                  type="button"
                  className="secondary compact"
                  disabled={isSaving}
                  onClick={() => fileInputRef.current?.click()}
                >
                  Replace
                </button>
                <button
                  type="button"
                  className="secondary compact"
                  disabled={isSaving}
                  onClick={() => onSaveVisitorBanner?.({ clear: true })}
                >
                  Remove
                </button>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}
