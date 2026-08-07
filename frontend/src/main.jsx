import React, { useCallback, useEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import { ArtistNameLink } from "./components/ArtistNameLink.jsx";
import { TrackNameLink } from "./components/TrackNameLink.jsx";
import { NotificationsPage, ProfilePage } from "./components/AccountPages.jsx";
import { PromotePage } from "./components/PromotePage.jsx";
import { AdsManagerPage } from "./components/AdsManagerPage.jsx";
import { FanCrmPage } from "./components/FanCrmPage.jsx";
import { AccountActions, AppShell } from "./components/AppShell.jsx";
import { AuthPanel } from "./components/AuthPanel.jsx";
import { IndieFundLogo } from "./components/IndieFundLogo.jsx";
import { FanStoresPage } from "./components/FanStoresPage.jsx";
import { FanSubscriptionsRail } from "./components/FanSubscriptionsRail.jsx";
import { FanFeedUpdateCard } from "./components/FanFeedUpdateCard.jsx";
import { ArtistThemeSettings } from "./components/ArtistThemeSettings.jsx";
import { ArtistVisitorBanner } from "./components/ArtistVisitorBanner.jsx";
import { LiveTab } from "./components/LiveTab.jsx";
import { MyScenePage } from "./components/MyScene.jsx";
import { TicketStubIconButton, TicketStubNavIcon, TicketStubSheet } from "./components/TicketStubSheet.jsx";
import { CalendarItemDateFields } from "./components/CalendarItemDateFields.jsx";
import { SpaceBookingDateFields } from "./components/SpaceBookingDateFields.jsx";
import {
  SpaceAvailabilityEditor,
  formatAvailabilityWindows,
  rowsToWindows,
  windowsToRows,
} from "./components/SpaceAvailabilityEditor.jsx";
import { SpaceListingAvailabilityPicker, slotsToWindows } from "./components/SpaceListingAvailabilityPicker.jsx";
import { SpaceListingCardPreview, SpaceListingDetailModal } from "./components/SpaceListingDetailModal.jsx";
import { ExternalLinkConfirm, PlaylistPickerSheet, PreviewBeforeShareSheet, ProductTypePicker, SupportConfirmSheet } from "./components/Modals.jsx";
import { StoreCart } from "./components/StoreCart.jsx";
import { FinalizeReleasePanel } from "./components/FinalizeReleasePanel.jsx";
import { SpaceListingWizard } from "./components/SpaceListingWizard.jsx";
import { ArtistTopbar, MainTopbar } from "./components/Topbar.jsx";
import { LegalFooter, LegalPageView } from "./components/LegalPages.jsx";
import { GrowthNextAction, SetupChecklistPanel } from "./components/SetupChecklistPanel.jsx";
import { PrelaunchFanGate } from "./components/PrelaunchFanGate.jsx";
import { CreatorEarlyAccessLanding } from "./components/CreatorEarlyAccessLanding.jsx";
import {
  canAccessFanExperience,
  fanRegistrationOpen,
  isFanGatedPage,
  isPrelaunchMode,
  normalizePlatformMode,
  PLATFORM_MODE_LIVE,
  resolvePageForPlatformMode,
} from "./lib/platformMode.js";
import {
  dismissSetup,
  getChecklistProgress,
  getFirstIncompleteChallenge,
  hasPreviewedPublicPage,
  hasSharedInviteLink,
  isSetupDismissed,
  markInviteLinkShared,
  markPreviewedPublicPage,
} from "./lib/setupChecklist.js";
import { SUPPORT_TIER_TEMPLATES } from "./lib/supportTierTemplates.js";
import { IubendaConsent } from "./components/IubendaConsent.jsx";
import { CookieConsentFallback } from "./components/CookieConsentFallback.jsx";
import { isIubendaConsentConfigured } from "./lib/iubenda.js";
import { getLegalPage, LEGAL_PAGE_IDS } from "./legal/index.js";
import { fetchArtistMeta, updateArtistPageMeta, updateLegalPageMeta } from "./lib/seo.js";
import { resolveArtistThemeName, resolvePersonalAppTheme, normalizeThemeId, normalizeHostThemeId, DEFAULT_THEME } from "./lib/themes.js";
import { resolveSettingsSection } from "./lib/profileSettings.js";
import { buildProductPageUrl, readArtistDeepLinkParams } from "./lib/productLinks.js";
import { getStructuredWindows, validateBookingWindow } from "./lib/spaceAvailability.js";
import "./styles/app.css";

function resolveApiBase() {
  const configured = (import.meta.env.VITE_API_URL || "/api").replace(/\/$/, "");
  if (configured.startsWith("/")) return configured;
  if (import.meta.env.DEV && typeof window !== "undefined") return "/api";
  return configured;
}

const API = resolveApiBase();
const FAN_PAGES = new Set(["home", "feed", "listen", "discover", "music", "my-music", "my-scene", "stores", "spaces", "notifications", "profile", "promote", "ads-manager", "faq", "prelaunch"]);
const FAN_ARTIST_RAIL_PAGES = new Set(["home", "feed", "my-scene", "listen", "my-music", "stores"]);
const HOST_PAGES = new Set(["spaces", "notifications", "profile", "faq"]);
const GUEST_SHELL_PAGES = new Set(["listen", "discover", "music", "profile", "spaces", "my-scene", "stores", "faq", "prelaunch", "early-access", ...LEGAL_PAGE_IDS]);
const SUPPORT_EMAIL = "support@indiefund.app";

function resolveListenRoute(page, tabParam = "", viewParam = "") {
  if (page === "saved") {
    return { page: "listen", listenTab: "discover", discoverView: "saved" };
  }
  if (page === "discover") {
    return {
      page: "listen",
      listenTab: "discover",
      discoverView: viewParam === "saved" ? "saved" : "recommendations",
    };
  }
  if (page === "music") {
    return { page: "listen", listenTab: "latest", discoverView: "recommendations" };
  }
  if (page === "listen") {
    const listenTab = tabParam === "latest" ? "latest" : "discover";
    return {
      page: "listen",
      listenTab,
      discoverView: listenTab === "discover" && viewParam === "saved" ? "saved" : "recommendations",
    };
  }
  return null;
}

function isListenDiscoverBrowse(activePage, listenTab, discoverView) {
  return activePage === "listen" && listenTab === "discover" && discoverView !== "saved";
}

function resolveProfileTab(tabParam = "") {
  if (tabParam === "themes") return "themes";
  if (tabParam === "profile") return "profile";
  if (tabParam === "settings" || tabParam === "account") return "settings";
  return "settings";
}

function resolveStoresRoute(page, tabParam = "") {
  if (page !== "stores") return null;
  return {
    page: "stores",
    storeTab: tabParam === "music-store" ? "music-store" : "merch",
  };
}

function resolveGuestPage(page, tabParam = "", viewParam = "") {
  const listenRoute = resolveListenRoute(page, tabParam, viewParam);
  if (listenRoute) return listenRoute.page;
  if (page && (GUEST_SHELL_PAGES.has(page) || LEGAL_PAGE_IDS.has(page))) return page;
  return "home";
}

function resolveAccountPage(page, user, tabParam = "", viewParam = "") {
  if (page && LEGAL_PAGE_IDS.has(page)) return page;
  if (page === "radio") return "my-music";
  const listenRoute = resolveListenRoute(page, tabParam, viewParam);
  if (listenRoute) return listenRoute.page;
  const resolved = page;
  if (user?.is_host) {
    if (!resolved || resolved === "home" || !HOST_PAGES.has(resolved)) return "spaces";
    return resolved;
  }
  if (!resolved) return "home";
  if (user && !user.is_artist && resolved === "spaces") return "my-scene";
  return resolved;
}
const CART_STORAGE_KEY = "indiefund_store_cart";
const DEFAULT_PROFESSION = "music";

const SPACE_PHOTO_TYPE_LABELS = {
  stage: "Stage / band setup",
  audience: "Audience area",
  room_overview: "Room overview",
  load_in: "Load-in / access",
  other: "Other",
};

const SPACE_SPLIT_LABELS = {
  door_percent: "Door split",
  flat_fee: "Flat fee",
  fb_only: "F&B focused",
};

function gigsForListing(gigs, listing) {
  const venueKey = (listing.name || "").trim().toLowerCase();
  const cityKey = (listing.city || "").trim().toLowerCase();
  return (gigs || []).filter(gig => {
    const gigVenue = (gig.venue_name || "").trim().toLowerCase();
    const gigCity = (gig.venue_city || "").trim().toLowerCase();
    return gigVenue === venueKey && (!cityKey || gigCity === cityKey);
  });
}

const PROFESSION_LABELS = {
  music: "Music",
  visual_art: "Painting / Drawing",
  digital_art: "Digital Art",
  craft: "Crafts",
  writing: "Writing",
  performance: "Performance",
  comedy: "Comedian",
  podcast: "Podcaster",
  film: "Filmmaker / Video",
  other: "Other",
};
const MUSIC_BRANCH_PROFESSIONS = new Set(["music", "comedy", "podcast", "film", "performance"]);
const MUSIC_PRODUCT_TYPES = ["digital_download", "vinyl", "cassette", "beat"];

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

async function fetchJson(path, fallback = null) {
  try {
    const res = await apiFetch(path);
    if (!res.ok) return fallback;
    return await res.json();
  } catch {
    return fallback;
  }
}

function formatTime(seconds) {
  if (isNaN(seconds) || seconds === Infinity) return "0:00";
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}:${secs < 10 ? "0" : ""}${secs}`;
}

function ProtectionBadges({ protection }) {
  if (!protection?.labels?.length) return null;
  return (
    <div className="post-badges protection-badges">
      {protection.labels.map(label => <span key={label}>{label}</span>)}
    </div>
  );
}

function ProtectedWorkNotice({ protection }) {
  if (!protection?.notice) return null;
  return <p className="protected-work-notice">{protection.notice}</p>;
}

function ProductDownloadButton({ product }) {
  if (!product.product_file || !product.can_download) return null;
  return (
    <a className="secondary compact product-download-link" href={product.product_file} download>
      Download
    </a>
  );
}

function GlobalPlayer({
  track,
  isPlaying,
  onClose,
  onEnded,
  onTogglePlay,
  onPlaybackEvent,
  onNext,
  onPrevious,
  onOpenArtistByUsername,
  audioRef,
  queueLabel = "",
  queuePosition = 0,
  queueTotal = 0,
}) {
  const [progress, setProgress] = useState(0);
  const [duration, setDuration] = useState(0);
  const [currentTime, setCurrentTime] = useState(0);
  const [volume, setVolume] = useState(() => {
    const saved = localStorage.getItem("playerVolume");
    return saved !== null ? parseFloat(saved) : 1;
  });
  const loggedPlaybackEventsRef = useRef({ preview: false, full: false, trackKey: "" });

  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;
    const trackKey = `${track?.is_product ? "product" : "track"}-${track?.id || ""}`;
    if (loggedPlaybackEventsRef.current.trackKey !== trackKey) {
      loggedPlaybackEventsRef.current = { preview: false, full: false, trackKey };
    }

    const updateProgress = () => {
      if (!isNaN(audio.duration)) {
        setCurrentTime(audio.currentTime);
        setProgress((audio.currentTime / audio.duration) * 100);
        if (!track?.is_product && track?.id && onPlaybackEvent) {
          if (!loggedPlaybackEventsRef.current.preview && audio.currentTime >= 1) {
            loggedPlaybackEventsRef.current.preview = true;
            onPlaybackEvent(track, "music_preview", Math.floor(audio.currentTime));
          }
          if (
            !loggedPlaybackEventsRef.current.full &&
            !track.is_preview_playback &&
            audio.duration > 0 &&
            audio.currentTime / audio.duration >= 0.8
          ) {
            loggedPlaybackEventsRef.current.full = true;
            onPlaybackEvent(track, "music_full_play", Math.floor(audio.currentTime));
          }
        }
        if (track?.is_preview_playback && track.preview_limit_seconds && audio.currentTime >= track.preview_limit_seconds) {
          audio.pause();
          audio.currentTime = track.preview_limit_seconds;
          onTogglePlay(false);
        }
      }
    };

    const updateDuration = () => setDuration(audio.duration);

    audio.addEventListener("timeupdate", updateProgress);
    audio.addEventListener("loadedmetadata", updateDuration);
    audio.addEventListener("ended", onEnded);

    return () => {
      audio.removeEventListener("timeupdate", updateProgress);
      audio.removeEventListener("loadedmetadata", updateDuration);
      audio.removeEventListener("ended", onEnded);
    };
  }, [track?.id, track?.is_product, onEnded, onPlaybackEvent]);

  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;

    if (isPlaying) {
      audio.play().catch(() => onTogglePlay(false));
    } else {
      audio.pause();
    }
  }, [isPlaying, track?.id]);

  useEffect(() => {
    if (audioRef.current) {
      audioRef.current.volume = volume;
    }
  }, [volume]);

  if (!track) return null;

  const artistUsername = track.artist_username || track.author_username;
  const openTrackArtist = () => {
    if (artistUsername && onOpenArtistByUsername) {
      onOpenArtistByUsername(artistUsername, {
        stage_name: track.stage_name || track.artist_stage_name,
      });
    }
  };

  const handleProgressChange = (e) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const pct = Math.max(0, Math.min(1, x / rect.width));
    if (audioRef.current && !isNaN(audioRef.current.duration)) {
      audioRef.current.currentTime = pct * audioRef.current.duration;
    }
  };

  const handleVolumeChange = (e) => {
    const v = parseFloat(e.target.value);
    setVolume(v);
    localStorage.setItem("playerVolume", v);
  };

  return (
    <div className="player-bar">
      <div className="player-track-info">
        <button
          type="button"
          className="player-cover-btn"
          onClick={openTrackArtist}
          disabled={!artistUsername}
          aria-label={artistUsername ? `Open ${track.title} artist page` : track.title}
        >
          {track.cover_art ? (
            <img className="player-cover" src={track.cover_art} alt={track.title} />
          ) : (
            <div className="player-cover"></div>
          )}
        </button>
        <div className="player-track-details">
          <TrackNameLink
            track={track}
            onOpenArtist={onOpenArtistByUsername}
            className="track-name-link player-track-title"
          />
          <p>
            {track.is_preview_playback ? "Preview - subscribe to unlock full track" : (
              (track.artist_username || track.author_username) ? (
                <ArtistNameLink
                  username={track.artist_username || track.author_username}
                  onOpenArtist={onOpenArtistByUsername}
                />
              ) : "Artist"
            )}
          </p>
          {queueTotal > 1 && (
            <p className="player-queue-meta">
              {queueLabel ? `${queueLabel} · ` : ""}{queuePosition}/{queueTotal}
            </p>
          )}
        </div>
      </div>

      <div className="player-controls">
        <div className="player-buttons">
          {queueTotal > 1 && (
            <button className="player-nav-btn" onClick={onPrevious} aria-label="Previous track">
              ‹
            </button>
          )}
          <button className="play-pause-btn" onClick={() => onTogglePlay(!isPlaying)}>
            {isPlaying ? "Ⅱ" : "▶"}
          </button>
          {queueTotal > 1 && (
            <button className="player-nav-btn" onClick={onNext} aria-label="Next track">
              ›
            </button>
          )}
        </div>
        <div className="player-progress-container">
          <span className="player-time">{formatTime(currentTime)}</span>
          <div className="player-progress-bar" onClick={handleProgressChange}>
            <div className="player-progress-fill" style={{ width: `${progress}%` }}></div>
          </div>
          <span className="player-time">{formatTime(duration)}</span>
        </div>
      </div>

      <div className="player-volume">
        <span className="player-time">VOL</span>
        <input
          type="range"
          min="0"
          max="1"
          step="0.01"
          value={volume}
          onChange={handleVolumeChange}
          className="volume-slider"
        />
      </div>

      <button
        type="button"
        className="player-close-btn"
        onClick={onClose}
        aria-label="Close player"
        title="Close player"
      >
        ×
      </button>

      <audio ref={audioRef} src={track.audio_file} />
    </div>
  );
}

function App() {
  const [activePage, setActivePage] = useState("home");
  const [listenTab, setListenTab] = useState("discover");
  const [storeTab, setStoreTab] = useState("merch");
  const [profileTab, setProfileTab] = useState("settings");
  const [settingsSection, setSettingsSection] = useState("library");
  const [themePreview, setThemePreview] = useState(null);
  const [fanChannelUsername, setFanChannelUsername] = useState("");
  const [discoverView, setDiscoverView] = useState("recommendations");
  const [discoveryMode, setDiscoveryMode] = useState(
    () => window.localStorage.getItem("indiefundDiscoveryMode") || "artists"
  );
  const [currentTrack, setCurrentTrack] = useState(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [playbackQueue, setPlaybackQueue] = useState([]);
  const [playbackIndex, setPlaybackIndex] = useState(0);
  const [playbackSource, setPlaybackSource] = useState(null);
  const audioRef = useRef(null);

  function handleTogglePlay(trackOrState) {
    if (typeof trackOrState === "boolean") {
      setIsPlaying(trackOrState);
      return;
    }

    const track = trackOrState;
    const isDifferent = track && (
      currentTrack?.id !== track.id ||
      !!currentTrack?.is_product !== !!track.is_product
    );

    if (isDifferent) {
      setPlaybackQueue([]);
      setPlaybackIndex(0);
      setPlaybackSource(null);
      setCurrentTrack(track);
      setIsPlaying(true);
    } else {
      setIsPlaying(!isPlaying);
    }
  }

  function playQueue(tracks, startIndex = 0, sourceLabel = "Playlist") {
    const playableTracks = tracks.filter(track => track.audio_file);
    if (playableTracks.length === 0) {
      setMessage("No playable tracks in this queue.");
      return;
    }

    const safeIndex = Math.max(0, Math.min(startIndex, playableTracks.length - 1));
    setPlaybackQueue(playableTracks);
    setPlaybackIndex(safeIndex);
    setPlaybackSource({ label: sourceLabel, loop: true });
    setCurrentTrack(playableTracks[safeIndex]);
    setIsPlaying(true);
  }

  function playQueueAtIndex(index) {
    if (!playbackQueue.length) return;

    const safeIndex = Math.max(0, Math.min(index, playbackQueue.length - 1));
    setPlaybackIndex(safeIndex);
    setCurrentTrack(playbackQueue[safeIndex]);
    setIsPlaying(true);
  }

  function playNextTrack() {
    if (!playbackQueue.length) return;

    if (playbackIndex < playbackQueue.length - 1) {
      playQueueAtIndex(playbackIndex + 1);
      return;
    }

    if (playbackSource?.loop) {
      playQueueAtIndex(0);
    }
  }

  function playPreviousTrack() {
    if (!playbackQueue.length) return;

    if (playbackIndex > 0) {
      playQueueAtIndex(playbackIndex - 1);
      return;
    }

    if (playbackSource?.loop) {
      playQueueAtIndex(playbackQueue.length - 1);
    }
  }

  function handlePlayerEnded() {
    if (playbackQueue.length) {
      if (playbackIndex < playbackQueue.length - 1) {
        playQueueAtIndex(playbackIndex + 1);
        return;
      }

      if (playbackSource?.loop) {
        playQueueAtIndex(0);
        return;
      }
    }

    setIsPlaying(false);
  }

  function handleClosePlayer() {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.currentTime = 0;
    }
    setIsPlaying(false);
    setCurrentTrack(null);
    setPlaybackQueue([]);
    setPlaybackIndex(0);
    setPlaybackSource(null);
  }

  const [artists, setArtists] = useState([]);
  const [discoveryArtists, setDiscoveryArtists] = useState([]);
  const [discoveryTracks, setDiscoveryTracks] = useState([]);
  const [discoveryMeta, setDiscoveryMeta] = useState({ skipped_count: 0, count: 0, exhausted: false });
  const [discoveryTrackMeta, setDiscoveryTrackMeta] = useState({ skipped_count: 0, count: 0, exhausted: false });
  const [savedArtists, setSavedArtists] = useState([]);
  const [music, setMusic] = useState([]);
  const [fanPlaylists, setFanPlaylists] = useState([]);
  const [selectedPlaylistId, setSelectedPlaylistId] = useState("");
  const [myMusicSidebarView, setMyMusicSidebarView] = useState("artists");
  const [myMusicListenMoreOpen, setMyMusicListenMoreOpen] = useState({});
  const [playlistPickerTrack, setPlaylistPickerTrack] = useState(null);
  const [artworks, setArtworks] = useState([]);
  const [songCovers, setSongCovers] = useState([]);
  const [posts, setPosts] = useState([]);
  const [povs, setPovs] = useState([]);
  const [instants, setInstants] = useState([]);
  const [products, setProducts] = useState([]);
  const [commissionRequests, setCommissionRequests] = useState([]);
  const [storeFormType, setStoreFormType] = useState(null);
  const [showStoreTypePicker, setShowStoreTypePicker] = useState(false);
  const [showPostForm, setShowPostForm] = useState(false);
  const [showPovForm, setShowPovForm] = useState(false);
  const [showInstantForm, setShowInstantForm] = useState(false);
  const [showMusicForm, setShowMusicForm] = useState(false);
  const [pendingRelease, setPendingRelease] = useState(null);
  const [showSongCoverForm, setShowSongCoverForm] = useState(false);
  const [trackCoverMode, setTrackCoverMode] = useState("upload");
  const [selectedLibraryCoverId, setSelectedLibraryCoverId] = useState("");
  const [saveCoverToLibrary, setSaveCoverToLibrary] = useState(true);
  const [aiDisclosureLevel, setAiDisclosureLevel] = useState("human_made");
  const [showArtworkForm, setShowArtworkForm] = useState(false);
  const [showCommissionForm, setShowCommissionForm] = useState(false);
  const [showLiveForm, setShowLiveForm] = useState(false);
  const [showCalendarForm, setShowCalendarForm] = useState(false);
  const calendarDateValuesRef = useRef({ starts_at: "", ends_at: "", hasStartDate: false, hasEndDate: false });
  const spaceBookingDateValuesRef = useRef({ starts_at: "", ends_at: "", hasStartDate: false, hasEndDate: false });
  const spaceBookingPanelRef = useRef(null);
  const [cameraDevices, setCameraDevices] = useState([]);
  const [selectedCameraId, setSelectedCameraId] = useState("");
  const [cameraStatus, setCameraStatus] = useState("");
  const [isLive, setIsLive] = useState(false);
  const [activeLiveSession, setActiveLiveSession] = useState(null);
  const [liveSessions, setLiveSessions] = useState([]);
  const [calendarItems, setCalendarItems] = useState([]);
  const [spaceListings, setSpaceListings] = useState([]);
  const [hostMarketListings, setHostMarketListings] = useState([]);
  const [spaceBookings, setSpaceBookings] = useState([]);
  const [spaceHostProfile, setSpaceHostProfile] = useState(null);
  const [spaceEarnings, setSpaceEarnings] = useState(null);
  const [spaceCityFilter, setSpaceCityFilter] = useState("");
  const [selectedSpaceListing, setSelectedSpaceListing] = useState(null);
  const [spaceBookingListingId, setSpaceBookingListingId] = useState(null);
  const [showSpaceListingForm, setShowSpaceListingForm] = useState(false);
  const [spacePhotoRows, setSpacePhotoRows] = useState([
    { id: 1, photo_type: "stage", caption: "" },
    { id: 2, photo_type: "audience", caption: "" },
  ]);
  const [spaceAvailabilitySlots, setSpaceAvailabilitySlots] = useState([]);
  const [spaceReviewTarget, setSpaceReviewTarget] = useState(null);
  const [spaceReviewRating, setSpaceReviewRating] = useState(5);
  const [spaceReviewComment, setSpaceReviewComment] = useState("");
  const [spaceReviewError, setSpaceReviewError] = useState("");
  const [spaceReviewSaving, setSpaceReviewSaving] = useState(false);
  const [showTicketStubSheet, setShowTicketStubSheet] = useState(false);
  const [artistLocalDraw, setArtistLocalDraw] = useState({});
  const [liveChatMessage, setLiveChatMessage] = useState("");
  const [liveChatMessages, setLiveChatMessages] = useState([
    { id: 1, name: "demo_fan", role: "Supporter", body: "Sound is good from here." },
    { id: 2, name: "artist1", role: "Artist", body: "Testing the live room and camera preview." },
  ]);
  const livePreviewRef = useRef(null);
  const [previewAsFan, setPreviewAsFan] = useState(false);
  const [highlightedProductId, setHighlightedProductId] = useState("");
  const [showPreviewBeforeShare, setShowPreviewBeforeShare] = useState(false);
  const [showEditProfile, setShowEditProfile] = useState(false);
  const [visitorBannerSaving, setVisitorBannerSaving] = useState(false);
  const [subData, setSubData] = useState({ subscriptions: [], fan_totals: {}, artist_totals: {} });
  const [supportTiers, setSupportTiers] = useState([]);
  const [tipData, setTipData] = useState({ results: [], count: 0 });
  const [notificationData, setNotificationData] = useState({ results: [], unread_count: 0 });
  const [dismissedNotificationIds, setDismissedNotificationIds] = useState(() => {
    try {
      return new Set(JSON.parse(localStorage.getItem("indiefundDismissedNotifications") || "[]"));
    } catch (error) {
      return new Set();
    }
  });
  const [myPurchases, setMyPurchases] = useState({ tickets: [], results: [] });
  const [storeCart, setStoreCart] = useState([]);
  const [showStoreCart, setShowStoreCart] = useState(false);
  const [message, setMessage] = useState("");
  const [selectedArtist, setSelectedArtist] = useState(null);
  const [activeProfession, setActiveProfession] = useState(DEFAULT_PROFESSION);
  const [pendingSupportArtist, setPendingSupportArtist] = useState(null);
  const [selectedSupportTierId, setSelectedSupportTierId] = useState("");
  const [selectedSupportEmailShare, setSelectedSupportEmailShare] = useState(false);
  const [mailingList, setMailingList] = useState(null);
  const [fanEmailSharing, setFanEmailSharing] = useState([]);
  const [artistDashboard, setArtistDashboard] = useState(null);
  const [connectStatus, setConnectStatus] = useState(null);
  const [challengeBoard, setChallengeBoard] = useState(null);
  const [artistTrustStatus, setArtistTrustStatus] = useState(null);
  const [artistProInsights, setArtistProInsights] = useState(null);
  const [promotionWallet, setPromotionWallet] = useState(null);
  const [promotionCampaigns, setPromotionCampaigns] = useState([]);
  const [growthCampaigns, setGrowthCampaigns] = useState([]);
  const [growthCampaignBusy, setGrowthCampaignBusy] = useState(false);
  const [promotionGenres, setPromotionGenres] = useState([]);
  const [promotionTargetingSuggestions, setPromotionTargetingSuggestions] = useState(null);
  const [applyDiscoveryCredits, setApplyDiscoveryCredits] = useState(true);
  const [promotionFeedbackSent, setPromotionFeedbackSent] = useState({});
  const [fansAlsoSupport, setFansAlsoSupport] = useState([]);
  const [homePromotionPlacements, setHomePromotionPlacements] = useState([]);
  const [artistPromotionPlacements, setArtistPromotionPlacements] = useState([]);
  const [playingNearYou, setPlayingNearYou] = useState([]);
  const [mySceneShowId, setMySceneShowId] = useState("");
  const [viewRefreshKey, setViewRefreshKey] = useState(0);
  const [setupChecklistDismissed, setSetupChecklistDismissed] = useState(false);
  const [platformMode, setPlatformMode] = useState(
    normalizePlatformMode(import.meta.env.VITE_PLATFORM_MODE || PLATFORM_MODE_LIVE)
  );
  const [showTipForm, setShowTipForm] = useState(false);
  const [activeTab, setActiveTab] = useState("listen");
  const [activeShopTab, setActiveShopTab] = useState("merch");
  const [activeMoreTab, setActiveMoreTab] = useState("settings");
  const [currentUser, setCurrentUser] = useState(null);
  const [isUserLoading, setIsUserLoading] = useState(true);
  const [betaFeedbackSummary, setBetaFeedbackSummary] = useState(null);
  const [authMode, setAuthMode] = useState("login");
  const [registerType, setRegisterType] = useState("fan");
  const [searchLocation, setSearchLocation] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [globalSearchResults, setGlobalSearchResults] = useState(null);
  const [featuredArtists, setFeaturedArtists] = useState([]);
  const [searchProfession, setSearchProfession] = useState("");
  const [savedSearchQuery, setSavedSearchQuery] = useState("");
  const [savedGenreFilter, setSavedGenreFilter] = useState("");
  const [reviewIndex, setReviewIndex] = useState(0);
  const [swipeDeltaX, setSwipeDeltaX] = useState(0);
  const [isSwiping, setIsSwiping] = useState(false);
  const swipeRef = useRef({ startX: null, startY: null, axis: null, pointerId: null });
  const reviewPanelRef = useRef(null);
  const [lastSkippedArtist, setLastSkippedArtist] = useState(null);
  const [lastSkippedTrack, setLastSkippedTrack] = useState(null);
  const [lastReviewAction, setLastReviewAction] = useState(null);
  const [expandedWhyArtistId, setExpandedWhyArtistId] = useState(null);
  const [pendingExternalLink, setPendingExternalLink] = useState(null);
  const [askBeforeExternalSocial, setAskBeforeExternalSocial] = useState(
    () => window.localStorage.getItem("askBeforeExternalSocial") !== "false"
  );
  const [hideSocialEmbeds, setHideSocialEmbeds] = useState(
    () => window.localStorage.getItem("hideSocialEmbeds") === "true"
  );
  const [skipUndoDismissed, setSkipUndoDismissed] = useState(
    () => window.localStorage.getItem("hideSkipUndoPrompt") === "true"
  );
  const [referralSource, setReferralSource] = useState(() => {
    const params = new URLSearchParams(window.location.search);
    const source = params.get("ref") || params.get("utm_source") || window.localStorage.getItem("indiefundReferralSource") || "";
    if (source) window.localStorage.setItem("indiefundReferralSource", source);
    return source;
  });
  const [pushEnabled, setPushEnabled] = useState(false);
  const pushSupported = typeof window !== "undefined" && "serviceWorker" in navigator && "PushManager" in window;
  const playbackEventKeysRef = useRef(new Set());

  function recordMusicPlaybackEvent(track, eventType, secondsPlayed = 0) {
    if (!track?.id || track.is_product) return;
    const key = `${track.id}:${eventType}:${currentUser?.id || "anon"}`;
    if (playbackEventKeysRef.current.has(key)) return;
    playbackEventKeysRef.current.add(key);

    apiFetch("/media/events/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        track_id: track.id,
        event_type: eventType,
        seconds_played: secondsPlayed,
        source: playbackSource?.label || "player",
      }),
    }).catch(() => {});
  }

  async function loadData() {
    const [
      artistData,
      musicData,
      playlistData,
      artworkData,
      songCoverData,
      postData,
      povData,
      instantData,
      productData,
      subDataResult,
      tierData,
      liveData,
      calendarData,
      spaceListingData,
      spaceBookingData,
    ] = await Promise.all([
      fetchJson("/artists/", []),
      fetchJson("/media/", []),
      fetchJson("/media/playlists/", { results: [] }),
      fetchJson("/media/artworks/", []),
      fetchJson("/media/cover-art/", []),
      fetchJson("/posts/", []),
      fetchJson("/posts/pov/", { results: [] }),
      fetchJson("/posts/instants/", { results: [] }),
      fetchJson("/marketplace/", []),
      fetchJson("/subscriptions/", { subscriptions: [], fan_totals: {}, artist_totals: {} }),
      fetchJson("/subscriptions/tiers/", { results: [] }),
      fetchJson("/live/", { results: [] }),
      fetchJson("/artists/calendar/", { results: [] }),
      fetchJson(`/spaces/listings/${currentUser?.is_host ? "?mine=1" : ""}`, { results: [] }),
      fetchJson("/spaces/bookings/", { results: [] }),
    ]);

    if (artistData) {
      setArtists(artistData);
      setSelectedArtist(current => {
        if (!current) return current;
        return artistData.find(artist => artist.owner_id === current.owner_id) || current;
      });
    }
    if (musicData) setMusic(musicData);
    if (playlistData) {
      const playlists = playlistData.results || [];
      setFanPlaylists(playlists);
      setSelectedPlaylistId(current => current || playlists[0]?.id || "");
    }
    if (artworkData) setArtworks(artworkData);
    if (songCoverData) setSongCovers(songCoverData);
    if (postData) setPosts(postData);
    if (povData) setPovs(povData.results || []);
    if (instantData) setInstants(instantData.results || []);
    if (productData) setProducts(productData);
    if (subDataResult) setSubData(subDataResult);
    if (tierData) setSupportTiers(tierData.results || []);
    if (liveData) setLiveSessions(liveData.results || []);
    if (calendarData) setCalendarItems(calendarData.results || []);
    if (spaceListingData) setSpaceListings(spaceListingData.results || []);
    if (spaceBookingData) setSpaceBookings(spaceBookingData.results || []);
  }

  function loadSpaces() {
    const listingsPromise = fetchJson(`/spaces/listings/${currentUser?.is_host ? "?mine=1" : ""}`, { results: [] })
      .then(data => {
        setSpaceListings(data.results || []);
        return data.results || [];
      });
    const bookingsPromise = fetchJson("/spaces/bookings/", { results: [] })
      .then(data => {
        setSpaceBookings(data.results || []);
        return data.results || [];
      });

    const hostPromises = [];
    if (currentUser?.is_host) {
      hostPromises.push(
        fetchJson("/spaces/listings/", { results: [] })
          .then(data => setHostMarketListings(data.results || [])),
        fetchJson("/spaces/host-profile/", null)
          .then(data => setSpaceHostProfile(data?.profile || null)),
        fetchJson("/spaces/host-earnings/", null)
          .then(data => setSpaceEarnings(data)),
      );
    } else {
      setHostMarketListings([]);
    }

    return Promise.all([listingsPromise, bookingsPromise, ...hostPromises]);
  }

  const refreshCurrentView = useCallback(async () => {
    const tasks = [loadData()];

    if (currentUser) {
      tasks.push(
        apiFetch("/notifications/")
          .then(r => r.json())
          .then(data => setNotificationData({
            results: data.results || [],
            unread_count: data.unread_count || 0,
          })),
        apiFetch("/discovery/saved-artists/")
          .then(r => r.json())
          .then(data => setSavedArtists(data.results || [])),
        apiFetch("/marketplace/my-purchases/")
          .then(r => (r.ok ? r.json() : { tickets: [], results: [] }))
          .then(data => setMyPurchases({
            tickets: data.tickets || [],
            results: data.results || [],
          })),
      );

      if (!currentUser.is_host) {
        tasks.push(Promise.resolve(loadPlayingNearYou()));
      }
      if (currentUser.is_host || currentUser.is_artist) {
        tasks.push(loadSpaces());
      }
      if (currentUser.is_artist) {
        tasks.push(Promise.resolve(loadArtistDashboard()));
      }
      if (activePage === "promote") {
        tasks.push(loadPromotionData());
      }
      if (activePage === "ads-manager") {
        tasks.push(loadGrowthCampaigns());
      }
    }

    if (isListenDiscoverBrowse(activePage, listenTab, discoverView)) {
      if (discoveryMode === "songs") {
        tasks.push(loadDiscoveryTracks({ backfill: Boolean(currentUser) }));
      } else {
        tasks.push(loadDiscovery({ backfill: Boolean(currentUser) }));
      }
    }

    if (activePage === "my-scene") {
      setViewRefreshKey(key => key + 1);
    }

    if (selectedArtist) {
      tasks.push(
        Promise.resolve(loadTips(selectedArtist, activeProfession)),
        Promise.resolve(loadCommissions()),
      );
    }

    await Promise.all(tasks);
  }, [
    activePage,
    activeProfession,
    currentUser,
    discoverView,
    discoveryMode,
    listenTab,
    searchLocation,
    searchProfession,
    searchQuery,
    selectedArtist,
  ]);

  function loadCommissions() {
    if (!currentUser) {
      setCommissionRequests([]);
      return;
    }

    apiFetch("/marketplace/commissions/")
      .then(r => r.ok ? r.json() : { results: [] })
      .then(data => setCommissionRequests(data.results || []));
  }

  function loadTips(artist = selectedArtist, profession = activeProfession) {
    if (!artist) {
      setTipData({ results: [], count: 0 });
      return;
    }

    apiFetch(`/subscriptions/tips/?artist_id=${artist.owner_id}&profession=${profession}`)
      .then(r => r.json())
      .then(data => setTipData({
        results: data.results || [],
        count: data.count || 0,
      }));
  }

  function loadDiscovery(options = {}) {
    const params = new URLSearchParams();
    if (searchQuery.trim()) params.set("q", searchQuery.trim());
    if (searchLocation.trim()) params.set("location", searchLocation.trim());
    if (searchProfession) params.set("profession", searchProfession);
    if (options.backfill) params.set("backfill", "true");

    const queryString = params.toString();
    return apiFetch(`/discovery/artists/${queryString ? `?${queryString}` : ""}`)
      .then(r => r.json())
      .then(data => {
        setDiscoveryArtists(data.results || []);
        setDiscoveryMeta({
          skipped_count: data.skipped_count || 0,
          count: data.count || 0,
          exhausted: Boolean(data.exhausted),
        });
        return data;
      });
  }

  function loadFeaturedArtists() {
    return apiFetch("/discovery/featured/")
      .then(r => r.ok ? r.json() : { results: [] })
      .then(data => {
        setFeaturedArtists(data.results || []);
        return data;
      });
  }

  function runGlobalSearch(query) {
    const trimmed = (query || "").trim();
    if (trimmed.length < 2) {
      setGlobalSearchResults(null);
      return Promise.resolve(null);
    }
    return apiFetch(`/discovery/search/?q=${encodeURIComponent(trimmed)}`)
      .then(r => r.ok ? r.json() : { artists: [], tracks: [], posts: [] })
      .then(data => {
        setGlobalSearchResults(data);
        return data;
      });
  }

  function openGlobalSearchResult(type, item) {
    setGlobalSearchResults(null);
    if (type === "artist") {
      window.location.href = `/?artist=${item.username}`;
      return;
    }
    if (type === "track") {
      goToListenTab("latest");
      return;
    }
    if (type === "post") {
      const match = artists.find(a => a.owner_username === item.author_username);
      if (match) openArtist(match);
    }
  }

  function loadDiscoveryTracks(options = {}) {
    const params = new URLSearchParams();
    if (searchQuery.trim()) params.set("q", searchQuery.trim());
    if (searchLocation.trim()) params.set("location", searchLocation.trim());
    if (searchProfession) params.set("profession", searchProfession);
    if (options.backfill) params.set("backfill", "true");

    const queryString = params.toString();
    return apiFetch(`/discovery/tracks/${queryString ? `?${queryString}` : ""}`)
      .then(r => r.json())
      .then(data => {
        setDiscoveryTracks(data.results || []);
        setDiscoveryTrackMeta({
          skipped_count: data.skipped_count || 0,
          count: data.count || 0,
          exhausted: Boolean(data.exhausted),
        });
        return data;
      });
  }

  function setDiscoveryBrowseMode(mode) {
    setDiscoveryMode(mode);
    window.localStorage.setItem("indiefundDiscoveryMode", mode);
    setReviewIndex(0);
    setLastSkippedArtist(null);
    setLastSkippedTrack(null);
    if (mode === "songs") {
      loadDiscoveryTracks({ backfill: Boolean(currentUser) });
    } else {
      loadDiscovery({ backfill: Boolean(currentUser) });
    }
  }

  function loadSavedArtists() {
    apiFetch("/discovery/saved-artists/")
      .then(r => r.json())
      .then(data => setSavedArtists(data.results || []));
  }

  function loadMyPurchases() {
    if (!currentUser) {
      setMyPurchases({ tickets: [], results: [] });
      return;
    }

    apiFetch("/marketplace/my-purchases/")
      .then(r => r.ok ? r.json() : { tickets: [], results: [] })
      .then(data => setMyPurchases({
        tickets: data.tickets || [],
        results: data.results || [],
      }));
  }

  function loadNotifications() {
    apiFetch("/notifications/")
      .then(r => r.json())
      .then(data => setNotificationData({
        results: data.results || [],
        unread_count: data.unread_count || 0,
      }));
  }

  async function enablePushNotifications() {
    if (!currentUser || !pushSupported) {
      setMessage("Push notifications are not supported in this browser.");
      return;
    }

    const permission = await Notification.requestPermission();
    if (permission !== "granted") {
      setMessage("Notification permission was not granted.");
      return;
    }

    const vapidResponse = await apiFetch("/notifications/push/vapid/");
    const vapidData = await vapidResponse.json();
    if (!vapidData.enabled || !vapidData.public_key) {
      setMessage("Push is not configured on the server yet. In-app notifications still work.");
      return;
    }

    const registration = await navigator.serviceWorker.ready;
    const subscription = await registration.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: urlBase64ToUint8Array(vapidData.public_key),
    });

    const res = await apiFetch("/notifications/push/subscribe/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ subscription: subscription.toJSON() }),
    });
    const data = await res.json();
    if (!res.ok) {
      setMessage(data.error || "Unable to enable push notifications.");
      return;
    }

    setPushEnabled(true);
    setMessage("Browser push notifications enabled.");
  }

  async function disablePushNotifications() {
    if (!currentUser) return;

    const registration = await navigator.serviceWorker.ready;
    const subscription = await registration.pushManager.getSubscription();
    await apiFetch("/notifications/push/unsubscribe/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ endpoint: subscription?.endpoint || "" }),
    });
    if (subscription) {
      await subscription.unsubscribe();
    }
    setPushEnabled(false);
    setMessage("Browser push notifications disabled.");
  }

  function urlBase64ToUint8Array(base64String) {
    const padding = "=".repeat((4 - (base64String.length % 4)) % 4);
    const base64 = (base64String + padding).replace(/-/g, "+").replace(/_/g, "/");
    const rawData = window.atob(base64);
    return Uint8Array.from([...rawData].map(char => char.charCodeAt(0)));
  }

  function loadMailingList() {
    if (!currentUser?.is_artist) {
      setMailingList(null);
      return;
    }

    apiFetch("/artists/mailing-list/")
      .then(r => r.ok ? r.json() : null)
      .then(data => setMailingList(data));
  }

  function loadFanEmailSharing() {
    if (!currentUser) {
      setFanEmailSharing([]);
      return;
    }

    apiFetch("/artists/fan-email-sharing/")
      .then(r => r.ok ? r.json() : { results: [] })
      .then(data => setFanEmailSharing(data.results || []));
  }

  function loadArtistDashboard() {
    if (!currentUser?.is_artist) {
      setArtistDashboard(null);
      setChallengeBoard(null);
      setConnectStatus(null);
      return;
    }

    apiFetch("/artists/dashboard/")
      .then(r => r.ok ? r.json() : null)
      .then(data => {
        setArtistDashboard(data);
        setConnectStatus(data?.payouts || null);
      });
    apiFetch("/challenges/today/")
      .then(r => r.ok ? r.json() : null)
      .then(data => setChallengeBoard(data));
    apiFetch("/artists/trust-status/")
      .then(r => r.ok ? r.json() : null)
      .then(data => setArtistTrustStatus(data));
    if (currentUser.artist_plan === "pro" || currentUser.artist_plan === "studio") {
      apiFetch("/artists/pro-insights/")
        .then(r => r.ok ? r.json() : null)
        .then(data => setArtistProInsights(data));
    } else {
      setArtistProInsights(null);
    }
  }

  async function startPayoutOnboarding() {
    const res = await apiFetch("/artists/connect/onboarding/", { method: "POST" });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      setMessage(data.error || "Unable to start payout setup.");
      return;
    }
    if (data.demo_mode) {
      setMessage("Demo mode: payout account linked locally. Real payouts start when Stripe is configured.");
      loadArtistDashboard();
      return;
    }
    if (data.onboarding_url) {
      window.location.assign(data.onboarding_url);
    }
  }

  async function loadPromotionData() {
    if (!currentUser?.is_artist) {
      setPromotionCampaigns([]);
      setPromotionGenres([]);
      setPromotionTargetingSuggestions(null);
      if (!currentUser) {
        setPromotionWallet(null);
        return;
      }
      const walletRes = await apiFetch("/promotions/wallet/");
      if (walletRes.ok) {
        setPromotionWallet(await walletRes.json());
      }
      return;
    }

    const [walletRes, campaignsRes, genresRes, targetingRes] = await Promise.all([
      apiFetch("/promotions/wallet/"),
      apiFetch("/promotions/campaigns/"),
      apiFetch("/promotions/genres/"),
      apiFetch("/promotions/targeting/suggestions/"),
    ]);

    if (walletRes.ok) {
      setPromotionWallet(await walletRes.json());
    }
    if (campaignsRes.ok) {
      const data = await campaignsRes.json();
      setPromotionCampaigns(data.results || []);
      if (data.balance && walletRes.ok === false) {
        setPromotionWallet(current => ({ ...(current || {}), balance: data.balance }));
      }
    }
    if (genresRes.ok) {
      const data = await genresRes.json();
      setPromotionGenres(data.results || []);
    }
    if (targetingRes.ok) {
      setPromotionTargetingSuggestions(await targetingRes.json());
    }
  }

  async function loadPromotionTargetingSuggestions(trackId = null) {
    const query = trackId ? `?track_id=${encodeURIComponent(trackId)}` : "";
    const res = await apiFetch(`/promotions/targeting/suggestions/${query}`);
    if (!res.ok) {
      return null;
    }
    const data = await res.json();
    setPromotionTargetingSuggestions(data);
    return data;
  }

  async function searchPromotionTargetArtists(query) {
    const res = await apiFetch(`/promotions/targeting/search/?q=${encodeURIComponent(query)}`);
    if (!res.ok) {
      return [];
    }
    const data = await res.json();
    return data.results || [];
  }

  async function buyPromotionCredits(amount) {
    const res = await apiFetch("/promotions/credits/checkout/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ amount }),
    });
    const data = await res.json();
    if (!res.ok) {
      setMessage(data.error || "Unable to add promotion credits.");
      return;
    }
    if (data.demo) {
      setMessage(
        data.launched_campaigns?.length
          ? `Credits added. ${data.launched_campaigns.length} draft campaign${data.launched_campaigns.length === 1 ? "" : "s"} launched.`
          : (data.message || "Promotion credits added.")
      );
      await loadPromotionData();
      return;
    }
    if (data.checkout_url) {
      window.location.href = data.checkout_url;
    }
  }

  async function createPromotionCampaign(payload) {
    const res = await apiFetch("/promotions/campaigns/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    if (!res.ok) {
      setMessage(data.error || "Unable to create campaign.");
      return;
    }
    if (data.needs_credits) {
      setMessage(`Campaign saved as draft. Add $${data.shortfall} more credits to launch.`);
    } else {
      setMessage("Campaign launched. Fans who match your targeting will start seeing it in Discovery.");
    }
    await loadPromotionData();
  }

  async function updatePromotionCampaign(campaignId, action) {
    const res = await apiFetch(`/promotions/campaigns/${campaignId}/action/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action }),
    });
    const data = await res.json();
    if (!res.ok) {
      setMessage(data.error || "Unable to update campaign.");
      return;
    }
    setMessage(`Campaign ${action}${action === "launch" ? "ed" : action.endsWith("e") ? "d" : "ed"}.`);
    await loadPromotionData();
  }

  async function loadGrowthCampaigns() {
    if (!currentUser?.is_artist) {
      setGrowthCampaigns([]);
      return;
    }
    const res = await apiFetch("/campaigns/");
    if (!res.ok) {
      return;
    }
    const data = await res.json();
    setGrowthCampaigns(data.results || []);
  }

  async function createGrowthCampaign(formData) {
    setGrowthCampaignBusy(true);
    try {
      const res = await apiFetch("/campaigns/", { method: "POST", body: formData });
      const data = await res.json();
      if (!res.ok) {
        setMessage(data.error || "Unable to save campaign.");
        return;
      }
      setMessage(data.message || "Campaign saved.");
      await loadGrowthCampaigns();
    } finally {
      setGrowthCampaignBusy(false);
    }
  }

  async function updateGrowthCampaign(campaignId, formData) {
    setGrowthCampaignBusy(true);
    try {
      const res = await apiFetch(`/campaigns/${campaignId}/update/`, { method: "POST", body: formData });
      const data = await res.json();
      if (!res.ok) {
        setMessage(data.error || "Unable to update campaign.");
        return;
      }
      setMessage(data.message || "Campaign updated.");
      await loadGrowthCampaigns();
    } finally {
      setGrowthCampaignBusy(false);
    }
  }

  async function deleteGrowthCampaign(campaignId) {
    setGrowthCampaignBusy(true);
    try {
      const res = await apiFetch(`/campaigns/${campaignId}/delete/`, { method: "POST" });
      const data = await res.json();
      if (!res.ok) {
        setMessage(data.error || "Unable to delete campaign.");
        return;
      }
      setMessage(data.message || "Campaign deleted.");
      await loadGrowthCampaigns();
    } finally {
      setGrowthCampaignBusy(false);
    }
  }

  async function updateGrowthCampaignStatus(campaignId, statusValue) {
    setGrowthCampaignBusy(true);
    try {
      const res = await apiFetch(`/campaigns/${campaignId}/update/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status: statusValue }),
      });
      const data = await res.json();
      if (!res.ok) {
        setMessage(data.error || "Unable to update campaign status.");
        return;
      }
      setMessage("Campaign status updated.");
      await loadGrowthCampaigns();
    } finally {
      setGrowthCampaignBusy(false);
    }
  }

  async function sendPromotionFeedback(campaignId, verdict) {
    if (!campaignId || !currentUser) return;
    const res = await apiFetch("/promotions/feedback/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ campaign_id: campaignId, verdict }),
    });
    const data = await res.json();
    if (!res.ok) {
      setMessage(data.error || "Unable to save feedback.");
      return;
    }
    setPromotionFeedbackSent(current => ({ ...current, [campaignId]: verdict }));
    if (data.wallet_balance) {
      setPromotionWallet(current => ({
        ...(current || {}),
        balance: data.wallet_balance,
        rewards_today: data.rewards_today,
      }));
    }
  }

  async function sharePromotedCampaign(campaignId, shareUrl) {
    if (!campaignId || !currentUser) return;
    const url = shareUrl || window.location.href;
    try {
      await navigator.clipboard.writeText(url);
    } catch {
      /* clipboard optional */
    }
    const res = await apiFetch("/promotions/share/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ campaign_id: campaignId }),
    });
    const data = await res.json();
    if (!res.ok) {
      setMessage(data.error || "Unable to record share.");
      return;
    }
    setMessage("Link copied. Thanks for spreading discovery.");
    setPromotionWallet(current => ({
      ...(current || {}),
      balance: data.wallet_balance,
      rewards_today: data.rewards_today,
    }));
  }

  async function upgradeArtistPlan(plan) {
    if (plan === "free") {
      const res = await apiFetch("/accounts/artist-plan/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ plan }),
      });
      const data = await res.json();
      if (!res.ok) {
        setMessage(data.error || "Unable to update artist plan.");
        return;
      }
      if (data.user) {
        setCurrentUser(data.user);
      }
      setMessage(data.message || "Artist plan updated.");
      await loadPromotionData();
      return;
    }

    const res = await apiFetch("/accounts/artist-plan/checkout/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ plan }),
    });
    const data = await res.json();
    if (!res.ok) {
      setMessage(data.error || "Unable to start artist plan checkout.");
      return;
    }
    if (data.demo) {
      if (data.user) {
        setCurrentUser(data.user);
      }
      if (data.studio_credits_granted) {
        setMessage(`Studio plan active. $${data.studio_credits_granted} in promotion credits added to your wallet.`);
      } else {
        setMessage(data.message || "Artist plan updated.");
      }
      await loadPromotionData();
      return;
    }
    if (data.checkout_url) {
      window.location.href = data.checkout_url;
    }
  }

  function loadPlayingNearYou(location = searchLocation || currentUser?.discovery_location || "") {
    const path = location
      ? `/discovery/playing-near-you/?location=${encodeURIComponent(location)}`
      : "/discovery/playing-near-you/";
    apiFetch(path)
      .then(r => r.ok ? r.json() : { results: [] })
      .then(data => setPlayingNearYou(data.results || []));
  }

  async function markNotificationsRead() {
    const res = await apiFetch("/notifications/mark-read/", { method: "POST" });
    if (res.ok) {
      loadNotifications();
    }
  }

  function persistDismissedNotificationIds(ids) {
    localStorage.setItem("indiefundDismissedNotifications", JSON.stringify([...ids]));
  }

  async function clearNotification(item) {
    if (!item || !currentUser) return;

    if (item.notificationId) {
      const res = await apiFetch("/notifications/clear/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id: item.notificationId }),
      });
      const data = await res.json();
      if (!res.ok) {
        setMessage(data.error || "Unable to clear notification.");
        return;
      }
      loadNotifications();
    }

    setDismissedNotificationIds(current => {
      const next = new Set(current);
      next.add(item.id);
      persistDismissedNotificationIds(next);
      return next;
    });
  }

  async function clearAllNotifications() {
    if (!currentUser) return;

    const visibleItems = buildNotificationsList();
    if (notificationData.results.length > 0) {
      const res = await apiFetch("/notifications/clear/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({}),
      });
      const data = await res.json();
      if (!res.ok) {
        setMessage(data.error || "Unable to clear notifications.");
        return;
      }
      loadNotifications();
    }

    setDismissedNotificationIds(current => {
      const next = new Set(current);
      visibleItems.forEach(item => next.add(item.id));
      persistDismissedNotificationIds(next);
      return next;
    });
    setMessage("Notifications cleared.");
  }

  async function loadCurrentUser() {
    const data = await fetchJson("/accounts/current-user/", { user: null });
    const user = data?.user ?? null;
    setCurrentUser(user);
    setIsUserLoading(false);
    setSearchLocation(user?.discovery_location || "");
    if (user?.user_type === "admin") {
      loadBetaFeedbackSummary();
    } else {
      setBetaFeedbackSummary(null);
    }
    return user;
  }

  async function loadBetaFeedbackSummary() {
    const data = await fetchJson("/accounts/beta-feedback/summary/", null);
    setBetaFeedbackSummary(data);
  }

  async function resolveBetaFeedback(feedbackId, resolved) {
    const res = await apiFetch(`/accounts/beta-feedback/${feedbackId}/resolve/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ resolved }),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      setMessage(data.error || "Unable to update feedback.");
      return;
    }
    if (data.summary) setBetaFeedbackSummary(data.summary);
    setMessage(data.message || (resolved ? "Marked resolved." : "Reopened."));
  }

  function gatePlatformPage(page, user = currentUser, mode = platformMode) {
    return resolvePageForPlatformMode(page || "home", mode, user);
  }

  async function loadPlatformMode() {
    const envDefault = normalizePlatformMode(import.meta.env.VITE_PLATFORM_MODE || PLATFORM_MODE_LIVE);
    try {
      const response = await apiFetch("/health/");
      if (!response.ok) return envDefault;
      const data = await response.json();
      const mode = normalizePlatformMode(data.platform_mode || envDefault);
      setPlatformMode(mode);
      return mode;
    } catch {
      return envDefault;
    }
  }

  function openCreatorSignup(type = "artist") {
    setAuthMode("register");
    setRegisterType(type);
    goToPage("profile");
  }

  function openFanWaitlist() {
    setAuthMode("waitlist");
    goToPage("profile");
  }

  function filterNavItemsForPlatform(items) {
    if (!isPrelaunchMode(platformMode) || canAccessFanExperience(platformMode, currentUser)) {
      return items;
    }
    return items.filter(item => !item.page || !isFanGatedPage(item.page));
  }

  function applyPageRoute(page, tabParam = "", viewParam = "", sectionParam = "", mode = platformMode) {
    const listenRoute = resolveListenRoute(page, tabParam, viewParam);
    if (listenRoute) {
      const gatedPage = gatePlatformPage(listenRoute.page, currentUser, mode);
      if (gatedPage === "prelaunch") {
        setActivePage("prelaunch");
        return "prelaunch";
      }
      setActivePage(listenRoute.page);
      setListenTab(listenRoute.listenTab);
      setDiscoverView(listenRoute.discoverView);
      return listenRoute.page;
    }
    const storesRoute = resolveStoresRoute(page, tabParam);
    if (storesRoute) {
      const gatedPage = gatePlatformPage(storesRoute.page, currentUser, mode);
      if (gatedPage === "prelaunch") {
        setActivePage("prelaunch");
        return "prelaunch";
      }
      setActivePage(storesRoute.page);
      setStoreTab(storesRoute.storeTab);
      return storesRoute.page;
    }
    if (page === "profile") {
      setActivePage("profile");
      setProfileTab(resolveProfileTab(tabParam));
      setSettingsSection(resolveSettingsSection(sectionParam, currentUser, "library"));
      return "profile";
    }
    if (page === "early-access" && !isPrelaunchMode(mode)) {
      setActivePage("home");
      return "home";
    }
    const resolved = gatePlatformPage(page || "home", currentUser, mode);
    setActivePage(resolved);
    return resolved;
  }

  function syncRouteFromUrl(user = currentUser) {
    const params = new URLSearchParams(window.location.search);
    const page = params.get("page");
    const tab = params.get("tab") || "";
    const view = params.get("view") || "";
    const section = params.get("section") || "";
    const artistUsername = params.get("artist");
    setMySceneShowId(params.get("show") || "");

    if (artistUsername && artists.length) {
      const artist = artists.find(item => item.owner_username === artistUsername);
      if (artist) {
        const profession = resolveArtistProfession(artist, params.get("profession") || "");
        setSelectedArtist(artist);
        setActiveProfession(profession);
        setActiveTab(primaryContentTab(profession));
        return;
      }
    }

    if (!user) {
      if (!artistUsername) {
        applyPageRoute(page, tab, view);
        setSelectedArtist(null);
      }
      return;
    }

    setSelectedArtist(null);
    const resolvedPage = resolveAccountPage(page, user, tab, view);
    const listenRoute = resolveListenRoute(page, tab, view);
    if (listenRoute) {
      applyPageRoute(page, tab, view);
    } else if (resolveStoresRoute(page, tab)) {
      applyPageRoute(page, tab, view);
    } else if (LEGAL_PAGE_IDS.has(resolvedPage)) {
      setActivePage(resolvedPage);
    } else if (resolvedPage === "profile") {
      setActivePage("profile");
      setProfileTab(resolveProfileTab(tab));
      setSettingsSection(resolveSettingsSection(section, user, "library"));
    } else {
      const allowedPages = user?.is_host ? HOST_PAGES : FAN_PAGES;
      const nextPage = resolvedPage && allowedPages.has(resolvedPage) ? resolvedPage : "home";
      setActivePage(gatePlatformPage(nextPage, user));
    }
  }

  useEffect(() => {
    async function init() {
      const platformModeFromHealth = await loadPlatformMode();
      const user = await loadCurrentUser();
      loadData();
      loadNotifications();

      const params = new URLSearchParams(window.location.search);
      const page = params.get("page");
      const tab = params.get("tab") || "";
      const view = params.get("view") || "";
      const supportStatus = params.get("support");
      const purchaseStatus = params.get("purchase");
      const artistUsername = params.get("artist");
      setMySceneShowId(params.get("show") || "");

      if (user) {
        const resolvedPage = resolveAccountPage(page, user, tab, view);
        const allowedPages = user.is_host ? HOST_PAGES : FAN_PAGES;
        const listenRoute = resolveListenRoute(page, tab, view);
        if (resolvedPage && LEGAL_PAGE_IDS.has(resolvedPage)) {
          setActivePage(resolvedPage);
        } else if (listenRoute) {
          applyPageRoute(page, tab, view, "", platformModeFromHealth);
        } else if (resolveStoresRoute(page, tab)) {
          applyPageRoute(page, tab, view, "", platformModeFromHealth);
        } else if (resolvedPage === "profile") {
          setActivePage("profile");
          setProfileTab(resolveProfileTab(tab));
          setSettingsSection(resolveSettingsSection(params.get("section") || "", user, "library"));
        } else if (resolvedPage && allowedPages.has(resolvedPage)) {
          setActivePage(gatePlatformPage(resolvedPage, user, platformModeFromHealth));
        } else if (!page && !artistUsername) {
          setActivePage(user.is_host ? "spaces" : "home");
        }
      } else if (!artistUsername) {
        applyPageRoute(page, tab, view, "", platformModeFromHealth);
      }

      if (supportStatus === "success") {
        setMessage("Payment started. Your supporter access will unlock after Stripe confirms the subscription.");
        window.history.replaceState({}, "", window.location.pathname);
      }

      if (supportStatus === "cancelled") {
        setMessage("Checkout cancelled. You were not charged.");
        window.history.replaceState({}, "", window.location.pathname);
      }

      if (purchaseStatus === "success") {
        setMessage("Payment received. Your purchase will appear in Profile → My tickets shortly.");
        loadMyPurchases();
        loadNotifications();
        window.history.replaceState({}, "", window.location.pathname);
      }

      if (purchaseStatus === "cancelled") {
        setMessage("Checkout cancelled. You were not charged.");
        window.history.replaceState({}, "", window.location.pathname);
      }

      const promoteStatus = params.get("promote");
      if (promoteStatus === "success") {
        setMessage("Promotion credits added. You can launch a campaign now.");
        if (user?.is_artist) {
          setActivePage("promote");
        }
        window.history.replaceState({}, "", window.location.pathname);
      }

      if (promoteStatus === "cancelled") {
        setMessage("Credit purchase cancelled.");
        window.history.replaceState({}, "", window.location.pathname);
      }

      const planStatus = params.get("plan");
      if (planStatus === "success") {
        setMessage("Artist plan payment started. Your upgrade unlocks after Stripe confirms the subscription.");
        loadCurrentUser().then(nextUser => {
          if (nextUser) setCurrentUser(nextUser);
        });
        loadPromotionData();
        window.history.replaceState({}, "", window.location.pathname);
      }

      if (planStatus === "cancelled") {
        setMessage("Artist plan checkout cancelled. You were not charged.");
        window.history.replaceState({}, "", window.location.pathname);
      }

      const reviewBookingId = params.get("review_booking");
      if (reviewBookingId && user) {
        setActivePage("spaces");
        openSpaceReviewModal(Number(reviewBookingId), user);
        window.history.replaceState({}, "", window.location.pathname);
      }

      const waitlistConfirm = params.get("waitlist-confirm");
      if (waitlistConfirm) {
        const confirmRes = await apiFetch(`/accounts/waitlist/confirm/?token=${encodeURIComponent(waitlistConfirm)}`);
        const confirmData = await confirmRes.json();
        setMessage(confirmRes.ok ? confirmData.message : confirmData.error || "Unable to confirm waitlist email.");
        window.history.replaceState({}, "", window.location.pathname);
      }

      loadFeaturedArtists();
    }

    init();
  }, []);

  useEffect(() => {
    try {
      const saved = JSON.parse(localStorage.getItem(CART_STORAGE_KEY) || "[]");
      if (Array.isArray(saved)) setStoreCart(saved);
    } catch {
      setStoreCart([]);
    }
  }, []);

  useEffect(() => {
    if (isPrelaunchMode(platformMode)) {
      setRegisterType(current => (current === "fan" ? "artist" : current));
    }
  }, [platformMode]);

  useEffect(() => {
    if (isUserLoading) return;
    const params = new URLSearchParams(window.location.search);
    if (params.get("artist")) return;
    applyPageRoute(
      params.get("page"),
      params.get("tab") || "",
      params.get("view") || "",
      params.get("section") || "",
      platformMode
    );
  }, [platformMode, isUserLoading, currentUser?.id]);

  useEffect(() => {
    if (previewAsFan && currentUser?.is_artist) {
      markPreviewedPublicPage(currentUser.id);
    }
  }, [previewAsFan, currentUser?.id, currentUser?.is_artist]);

  useEffect(() => {
    setReviewIndex(0);
  }, [fanChannelUsername]);

  useEffect(() => {
    if (!currentUser?.id) {
      setSetupChecklistDismissed(false);
      return;
    }
    const role = currentUser.is_artist ? "artist" : currentUser.is_host ? "host" : "fan";
    setSetupChecklistDismissed(isSetupDismissed(currentUser.id, role));
  }, [currentUser?.id, currentUser?.is_artist, currentUser?.is_host]);

  useEffect(() => {
    const onProfileThemes = activePage === "profile" && profileTab === "themes";
    const onStudioThemes = Boolean(
      selectedArtist
      && currentUser?.username === selectedArtist.owner_username
      && activeTab === "more"
      && activeMoreTab === "settings"
    );
    if (!onProfileThemes && !onStudioThemes) {
      setThemePreview(null);
    }
  }, [activePage, profileTab, selectedArtist?.owner_username, currentUser?.username, activeTab, activeMoreTab]);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const artistUsername = params.get("artist");
    const profession = params.get("profession") || "";
    const { tab, productId } = readArtistDeepLinkParams(window.location.search);
    if (!artistUsername || artists.length === 0) return;

    const artist = artists.find(item => item.owner_username === artistUsername);
    if (!artist) return;

    const sameArtist = selectedArtist?.owner_username === artistUsername;
    const sameProfession = !profession || profession === activeProfession;
    if (sameArtist && sameProfession && !productId) {
      if (!tab) return;
      const mapped = LEGACY_PROFILE_TAB_MAP[tab];
      if (mapped) {
        const shopMatches = !mapped.shopTab || activeShopTab === mapped.shopTab;
        if (activeTab === mapped.section && shopMatches) return;
      }
    }

    openArtist(artist, false, { profession, tab, productId });
  }, [artists, selectedArtist?.owner_username, activeProfession, activeTab, activeShopTab]);

  useEffect(() => {
    if (!highlightedProductId) return undefined;

    const frameId = window.requestAnimationFrame(() => {
      const element = document.getElementById(`product-${highlightedProductId}`);
      if (!element) return;

      element.scrollIntoView({ behavior: "smooth", block: "center" });
      element.classList.add("product-card--highlight");
      window.setTimeout(() => {
        element.classList.remove("product-card--highlight");
        setHighlightedProductId("");
      }, 3200);
    });

    return () => window.cancelAnimationFrame(frameId);
  }, [highlightedProductId, products, activeTab, activeShopTab, selectedArtist?.owner_id]);

  useEffect(() => {
    let cancelled = false;

    async function syncArtistMeta() {
      if (!selectedArtist?.owner_username) {
        updateArtistPageMeta(null);
        return;
      }

      const meta = await fetchArtistMeta(API, selectedArtist.owner_username, activeProfession);
      if (!cancelled) {
        const sideProfile = getActiveProfessionProfile(selectedArtist, activeProfession);
        updateArtistPageMeta(meta || {
          stage_name: selectedArtist.stage_name,
          title: `${sideProfile?.display_title || selectedArtist.stage_name} — ${professionLabel(activeProfession)} on IndieFund`,
          description: sideProfile?.bio || selectedArtist.artist_story || `Support ${selectedArtist.stage_name} on IndieFund.`,
          page_url: getArtistPublicUrl("", selectedArtist, activeProfession),
          hero_image: sideProfile?.cover_image || selectedArtist.hero_image || "",
        });
      }
    }

    syncArtistMeta();
    return () => {
      cancelled = true;
    };
  }, [selectedArtist?.owner_username, selectedArtist?.stage_name, selectedArtist?.hero_image, activeProfession]);

  useEffect(() => {
    if (!LEGAL_PAGE_IDS.has(activePage)) return;
    updateLegalPageMeta(getLegalPage(activePage));
  }, [activePage]);

  useEffect(() => {
    const onPopState = () => syncRouteFromUrl(currentUser);
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, [artists, currentUser]);

  useEffect(() => {
    if (currentUser?.is_host && activePage === "home") {
      goToPage("spaces", true);
    }
  }, [currentUser?.id, currentUser?.is_host, activePage]);

  useEffect(() => {
    if (currentUser) {
      loadSpaces();
    }
  }, [currentUser?.id, currentUser?.is_host]);

  useEffect(() => {
    if (!currentUser && (activePage !== "listen" || listenTab !== "discover")) return;
    if (discoverView === "saved") return;
    const timeoutId = window.setTimeout(() => {
      if (discoveryMode === "songs") {
        loadDiscoveryTracks({ backfill: Boolean(currentUser) });
      } else {
        loadDiscovery({ backfill: Boolean(currentUser) });
      }
    }, 150);
    return () => window.clearTimeout(timeoutId);
  }, [searchQuery, searchLocation, searchProfession, currentUser?.id, activePage, discoveryMode, discoverView, listenTab]);

  useEffect(() => {
    loadSavedArtists();
  }, [currentUser?.id]);

  useEffect(() => {
    if (!selectedArtist) return;
    const professions = getArtistProfessions(selectedArtist);
    if (!professions.some(profession => profession.key === activeProfession)) {
      setActiveProfession(professions[0]?.key || DEFAULT_PROFESSION);
    }
  }, [selectedArtist?.id, selectedArtist?.profession_keys?.join(","), activeProfession]);

  useEffect(() => {
    loadNotifications();
  }, [currentUser?.id]);

  useEffect(() => {
    loadMyPurchases();
  }, [currentUser?.id]);

  useEffect(() => {
    loadMailingList();
    loadFanEmailSharing();
    loadArtistDashboard();
  }, [currentUser?.id, currentUser?.artist_plan]);

  useEffect(() => {
    if (currentUser?.is_artist && activePage === "promote") {
      loadPromotionData();
      return;
    }
    if (currentUser?.is_artist && activePage === "ads-manager") {
      loadGrowthCampaigns();
      return;
    }
    if (currentUser && !currentUser.is_artist && (activePage === "listen" || activePage === "profile")) {
      loadPromotionData();
    }
  }, [currentUser?.id, currentUser?.artist_plan, currentUser?.is_artist, activePage]);

  useEffect(() => {
    if (currentUser && !currentUser.is_host) {
      loadPlayingNearYou();
    }
  }, [currentUser?.id, currentUser?.discovery_location, searchLocation]);

  useEffect(() => {
    loadCommissions();
  }, [currentUser?.id]);

  useEffect(() => {
    if (selectedArtist?.owner_id) {
      loadFansAlsoSupport(selectedArtist);
      if (currentUser && currentUser.username !== selectedArtist.owner_username) {
        loadPromotionPlacements("artist_page", selectedArtist.owner_id);
      } else {
        setArtistPromotionPlacements([]);
      }
      return;
    }
    setFansAlsoSupport([]);
    setArtistPromotionPlacements([]);
  }, [selectedArtist?.owner_id, currentUser?.id, currentUser?.username]);

  useEffect(() => {
    if (currentUser && !currentUser.is_artist && !currentUser.is_host && activePage === "home") {
      loadPromotionPlacements("home");
      return;
    }
    setHomePromotionPlacements([]);
  }, [currentUser?.id, currentUser?.is_artist, currentUser?.is_host, activePage]);

  useEffect(() => {
    if (selectedArtist) {
      loadTips(selectedArtist, activeProfession);
      return;
    }

    if (activePage === "home" && currentUser?.is_artist) {
      const artist = artists.find(item => item.owner_username === currentUser.username);
      if (artist) loadTips(artist, DEFAULT_PROFESSION);
    }
  }, [selectedArtist?.owner_id, activeProfession, activePage, currentUser?.id, artists]);

  useEffect(() => {
    if (!currentUser?.is_artist || activePage !== "spaces" || spaceListings.length === 0) {
      return;
    }

    const artist = getCurrentArtist();
    if (!artist?.owner_id) return;

    const cities = [...new Set(spaceListings.map(listing => (listing.city || "").trim()).filter(Boolean))];
    if (cities.length === 0) return;

    let cancelled = false;
    Promise.all(
      cities.map(city =>
        apiFetch(`/spaces/artists/${artist.owner_id}/draw-profile/?venue_city=${encodeURIComponent(city)}`)
          .then(res => (res.ok ? res.json() : null))
          .then(data => [city.toLowerCase(), data])
          .catch(() => [city.toLowerCase(), null])
      )
    ).then(results => {
      if (cancelled) return;
      const next = {};
      cities.forEach(city => {
        next[city.toLowerCase()] = { local_supporters: 0 };
      });
      results.forEach(([city, data]) => {
        if (data) next[city] = data;
      });
      setArtistLocalDraw(next);
    });

    return () => {
      cancelled = true;
    };
  }, [currentUser?.is_artist, currentUser?.username, activePage, spaceListings.length, artists.length]);

  useEffect(() => {
    if (window.instgrm?.Embeds) {
      window.instgrm.Embeds.process();
    } else if (document.querySelector(".instagram-media")) {
      const script = document.createElement("script");
      script.async = true;
      script.src = "https://www.instagram.com/embed.js";
      document.body.appendChild(script);
    }

    if (document.querySelector(".tiktok-embed") && !document.querySelector("script[src='https://www.tiktok.com/embed.js']")) {
      const script = document.createElement("script");
      script.async = true;
      script.src = "https://www.tiktok.com/embed.js";
      document.body.appendChild(script);
    }
  }, [posts, selectedArtist?.id, activePage, activeTab]);

  function professionLabel(profession) {
    return PROFESSION_LABELS[profession] || "Music";
  }

  function isMusicBranchProfession(profession) {
    return MUSIC_BRANCH_PROFESSIONS.has(profession);
  }

  function branchLabel(profession) {
    return isMusicBranchProfession(profession) ? "IndieFund | Music" : "IndieFund | Arts";
  }

  function professionBranch(profession) {
    return isMusicBranchProfession(profession) ? "music" : "arts";
  }

  function primaryContentTab(profession) {
    return isMusicBranchProfession(profession) ? "listen" : "feed";
  }

  const LEGACY_PROFILE_TAB_MAP = {
    music: { section: "listen" },
    works: { section: "listen" },
    posts: { section: "feed" },
    merch: { section: "shop", shopTab: "merch" },
    "music-store": { section: "shop", shopTab: "music-store" },
    support: { section: "shop", shopTab: "support" },
    lives: { section: "live" },
    calendar: { section: "more", moreTab: "calendar" },
    settings: { section: "more", moreTab: "settings" },
    "support-tiers": { section: "more", moreTab: "support-tiers" },
    about: { section: "listen" },
  };

  function resolveProfileContentTab(section, shopTab, moreTab, profession) {
    if (section === "listen") {
      return isMusicBranchProfession(profession) ? "music" : "works";
    }
    if (section === "feed") return "posts";
    if (section === "shop") return shopTab;
    if (section === "live") return "lives";
    if (section === "more") {
      if (moreTab === "support-tiers") return "support-tiers";
      if (moreTab === "calendar") return "calendar";
      return "settings";
    }
    return section;
  }

  function getProfileSectionLabel(section, profession = activeProfession) {
    if (section === "listen") {
      if (profession === "comedy") return "Sets";
      if (profession === "podcast") return "Episodes";
      if (profession === "film") return "Films";
      if (profession === "performance") return "Performance";
      if (profession === "writing") return "Writing";
      if (isMusicBranchProfession(profession)) return "Listen";
      return "Works";
    }
    return {
      feed: "Feed",
      shop: "Shop",
      live: "Live",
      more: "More",
    }[section] || section;
  }

  function getProfileShopLabel(shopTab) {
    return {
      merch: "Merch",
      "music-store": "Music products",
      support: "Support",
    }[shopTab] || shopTab;
  }

  function getProfileMoreLabel(moreTab) {
    return {
      calendar: "Calendar",
      "support-tiers": "Support tier editor",
      settings: "Settings",
    }[moreTab] || moreTab;
  }

  function navigateProfileSection(section, { shopTab, moreTab } = {}) {
    const mapped = LEGACY_PROFILE_TAB_MAP[section] || { section };
    const nextSection = mapped.section || section;
    setActiveTab(nextSection);
    if (nextSection === "shop" && shopTab) {
      setActiveShopTab(shopTab);
    } else if (mapped.shopTab || shopTab) {
      setActiveShopTab(shopTab || mapped.shopTab);
    }
    if (mapped.moreTab || moreTab) {
      setActiveMoreTab(moreTab || mapped.moreTab);
    }
  }

  function getArtistProfessions(artist) {
    if (!artist) return [{ key: DEFAULT_PROFESSION, label: professionLabel(DEFAULT_PROFESSION) }];
    if (Array.isArray(artist.professions) && artist.professions.length) return artist.professions;
    if (Array.isArray(artist.profession_keys) && artist.profession_keys.length) {
      return artist.profession_keys.map(key => ({ key, label: professionLabel(key) }));
    }
    return [{ key: DEFAULT_PROFESSION, label: professionLabel(DEFAULT_PROFESSION) }];
  }

  function getDefaultProfession(artist) {
    return getArtistProfessions(artist)[0]?.key || DEFAULT_PROFESSION;
  }

  function resolveArtistProfession(artist, professionKey = "") {
    const professions = getArtistProfessions(artist);
    if (professionKey && professions.some(item => item.key === professionKey)) {
      return professionKey;
    }
    return professions[0]?.key || DEFAULT_PROFESSION;
  }

  function buildArtistPageUrl(artist, profession = "", { ref = "", tab = "", productId = "" } = {}) {
    const params = new URLSearchParams({ artist: artist.owner_username });
    if (profession) params.set("profession", profession);
    if (ref) params.set("ref", ref);
    if (tab) params.set("tab", tab);
    if (productId) params.set("product", String(productId));
    return `${window.location.pathname}?${params.toString()}`;
  }

  function updateArtistPageUrl(artist, profession = "", { replace = false, ref = "", tab = "", productId = "" } = {}) {
    const url = buildArtistPageUrl(artist, profession, { ref, tab, productId });
    if (replace) {
      window.history.replaceState({}, "", url);
    } else {
      window.history.pushState({}, "", url);
    }
  }

  function applyArtistPageRoute(options = {}) {
    const mapped = options.tab ? LEGACY_PROFILE_TAB_MAP[options.tab] : null;
    if (mapped) {
      setActiveTab(mapped.section);
      if (mapped.shopTab) setActiveShopTab(mapped.shopTab);
      if (mapped.moreTab) setActiveMoreTab(mapped.moreTab);
    } else if (options.shopTab) {
      setActiveTab("shop");
      setActiveShopTab(options.shopTab);
    } else if (options.sectionTab) {
      setActiveTab(options.sectionTab);
    }
    if (options.productId) {
      setHighlightedProductId(String(options.productId));
    }
  }

  function switchArtistProfession(professionKey) {
    if (!selectedArtist) return;
    const nextProfession = resolveArtistProfession(selectedArtist, professionKey);
    setActiveProfession(nextProfession);
    setActiveTab(primaryContentTab(nextProfession));
    setStoreFormType(null);
    setShowStoreTypePicker(false);
    updateArtistPageUrl(selectedArtist, nextProfession, { replace: true });
    loadTips(selectedArtist, nextProfession);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function getActiveProfessionProfile(artist, profession = activeProfession) {
    return artist?.profession_profiles?.[profession] || null;
  }

  function isSupporting(username, profession = activeProfession) {
    return subData.subscriptions?.some(sub =>
      sub.artist === username &&
      sub.fan_id === currentUser?.id &&
      (sub.profession || DEFAULT_PROFESSION) === profession &&
      sub.active
    );
  }

  function isSupportingAny(username) {
    return subData.subscriptions?.some(sub =>
      sub.artist === username &&
      sub.fan_id === currentUser?.id &&
      sub.active
    );
  }

  function artistSupportState(artist) {
    const profession = getDefaultProfession(artist);
    return {
      profession,
      supporting: isSupporting(artist.owner_username, profession),
    };
  }

  async function supportArtist(username, profession = activeProfession, tierId = selectedSupportTierId, shareEmail = selectedSupportEmailShare) {
    if (!currentUser) {
      setMessage("Log in before supporting artists.");
      return;
    }

    const artist = artists.find(a => a.owner_username === username)
      || (selectedArtist?.owner_username === username ? selectedArtist : null);
    if (!artist) {
      setMessage("Unable to find this artist.");
      return;
    }

    const ownerId = await resolveArtistOwnerId(artist);
    if (!ownerId) {
      setMessage("Unable to start checkout for this artist.");
      return;
    }

    const res = await apiFetch("/subscriptions/checkout/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        artist_id: ownerId,
        profession,
        tier_id: tierId || undefined,
        monthly_amount: "1.00",
        billing_date: new Date().getDate(),
        share_email_with_artist: shareEmail,
        referral_source: referralSource,
      }),
    });
    const data = await res.json();

    if (!res.ok) {
      setMessage(data.error || "Unable to start checkout.");
      setPendingSupportArtist(null);
      return;
    }

    if (data.checkout_url) {
      window.location.href = data.checkout_url;
      return;
    }

    setSubData(current => {
      const existing = current.subscriptions || [];
      const nextSubscription = {
        id: data.subscription_id || `demo-${Date.now()}`,
        fan_id: currentUser.id,
        fan: currentUser.username,
        artist_id: artist.owner_id,
        artist: username,
        profession,
        profession_label: data.profession_label || professionLabel(profession),
        tier_id: data.tier_id || null,
        tier_name: data.tier_name || "Supporter",
        monthly_amount: data.monthly_amount || "1.00",
        artist_share: data.artist_share || "0.90",
        platform_fee: data.platform_fee || "0.10",
        billing_date: new Date().getDate(),
        active: true,
        payment_provider: data.demo ? "demo" : "stripe_pending",
      };
      const filtered = existing.filter(sub =>
        !(
          sub.fan_id === currentUser.id &&
          sub.artist === username &&
          (sub.profession || DEFAULT_PROFESSION) === profession
        )
      );
      return {
        ...current,
        subscriptions: [...filtered, nextSubscription],
      };
    });

    setArtists(current =>
      current.map(item => {
        if (item.owner_username !== username) return item;
        const health = { ...(item.business_health || {}) };
        const nextCount = Number(health.active_subscribers || 0) + 1;
        const nextShare = (
          Number(health.monthly_artist_share || 0) + Number(data.artist_share || 0.9)
        ).toFixed(2);
        return {
          ...item,
          business_health: {
            ...health,
            active_subscribers: nextCount,
            monthly_artist_share: nextShare,
          },
        };
      })
    );
    setSelectedArtist(current => {
      if (!current || current.owner_username !== username) return current;
      const health = { ...(current.business_health || {}) };
      const nextCount = Number(health.active_subscribers || 0) + 1;
      const nextShare = (
        Number(health.monthly_artist_share || 0) + Number(data.artist_share || 0.9)
      ).toFixed(2);
      return {
        ...current,
        business_health: {
          ...health,
          active_subscribers: nextCount,
          monthly_artist_share: nextShare,
        },
      };
    });

    setMessage(data.message || "Checkout started.");
    setPendingSupportArtist(null);
    setSelectedSupportEmailShare(false);
    await Promise.all([
      loadData(),
      loadMailingList(),
      loadFanEmailSharing(),
      loadArtistDashboard(),
      loadNotifications(),
    ]);
  }

  function requestSupport(artist, supporting, profession = activeProfession) {
    if (supporting) {
      manageSupport(artist.owner_username, profession);
      return;
    }

    if (!currentUser) {
      setMessage("Log in before supporting artists.");
      return;
    }

    setSelectedSupportTierId("");
    setSelectedSupportEmailShare(false);
    setPendingSupportArtist({ artist, profession });
  }

  function confirmSupport() {
    if (!pendingSupportArtist) return;
    supportArtist(
      pendingSupportArtist.artist.owner_username,
      pendingSupportArtist.profession,
      selectedSupportTierId,
      selectedSupportEmailShare
    );
  }

  async function saveGlobalEmailSharing(value) {
    const res = await apiFetch("/accounts/email-preferences/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ share_email_with_supported_artists: value }),
    });
    const data = await res.json();

    if (!res.ok) {
      setMessage(data.error || "Unable to update email sharing.");
      return;
    }

    setCurrentUser(data.user);
    setMessage(value ? "Email sharing enabled for future supported artists." : "Email sharing revoked.");
    loadFanEmailSharing();
    loadMailingList();
  }

  async function saveDiscoveryLocation(location) {
    const res = await apiFetch("/accounts/email-preferences/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ discovery_location: location }),
    });
    const data = await res.json();

    if (!res.ok) {
      setMessage(data.error || "Unable to update your city.");
      return;
    }

    setCurrentUser(data.user);
    setMessage("Discovery city updated.");
  }

  async function saveDiscoveryPreferences(prefs) {
    const res = await apiFetch("/accounts/email-preferences/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(prefs),
    });
    const data = await res.json();

    if (!res.ok) {
      setMessage(data.error || "Unable to update discovery preferences.");
      return;
    }

    setCurrentUser(data.user);
    setMessage("Discovery preferences updated.");
    if (isListenDiscoverBrowse(activePage, listenTab, discoverView)) {
      if (discoveryMode === "songs") {
        loadDiscoveryTracks({ backfill: Boolean(currentUser) });
      } else {
        loadDiscovery({ backfill: Boolean(currentUser) });
      }
    }
  }

  async function loadFansAlsoSupport(artist) {
    if (!artist?.owner_id) {
      setFansAlsoSupport([]);
      return;
    }
    const data = await fetchJson(`/artists/fans-also-support/?artist_id=${artist.owner_id}`, { results: [] });
    setFansAlsoSupport(data?.results || []);
  }

  async function loadPromotionPlacements(surface, artistId = null) {
    if (!currentUser || currentUser.is_artist || currentUser.is_host) {
      if (surface === "home") setHomePromotionPlacements([]);
      if (surface === "artist_page") setArtistPromotionPlacements([]);
      return;
    }

    const params = new URLSearchParams({ surface });
    if (artistId) params.set("artist_id", String(artistId));
    const data = await fetchJson(`/promotions/placements/?${params.toString()}`, { results: [] });
    const results = data?.results || [];
    if (surface === "home") {
      setHomePromotionPlacements(results);
    } else {
      setArtistPromotionPlacements(results);
    }
  }

  async function uploadProfileMedia(kind, file) {
    if (!file) return;

    if (!file.type?.startsWith("image/")) {
      setMessage("Please choose an image file.");
      return;
    }

    const formData = new FormData();
    formData.append(kind, file);

    const res = await apiFetch("/accounts/profile-media/", {
      method: "POST",
      body: formData,
    });
    const data = await res.json();

    if (!res.ok) {
      setMessage(data.error || "Unable to upload image.");
      return;
    }

    setCurrentUser(data.user);
    setMessage(kind === "avatar" ? "Profile photo updated." : "Cover photo updated.");
    if (currentUser?.is_artist) loadData();
  }

  async function saveFanEmailSharing(artistId, emailShared) {
    const res = await apiFetch("/artists/fan-email-sharing/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ artist_id: artistId, email_shared: emailShared }),
    });
    const data = await res.json();

    if (!res.ok) {
      setMessage(data.error || "Unable to update artist email sharing.");
      return;
    }

    setFanEmailSharing(data.results || []);
    setMessage(emailShared ? "Email shared with this artist." : "Email sharing revoked for this artist.");
    loadMailingList();
  }

  function exportMailingList() {
    window.location.href = `${API}/artists/mailing-list/?export=csv`;
  }

  function getArtistPublicUrl(ref = "", artist = selectedArtist, profession = activeProfession) {
    const username = artist?.owner_username || currentUser?.username || "";
    const resolvedProfession = artist ? resolveArtistProfession(artist, profession) : profession;
    const params = new URLSearchParams({ artist: username });
    if (resolvedProfession) params.set("profession", resolvedProfession);
    if (ref) params.set("ref", ref);
    return `${window.location.origin}${window.location.pathname}?${params.toString()}`;
  }

  function getArtistInviteUrl(artist = selectedArtist) {
    const username = artist?.owner_username || currentUser?.username || "";
    return getArtistPublicUrl(`invite_${username}`, artist);
  }

  async function copyText(value, successMessage = "Copied.") {
    try {
      await navigator.clipboard.writeText(value);
      setMessage(successMessage);
    } catch {
      setMessage(value);
    }
  }

  async function copyArtistInviteLink() {
    if (!hasPreviewedPublicPage(currentUser?.id)) {
      setShowPreviewBeforeShare(true);
      return;
    }
    markInviteLinkShared(currentUser?.id);
    await copyText(getArtistInviteUrl(), "Invite link copied.");
  }

  function startPublicPagePreview() {
    const artist = getCurrentArtist();
    if (!artist || !currentUser?.id) return;
    markPreviewedPublicPage(currentUser.id);
    setShowPreviewBeforeShare(false);
    setPreviewAsFan(true);
    setSelectedArtist(artist);
    setActiveProfession(getDefaultProfession(artist));
    setActiveTab("listen");
    setActivePage("home");
    window.history.pushState({}, "", getArtistPublicUrl("", artist));
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function dismissSetupChecklist() {
    if (!currentUser?.id) return;
    const role = currentUser.is_artist ? "artist" : currentUser.is_host ? "host" : "fan";
    dismissSetup(currentUser.id, role);
    setSetupChecklistDismissed(true);
  }

  async function shareArtistPageLink(ref = "") {
    copyText(getArtistPublicUrl(ref), "Public page link copied.");
  }

  async function copyProductLink(product, artist = selectedArtist) {
    const url = buildProductPageUrl(product, {
      artistUsername: artist?.owner_username || product.artist_username || currentUser?.username || "",
      profession: product.profession || activeProfession,
    });
    await copyText(url, "Product link copied.");
  }

  function openExternalSocial(url, provider = "social platform") {
    if (!url) return;

    if (askBeforeExternalSocial) {
      setPendingExternalLink({ url, provider });
      return;
    }

    window.open(url, "_blank", "noopener,noreferrer");
  }

  function saveExternalSocialPreference(value) {
    setAskBeforeExternalSocial(value);
    window.localStorage.setItem("askBeforeExternalSocial", value ? "true" : "false");
  }

  function saveHideSocialEmbedsPreference(value) {
    setHideSocialEmbeds(value);
    window.localStorage.setItem("hideSocialEmbeds", value ? "true" : "false");
  }

  function renderExternalLinkConfirm() {
    return (
      <>
        <ExternalLinkConfirm
          askBeforeExternalSocial={askBeforeExternalSocial}
          link={pendingExternalLink}
          onClose={() => setPendingExternalLink(null)}
          onPreferenceChange={saveExternalSocialPreference}
          onOpen={() => {
            window.open(pendingExternalLink.url, "_blank", "noopener,noreferrer");
            setPendingExternalLink(null);
          }}
        />
        {showPreviewBeforeShare && (
          <PreviewBeforeShareSheet
            onClose={() => setShowPreviewBeforeShare(false)}
            onPreview={startPublicPagePreview}
          />
        )}
      </>
    );
  }

  function renderPlaylistPicker() {
    return (
      <PlaylistPickerSheet
        track={playlistPickerTrack}
        playlists={fanPlaylists}
        onClose={() => setPlaylistPickerTrack(null)}
        onCreatePlaylist={handlePlaylistPickerCreate}
        onSelectPlaylist={handlePlaylistPickerSelect}
        onOpenArtist={openArtistByUsername}
      />
    );
  }

  async function resolveArtistOwnerId(artist) {
    if (!artist) return null;
    if (artist.owner_id) return artist.owner_id;

    const username = artist.owner_username;
    if (!username) return null;

    const fromList = artists.find(entry => entry.owner_username === username);
    if (fromList?.owner_id) return fromList.owner_id;

    const meta = await fetchJson(`/artists/public/${encodeURIComponent(username)}/`, null);
    if (!meta?.owner_id) return null;

    const patch = {
      owner_id: meta.owner_id,
      profession_keys: meta.profession_keys || artist.profession_keys,
    };
    setArtists(current =>
      current.map(entry => (entry.owner_username === username ? { ...entry, ...patch } : entry))
    );
    if (selectedArtist?.owner_username === username) {
      setSelectedArtist(current => (current ? { ...current, ...patch } : current));
    }
    return meta.owner_id;
  }

  async function sendDiscoverySignal(artist, signalType) {
    if (!currentUser) {
      setMessage("Log in before personalizing discovery.");
      return;
    }

    const ownerId = await resolveArtistOwnerId(artist);
    if (!ownerId) {
      setMessage("Unable to load this artist. Refresh and try again.");
      return;
    }

    const res = await apiFetch("/discovery/signal/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        artist_id: ownerId,
        signal_type: signalType,
        referral_source: referralSource,
      }),
    });
    const data = await res.json();

    if (!res.ok) {
      setMessage(data.error || "Unable to save discovery signal.");
      return;
    }

    const labels = {
      save: selectedArtist?.owner_id === artist.owner_id
        ? `You're following ${artist.stage_name}.`
        : "Saved. Discovery will keep this artist in mind.",
      skip: "Skipped. This artist will be hidden from your recommendations.",
      more_like_this: `Finding artists similar to ${artist.stage_name}.`,
    };

    setMessage(labels[signalType] || data.message || "Discovery updated.");
    if (activePage === "listen" && listenTab === "discover") {
      setLastReviewAction({ artist, signalType });
    }
    if (signalType === "skip") {
      if (!skipUndoDismissed) {
        setLastSkippedArtist(artist);
      }
      setDiscoveryArtists(currentArtists => currentArtists.filter(item => item.owner_id !== artist.owner_id));
      await loadDiscovery({ backfill: true });
    } else if (signalType === "save") {
      setDiscoveryArtists(currentArtists => currentArtists.filter(item => item.owner_id !== artist.owner_id));
      setReviewIndex(0);
      await loadDiscovery({ backfill: true });
    } else if (signalType === "more_like_this") {
      const discoveryData = await loadDiscovery({ backfill: true });
      const results = discoveryData?.results || [];
      const nextIndex = results.findIndex(item => item.owner_id !== artist.owner_id);
      setReviewIndex(nextIndex >= 0 ? nextIndex : 0);
    } else {
      if (activePage === "listen" && listenTab === "discover") {
        advanceReview();
      }
      await loadDiscovery({ backfill: true });
    }
    loadSavedArtists();
    if (signalType === "save") {
      loadData();
    }
  }

  async function sendDiscoveryTrackSignal(track, signalType) {
    if (!currentUser) {
      setMessage("Log in before personalizing discovery.");
      return;
    }

    const res = await apiFetch("/discovery/track-signal/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        track_id: track.id,
        signal_type: signalType,
      }),
    });
    const data = await res.json();

    if (!res.ok) {
      setMessage(data.error || "Unable to save track signal.");
      return;
    }

    setMessage(
      signalType === "save"
        ? `Saved ${track.title} to My Playlists.`
        : "Skipped. This song will stay out of your track recommendations."
    );

    if (signalType === "skip") {
      setLastSkippedTrack(track);
      setDiscoveryTracks(currentTracks => currentTracks.filter(item => item.id !== track.id));
      await loadDiscoveryTracks({ backfill: true });
    } else {
      setDiscoveryTracks(currentTracks => currentTracks.filter(item => item.id !== track.id));
      setReviewIndex(0);
      await loadDiscoveryTracks({ backfill: true });
      if (data.playlist) {
        apiFetch("/media/playlists/")
          .then(r => r.ok ? r.json() : { results: [] })
          .then(playlistData => {
            const playlists = playlistData.results || [];
            setFanPlaylists(playlists);
            setSelectedPlaylistId(current => current || playlists[0]?.id || "");
          });
      }
    }
  }

  async function undoLastTrackSkip() {
    if (!lastSkippedTrack) return;

    const res = await apiFetch("/discovery/undo-track-skip/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ track_id: lastSkippedTrack.id }),
    });
    const data = await res.json();

    if (!res.ok) {
      setMessage(data.error || "Unable to undo track skip.");
      return;
    }

    setMessage(`${lastSkippedTrack.title} is back in discovery.`);
    setLastSkippedTrack(null);
    await loadDiscoveryTracks({ backfill: true });
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
    setSearchProfession("");
    loadDiscovery({ backfill: true });
  }

  async function manageSupport(username, profession = activeProfession) {
    if (!currentUser) {
      setMessage("Log in before managing support.");
      return;
    }

    const artist = artists.find(a => a.owner_username === username);
    if (!artist) return;

    const res = await apiFetch("/subscriptions/billing-portal/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ artist_id: artist.owner_id, profession }),
    });
    const data = await res.json();

    if (!res.ok) {
      if ((data.error || "").includes("Stripe is not configured")) {
        setMessage("Beta support is active locally. Stripe billing management will open here once production payments are configured.");
      } else {
        setMessage(data.error || "Unable to open subscription management.");
      }
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
    formData.append("profession", activeProfession);

    const res = await apiFetch("/posts/create/", {
      method: "POST",
      body: formData,
    });

    const data = await res.json();
    if (!res.ok) {
      setMessage(data.error || data.message || "Unable to save post.");
      return;
    }

    if (data.post) {
      setPosts(current => {
        const exists = current.some(post => post.id === data.post.id);
        return exists ? current : [data.post, ...current];
      });
    }

    form.reset();
    setShowPostForm(false);
    setMessage(data.message || "Post created.");
    await Promise.all([loadData(), loadArtistDashboard()]);
  }

  async function createPointOfView(event) {
    event.preventDefault();

    const form = event.target;
    const formData = new FormData(form);
    formData.append("profession", activeProfession);
    formData.append("is_pinned", "true");

    const res = await apiFetch("/posts/pov/", {
      method: "POST",
      body: formData,
    });
    const data = await res.json();

    if (res.ok) {
      form.reset();
      setShowPovForm(false);
    }

    setMessage(data.message || data.error || "Point of view saved.");
    loadData();
    loadArtistDashboard();
  }

  async function createInstant(event) {
    event.preventDefault();

    const form = event.target;
    const formData = new FormData(form);

    const res = await apiFetch("/posts/instants/", {
      method: "POST",
      body: formData,
    });
    const data = await res.json();

    if (res.ok) {
      form.reset();
      setShowInstantForm(false);
    }

    setMessage(data.message || data.error || "Instant posted.");
    loadData();
    loadArtistDashboard();
  }

  async function saveCalendarItem(event) {
    event.preventDefault();

    const { starts_at: startsAt, ends_at: endsAt, hasStartDate } = calendarDateValuesRef.current;
    if (!hasStartDate || !startsAt) {
      setMessage("Pick a start date on the calendar.");
      return;
    }

    if (endsAt && new Date(endsAt) < new Date(startsAt)) {
      setMessage("End date must be after the start date.");
      return;
    }

    const form = event.target;
    const formData = new FormData(form);
    formData.set("starts_at", startsAt);
    formData.set("ends_at", endsAt || "");
    formData.set("profession", activeProfession);

    const res = await apiFetch("/artists/calendar/", {
      method: "POST",
      body: formData,
    });
    let data = {};
    try {
      data = await res.json();
    } catch {
      setMessage("Unable to save calendar item.");
      return;
    }

    if (res.ok) {
      form.reset();
      calendarDateValuesRef.current = { starts_at: "", ends_at: "", hasStartDate: false, hasEndDate: false };
      setShowCalendarForm(false);
      setMessage(data.message || "Calendar item saved.");
    } else {
      setMessage(data.error || data.message || "Unable to save calendar item.");
    }

    loadData();
    loadArtistDashboard();
  }

  async function saveHostProfile(event) {
    event.preventDefault();

    const payload = Object.fromEntries(new FormData(event.target).entries());
    const res = await apiFetch("/spaces/host-profile/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    if (res.ok) {
      setSpaceHostProfile(data.profile);
    }
    setMessage(data.message || data.error || "Host profile saved.");
    loadSpaces();
  }

  async function saveSpaceListing(event) {
    event.preventDefault();

    const form = event.target;
    const availability = slotsToWindows(spaceAvailabilitySlots);
    if (availability.length === 0) {
      setMessage("Add at least one open date before saving.");
      return;
    }

    const formData = new FormData(form);
    formData.set("bar_open", form.bar_open?.checked ? "true" : "false");
    formData.set("kitchen_open", form.kitchen_open?.checked ? "true" : "false");
    formData.set("available_windows", JSON.stringify(availability));

    spacePhotoRows.forEach(row => {
      const fileInput = form.querySelector(`input[data-photo-row="${row.id}"]`);
      if (fileInput?.files?.[0]) {
        formData.append("photos", fileInput.files[0]);
        formData.append("photo_types", row.photo_type);
        formData.append("photo_captions", row.caption || "");
      }
    });

    const res = await apiFetch("/spaces/listings/", {
      method: "POST",
      body: formData,
    });
    const data = await res.json();

    if (res.ok) {
      form.reset();
      closeSpaceListingForm();
    }

    setMessage(data.message || data.error || "Space listing saved.");
    loadSpaces();
  }

  function closeSpaceListingForm() {
    setShowSpaceListingForm(false);
    setSpaceAvailabilitySlots([]);
    setSpacePhotoRows([
      { id: 1, photo_type: "stage", caption: "" },
      { id: 2, photo_type: "audience", caption: "" },
    ]);
  }

  function renderSpaceListingModal() {
    if (!showSpaceListingForm || !currentUser?.is_host) return null;

    return (
      <SpaceListingWizard
        defaultCity={spaceHostProfile?.city || currentUser?.discovery_location || ""}
        photoTypeLabels={SPACE_PHOTO_TYPE_LABELS}
        spaceAvailabilitySlots={spaceAvailabilitySlots}
        onAvailabilityChange={setSpaceAvailabilitySlots}
        spacePhotoRows={spacePhotoRows}
        onAddPhoto={addSpacePhotoRow}
        onUpdatePhoto={updateSpacePhotoRow}
        onRemovePhoto={removeSpacePhotoRow}
        onClose={closeSpaceListingForm}
        onSubmit={saveSpaceListing}
      />
    );
  }

  function addSpacePhotoRow() {
    setSpacePhotoRows(rows => {
      if (rows.length >= 8) return rows;
      const nextId = rows.reduce((max, row) => Math.max(max, row.id), 0) + 1;
      return [...rows, { id: nextId, photo_type: "room_overview", caption: "" }];
    });
  }

  function updateSpacePhotoRow(rowId, field, value) {
    setSpacePhotoRows(rows => rows.map(row => (row.id === rowId ? { ...row, [field]: value } : row)));
  }

  function removeSpacePhotoRow(rowId) {
    setSpacePhotoRows(rows => (rows.length <= 1 ? rows : rows.filter(row => row.id !== rowId)));
  }

  function openSpaceBookingForm(listingId) {
    setSpaceBookingListingId(listingId);
    spaceBookingDateValuesRef.current = { starts_at: "", ends_at: "", hasStartDate: false, hasEndDate: false };
    requestAnimationFrame(() => {
      spaceBookingPanelRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
    });
  }

  async function requestSpaceBooking(event, listingId) {
    event.preventDefault();

    if (!currentUser?.is_artist) {
      setMessage("Artist account required to request a booking.");
      return;
    }

    const listing = spaceListings.find(item => item.id === listingId);
    const { starts_at: startsAt, ends_at: endsAt, hasStartDate, hasEndDate } = spaceBookingDateValuesRef.current;
    if (!hasStartDate || !startsAt) {
      setMessage("Pick an available date from the host schedule.");
      return;
    }
    if (!hasEndDate || !endsAt) {
      setMessage("Pick start and end times within the host window.");
      return;
    }

    const windowError = validateBookingWindow({
      dateValue: startsAt.split("T")[0],
      startTime: startsAt.split("T")[1],
      endTime: endsAt.split("T")[1],
      availableWindows: listing?.available_windows || [],
    });
    if (windowError) {
      setMessage(windowError);
      return;
    }

    if (new Date(endsAt) <= new Date(startsAt)) {
      setMessage("End time must be after the start time.");
      return;
    }

    const payload = Object.fromEntries(new FormData(event.target).entries());
    payload.listing_id = listingId;
    payload.starts_at = startsAt;
    payload.ends_at = endsAt;
    payload.publish_to_calendar = true;

    const res = await apiFetch("/spaces/bookings/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    let data = {};
    try {
      data = await res.json();
    } catch {
      setMessage("Unable to submit booking request.");
      return;
    }

    if (res.ok) {
      event.target.reset();
      spaceBookingDateValuesRef.current = { starts_at: "", ends_at: "", hasStartDate: false, hasEndDate: false };
      setSpaceBookingListingId(null);
      setMessage(data.message || "Booking requested.");
    } else if (data.error && /local supporter/i.test(data.error)) {
      setMessage(`${data.error} Grow local fans in Profile → set your city, then ask supporters in that city to subscribe.`);
    } else {
      setMessage(data.error || data.message || "Unable to submit booking request.");
    }
    loadSpaces();
  }

  async function dismissSpaceBooking(bookingId) {
    const res = await apiFetch(`/spaces/bookings/${bookingId}/dismiss/`, { method: "POST" });
    let data = {};
    try {
      data = await res.json();
    } catch {
      data = { error: "Unexpected server response." };
    }
    if (res.ok) {
      setSpaceBookings(prev => prev.filter(item => item.id !== bookingId));
      setMessage(data.message || "Removed from list.");
      return true;
    }
    setMessage(data.error || data.message || "Could not remove booking.");
    return false;
  }

  async function clearSpaceBookings(scope = "all") {
    const res = await apiFetch("/spaces/bookings/clear/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ scope }),
    });
    let data = {};
    try {
      data = await res.json();
    } catch {
      data = { error: "Unexpected server response." };
    }
    if (res.ok) {
      if (scope === "history") {
        setSpaceBookings(prev => prev.filter(item => item.status === "requested"));
      } else {
        setSpaceBookings([]);
      }
      setMessage(data.message || "Booking list cleared.");
      await loadSpaces();
      return true;
    }
    setMessage(data.error || data.message || "Could not clear bookings.");
    return false;
  }

  function renderSpaceBookingDismissButton(bookingId, label = "Remove from list") {
    return (
      <button
        className="space-booking-dismiss"
        type="button"
        aria-label={label}
        onClick={() => dismissSpaceBooking(bookingId)}
      >
        ×
      </button>
    );
  }

  async function updateSpaceBookingStatus(bookingId, nextStatus, attendance = "", options = {}) {
    const res = await apiFetch(`/spaces/bookings/${bookingId}/status/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        status: nextStatus,
        attendance_checked_in: attendance,
        publish_to_calendar: nextStatus === "confirmed",
      }),
    });

    let data = {};
    try {
      data = await res.json();
    } catch {
      data = { error: "Unexpected server response." };
    }

    if (res.ok) {
      setMessage(data.message || "Booking updated.");
      if (data.booking) {
        setSpaceBookings(prev => prev.map(item => (
          item.id === bookingId ? { ...item, ...data.booking } : item
        )));
      }
      await loadSpaces();
      loadArtistDashboard();
      loadData();
      if (options.openReviewAfter && currentUser?.is_host && nextStatus === "completed") {
        const booking = data.booking || findSpaceBooking(bookingId);
        openSpaceReviewModal(bookingId, currentUser, booking?.artist_name || "the artist");
      }
      return true;
    }

    setMessage(data.error || data.message || "Booking update failed.");
    return false;
  }

  function findSpaceBooking(bookingId) {
    return spaceBookings.find(item => item.id === bookingId) || null;
  }

  function resolveSpaceReviewTarget(user, bookingId, label = "") {
    if (user?.is_host) {
      return { bookingId, revieweeType: "artist", label: label || "the artist" };
    }
    if (user?.is_artist) {
      return { bookingId, revieweeType: "host", label: label || "the venue" };
    }
    return { bookingId, revieweeType: "show", label: label || "the show" };
  }

  function openSpaceReviewModal(bookingId, user = currentUser, label = "") {
    if (!bookingId || !user) return;
    const booking = findSpaceBooking(bookingId);
    const existingReview = user.is_host
      ? booking?.my_reviews?.artist
      : user.is_artist
        ? booking?.my_reviews?.host
        : booking?.my_reviews?.show;
    setSpaceReviewError("");
    setSpaceReviewSaving(false);
    setSpaceReviewRating(existingReview?.rating || 5);
    setSpaceReviewComment(existingReview?.comment || "");
    setSpaceReviewTarget(resolveSpaceReviewTarget(user, bookingId, label));
  }

  async function completeBookingForReview(bookingId) {
    const booking = findSpaceBooking(bookingId);
    if (!booking || booking.status === "completed") return;
    setSpaceReviewSaving(true);
    setSpaceReviewError("");
    const ok = await updateSpaceBookingStatus(
      bookingId,
      "completed",
      booking.expected_audience || booking.attendance_checked_in || 0,
      { openReviewAfter: false },
    );
    setSpaceReviewSaving(false);
    if (!ok) {
      setSpaceReviewError("Could not mark this gig complete. Try again from the host dashboard.");
    } else {
      setSpaceReviewError("");
    }
  }

  function resetSpaceReviewModal() {
    setSpaceReviewTarget(null);
    setSpaceReviewError("");
    setSpaceReviewRating(5);
    setSpaceReviewComment("");
  }

  function closeSpaceReviewModal() {
    if (spaceReviewSaving) return;
    resetSpaceReviewModal();
  }

  async function submitSpaceReview(event) {
    event.preventDefault();
    if (!spaceReviewTarget || spaceReviewSaving) return;

    const comment = spaceReviewComment.trim();
    if (!comment) {
      setSpaceReviewError("Add a short comment before saving your review.");
      return;
    }

    setSpaceReviewSaving(true);
    setSpaceReviewError("");

    try {
      const res = await apiFetch(`/spaces/bookings/${spaceReviewTarget.bookingId}/reviews/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          reviewee_type: spaceReviewTarget.revieweeType,
          rating: Number(spaceReviewRating),
          comment,
        }),
      });

      let data = {};
      try {
        data = await res.json();
      } catch {
        data = { error: "Unexpected server response. Try again." };
      }

      if (res.ok) {
        resetSpaceReviewModal();
        setMessage(data.message || "Review saved.");
        loadSpaces();
        return;
      }

      setSpaceReviewError(data.error || data.message || "Unable to save review.");
      if (/completed/i.test(data.error || data.message || "")) {
        setSpaceReviewError(
          (data.error || data.message || "Reviews are available after the gig is completed.")
          + " Mark the gig complete first, then save your review.",
        );
      }
    } catch {
      setSpaceReviewError("Network error. Check your connection and try again.");
    } finally {
      setSpaceReviewSaving(false);
    }
  }

  function renderSpaceReviewModal() {
    if (!spaceReviewTarget) return null;

    const booking = findSpaceBooking(spaceReviewTarget.bookingId);
    const needsComplete = booking && booking.status !== "completed" && currentUser?.is_host && spaceReviewTarget.revieweeType === "artist";
    const existingReview = currentUser?.is_host
      ? booking?.my_reviews?.artist
      : currentUser?.is_artist
        ? booking?.my_reviews?.host
        : booking?.my_reviews?.show;

    return (
      <div className="modal-backdrop" role="presentation" onClick={closeSpaceReviewModal}>
        <section
          className="support-sheet space-review-sheet"
          role="dialog"
          aria-modal="true"
          aria-labelledby="space-review-title"
          onClick={event => event.stopPropagation()}
        >
          <button className="sheet-close" type="button" onClick={closeSpaceReviewModal} aria-label="Close review form" disabled={spaceReviewSaving}>
            ×
          </button>
          <form className="auth-form space-review-form" onSubmit={submitSpaceReview}>
            <h2 id="space-review-title">Review {spaceReviewTarget.label}</h2>
            <p className="muted">
              {existingReview
                ? "Update your review anytime. Changes save immediately."
                : "Share how the gig went. Your review helps artists and venues build trust."}
            </p>
            {needsComplete && (
              <p className="form-error" role="status">
                This gig is still marked confirmed. Mark it complete before saving your artist review.
              </p>
            )}
            <label>
              Rating
              <select value={spaceReviewRating} onChange={event => setSpaceReviewRating(event.target.value)} disabled={spaceReviewSaving}>
                {[5, 4, 3, 2, 1].map(value => (
                  <option value={value} key={value}>{value} star{value === 1 ? "" : "s"}</option>
                ))}
              </select>
            </label>
            <label>
              Comment
              <textarea
                value={spaceReviewComment}
                onChange={event => {
                  setSpaceReviewComment(event.target.value);
                  if (spaceReviewError) setSpaceReviewError("");
                }}
                placeholder="How was the turnout, room, and experience?"
                disabled={spaceReviewSaving}
              />
            </label>
            {spaceReviewError && <p className="form-error" role="alert">{spaceReviewError}</p>}
            <div className="sheet-actions">
              <button className="secondary" type="button" onClick={closeSpaceReviewModal} disabled={spaceReviewSaving}>Cancel</button>
              {needsComplete ? (
                <button className="primary" type="button" disabled={spaceReviewSaving} onClick={() => completeBookingForReview(spaceReviewTarget.bookingId)}>
                  {spaceReviewSaving ? "Marking complete…" : "Mark complete & continue"}
                </button>
              ) : (
                <button className="primary" type="submit" disabled={spaceReviewSaving}>
                  {spaceReviewSaving ? "Saving…" : existingReview ? "Update review" : "Save review"}
                </button>
              )}
            </div>
          </form>
        </section>
      </div>
    );
  }

  function ownedTicketProductIds() {
    return new Set((myPurchases.tickets || []).map(item => item.product_id));
  }

  async function purchaseProduct(product, showContext = null) {
    if (!currentUser) {
      setMessage("Log in to purchase.");
      return;
    }

    if (ownedTicketProductIds().has(product.id)) {
      setMessage("You already have a ticket for this show. See Profile → My tickets.");
      return;
    }

    const res = await apiFetch("/marketplace/checkout/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        product_id: product.id,
        apply_discovery_credits: applyDiscoveryCredits && Number(promotionWallet?.balance || 0) > 0,
      }),
    });
    const data = await res.json();
    if (res.status === 409 && data.already_purchased) {
      setMessage("You already have a ticket for this show. See Profile → My tickets.");
      loadMyPurchases();
      return;
    }
    if (res.status === 409 && data.sold_out) {
      setMessage("This show is sold out.");
      return;
    }
    if (res.status === 403 && data.presale_only) {
      setMessage("Tickets are in supporter presale. Support this artist to buy now.");
      if (data.artist_username) {
        openArtistByUsername(data.artist_username);
      }
      return;
    }
    if (data.checkout_url) {
      window.location.href = data.checkout_url;
      return;
    }
    if (res.ok) {
      const receipt = data.receipt || data;
      const show = receipt.show || showContext;
      if (data.discovery_credits_applied && Number(data.discovery_credits_applied) > 0) {
        loadPromotionData();
      }
      if (show) {
        setMessage(
          `Ticket confirmed: ${receipt.product_title || product.title}${Number(receipt.amount || product.price) > 0 ? ` · $${receipt.amount || product.price}` : ""} for ${show.stage_name || show.venue_name}. Tap I'm here when you arrive.`
        );
        goToPage("my-scene", true, { show: show.booking_id });
      } else {
        setMessage(`Purchase confirmed: ${receipt.product_title || product.title} · $${receipt.amount || product.price}.`);
      }
      loadMyPurchases();
      loadNotifications();
      loadArtistDashboard();
      return;
    }
    setMessage(data.error || data.detail || data.message || "Purchase failed.");
  }

  function parseNotificationTarget(targetUrl = "") {
    const query = targetUrl.includes("?") ? targetUrl.split("?")[1] : targetUrl.replace(/^\/?\?/, "");
    return new URLSearchParams(query);
  }

  async function openNotification(item) {
    if (!item) return;

    const rawId = item.notificationId || String(item.id || "").replace(/^stored-/, "");
    if (rawId && notificationData.results.length > 0) {
      await apiFetch("/notifications/mark-read/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id: Number(rawId) }),
      });
      loadNotifications();
    }

    const params = parseNotificationTarget(item.target_url || "");
    const page = params.get("page");
    const show = params.get("show");
    const artistUsername = params.get("artist");

    if (page === "my-scene") {
      goToMyScene(show || null);
      return;
    }
    if (artistUsername) {
      await openArtistByUsername(artistUsername);
      return;
    }
    const reviewBookingId = params.get("review_booking");
    if (reviewBookingId && currentUser) {
      goToPage("spaces");
      openSpaceReviewModal(Number(reviewBookingId), currentUser);
      return;
    }

    if (page && FAN_PAGES.has(page)) {
      goToPage(page);
    }
  }

  async function notifyLocalSupporters(bookingId) {
    const res = await apiFetch(`/spaces/bookings/${bookingId}/notify-local-supporters/`, { method: "POST" });
    const data = await res.json();
    setMessage(data.message || data.error || "Local supporters notified.");
  }

  async function reportInstant(instantId) {
    if (!currentUser) {
      setMessage("Log in before reporting Instants.");
      return;
    }

    const res = await apiFetch(`/posts/instants/${instantId}/report/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ reason: "Reported from profile" }),
    });
    const data = await res.json();
    setMessage(data.message || data.error || "Report saved.");
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
    formData.append("profession", activeProfession);

    const res = await apiFetch("/marketplace/create/", {
      method: "POST",
      body: formData,
    });

    const data = await res.json();
    setMessage(data.message || data.error || "Product saved.");
    setStoreFormType(null);
    if (res.ok && data.release_approval_id) {
      setPendingRelease({
        id: data.release_approval_id,
        content_title: data.title,
        file_name: data.title,
      });
    }
    loadData();
  }

  async function sendLiveChatMessage(event) {
    event.preventDefault();

    const body = liveChatMessage.trim();
    if (!body) return;

    if (activeLiveSession?.id) {
      const res = await apiFetch(`/live/${activeLiveSession.id}/chat/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ body }),
      });
      const data = await res.json();

      if (!res.ok) {
        setMessage(data.error || "Unable to send chat message.");
        return;
      }

      setLiveChatMessages(messages => [
        ...messages,
        {
          id: data.message.id,
          name: data.message.author_username,
          role: data.message.author_role,
          body: data.message.body,
        },
      ]);
      setLiveChatMessage("");
      return;
    }

    setLiveChatMessages(messages => [
      ...messages,
      {
        id: Date.now(),
        name: currentUser?.username || "guest",
        role: currentUser?.is_artist ? "Artist" : "Fan",
        body,
      },
    ]);
    setLiveChatMessage("");
  }

  async function enableLiveCamera(deviceId = selectedCameraId) {
    if (!navigator.mediaDevices?.getUserMedia) {
      setCameraStatus("Camera access is not supported in this browser.");
      return;
    }

    try {
      if (livePreviewRef.current?.srcObject) {
        livePreviewRef.current.srcObject.getTracks().forEach(track => track.stop());
      }

      const stream = await navigator.mediaDevices.getUserMedia({
        video: deviceId ? { deviceId: { exact: deviceId } } : true,
        audio: true,
      });

      if (livePreviewRef.current) {
        livePreviewRef.current.srcObject = stream;
      }

      const devices = await navigator.mediaDevices.enumerateDevices();
      const videoInputs = devices.filter(device => device.kind === "videoinput");
      setCameraDevices(videoInputs);

      if (!deviceId && videoInputs[0]?.deviceId) {
        setSelectedCameraId(videoInputs[0].deviceId);
      }

      setCameraStatus("Camera enabled for preview.");
    } catch (error) {
      setCameraStatus("Unable to access camera. Check browser permissions.");
    }
  }

  function stopLiveCamera() {
    if (livePreviewRef.current?.srcObject) {
      livePreviewRef.current.srcObject.getTracks().forEach(track => track.stop());
      livePreviewRef.current.srcObject = null;
    }
  }

  async function startLiveSession() {
    if (!livePreviewRef.current?.srcObject) {
      await enableLiveCamera();
    }

    const title = document.querySelector("[name='live_title']")?.value || "Live session";
    const description = document.querySelector("[name='live_description']")?.value || "";
    const accessMode = document.querySelector("[name='live_access_mode']")?.value || "preview_30";
    const res = await apiFetch("/live/start/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title, description, access_mode: accessMode }),
    });
    const data = await res.json();

    if (!res.ok) {
      setMessage(data.error || "Unable to start live session.");
      return;
    }

    setActiveLiveSession(data.session);
    setLiveChatMessages((data.session.messages || []).map(chat => ({
      id: chat.id,
      name: chat.author_username,
      role: chat.author_role,
      body: chat.body,
    })));
    setIsLive(true);
    loadData();
    loadArtistDashboard();
    loadNotifications();
    setCameraStatus("Live now. Your camera preview is active.");
  }

  async function stopLiveSession() {
    if (activeLiveSession?.id) {
      const res = await apiFetch(`/live/${activeLiveSession.id}/stop/`, { method: "POST" });
      const data = await res.json();

      if (!res.ok) {
        setMessage(data.error || "Unable to stop live session.");
        return;
      }
    }

    setIsLive(false);
    setActiveLiveSession(null);
    loadData();
    stopLiveCamera();
    setCameraStatus("Live stopped. Camera turned off.");
  }

  function closeLiveForm() {
    setShowLiveForm(false);
    setIsLive(false);
    stopLiveCamera();
    setCameraStatus("");
  }

  function isPurchasableProduct(product) {
    const purchasableTypes = new Set([
      "digital_download",
      "vinyl",
      "cassette",
      "beat",
      "merch",
      "sample_pack",
      "acapella",
      "stems",
      "midi_pack",
      "drum_kit",
      "preset_pack",
      "event_ticket",
      "membership_merch",
    ]);
    return Boolean(product?.can_access && purchasableTypes.has(product.product_type) && !product.external_url);
  }

  function isCartableProduct(product) {
    if (currentUser?.is_host) return false;
    return isPurchasableProduct(product) && product.product_type !== "event_ticket";
  }

  function persistStoreCart(items) {
    setStoreCart(items);
    localStorage.setItem(CART_STORAGE_KEY, JSON.stringify(items));
  }

  function addToCart(product) {
    if (currentUser?.is_host) return;
    if (!currentUser) {
      setMessage("Log in to add items to your cart.");
      return;
    }
    if (!isCartableProduct(product)) {
      setMessage("This item must be purchased directly.");
      return;
    }
    if (storeCart.some(item => item.id === product.id)) {
      setMessage(`${product.title} is already in your cart.`);
      setShowStoreCart(true);
      return;
    }
    const next = [...storeCart, {
      id: product.id,
      title: product.title,
      price: product.price,
      artist_username: product.artist_username,
      stage_name: product.stage_name,
      product_type: product.product_type,
    }];
    persistStoreCart(next);
    setMessage(`Added to cart: ${product.title}`);
    setShowStoreCart(true);
  }

  function removeFromCart(productId) {
    persistStoreCart(storeCart.filter(item => item.id !== productId));
  }

  async function checkoutCart() {
    if (!currentUser) {
      setMessage("Log in to checkout.");
      return;
    }
    if (storeCart.length === 0) {
      setMessage("Your cart is empty.");
      return;
    }

    const res = await apiFetch("/marketplace/cart-checkout/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ product_ids: storeCart.map(item => item.id) }),
    });
    const data = await res.json();
    if (data.checkout_url) {
      window.location.href = data.checkout_url;
      return;
    }
    if (res.ok) {
      persistStoreCart([]);
      setShowStoreCart(false);
      setMessage(data.message || `Cart purchase complete (${data.count || storeCart.length} items).`);
      loadMyPurchases();
      loadNotifications();
      loadArtistDashboard();
      return;
    }
    setMessage(data.error || "Cart checkout failed.");
  }

  function productTypeLabel(type) {
    if (type === "membership_merch") return "Subscriber Reward";
    if (type === "digital_download") return "Digital Music";
    if (type === "vinyl") return "Vinyl";
    if (type === "cassette") return "Cassette";
    if (type === "external_fulfillment") return "Linked Store";
    if (type === "gelato_pod") return "Gelato POD";
    if (type === "shopify_store") return "Shopify Store";
    if (type === "printify_pod") return "Printify POD";
    if (type === "fourthwall_store") return "Fourthwall Store";
    if (type === "bandcamp_store") return "Bandcamp Store";
    if (type === "printful_pod") return "Printful POD";
    if (type === "merch") return "Merch";
    if (type === "beat") return "Beat";
    if (type === "event_ticket") return "Event Ticket";
    if (type === "sample_pack") return "Sample Pack";
    if (type === "acapella") return "Acapella";
    return type;
  }


  async function uploadTrack(event) {
    event.preventDefault();

    const form = event.target;
    const formData = new FormData(form);
    formData.append("profession", activeProfession);

    if (trackCoverMode === "library") {
      formData.delete("cover_art");
      if (selectedLibraryCoverId) {
        formData.append("library_cover_id", selectedLibraryCoverId);
      }
    } else if (trackCoverMode === "none") {
      formData.delete("cover_art");
    } else if (saveCoverToLibrary) {
      formData.append("save_cover_to_library", "true");
    }

    const res = await apiFetch("/media/create/", {
      method: "POST",
      body: formData,
    });

    const data = await res.json();

    setMessage(data.message || data.error || "Track uploaded.");
    setShowMusicForm(false);
    setTrackCoverMode("upload");
    setSelectedLibraryCoverId("");
    setSaveCoverToLibrary(true);
    setAiDisclosureLevel("human_made");
    if (res.ok && data.release_approval_id) {
      setPendingRelease({
        id: data.release_approval_id,
        content_title: data.title,
        file_name: data.title,
        ai_usage_status: aiDisclosureLevel,
      });
    }
    loadData();
  }

  async function uploadSongCover(event) {
    event.preventDefault();

    const formData = new FormData(event.target);
    formData.append("profession", activeProfession);

    const res = await apiFetch("/media/cover-art/create/", {
      method: "POST",
      body: formData,
    });

    const data = await res.json();

    setMessage(data.message || data.error || "Cover art saved.");
    setShowSongCoverForm(false);
    event.target.reset();
    loadData();
  }

  async function setDefaultSongCover(coverId) {
    const res = await apiFetch(`/media/cover-art/${coverId}/set-default/`, {
      method: "POST",
    });
    const data = await res.json();

    setMessage(data.message || data.error || "Default cover updated.");
    loadData();
  }

  function getArtistSongCovers() {
    if (!currentUser?.is_artist) return [];

    return songCovers.filter(cover => (cover.profession || DEFAULT_PROFESSION) === activeProfession);
  }

  function renderSongCoverLibrary() {
    const covers = getArtistSongCovers();

    if (covers.length === 0) {
      return <p className="muted">Add saved covers here to reuse them on track uploads or as the fallback when a track has no cover.</p>;
    }

    return (
      <div className="cover-art-picker">
        {covers.map(cover => (
          <article className={`cover-art-option${cover.is_default ? " is-default" : ""}`} key={cover.id}>
            <img src={cover.image} alt={cover.label || "Saved cover"} />
            <div className="cover-art-meta">
              <strong>{cover.label || "Saved cover"}</strong>
              {cover.is_default ? (
                <span className="cover-art-badge">Default</span>
              ) : (
                <button type="button" className="secondary compact" onClick={() => setDefaultSongCover(cover.id)}>
                  Set default
                </button>
              )}
            </div>
          </article>
        ))}
      </div>
    );
  }

  async function uploadArtwork(event) {
    event.preventDefault();

    const form = event.target;
    const formData = new FormData(form);
    formData.append("profession", activeProfession);

    const res = await apiFetch("/media/artworks/create/", {
      method: "POST",
      body: formData,
    });

    const data = await res.json();

    setMessage(data.message || data.error || "Artwork uploaded.");
    if (res.ok) {
      setShowArtworkForm(false);
      form.reset();
    }
    loadData();
  }

  async function createFanPlaylist(event) {
    event.preventDefault();

    if (!currentUser) {
      setMessage("Log in before creating fan playlists.");
      return;
    }

    const form = event.target;
    const payload = Object.fromEntries(new FormData(form).entries());
    const playlist = await createFanPlaylistRequest(payload);

    if (!playlist) return;

    form.reset();
    setSelectedPlaylistId(playlist.id);
    setMyMusicSidebarView(String(playlist.id));
  }

  async function createFanPlaylistRequest(payload) {
    const res = await apiFetch("/media/playlists/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await res.json();

    if (!res.ok) {
      setMessage(data.error || "Unable to create playlist.");
      return null;
    }

    updatePlaylistInState(data.playlist);
    setMessage(data.message || "Playlist created.");
    return data.playlist;
  }

  function updatePlaylistInState(updatedPlaylist) {
    if (!updatedPlaylist) return;

    setFanPlaylists(current => {
      const exists = current.some(playlist => String(playlist.id) === String(updatedPlaylist.id));
      if (exists) {
        return current.map(playlist => (
          String(playlist.id) === String(updatedPlaylist.id) ? updatedPlaylist : playlist
        ));
      }
      return [updatedPlaylist, ...current];
    });
    setSelectedPlaylistId(updatedPlaylist.id);
  }

  function getMyMusicTracks() {
    const seen = new Set();
    const tracks = [];

    fanPlaylists.forEach(playlist => {
      (playlist.tracks || []).forEach(track => {
        if (!seen.has(track.id)) {
          seen.add(track.id);
          tracks.push(track);
        }
      });
    });

    return tracks;
  }

  function getMyMusicByArtist() {
    const groups = new Map();

    getMyMusicTracks().forEach(track => {
      const username = track.artist_username;
      if (!username) return;

      if (!groups.has(username)) {
        const artist = artistFromUsername(username);
        groups.set(username, {
          owner_username: username,
          stage_name: artist?.stage_name || username,
          is_verified: artist?.is_verified,
          hero_image: artist?.hero_image,
          owner_id: artist?.owner_id,
          tracks: [],
        });
      }

      groups.get(username).tracks.push(track);
    });

    return [...groups.values()]
      .map(group => ({
        ...group,
        tracks: group.tracks.sort((a, b) => a.title.localeCompare(b.title)),
      }))
      .sort((a, b) => a.stage_name.localeCompare(b.stage_name));
  }

  async function createPlaylistFromArtistSaves(group) {
    if (!currentUser) {
      setMessage("Log in before creating playlists.");
      return;
    }

    if (!group?.tracks?.length) return;

    const title = `${group.stage_name} – Saved`;
    const playlist = await createFanPlaylistRequest({
      title,
      description: `Songs you saved from ${group.stage_name}`,
    });
    if (!playlist) return;

    let latestPlaylist = playlist;
    for (const track of group.tracks) {
      const res = await apiFetch(`/media/playlists/${playlist.id}/add-track/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ track_id: track.id }),
      });
      const data = await res.json();
      if (res.ok && data.playlist) {
        latestPlaylist = data.playlist;
      }
    }

    updatePlaylistInState(latestPlaylist);
    setSelectedPlaylistId(latestPlaylist.id);
    setMyMusicSidebarView(String(latestPlaylist.id));
    setMessage(`Created playlist "${title}" with ${group.tracks.length} song${group.tracks.length === 1 ? "" : "s"}.`);
  }

  function getArtistListenMoreTracks(username) {
    const savedIds = new Set(
      getMyMusicByArtist().find(group => group.owner_username === username)?.tracks.map(track => track.id) || []
    );

    return music.filter(track =>
      track.artist_username === username &&
      track.audio_file &&
      !savedIds.has(track.id)
    );
  }

  function toggleMyMusicListenMore(username) {
    setMyMusicListenMoreOpen(current => ({
      ...current,
      [username]: !current[username],
    }));
  }

  function getPlaylistsContainingTrack(trackId) {
    return fanPlaylists.filter(playlist =>
      (playlist.tracks || []).some(track => track.id === trackId)
    );
  }

  async function removeSavedTrack(track) {
    const playlists = getPlaylistsContainingTrack(track.id);
    if (!playlists.length) {
      setMessage("Track is not in any of your playlists.");
      return;
    }

    for (const playlist of playlists) {
      await removeTrackFromPlaylist(track, playlist.id);
    }
  }

  function renderMyMusicTrackRow(track, options = {}) {
    const { showRemove = true } = options;

    return (
      <div className="my-music-track-row" key={track.id}>
        {track.cover_art ? (
          <img className="my-music-track-cover" src={track.cover_art} alt={track.title} />
        ) : (
          <div className="my-music-track-cover my-music-track-cover-fallback">{track.title?.[0]?.toUpperCase() || "?"}</div>
        )}
        <div className="my-music-track-copy">
          {renderTrackTitle(track, { className: "track-name-link" })}
          <p className="muted">{track.genre || "Unknown genre"} • {formatTrackBpm(track.bpm)}</p>
        </div>
        <div className="action-grid my-music-track-actions">
          <button className="primary compact" type="button" onClick={() => handleTogglePlay(track)}>
            {currentTrack?.id === track.id && isPlaying ? "Pause" : "Play"}
          </button>
          <button className="secondary compact" type="button" onClick={() => openPlaylistPicker(track)}>Add to playlist</button>
          {showRemove && (
            <button className="secondary compact" type="button" onClick={() => removeSavedTrack(track)}>Remove</button>
          )}
        </div>
      </div>
    );
  }

  function renderMyMusicByArtistSection() {
    const artistGroups = getMyMusicByArtist().filter(
      group => !fanChannelUsername || group.owner_username === fanChannelUsername
    );

    if (!currentUser) {
      return (
        <div className="empty-state">
          <h3>Log in to build your library.</h3>
          <p>Save songs from Listen or browse latest drops, then find them here grouped by artist.</p>
          <button className="secondary" type="button" onClick={() => goToPage("profile")}>Sign up or log in</button>
        </div>
      );
    }

    if (artistGroups.length === 0) {
      return (
        <div className="empty-state">
          <h3>{fanChannelUsername ? "No saved songs from this artist." : "No saved songs yet."}</h3>
          <p>
            {fanChannelUsername
              ? "Try another channel or browse latest music from this artist."
              : "Swipe songs in Discover or add tracks from Latest to start building your library."}
          </p>
          <div className="action-grid">
            {fanChannelUsername ? (
              <button className="secondary" type="button" onClick={() => setFanChannelUsername("")}>Show all artists</button>
            ) : null}
            <button className="secondary" type="button" onClick={() => goToListenTab("discover")}>Open Listen</button>
            <button className="secondary" type="button" onClick={() => goToListenTab("latest")}>Browse latest music</button>
          </div>
        </div>
      );
    }

    return (
      <section className="my-music-by-artist">
        {artistGroups.map(group => {
          const listenMoreTracks = getArtistListenMoreTracks(group.owner_username);
          const listenMoreOpen = Boolean(myMusicListenMoreOpen[group.owner_username]);
          const coverArt = group.hero_image || group.tracks.find(track => track.cover_art)?.cover_art;

          return (
            <article className="my-music-artist-card" key={group.owner_username}>
              <div className="my-music-artist-head">
                {coverArt ? (
                  <img className="my-music-artist-cover" src={coverArt} alt={group.stage_name} />
                ) : (
                  <div className="my-music-artist-cover my-music-artist-cover-fallback">
                    {group.stage_name?.[0]?.toUpperCase() || "?"}
                  </div>
                )}
                <div className="my-music-artist-meta">
                  <h3>
                    {renderArtistName(group.owner_username, {
                      label: group.stage_name,
                      verified: group.is_verified,
                      className: "artist-name-link click-title",
                      fallback: {
                        owner_id: group.owner_id,
                        stage_name: group.stage_name,
                      },
                    })}
                  </h3>
                  <p className="muted">
                    {group.tracks.length} saved song{group.tracks.length === 1 ? "" : "s"}
                    {listenMoreTracks.length > 0 ? ` · ${listenMoreTracks.length} more to explore` : ""}
                  </p>
                </div>
                <button
                  className="secondary compact"
                  type="button"
                  onClick={() => openArtistByUsername(group.owner_username, {
                    owner_id: group.owner_id,
                    stage_name: group.stage_name,
                    hero_image: group.hero_image,
                  })}
                >
                  View artist
                </button>
              </div>

              <div className="my-music-artist-actions action-grid">
                <button
                  className="primary compact"
                  type="button"
                  onClick={() => playQueue(group.tracks, 0, `${group.stage_name} saved`)}
                >
                  Play saved
                </button>
                {listenMoreTracks.length > 0 && (
                  <button
                    className="secondary compact"
                    type="button"
                    onClick={() => toggleMyMusicListenMore(group.owner_username)}
                  >
                    {listenMoreOpen ? "Hide more" : "Listen more"}
                  </button>
                )}
                <button
                  className="secondary compact"
                  type="button"
                  onClick={() => createPlaylistFromArtistSaves(group)}
                >
                  Create playlist
                </button>
              </div>

              <div className="my-music-saved-list">
                <p className="eyebrow">Saved from {group.stage_name}</p>
                {group.tracks.map(track => renderMyMusicTrackRow(track))}
              </div>

              {listenMoreOpen && listenMoreTracks.length > 0 && (
                <div className="my-music-listen-more">
                  <div className="tab-title-row">
                    <div>
                      <p className="eyebrow">Listen more</p>
                      <h4>More from {group.stage_name}</h4>
                    </div>
                    <button
                      className="primary compact"
                      type="button"
                      onClick={() => playQueue(listenMoreTracks, 0, `${group.stage_name} – more`)}
                    >
                      Play all
                    </button>
                  </div>
                  {listenMoreTracks.map(track => renderMyMusicTrackRow(track, { showRemove: false }))}
                </div>
              )}
            </article>
          );
        })}
      </section>
    );
  }

  function openPlaylistPicker(track) {
    if (!currentUser) {
      setMessage("Log in before saving tracks to playlists.");
      return;
    }

    setPlaylistPickerTrack(track);
  }

  async function addTrackToPlaylist(track, playlistId = selectedPlaylistId) {
    if (!currentUser) {
      setMessage("Log in before saving tracks to playlists.");
      return;
    }

    if (!playlistId) {
      openPlaylistPicker(track);
      return;
    }

    const res = await apiFetch(`/media/playlists/${playlistId}/add-track/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ track_id: track.id }),
    });
    const data = await res.json();

    if (!res.ok) {
      setMessage(data.error || "Unable to add track.");
      return false;
    }

    updatePlaylistInState(data.playlist);
    setMessage(data.message || "Track added.");
    return true;
  }

  async function handlePlaylistPickerSelect(playlistId) {
    if (!playlistPickerTrack) return;

    const added = await addTrackToPlaylist(playlistPickerTrack, playlistId);
    if (added) {
      setPlaylistPickerTrack(null);
    }
  }

  async function handlePlaylistPickerCreate({ title, description = "" }) {
    const playlist = await createFanPlaylistRequest({ title, description });
    if (!playlist || !playlistPickerTrack) return;

    const added = await addTrackToPlaylist(playlistPickerTrack, playlist.id);
    if (added) {
      setPlaylistPickerTrack(null);
    }
  }

  async function removeTrackFromPlaylist(track, playlistId) {
    const res = await apiFetch(`/media/playlists/${playlistId}/remove-track/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ track_id: track.id }),
    });
    const data = await res.json();

    if (!res.ok) {
      setMessage(data.error || "Unable to remove track.");
      return;
    }

    updatePlaylistInState(data.playlist);
    setMessage(data.message || "Track removed.");
  }

  async function submitCommissionRequest(event) {
    event.preventDefault();

    if (!currentUser) {
      setMessage("Log in before requesting a commission.");
      return;
    }

    if (!selectedArtist) return;

    const form = event.target;
    const payload = Object.fromEntries(new FormData(form).entries());
    payload.artist_id = selectedArtist.owner_id;
    payload.profession = activeProfession;
    payload.shipping_required = Boolean(payload.shipping_required);

    const res = await apiFetch("/marketplace/commissions/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await res.json();

    if (!res.ok) {
      setMessage(data.error || "Unable to send commission request.");
      return;
    }

    setMessage(data.message || "Commission request sent.");
    setShowCommissionForm(false);
    form.reset();
    loadCommissions();
  }

  async function updateCommissionRequest(commissionId, statusValue) {
    const res = await apiFetch(`/marketplace/commissions/${commissionId}/update/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status: statusValue }),
    });
    const data = await res.json();

    if (!res.ok) {
      setMessage(data.error || "Unable to update commission request.");
      return;
    }

    setMessage(data.message || "Commission request updated.");
    loadCommissions();
  }

  async function createSupportTier(event) {
    event.preventDefault();

    if (!currentUser?.is_artist) {
      setMessage("Artist account required.");
      return;
    }

    const form = event.target;
    const payload = Object.fromEntries(new FormData(form).entries());
    payload.profession = activeProfession;

    const res = await apiFetch("/subscriptions/tiers/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await res.json();

    if (!res.ok) {
      setMessage(data.error || "Unable to create support tier.");
      return;
    }

    setMessage(data.message || "Support tier created.");
    form.reset();
    loadData();
  }

  async function createSupportTierFromTemplate(template) {
    if (!currentUser?.is_artist) {
      setMessage("Artist account required.");
      return;
    }

    const res = await apiFetch("/subscriptions/tiers/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        profession: activeProfession,
        name: template.name,
        monthly_amount: template.monthly_amount,
        benefits: template.benefits,
      }),
    });
    const data = await res.json();

    if (!res.ok) {
      setMessage(data.error || "Unable to create support tier.");
      return;
    }

    setMessage(`${template.label} tier is live.`);
    loadData();
  }

  async function submitTip(event) {
    event.preventDefault();

    if (!currentUser) {
      setMessage("Log in before sending a tip.");
      return;
    }

    if (!selectedArtist) return;

    const form = event.target;
    const payload = Object.fromEntries(new FormData(form).entries());
    payload.artist_id = selectedArtist.owner_id;
    payload.profession = activeProfession;
    payload.is_public = Boolean(payload.is_public);
    payload.share_email_with_artist = Boolean(payload.share_email_with_artist);
    payload.apply_discovery_credits = Boolean(payload.apply_discovery_credits);

    const res = await apiFetch("/subscriptions/tips/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await res.json();

    if (!res.ok) {
      setMessage(data.error || "Unable to send tip.");
      return;
    }

    setMessage(data.message || "Tip sent.");
    setShowTipForm(false);
    form.reset();
    loadTips(selectedArtist, activeProfession);
    loadMailingList();
    loadFanEmailSharing();
    loadArtistDashboard();
    if (Number(data.discovery_credits_applied || 0) > 0) {
      loadPromotionData();
    }
  }


  async function updateArtistProfile(event) {
    event.preventDefault();

    const form = event.target;
    const formData = new FormData(form);
    const professions = formData.getAll("professions");

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
      instagram_url: formData.get("instagram_url"),
      tiktok_url: formData.get("tiktok_url"),
      youtube_url: formData.get("youtube_url"),
      website_url: formData.get("website_url"),
      website_label: formData.get("website_label"),
      hero_image: data.hero_image || selectedArtist.hero_image,
      profession_profiles: data.profession_profiles || selectedArtist.profession_profiles,
      professions: professions.length
        ? professions.map(key => ({ key, label: professionLabel(key) }))
        : [{ key: DEFAULT_PROFESSION, label: professionLabel(DEFAULT_PROFESSION) }],
      profession_keys: professions.length ? professions : [DEFAULT_PROFESSION],
    });
  }

  async function saveVisitorBanner({ file, durationSeconds, clear } = {}) {
    const artist = selectedArtist || getCurrentArtist();
    if (!artist) return;

    setVisitorBannerSaving(true);
    const formData = new FormData();
    formData.append("stage_name", artist.stage_name);
    formData.append("active_profession", activeProfession);
    if (file) formData.append("profession_visitor_banner", file);
    if (durationSeconds) formData.append("profession_visitor_banner_duration", String(durationSeconds));
    if (clear) formData.append("profession_clear_visitor_banner", "true");

    try {
      const res = await apiFetch("/artists/update-profile/", {
        method: "POST",
        body: formData,
      });
      const data = await res.json();
      setMessage(data.message || data.error || (clear ? "Visitor visual removed." : "Visitor visual saved."));
      if (res.ok) {
        loadData();
        setSelectedArtist(current => (current ? {
          ...current,
          profession_profiles: data.profession_profiles || current.profession_profiles,
        } : current));
      }
    } finally {
      setVisitorBannerSaving(false);
    }
  }


  async function savePageBuilder(event) {
    event.preventDefault();

    const form = event.target;
    const formData = new FormData();
    const layoutPatch = {};

    if (form.show_music) {
      formData.append("show_music", form.show_music.checked ? "true" : "false");
      layoutPatch.show_music = form.show_music.checked;
    }
    if (form.show_posts) {
      formData.append("show_posts", form.show_posts.checked ? "true" : "false");
      layoutPatch.show_posts = form.show_posts.checked;
    }
    if (form.show_store) {
      formData.append("show_store", form.show_store.checked ? "true" : "false");
      layoutPatch.show_store = form.show_store.checked;
    }
    if (form.show_lives) {
      formData.append("show_lives", form.show_lives.checked ? "true" : "false");
      layoutPatch.show_lives = form.show_lives.checked;
    }
    if (form.show_about) {
      formData.append("show_about", form.show_about.checked ? "true" : "false");
      layoutPatch.show_about = form.show_about.checked;
    }
    if (form.theme_name?.value) {
      formData.append("theme_name", form.theme_name.value);
    }
    if (form.studio_theme_name?.value) {
      formData.append("studio_theme_name", form.studio_theme_name.value);
    }

    const res = await apiFetch("/artists/update-page-builder/", {
      method: "POST",
      body: formData,
    });

    const data = await res.json();

    setMessage(data.message || data.error || "Page layout updated.");

    setSelectedArtist({
      ...selectedArtist,
      ...layoutPatch,
      theme_name: data.theme_name || form.theme_name?.value || selectedArtist.theme_name,
      studio_theme_name: data.studio_theme_name || form.studio_theme_name?.value || selectedArtist.studio_theme_name,
    });

    loadData();
  }

  async function saveFanTheme({ theme_name }) {
    const res = await apiFetch("/accounts/profile-theme/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ theme_name }),
    });
    const data = await res.json();

    if (!res.ok) {
      setMessage(data.error || "Unable to save profile theme.");
      return;
    }

    setMessage(data.message || "Profile theme saved.");
    setCurrentUser(current => (current ? { ...current, theme_name: data.theme_name || theme_name } : current));
    setThemePreview(null);
  }

  async function saveArtistThemes({ theme_name, studio_theme_name }) {
    const formData = new FormData();
    if (theme_name) formData.append("theme_name", theme_name);
    if (studio_theme_name) formData.append("studio_theme_name", studio_theme_name);

    const res = await apiFetch("/artists/update-page-builder/", {
      method: "POST",
      body: formData,
    });
    const data = await res.json();

    if (!res.ok) {
      setMessage(data.error || "Unable to save themes.");
      return;
    }

    setMessage(data.message || "Themes saved.");
    const artist = getCurrentArtist();
    if (artist) {
      const patch = {
        theme_name: data.theme_name || theme_name || artist.theme_name,
        studio_theme_name: data.studio_theme_name || studio_theme_name || artist.studio_theme_name,
      };
      setSelectedArtist(current => (current ? { ...current, ...patch } : current));
      setArtists(current => current.map(item =>
        item.owner_id === artist.owner_id ? { ...item, ...patch } : item
      ));
    }
    setThemePreview(null);
    loadData();
  }

  function openArtist(artist, updateUrl = true, options = {}) {
    const profession = resolveArtistProfession(artist, options.profession || "");
    setSelectedArtist(artist);
    setActiveProfession(profession);
    if (options.tab || options.shopTab || options.sectionTab) {
      applyArtistPageRoute(options);
    } else {
      setActiveTab(primaryContentTab(profession));
      setActiveShopTab(options.shopTab || "merch");
      setActiveMoreTab("settings");
    }
    if (options.productId) {
      setHighlightedProductId(String(options.productId));
    }
    if (updateUrl) {
      const shopTab = options.tab ? (LEGACY_PROFILE_TAB_MAP[options.tab]?.shopTab || options.tab) : "";
      updateArtistPageUrl(artist, profession, {
        replace: options.replaceUrl,
        tab: shopTab || options.shopTab || "",
        productId: options.productId || "",
      });
    }
    apiFetch("/artists/page-view/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ artist_id: artist.owner_id }),
    }).catch(() => {});
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  async function openArtistFromGig(gig) {
    if (gig?.artist_username) {
      await openArtistByUsername(gig.artist_username, {
        owner_id: gig.artist_id,
        stage_name: gig.stage_name,
        genre: gig.genre || "",
        city: gig.venue_city || "",
      });
      return;
    }

    const existing = artists.find(item => item.owner_id === gig.artist_id);
    if (existing) {
      openArtist(existing);
      return;
    }

    openArtist({
      owner_id: gig.artist_id,
      owner_username: gig.artist_username,
      stage_name: gig.stage_name,
      genre: gig.genre || "",
      city: gig.venue_city || "",
    });
  }

  async function openArtistByUsername(username, fallback = {}, options = {}) {
    if (!username) return;

    const existing = artistFromUsername(username);
    if (existing) {
      openArtist(existing, true, {
        profession: options.profession || fallback.profession || "",
        tab: options.tab,
        shopTab: options.shopTab,
      });
      return;
    }

    const artistData = await fetchJson("/artists/", []);
    if (Array.isArray(artistData)) {
      setArtists(artistData);
      const fresh = artistData.find(item => item.owner_username === username);
      if (fresh) {
        openArtist(fresh, true, {
          profession: options.profession || fallback.profession || "",
          tab: options.tab,
          shopTab: options.shopTab,
        });
        return;
      }
    }

    const professionQuery = options.profession || fallback.profession || "";
    const metaPath = professionQuery
      ? `/artists/public/${encodeURIComponent(username)}/?profession=${encodeURIComponent(professionQuery)}`
      : `/artists/public/${encodeURIComponent(username)}/`;
    const meta = await fetchJson(metaPath, null);
    if (meta && !meta.error) {
      openArtist({
        owner_id: meta.owner_id,
        owner_username: meta.username || username,
        stage_name: meta.stage_name || fallback.stage_name || username,
        genre: meta.genre || fallback.genre || "",
        city: meta.city || fallback.city || "",
        hero_image: meta.hero_image || fallback.hero_image,
        profession_keys: meta.profession_keys || fallback.profession_keys,
        on_hiatus: meta.on_hiatus,
        ...fallback,
      }, true, {
        profession: meta.profession || professionQuery,
        tab: options.tab,
        shopTab: options.shopTab,
      });
      return;
    }

    openArtist({
      owner_username: username,
      stage_name: fallback.stage_name || username,
      ...fallback,
    }, true, {
      profession: professionQuery,
      tab: options.tab,
      shopTab: options.shopTab,
    });
  }

  function openArtistHome(updateUrl = true) {
    const artist = getCurrentArtist();
    if (!artist) {
      setPreviewAsFan(false);
      setDiscoverView("recommendations");
      setActivePage("home");
      setSelectedArtist(null);
      if (updateUrl) {
        window.history.pushState({}, "", window.location.pathname);
      }
      window.scrollTo({ top: 0, behavior: "smooth" });
      return;
    }

    setPreviewAsFan(false);
    setDiscoverView("recommendations");
    setActivePage("home");
    setSelectedArtist(artist);
    setActiveProfession(getDefaultProfession(artist));
    setActiveTab("listen");
    setActiveShopTab("merch");
    setActiveMoreTab("settings");
    if (updateUrl) {
      window.history.pushState({}, "", window.location.pathname);
    }
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function goToPage(page, updateUrl = true, options = {}) {
    let resolvedPage = page;
    let nextDiscoverView = discoverView;
    let nextListenTab = listenTab;
    let nextStoreTab = storeTab;

    if (page === "profile" && options.tab) {
      setProfileTab(resolveProfileTab(options.tab));
      if (options.section) {
        setSettingsSection(resolveSettingsSection(options.section, currentUser, "library"));
      }
    }

    if (currentUser?.is_host) {
      resolvedPage = resolveAccountPage(page, currentUser, options.tab || "", options.view || "");
    } else if (currentUser && !currentUser.is_artist && !currentUser.is_host && page === "spaces") {
      resolvedPage = "my-scene";
    } else if (page === "radio") {
      resolvedPage = "my-music";
    } else if (page === "saved") {
      resolvedPage = "listen";
      nextListenTab = "discover";
      nextDiscoverView = "saved";
    } else if (page === "discover") {
      resolvedPage = "listen";
      nextListenTab = "discover";
      nextDiscoverView = options.view === "saved" ? "saved" : "recommendations";
    } else if (page === "music") {
      resolvedPage = "listen";
      nextListenTab = "latest";
      nextDiscoverView = "recommendations";
    } else if (page === "listen") {
      resolvedPage = "listen";
      if (options.tab === "latest" || options.tab === "discover") {
        nextListenTab = options.tab;
      }
      if (options.view === "saved") {
        nextDiscoverView = "saved";
        nextListenTab = "discover";
      } else if (options.view === "recommendations") {
        nextDiscoverView = "recommendations";
      }
    } else if (page === "stores") {
      resolvedPage = "stores";
      if (options.tab === "music-store" || options.tab === "merch") {
        nextStoreTab = options.tab;
      }
    }

    setDiscoverView(nextDiscoverView);
    setListenTab(nextListenTab);
    setStoreTab(nextStoreTab);
    if (!FAN_ARTIST_RAIL_PAGES.has(resolvedPage)) {
      setFanChannelUsername("");
    }
    resolvedPage = gatePlatformPage(resolvedPage);
    setActivePage(resolvedPage);
    setSelectedArtist(null);
    if (options.show) {
      setMySceneShowId(String(options.show));
    } else if (resolvedPage !== "my-scene") {
      setMySceneShowId("");
    }
    if (updateUrl) {
      let nextUrl = window.location.pathname;
      if (resolvedPage === "home") {
        nextUrl = window.location.pathname;
      } else if (resolvedPage === "prelaunch") {
        nextUrl = `${window.location.pathname}?page=prelaunch`;
      } else if (resolvedPage === "listen") {
        const params = new URLSearchParams({ page: "listen", tab: nextListenTab });
        if (nextListenTab === "discover" && nextDiscoverView === "saved") {
          params.set("view", "saved");
        }
        nextUrl = `${window.location.pathname}?${params.toString()}`;
      } else if (resolvedPage === "stores") {
        nextUrl = `${window.location.pathname}?page=stores&tab=${encodeURIComponent(nextStoreTab)}`;
      } else if (resolvedPage === "profile") {
        const tab = resolveProfileTab(options.tab || profileTab);
        const section = resolveSettingsSection(options.section || settingsSection, currentUser, "library");
        nextUrl = `${window.location.pathname}?page=profile&tab=${encodeURIComponent(tab)}&section=${encodeURIComponent(section)}`;
      } else if (resolvedPage === "my-scene" && options.show) {
        nextUrl = `${window.location.pathname}?page=my-scene&show=${encodeURIComponent(options.show)}`;
      } else {
        nextUrl = `${window.location.pathname}?page=${encodeURIComponent(resolvedPage)}`;
      }
      window.history.pushState({}, "", nextUrl);
    }
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function goToListenTab(tab, options = {}) {
    goToPage("listen", true, { tab, view: options.view });
  }

  function goToStoreTab(tab) {
    goToPage("stores", true, { tab });
  }

  function goToMyScene(showId = null) {
    if (showId) {
      goToPage("my-scene", true, { show: showId });
      return;
    }
    goToPage("my-scene");
  }

  function getCurrentArtist() {
    if (!currentUser?.is_artist) return null;

    const fromList = artists.find(artist => artist.owner_username === currentUser.username);
    if (fromList) return fromList;
    if (selectedArtist?.owner_username === currentUser.username) return selectedArtist;

    return {
      id: currentUser.id,
      owner_id: currentUser.id,
      owner_username: currentUser.username,
      stage_name: currentUser.display_name || currentUser.username,
      genre: "",
      city: "",
      artist_story: "",
      influences: "",
      is_verified: false,
      on_hiatus: false,
      professions: [{ key: DEFAULT_PROFESSION, label: professionLabel(DEFAULT_PROFESSION) }],
      profession_keys: [DEFAULT_PROFESSION],
      show_music: true,
      show_posts: true,
      show_store: true,
      show_lives: true,
      show_about: true,
    };
  }

  function formatTrackBpm(bpm) {
    return bpm ? `${bpm} BPM` : "No BPM";
  }

  function getArtistProfessionStats(artist, profession = activeProfession) {
    const health = artist.business_health || {};
    const publicStats = {
      supporterCount: health.active_subscribers ?? 0,
      earnings: health.monthly_artist_share ?? "0.00",
    };

    if (currentUser?.username === artist.owner_username) {
      const subs = (subData.subscriptions || []).filter(sub =>
        sub.artist === artist.owner_username &&
        (sub.profession || DEFAULT_PROFESSION) === profession &&
        sub.active !== false
      );
      return {
        supporterCount: subs.length,
        earnings: subs.reduce((total, sub) => total + Number(sub.artist_share || 0), 0).toFixed(2),
      };
    }

    return publicStats;
  }

  function getArtistStudioSnapshot(artist, profession = DEFAULT_PROFESSION) {
    if (!artist) return null;

    const tracks = music.filter(track =>
      track.artist_username === artist.owner_username &&
      (track.profession || DEFAULT_PROFESSION) === profession
    );
    const artistPostsList = posts.filter(post =>
      post.author_username === artist.owner_username &&
      (post.profession || DEFAULT_PROFESSION) === profession
    );
    const artistProductsList = products.filter(product =>
      product.artist_username === artist.owner_username &&
      (product.profession || DEFAULT_PROFESSION) === profession
    );
    const professionSubscriptions = subData.subscriptions?.filter(sub =>
      sub.artist === artist.owner_username &&
      (sub.profession || DEFAULT_PROFESSION) === profession
    ) || [];
    const professionTips = tipData.results.filter(tip =>
      tip.artist === artist.owner_username &&
      tip.profession === profession
    );
    const professionCommissions = commissionRequests.filter(item =>
      item.artist_username === artist.owner_username &&
      item.profession === profession
    );
    const professionSupportTiers = supportTiers.filter(tier =>
      tier.artist === artist.owner_username &&
      tier.profession === profession
    );

    return {
      artist,
      profession,
      professionLabel: professionLabel(profession),
      tracks,
      posts: artistPostsList,
      products: artistProductsList,
      supporterCount: professionSubscriptions.length,
      earnings: professionSubscriptions
        .reduce((total, sub) => total + Number(sub.artist_share || 0), 0)
        .toFixed(2),
      tipTotal: professionTips
        .reduce((total, tip) => total + Number(tip.artist_share || 0), 0)
        .toFixed(2),
      commissions: professionCommissions,
      supportTiers: professionSupportTiers,
    };
  }

  function getOwnerStudioSnapshot(profession) {
    const artist = getCurrentArtist();
    if (!artist || !currentUser?.is_artist) return null;
    const resolvedProfession = profession || getDefaultProfession(artist);
    return getArtistStudioSnapshot(artist, resolvedProfession);
  }

  function openTrustChecklistItem(item) {
    const actions = {
      avatar: () => openStudioTab("settings"),
      artist_story: () => openStudioTab("settings"),
      city: () => openStudioTab("settings"),
      genre: () => openStudioTab("settings"),
      social_link: () => openStudioTab("settings"),
      pov: () => openStudioTab("feed", { createPov: true }),
      post_or_instant: () => openStudioTab("feed", { createPost: true }),
    };
    (actions[item?.key] || (() => openStudioTab("settings")))();
  }

  function openAiReviewFlag(flag) {
    openStudioTab("listen");
    if (flag?.upload_title) {
      setMessage(`Review upload: ${flag.upload_title}`);
    }
  }

  function getArtistLaunchChecklistItems(snapshot) {
    if (!snapshot) return [];

    const { artist, profession, tracks, posts, supportTiers } = snapshot;
    const inviteShared = hasSharedInviteLink(currentUser?.id, artistDashboard?.referrals);
    const previewed = hasPreviewedPublicPage(currentUser?.id);

    return [
      {
        index: "1",
        label: "Public profile",
        detail: artist.artist_story && artist.genre && artist.city
          ? "Stage name, genre, city and story are filled."
          : "Add style, city, story and influences fans see on your page.",
        done: Boolean(artist.artist_story && artist.genre && artist.city),
        onClick: () => openStudioTab("settings"),
      },
      {
        index: "2",
        label: isMusicBranchProfession(profession) ? "First upload" : "First post",
        detail: isMusicBranchProfession(profession)
          ? (tracks.length ? `${tracks.length} track${tracks.length === 1 ? "" : "s"} uploaded.` : "Upload one public or supporter-only track.")
          : (posts.length ? `${posts.length} post${posts.length === 1 ? "" : "s"} published.` : "Publish one update, work-in-progress, or studio note."),
        done: isMusicBranchProfession(profession) ? tracks.length > 0 : posts.length > 0,
        onClick: () => openStudioTab(primaryContentTab(profession), isMusicBranchProfession(profession) ? { createMusic: true } : { createPost: true }),
      },
      {
        index: "3",
        label: "Support tier",
        detail: supportTiers.length
          ? `${supportTiers.length} monthly tier${supportTiers.length === 1 ? "" : "s"} live.`
          : "Add a $1+ monthly tier so fans can subscribe.",
        done: supportTiers.length > 0,
        onClick: () => openStudioTab("support-tiers"),
      },
      {
        index: "4",
        label: "Share invite link",
        detail: inviteShared && previewed
          ? "Invite link copied or referrals already tracked."
          : !previewed
            ? "Preview your public page as a fan, then copy your invite link."
            : "Copy your invite link and send it to early supporters.",
        done: inviteShared && previewed,
        onClick: () => {
          if (!previewed) {
            startPublicPagePreview();
            return;
          }
          copyArtistInviteLink();
        },
      },
    ];
  }

  function getFanSetupChecklistItems() {
    const savedTrackCount = getMyMusicTracks().length;

    return [
      {
        index: "1",
        label: "Save an artist",
        detail: savedArtists.length
          ? `${savedArtists.length} saved artist${savedArtists.length === 1 ? "" : "s"}.`
          : "Follow one artist you like from Listen or Discover.",
        done: savedArtists.length > 0,
        onClick: () => goToPage("listen"),
      },
      {
        index: "2",
        label: "Save a track",
        detail: savedTrackCount
          ? `${savedTrackCount} track${savedTrackCount === 1 ? "" : "s"} in My Playlists.`
          : "Tap save on any track while browsing Listen.",
        done: savedTrackCount > 0,
        onClick: () => goToPage("listen"),
      },
      {
        index: "3",
        label: "Support one artist",
        detail: getSupportedArtistUsernames().length
          ? `${getSupportedArtistUsernames().length} active support relationship${getSupportedArtistUsernames().length === 1 ? "" : "s"}.`
          : "Start with $1/month demo support on an artist you save.",
        done: getSupportedArtistUsernames().length > 0,
        onClick: () => (savedArtists[0] ? openArtist(savedArtists[0]) : goToPage("listen")),
      },
    ];
  }

  function computeFanEngagementScore() {
    const checklist = getFanSetupChecklistItems();
    const doneCount = checklist.filter(item => item.done).length;
    let score = (doneCount / checklist.length) * 40;
    score += Math.min(savedArtists.length * 8, 24);
    if (getSupportedArtistUsernames().length > 0) score += 20;
    score += Math.min(getMyMusicTracks().length * 2, 16);
    if (currentUser?.favorite_genres && currentUser?.discovery_location) score += 10;
    return Math.min(100, Math.round(score));
  }

  function computeArtistEngagementScore(snapshot) {
    if (!snapshot) return 0;
    const checklist = getArtistLaunchChecklistItems(snapshot);
    const doneCount = checklist.filter(item => item.done).length;
    let score = checklist.length ? (doneCount / checklist.length) * 45 : 0;
    const dashboard = artistDashboard;
    if (Number(dashboard?.fans?.active_subscribers || 0) > 0) score += 25;
    if (Number(dashboard?.revenue?.mrr?.amount || 0) > 0) score += 15;
    if ((snapshot.tracks?.length || 0) + (snapshot.posts?.length || 0) > 0) score += 10;
    if ((snapshot.products?.length || 0) > 0) score += 5;
    return Math.min(100, Math.round(score));
  }

  function computeHostEngagementScore() {
    const checklist = getHostSetupChecklistItems();
    const doneCount = checklist.filter(item => item.done).length;
    let score = checklist.length ? (doneCount / checklist.length) * 50 : 0;
    score += Math.min(spaceListings.length * 12, 24);
    score += Math.min(spaceBookings.filter(booking => booking.status === "confirmed").length * 10, 20);
    if (spaceHostProfile?.city && spaceHostProfile?.contact_email) score += 6;
    return Math.min(100, Math.round(score));
  }

  function getWelcomeDismissLoginThreshold(engagementScore) {
    if (engagementScore >= 70) return 5;
    if (engagementScore >= 45) return 7;
    if (engagementScore >= 25) return 8;
    return 10;
  }

  function shouldShowHomeWelcome() {
    if (!currentUser) return false;
    const loginCount = currentUser.session_login_count || 0;
    let engagementScore = 0;
    if (currentUser.is_artist) {
      engagementScore = computeArtistEngagementScore(getOwnerStudioSnapshot());
    } else if (currentUser.is_host) {
      engagementScore = computeHostEngagementScore();
    } else {
      engagementScore = computeFanEngagementScore();
    }
    return loginCount < getWelcomeDismissLoginThreshold(engagementScore);
  }

  function getHostSetupChecklistItems() {
    const profile = spaceHostProfile;
    const profileComplete = Boolean(profile?.city && profile?.address && profile?.contact_email);
    const roomCount = spaceListings.length;
    const bookingCount = spaceBookings.length;

    return [
      {
        index: "1",
        label: "Complete venue details",
        detail: profileComplete
          ? "Business name, city, address and contact email are set."
          : "Add your venue city, address and contact email from Profile.",
        done: profileComplete,
        onClick: () => goToPage("profile"),
      },
      {
        index: "2",
        label: "List your first room",
        detail: roomCount ? `${roomCount} room${roomCount === 1 ? "" : "s"} listed.` : "Add a room so artists can request bookings.",
        done: roomCount > 0,
        onClick: () => setShowSpaceListingForm(true),
      },
      {
        index: "3",
        label: "Review booking requests",
        detail: bookingCount ? `${bookingCount} booking record${bookingCount === 1 ? "" : "s"} to manage.` : "Requests from artists will appear here and in Notifications.",
        done: bookingCount > 0,
        onClick: () => goToPage("notifications"),
      },
    ];
  }

  function renderSupportTierEditorPanel(snapshot) {
    if (!snapshot) return null;

    return (
      <section className="support-tier-panel">
        <div className="tab-title-row">
          <div>
            <p className="eyebrow">Supporter tiers</p>
            <h3>{snapshot.professionLabel} monthly tiers</h3>
          </div>
        </div>

        {snapshot.supportTiers.length === 0 && (
          <div className="tier-template-row">
            <p className="muted form-hint">Launch with a preset tier in one tap, or create your own below.</p>
            <div className="action-grid tier-template-actions">
              {SUPPORT_TIER_TEMPLATES.map(template => (
                <button
                  key={template.id}
                  type="button"
                  className="secondary compact"
                  onClick={() => createSupportTierFromTemplate(template)}
                >
                  {template.label}
                </button>
              ))}
            </div>
          </div>
        )}

        <form className="playlist-form" onSubmit={createSupportTier}>
          <input name="name" required placeholder="Custom tier name" aria-label="Tier name" />
          <input name="monthly_amount" type="number" min="1" step="0.01" defaultValue="3.00" aria-label="Monthly amount" />
          <input name="benefits" placeholder="Benefits e.g. process posts, early drops" aria-label="Tier benefits" />
          <button className="secondary compact" type="submit">Create custom tier</button>
        </form>
        <div className="tier-card-grid">
          {SUPPORT_TIER_TEMPLATES.map(template => (
            <article className="tier-card tier-card--template" key={template.id}>
              <strong>{template.label}</strong>
              <span>${template.monthly_amount}/month</span>
              <p>{template.benefits}</p>
            </article>
          ))}
          {snapshot.supportTiers.map(tier => (
            <article className="tier-card" key={tier.id}>
              <strong>{tier.name}</strong>
              <span>${tier.monthly_amount}/month</span>
              <p>{tier.benefits || tier.description || "Custom supporter tier."}</p>
            </article>
          ))}
        </div>
      </section>
    );
  }

  function renderArtistStudioTools(snapshot) {
    if (!snapshot) return null;

    return (
      <>
        {!isMusicBranchProfession(snapshot.profession) && (
          <section className="commission-panel">
            <div className="tab-title-row">
              <div>
                <p className="eyebrow">Commissions</p>
                <h3>{snapshot.professionLabel} requests</h3>
              </div>
              <span className="muted">{snapshot.commissions.length} active request{snapshot.commissions.length === 1 ? "" : "s"}</span>
            </div>

            {snapshot.commissions.length === 0 && (
              <div className="empty-state">
                <h3>No commission requests yet.</h3>
                <p>Fans can request custom work from your Arts profile.</p>
              </div>
            )}

            <div className="commission-list">
              {snapshot.commissions.map(item => (
                <article className="commission-card" key={item.id}>
                  <div>
                    <p className="eyebrow">{item.status_label} • {item.fan_username}</p>
                    <h4>{item.title}</h4>
                    <p>{item.brief}</p>
                    <div className="post-badges">
                      {item.budget && <span>Budget: ${item.budget}</span>}
                      {item.deadline && <span>Deadline: {item.deadline}</span>}
                      {item.size_format && <span>{item.size_format}</span>}
                      {item.shipping_required && <span>Shipping</span>}
                    </div>
                    {item.reference_notes && <p className="muted">References: {item.reference_notes}</p>}
                    {item.delivery_notes && <p className="muted">Delivery: {item.delivery_notes}</p>}
                  </div>
                  <div className="commission-actions">
                    <button className="secondary compact" onClick={() => updateCommissionRequest(item.id, "reviewing")}>Reviewing</button>
                    <button className="primary compact" onClick={() => updateCommissionRequest(item.id, "accepted")}>Accept</button>
                    <button className="secondary compact" onClick={() => updateCommissionRequest(item.id, "declined")}>Decline</button>
                    <button className="secondary compact" onClick={() => updateCommissionRequest(item.id, "completed")}>Complete</button>
                  </div>
                </article>
              ))}
            </div>
          </section>
        )}
      </>
    );
  }

  function renderArtistDevelopmentDashboard() {
    const dashboard = artistDashboard;
    const revenue = dashboard?.revenue || {};
    const fans = dashboard?.fans || {};
    const ratios = dashboard?.ratios || {};
    const funnel = dashboard?.funnel || {};
    const musicFunnelTracks = dashboard?.music_funnel?.tracks || [];
    const topSupporters = dashboard?.top_supporters || [];
    const recentActivity = dashboard?.recent_activity || [];
    const referralRows = dashboard?.referrals?.supporters_this_month || [];
    const instagramSupporters = referralRows.find(row => row.source === "instagram")?.supporters || 0;
    const artistLink = getArtistPublicUrl();
    const instagramLink = getArtistPublicUrl("instagram");
    const shareTemplate = `I'm on IndieFund - subscribe for exclusive content: ${artistLink}`;
    const embedSnippet = `<a data-embed-from="indiefund" href="${artistLink}">Support ${currentUser.display_name || currentUser.username} on IndieFund</a>`;
    const hasSupporters = Number(fans.active_subscribers || 0) > 0;
    const hasMailingList = Number(fans.mailing_list_size || 0) > 0;
    const studioSnapshot = getOwnerStudioSnapshot();
    const spaces = dashboard?.spaces || {};
    const trust = dashboard?.trust || {};
    const showWelcome = shouldShowHomeWelcome();

    return (
      <>
        <section className={`home-dashboard-head section-head tab-title-row${showWelcome ? "" : " home-dashboard-head--compact"}`}>
          <div>
            <p className="eyebrow">Artist Dashboard</p>
            {showWelcome ? (
              <>
                <h2>Welcome back, {currentUser.display_name || currentUser.username}</h2>
                <p className="muted">Your artist dashboard — profile, releases, store, and fan relationships.</p>
              </>
            ) : (
              <>
                <h2>Business health</h2>
                <p className="muted">Track capture, conversion, retention and monetization from your direct fan relationships.</p>
              </>
            )}
          </div>
          <div className="action-grid">
            <button className="secondary compact" onClick={() => shareArtistPageLink()}>Share your page link</button>
            <button className="primary compact" onClick={() => openArtistHome()}>View public page</button>
          </div>
        </section>

        {(() => {
          const artist = getCurrentArtist();
          const professions = getArtistProfessions(artist);
          if (professions.length <= 1) return null;
          return (
            <section className="feature-card artist-sides-panel">
              <p className="eyebrow">Creative work</p>
              <h3>Your public sides</h3>
              <p className="muted">Each creative work has its own page, store, and supporters. Open a side to manage or share it.</p>
              <div className="profession-switcher">
                {professions.map(item => (
                  <button
                    key={item.key}
                    type="button"
                    className={`profession-side-chip profession-side-chip--${item.key}`}
                    onClick={() => openStudioTab(primaryContentTab(item.key), { profession: item.key })}
                  >
                    {item.label}
                  </button>
                ))}
              </div>
            </section>
          );
        })()}

        {(() => {
          const launchItems = getArtistLaunchChecklistItems(studioSnapshot);
          const { complete: launchComplete } = getChecklistProgress(launchItems);
          if (launchComplete) {
            return (
              <>
                <GrowthNextAction action={getArtistGrowthNextAction()} />
                {renderChallengeBoard()}
              </>
            );
          }
          return (
            <SetupChecklistPanel
              title="Launch your page"
              subtitle="Finish these four steps so fans can find you, hear your work, and subscribe."
              items={launchItems}
              checklistHidden={setupChecklistDismissed}
              onDismiss={dismissSetupChecklist}
            />
          );
        })()}

        <section className="feature-card ads-manager-teaser">
          <p className="eyebrow">Artist Growth</p>
          <h3>Plan your first growth campaign</h3>
          <p className="muted">Map external ads for Instagram, YouTube, and more with a simple step-by-step wizard.</p>
          <button className="secondary compact" type="button" onClick={() => goToPage("ads-manager")}>
            Open Ads Manager
          </button>
        </section>

        <section className="artist-stat-panel">
          <div className="artist-stat-grid">
            <div className="artist-stat-item">
              <p className="eyebrow">MRR</p>
              <strong className="artist-stat-value">${revenue.mrr?.amount || "0.00"}</strong>
              <p className="artist-stat-detail">${revenue.mrr?.artist_share || "0.00"} artist share.</p>
            </div>
            <div className="artist-stat-item">
              <p className="eyebrow">Active subscribers</p>
              <strong className="artist-stat-value">{fans.active_subscribers || 0}</strong>
              <p className="artist-stat-detail">{ratios.supporter_to_follower_ratio ?? 0}% supporter-to-follower ratio.</p>
            </div>
            <div className="artist-stat-item">
              <p className="eyebrow">Mailing list</p>
              <strong className="artist-stat-value">{fans.mailing_list_size || 0}</strong>
              <p className="artist-stat-detail">+{fans.mailing_list_growth_30d || 0} contacts in 30 days.</p>
            </div>
            <div className="artist-stat-item">
              <p className="eyebrow">Revenue this month</p>
              <strong className="artist-stat-value">${revenue.total_revenue_this_month?.amount || "0.00"}</strong>
              <p className="artist-stat-detail">${revenue.platform_fees_this_month || "0.00"} platform fees.</p>
            </div>
            <div className="artist-stat-item">
              <p className="eyebrow">Visitors</p>
              <strong className="artist-stat-value">{funnel.visitors || 0}</strong>
              <p className="artist-stat-detail">Known page viewers captured in the journey funnel.</p>
            </div>
            <div className="artist-stat-item">
              <p className="eyebrow">Subscriber growth</p>
              <strong className="artist-stat-value">{fans.new_subscribers_30d || 0}</strong>
              <p className="artist-stat-detail">New active subscribers in the last 30 days.</p>
            </div>
            <div className="artist-stat-item">
              <p className="eyebrow">New supporters</p>
              <strong className="artist-stat-value">{fans.new_subscribers_7d || 0}</strong>
              <p className="artist-stat-detail">New subscribers in the last 7 days.</p>
            </div>
            <div className="artist-stat-item">
              <p className="eyebrow">Merch this month</p>
              <strong className="artist-stat-value">${revenue.marketplace_sales_this_month?.amount || "0.00"}</strong>
              <p className="artist-stat-detail">${revenue.marketplace_sales_this_month?.artist_share || "0.00"} artist share.</p>
            </div>
            <div className="artist-stat-item">
              <p className="eyebrow">Retention</p>
              <strong className="artist-stat-value">{dashboard?.retention?.repeat_purchasers || 0}</strong>
              <p className="artist-stat-detail">{dashboard?.retention?.churn_30d || 0} unsubscribes in 30 days.</p>
            </div>
            <div className="artist-stat-item">
              <p className="eyebrow">Invite funnel</p>
              <strong className="artist-stat-value">{dashboard?.referrals?.invite_subscribers || 0}</strong>
              <p className="artist-stat-detail">{dashboard?.referrals?.invite_follows || 0} follows from invite links.</p>
            </div>
          </div>
        </section>

        {(dashboard?.audience_cities?.length > 0 || dashboard?.engaging_content?.length > 0) && (
          <section className="dashboard-two-column">
            {dashboard?.audience_cities?.length > 0 && (
              <div className="home-activity">
                <p className="eyebrow">Audience locations</p>
                <h3>Top cities</h3>
                <ul className="simple-list">
                  {dashboard.audience_cities.map(row => (
                    <li key={row.city}>{row.city} — {row.count} supporter{row.count === 1 ? "" : "s"}</li>
                  ))}
                </ul>
              </div>
            )}
            {dashboard?.engaging_content?.length > 0 && (
              <div className="home-activity">
                <p className="eyebrow">Most engaging content</p>
                <h3>Posts fans react to</h3>
                <ul className="simple-list">
                  {dashboard.engaging_content.map(item => (
                    <li key={item.id}>{item.title} — {item.likes} likes, {item.comments} comments</li>
                  ))}
                </ul>
              </div>
            )}
          </section>
        )}

        {(() => {
          const schedule = dashboard?.fee_schedule;
          const payoutsReady = connectStatus?.payouts_enabled;
          const connected = connectStatus?.connected;
          const demoPayouts = connectStatus?.demo_mode;
          const payoutLabel = payoutsReady
            ? "Payouts active"
            : connected
              ? "Finish payout setup"
              : "Set up payouts";
          const payoutDetail = payoutsReady
            ? "Your earnings will be paid out to your connected account."
            : connected
              ? "Your payout account needs a few more details before money can be released."
              : "Connect a payout account so your sales, tips and support reach your bank.";
          return (
            <section className="payouts-panel" aria-label="Payouts and fees">
              <div className="payouts-status">
                <div>
                  <p className="eyebrow">Getting paid</p>
                  <strong className={payoutsReady ? "payout-ok" : "payout-todo"}>{payoutLabel}</strong>
                  <p className="muted">{payoutDetail}</p>
                  {demoPayouts && <p className="muted form-hint">Demo mode — real payouts start when Stripe is configured.</p>}
                </div>
                {!payoutsReady && (
                  <button className="primary compact" type="button" onClick={startPayoutOnboarding}>
                    {connected ? "Continue setup" : "Set up payouts"}
                  </button>
                )}
              </div>
              {schedule && (
                <div className="fee-schedule">
                  <p className="eyebrow">What you keep</p>
                  <ul className="fee-schedule-list">
                    {schedule.items.map(item => (
                      <li key={item.id}>
                        <span>{item.label}</span>
                        <strong>You keep {item.you_keep_percent}</strong>
                        <span className="muted">{item.platform_percent} platform fee</span>
                      </li>
                    ))}
                  </ul>
                  {schedule.plan_note && <p className="muted form-hint">{schedule.plan_note}</p>}
                  <p className="muted form-hint">{schedule.live_policy}</p>
                </div>
              )}
            </section>
          );
        })()}

        {!hasSupporters && (
          <section className="empty-state">
            <h3>No paid supporters yet.</h3>
            <p>Start by sharing your page and setting up a clear first tier. Streaming is the touchpoint; the supporter relationship is the asset.</p>
            <div className="action-grid">
              <button className="primary" onClick={() => shareArtistPageLink()}>Share your link</button>
              <button className="secondary" onClick={() => openStudioTab("support-tiers")}>Set up your first tier</button>
            </div>
          </section>
        )}

        <section className="dashboard-two-column">
          <div className="home-activity">
            <div className="tab-title-row">
              <div>
                <p className="eyebrow">Top supporters</p>
                <h3>Highest direct value</h3>
              </div>
            </div>
            {topSupporters.length === 0 ? (
              <div className="empty-state compact-empty">
                <h3>No supporter spend yet.</h3>
                <p>Invite existing fans to become your first direct supporters.</p>
              </div>
            ) : (
              <div className="supporter-table">
                <div className="supporter-table-row supporter-table-head">
                  <span>Fan</span>
                  <span>Total</span>
                  <span>Tenure</span>
                </div>
                {topSupporters.slice(0, 5).map(item => (
                  <div className="supporter-table-row" key={item.fan_id}>
                    <span>{item.fan_username}</span>
                    <strong>${item.total_spend}</strong>
                    <span>{item.tenure_days}d</span>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="home-activity">
            <div className="tab-title-row">
              <div>
                <p className="eyebrow">Mailing list</p>
                <h3>{fans.mailing_list_size || 0} opted-in contacts</h3>
              </div>
            </div>
            <p className="muted">+{fans.mailing_list_growth_30d || 0} contacts in the last 30 days.</p>
            {!hasMailingList && (
              <div className="empty-state compact-empty">
                <h3>No emails shared yet.</h3>
                <p>Fans can opt in at signup or when they support you.</p>
              </div>
            )}
            <div className="action-grid">
              <button className="secondary" onClick={() => goToPage("profile")}>Full list</button>
              {mailingList?.can_export ? (
                <button className="primary" onClick={exportMailingList}>Export CSV</button>
              ) : (
                <button className="secondary" onClick={() => goToPage("profile")}>Upgrade for CSV</button>
              )}
            </div>
          </div>
        </section>

        {!trust.profile_complete && (
          <section className="anti-bot">
            <div className="tab-title-row">
              <div>
                <p className="eyebrow">Profile trust</p>
                <h3>Complete your profile to unlock full uploads</h3>
              </div>
            </div>
            <p className="muted">{trust.upload_limit_message || "Human-first platform: complete your profile so fans and venues trust you."}</p>
            <div className="beta-task-list">
              {(trust.missing_profile_items || artistTrustStatus?.profile_completion?.missing || []).map(item => (
                <button type="button" className="secondary compact" key={item.key} onClick={() => openTrustChecklistItem(item)}>
                  {item.label}
                </button>
              ))}
            </div>
            {(trust.ai_review_flags || artistTrustStatus?.ai_review_flags || []).length > 0 && (
              <div className="activity-list">
                {(trust.ai_review_flags || artistTrustStatus?.ai_review_flags || []).map(flag => (
                  <article className="activity-item activity-item-clickable" key={flag.id}>
                    <span>review</span>
                    <div>
                      <strong>{flag.upload_title}</strong>
                      <p>{flag.reason}</p>
                    </div>
                    <button type="button" className="secondary compact" onClick={() => openAiReviewFlag(flag)}>
                      Review upload
                    </button>
                  </article>
                ))}
              </div>
            )}
          </section>
        )}

        <section className="home-activity">
          <div className="tab-title-row">
            <div>
              <p className="eyebrow">IndieFund | Spaces</p>
              <h3>Local draw for gigs</h3>
            </div>
            <button className="secondary compact" onClick={() => goToPage("spaces")}>Browse spaces</button>
          </div>
          <div className="home-stat-grid fan-stat-grid">
            <div className="feature-card">
              <p className="eyebrow">Local supporters</p>
              <h3>{spaces.local_supporters || 0}</h3>
              <p>{spaces.message || "Add your city to see local supporter counts."}</p>
            </div>
            <div className="feature-card">
              <p className="eyebrow">Notifyable local contacts</p>
              <h3>{spaces.notifyable_local_supporters || 0}</h3>
              <p>Opted-in supporters you can alert about confirmed gigs.</p>
            </div>
            <div className="feature-card">
              <p className="eyebrow">Upcoming gigs</p>
              <h3>{spaces.upcoming_gigs || 0}</h3>
              <p>Confirmed IndieFund | Spaces bookings.</p>
            </div>
          </div>
          {(spaces.upcoming_bookings || []).length > 0 && (
            <div className="activity-list">
              {spaces.upcoming_bookings.map(booking => (
                <article className="activity-item" key={booking.id}>
                  <span>gig</span>
                  <div>
                    <strong>{booking.venue_name} · {booking.city}</strong>
                    <p>{new Date(booking.starts_at).toLocaleString()}</p>
                  </div>
                </article>
              ))}
            </div>
          )}
        </section>

        {artistProInsights && (
          <section className="home-activity">
            <div className="tab-title-row">
              <div>
                <p className="eyebrow">Artist Pro</p>
                <h3>Development insights</h3>
              </div>
            </div>
            <p className="muted">{artistProInsights.mrr_forecast?.message}</p>
            <div className="home-stat-grid fan-stat-grid">
              <div className="feature-card">
                <p className="eyebrow">MRR forecast (30d)</p>
                <h3>${artistProInsights.mrr_forecast?.projected_mrr_30d || "0.00"}</h3>
                <p>Current ${artistProInsights.mrr_forecast?.current_mrr || "0.00"}</p>
              </div>
              <div className="feature-card">
                <p className="eyebrow">Top converting track</p>
                <h3>{artistProInsights.content_conversion?.top_converting_track?.title || "—"}</h3>
                <p>{artistProInsights.content_conversion?.suggestions?.[0] || "Upload tracks to measure conversion."}</p>
              </div>
            </div>
            <div className="supporter-table">
              <div className="supporter-table-row supporter-table-head">
                <span>Segment</span>
                <span>Count</span>
              </div>
              {(artistProInsights.segments || []).slice(0, 4).map(segment => (
                <div className="supporter-table-row" key={segment.key}>
                  <span>{segment.label}</span>
                  <strong>{segment.count}</strong>
                </div>
              ))}
            </div>
          </section>
        )}

        <section className="home-activity">
          <div className="tab-title-row">
            <div>
              <p className="eyebrow">Music funnel</p>
              <h3>Tracks driving subscribers</h3>
            </div>
          </div>
          {musicFunnelTracks.length === 0 ? (
            <div className="empty-state compact-empty">
              <h3>No music funnel data yet.</h3>
              <p>Play events will appear after fans preview or complete tracks.</p>
            </div>
          ) : (
            <div className="supporter-table">
              <div className="supporter-table-row supporter-table-head">
                <span>Track</span>
                <span>Plays</span>
                <span>Subs</span>
              </div>
              {musicFunnelTracks.slice(0, 6).map(track => (
                <div className="supporter-table-row" key={track.track_id}>
                  <span>{track.title}</span>
                  <strong>{track.preview_plays}/{track.full_plays}</strong>
                  <span>{track.subscriber_conversions_7d}</span>
                </div>
              ))}
            </div>
          )}
        </section>

        <section className="home-activity">
          <div className="tab-title-row">
            <div>
              <p className="eyebrow">Recent activity</p>
              <h3>Last 7 days</h3>
            </div>
          </div>
          <div className="activity-list">
            {recentActivity.length === 0 && (
              <div className="empty-state compact-empty">
                <h3>No recent fan activity.</h3>
                <p>Share your page or invite existing fans to create the first signals.</p>
              </div>
            )}
            {recentActivity.map(item => (
              <article className="activity-item" key={item.id}>
                <span>{item.type}</span>
                <div>
                  <strong>{item.title}</strong>
                  <p>{item.detail}</p>
                </div>
              </article>
            ))}
          </div>
        </section>

        <section className="home-studio-actions">
          <div className="tab-title-row">
            <div>
              <p className="eyebrow">Bring your fans</p>
              <h3>One link for music, store, support, live and posts</h3>
            </div>
          </div>
          <div className="beta-task-list">
            <span>Page link: {artistLink}</span>
            <span>Instagram referrals this month: {instagramSupporters} supporter{instagramSupporters === 1 ? "" : "s"}</span>
            <span>Embed snippet: {embedSnippet}</span>
          </div>
          <div className="action-grid">
            <button className="primary" onClick={() => shareArtistPageLink()}>Copy page link</button>
            <button className="secondary" onClick={() => copyText(instagramLink, "Instagram referral link copied.")}>Copy Instagram link</button>
            <button className="secondary" onClick={() => copyArtistInviteLink()}>Copy invite link</button>
            <button className="secondary" onClick={() => copyText(shareTemplate, "Share message copied.")}>Copy invite message</button>
            <button className="secondary" onClick={() => copyText(embedSnippet, "Embed snippet copied.")}>Copy embed snippet</button>
            <button className="secondary" onClick={() => openStudioTab("feed", { createPost: true })}>Post an update</button>
            {studioSnapshot && isMusicBranchProfession(studioSnapshot.profession) && (
              <button className="secondary" onClick={() => openStudioTab("listen", { createMusic: true })}>Upload track</button>
            )}
            <button className="secondary" onClick={() => openStudioTab("merch")}>Add supporter offer</button>
            <button className="secondary" onClick={() => goToPage("promote")}>Promote a release</button>
          </div>
          <p className="muted">CSV email import should only create invites after fans opt in. Do not paste email lists without permission.</p>
        </section>
      </>
    );
  }

  function getListingLocalDrawState(listing) {
    const cityKey = (listing.city || "").trim().toLowerCase();
    const localDraw = artistLocalDraw[cityKey];
    const localCount = localDraw?.local_supporters ?? null;
    const localDrawLoading = currentUser?.is_artist
      && listing.min_local_supporters > 0
      && !Object.prototype.hasOwnProperty.call(artistLocalDraw, cityKey);
    const meetsLocalRequirement = listing.min_local_supporters <= 0
      || (localCount !== null && localCount >= listing.min_local_supporters);
    return { cityKey, localCount, localDrawLoading, meetsLocalRequirement };
  }

  function openSpaceListingDetail(listing) {
    setSelectedSpaceListing(listing);
  }

  function handleSpaceCardClick(event, listing) {
    if (event.target.closest("button, a, input, textarea, select, label")) return;
    openSpaceListingDetail(listing);
  }

  function requestBookingFromListingDetail(listingId) {
    setSelectedSpaceListing(null);
    openSpaceBookingForm(listingId);
  }

  function renderSpaceListingDetailFooter(listing) {
    if (!currentUser?.is_artist) return null;

    const { localCount, localDrawLoading, meetsLocalRequirement } = getListingLocalDrawState(listing);

    return (
      <div className="space-detail-actions">
        {localDrawLoading ? (
          <p className="muted form-hint">Checking your local supporter count in {listing.city}…</p>
        ) : meetsLocalRequirement ? (
          <button className="primary" type="button" onClick={() => requestBookingFromListingDetail(listing.id)}>
            Request booking
          </button>
        ) : (
          <>
            <p className="muted form-hint">Need more local supporters in {listing.city} to request this room.</p>
            {listing.min_local_supporters > 0 && localCount !== null && (
              <p className="space-draw-warning">
                You need at least {listing.min_local_supporters} local supporters in {listing.city}. You currently have {localCount}.
              </p>
            )}
          </>
        )}
      </div>
    );
  }

  function renderHostListingFeedCard(listing, { own = false } = {}) {
    return (
      <article
        className="space-card host-feed-card space-card--clickable"
        key={`${own ? "mine" : "market"}-${listing.id}`}
        data-testid="space-listing-card"
        onClick={(event) => handleSpaceCardClick(event, listing)}
      >
        <button type="button" className="space-card-preview-button" onClick={() => openSpaceListingDetail(listing)} aria-label={`View photos for ${listing.name}`}>
          <SpaceListingCardPreview listing={listing} photoTypeLabels={SPACE_PHOTO_TYPE_LABELS} />
        </button>
        <div className="space-card-summary">
          <p className="eyebrow">{listing.city || "Local room"} · {listing.capacity} cap</p>
          <h3>{listing.name}</h3>
          <p className="muted">{listing.host_business_name} · {SPACE_SPLIT_LABELS[listing.split_type] || listing.split_type}</p>
          <p className="space-card-teaser">{listing.description || "Flexible room for independent performers."}</p>
        </div>
        <div className="post-badges">
          {listing.tags?.slice(0, 3).map(tag => <span key={tag}>{tag.replaceAll("_", " ")}</span>)}
          {listing.bar_open && <span>Bar open</span>}
          {listing.kitchen_open && <span>Kitchen open</span>}
          {listing.status !== "live" && own && <span>{listing.status}</span>}
        </div>
        <div className="space-meta-grid space-card-meta-compact">
          <span>Availability: {formatAvailabilityWindows(listing.available_windows)}</span>
          <span>Host cut: {listing.split_type === "door_percent" ? `${listing.host_cut_percent}%` : listing.split_type === "flat_fee" ? `$${listing.flat_fee_amount}` : "F&B only"}</span>
        </div>
        {own ? null : (
          <p className="muted form-hint">Tap to view photos and venue details.</p>
        )}
      </article>
    );
  }

  function renderHomeDashboard() {
    if (currentUser.is_artist) {
      return renderArtistDevelopmentDashboard();
    }

    if (currentUser.is_host) {
      return null;
    }

    if (isPrelaunchMode(platformMode) && !canAccessFanExperience(platformMode, currentUser)) {
      return (
        <PrelaunchFanGate
          onArtistSignup={() => openCreatorSignup("artist")}
          onHostSignup={() => openCreatorSignup("host")}
          onFanWaitlist={openFanWaitlist}
          onHome={() => goToPage(isPrelaunchMode(platformMode) ? "early-access" : "home")}
        />
      );
    }

    const supportedCount = getSupportedArtistUsernames().length;
    const checklistItems = getFanSetupChecklistItems();
    const showWelcome = shouldShowHomeWelcome();

    return (
      <>
        <section className={`home-dashboard-head section-head tab-title-row${showWelcome ? "" : " home-dashboard-head--compact"}`}>
          <div>
            <p className="eyebrow">Home</p>
            {showWelcome ? (
              <>
                <h2>Welcome back, {currentUser.display_name || currentUser.username}</h2>
                <p className="muted">Your overview — saves, support, and quick links.</p>
              </>
            ) : (
              <>
                <h2>Your overview</h2>
                <p className="muted">Saves, support, and quick links.</p>
              </>
            )}
          </div>
          <button className="secondary compact" onClick={() => goToPage("notifications")}>
            Notifications
          </button>
        </section>

        <SetupChecklistPanel
          title="Three steps to your local scene"
          subtitle="Save artists you like, build a playlist, then support one to unlock gig alerts and Shows near me."
          items={checklistItems}
          checklistHidden={setupChecklistDismissed}
          onDismiss={dismissSetupChecklist}
        />

        <section className="home-stat-grid fan-stat-grid">
          <div className="feature-card">
            <p className="eyebrow">Supporting</p>
            <h3>{supportedCount}</h3>
            <p>Artists receiving your monthly support.</p>
          </div>
          <div className="feature-card">
            <p className="eyebrow">Saved</p>
            <h3>{savedArtists.length}</h3>
            <p>Artists you are tracking for later.</p>
          </div>
          <div className="feature-card">
            <p className="eyebrow">Monthly support</p>
            <h3>${fanTotal}</h3>
            <p>Direct support flowing from your account.</p>
          </div>
        </section>

        {playingNearYou.length > 0 && !currentUser?.is_host && (
          renderPlayingNearYouSection({
            title: fanChannelUsername ? "Gigs from your artist" : "Local gigs on IndieFund | Spaces",
            filterArtist: fanChannelUsername ? gig => gig.artist_username === fanChannelUsername : null,
          })
        )}

        {fanChannelUsername && getFanNetworkItems().length > 0 && (
          <section className="home-activity">
            <div className="tab-title-row">
              <div>
                <p className="eyebrow">Your artist</p>
                <h3>Recent updates</h3>
              </div>
              <button className="secondary compact" type="button" onClick={() => goToPage("feed")}>Open Feed</button>
            </div>
            <div className="activity-list">
              {renderFanFeedCards(getFanNetworkItems())}
            </div>
          </section>
        )}

        {renderPromotionPlacements(homePromotionPlacements)}

        <section className="feature-grid home-links">
          <button className="feature-card page-link" onClick={() => goToPage("feed")}>
            <p className="eyebrow">Feed</p>
            <h3>Artist updates</h3>
            <p>Posts, drops, and activity from artists you save or support.</p>
          </button>
          <button className="feature-card page-link" onClick={() => goToPage("listen")}>
            <p className="eyebrow">Listen</p>
            <h3>Discover & latest</h3>
            <p>Find new artists, swipe recommendations, and browse the newest uploads.</p>
          </button>
          <button className="feature-card page-link" onClick={() => goToPage("my-music")}>
            <p className="eyebrow">Your library</p>
            <h3>My Playlists</h3>
            <p>Build playlists and let the player keep going while you browse.</p>
          </button>
          <button className="feature-card page-link" onClick={() => goToPage("saved")}>
            <p className="eyebrow">Discovery</p>
            <h3>Saved Artists</h3>
            <p>Review recommendations and revisit artists you have saved.</p>
          </button>
          <button className="feature-card page-link" onClick={() => goToPage("stores")}>
            <p className="eyebrow">Stores</p>
            <h3>Merch & music</h3>
            <p>Shop from artists you support — pick a channel to focus.</p>
          </button>
        </section>
      </>
    );
  }

  function renderFanFeedPage() {
    const feedItems = buildFanFeedItems(20);

    return (
      <>
        <section className="section-head tab-title-row">
          <div>
            <p className="eyebrow">Feed</p>
            <h2>Artist updates</h2>
            <p className="muted">POVs, release news, merch drops, tracks, and posts from artists you follow.</p>
          </div>
        </section>

        <section className="home-activity">
          {feedItems.length === 0 ? (
            <div className="empty-state">
              <h3>{fanChannelUsername ? "No updates from this artist yet." : "No activity yet."}</h3>
              <p>
                {fanChannelUsername
                  ? "Try another channel or check back later."
                  : "Save or support artists to see their latest drops here."}
              </p>
              {fanChannelUsername ? (
                <button className="secondary" type="button" onClick={() => setFanChannelUsername("")}>Show all artists</button>
              ) : (
                <button className="secondary" type="button" onClick={() => goToPage("listen")}>Open Listen</button>
              )}
            </div>
          ) : (
            renderFanFeedCards(feedItems)
          )}
        </section>
      </>
    );
  }

  function resolveStudioTabUrlParam(tab, mapped) {
    if (mapped.shopTab) return mapped.shopTab;
    if (mapped.moreTab) return mapped.moreTab;
    if (LEGACY_PROFILE_TAB_MAP[tab]) return tab;
    return "";
  }

  function openStudioTab(tab, options = {}) {
    const artist = getCurrentArtist();

    if (!artist) {
      setMessage("Your artist page is still loading. Try again in a moment.");
      return;
    }

    setPreviewAsFan(false);
    const onOwnArtistPage = selectedArtist?.owner_username === currentUser?.username;
    if (!onOwnArtistPage) {
      setActivePage("home");
    }
    setSelectedArtist(artist);
    const profession = resolveArtistProfession(artist, options.profession || activeProfession);
    setActiveProfession(profession);

    const mapped = LEGACY_PROFILE_TAB_MAP[tab] || { section: tab };
    setActiveTab(mapped.section || primaryContentTab(profession));
    if (options.shopTab || mapped.shopTab) {
      setActiveShopTab(options.shopTab || mapped.shopTab);
    }
    if (options.moreTab || mapped.moreTab) {
      setActiveMoreTab(options.moreTab || mapped.moreTab);
    }

    if (options.updateUrl !== false) {
      updateArtistPageUrl(artist, profession, {
        replace: true,
        tab: resolveStudioTabUrlParam(tab, mapped),
      });
    }

    if (options.createPost) setShowPostForm(true);
    if (options.createPov) setShowPovForm(true);
    if (options.createMusic) setShowMusicForm(true);
    if (options.createCalendar) setShowCalendarForm(true);
  }

  function renderAccountActions() {
    return (
      <AccountActions
        activePage={activePage}
        activeProfileTab={profileTab}
        cartCount={storeCart.length}
        currentUser={currentUser}
        unreadCount={notificationData.unread_count}
        onCart={() => setShowStoreCart(true)}
        onLogin={() => goToPage("home")}
        onNotifications={() => goToPage("notifications")}
        onOpenProfileTab={(tab, section) => {
          goToPage("profile", true, { tab, section: section || settingsSection });
        }}
      />
    );
  }

  function openProfileTab(tab = "settings", section = settingsSection) {
    goToPage("profile", true, { tab, section });
  }

  function openSettingsSection(section) {
    goToPage("profile", true, { tab: "settings", section });
  }

  function renderMyMusicPlaylistDetail(playlist) {
    if (!playlist) {
      return (
        <div className="empty-state">
          <h3>Playlist not found.</h3>
          <p>Choose a playlist from the sidebar or create a new one.</p>
        </div>
      );
    }

    return (
      <section className="my-music-main-panel playlist-detail">
        <div className="tab-title-row">
          <div>
            <p className="eyebrow">Playlist</p>
            <h3>{playlist.title}</h3>
            <p className="muted">{playlist.description || `${playlist.track_count} saved track${playlist.track_count === 1 ? "" : "s"}`}</p>
          </div>
          {playlist.tracks.length > 0 && (
            <button className="primary compact" type="button" onClick={() => playQueue(playlist.tracks, 0, playlist.title)}>
              Play playlist
            </button>
          )}
        </div>

        {playlist.tracks.length === 0 && (
          <div className="empty-state">
            <h3>This playlist is empty.</h3>
            <p>Add songs from Listen or save tracks while you browse.</p>
            <button className="secondary" type="button" onClick={() => goToListenTab("latest")}>Browse latest music</button>
          </div>
        )}

        <div className="my-music-playlist-tracks">
          {playlist.tracks.map((track, index) => (
            <div className="playlist-track-row" key={track.id}>
              <span>{index + 1}</span>
              <div className="playlist-track-copy">
                {renderTrackTitle(track, { className: "track-name-link" })}
                <small>{renderArtistName(track.artist_username)}</small>
              </div>
              <button className="secondary compact" type="button" onClick={() => handleTogglePlay(track)}>Play</button>
              <button className="secondary compact" type="button" onClick={() => removeTrackFromPlaylist(track, playlist.id)}>Remove</button>
            </div>
          ))}
        </div>
      </section>
    );
  }

  function renderMyMusicSidebar() {
    const savedTrackCount = getMyMusicTracks().length;

    return (
      <aside className="my-music-sidebar">
        <div className="my-music-sidebar-head">
          <p className="eyebrow">Playlists</p>
          <button className="secondary compact" type="button" onClick={() => goToListenTab("latest")}>Browse music</button>
        </div>

        <nav className="my-music-sidebar-nav" aria-label="My Playlists">
          <button
            type="button"
            className={myMusicSidebarView === "artists" ? "my-music-sidebar-item active" : "my-music-sidebar-item"}
            onClick={() => setMyMusicSidebarView("artists")}
          >
            <strong>Saved by artist</strong>
            <span>{savedTrackCount} track{savedTrackCount === 1 ? "" : "s"}</span>
          </button>

          {fanPlaylists.map(playlist => (
            <button
              key={playlist.id}
              type="button"
              className={myMusicSidebarView === String(playlist.id) ? "my-music-sidebar-item active" : "my-music-sidebar-item"}
              onClick={() => {
                setMyMusicSidebarView(String(playlist.id));
                setSelectedPlaylistId(playlist.id);
              }}
            >
              <strong>{playlist.title}</strong>
              <span>{playlist.track_count} track{playlist.track_count === 1 ? "" : "s"}</span>
            </button>
          ))}
        </nav>

        {fanPlaylists.length === 0 && (
          <p className="muted my-music-sidebar-empty">Create a playlist to organize saves beyond your artist library.</p>
        )}

        <form className="my-music-sidebar-create" onSubmit={createFanPlaylist}>
          <input name="title" required placeholder="New playlist name" aria-label="New playlist name" />
          <input name="description" type="hidden" value="" />
          <button className="secondary compact" type="submit">+ Create playlist</button>
        </form>
      </aside>
    );
  }

  function renderMyMusicLayout() {
    const activePlaylist = fanPlaylists.find(playlist => String(playlist.id) === myMusicSidebarView);

    return (
      <div className="my-music-layout">
        {currentUser && renderMyMusicSidebar()}
        <div className="my-music-main">
          {myMusicSidebarView === "artists" || !currentUser
            ? renderMyMusicByArtistSection()
            : renderMyMusicPlaylistDetail(activePlaylist)}
        </div>
      </div>
    );
  }

  function isThemePreviewActive() {
    if (!themePreview || !currentUser) return false;
    if (activePage === "profile" && profileTab === "themes") return true;
    return Boolean(
      selectedArtist
      && selectedArtist.owner_username === currentUser.username
      && activeTab === "more"
      && activeMoreTab === "settings"
    );
  }

  function resolveThemePreviewClass() {
    if (!isThemePreviewActive()) return null;
    if (themePreview.target === "studio") {
      return normalizeThemeId(themePreview.studioTheme);
    }
    if (currentUser?.is_host) {
      return normalizeHostThemeId(themePreview.fanTheme);
    }
    return normalizeThemeId(themePreview.fanTheme);
  }

  function resolvePersonalThemeForApp() {
    const previewClass = resolveThemePreviewClass();
    if (previewClass) return previewClass;
    return resolvePersonalAppTheme(currentUser, getCurrentArtist());
  }

  function resolveLiveArtistThemeName(artist, { isOwner, previewAsFan, activeTab: studioTab, activeMoreTab: studioMoreTab }) {
    const base = resolveArtistThemeName(artist, { isOwner, previewAsFan });
    if (!themePreview || !isOwner || artist?.owner_username !== currentUser?.username) {
      return base;
    }

    const inStudioThemes = studioTab === "more" && studioMoreTab === "settings";
    const inProfileThemes = activePage === "profile" && profileTab === "themes";
    if (!inStudioThemes && !inProfileThemes) {
      return base;
    }

    if (themePreview.target === "studio" && !previewAsFan) {
      return normalizeThemeId(themePreview.studioTheme);
    }
    if (themePreview.target === "fan") {
      return normalizeThemeId(themePreview.fanTheme);
    }
    return base;
  }

  function resolveAppShellPageClass() {
    const theme = resolvePersonalThemeForApp();
    return `${theme} page-shell-${activePage}`;
  }

  function renderAppShell(content, pageClass = "") {
    const showNavigation = Boolean(currentUser) || Boolean(selectedArtist) || GUEST_SHELL_PAGES.has(activePage) || LEGAL_PAGE_IDS.has(activePage);
    const myMusicTrackCount = getMyMusicTracks().length;

    const spacesNavItem = {
      id: "spaces",
      kind: "page",
      page: "spaces",
      icon: "S",
      label: "Spaces",
      detail: currentUser?.is_host ? "Your rooms" : "Book rooms",
      onClick: () => goToPage("spaces"),
    };

    const ticketStubNavItem = {
      id: "ticket-stub",
      kind: "action",
      icon: <TicketStubNavIcon />,
      label: "Ticket stub",
      detail: "Door check-in codes",
      isActive: showTicketStubSheet,
      onClick: () => setShowTicketStubSheet(true),
    };

    const hostNav = [spacesNavItem, ticketStubNavItem];

    const fanNav = currentUser?.is_host ? hostNav : [
      { id: "home", kind: "page", page: "home", icon: "H", label: currentUser?.is_artist ? "Dashboard" : "Home", detail: currentUser?.is_artist ? "Business health" : "Overview", onClick: () => goToPage("home") },
      ...(!currentUser?.is_artist && !currentUser?.is_host ? [
        { id: "feed", kind: "page", page: "feed", icon: "F", label: "Feed", detail: "Artist updates", onClick: () => goToPage("feed") },
        {
          id: "my-scene",
          kind: "page",
          page: "my-scene",
          icon: "G",
          label: "Shows near me",
          detail: "Browse & buy tickets",
          onClick: () => goToPage("my-scene"),
        },
        { id: "stores", kind: "page", page: "stores", icon: "$", label: "Stores", detail: "Merch & music", onClick: () => goToPage("stores") },
      ] : []),
      { id: "listen", kind: "page", page: "listen", icon: "L", label: "Listen", detail: "Discover & latest", onClick: () => goToPage("listen") },
      { id: "my-music", kind: "page", page: "my-music", icon: "♫", label: "My Playlists", detail: `${myMusicTrackCount} saved tracks`, onClick: () => goToPage("my-music") },
      ...(currentUser?.is_artist || currentUser?.is_host ? [spacesNavItem] : []),
      ...(!currentUser?.is_artist ? [
        {
          id: "themes",
          kind: "action",
          icon: "◐",
          label: currentUser?.is_host ? "My theme" : "Themes",
          detail: currentUser?.is_host ? "Dashboard colours" : "Profile colours",
          isActive: activePage === "profile" && profileTab === "themes",
          onClick: () => openProfileTab("themes"),
        },
      ] : []),
    ];

    const artistNav = currentUser?.is_artist ? [
      { id: "create", kind: "studio", tab: "feed", activeTabs: ["feed", "live", "more"], icon: "+", label: "Create", detail: "Post or drop", onClick: () => openStudioTab("feed", { createPost: true }) },
      { id: "fans", kind: "page", page: "fans", icon: "♥", label: "Fans", detail: "CRM & messages", onClick: () => goToPage("fans") },
      { id: "promote", kind: "page", page: "promote", icon: "P", label: "Promote", detail: "Discovery ads", onClick: () => goToPage("promote") },
      { id: "ads-manager", kind: "page", page: "ads-manager", icon: "A", label: "Ads Manager", detail: "Growth campaigns", onClick: () => goToPage("ads-manager") },
      { id: "store", kind: "studio", tab: "shop", shopTab: "merch", activeTabs: ["shop"], icon: "$", label: "Merch", detail: "Merch store", onClick: () => openStudioTab("merch") },
      { id: "music-store", kind: "studio", tab: "shop", shopTab: "music-store", activeTabs: ["shop"], icon: "♫", label: "Music Store", detail: "Vinyl & Digital", onClick: () => openStudioTab("music-store") },
      { id: "themes", kind: "action", icon: "◐", label: "Themes", detail: "Page colours", isActive: activePage === "profile" && profileTab === "themes", onClick: () => openProfileTab("themes") },
    ] : [];

    const guestNav = filterNavItemsForPlatform([
      { id: "home", kind: "page", page: "home", icon: "H", label: "Home", detail: "IndieFund", onClick: () => { setSelectedArtist(null); window.history.pushState({}, "", window.location.pathname); setActivePage("home"); } },
      ...(isPrelaunchMode(platformMode)
        ? [{ id: "signup", kind: "page", page: "profile", icon: "→", label: "Early signup", detail: "Artist or host", onClick: () => openCreatorSignup("artist") }]
        : [{ id: "listen", kind: "page", page: "listen", icon: "L", label: "Listen", detail: "Discover & latest", onClick: () => goToPage("listen") }]),
      { id: "faq", kind: "page", page: "faq", icon: "?", label: "FAQ", detail: "How it works", onClick: () => goToPage("faq") },
      { id: "login", kind: "page", page: "profile", icon: "→", label: isPrelaunchMode(platformMode) ? "Log in" : "Sign up", detail: isPrelaunchMode(platformMode) ? "Creator account" : "Free fan account", onClick: () => goToPage("profile") },
    ]);

    const profileNavItem = { id: "profile", kind: "page", page: "profile", icon: "⋯", label: "More", detail: "Account", onClick: () => goToPage("profile") };

    const mobileNav = !currentUser
      ? guestNav
      : currentUser.is_artist
        ? filterNavItemsForPlatform([
            fanNav[0],
            fanNav.find(item => item.id === "listen"),
            fanNav.find(item => item.id === "spaces"),
            artistNav[0],
            profileNavItem,
          ].filter(Boolean))
        : currentUser.is_host
          ? filterNavItemsForPlatform([
              fanNav.find(item => item.id === "spaces"),
              fanNav.find(item => item.id === "ticket-stub"),
              profileNavItem,
            ].filter(Boolean))
          : filterNavItemsForPlatform([
              fanNav[0],
              fanNav.find(item => item.id === "feed"),
              fanNav.find(item => item.id === "my-scene"),
              fanNav.find(item => item.id === "stores"),
              profileNavItem,
            ].filter(Boolean));

    return (
      <>
        {currentUser?.is_host && (
          <TicketStubSheet
            open={showTicketStubSheet}
            onClose={() => setShowTicketStubSheet(false)}
            bookings={spaceBookings}
            apiFetch={apiFetch}
            onMessage={setMessage}
          />
        )}
        <AppShell
          activePage={activePage}
          activeTab={activeTab}
          activeShopTab={activeShopTab}
          accountActions={renderAccountActions()}
          artistNav={artistNav}
          currentUser={currentUser}
          fanNav={fanNav}
          guestNav={guestNav}
          mobileNav={mobileNav}
          onRefresh={refreshCurrentView}
          pageClass={pageClass}
          playerActive={Boolean(currentTrack)}
          previewAsFan={previewAsFan}
          pullRefreshDisabled={Boolean(
            showSpaceListingForm
            || showTicketStubSheet
            || spaceReviewTarget
            || pendingSupportArtist
            || showStoreCart
            || pendingExternalLink
            || playlistPickerTrack
          )}
          selectedArtist={selectedArtist}
          onHome={() => goToPage(currentUser?.is_host ? "spaces" : "home")}
          showNavigation={showNavigation}
          legalFooter={<LegalFooter onNavigate={goToPage} />}
        >
          {content}
        </AppShell>
        <GlobalPlayer
          track={currentTrack}
          isPlaying={isPlaying}
          onClose={handleClosePlayer}
          onEnded={handlePlayerEnded}
          onTogglePlay={handleTogglePlay}
          onPlaybackEvent={recordMusicPlaybackEvent}
          onNext={playNextTrack}
          onPrevious={playPreviousTrack}
          onOpenArtistByUsername={openArtistByUsername}
          audioRef={audioRef}
          queueLabel={playbackSource?.label || ""}
          queuePosition={playbackQueue.length ? playbackIndex + 1 : 0}
          queueTotal={playbackQueue.length}
        />
      </>
    );
  }

  async function handleAuth(event) {
    event.preventDefault();

    const form = event.target;
    const formData = new FormData(form);
    const payload = Object.fromEntries(formData.entries());
    if (authMode === "register" && payload.user_type === "artist") {
      const professions = formData.getAll("professions");
      payload.professions = professions.length ? professions : [DEFAULT_PROFESSION];
    }
    if (authMode === "register") {
      payload.terms_accepted = formData.get("terms_accepted") === "true";
      if (!payload.terms_accepted) {
        setMessage("Please accept the Terms of Service and Privacy Policy to create an account.");
        return;
      }
    }
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
      if (data.code === "prelaunch_fan_registration_closed") {
        setAuthMode("waitlist");
      }
      setMessage(data.error || "Authentication failed.");
      return;
    }

    setCurrentUser(data.user);
    form.reset();
    loadData();
    loadDiscovery();
    loadSavedArtists();

    if (authMode === "register" && data.user?.is_host) {
      setSearchLocation(data.user?.discovery_location || "");
      goToPage("spaces");
      setShowSpaceListingForm(true);
    } else if (data.user?.is_host) {
      setSearchLocation(data.user?.discovery_location || "");
      goToPage("spaces");
    } else {
      if (data.user?.is_artist) {
        await loadData();
      }
      setSearchLocation(data.user?.discovery_location || "");
      goToPage("home");
    }
  }

  async function handleWaitlist(event) {
    event.preventDefault();

    const form = event.target;
    const formData = new FormData(form);
    const payload = {
      email: formData.get("email"),
      city: formData.get("city") || "",
      favorite_genres: formData.get("favorite_genres") || "",
      terms_accepted: formData.get("terms_accepted") === "true",
    };

    if (!payload.terms_accepted) {
      setMessage("Please accept the Privacy Policy to join the waitlist.");
      return;
    }

    if (!getCookie("csrftoken")) {
      await apiFetch("/accounts/current-user/");
    }

    const res = await apiFetch("/accounts/waitlist/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await res.json();

    if (!res.ok) {
      setMessage(data.error || "Unable to join waitlist.");
      return;
    }

    setMessage(data.message || "You are on the launch waitlist.");
    form.reset();
  }

  async function handleLogout() {
    const res = await apiFetch("/accounts/logout/", { method: "POST" });
    let logoutMessage = "Logged out.";

    if (res.ok) {
      const data = await res.json();
      logoutMessage = data.message || logoutMessage;
    } else {
      logoutMessage = "Session ended on this device.";
    }

    setCurrentUser(null);
    setSavedArtists([]);
    setDiscoveryArtists([]);
    setDiscoveryTracks([]);
    setDiscoveryMeta({ skipped_count: 0, count: 0, exhausted: false });
    setDiscoveryTrackMeta({ skipped_count: 0, count: 0, exhausted: false });
    setSelectedArtist(null);
    setActivePage("home");
    setMessage(logoutMessage);
    window.history.replaceState({}, "", window.location.pathname);
    loadData();
  }

  async function submitBetaFeedback(event) {
    event.preventDefault();

    if (!currentUser) {
      setMessage("Log in before sending beta feedback.");
      return;
    }

    const form = event.target;
    const payload = Object.fromEntries(new FormData(form).entries());

    const res = await apiFetch("/accounts/beta-feedback/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await res.json();

    if (!res.ok) {
      setMessage(data.error || "Unable to send beta feedback.");
      return;
    }

    setMessage(data.message || "Thanks, beta feedback recorded.");
    form.reset();
    loadCurrentUser();
    if (currentUser?.user_type === "admin") {
      loadBetaFeedbackSummary();
    }
  }

  const artistTracks = selectedArtist
    ? music.filter(track =>
        track.artist_username === selectedArtist.owner_username &&
        (track.profession || DEFAULT_PROFESSION) === activeProfession
      )
    : [];

  const artistArtworks = selectedArtist
    ? artworks.filter(artwork =>
        artwork.artist_username === selectedArtist.owner_username &&
        (artwork.profession || DEFAULT_PROFESSION) === activeProfession
      )
    : [];

  const artistPosts = selectedArtist
    ? posts.filter(post =>
        post.author_username === selectedArtist.owner_username &&
        (post.profession || DEFAULT_PROFESSION) === activeProfession
      )
    : [];

  const artistPovs = selectedArtist
    ? povs.filter(pov =>
        pov.artist_username === selectedArtist.owner_username &&
        (!pov.profession || pov.profession === activeProfession)
      )
    : [];

  const artistInstants = selectedArtist
    ? instants.filter(instant => instant.artist_username === selectedArtist.owner_username)
    : [];

  const artistProducts = selectedArtist
    ? products.filter(product =>
        product.artist_username === selectedArtist.owner_username &&
        (product.profession || DEFAULT_PROFESSION) === activeProfession
      )
    : [];

  const artistCalendarItems = selectedArtist
    ? [
        ...(calendarItems || []),
        ...(selectedArtist.upcoming_calendar_items || []),
      ]
        .filter((item, index, list) =>
          item.artist_username === selectedArtist.owner_username &&
          (item.profession || DEFAULT_PROFESSION) === activeProfession &&
          list.findIndex(candidate => candidate.id === item.id) === index
        )
        .sort((a, b) => new Date(a.starts_at) - new Date(b.starts_at))
    : [];

  const fanTotal = currentUser ? subData.fan_totals?.[currentUser.username] || "0.00" : "0.00";
  const filteredArtists = fanChannelUsername
    ? discoveryArtists.filter(artist => artist.owner_username === fanChannelUsername)
    : discoveryArtists;
  const filteredTracks = fanChannelUsername
    ? discoveryTracks.filter(track => track.artist_username === fanChannelUsername)
    : discoveryTracks;
  const savedGenres = [...new Set(savedArtists.map(artist => artist.genre).filter(Boolean))].sort();
  const filteredSavedArtists = savedArtists.filter(artist => {
    const query = savedSearchQuery.trim().toLowerCase();
    const queryMatch = query
      ? [artist.stage_name, artist.owner_username, artist.genre, artist.city]
          .some(value => value?.toLowerCase().includes(query))
      : true;
    const genreMatch = savedGenreFilter ? artist.genre === savedGenreFilter : true;
    const channelMatch = fanChannelUsername ? artist.owner_username === fanChannelUsername : true;
    return queryMatch && genreMatch && channelMatch;
  });
  const reviewArtist = filteredArtists[reviewIndex] || filteredArtists[0];
  const reviewTrack = filteredTracks[reviewIndex] || filteredTracks[0];
  const latestMusicTracks = fanChannelUsername
    ? music.filter(track => track.artist_username === fanChannelUsername)
    : music;

  function resolvePlayableDiscoveryTrack(track) {
    if (!track) return null;
    if (track.audio_file) return track;
    if (track.preview_audio_file) {
      return {
        ...track,
        audio_file: track.preview_audio_file,
        is_preview_playback: true,
        preview_limit_seconds: track.preview_seconds || 30,
      };
    }
    return null;
  }

  function resolveDiscoveryPreviewTrack(artist) {
    const embedded = artist?.preview_track;
    if (embedded) {
      if (embedded.audio_file) {
        return {
          ...embedded,
          artist_username: artist.owner_username,
        };
      }
      if (embedded.preview_audio_file) {
        return {
          ...embedded,
          artist_username: artist.owner_username,
          audio_file: embedded.preview_audio_file,
          is_preview_playback: true,
          preview_limit_seconds: embedded.preview_seconds || 30,
        };
      }
    }

    const artistTracks = music
      .filter(track => track.artist_username === artist.owner_username)
      .sort((a, b) => new Date(b.created_at || 0) - new Date(a.created_at || 0));
    const track = artistTracks.find(item => item.audio_file) || artistTracks.find(item => item.preview_audio_file);
    if (!track) return null;
    if (track.audio_file) return track;
    return {
      ...track,
      audio_file: track.preview_audio_file,
      is_preview_playback: true,
      preview_limit_seconds: track.preview_seconds || 30,
    };
  }

  useEffect(() => {
    if (activePage === "listen" && listenTab === "discover" && discoverView === "recommendations") {
      return;
    }
    if (!playbackSource?.discovery) {
      return;
    }
    setIsPlaying(false);
    setCurrentTrack(null);
    setPlaybackSource(null);
  }, [activePage, discoverView, playbackSource?.discovery]);

  useEffect(() => {
    setReviewIndex(0);
  }, [searchQuery, searchLocation, searchProfession, currentUser?.id, discoveryMode]);

  function advanceReview() {
    const itemCount = discoveryMode === "songs" ? filteredTracks.length : filteredArtists.length;
    setReviewIndex(current => {
      if (itemCount <= 1) return 0;
      return Math.min(current + 1, itemCount - 1);
    });
  }

  function resetSwipeState() {
    swipeRef.current = { startX: null, startY: null, axis: null, pointerId: null };
    setIsSwiping(false);
    setSwipeDeltaX(0);
  }

  function startReviewSwipe(event) {
    if (event.pointerType === "mouse" && event.button !== 0) return;

    swipeRef.current = {
      startX: event.clientX,
      startY: event.clientY,
      axis: null,
      pointerId: event.pointerId,
    };
  }

  function moveReviewSwipe(event) {
    const swipe = swipeRef.current;
    if (swipe.startX === null || event.pointerId !== swipe.pointerId) return;

    const deltaX = event.clientX - swipe.startX;
    const deltaY = event.clientY - swipe.startY;

    if (!swipe.axis) {
      if (Math.abs(deltaX) < 10 && Math.abs(deltaY) < 10) return;
      swipe.axis = Math.abs(deltaX) >= Math.abs(deltaY) ? "x" : "y";
      if (swipe.axis === "y") {
        resetSwipeState();
        return;
      }

      const panel = reviewPanelRef.current;
      if (panel) panel.setPointerCapture(event.pointerId);
      setIsSwiping(true);
    }

    event.preventDefault();
    setSwipeDeltaX(Math.max(-140, Math.min(140, deltaX)));
  }

  function finishReviewSwipe(event) {
    const swipe = swipeRef.current;
    if (swipe.startX === null) return;

    const panel = reviewPanelRef.current;
    if (panel && swipe.pointerId !== null) {
      try {
        panel.releasePointerCapture(swipe.pointerId);
      } catch {
        // Pointer may already be released.
      }
    }

    const delta = event.clientX - swipe.startX;
    const axis = swipe.axis;
    resetSwipeState();

    if (axis !== "x" || Math.abs(delta) < 80) return;

    if (discoveryMode === "songs") {
      if (!reviewTrack) return;
      if (!currentUser) {
        advanceReview();
        return;
      }
      if (delta < 0) {
        sendDiscoveryTrackSignal(reviewTrack, "skip");
        return;
      }
      sendDiscoveryTrackSignal(reviewTrack, "save");
      return;
    }

    if (!reviewArtist) return;

    if (!currentUser) {
      advanceReview();
      return;
    }

    if (delta < 0) {
      sendDiscoverySignal(reviewArtist, "skip");
      return;
    }

    sendDiscoverySignal(reviewArtist, "save");
  }

  function cancelReviewSwipe(event) {
    const swipe = swipeRef.current;
    if (swipe.startX === null) return;

    const panel = reviewPanelRef.current;
    if (panel && swipe.pointerId !== null) {
      try {
        panel.releasePointerCapture(swipe.pointerId);
      } catch {
        // Pointer may already be released.
      }
    }

    resetSwipeState();
  }

  function renderSupportButton(artist, supporting, size = "default", profession = activeProfession) {
    const label = professionLabel(profession);
    const prompt = supporting
      ? `Manage monthly support for ${artist.stage_name}'s ${label}.`
      : `Support ${artist.stage_name}'s ${label} for $1 a month?`;

    return (
      <button
        className={`support-dollar ${supporting ? "supported" : ""} ${size}`}
        onClick={() => requestSupport(artist, supporting, profession)}
        title={prompt}
        aria-label={prompt}
      >
        $
      </button>
    );
  }

  function getMinimumSupportAmount(artist, profession = activeProfession) {
    const tierAmounts = supportTiers
      .filter(tier => tier.artist === artist.owner_username && tier.profession === profession)
      .map(tier => Number(tier.monthly_amount))
      .filter(amount => Number.isFinite(amount) && amount > 0);
    if (tierAmounts.length === 0) return "1";
    return Math.min(...tierAmounts).toFixed(0);
  }

  function artistFromUsername(username) {
    return artists.find(artist => artist.owner_username === username)
      || discoveryArtists.find(artist => artist.owner_username === username)
      || savedArtists.find(artist => artist.owner_username === username)
      || (selectedArtist?.owner_username === username ? selectedArtist : null);
  }

  function renderArtistName(username, options = {}) {
    if (!username) return options.fallbackText || null;

    const {
      label,
      artist,
      className,
      verified = false,
      stopPropagation = false,
      fallback = {},
      knownOnly = false,
    } = options;
    const resolvedArtist = artist || artistFromUsername(username);

    return (
      <ArtistNameLink
        username={username}
        label={label}
        artist={resolvedArtist}
        onOpenArtist={openArtistByUsername}
        className={className}
        verified={verified}
        stopPropagation={stopPropagation}
        fallback={{ ...fallback, stage_name: label || fallback.stage_name }}
        knownOnly={knownOnly}
      />
    );
  }

  function renderTrackTitle(track, options = {}) {
    if (!track?.title) return options.fallbackText || null;

    const { className, stopPropagation = false, fallback = {} } = options;
    const artist = track.artist_username ? artistFromUsername(track.artist_username) : null;

    return (
      <TrackNameLink
        track={track}
        onOpenArtist={openArtistByUsername}
        className={className}
        stopPropagation={stopPropagation}
        fallback={{
          ...fallback,
          stage_name: fallback.stage_name || artist?.stage_name || track.artist?.stage_name,
        }}
      />
    );
  }

  function renderNetworkItemTitle(item) {
    if (item.artistUsername && item.action) {
      return (
        <>
          {renderArtistName(item.artistUsername)}
          {" "}{item.action}
        </>
      );
    }
    return item.headline || item.title;
  }

  function renderNetworkItemDetail(item) {
    if (item.detailArtistUsername && item.detailSuffix) {
      return (
        <>
          {renderArtistName(item.detailArtistUsername)}
          {" "}{item.detailSuffix}
        </>
      );
    }
    return item.detail;
  }

  function renderLockedContentPrompt(artist, label = "this") {
    if (!artist) {
      return <p className="muted">Supporters only</p>;
    }

    return (
      <div className="locked-support">
        <div>
          <strong>Support for $1/month</strong>
          <p className="muted">
            Unlock {label} and supporter-only drops from{" "}
            {renderArtistName(artist.owner_username, { label: artist.stage_name, artist })}.
          </p>
        </div>
        {renderSupportButton(
          artist,
          isSupporting(artist.owner_username, getDefaultProfession(artist)),
          "small",
          getDefaultProfession(artist)
        )}
      </div>
    );
  }

  function renderLockedTrackPrompt(track) {
    const artist = artistFromUsername(track.artist_username);
    if (track.preview_audio_file) {
      const previewTrack = {
        ...track,
        audio_file: track.preview_audio_file,
        is_preview_playback: true,
        preview_limit_seconds: track.preview_seconds || 30,
      };
      return (
        <div className="locked-support">
          <div>
            <strong>Preview available</strong>
            <p className="muted">Subscribe to unlock full track.</p>
          </div>
          <div className="action-grid">
            <button className="secondary compact" onClick={() => handleTogglePlay(previewTrack)}>
              {currentTrack?.id === track.id && currentTrack?.is_preview_playback && isPlaying ? "Pause Preview" : `Play ${track.preview_seconds || 30}s Preview`}
            </button>
            {artist && renderSupportButton(
              artist,
              isSupporting(artist.owner_username, getDefaultProfession(artist)),
              "small",
              getDefaultProfession(artist)
            )}
          </div>
        </div>
      );
    }
    return renderLockedContentPrompt(artist, "this track");
  }

  function renderLockedProductPrompt(product) {
    return renderLockedContentPrompt(artistFromUsername(product.artist_username), "this item");
  }

  function renderProductTitle(product) {
    if (!isOwner || previewAsFan) {
      return <h3>{product.title}</h3>;
    }

    return (
      <h3>
        <button
          type="button"
          className="product-title-link"
          aria-label={`Copy link for ${product.title}`}
          onClick={() => copyProductLink(product)}
        >
          {product.title}
        </button>
      </h3>
    );
  }

  function renderProductLinkAction(product) {
    if (!isOwner || previewAsFan) return null;

    return (
      <button
        className="secondary compact product-copy-link"
        type="button"
        onClick={() => copyProductLink(product)}
      >
        Copy product link
      </button>
    );
  }

  function openChallengeAction(challenge) {
    const actions = {
      "post-instant": () => openStudioTab("feed", { createPost: true }),
      "add-update-pov": () => openStudioTab("feed", { createPov: true }),
      "reply-comments": () => openStudioTab("feed"),
      "go-live": () => openStudioTab("lives"),
      "add-public-calendar-items": () => openStudioTab("calendar", { createCalendar: true }),
      "new-subscriber": () => copyArtistInviteLink(),
      "book-spaces-gig": () => goToPage("spaces"),
    };
    (actions[challenge?.slug] || (() => openStudioTab("feed")))();
  }

  function getArtistGrowthNextAction() {
    const studioSnapshot = getArtistStudioSnapshot(getCurrentArtist(), activeProfession);
    const hasTier = (studioSnapshot?.supportTiers?.length || 0) > 0;

    if (hasTier && !connectStatus?.payouts_enabled && !connectStatus?.demo_mode) {
      return {
        label: "Set up payouts",
        detail: "You have a support tier live — connect Stripe so subscriptions and store sales reach your bank.",
        buttonLabel: "Set up payouts",
        onClick: startPayoutOnboarding,
      };
    }

    const nextChallenge = getFirstIncompleteChallenge(challengeBoard);
    if (nextChallenge) {
      return {
        label: nextChallenge.title,
        detail: nextChallenge.description,
        buttonLabel: "Start challenge",
        onClick: () => openChallengeAction(nextChallenge),
      };
    }

    return null;
  }

  function renderChallengeBoard() {
    if (!challengeBoard) return null;

    const renderChallenge = item => {
      const percent = Math.min(100, Math.round((item.progress / Math.max(item.target_count, 1)) * 100));
      return (
        <article className={item.completed ? "challenge-card completed" : "challenge-card"} key={item.id}>
          <div className="challenge-card-top">
            <strong>{item.title}</strong>
            <span>{item.progress}/{item.target_count}</span>
          </div>
          <p>{item.description}</p>
          <div className="challenge-progress" aria-label={`${percent}% complete`}>
            <span style={{ width: `${percent}%` }}></span>
          </div>
        </article>
      );
    };

    return (
      <section className="challenge-board">
        <div className="tab-title-row">
          <div>
            <p className="eyebrow">Challenges</p>
            <h3>Engagement board</h3>
          </div>
          <div className="challenge-stats">
            <span>{challengeBoard.streak?.current_streak || 0}-day streak</span>
            <span>{challengeBoard.growth_points || 0} pts</span>
          </div>
        </div>

        <div className="challenge-columns">
          <div>
            <h4>Daily</h4>
            <div className="challenge-list">
              {(challengeBoard.daily || []).map(renderChallenge)}
            </div>
          </div>
          <div>
            <h4>Weekly</h4>
            <div className="challenge-list">
              {(challengeBoard.weekly || []).map(renderChallenge)}
            </div>
          </div>
        </div>
      </section>
    );
  }

  function getSupportedArtistUsernames() {
    if (!currentUser) return [];

    return subData.subscriptions
      ?.filter(sub => sub.fan_id === currentUser.id && sub.active)
      .map(sub => sub.artist) || [];
  }

  function getFanSubscriptionChannels() {
    if (!currentUser) return [];

    const seen = new Set();
    const channels = [];

    for (const sub of subData.subscriptions || []) {
      if (sub.fan_id !== currentUser.id || !sub.active) continue;
      const username = sub.artist;
      if (!username || seen.has(username)) continue;
      seen.add(username);

      const fromList = artists.find(item => item.owner_username === username);
      const fromSaved = savedArtists.find(item => item.owner_username === username);
      channels.push({
        username,
        stage_name: fromList?.stage_name || fromSaved?.stage_name || username,
        hero_image: fromList?.hero_image || fromSaved?.hero_image || "",
        owner_id: fromList?.owner_id || fromSaved?.owner_id,
      });
    }

    return channels.sort((a, b) => a.stage_name.localeCompare(b.stage_name));
  }

  function showFanArtistRail() {
    return Boolean(
      currentUser &&
      !currentUser.is_artist &&
      !currentUser.is_host &&
      FAN_ARTIST_RAIL_PAGES.has(activePage) &&
      getFanSubscriptionChannels().length > 0
    );
  }

  function renderFanArtistRail() {
    return (
      <FanSubscriptionsRail
        channels={getFanSubscriptionChannels()}
        activeUsername={fanChannelUsername}
        compact
        onSelectAll={() => setFanChannelUsername("")}
        onSelectArtist={(channel) => setFanChannelUsername(channel.username)}
      />
    );
  }

  function renderListenSectionHead() {
    return (
      <section id="listen" className="section-head tab-title-row">
        <div>
          <p className="eyebrow">IndieFund | Listen</p>
          <h2>Listen</h2>
          <p className="muted">Discover new artists and browse the latest independent drops.</p>
        </div>
        {currentUser && listenTab === "discover" && (
          <button className="secondary" onClick={() => goToPage("saved")}>
            View Saved Artists{savedArtists.length ? ` (${savedArtists.length})` : ""}
          </button>
        )}
        {currentUser && listenTab === "latest" && (
          <button className="secondary" onClick={() => goToPage("my-music")}>Open My Playlists</button>
        )}
      </section>
    );
  }

  function renderListenTabRow() {
    return (
      <section className="listen-tab-row fan-page-tab-row">
        <div className="discovery-mode-toggle" role="tablist" aria-label="Listen sections">
          <button
            type="button"
            role="tab"
            aria-selected={listenTab === "discover"}
            className={listenTab === "discover" ? "discovery-mode-pill active" : "discovery-mode-pill"}
            onClick={() => goToListenTab("discover")}
          >
            Discover
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={listenTab === "latest"}
            className={listenTab === "latest" ? "discovery-mode-pill active" : "discovery-mode-pill"}
            onClick={() => goToListenTab("latest")}
          >
            Latest
          </button>
        </div>
      </section>
    );
  }

  function renderStoresSectionHead() {
    return (
      <section className="section-head tab-title-row">
        <div>
          <p className="eyebrow">IndieFund | Stores</p>
          <h2>Stores</h2>
          <p className="muted">
            Browse merch and music from artists you support. Use Your artists above to focus on one channel.
          </p>
        </div>
      </section>
    );
  }

  function renderStoresTabRow() {
    return (
      <section className="listen-tab-row fan-page-tab-row">
        <div className="discovery-mode-toggle" role="tablist" aria-label="Store type">
          <button
            type="button"
            role="tab"
            aria-selected={storeTab === "merch"}
            className={storeTab === "merch" ? "discovery-mode-pill active" : "discovery-mode-pill"}
            onClick={() => goToStoreTab("merch")}
          >
            Merch store
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={storeTab === "music-store"}
            className={storeTab === "music-store" ? "discovery-mode-pill active" : "discovery-mode-pill"}
            onClick={() => goToStoreTab("music-store")}
          >
            Music store
          </button>
        </div>
      </section>
    );
  }

  function isImageMediaUrl(url) {
    if (!url) return false;
    return /\.(jpe?g|png|webp|gif)(\?|$)/i.test(url);
  }

  function getArtistFeedMeta(username) {
    const artist = artistFromUsername(username);
    return {
      stageName: artist?.stage_name || username,
      heroImage: artist?.hero_image || "",
    };
  }

  function postFeedLabel(post) {
    if (post.post_type === "story") return "Story";
    if (post.post_type === "music") return "Release news";
    if (post.post_type === "live") return "Live";
    if (post.post_type === "instagram") return "Instagram";
    if (post.post_type === "tiktok") return "TikTok";
    return "Update";
  }

  function storeFeedLabel(product) {
    const type = product.product_type;
    if (["vinyl", "cassette", "digital_download", "beat", "sample_pack", "acapella"].includes(type)) {
      return "Music drop";
    }
    if (type === "membership_merch") return "Supporter merch";
    return "Merch drop";
  }

  function buildFanFeedItems(limit = 20) {
    const watchedArtists = new Set([
      ...savedArtists.map(artist => artist.owner_username),
      ...getSupportedArtistUsernames(),
    ]);

    const items = [
      ...povs
        .filter(pov => watchedArtists.has(pov.artist_username))
        .map(pov => {
          const meta = getArtistFeedMeta(pov.artist_username);
          return {
            id: `pov-${pov.id}`,
            kind: "pov",
            label: "POV",
            title: "",
            body: pov.body,
            imageUrl: "",
            artistUsername: pov.artist_username,
            stageName: meta.stageName,
            heroImage: meta.heroImage,
            createdAt: pov.created_at,
            targetUrl: `/?artist=${pov.artist_username}`,
            openTab: "feed",
            profession: pov.profession || "",
          };
        }),
      ...instants
        .filter(instant => watchedArtists.has(instant.artist_username))
        .map(instant => {
          const meta = getArtistFeedMeta(instant.artist_username);
          return {
            id: `instant-${instant.id}`,
            kind: "instant",
            label: "Instant",
            title: "",
            body: instant.body,
            imageUrl: isImageMediaUrl(instant.media) ? instant.media : "",
            artistUsername: instant.artist_username,
            stageName: meta.stageName,
            heroImage: meta.heroImage,
            createdAt: instant.created_at,
            targetUrl: `/?artist=${instant.artist_username}`,
            openTab: "feed",
            profession: "",
          };
        }),
      ...posts
        .filter(post => watchedArtists.has(post.author_username))
        .map(post => {
          const meta = getArtistFeedMeta(post.author_username);
          const imageUrl = isImageMediaUrl(post.file) ? post.file : "";
          return {
            id: `post-${post.id}`,
            kind: "post",
            label: postFeedLabel(post),
            title: post.title || "",
            body: post.body || (post.external_url ? `Shared on ${post.post_type}.` : ""),
            imageUrl,
            artistUsername: post.author_username,
            stageName: meta.stageName,
            heroImage: meta.heroImage,
            createdAt: post.created_at,
            targetUrl: `/?artist=${post.author_username}`,
            openTab: "feed",
            profession: post.profession || "",
          };
        }),
      ...music
        .filter(track => watchedArtists.has(track.artist_username))
        .map(track => {
          const meta = getArtistFeedMeta(track.artist_username);
          return {
            id: `track-${track.id}`,
            kind: "music",
            label: "New track",
            title: track.title,
            body: [track.genre, track.profession_label].filter(Boolean).join(" • ") || "Fresh upload from an artist you follow.",
            imageUrl: track.cover_art || "",
            artistUsername: track.artist_username,
            stageName: meta.stageName,
            heroImage: meta.heroImage || track.cover_art || "",
            createdAt: track.created_at,
            targetUrl: `/?artist=${track.artist_username}`,
            openTab: "listen",
            profession: track.profession || "",
          };
        }),
      ...products
        .filter(product => watchedArtists.has(product.artist_username))
        .map(product => {
          const meta = getArtistFeedMeta(product.artist_username);
          return {
            id: `product-${product.id}`,
            kind: "store",
            label: storeFeedLabel(product),
            title: product.title,
            body: product.description || `${storeFeedLabel(product)} from ${meta.stageName}.`,
            imageUrl: product.image || "",
            artistUsername: product.artist_username,
            stageName: meta.stageName,
            heroImage: meta.heroImage || product.image || "",
            createdAt: product.created_at,
            targetUrl: `/?artist=${product.artist_username}`,
            openTab: "shop",
            profession: product.profession || "",
          };
        }),
    ]
      .filter(matchesFanChannelItem)
      .sort((a, b) => new Date(b.createdAt || 0) - new Date(a.createdAt || 0));

    return items.slice(0, limit);
  }

  function getFanNetworkItems() {
    return buildFanFeedItems(8);
  }

  async function openFanFeedItem(item) {
    await openArtistByUsername(item.artistUsername, {
      stage_name: item.stageName,
      hero_image: item.heroImage,
    }, {
      profession: item.profession || "",
      tab: item.openTab,
      shopTab: item.openTab === "shop" ? "merch" : undefined,
    });
  }

  function renderFanFeedCards(items) {
    return (
      <div className="feed-update-list">
        {items.map(item => (
          <FanFeedUpdateCard
            key={item.id}
            item={item}
            onOpen={openFanFeedItem}
            renderArtistName={renderArtistName}
          />
        ))}
      </div>
    );
  }

  function matchesFanChannelItem(item) {
    if (!fanChannelUsername) return true;
    return item.artistUsername === fanChannelUsername;
  }

  function buildNotificationsList() {
    if (!currentUser) return [];

    if (notificationData.results.length > 0) {
      return notificationData.results.map(item => ({
        id: `stored-${item.id}`,
        notificationId: item.id,
        type: item.type,
        title: item.title,
        detail: item.body || item.actor_username || "Account update",
        read: item.read,
        target_url: item.target_url || "",
      }));
    }

    if (currentUser.is_artist) {
      const supporterNotes = subData.subscriptions
        ?.filter(sub => sub.artist === currentUser.username && sub.active)
        .slice(0, 5)
        .map(sub => ({
          id: `supporter-${sub.fan_id}`,
          type: "Supporter",
          title: `${sub.fan} supports you`,
          detail: `Monthly support: $${sub.monthly_amount || "1.00"}.`,
          target_url: "/?page=profile",
        })) || [];

      const commentNotes = posts
        .filter(post => post.author_username === currentUser.username)
        .flatMap(post => post.comments?.map(comment => ({
          id: `comment-${post.id}-${comment.id}`,
          type: "Comment",
          title: `${comment.author_username} commented`,
          detail: post.title || "On your post.",
          target_url: "/?page=home",
        })) || [])
        .slice(0, 6);

      const likeNotes = posts
        .filter(post => post.author_username === currentUser.username && post.likes_count > 0)
        .slice(0, 4)
        .map(post => ({
          id: `likes-${post.id}`,
          type: "Like",
          title: `${post.likes_count} likes on ${post.title || "your post"}`,
          detail: "Your artist activity is getting engagement.",
          target_url: "/?page=home",
        }));

      return [...supporterNotes, ...commentNotes, ...likeNotes].slice(0, 12);
    }

    return buildFanFeedItems(12).map(item => ({
      id: item.id,
      type: item.label,
      title: item.title ? `${item.stageName}: ${item.title}` : `${item.stageName} · ${item.label}`,
      detail: item.body,
      read: false,
      target_url: item.targetUrl,
    }));
  }

  function getNotifications() {
    return buildNotificationsList().filter(item => !dismissedNotificationIds.has(item.id));
  }

  function getTikTokVideoId(url) {
    const match = url?.match(/\/video\/(\d+)/);
    return match?.[1] || "";
  }

  function buildExternalStoreUrl(product) {
    if (!product.external_url) return "";

    const code = product.external_discount_code?.trim();
    if (!code) return product.external_url;

    try {
      const url = new URL(product.external_url);
      const redirectPath = `${url.pathname}${url.search}`;
      url.pathname = `/discount/${encodeURIComponent(code)}`;
      url.search = redirectPath && redirectPath !== "/" ? `?redirect=${encodeURIComponent(redirectPath)}` : "";
      url.hash = "";
      return url.toString();
    } catch (error) {
      return product.external_url;
    }
  }

  function renderPostEngagement(post) {
    return (
      <>
        <div className="post-actions">
          {currentUser ? (
            <button
              className={post.liked_by_current_user ? "supporting compact" : "secondary compact"}
              onClick={() => togglePostLike(post.id)}
            >
              {post.liked_by_current_user ? "Unlike" : "Like"} ({post.likes_count})
            </button>
          ) : (
            <button className="secondary compact" onClick={() => goToPage("profile")}>
              Log in to like ({post.likes_count})
            </button>
          )}
          <span className="muted">{post.comments_count} comments</span>
        </div>

        <div className="comments-list">
          {post.comments?.map(comment => (
            <div className="comment-item" key={comment.id}>
              <strong>{renderArtistName(comment.author_username, { knownOnly: true })}</strong>
              <p>{comment.body}</p>
            </div>
          ))}
          {(!post.comments || post.comments.length === 0) && (
            <p className="muted">No comments yet.</p>
          )}
        </div>

        {currentUser && post.can_comment ? (
          <form className="comment-form" onSubmit={(event) => createComment(event, post.id)}>
            <input name="body" placeholder="Write a comment..." required />
            <button className="secondary compact" type="submit">Comment</button>
          </form>
        ) : !currentUser ? (
          <p className="muted"><button type="button" className="link-button" onClick={() => goToPage("profile")}>Log in</button> to comment.</p>
        ) : (
          <p className="muted">{post.comment_block_reason || "Comments are restricted."}</p>
        )}
      </>
    );
  }

  function renderSocialEmbed(post) {
    if (!post.external_url) return null;

    if (hideSocialEmbeds) {
      return (
        <div className="social-hidden">
          <div>
            <strong>Social post hidden</strong>
            <p className="muted">Your settings hide Instagram and TikTok embeds on artist profiles.</p>
          </div>
          <button className="secondary compact" onClick={() => openExternalSocial(post.external_url, post.external_provider)}>
            Open Original
          </button>
        </div>
      );
    }

    if (post.external_provider === "tiktok") {
      const videoId = getTikTokVideoId(post.external_url);

      return (
        <div className="social-embed">
          <div className="social-embed-actions">
            <span>TikTok embed</span>
            <button className="secondary compact" onClick={() => openExternalSocial(post.external_url, "TikTok")}>
              Open Original
            </button>
          </div>
          <blockquote
            className="tiktok-embed"
            cite={post.external_url}
            data-video-id={videoId}
            data-embed-from="indiefund"
          >
            <section>
              <a href={post.external_url} target="_blank" rel="noreferrer">Watch on TikTok</a>
            </section>
          </blockquote>
        </div>
      );
    }

    if (post.external_provider === "instagram") {
      return (
        <div className="social-embed">
          <div className="social-embed-actions">
            <span>Instagram embed</span>
            <button className="secondary compact" onClick={() => openExternalSocial(post.external_url, "Instagram")}>
              Open Original
            </button>
          </div>
          <blockquote
            className="instagram-media"
            data-instgrm-permalink={post.external_url}
            data-instgrm-version="14"
          >
            <a href={post.external_url} target="_blank" rel="noreferrer">View on Instagram</a>
          </blockquote>
        </div>
      );
    }

    return (
      <button className="external-post-link" onClick={() => openExternalSocial(post.external_url)}>
        Open original post
      </button>
    );
  }

  function getArtistSocialLinks(artist) {
    if (!artist) return [];

    return [
      { id: "instagram", label: "Instagram", url: artist.instagram_url },
      { id: "tiktok", label: "TikTok", url: artist.tiktok_url },
      { id: "youtube", label: "YouTube", url: artist.youtube_url },
      { id: "website", label: "Website", url: artist.website_url },
    ].filter(item => item.url);
  }

  function renderSupportConfirmSheet() {
    const pendingArtist = pendingSupportArtist?.artist || null;
    const pendingProfession = pendingSupportArtist?.profession || DEFAULT_PROFESSION;
    const pendingTiers = pendingArtist
      ? supportTiers.filter(tier =>
          tier.artist === pendingArtist.owner_username &&
          tier.profession === pendingProfession
        )
      : [];
    return (
      <SupportConfirmSheet
        artist={pendingArtist}
        professionLabel={professionLabel(pendingProfession)}
        tiers={pendingTiers}
        selectedTierId={selectedSupportTierId}
        onTierChange={setSelectedSupportTierId}
        onCancel={() => {
          setPendingSupportArtist(null);
          setSelectedSupportTierId("");
          setSelectedSupportEmailShare(false);
        }}
        emailShareChecked={selectedSupportEmailShare}
        onEmailShareChange={currentUser?.share_email_with_supported_artists ? null : setSelectedSupportEmailShare}
        onConfirm={confirmSupport}
      />
    );
  }

  function renderDiscoveryArtistCard(artist, compact = false) {
    const { profession, supporting } = artistSupportState(artist);
    const artistTrack = music.find(track => track.artist_username === artist.owner_username);

    return (
      <article className={compact ? "artist-card compact-card" : "artist-card"} key={artist.id}>
        <div className="artist-banner" onClick={() => openArtist(artist)}></div>
        <div className="artist-body">
          <div className="artist-card-content">
            <div className="avatar" onClick={() => openArtist(artist)}>{artist.stage_name?.[0]?.toUpperCase()}</div>
            <div className="artist-row-head">
              <div>
                <h3>
                  {renderArtistName(artist.owner_username, {
                    label: artist.stage_name,
                    artist,
                    verified: artist.is_verified,
                    className: "artist-name-link click-title",
                  })}
                </h3>
                <p className="muted">{artist.genre} • {artist.city}</p>
                {artist.business_health && (
                  <p className="muted">{artist.business_health.followers} followers · {artist.business_health.supporter_ratio_label} · {artist.business_health.engagement.badge}</p>
                )}
                {artist.next_local_gig && (
                  <p className="local-gig-hint">
                    Playing @ {artist.next_local_gig.venue_name}
                    {artist.next_local_gig.starts_at ? ` · ${new Date(artist.next_local_gig.starts_at).toLocaleDateString()}` : ""}
                    {artist.next_local_gig.venue_city ? ` · ${artist.next_local_gig.venue_city}` : ""}
                  </p>
                )}
              </div>
              <div className="artist-row-primary">
                {renderSupportButton(artist, supporting, "small", profession)}
              </div>
            </div>

            {artistTrack && (
              <div className="card-track">
                <div>
                  {renderTrackTitle(artistTrack, { className: "track-name-link" })}
                  <p className="muted">{artistTrack.genre} • {artistTrack.bpm || "No"} BPM</p>
                </div>
                {artistTrack.audio_file ? (
                  <button className="primary compact" onClick={() => handleTogglePlay(artistTrack)}>
                    {currentTrack?.id === artistTrack.id && isPlaying ? "Pause Preview" : "Play Preview"}
                  </button>
                ) : (
                  renderLockedTrackPrompt(artistTrack)
                )}
              </div>
            )}

            <div className="discovery-meta">
              <span>Score {artist.discovery_score}</span>
              {artist.signals && <span>{artist.signals.tracks} tracks</span>}
              {artist.signals && <span>{artist.signals.supporter_ratio}% supporters</span>}
              {artist.signals?.is_emerging && <span>Emerging</span>}
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
                    community: "Supporter signal",
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
    const { profession, supporting } = artistSupportState(artist);
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
            <h3>
              {renderArtistName(artist.owner_username, {
                label: artist.stage_name,
                artist,
                verified: artist.is_verified,
                className: "artist-name-link click-title",
              })}
            </h3>
            <p className="muted">{artist.genre} • {artist.city}</p>
            {artist.business_health && (
              <p className="muted">{artist.business_health.followers} followers · {artist.business_health.supporter_ratio_label} · {artist.business_health.engagement.badge}</p>
            )}
            {artist.next_local_gig && (
              <div className="saved-gig-row">
                <p className="local-gig-hint">
                  {renderArtistName(artist.owner_username, { label: artist.next_local_gig.stage_name || artist.stage_name })}
                  {" @ "}{artist.next_local_gig.venue_name}
                  {artist.next_local_gig.starts_at ? ` · ${new Date(artist.next_local_gig.starts_at).toLocaleString()}` : ""}
                </p>
                <button className="secondary compact" type="button" onClick={() => goToMyScene(artist.next_local_gig.booking_id)}>
                  View show
                </button>
              </div>
            )}
            <div className="saved-status">
              <span>{isSupportingAny(artist.owner_username) ? "Supporting" : "Not supporting"}</span>
            </div>
          </div>
        </div>

        <div className="saved-preview">
          {artistTrack ? (
            <>
              {renderTrackTitle(artistTrack, { className: "track-name-link" })}
              {artistTrack.audio_file ? (
                <button className="primary compact" onClick={() => handleTogglePlay(artistTrack)}>
                  {currentTrack?.id === artistTrack.id && isPlaying ? "Pause" : "Play Preview"}
                </button>
              ) : (
                renderLockedTrackPrompt(artistTrack)
              )}
            </>
          ) : (
            <p className="muted">No preview track yet.</p>
          )}
        </div>

        <div className="saved-actions">
          <button className="secondary small-pill" onClick={() => openArtist(artist)}>
            Open Page
          </button>
          {renderSupportButton(artist, supporting, "small", profession)}
          <button className="secondary small-pill" onClick={() => removeSavedArtist(artist)}>
            Remove
          </button>
        </div>
      </article>
    );
  }

  function renderPlayingNearYouSection({ title = "Playing near you", filterArtist = null, limit = 5 } = {}) {
    const gigs = (filterArtist
      ? playingNearYou.filter(gig => filterArtist(gig))
      : playingNearYou
    ).slice(0, limit);

    if (gigs.length === 0) return null;

    return (
      <section className="home-activity">
        <div className="tab-title-row">
          <div>
            <p className="eyebrow">Playing near you</p>
            <h3>{title}</h3>
          </div>
          <button className="secondary compact" type="button" onClick={() => goToMyScene()}>Shows near me</button>
        </div>
        <div className="activity-list">
          {gigs.map(gig => (
            <article className="activity-item" key={gig.booking_id}>
              <span>{gig.is_supported ? "supported" : "live"}</span>
              <div>
                <strong>
                  {renderArtistName(gig.artist_username, { label: gig.stage_name })}
                  {" @ "}{gig.venue_name}
                </strong>
                <p>
                  {new Date(gig.starts_at).toLocaleString()} · {gig.venue_city}
                  {gig.bar_open ? " · bar open" : ""}
                </p>
              </div>
              <button className="secondary compact" type="button" onClick={() => goToMyScene(gig.booking_id)}>
                Details
              </button>
              <button className="secondary compact" type="button" onClick={() => openArtistFromGig(gig)}>
                View artist
              </button>
            </article>
          ))}
        </div>
      </section>
    );
  }

  function renderSavedArtistsSection() {
    const savedUsernames = new Set([
      ...savedArtists.map(artist => artist.owner_username),
      ...getSupportedArtistUsernames(),
    ]);

    return (
      <>
        <section className="section-head saved-head tab-title-row">
          <div>
            <p className="eyebrow">Discovery</p>
            <h2>Saved Artists</h2>
            <p>{currentUser ? "Artists you marked to revisit." : "Log in to save and manage artists."}</p>
          </div>
          <button className="secondary" onClick={() => goToPage("listen", true, { tab: "discover", view: "recommendations" })}>Back to Listen</button>
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

        {renderPlayingNearYouSection({
          title: "Gigs from artists you save or support",
          filterArtist: gig => savedUsernames.has(gig.artist_username),
        })}

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
              <p>Save artists while reviewing recommendations, then return here to open their page, play a preview, or support them.</p>
              <button className="secondary" onClick={() => goToPage("listen", true, { tab: "discover", view: "recommendations" })}>Back to Listen</button>
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
    );
  }

  function renderBookingArtistMaterial(booking) {
    if (!booking?.material_url && !booking?.material_credit) {
      return null;
    }

    return (
      <div className="booking-artist-material">
        {booking.material_credit && <strong>{booking.material_credit}</strong>}
        {booking.material_url && (
          <a href={booking.material_url} target="_blank" rel="noopener noreferrer">
            {booking.material_credit ? "Open artist material" : booking.material_url}
          </a>
        )}
      </div>
    );
  }

  function renderBookingTicketSales(booking) {
    if (!booking?.ticket_product_id) {
      return (
        <p className="muted form-hint">No ticket attached yet — F&B and door only.</p>
      );
    }

    const sold = booking.tickets_sold || 0;
    const capacity = booking.tickets_capacity;
    const remaining = booking.tickets_remaining;
    const hasCapacity = typeof capacity === "number" && capacity > 0;

    return (
      <p className="muted form-hint booking-ticket-sales">
        <strong>{sold}</strong> ticket{sold === 1 ? "" : "s"} sold
        {hasCapacity && ` of ${capacity}`}
        {booking.ticket_title ? ` · ${booking.ticket_title}` : ""}
        {hasCapacity && (
          booking.tickets_sold_out
            ? " · Sold out"
            : typeof remaining === "number" ? ` · ${remaining} left` : ""
        )}
        {typeof booking.tickets_verified_at_door === "number" && (
          <> · <strong>{booking.tickets_verified_at_door}</strong> verified at door</>
        )}
      </p>
    );
  }

  function renderSpacesPage() {
    if (currentUser && !currentUser.is_artist && !currentUser.is_host) {
      goToPage("my-scene");
      return null;
    }

    const isHost = Boolean(currentUser?.is_host);
    const businessName = spaceHostProfile?.business_name || currentUser?.display_name || currentUser?.username;
    const pendingRequests = spaceBookings.filter(booking => booking.status === "requested").length;
    const confirmedShows = spaceBookings.filter(booking => booking.status === "confirmed").length;
    const otherRooms = isHost
      ? hostMarketListings.filter(listing => listing.host_id !== currentUser.id)
      : [];

    const filteredListings = spaceListings.filter(listing => {
      if (!spaceCityFilter.trim()) return true;
      return listing.city?.toLowerCase().includes(spaceCityFilter.trim().toLowerCase());
    });

    return (
      <>
        {renderSpaceListingModal()}

        <section className={`section-head tab-title-row${shouldShowHomeWelcome() ? "" : " home-dashboard-head--compact"}`}>
          <div>
            <p className="eyebrow">IndieFund | Spaces</p>
            {isHost && shouldShowHomeWelcome() ? (
              <>
                <h2>Welcome back, {businessName}</h2>
                <p className="muted">Manage listings, review booking requests, and see how your rooms appear to artists.</p>
              </>
            ) : (
              <>
                <h2>{isHost ? "Your rooms" : "Book local rooms"}</h2>
                <p className="muted">
                  {isHost
                    ? `Run ${businessName} on IndieFund — manage listings, review booking requests, and see how your rooms appear to artists.`
                    : "Request a room, attach a ticket, and notify local supporters when the gig confirms."}
                </p>
              </>
            )}
          </div>
          {isHost && (
            <div className="section-head-actions">
              <button className="primary" type="button" onClick={() => setShowSpaceListingForm(true)}>
                Add room
              </button>
            </div>
          )}
        </section>

        {isHost && (
          <section className="host-kpi-strip" aria-label="Host overview">
            <div className="host-kpi-item">
              <span className="host-kpi-value">{filteredListings.length}</span>
              <span className="host-kpi-label">Your rooms</span>
              <span className="host-kpi-detail">Live listings on IndieFund</span>
              <TicketStubIconButton onClick={() => setShowTicketStubSheet(true)} />
            </div>
            <div className="host-kpi-divider" aria-hidden="true" />
            <div className="host-kpi-item">
              <span className="host-kpi-value">{pendingRequests}</span>
              <span className="host-kpi-label">Pending requests</span>
              <span className="host-kpi-detail">Awaiting your review</span>
            </div>
            <div className="host-kpi-divider" aria-hidden="true" />
            <div className="host-kpi-item">
              <span className="host-kpi-value">{confirmedShows}</span>
              <span className="host-kpi-label">Confirmed shows</span>
              <span className="host-kpi-detail">Upcoming on your calendar</span>
            </div>
          </section>
        )}

        {isHost && (
          <SetupChecklistPanel
            title="Set up your venue"
            subtitle="Finish these steps so artists can find and book your room."
            items={getHostSetupChecklistItems()}
            checklistHidden={setupChecklistDismissed}
            onDismiss={dismissSetupChecklist}
          />
        )}

        {currentUser?.is_artist && (
          <section className="space-panel">
            <div className="tab-title-row">
              <div>
                <h3>Your booking requests</h3>
                <p className="muted">{spaceBookings.length} active or historical booking records.</p>
              </div>
              {spaceBookings.length > 0 && (
                <button className="secondary compact" type="button" onClick={() => clearSpaceBookings("all")}>
                  Clear all
                </button>
              )}
            </div>

            <div className="space-booking-list">
              {spaceBookings.length === 0 && <p className="muted">No bookings yet. Pick a venue below to request your first show.</p>}
              {spaceBookings.map(booking => (
                <div className="space-booking-row space-booking-row--dismissible" key={`artist-${booking.id}`}>
                  {renderSpaceBookingDismissButton(booking.id)}
                  <div>
                    <strong>{booking.listing?.name}</strong>
                    <p className="muted">
                      {new Date(booking.starts_at).toLocaleString()} · {booking.status}
                    </p>
                  </div>
                  <div className="action-grid">
                    {booking.status === "confirmed" && (
                      <button className="secondary compact" onClick={() => notifyLocalSupporters(booking.id)}>
                        Notify Local Supporters
                      </button>
                    )}
                    {booking.status === "completed" && (
                      <button
                        className="secondary compact"
                        onClick={() => openSpaceReviewModal(booking.id, currentUser, booking.listing?.name)}
                      >
                        Review venue
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </section>
        )}

        {currentUser?.is_host && (
          <section className="host-dashboard space-panel">
            <div className="tab-title-row">
              <div>
                <p className="eyebrow">Host dashboard</p>
                <h3>Booking requests</h3>
                <p className="muted">
                  {spaceBookings.length} active or historical booking record{spaceBookings.length === 1 ? "" : "s"}.
                  Confirm gigs, review local draw, and track check-ins in one place.
                </p>
              </div>
            </div>

            <div className="host-dashboard-section">
              <h4>Pending requests</h4>
              <div className="space-booking-list">
                {spaceBookings.filter(booking => booking.status === "requested").length === 0 && (
                  <p className="muted">No pending requests right now.</p>
                )}
                {spaceBookings.filter(booking => booking.status === "requested").map(booking => (
                  <div className="space-booking-row host-dashboard-row" key={`pending-${booking.id}`}>
                    <div>
                      <strong>
                        {renderArtistName(booking.artist_username, { label: booking.artist_name })}
                        {" → "}{booking.listing?.name}
                      </strong>
                      <p className="muted">{new Date(booking.starts_at).toLocaleString()} · {booking.status}</p>
                      {booking.artist_local_draw && (
                        <p className="booking-local-draw">
                          <strong>{booking.artist_local_draw.local_supporters}</strong> supporter{booking.artist_local_draw.local_supporters === 1 ? "" : "s"} in {booking.artist_local_draw.local_city || booking.listing?.city}
                          <span className="muted"> · {booking.artist_local_draw.active_subscribers} subscribers · {booking.artist_local_draw.engagement_badge} engagement</span>
                        </p>
                      )}
                      {booking.ticket_product_id && renderBookingTicketSales(booking)}
                      {booking.pitch && <p className="booking-pitch">{booking.pitch}</p>}
                      {renderBookingArtistMaterial(booking)}
                    </div>
                    <div className="action-grid">
                      <button className="primary compact" onClick={() => updateSpaceBookingStatus(booking.id, "confirmed")}>Confirm</button>
                      <button className="secondary compact" onClick={() => updateSpaceBookingStatus(booking.id, "cancelled")}>Decline</button>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {spaceBookings.filter(booking => booking.status !== "requested").length > 0 && (
              <div className="host-dashboard-section">
                <div className="host-dashboard-section-head">
                  <h4>Confirmed & history</h4>
                  <button className="secondary compact" type="button" onClick={() => clearSpaceBookings("history")}>
                    Clear all
                  </button>
                </div>
                <div className="space-booking-list">
                  {spaceBookings.filter(booking => booking.status !== "requested").map(booking => (
                    <div className="space-booking-row host-dashboard-row space-booking-row--dismissible" key={booking.id}>
                      {renderSpaceBookingDismissButton(booking.id)}
                      <div>
                        <strong>
                        {renderArtistName(booking.artist_username, { label: booking.artist_name })}
                        {" → "}{booking.listing?.name}
                      </strong>
                        <p className="muted">
                          {new Date(booking.starts_at).toLocaleString()} · {booking.status}
                        </p>
                        {booking.artist_local_draw && (
                          <p className="muted form-hint">
                            Local draw in {booking.artist_local_draw.local_city}: {booking.artist_local_draw.local_supporters} supporters
                            · {booking.artist_local_draw.active_subscribers} subscribers
                            · {booking.artist_local_draw.engagement_badge} engagement
                            · {booking.tickets_verified_at_door || booking.check_in_count || 0} verified at door
                          </p>
                        )}
                        {renderBookingTicketSales(booking)}
                        {booking.pitch && <p className="booking-pitch">{booking.pitch}</p>}
                        {renderBookingArtistMaterial(booking)}
                      </div>
                      <div className="action-grid">
                        {booking.status === "confirmed" && (
                          <>
                            <button className="secondary compact" onClick={() => updateSpaceBookingStatus(booking.id, "cancelled")}>Cancel</button>
                            <button
                              className="primary compact"
                              onClick={() => updateSpaceBookingStatus(
                                booking.id,
                                "completed",
                                booking.expected_audience || booking.attendance_checked_in || 0,
                                { openReviewAfter: true },
                              )}
                            >
                              Complete & review
                            </button>
                          </>
                        )}
                        {booking.status === "completed" && (
                          <button
                            className="secondary compact"
                            onClick={() => openSpaceReviewModal(booking.id, currentUser, booking.artist_name)}
                          >
                            {booking.my_reviews?.artist ? "Edit review" : "Review artist"}
                          </button>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </section>
        )}

        {currentUser?.is_host && (
          <section className="spaces-host-summary" aria-label="Host summary">
            <div className="spaces-host-summary-item">
              <span>Completed bookings</span>
              <strong>{spaceEarnings?.completed_bookings || 0}</strong>
            </div>
            <div className="spaces-host-summary-item">
              <span>Upcoming tickets sold</span>
              <strong>
                {spaceBookings
                  .filter(booking => booking.status === "confirmed")
                  .reduce((total, booking) => total + (booking.tickets_sold || 0), 0)}
              </strong>
            </div>
            <div className="spaces-host-summary-item">
              <span>Verified at door</span>
              <strong>
                {spaceBookings
                  .filter(booking => booking.status === "confirmed")
                  .reduce((total, booking) => total + (booking.tickets_verified_at_door || 0), 0)}
              </strong>
            </div>
            <p className="spaces-host-summary-note">
              {spaceEarnings?.policy || "IndieFund does not take a cut of food and beverage revenue. F&B stays with the venue."}
            </p>
          </section>
        )}

        {!currentUser?.is_host && (
          <section className="discovery-filter-row">
            <input
              value={spaceCityFilter}
              onChange={(event) => setSpaceCityFilter(event.target.value)}
              placeholder="Filter by city"
              aria-label="Filter spaces by city"
            />
          </section>
        )}

        {isHost && (
          <div className="tab-title-row">
            <div>
              <p className="eyebrow">Your listings</p>
              <h3>Rooms you operate</h3>
              <p className="muted">These are the spaces artists can request when they browse your venue profile.</p>
            </div>
          </div>
        )}

        <section className="spaces-grid">
          {filteredListings.length === 0 && (
            <div className="empty-state full-span">
              <h3>No spaces listed yet.</h3>
              <p>{currentUser?.is_host ? "Add your first room to start taking booking requests." : "Try another city or check back as hosts join the pilot."}</p>
            </div>
          )}

          {filteredListings.map(listing => {
            const { localCount, localDrawLoading, meetsLocalRequirement } = getListingLocalDrawState(listing);

            return (
            <article
              className="space-card space-card--clickable"
              key={listing.id}
              data-testid="space-listing-card"
              onClick={(event) => handleSpaceCardClick(event, listing)}
            >
              <button type="button" className="space-card-preview-button" onClick={() => openSpaceListingDetail(listing)} aria-label={`View photos for ${listing.name}`}>
                <SpaceListingCardPreview listing={listing} photoTypeLabels={SPACE_PHOTO_TYPE_LABELS} />
              </button>
              <div className="space-card-summary">
                <p className="eyebrow">{listing.city || "Local room"} · {listing.capacity} cap</p>
                <h3>{listing.name}</h3>
                <p className="muted">{listing.host_business_name} · {SPACE_SPLIT_LABELS[listing.split_type] || listing.split_type}</p>
                <p className="space-card-teaser">{listing.description || "Flexible room for independent performers."}</p>
              </div>
              <div className="post-badges">
                {listing.tags?.slice(0, 4).map(tag => <span key={tag}>{tag.replaceAll("_", " ")}</span>)}
                {listing.bar_open && <span>Bar open</span>}
                {listing.kitchen_open && <span>Kitchen open</span>}
              </div>
              <div className="space-meta-grid space-card-meta-compact">
                <span>Availability: {formatAvailabilityWindows(listing.available_windows)}</span>
                <span>Host cut: {listing.split_type === "door_percent" ? `${listing.host_cut_percent}%` : listing.split_type === "flat_fee" ? `$${listing.flat_fee_amount}` : "F&B only"}</span>
                {listing.drink_minimum && <span>Minimum: {listing.drink_minimum}</span>}
                {listing.last_call && <span>Last call: {listing.last_call}</span>}
                {listing.min_local_supporters > 0 && (
                  <span className={meetsLocalRequirement ? "space-requirement-met" : "space-requirement-unmet"}>
                    Requires {listing.min_local_supporters}+ local supporters in {listing.city}
                    {currentUser?.is_artist && localCount !== null && (
                      <> · You have {localCount}</>
                    )}
                  </span>
                )}
              </div>

              {currentUser?.is_artist && (
                <SpaceAvailabilityEditor rows={windowsToRows(listing.available_windows)} windows={listing.available_windows} readOnly />
              )}

              {currentUser?.is_artist && (
                localDrawLoading ? (
                  <p className="muted form-hint">Checking your local supporter count in {listing.city}…</p>
                ) : meetsLocalRequirement ? (
                  <button
                    className="primary compact"
                    type="button"
                    onClick={() => openSpaceBookingForm(listing.id)}
                  >
                    Request booking
                  </button>
                ) : (
                  <>
                    <p className="muted form-hint">Need more local supporters in {listing.city} to request this room.</p>
                    {listing.min_local_supporters > 0 && localCount !== null && !meetsLocalRequirement && (
                      <p className="space-draw-warning">
                        You need at least {listing.min_local_supporters} local supporters in {listing.city}. You currently have {localCount}.
                        Grow local subscribers in Profile → set your city, then ask fans in {listing.city} to support you.
                      </p>
                    )}
                  </>
                )
              )}
            </article>
            );
          })}
        </section>

        {isHost && (
          <section className="host-home-feed">
            <div className="tab-title-row">
              <div>
                <p className="eyebrow">IndieFund | Spaces</p>
                <h3>Other rooms on the platform</h3>
                <p className="muted">Preview how listed venues appear to artists when they search for performance space.</p>
              </div>
            </div>

            {otherRooms.length === 0 ? (
              <div className="empty-state">
                <h3>No other venues listed yet.</h3>
                <p>As more hosts join the pilot, their rooms will appear here for comparison.</p>
              </div>
            ) : (
              <div className="spaces-grid host-home-grid">
                {otherRooms.map(listing => renderHostListingFeedCard(listing))}
              </div>
            )}
          </section>
        )}

        {currentUser?.is_artist && spaceBookingListingId && (() => {
          const bookingListing = filteredListings.find(item => item.id === spaceBookingListingId);
          if (!bookingListing) return null;

          const cityKey = (bookingListing.city || "").trim().toLowerCase();
          const localDraw = artistLocalDraw[cityKey];
          const localCount = localDraw?.local_supporters ?? null;
          const meetsLocalRequirement = bookingListing.min_local_supporters <= 0
            || (localCount !== null && localCount >= bookingListing.min_local_supporters);
          const hasBookableWindows = getStructuredWindows(bookingListing.available_windows).length > 0;
          const artistProfile = getCurrentArtist();
          const defaultMaterialUrl = artistProfile?.youtube_url || artistProfile?.website_url || "";

          return (
            <section className="space-panel space-booking-panel" ref={spaceBookingPanelRef}>
              <div className="tab-title-row">
                <div>
                  <p className="eyebrow">Request a show</p>
                  <h3>{bookingListing.name}</h3>
                  <p className="muted">{bookingListing.city} · {bookingListing.capacity} cap</p>
                </div>
                <button className="secondary compact" type="button" onClick={() => setSpaceBookingListingId(null)}>Close</button>
              </div>
              <form className="space-booking-form" onSubmit={(event) => requestSpaceBooking(event, bookingListing.id)} noValidate>
                <div className="space-panel compact">
                  <p className="eyebrow">Venue availability</p>
                  <SpaceAvailabilityEditor rows={windowsToRows(bookingListing.available_windows)} windows={bookingListing.available_windows} readOnly />
                  <p className="muted form-hint">Choose one of the host&apos;s open days below, then pick times inside that window.</p>
                </div>
                <SpaceBookingDateFields
                  key={`booking-${bookingListing.id}`}
                  availableWindows={bookingListing.available_windows}
                  onValuesChange={values => { spaceBookingDateValuesRef.current = values; }}
                />
                {localCount !== null && (
                  <p className="muted form-hint">
                    The host will see your {localCount} local supporter{localCount === 1 ? "" : "s"} in {bookingListing.city} when reviewing this request.
                  </p>
                )}
                <label htmlFor={`booking-pitch-${bookingListing.id}`}>Pitch</label>
                <textarea
                  id={`booking-pitch-${bookingListing.id}`}
                  name="pitch"
                  placeholder="Pitch the show, your local draw, and what kind of night you are proposing"
                ></textarea>
                <label htmlFor={`booking-material-url-${bookingListing.id}`}>Show the host your material (optional)</label>
                <input
                  id={`booking-material-url-${bookingListing.id}`}
                  name="material_url"
                  type="url"
                  placeholder="YouTube, Spotify, SoundCloud, or other link"
                  defaultValue={defaultMaterialUrl}
                />
                <label htmlFor={`booking-material-credit-${bookingListing.id}`}>Credit / note (optional)</label>
                <input
                  id={`booking-material-credit-${bookingListing.id}`}
                  name="material_credit"
                  placeholder="e.g. Live set at Corner Hotel · latest single"
                />
                <label htmlFor={`booking-ticket-price-${bookingListing.id}`}>Cover charge (ticket)</label>
                <input
                  id={`booking-ticket-price-${bookingListing.id}`}
                  name="ticket_price"
                  type="number"
                  min="0"
                  step="0.01"
                  defaultValue="15"
                  placeholder="15.00"
                />
                <p className="muted form-hint">Fans buy a ticket when the show confirms. Set 0 for a free RSVP ticket.</p>
                <label htmlFor={`booking-presale-hours-${bookingListing.id}`}>Supporter presale (hours)</label>
                <input
                  id={`booking-presale-hours-${bookingListing.id}`}
                  name="supporter_presale_hours"
                  type="number"
                  min="0"
                  max="720"
                  step="1"
                  defaultValue="0"
                  placeholder="0"
                />
                <p className="muted form-hint">Give your supporters first dibs — only they can buy tickets for this many hours after the show confirms. Set 0 to open sales to everyone immediately.</p>
                <button className="primary compact" type="submit" disabled={!meetsLocalRequirement || !hasBookableWindows}>
                  {!hasBookableWindows
                    ? "Host availability not set"
                    : meetsLocalRequirement
                      ? "Submit booking request"
                      : "Need more local supporters"}
                </button>
              </form>
            </section>
          );
        })()}

        <SpaceListingDetailModal
          listing={selectedSpaceListing}
          onClose={() => setSelectedSpaceListing(null)}
          splitLabels={SPACE_SPLIT_LABELS}
          photoTypeLabels={SPACE_PHOTO_TYPE_LABELS}
          formatAvailabilityWindows={formatAvailabilityWindows}
          footer={selectedSpaceListing ? renderSpaceListingDetailFooter(selectedSpaceListing) : null}
        />

      </>
    );
  }

  function renderPromotedBadge(item) {
    if (!item?.promoted || !item?.promotion?.label) return null;
    return <span className="promoted-badge">{item.promotion.label}</span>;
  }

  function renderPromotionFeedback(item) {
    const campaignId = item?.promotion?.campaign_id;
    if (!item?.promoted || !currentUser || !campaignId) return null;
    const verdict = promotionFeedbackSent[campaignId];
    const shareUrl = item?.promotion?.share_url || window.location.href;
    if (verdict) {
      return (
        <div className="promotion-feedback-done">
          <p className="promotion-feedback-thanks">Thanks — your feedback helps discovery stay fair.</p>
          <button
            className="secondary compact"
            type="button"
            onClick={() => sharePromotedCampaign(campaignId, shareUrl)}
          >
            Share this find
          </button>
        </div>
      );
    }
    return (
      <div className="promotion-feedback">
        <p>Would you listen to more like this?</p>
        <div className="promotion-feedback-actions">
          <button className="secondary compact" type="button" onClick={() => sendPromotionFeedback(campaignId, "up")}>👍 Yes</button>
          <button className="secondary compact" type="button" onClick={() => sendPromotionFeedback(campaignId, "down")}>👎 Not for me</button>
          <button className="secondary compact" type="button" onClick={() => sharePromotedCampaign(campaignId, shareUrl)}>Share</button>
        </div>
      </div>
    );
  }

  function isPromotionArtistCard(item) {
    return Boolean(item?.owner_username && item?.stage_name && !item?.title);
  }

  function openPromotionPlacement(item) {
    if (isPromotionArtistCard(item)) {
      openArtist({
        owner_id: item.owner_id,
        owner_username: item.owner_username,
        stage_name: item.stage_name,
        genre: item.genre,
        city: item.city,
        hero_image: item.hero_image,
        is_verified: item.is_verified,
      });
      return;
    }

    const artistInfo = item.artist || {};
    openArtist({
      owner_id: artistInfo.owner_id,
      owner_username: item.artist_username || artistInfo.owner_username,
      stage_name: artistInfo.stage_name || item.artist_username,
      genre: artistInfo.genre || item.genre,
      city: artistInfo.city,
      hero_image: artistInfo.hero_image,
      is_verified: artistInfo.is_verified,
    });
  }

  function renderPromotionPlacementCard(item) {
    const isArtistCard = isPromotionArtistCard(item);
    const key = isArtistCard ? `artist-${item.owner_id}` : `track-${item.id}`;
    const title = isArtistCard ? item.stage_name : item.title;
    const subtitle = isArtistCard
      ? [item.genre, item.city].filter(Boolean).join(" • ")
      : [item.genre, item.artist?.stage_name || item.artist_username].filter(Boolean).join(" • ");
    const image = isArtistCard ? item.hero_image : item.cover_art;
    const previewTrack = isArtistCard ? item.preview_track : item;
    const canPlay = Boolean(
      previewTrack?.audio_file ||
      previewTrack?.preview_audio_file ||
      previewTrack?.can_preview
    );
    const isPlayingPlacement = Boolean(
      previewTrack?.id &&
      currentTrack?.id === previewTrack.id &&
      isPlaying
    );

    return (
      <article className="promotion-placement-card" key={key}>
        <button type="button" className="promotion-placement-main" onClick={() => openPromotionPlacement(item)}>
          {image ? (
            <img src={image} alt={title} />
          ) : (
            <div className="promotion-placement-fallback">{title?.[0]?.toUpperCase() || "?"}</div>
          )}
          <div>
            {renderPromotedBadge(item)}
            <strong>{title}</strong>
            <p className="muted">{subtitle}</p>
          </div>
        </button>
        <div className="promotion-placement-actions">
          {canPlay && (
            <button
              className="secondary compact"
              type="button"
              onClick={() => handleTogglePlay(previewTrack)}
            >
              {isPlayingPlacement ? "Pause" : "Play"}
            </button>
          )}
          <button className="secondary compact" type="button" onClick={() => openPromotionPlacement(item)}>
            {isArtistCard ? "View artist" : "View release"}
          </button>
        </div>
        {renderPromotionFeedback(item)}
      </article>
    );
  }

  function renderPromotionPlacements(items, heading = "Featured for you") {
    if (!currentUser || currentUser.is_artist || !items?.length) return null;

    return (
      <section className="promotion-placements">
        <div className="tab-title-row">
          <div>
            <p className="eyebrow">Discovery</p>
            <h3>{heading}</h3>
            <p className="muted">Promoted releases matched to your taste. Engage to earn discovery credits.</p>
          </div>
        </div>
        <div className="promotion-placements-grid">
          {items.map(item => renderPromotionPlacementCard(item))}
        </div>
      </section>
    );
  }

  function renderDiscoveryCreditsBanner() {
    if (!currentUser || currentUser.is_artist || !promotionWallet?.authenticated) return null;
    const balance = promotionWallet.balance || "0.00";
    const remaining = promotionWallet.rewards_remaining_today || promotionWallet.fan_reward_daily_cap || "1.00";
    return (
      <section className="discovery-credits-banner">
        <div>
          <p className="eyebrow">Discovery credits</p>
          <h3>${Number(balance).toFixed(2)} earned</h3>
          <p className="muted">
            Engage with promoted releases — full listens, saves, feedback — to earn up to ${remaining} more today.
            Credits apply to tips and store purchases.
          </p>
        </div>
      </section>
    );
  }

  function renderReviewArtist() {
    if (!reviewArtist) {
      return (
        <div className="empty-state full-span">
          <h3>No new artists to discover.</h3>
          <p>
            {currentUser
              ? discoveryMeta.exhausted
                ? "You have saved or skipped everyone we can match to your taste right now. Check Saved Artists or reset skips to keep exploring."
                : "Clear filters or reset skipped artists to bring more recommendations into review mode."
              : "Create a fan account to personalize discovery and save artists you love."}
          </p>
        </div>
      );
    }

    const artist = reviewArtist;
    const { profession, supporting } = artistSupportState(artist);
    const previewTrack = resolveDiscoveryPreviewTrack(artist);
    const discoveryPreviewActive = Boolean(
      playbackSource?.discovery &&
      currentTrack?.artist_username === artist.owner_username &&
      isPlaying
    );
    const coverArt = previewTrack?.cover_art || artist.hero_image;

    return (
      <section className="review-mode">
        <div className="review-top-bar">
          {currentUser && lastSkippedArtist && (
            <button className="secondary compact review-undo-skip" type="button" onClick={undoLastSkip}>
              Undo skip
            </button>
          )}
          <p className={`review-swipe-hint${currentUser && lastSkippedArtist ? "" : " review-swipe-hint-centered"}`}>
            {currentUser
              ? "Swipe left to skip · Swipe right to save artist"
              : "Swipe to browse artists, then create a free fan account to save favorites."}
          </p>
        </div>

        <div
          ref={reviewPanelRef}
          className={isSwiping ? "review-panel is-swiping" : "review-panel"}
          style={{
            transform: swipeDeltaX
              ? `translate3d(${swipeDeltaX}px, 0, 0) rotate(${swipeDeltaX / 32}deg)`
              : undefined,
          }}
          onPointerDown={startReviewSwipe}
          onPointerMove={moveReviewSwipe}
          onPointerUp={finishReviewSwipe}
          onPointerCancel={cancelReviewSwipe}
        >
          <div className="review-hero">
            {coverArt ? (
              <img className="review-cover" src={coverArt} alt={previewTrack?.title || artist.stage_name} onClick={() => openArtist(artist)} />
            ) : (
              <div className="review-avatar" onClick={() => openArtist(artist)}>{artist.stage_name?.[0]?.toUpperCase()}</div>
            )}
            <div className="review-hero-copy">
              {renderPromotedBadge(artist)}
              <h3>
                {renderArtistName(artist.owner_username, {
                  label: artist.stage_name,
                  artist,
                  verified: artist.is_verified,
                  className: "artist-name-link click-title",
                })}
              </h3>
              <p className="muted review-hero-meta">{artist.genre} • {artist.city}</p>
              {artist.business_health && (
                <p className="muted review-hero-stats">
                  {artist.business_health.followers} followers · {artist.business_health.supporter_ratio_label}
                </p>
              )}
            </div>
            <div className="review-hero-actions">
              {renderSupportButton(artist, supporting, "review", profession)}
              {currentUser && (
                <button
                  className="secondary compact review-more-like-this review-more-like-this-hero"
                  type="button"
                  onPointerDown={(event) => event.stopPropagation()}
                  onClick={(event) => {
                    event.stopPropagation();
                    sendDiscoverySignal(artist, "more_like_this");
                  }}
                >
                  More like this
                </button>
              )}
            </div>
          </div>

          <div className={swipeDeltaX > 24 ? "swipe-label save-label visible" : "swipe-label save-label"}>Save</div>
          <div className={swipeDeltaX < -24 ? "swipe-label skip-label visible" : "swipe-label skip-label"}>Skip for now</div>

          <div className="review-main">
            <div>
              <p className="review-story">{artist.artist_story}</p>
              <p className="tag">Influences: {artist.influences}</p>

              {previewTrack && (
                <div className={`review-track${discoveryPreviewActive ? " review-track-live" : ""}`}>
                  <div>
                    <p className="eyebrow">{discoveryPreviewActive ? "Preview playing now" : "Preview track"}</p>
                    {renderTrackTitle(previewTrack, { className: "track-name-link" })}
                    <p className="muted">{previewTrack.genre} • {previewTrack.bpm || "No"} BPM</p>
                  </div>
                  <button
                    className="primary full"
                    onPointerDown={(event) => event.stopPropagation()}
                    onClick={(event) => {
                      event.stopPropagation();
                      handleTogglePlay(previewTrack);
                    }}
                  >
                    {discoveryPreviewActive ? "Pause Preview" : "Play Preview"}
                  </button>
                </div>
              )}
              {!previewTrack && music.some(track => track.artist_username === artist.owner_username) && (
                renderLockedTrackPrompt(
                  music.find(track => track.artist_username === artist.owner_username)
                )
              )}
            </div>

            <div className="review-signals">
              <div className="review-signal-row">
                <div className="discovery-meta compact-meta">
                  <span>Score {artist.discovery_score}</span>
                  {artist.signals?.is_emerging && <span>Emerging</span>}
                </div>
                <button
                  className="why-button why-button-inline"
                  onClick={() => setExpandedWhyArtistId(expandedWhyArtistId === artist.id ? null : artist.id)}
                >
                  Why?
                </button>
              </div>
              {artist.discovery_reasons?.length > 0 && (
                <div className="reason-list compact-reasons">
                  {artist.discovery_reasons.slice(0, 2).map(reason => (
                    <span key={`${artist.id}-${reason.label}`}>{reason.label}</span>
                  ))}
                </div>
              )}
              {renderPromotionFeedback(artist)}
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
                  community: "Supporter signal",
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

        {!currentUser && (
          <div className="review-controls review-controls-guest">
            <button className="primary" onClick={() => goToPage("profile")}>Sign up to save artists</button>
            <button className="secondary" onClick={() => openArtist(artist)}>View profile</button>
          </div>
        )}
      </section>
    );
  }

  function renderReviewTrack() {
    if (!reviewTrack) {
      return (
        <div className="empty-state full-span">
          <h3>No new songs to discover.</h3>
          <p>
            {currentUser
              ? discoveryTrackMeta.exhausted
                ? "You have saved or skipped every track we can match to your taste right now. Check My Playlists or try artist discovery."
                : "Clear filters to bring more song recommendations back."
              : "Create a fan account to save songs while you swipe."}
          </p>
        </div>
      );
    }

    const track = reviewTrack;
    const artistInfo = track.artist || {};
    const playableTrack = resolvePlayableDiscoveryTrack(track);
    const discoveryPreviewActive = Boolean(
      playbackSource?.discovery &&
      currentTrack?.id === track.id &&
      isPlaying
    );
    const artistRecord = artistFromUsername(track.artist_username) || {
      owner_id: artistInfo.owner_id,
      owner_username: track.artist_username,
      stage_name: artistInfo.stage_name || track.artist_username,
      genre: artistInfo.genre,
      city: artistInfo.city,
      hero_image: artistInfo.hero_image,
      is_verified: artistInfo.is_verified,
    };

    return (
      <section className="review-mode review-mode-songs">
        <div className="review-top-bar">
          {currentUser && lastSkippedTrack && (
            <button className="secondary compact review-undo-skip" type="button" onClick={undoLastTrackSkip}>
              Undo skip
            </button>
          )}
          <p className={`review-swipe-hint${currentUser && lastSkippedTrack ? "" : " review-swipe-hint-centered"}`}>
            {currentUser
              ? "Swipe left to skip · Swipe right to save song to My Playlists"
              : "Swipe to preview songs, then create a free fan account to save favorites."}
          </p>
        </div>

        <div
          ref={reviewPanelRef}
          className={isSwiping ? "review-panel review-panel-song is-swiping" : "review-panel review-panel-song"}
          style={{
            transform: swipeDeltaX
              ? `translate3d(${swipeDeltaX}px, 0, 0) rotate(${swipeDeltaX / 32}deg)`
              : undefined,
          }}
          onPointerDown={startReviewSwipe}
          onPointerMove={moveReviewSwipe}
          onPointerUp={finishReviewSwipe}
          onPointerCancel={cancelReviewSwipe}
        >
          <div className={swipeDeltaX > 24 ? "swipe-label save-label visible" : "swipe-label save-label"}>Save song</div>
          <div className={swipeDeltaX < -24 ? "swipe-label skip-label visible" : "swipe-label skip-label"}>Skip</div>

          <div className="review-song-hero">
            {track.cover_art ? (
              <img className="review-song-cover" src={track.cover_art} alt={track.title} />
            ) : (
              <div className="review-song-cover review-song-cover-fallback">{track.title?.[0]?.toUpperCase() || "?"}</div>
            )}
            <div className="review-song-copy">
              <p className="eyebrow">Song {Math.min(reviewIndex + 1, filteredTracks.length)} of {filteredTracks.length}</p>
              {renderPromotedBadge(track)}
              {renderTrackTitle(track, { className: "track-name-link click-title review-song-title" })}
              {renderArtistName(track.artist_username, {
                label: artistInfo.stage_name || track.artist_username,
                artist: artistRecord,
                verified: artistInfo.is_verified,
                className: "artist-name-link review-song-artist",
              })}
              <p className="muted review-song-meta">
                {track.genre || "Unknown genre"} • {track.bpm ? `${track.bpm} BPM` : "No BPM"} • {track.profession_label || professionLabel(track.profession)}
              </p>
              {discoveryPreviewActive && <p className="review-song-live">Preview playing now</p>}
            </div>
          </div>

          <div className="review-signals">
            <div className="review-signal-row">
              <div className="discovery-meta compact-meta">
                <span>Score {track.discovery_score}</span>
                {track.ai_disclosure_badge && <span>{track.ai_disclosure_badge}</span>}
              </div>
              {playableTrack && (
                <button
                  className="secondary compact"
                  type="button"
                  onPointerDown={(event) => event.stopPropagation()}
                  onClick={(event) => {
                    event.stopPropagation();
                    handleTogglePlay(playableTrack);
                  }}
                >
                  {discoveryPreviewActive ? "Pause" : "Play"}
                </button>
              )}
            </div>
            {track.discovery_reasons?.length > 0 && (
              <div className="reason-list compact-reasons">
                {track.discovery_reasons.slice(0, 2).map(reason => (
                  <span key={`${track.id}-${reason.label}`}>{reason.label}</span>
                ))}
              </div>
            )}
            {renderPromotionFeedback(track)}
          </div>
        </div>

        {!currentUser && (
          <div className="review-controls review-controls-guest">
            <button className="primary" onClick={() => goToPage("profile")}>Sign up to save songs</button>
            <button className="secondary" onClick={() => openArtist(artistRecord)}>View artist</button>
          </div>
        )}
      </section>
    );
  }

  const authPanel = (
    <AuthPanel
      authMode={authMode}
      currentUser={currentUser}
      fanRegistrationOpen={fanRegistrationOpen(platformMode)}
      onAuth={handleAuth}
      onWaitlist={handleWaitlist}
      onProfile={() => goToPage("profile")}
      registerType={registerType}
      setAuthMode={setAuthMode}
      setRegisterType={setRegisterType}
    />
  );

  if (selectedArtist) {
    const supporting = isSupporting(selectedArtist.owner_username, activeProfession);
    const artistProfessions = getArtistProfessions(selectedArtist);
    const activeProfessionLabel = professionLabel(activeProfession);
    const activeProfessionProfile = getActiveProfessionProfile(selectedArtist, activeProfession);
    const activeDisplayTitle = activeProfessionProfile?.display_title || selectedArtist.stage_name;
    const activeBio = activeProfessionProfile?.bio || selectedArtist.artist_story;
    const activeStyle = activeProfessionProfile?.style || selectedArtist.genre;
    const activeCoverImage = activeProfessionProfile?.cover_image || selectedArtist.hero_image;
    const selectedDiscoveryRecord = [...discoveryArtists, ...savedArtists]
      .find(artist => artist.owner_id === selectedArtist.owner_id);
    const selectedSaved = savedArtists.some(artist => artist.owner_id === selectedArtist.owner_id);
    const profilePreviewTrack = music.find(track =>
      track.artist_username === selectedArtist.owner_username &&
      (track.profession || DEFAULT_PROFESSION) === activeProfession
    );

    const realOwner =
      currentUser?.username === selectedArtist.owner_username;

    const isOwner = realOwner && !previewAsFan;
    const activeProfessionTips = tipData.results.filter(tip =>
      tip.artist === selectedArtist.owner_username &&
      tip.profession === activeProfession
    );
    const { supporterCount, earnings } = getArtistProfessionStats(selectedArtist, activeProfession);
    const tipTotal = activeProfessionTips
      .reduce((total, tip) => total + Number(tip.artist_share || 0), 0)
      .toFixed(2);
    const primaryTabs = [
      selectedArtist.show_music && "listen",
      selectedArtist.show_posts && "feed",
      "shop",
      selectedArtist.show_lives && "live",
      isOwner && "more",
    ].filter(Boolean);
    const shopSubTabs = [
      selectedArtist.show_store && "merch",
      isMusicBranchProfession(activeProfession) && selectedArtist.show_store && "music-store",
      "support",
    ].filter(Boolean);
    const moreSubTabs = isOwner ? ["calendar", "support-tiers", "settings"] : [];
    const profileSection = primaryTabs.includes(activeTab) ? activeTab : primaryTabs[0];
    const resolvedShopTab = shopSubTabs.includes(activeShopTab) ? activeShopTab : shopSubTabs[0];
    const resolvedMoreTab = moreSubTabs.includes(activeMoreTab) ? activeMoreTab : moreSubTabs[0];
    const currentTab = resolveProfileContentTab(
      profileSection,
      resolvedShopTab,
      resolvedMoreTab,
      activeProfession,
    );
    const showPublicProfileHero = !isOwner || previewAsFan || profileSection === "listen";
    const artistThemeName = resolveLiveArtistThemeName(selectedArtist, {
      isOwner,
      previewAsFan,
      activeTab,
      activeMoreTab,
    });

    return renderAppShell(
      <main
        className={`artist-profile-main artist-profile-main--${activeProfession}`}
        data-profession={activeProfession}
        data-branch={professionBranch(activeProfession)}
      >
        {renderSupportConfirmSheet()}
        {renderExternalLinkConfirm()}
        {renderPlaylistPicker()}
        <ArtistTopbar
          accountActions={renderAccountActions()}
          backLabel={currentUser ? "Back to Listen" : "Back to Home"}
          onBack={() => goToPage(currentUser ? "listen" : "home")}
        />

        {message && <div className="notice">{message}</div>}

        {(showPublicProfileHero || isOwner) && (
        <section className={`profile-hero${!showPublicProfileHero && isOwner ? " profile-hero--banner-only" : ""}`}>
          <ArtistVisitorBanner
            artistId={selectedArtist.owner_id}
            profession={activeProfession}
            bannerUrl={activeProfessionProfile?.visitor_banner}
            bannerDurationSeconds={activeProfessionProfile?.visitor_banner_duration_seconds || 30}
            fallbackCoverImage={activeCoverImage}
            isOwner={isOwner}
            isSaving={visitorBannerSaving}
            onSaveVisitorBanner={saveVisitorBanner}
          />
          {showPublicProfileHero && (
          <>
          <div className="profile-info">
            <div className="profile-avatar">
              {selectedArtist.avatar
                ? <img src={selectedArtist.avatar} alt={selectedArtist.stage_name} />
                : selectedArtist.stage_name?.[0]?.toUpperCase()}
            </div>
            <div>
              <h1>{activeDisplayTitle} {selectedArtist.is_verified ? "✅" : ""}</h1>
              <p className="muted">{activeProfessionLabel} side • {activeStyle || selectedArtist.genre || "Independent"} • {selectedArtist.city}</p>
              {selectedArtist.business_health && (
                <p className="muted">
                  {selectedArtist.business_health.followers} followers · {selectedArtist.business_health.supporter_ratio_label} · {selectedArtist.business_health.engagement.badge}
                </p>
              )}
              {activeProfessionProfile?.tagline && <p className="eyebrow">{activeProfessionProfile.tagline}</p>}
              <p>{activeBio}</p>
              {artistProfessions.length > 1 && (
                <div className="profession-switcher-wrap">
                  <p className="eyebrow">Creative work</p>
                  <div className="profession-switcher" role="tablist" aria-label="Creative work profiles">
                    {artistProfessions.map(profession => (
                      <button
                        key={profession.key}
                        type="button"
                        role="tab"
                        aria-selected={activeProfession === profession.key}
                        className={`profession-side-chip profession-side-chip--${profession.key}${activeProfession === profession.key ? " active" : ""}`}
                        onClick={() => switchArtistProfession(profession.key)}
                      >
                        {profession.label}
                      </button>
                    ))}
                  </div>
                  <p className="muted profession-switcher-hint">Each creative work has its own page, store, and supporters.</p>
                </div>
              )}
              {getArtistSocialLinks(selectedArtist).length > 0 && (
                <div className="social-badge-row">
                  {getArtistSocialLinks(selectedArtist).map(link => (
                    <button
                      key={link.id}
                      className="social-badge"
                      onClick={() => openExternalSocial(link.url, link.label)}
                    >
                      {link.label}
                    </button>
                  ))}
                </div>
              )}
              {(selectedArtist.pinned_pov || artistPovs[0] || isOwner) && (
                <div className="pov-block">
                  <p className="eyebrow">Point of View</p>
                  {(selectedArtist.pinned_pov || artistPovs[0]) ? (
                    <p>{(selectedArtist.pinned_pov || artistPovs[0]).body}</p>
                  ) : (
                    <p className="muted">What’s your perspective?</p>
                  )}
                  {isOwner && (
                    <button className="secondary compact" onClick={() => setShowPovForm(!showPovForm)}>
                      {showPovForm ? "Cancel POV" : "Update POV"}
                    </button>
                  )}
                </div>
              )}
            </div>
            {!realOwner && !(profileSection === "shop" && resolvedShopTab === "support") && (
              <div className="profile-actions">
                {!currentUser ? (
                  <>
                    <button className="primary" onClick={() => goToPage("profile")}>
                      Log in or sign up
                    </button>
                    <button
                      className="secondary"
                      onClick={() => sendDiscoverySignal(selectedDiscoveryRecord || selectedArtist, "save")}
                    >
                      Follow
                    </button>
                  </>
                ) : (
                  <>
                <button className="primary" onClick={() => requestSupport(selectedArtist, supporting, activeProfession)}>
                  {supporting ? "Manage support" : `Support from $${getMinimumSupportAmount(selectedArtist, activeProfession)}/mo`}
                </button>
                {selectedArtist.show_store && (
                  <button className="secondary" onClick={() => navigateProfileSection("shop", {
                    shopTab: isMusicBranchProfession(activeProfession) ? "music-store" : "merch",
                  })}>
                    Buy
                  </button>
                )}
                <button
                  className={selectedSaved ? "secondary supporting" : "secondary"}
                  onClick={() => selectedSaved ? removeSavedArtist(selectedDiscoveryRecord || selectedArtist) : sendDiscoverySignal(selectedDiscoveryRecord || selectedArtist, "save")}
                >
                  {selectedSaved ? "Following" : "Follow"}
                </button>
                <button className="secondary" onClick={() => setShowTipForm(!showTipForm)}>
                  Send Tip
                </button>
                {!isMusicBranchProfession(activeProfession) && (
                  <button className="secondary" onClick={() => setShowCommissionForm(!showCommissionForm)}>
                    Request Commission
                  </button>
                )}
                  </>
                )}
              </div>
            )}
            {realOwner && (
              <div className="profile-actions">
                <button className="primary" onClick={() => copyText(getArtistPublicUrl(), "Page link copied.")}>
                  Copy page link
                </button>
                <button className="secondary" onClick={() => {
                  navigateProfileSection("feed");
                  setShowInstantForm(true);
                }}>
                  Post Instant
                </button>
                <button className="secondary" onClick={() => copyArtistInviteLink()}>
                  Copy invite link
                </button>
                <button className="secondary" onClick={() => copyText(getArtistPublicUrl("instagram"), "Instagram referral link copied.")}>
                  Copy Instagram link
                </button>
              </div>
            )}
          </div>

          {isOwner && showPovForm && (
            <form className="store-form pov-form" onSubmit={createPointOfView}>
              <h3>What’s your perspective?</h3>
              <textarea name="body" maxLength="500" required placeholder="State the lens behind your work..." />
              <div className="action-grid">
                <button className="primary" type="submit">Pin Point of View</button>
                <button className="secondary" type="button" onClick={() => setShowPovForm(false)}>Cancel</button>
              </div>
            </form>
          )}

          {isOwner && showInstantForm && (
            <form className="store-form instant-form" onSubmit={createInstant}>
              <h3>Post Instant</h3>
              <textarea name="body" maxLength="280" required placeholder="A quick note between releases..." />
              <label>Visibility</label>
              <select name="visibility" defaultValue="supporters">
                <option value="supporters">Supporters</option>
                <option value="followers">Followers</option>
                <option value="public">Public</option>
              </select>
              <label>Optional image or short audio</label>
              <input name="media" type="file" accept="image/*,audio/*" />
              <label>Expires after</label>
              <select name="lifetime_hours" defaultValue="24">
                <option value="24">24 hours</option>
                <option value="168">7 days</option>
              </select>
              <p className="muted">Instants are not for full song dumps or fully AI-generated uploads.</p>
              <div className="action-grid">
                <button className="primary" type="submit">Publish Instant</button>
                <button className="secondary" type="button" onClick={() => setShowInstantForm(false)}>Cancel</button>
              </div>
            </form>
          )}

          {!realOwner && currentUser && showTipForm && (
            <form className="store-form tip-form" onSubmit={submitTip}>
              <h3>Send a One-Time Tip</h3>
              <label>Amount</label>
              <input name="amount" type="number" min="1" step="0.01" defaultValue="5.00" />

              <label>Supporter message</label>
              <textarea name="message" maxLength="240" placeholder="Leave a short note for the artist."></textarea>

              <label className="check-row">
                <input name="is_public" type="checkbox" value="true" defaultChecked />
                Show my message publicly on this profile
              </label>
              {!currentUser.share_email_with_supported_artists && (
                <label className="check-row preference-row">
                  <input name="share_email_with_artist" type="checkbox" value="true" />
                  Share my email with this artist
                </label>
              )}
              {Number(promotionWallet?.balance || 0) > 0 && (
                <label className="check-row preference-row">
                  <input
                    name="apply_discovery_credits"
                    type="checkbox"
                    value="true"
                    defaultChecked
                  />
                  Apply up to ${Math.min(
                    Number(promotionWallet.balance),
                    Number(promotionWallet.max_redeem_per_tip || 5),
                  ).toFixed(2)} discovery credits to this tip
                </label>
              )}

              <div className="action-grid">
                <button className="primary" type="submit">Send Tip</button>
                <button className="secondary" type="button" onClick={() => setShowTipForm(false)}>Cancel</button>
              </div>
            </form>
          )}

          {!realOwner && currentUser && !isMusicBranchProfession(activeProfession) && showCommissionForm && (
            <form className="store-form commission-form" onSubmit={submitCommissionRequest}>
              <h3>Request a Commission</h3>
              <label>Request title</label>
              <input name="title" required placeholder="Watercolour portrait, digital cover art, custom piece" />

              <label>Brief</label>
              <textarea name="brief" required placeholder="Describe what you want made, style, purpose, and important details."></textarea>

              <label>Budget</label>
              <input name="budget" type="number" step="0.01" placeholder="120.00" />

              <label>Deadline</label>
              <input name="deadline" type="date" />

              <label>Size / format</label>
              <input name="size_format" placeholder="A4, 30 x 40 cm, profile icon, print-ready file" />

              <label>Reference notes</label>
              <textarea name="reference_notes" placeholder="Describe references, colours, mood, materials, or examples."></textarea>

              <label>Reference links</label>
              <textarea name="reference_links" placeholder="Paste links to references, moodboards, or previous works."></textarea>

              <label>Delivery / shipping notes</label>
              <textarea name="delivery_notes" placeholder="Digital delivery, shipping city, framing, packaging, or timing notes."></textarea>

              <label className="check-row">
                <input name="shipping_required" type="checkbox" value="true" />
                Physical delivery or shipping required
              </label>

              <div className="action-grid">
                <button className="primary" type="submit">Send Request</button>
                <button className="secondary" type="button" onClick={() => setShowCommissionForm(false)}>Cancel</button>
              </div>
            </form>
          )}

          {profilePreviewTrack && (
            <div className="profile-preview">
              {profilePreviewTrack.cover_art ? (
                <img src={profilePreviewTrack.cover_art} alt={profilePreviewTrack.title} />
              ) : (
                <div className="cover-placeholder"></div>
              )}
              <div>
                <p className="eyebrow">Featured track</p>
                {renderTrackTitle(profilePreviewTrack, { className: "track-name-link click-title" })}
                <p className="muted">{profilePreviewTrack.genre} • {formatTrackBpm(profilePreviewTrack.bpm)}</p>
                {profilePreviewTrack.audio_file ? (
                  <button className="primary" onClick={() => handleTogglePlay(profilePreviewTrack)}>
                    {currentTrack?.id === profilePreviewTrack.id && isPlaying ? "Pause Preview" : "Play Preview"}
                  </button>
                ) : (
                  renderLockedTrackPrompt(profilePreviewTrack)
                )}
              </div>
            </div>
          )}

          <div className="stats-row">
            <div><strong>{supporterCount}</strong><span>Supporters</span></div>
            <div><strong>${earnings}</strong><span>Monthly artist revenue</span></div>
            {!currentUser && <div><strong>90%</strong><span>Artist share</span></div>}
          </div>

          {artistCalendarItems.length > 0 && (
            <section className="upcoming-panel">
              <div className="tab-title-row">
                <div>
                  <p className="eyebrow">Upcoming</p>
                  <h3>Dates to watch</h3>
                </div>
                {isOwner && (
                  <button className="secondary compact" onClick={() => openStudioTab("calendar", { createCalendar: true })}>
                    Add date
                  </button>
                )}
              </div>
              <div className="calendar-list">
                {artistCalendarItems.slice(0, 4).map(item => (
                  <article className="calendar-card" key={item.id}>
                    <span>{new Date(item.starts_at).toLocaleDateString(undefined, { month: "short", day: "numeric" })}</span>
                    <div>
                      <strong>{item.title}</strong>
                      <p>{item.item_type_label} · {item.visibility}{item.supporter_early_hours ? ` · supporters ${item.supporter_early_hours}h early` : ""}</p>
                    </div>
                  </article>
                ))}
              </div>
            </section>
          )}

          {activeProfessionTips.length > 0 && (
            <section className="supporter-message-panel">
              <div className="tab-title-row">
                <div>
                  <p className="eyebrow">Supporter Messages</p>
                  <h3>Recent Tips</h3>
                </div>
              </div>
              <div className="supporter-message-list">
                {activeProfessionTips.slice(0, 4).map(tip => (
                  <article className="supporter-message" key={tip.id}>
                    <strong>{tip.fan}</strong>
                    <span>${tip.amount}</span>
                    {tip.message && <p>{tip.message}</p>}
                  </article>
                ))}
              </div>
            </section>
          )}
          </>
          )}
        </section>
        )}

        {!isOwner && renderPromotionPlacements(artistPromotionPlacements, "More to discover")}

        {!isOwner && fansAlsoSupport.length > 0 && (
          <section className="fans-also-support">
            <div className="tab-title-row">
              <div>
                <p className="eyebrow">Discovery</p>
                <h3>Fans also support</h3>
              </div>
            </div>
            <div className="fans-also-support-grid">
              {fansAlsoSupport.map(item => (
                <button
                  type="button"
                  key={item.owner_id}
                  className="fans-also-support-card"
                  onClick={() => openArtist({
                    owner_id: item.owner_id,
                    owner_username: item.owner_username,
                    stage_name: item.stage_name,
                    genre: item.genre,
                    city: item.city,
                    hero_image: item.hero_image,
                    is_verified: item.is_verified,
                  })}
                >
                  {item.hero_image ? (
                    <img src={item.hero_image} alt={item.stage_name} />
                  ) : (
                    <div className="fans-also-support-fallback">{item.stage_name?.[0]?.toUpperCase()}</div>
                  )}
                  <div>
                    <strong>{item.stage_name}</strong>
                    <p className="muted">{item.genre}{item.city ? ` • ${item.city}` : ""}</p>
                    {item.is_emerging && <span className="promoted-badge">Emerging</span>}
                  </div>
                </button>
              ))}
            </div>
          </section>
        )}

        <section className="tabs" aria-label="Artist sections">
          {primaryTabs.map(section => (
            <button
              key={section}
              type="button"
              className={profileSection === section ? "tab active" : "tab"}
              onClick={() => navigateProfileSection(section)}
            >
              {getProfileSectionLabel(section, activeProfession)}
            </button>
          ))}
        </section>

        {profileSection === "shop" && shopSubTabs.length > 0 && (
          <section className="shop-tabs" role="tablist" aria-label="Shop">
            {shopSubTabs.map(shopTab => (
              <button
                key={shopTab}
                type="button"
                role="tab"
                aria-selected={resolvedShopTab === shopTab}
                className={resolvedShopTab === shopTab ? "shop-tab is-active" : "shop-tab"}
                onClick={() => navigateProfileSection("shop", { shopTab })}
              >
                {getProfileShopLabel(shopTab)}
              </button>
            ))}
          </section>
        )}

        {profileSection === "more" && isOwner && moreSubTabs.length > 0 && (
          <section className="tabs tabs--sub profile-more-nav" aria-label="More">
            {moreSubTabs.map(moreTab => (
              <button
                key={moreTab}
                type="button"
                className={resolvedMoreTab === moreTab ? "tab active" : "tab"}
                onClick={() => navigateProfileSection("more", { moreTab })}
              >
                {getProfileMoreLabel(moreTab)}
              </button>
            ))}
            <button
              type="button"
              className="secondary compact profile-more-preview"
              onClick={() => setPreviewAsFan(!previewAsFan)}
            >
              {previewAsFan ? "Exit fan preview" : "Preview as fan"}
            </button>
          </section>
        )}

        <section className="tab-panel">
          {!currentTab && (
            <div className="empty-state">
              <h3>No public sections.</h3>
              <p>This artist has not made any page sections public yet.</p>
            </div>
          )}

          {currentTab === "support-tiers" && isOwner && (
            <>
              <div className="tab-title-row">
                <div>
                  <p className="eyebrow">More</p>
                  <h2>Support tier editor</h2>
                </div>
              </div>
              {renderSupportTierEditorPanel(getArtistStudioSnapshot(selectedArtist, activeProfession))}
            </>
          )}

          {currentTab === "calendar" && isOwner && (
            <>
              <div className="tab-title-row">
                <div>
                  <h2>Calendar</h2>
                  <p className="muted">Plan privately, then publish selected release, live, and gig dates.</p>
                </div>
                <button className="small-action" onClick={() => setShowCalendarForm(true)}>
                  + Add Date
                </button>
              </div>

              {!artistCalendarItems.some(item =>
                item.visibility === "public" &&
                new Date(item.starts_at) <= new Date(Date.now() + 30 * 24 * 60 * 60 * 1000)
              ) && (
                <div className="notice subtle-notice">
                  No public dates in the next 30 days. Add one for consistency.
                </div>
              )}

              {showCalendarForm && (
                <form className="store-form calendar-form" onSubmit={saveCalendarItem} noValidate>
                  <h3>Add Calendar Item</h3>

                  <label>Title</label>
                  <input name="title" required placeholder="Single release, listening party, local show" />

                  <label>Description</label>
                  <textarea name="description" placeholder="Optional details for supporters or fans." />

                  <CalendarItemDateFields onValuesChange={values => { calendarDateValuesRef.current = values; }} />

                  <div className="two-column-form">
                    <div>
                      <label>Type</label>
                      <select name="item_type" defaultValue="release">
                        <option value="release">Release</option>
                        <option value="live">Live</option>
                        <option value="gig">Gig</option>
                        <option value="pov">POV</option>
                        <option value="other">Other</option>
                      </select>
                    </div>
                    <div>
                      <label>Visibility</label>
                      <select name="visibility" defaultValue="private">
                        <option value="private">Private</option>
                        <option value="supporters">Supporters</option>
                        <option value="public">Public</option>
                      </select>
                    </div>
                  </div>

                  <label>Supporter early access hours</label>
                  <input name="supporter_early_hours" type="number" min="0" max="720" defaultValue="0" />

                  <div className="action-grid">
                    <button className="primary" type="submit">Save Date</button>
                    <button className="secondary" type="button" onClick={() => setShowCalendarForm(false)}>Cancel</button>
                  </div>
                </form>
              )}

              <div className="calendar-month-grid">
                {artistCalendarItems.slice(0, 12).map(item => (
                  <article className="calendar-card" key={item.id}>
                    <span>{new Date(item.starts_at).toLocaleDateString(undefined, { month: "short", day: "numeric" })}</span>
                    <div>
                      <strong>{item.title}</strong>
                      <p>{new Date(item.starts_at).toLocaleTimeString([], { hour: "numeric", minute: "2-digit" })} · {item.item_type_label} · {item.visibility}</p>
                    </div>
                  </article>
                ))}
              </div>

              {artistCalendarItems.length === 0 && !showCalendarForm && (
                <div className="empty-state">
                  <h3>No calendar items yet.</h3>
                  <p>Add private plans first, then make selected dates public or supporter-only.</p>
                </div>
              )}
            </>
          )}

          {currentTab === "music" && (
            <>
              <div className="tab-title-row">
                <h2>Listen</h2>
                {isOwner && (
                  <button className="small-action" onClick={() => setShowMusicForm(true)}>
                    + Upload Track
                  </button>
                )}
              </div>

              {isOwner && (
                <section className="song-cover-library">
                  <div className="tab-title-row">
                    <div>
                      <p className="eyebrow">Cover library</p>
                      <h3>Default song artwork</h3>
                      <p className="muted">Upload covers once, reuse them on tracks, and pick one as the fallback default.</p>
                    </div>
                    <button className="secondary compact" type="button" onClick={() => setShowSongCoverForm(current => !current)}>
                      {showSongCoverForm ? "Close" : "+ Add cover"}
                    </button>
                  </div>

                  {showSongCoverForm && (
                    <form className="store-form song-cover-form" onSubmit={uploadSongCover}>
                      <label>Cover label</label>
                      <input name="label" placeholder="Album art, single cover, etc." />

                      <label>Cover image</label>
                      <input name="image" type="file" accept="image/*" required />

                      <label className="check-row">
                        <input name="is_default" type="checkbox" value="true" />
                        Set as default cover for new tracks
                      </label>

                      <div className="action-grid">
                        <button className="primary" type="submit">Save cover</button>
                        <button className="secondary" type="button" onClick={() => setShowSongCoverForm(false)}>Cancel</button>
                      </div>
                    </form>
                  )}

                  {renderSongCoverLibrary()}
                </section>
              )}

              {isOwner && showMusicForm && (
                <form className="store-form" onSubmit={uploadTrack}>
                  <h3>Upload Track</h3>

                  <label>Title</label>
                  <input name="title" required placeholder="Track title" />

                  <label>Genre</label>
                  <input name="genre" placeholder="Hip Hop" />

                  <label>BPM</label>
                  <input name="bpm" type="number" placeholder="98" />

                  <div className="cover-upload-panel">
                    <label>Cover art</label>
                    <div className="cover-mode-tabs">
                      <button
                        type="button"
                        className={trackCoverMode === "upload" ? "cover-mode-tab active" : "cover-mode-tab"}
                        onClick={() => setTrackCoverMode("upload")}
                      >
                        Upload new
                      </button>
                      <button
                        type="button"
                        className={trackCoverMode === "library" ? "cover-mode-tab active" : "cover-mode-tab"}
                        onClick={() => setTrackCoverMode("library")}
                      >
                        Saved cover
                      </button>
                      <button
                        type="button"
                        className={trackCoverMode === "none" ? "cover-mode-tab active" : "cover-mode-tab"}
                        onClick={() => setTrackCoverMode("none")}
                      >
                        Use default
                      </button>
                    </div>

                    {trackCoverMode === "upload" && (
                      <>
                        <input name="cover_art" type="file" accept="image/*" />
                        <label className="check-row">
                          <input
                            type="checkbox"
                            checked={saveCoverToLibrary}
                            onChange={event => setSaveCoverToLibrary(event.target.checked)}
                          />
                          Save to my cover library for reuse
                        </label>
                      </>
                    )}

                    {trackCoverMode === "library" && (
                      <>
                        {getArtistSongCovers().length === 0 ? (
                          <p className="muted">Add a saved cover in the library above first.</p>
                        ) : (
                          <div className="cover-art-picker cover-art-picker--selectable">
                            {getArtistSongCovers().map(cover => (
                              <button
                                key={cover.id}
                                type="button"
                                className={`cover-art-option${String(selectedLibraryCoverId) === String(cover.id) ? " selected" : ""}${cover.is_default ? " is-default" : ""}`}
                                onClick={() => setSelectedLibraryCoverId(String(cover.id))}
                              >
                                <img src={cover.image} alt={cover.label || "Saved cover"} />
                                <span>{cover.label || "Saved cover"}</span>
                                {cover.is_default && <small className="cover-art-badge">Default</small>}
                              </button>
                            ))}
                          </div>
                        )}
                      </>
                    )}

                    {trackCoverMode === "none" && (
                      <p className="muted">This track will use your default saved cover if one is set.</p>
                    )}
                  </div>

                  <label>Audio File</label>
                  <input name="audio_file" type="file" accept="audio/*" required />

                  <section className="ai-disclosure-panel">
                    <div>
                      <p className="eyebrow">AI disclosure</p>
                      <p className="muted">IndieFund is for independent human artists. AI as a tool is welcome with disclosure. Fully AI-generated tracks are not allowed.</p>
                    </div>

                    <label className="check-row">
                      <input
                        name="ai_disclosure_level"
                        type="radio"
                        value="human_made"
                        checked={aiDisclosureLevel === "human_made"}
                        onChange={event => setAiDisclosureLevel(event.target.value)}
                      />
                      Human-made
                    </label>

                    <label className="check-row">
                      <input
                        name="ai_disclosure_level"
                        type="radio"
                        value="ai_assisted"
                        checked={aiDisclosureLevel === "ai_assisted"}
                        onChange={event => setAiDisclosureLevel(event.target.value)}
                      />
                      AI-assisted
                    </label>

                    <label className="check-row">
                      <input
                        name="ai_disclosure_level"
                        type="radio"
                        value="ai_collaborative"
                        checked={aiDisclosureLevel === "ai_collaborative"}
                        onChange={event => setAiDisclosureLevel(event.target.value)}
                      />
                      AI-collaborative
                    </label>

                    <label className="check-row disabled-row">
                      <input type="radio" value="ai_generated" disabled />
                      Fully AI-generated - not permitted
                    </label>

                    {aiDisclosureLevel !== "human_made" && (
                      <>
                        <label>Disclosure note</label>
                        <textarea
                          name="ai_disclosure_note"
                          maxLength="500"
                          required
                          placeholder="Explain the AI-assisted part: MIDI, stems, cleanup, arrangement, or collaboration details."
                        />
                      </>
                    )}
                  </section>

                  <label className="check-row">
                    <input name="is_downloadable" type="checkbox" value="true" />
                    Allow download
                  </label>

                  <label className="check-row">
                    <input name="is_subscriber_only" type="checkbox" value="true" defaultChecked />
                    Full track for supporters only
                  </label>

                  <label className="check-row">
                    <input name="preview_enabled" type="checkbox" value="true" defaultChecked />
                    Public 30-second preview
                  </label>
                  <input name="preview_seconds" type="number" min="10" max="120" defaultValue="30" />

                  <label className="check-row">
                    <input name="allow_fan_radio" type="checkbox" value="true" />
                    Allow this song in fan shuffle mixes
                  </label>

                  <div className="action-grid">
                    <button className="primary" type="submit">Upload Track</button>
                    <button
                      className="secondary"
                      type="button"
                      onClick={() => {
                        setShowMusicForm(false);
                        setTrackCoverMode("upload");
                        setSelectedLibraryCoverId("");
                        setSaveCoverToLibrary(true);
                        setAiDisclosureLevel("human_made");
                      }}
                    >
                      Cancel
                    </button>
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
                    {track.cover_art ? (
                      <img src={track.cover_art} alt={track.title} />
                    ) : (
                      <div className="cover-placeholder"><span>♫</span></div>
                    )}
                    {track.is_subscriber_only && (
                      <div className="post-badges"><span>Supporter only</span></div>
                    )}
                    {track.ai_disclosure_badge && (
                      <div className="post-badges ai-badges"><span>{track.ai_disclosure_badge}</span></div>
                    )}
                    {track.origin_badges?.length > 0 && (
                      <div className="post-badges origin-lock-badges">
                        {track.origin_badges.map(badge => <span key={badge}>{badge}</span>)}
                      </div>
                    )}
                    <ProtectionBadges protection={track.protection} />
                    {isOwner && track.release_status === "pending" && (
                      <div className="origin-lock-pending">
                        <span className="origin-lock-pending-label">Not published yet</span>
                        <button
                          className="secondary compact"
                          type="button"
                          onClick={() => setPendingRelease({
                            id: track.origin_lock?.id,
                            content_title: track.title,
                            file_name: track.origin_lock?.file_name || track.title,
                            ai_usage_status: track.ai_disclosure_level,
                          })}
                        >
                          Finalise Release
                        </button>
                      </div>
                    )}
                    {renderTrackTitle(track, { className: "track-name-link click-title" })}
                    <p>{track.genre} • {formatTrackBpm(track.bpm)}</p>
                    {isOwner && track.funnel && (
                      <p className="muted">
                        Funnel: {track.funnel.preview_plays} previews • {track.funnel.full_plays} full plays • drove {track.funnel.subscriber_conversions_7d} subscriber{track.funnel.subscriber_conversions_7d === 1 ? "" : "s"}
                      </p>
                    )}
                    {track.audio_file ? (
                      <button className="primary compact" onClick={() => handleTogglePlay(track)}>
                        {currentTrack?.id === track.id && isPlaying ? "Pause" : "Play"}
                      </button>
                    ) : track.is_subscriber_only && (
                      renderLockedTrackPrompt(track)
                    )}
                  </article>
                ))}
              </div>

              {selectedArtist.show_about && (
                <section className="about-panel">
                  <h3>About {selectedArtist.stage_name}</h3>
                  {selectedArtist.influences && <p><strong>Influences:</strong> {selectedArtist.influences}</p>}
                  {artistPovs.length > 0 && (
                    <div className="pov-history">
                      <h4>Point of View History</h4>
                      <div className="activity-list">
                        {artistPovs.map(pov => (
                          <article className="activity-item" key={pov.id}>
                            <span>{pov.profession_label || "POV"}</span>
                            <div>
                              <strong>{new Date(pov.created_at).toLocaleDateString()}</strong>
                              <p>{pov.body}</p>
                            </div>
                          </article>
                        ))}
                      </div>
                    </div>
                  )}
                  {selectedArtist.youtube_url && selectedArtist.youtube_reach_verified && (
                    <div className="reach-section">
                      <h4>Reach & Following</h4>
                      <div className="reach-grid">
                        <div className="reach-card">
                          <strong>YouTube</strong>
                          <span>{selectedArtist.youtube_reach} subscribers</span>
                          <small className="reach-verified">Verified by IndieFund</small>
                        </div>
                      </div>
                    </div>
                  )}
                </section>
              )}
            </>
          )}

          {currentTab === "posts" && (
            <>
              {artistInstants.length > 0 && (
                <section className="instant-strip">
                  <div className="tab-title-row">
                    <div>
                      <p className="eyebrow">Instants</p>
                      <h3>Active now</h3>
                    </div>
                  </div>
                  <div className="instant-list">
                    {artistInstants.map(instant => (
                      <article className="instant-card" key={instant.id}>
                        <div className="post-top">
                          <strong>{renderArtistName(instant.artist_username)}</strong>
                          <span>{instant.visibility}</span>
                        </div>
                        <p>{instant.body}</p>
                        {instant.media && (
                          instant.media.match(/\.(mp3|wav|m4a|aac|ogg)(\?|$)/i)
                            ? <audio src={instant.media} controls />
                            : <img src={instant.media} alt="" />
                        )}
                        <div className="post-actions">
                          <span className="muted">Expires {new Date(instant.expires_at).toLocaleString()}</span>
                          {!isOwner && currentUser && (
                            <button className="secondary compact" onClick={() => reportInstant(instant.id)}>Report</button>
                          )}
                        </div>
                      </article>
                    ))}
                  </div>
                </section>
              )}

              <div className="tab-title-row">
                <h2>Feed</h2>
                {isOwner && (
                  <div className="inline-actions">
                    <button className="small-action" onClick={() => setShowInstantForm(true)}>
                      + Instant
                    </button>
                    <button className="small-action" onClick={() => setShowPovForm(true)}>
                      + POV
                    </button>
                    <button className="small-action" onClick={() => setShowPostForm(true)}>
                      + Create Post
                    </button>
                  </div>
                )}
              </div>

              {isOwner && showPostForm && (
                <form className="store-form" onSubmit={createPost}>
                  <h3>Create Post</h3>

                  <div className="social-url-field">
                    <label>Instagram or TikTok URL</label>
                    <input name="external_url" placeholder="Paste a public Instagram Reel/post or TikTok video link" />
                  </div>

                  <label>Attach file</label>
                  <input name="file" type="file" />

                  <label>Title</label>
                  <input name="title" placeholder="Post title" />

                  <label>Body</label>
                  <textarea name="body" placeholder="Write your post..." />

                  <section className="post-access-panel">
                    <div>
                      <label>Comment access</label>
                      <select name="comment_mode" defaultValue="account_default">
                        <option value="account_default">Use artist default</option>
                        <option value="anyone">Anyone</option>
                        <option value="followers_subscribers">Supporters</option>
                        <option value="subscribers_only">Supporters only</option>
                      </select>
                    </div>

                    <label className="check-row">
                      <input name="is_subscriber_only" type="checkbox" value="true" />
                      Supporter only post
                    </label>
                  </section>

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
                      <strong>{renderArtistName(post.author_username)}</strong>
                      <span>{post.post_type}</span>
                    </div>
                    <div className="post-badges">
                      {post.is_subscriber_only && <span>Supporter only</span>}
                      {post.effective_comment_mode && <span>Comments: {post.effective_comment_mode.replaceAll("_", " ")}</span>}
                    </div>
                    <h3>{post.title}</h3>
                    <p>{post.body}</p>

                    {post.external_url ? (
                      <div className="social-post-container">
                        <div className="social-post-main">
                          {renderSocialEmbed(post)}
                        </div>
                        <div className="social-post-comments">
                          {renderPostEngagement(post)}
                        </div>
                      </div>
                    ) : (
                      renderPostEngagement(post)
                    )}
                  </article>
                ))}
              </div>
            </>
          )}

          {currentTab === "works" && (
            <>
              <div className="tab-title-row">
                <h2>Works</h2>
                {isOwner && (
                  <button className="small-action" onClick={() => setShowArtworkForm(true)}>
                    + Add Artwork
                  </button>
                )}
              </div>

              {isOwner && showArtworkForm && (
                <form className="store-form" onSubmit={uploadArtwork}>
                  <h3>Add Artwork</h3>

                  <label>Title</label>
                  <input name="title" required placeholder="Artwork title" />

                  <label>Artwork image</label>
                  <input name="image" type="file" accept="image/*" required />

                  <label>Medium</label>
                  <input name="medium" placeholder="Watercolour, ink, digital painting" />

                  <label>Dimensions</label>
                  <input name="dimensions" placeholder="A3, 30 x 40 cm, 4000px square" />

                  <label>Year</label>
                  <input name="year" type="number" placeholder="2026" />

                  <label>Availability</label>
                  <select name="availability" defaultValue="available">
                    <option value="available">Available</option>
                    <option value="print_only">Print only</option>
                    <option value="sold">Sold</option>
                    <option value="not_for_sale">Not for sale</option>
                  </select>

                  <label>Description</label>
                  <textarea name="description" placeholder="Process notes, materials, or story behind the work"></textarea>

                  <label className="check-row">
                    <input name="is_supporter_only" type="checkbox" value="true" />
                    Supporter only artwork
                  </label>

                  <div className="action-grid">
                    <button className="primary" type="submit">Publish Artwork</button>
                    <button className="secondary" type="button" onClick={() => setShowArtworkForm(false)}>Cancel</button>
                  </div>
                </form>
              )}

              {artistArtworks.length === 0 && !showArtworkForm && (
                <div className="empty-state">
                  <h3>No works yet.</h3>
                  <p>{isOwner ? "Upload artworks, process images, prints, originals, or supporter-only previews." : "This artist has not added works for this creative profile yet."}</p>
                </div>
              )}

              <div className="artwork-grid">
                {artistArtworks.map(artwork => (
                  <article className="artwork-card" key={artwork.id}>
                    {artwork.image ? (
                      <img src={artwork.image} alt={artwork.title} />
                    ) : (
                      <div className="locked-artwork">
                        {renderLockedContentPrompt(artistFromUsername(artwork.artist_username), "this artwork")}
                      </div>
                    )}
                    <div>
                      <p className="eyebrow">{artwork.medium || artwork.profession_label}</p>
                      <h3>{artwork.title}</h3>
                      <p>{artwork.description}</p>
                      <div className="post-badges">
                        {artwork.dimensions && <span>{artwork.dimensions}</span>}
                        {artwork.year && <span>{artwork.year}</span>}
                        {artwork.availability_label && <span>{artwork.availability_label}</span>}
                        {artwork.is_supporter_only && <span>Supporter only</span>}
                      </div>
                    </div>
                  </article>
                ))}
              </div>

              {selectedArtist.show_about && (
                <section className="about-panel">
                  <h3>About {selectedArtist.stage_name}</h3>
                  {selectedArtist.influences && <p><strong>Influences:</strong> {selectedArtist.influences}</p>}
                  {artistPovs.length > 0 && (
                    <div className="pov-history">
                      <h4>Point of View History</h4>
                      <div className="activity-list">
                        {artistPovs.map(pov => (
                          <article className="activity-item" key={pov.id}>
                            <span>{pov.profession_label || "POV"}</span>
                            <div>
                              <strong>{new Date(pov.created_at).toLocaleDateString()}</strong>
                              <p>{pov.body}</p>
                            </div>
                          </article>
                        ))}
                      </div>
                    </div>
                  )}
                </section>
              )}
            </>
          )}

          {currentTab === "merch" && (
            <div>
              <div className="tab-title-row">
                <h2>{isMusicBranchProfession(activeProfession) ? "Merch Store" : `${activeProfessionLabel} Store`}</h2>
                <div className="tab-actions">
                  {isOwner && (
                    <button className="secondary small-action" onClick={() => setPreviewAsFan(!previewAsFan)}>
                      {previewAsFan ? "Unpreview Store" : "Preview Store"}
                    </button>
                  )}
                  {isOwner && !previewAsFan && !storeFormType && (
                    <button className="small-action" onClick={() => setShowStoreTypePicker(true)}>
                      + Add Item
                    </button>
                  )}
                </div>
              </div>

              {isOwner && showStoreTypePicker && (
                <ProductTypePicker
                  filter={["merch", "perks", "pod", "integrations"]}
                  onClose={() => setShowStoreTypePicker(false)}
                  onSelect={(type) => {
                    setStoreFormType(type);
                    setShowStoreTypePicker(false);
                  }}
                />
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

                  {storeFormType === "membership_merch" && (
                    <section className="post-access-panel">
                      <strong>Automatic Subscriber Reward</strong>

                      <label className="check-row">
                        <input name="is_supporter_only" type="checkbox" value="true" defaultChecked disabled />
                        Grant automatically to eligible supporters
                      </label>

                      <div className="reward-hint">
                        💡 <strong>Tip:</strong> Digital products (exclusive tracks, sample packs, acapellas) make great automatic rewards because they don't require shipping!
                      </div>

                      <label style={{marginTop: "14px"}}>Sizes / variants (if physical)</label>
                      <input name="sizes" placeholder="S,M,L,XL or Sticker Pack A" />

                      <label>Stock quantity</label>
                      <input name="stock_quantity" type="number" defaultValue="0" />

                      <label>Eligible after</label>
                      <select name="eligibility_months" defaultValue="3">
                        <option value="1">1 month subscribed</option>
                        <option value="2">2 months subscribed</option>
                        <option value="3">3 months subscribed</option>
                        <option value="6">6 months subscribed</option>
                      </select>

                      <label className="check-row">
                        <input name="shipping_required" type="checkbox" value="true" defaultChecked />
                        Shipping required (physical item)
                      </label>
                    </section>
                  )}

                  {(storeFormType === "external_fulfillment" || storeFormType === "gelato_pod" || storeFormType === "shopify_store" || storeFormType === "printify_pod" || storeFormType === "fourthwall_store" || storeFormType === "bandcamp_store" || storeFormType === "printful_pod") && (
                    <section className="post-access-panel">
                      <strong>{productTypeLabel(storeFormType)}</strong>

                      <label>
                        {storeFormType === "shopify_store" ? "Shopify product URL" :
                         storeFormType === "gelato_pod" ? "Gelato product link" :
                         storeFormType === "printify_pod" ? "Printify product link" :
                         storeFormType === "fourthwall_store" ? "Fourthwall product link" :
                         storeFormType === "bandcamp_store" ? "Bandcamp item URL" :
                         storeFormType === "printful_pod" ? "Printful product link" :
                         "External store URL"}
                      </label>
                      <input name="external_url" type="url" placeholder="https://..." />

                      {(storeFormType === "gelato_pod" || storeFormType === "printify_pod" || storeFormType === "printful_pod") && (
                        <>
                          <label>{productTypeLabel(storeFormType)} SKU (Optional)</label>
                          <input name="fulfillment_notes" placeholder="e.g. tshirt-black-large-01" />
                        </>
                      )}

                      <label>Member discount code</label>
                      <input name="external_discount_code" placeholder="SUPPORTER10" />
                    </section>
                  )}

                  {storeFormType !== "merch" && storeFormType !== "membership_merch" && storeFormType !== "external_fulfillment" && storeFormType !== "gelato_pod" && storeFormType !== "shopify_store" && storeFormType !== "printify_pod" && storeFormType !== "fourthwall_store" && storeFormType !== "bandcamp_store" && storeFormType !== "printful_pod" && (
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

                  {storeFormType !== "membership_merch" && (
                    <label className="check-row">
                      <input name="is_supporter_only" type="checkbox" value="true" />
                      Supporter only
                    </label>
                  )}

                  <div className="action-grid">
                    <button className="primary" type="submit">Upload Product</button>
                    <button className="secondary" type="button" onClick={() => setStoreFormType(null)}>Cancel</button>
                  </div>
                </form>
              )}

              {artistProducts.filter(p => !MUSIC_PRODUCT_TYPES.includes(p.product_type)).length === 0 && !storeFormType && !showStoreTypePicker && (
                <div className="empty-state">
                  <h3>No store items yet.</h3>
                  <p>{isOwner ? "Add products, originals, prints, digital files, supporter perks or external store links." : "This artist has not added items for this creative profile yet."}</p>
                </div>
              )}

              {artistProducts.filter(p => !MUSIC_PRODUCT_TYPES.includes(p.product_type)).length > 0 && (
                <div className="product-grid">
                  {artistProducts.filter(p => !MUSIC_PRODUCT_TYPES.includes(p.product_type)).map(product => (
                    <article className="product-card" id={`product-${product.id}`} key={product.id}>
                      {product.image && <img src={product.image} alt={product.title} />}
                      <div>
                        <p className="eyebrow">{productTypeLabel(product.product_type)}</p>
                        {product.is_supporter_only && (
                          <div className="post-badges"><span>Supporter only</span></div>
                        )}
                        {product.product_type === "membership_merch" && (
                          <div className="post-badges"><span>{product.eligibility_months || 3} month eligibility</span></div>
                        )}
                        {product.product_type === "external_fulfillment" && (
                          <div className="post-badges"><span>Linked store</span></div>
                        )}
                        {product.product_type === "gelato_pod" && (
                          <div className="post-badges"><span>Gelato POD</span></div>
                        )}
                        {product.product_type === "shopify_store" && (
                          <div className="post-badges"><span>Shopify Store</span></div>
                        )}
                        {product.product_type === "printify_pod" && (
                          <div className="post-badges"><span>Printify POD</span></div>
                        )}
                        {product.product_type === "fourthwall_store" && (
                          <div className="post-badges"><span>Fourthwall Store</span></div>
                        )}
                        {product.product_type === "bandcamp_store" && (
                          <div className="post-badges"><span>Bandcamp</span></div>
                        )}
                        {product.product_type === "printful_pod" && (
                          <div className="post-badges"><span>Printful POD</span></div>
                        )}
                        {product.external_discount_code && (
                          <div className="post-badges"><span>Member code: {product.external_discount_code}</span></div>
                        )}
                        {product.origin_badges?.length > 0 && (
                          <div className="post-badges origin-lock-badges">
                            {product.origin_badges.map(badge => <span key={badge}>{badge}</span>)}
                          </div>
                        )}
                        <ProtectionBadges protection={product.protection} />
                        {isOwner && product.release_status === "pending" && (
                          <div className="origin-lock-pending">
                            <span className="origin-lock-pending-label">Not published yet</span>
                            <button
                              className="secondary compact"
                              type="button"
                              onClick={() => setPendingRelease({
                                id: product.origin_lock?.id,
                                content_title: product.title,
                                file_name: product.origin_lock?.file_name || product.title,
                              })}
                            >
                              Finalise Release
                            </button>
                          </div>
                        )}
                        {renderProductTitle(product)}
                        <p>{product.description}</p>
                        <strong>${product.price}</strong>
                        {renderProductLinkAction(product)}
                        {isPurchasableProduct(product) && (
                          <div className="product-buy-row">
                            {isCartableProduct(product) && (
                              <button className="secondary compact" type="button" onClick={() => addToCart(product)}>Add to cart</button>
                            )}
                            <button className="primary compact" type="button" onClick={() => purchaseProduct(product)}>
                              {isCartableProduct(product) ? "Buy now" : "Buy"}
                            </button>
                          </div>
                        )}
                        {product.preview_audio && (
                          <button className="primary compact" onClick={() => handleTogglePlay({ ...product, audio_file: product.preview_audio, is_product: true })}>
                            {currentTrack?.id === product.id && currentTrack?.is_product && isPlaying ? "Pause Preview" : "Play Preview"}
                          </button>
                        )}
                        {isOwner && product.product_file && <p className="muted">Download file uploaded ✅</p>}
                        {!isOwner && <ProductDownloadButton product={product} />}
                        {product.external_url && (
                          <button className="secondary compact" onClick={() => openExternalSocial(buildExternalStoreUrl(product), "external store")}>
                            Open Store
                          </button>
                        )}
                        <ProtectedWorkNotice protection={product.protection} />
                        {!product.can_access && renderLockedProductPrompt(product)}
                      </div>
                    </article>
                  ))}
                </div>
              )}
            </div>
          )}

          {currentTab === "music-store" && (
            <div>
              <div className="tab-title-row">
                <h2>Music Store</h2>
                <div className="tab-actions">
                  {isOwner && (
                    <button className="secondary small-action" onClick={() => setPreviewAsFan(!previewAsFan)}>
                      {previewAsFan ? "Unpreview Store" : "Preview Store"}
                    </button>
                  )}
                  {isOwner && !previewAsFan && !storeFormType && (
                    <button className="small-action" onClick={() => setShowStoreTypePicker(true)}>
                      + Add Music
                    </button>
                  )}
                </div>
              </div>

              {isOwner && showStoreTypePicker && (
                <ProductTypePicker
                  filter={["music"]}
                  onClose={() => setShowStoreTypePicker(false)}
                  onSelect={(type) => {
                    setStoreFormType(type);
                    setShowStoreTypePicker(false);
                  }}
                />
              )}

              {artistProducts.filter(p => MUSIC_PRODUCT_TYPES.includes(p.product_type)).length === 0 && !storeFormType && !showStoreTypePicker && (
                <div className="empty-state">
                  <h3>No music products yet.</h3>
                  <p>{isOwner ? "Add vinyl, cassettes, or digital music products." : "This artist has not added music products yet."}</p>
                </div>
              )}

              <div className="product-grid">
                {artistProducts.filter(p => MUSIC_PRODUCT_TYPES.includes(p.product_type)).map(product => (
                  <article className="product-card" id={`product-${product.id}`} key={product.id}>
                    {product.image && <img src={product.image} alt={product.title} />}
                    <div>
                      <p className="eyebrow">{productTypeLabel(product.product_type)}</p>
                      {renderProductTitle(product)}
                      {product.origin_badges?.length > 0 && (
                        <div className="post-badges origin-lock-badges">
                          {product.origin_badges.map(badge => <span key={badge}>{badge}</span>)}
                        </div>
                      )}
                      <ProtectionBadges protection={product.protection} />
                      {isOwner && product.release_status === "pending" && (
                        <div className="origin-lock-pending">
                          <span className="origin-lock-pending-label">Not published yet</span>
                          <button
                            className="secondary compact"
                            type="button"
                            onClick={() => setPendingRelease({
                              id: product.origin_lock?.id,
                              content_title: product.title,
                              file_name: product.origin_lock?.file_name || product.title,
                            })}
                          >
                            Finalise Release
                          </button>
                        </div>
                      )}
                      <p>{product.description}</p>
                      <strong>${product.price}</strong>
                      {renderProductLinkAction(product)}
                      {isPurchasableProduct(product) && (
                        <div className="product-buy-row">
                          {isCartableProduct(product) && (
                            <button className="secondary compact" type="button" onClick={() => addToCart(product)}>Add to cart</button>
                          )}
                          <button className="primary compact" type="button" onClick={() => purchaseProduct(product)}>Buy now</button>
                        </div>
                      )}
                      {product.preview_audio && (
                        <button className="primary compact" onClick={() => handleTogglePlay({ ...product, audio_file: product.preview_audio, is_product: true })}>
                          {currentTrack?.id === product.id && currentTrack?.is_product && isPlaying ? "Pause Preview" : "Play Preview"}
                        </button>
                      )}
                      {!isOwner && <ProductDownloadButton product={product} />}
                      <ProtectedWorkNotice protection={product.protection} />
                      {!product.can_access && renderLockedProductPrompt(product)}
                    </div>
                  </article>
                ))}
              </div>
            </div>
          )}

          {currentTab === "support" && (
            <section className="support-tier-panel">
              <div className="tab-title-row">
                <div>
                  <p className="eyebrow">Support</p>
                  <h2>Support {selectedArtist.stage_name} from ${getMinimumSupportAmount(selectedArtist, activeProfession)}/mo</h2>
                  <p className="muted">Membership unlocks full tracks, supporter-only posts, drops and live moments.</p>
                </div>
              </div>
              <div className="tier-card-grid">
                <article className="tier-card">
                  <strong>$1 Supporter</strong>
                  <span>Entry membership</span>
                  <p>Unlock supporter access and help this artist keep creating.</p>
                </article>
                {supportTiers
                  .filter(tier => tier.artist === selectedArtist.owner_username && tier.profession === activeProfession)
                  .map(tier => (
                    <article className="tier-card" key={tier.id}>
                      <strong>{tier.name}</strong>
                      <span>${tier.monthly_amount}/month</span>
                      <p>{tier.benefits || tier.description || "Supporter tier."}</p>
                    </article>
                  ))}
              </div>
              {!realOwner && !currentUser && (
                <div className="action-grid">
                  <button className="primary" type="button" onClick={() => goToPage("profile")}>
                    Log in or sign up
                  </button>
                </div>
              )}
              {!realOwner && currentUser && (
                <div className="action-grid">
                  <button className="primary" type="button" onClick={() => requestSupport(selectedArtist, supporting, activeProfession)}>
                    {supporting ? "Manage support" : `Support from $${getMinimumSupportAmount(selectedArtist, activeProfession)}/mo`}
                  </button>
                </div>
              )}
            </section>
          )}

          {currentTab === "lives" && (
            <LiveTab
              cameraDevices={cameraDevices}
              cameraStatus={cameraStatus}
              enableLiveCamera={enableLiveCamera}
              isLive={isLive}
              isOwner={isOwner}
              liveChatMessage={liveChatMessage}
              liveChatMessages={liveChatMessages}
              livePreviewRef={livePreviewRef}
              onCloseLiveForm={closeLiveForm}
              onSendLiveChatMessage={sendLiveChatMessage}
              onStartLiveSession={startLiveSession}
              onStopLiveSession={stopLiveSession}
              renderArtistName={renderArtistName}
              selectedCameraId={selectedCameraId}
              setLiveChatMessage={setLiveChatMessage}
              setSelectedCameraId={setSelectedCameraId}
              setShowLiveForm={setShowLiveForm}
              showLiveForm={showLiveForm}
            />
          )}


          {currentTab === "settings" && (
            <>
              <h2>Artist Settings</h2>

              {showEditProfile && (
                <form className="store-form" onSubmit={updateArtistProfile}>
                  <h3>Edit Profile</h3>

                  <label>Stage Name</label>
                  <input name="stage_name" defaultValue={selectedArtist.stage_name} />

                  <label>Cover Photo</label>
                  <input name="hero_image" type="file" accept="image/*" />
                  {selectedArtist.hero_image && <p className="form-hint">Uploading a new image replaces the current cover photo.</p>}
                  <input name="active_profession" type="hidden" value={activeProfession} />

                  <div className="profession-picker">
                    <label>Creative work</label>
                    <div className="profession-grid">
                      {Object.entries(PROFESSION_LABELS).map(([key, label]) => (
                        <label className="check-row" key={key}>
                          <input
                            name="professions"
                            type="checkbox"
                            value={key}
                            defaultChecked={getArtistProfessions(selectedArtist).some(profession => profession.key === key)}
                          />
                          {label}
                        </label>
                      ))}
                    </div>
                  </div>

                  <label>Genre</label>
                  <input name="genre" defaultValue={selectedArtist.genre} />

                  <label>City</label>
                  <input name="city" defaultValue={selectedArtist.city} />

                  <label>Bio</label>
                  <textarea name="artist_story" defaultValue={selectedArtist.artist_story}></textarea>

                  <label>Influences</label>
                  <input name="influences" defaultValue={selectedArtist.influences} />

                  <section className="post-access-panel">
                    <strong>{activeProfessionLabel} profile details</strong>

                    <label>Profile title</label>
                    <input name="profession_display_title" defaultValue={activeProfessionProfile?.display_title || ""} placeholder={selectedArtist.stage_name} />

                    <label>Short tagline</label>
                    <input name="profession_tagline" defaultValue={activeProfessionProfile?.tagline || ""} placeholder={isMusicBranchProfession(activeProfession) ? "New sets, episodes, shorts, demos and live sketches" : "Watercolour originals, prints and process notes"} />

                    <label>{isMusicBranchProfession(activeProfession) ? "Genre / format" : "Medium / style"}</label>
                    <input name="profession_style" defaultValue={activeProfessionProfile?.style || ""} placeholder={isMusicBranchProfession(activeProfession) ? "Comedy sets, interview podcast, short film" : "Watercolour, ink, digital painting"} />

                    <label>{activeProfessionLabel} bio</label>
                    <textarea name="profession_bio" defaultValue={activeProfessionProfile?.bio || ""} placeholder="Write the story for this side of your work."></textarea>

                    <label>{activeProfessionLabel} cover photo</label>
                    <input name="profession_cover_image" type="file" accept="image/*" />
                    {activeProfessionProfile?.cover_image && <p className="form-hint">This replaces the cover for the current creative profile only.</p>}
                  </section>

                  <label>Instagram URL</label>
                  <input name="instagram_url" type="url" defaultValue={selectedArtist.instagram_url || ""} placeholder="https://www.instagram.com/..." />

                  <label>TikTok URL</label>
                  <input name="tiktok_url" type="url" defaultValue={selectedArtist.tiktok_url || ""} placeholder="https://www.tiktok.com/@..." />

                  <label>YouTube URL</label>
                  <input name="youtube_url" type="url" defaultValue={selectedArtist.youtube_url || ""} placeholder="https://www.youtube.com/@yourchannel" />
                  <p className="form-hint">
                    {selectedArtist.youtube_reach_verified
                      ? `Verified reach: ${selectedArtist.youtube_reach} subscribers, pulled directly from YouTube.`
                      : "Add your channel URL and IndieFund displays your real subscriber count, verified from YouTube."}
                  </p>

                  <label>Website URL</label>
                  <input name="website_url" type="url" defaultValue={selectedArtist.website_url || ""} placeholder="https://..." />

                  <label>Website Label (e.g. Official Store)</label>
                  <input name="website_label" defaultValue={selectedArtist.website_label || ""} placeholder="Official Site" />

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
                  <p><strong>Social links:</strong> {getArtistSocialLinks(selectedArtist).length || "None added"}</p>

                  <button className="primary" onClick={() => setShowEditProfile(true)}>
                    Edit Profile
                  </button>
                </div>

                <div className="feature-card">
                  <h3>Page Builder</h3>

                  <form onSubmit={savePageBuilder} className="settings-form">
                    <label className="check-row">
                      <input name="show_music" type="checkbox" defaultChecked={selectedArtist.show_music} />
                      Show Listen
                    </label>

                    <label className="check-row">
                      <input name="show_posts" type="checkbox" defaultChecked={selectedArtist.show_posts} />
                      Show Feed
                    </label>

                    <label className="check-row">
                      <input name="show_store" type="checkbox" defaultChecked={selectedArtist.show_store} />
                      Show Store
                    </label>

                    <label className="check-row">
                      <input name="show_lives" type="checkbox" defaultChecked={selectedArtist.show_lives} />
                      Show Live
                    </label>

                    <label className="check-row">
                      <input name="show_about" type="checkbox" defaultChecked={selectedArtist.show_about} />
                      Show About on Listen
                    </label>

                    <button className="secondary" type="submit">
                      Save Layout
                    </button>
                  </form>
                </div>

                <div className="feature-card feature-card--full">
                  <ArtistThemeSettings
                    key={`studio-${selectedArtist.theme_name}-${selectedArtist.studio_theme_name}`}
                    activePreviewTarget={themePreview?.target || null}
                    themeName={selectedArtist.theme_name}
                    studioThemeName={selectedArtist.studio_theme_name}
                    onPreviewChange={setThemePreview}
                    onSave={saveArtistThemes}
                  />
                </div>

              </div>

              {isOwner && renderArtistStudioTools(getArtistStudioSnapshot(selectedArtist, activeProfession))}
            </>
          )}

        </section>
      </main>
    , `artist-profile-shell ${artistThemeName} artist-profile-shell--profession-${activeProfession} artist-profile-shell--branch-${professionBranch(activeProfession)}${showPublicProfileHero ? "" : " artist-profile-shell--studio"}`
    );
  }

  return renderAppShell(
    <main className={`page-${activePage}${!currentUser && (activePage === "home" || activePage === "early-access") ? " page-guest-auth" : ""}`}>
      {renderSupportConfirmSheet()}
      {renderSpaceReviewModal()}
      {renderExternalLinkConfirm()}
      {renderPlaylistPicker()}

      {!currentUser && !isUserLoading && (activePage === "home" || activePage === "early-access") && isPrelaunchMode(platformMode) ? (
        <>
          {message && <div className="notice">{message}</div>}
          <CreatorEarlyAccessLanding
            featuredArtists={featuredArtists}
            authPanel={authPanel}
            onArtistSignup={() => openCreatorSignup("artist")}
            onHostSignup={() => openCreatorSignup("host")}
            onFanWaitlist={openFanWaitlist}
            onFaq={() => goToPage("faq")}
            onBrowseArtist={username => {
              window.location.href = `/?artist=${encodeURIComponent(username)}`;
            }}
          />
        </>
      ) : !currentUser && !isUserLoading && activePage === "home" ? (
        <>
          {message && <div className="notice">{message}</div>}
          <section className="guest-landing">
            <IndieFundLogo className="guest-brand" />
            <h1>Build a sustainable music business with your fans</h1>
            <p className="muted guest-lead">
              Subscriptions, merch, local shows, and fair discovery — owned by artists, not algorithms.
            </p>
            <div className="action-grid guest-cta-row">
              <button className="primary" type="button" onClick={() => goToPage("listen")}>Browse without account</button>
              <button className="secondary" type="button" onClick={() => goToPage("faq")}>How it works</button>
            </div>
            {featuredArtists.length > 0 && (
              <section className="featured-artists-row" aria-label="Featured artists">
                <p className="eyebrow">Launch artists</p>
                <div className="featured-artist-grid">
                  {featuredArtists.map(artist => (
                    <button key={artist.id} type="button" className="featured-artist-card" onClick={() => { window.location.href = `/?artist=${artist.username}`; }}>
                      <strong>{artist.stage_name || artist.username}</strong>
                      <span className="muted">{artist.city}{artist.genre ? ` • ${artist.genre}` : ""}</span>
                    </button>
                  ))}
                </div>
              </section>
            )}
            <div className="guest-auth-wrap">
              {authPanel}
            </div>
          </section>
        </>
      ) : (
        <>
      <MainTopbar
        accountActions={renderAccountActions()}
        activePage={activePage}
        channelRail={showFanArtistRail() ? renderFanArtistRail() : null}
        currentUser={currentUser}
        globalSearchResults={globalSearchResults}
        listenTab={listenTab}
        onGlobalSearch={runGlobalSearch}
        onOpenSearchResult={openGlobalSearchResult}
        onLogin={() => goToPage("profile")}
        onNavigate={goToPage}
        searchLocation={searchLocation}
        searchQuery={searchQuery}
        setSearchLocation={setSearchLocation}
        setSearchQuery={setSearchQuery}
      />

      {message && <div className="notice">{message}</div>}

      {activePage === "prelaunch" && (
        <PrelaunchFanGate
          onArtistSignup={() => openCreatorSignup("artist")}
          onHostSignup={() => openCreatorSignup("host")}
          onFanWaitlist={openFanWaitlist}
          onHome={() => goToPage(isPrelaunchMode(platformMode) ? "early-access" : "home")}
        />
      )}

      {activePage === "listen" && !(listenTab === "discover" && discoverView === "saved") && (
        <>
          {renderListenSectionHead()}
          {renderListenTabRow()}
        </>
      )}

      {activePage === "stores" && currentUser && (
        <>
          {renderStoresSectionHead()}
          {renderStoresTabRow()}
        </>
      )}

      {activePage === "home" && !currentUser && isUserLoading && (
        <section className="home-dashboard-head section-head">
          <p className="muted">Loading your account…</p>
        </section>
      )}

      {activePage === "home" && currentUser && renderHomeDashboard()}

      {activePage === "feed" && !currentUser && (
        <section className="space-panel">
          <p className="eyebrow">Feed</p>
          <h2>Artist updates</h2>
          <p className="muted">Log in to see posts and drops from artists you follow.</p>
          <button className="primary" type="button" onClick={() => goToPage("profile")}>Sign up or log in</button>
        </section>
      )}

      {activePage === "feed" && currentUser && renderFanFeedPage()}

      {activePage === "listen" && (
        <>
          {!currentUser && !isUserLoading && listenTab === "discover" && discoverView !== "saved" && (
            <section className="guest-browse-banner">
              <p>Browsing as a guest. <button type="button" className="link-button" onClick={() => goToPage("profile")}>Create a free fan account</button> to save artists and personalize discovery.</p>
            </section>
          )}
          {listenTab === "discover" && discoverView === "saved" ? renderSavedArtistsSection() : (
            <>
              {listenTab === "discover" ? (
                <>
                  <section className="section-head discovery-head tab-title-row">
                    <div>
                      <p className="eyebrow">Discovery</p>
                      <h3>{discoveryMode === "songs" ? "Recommended Songs" : "Recommended Artists"}</h3>
                      <p>
                        {discoveryMode === "songs"
                          ? (currentUser ? "Swipe tracks, save songs to My Playlists, and keep finding new drops." : "Preview songs from independent artists.")
                          : (currentUser ? "Ranked from your genres, location, saves and support." : "Ranked by activity, identity and early community signals.")}
                      </p>
                    </div>
                  </section>

                  {renderDiscoveryCreditsBanner()}

                  <section className="discovery-mode-row">
                    <div className="discovery-mode-toggle" role="tablist" aria-label="Discovery mode">
                      <button
                        type="button"
                        className={discoveryMode === "artists" ? "discovery-mode-pill active" : "discovery-mode-pill"}
                        onClick={() => setDiscoveryBrowseMode("artists")}
                      >
                        Artists
                      </button>
                      <button
                        type="button"
                        className={discoveryMode === "songs" ? "discovery-mode-pill active" : "discovery-mode-pill"}
                        onClick={() => setDiscoveryBrowseMode("songs")}
                      >
                        Songs
                      </button>
                    </div>
                  </section>

                  <section className="discovery-filter-row">
                    <select
                      value={searchProfession}
                      onChange={(event) => setSearchProfession(event.target.value)}
                      aria-label="Filter by profession"
                    >
                      <option value="">All professions</option>
                      {Object.entries(PROFESSION_LABELS).map(([key, label]) => (
                        <option value={key} key={key}>{label}</option>
                      ))}
                    </select>
                  </section>

                  {currentUser && (
                    <section className="discovery-prefs-row feature-card">
                      <p className="eyebrow">Your discovery mix</p>
                      <div className="discovery-prefs-grid">
                        <label className="check-row preference-row">
                          <input
                            type="checkbox"
                            checked={Boolean(currentUser.discovery_prefer_emerging)}
                            onChange={event => saveDiscoveryPreferences({ discovery_prefer_emerging: event.target.checked })}
                          />
                          Emerging artists first
                        </label>
                        <label className="check-row preference-row">
                          <input
                            type="checkbox"
                            checked={Boolean(currentUser.discovery_fewer_promoted)}
                            onChange={event => saveDiscoveryPreferences({ discovery_fewer_promoted: event.target.checked })}
                          />
                          Fewer promoted posts
                        </label>
                        <label className="check-row preference-row">
                          <input
                            type="checkbox"
                            checked={Boolean(currentUser.discovery_promoted_genres_only)}
                            onChange={event => saveDiscoveryPreferences({ discovery_promoted_genres_only: event.target.checked })}
                          />
                          Promoted music in my genres only
                        </label>
                      </div>
                    </section>
                  )}

                  {(discoveryMode === "songs" ? filteredTracks.length === 0 : filteredArtists.length === 0) ? (
                    <div className="empty-state full-span">
                      <h3>{discoveryMode === "songs" ? "No new songs to discover." : "No new artists to discover."}</h3>
                      <p>
                        {currentUser && (discoveryMode === "songs" ? discoveryTrackMeta.exhausted : discoveryMeta.exhausted)
                          ? discoveryMode === "songs"
                            ? "You have saved or skipped every track we can match to your taste right now. Try artist discovery or open My Playlists."
                            : "You have saved or skipped everyone we can match to your taste right now. Open Saved Artists or reset skips to keep exploring."
                          : (discoveryMode === "songs" ? discoveryTrackMeta : discoveryMeta).skipped_count > 0
                          ? "Your skipped items are hidden. Reset skips or clear your search filters to bring recommendations back."
                          : searchLocation || searchQuery
                            ? "Try changing or clearing your search filters."
                            : discoveryMode === "songs"
                              ? "Upload music as an artist to seed the song discovery stack."
                              : "Register as an artist to create the first artist page."}
                      </p>
                      <div className="action-grid empty-actions">
                        {(searchLocation || searchQuery || searchProfession) && (
                          <button className="secondary" onClick={() => { setSearchQuery(""); setSearchLocation(""); setSearchProfession(""); }}>
                            Clear Search
                          </button>
                        )}
                        {discoveryMode === "artists" && (
                          <button className="secondary" onClick={showAllArtists}>
                            Show All Artists
                          </button>
                        )}
                        {(discoveryMode === "songs" ? discoveryTrackMeta : discoveryMeta).skipped_count > 0 && discoveryMode === "artists" && (
                          <button className="secondary" onClick={resetSkippedArtists}>
                            Reset Skipped Artists
                          </button>
                        )}
                        {currentUser && savedArtists.length > 0 && discoveryMode === "artists" && (
                          <button className="secondary" onClick={() => goToPage("saved")}>
                            View Saved Artists
                          </button>
                        )}
                        {discoveryMode === "songs" && (
                          <button className="secondary" onClick={() => setDiscoveryBrowseMode("artists")}>
                            Switch to Artists
                          </button>
                        )}
                      </div>
                    </div>
                  ) : (discoveryMode === "songs" ? renderReviewTrack() : renderReviewArtist())}
                </>
              ) : (
                <>
                  <section id="music" className="section-head">
                    <div>
                      <p className="eyebrow">Latest drops</p>
                      <h3>Latest music</h3>
                      <p className="muted">Browse new uploads and save tracks to playlists in My Playlists.</p>
                    </div>
                    {currentUser ? (
                      <button className="secondary" onClick={() => goToPage("my-music")}>Open My Playlists</button>
                    ) : (
                      <button className="secondary" onClick={() => goToPage("profile")}>Sign up to save tracks</button>
                    )}
                  </section>

                  <section className="music-grid">
                    {latestMusicTracks.length === 0 && (
                      <div className="empty-state full-span">
                        <h3>{fanChannelUsername ? "No music from this artist yet." : "No music uploaded yet."}</h3>
                        <p>{fanChannelUsername ? "Try another channel or browse all artists." : "Artist accounts can upload their first track from their artist page."}</p>
                      </div>
                    )}

                    {latestMusicTracks.map(track => (
                      <article className="music-card" key={track.id}>
                        {track.cover_art ? <img src={track.cover_art} alt={track.title} /> : <div className="cover-placeholder"></div>}
                        <div>
                          {track.is_subscriber_only && (
                            <div className="post-badges"><span>Supporter only</span></div>
                          )}
                          {track.ai_disclosure_badge && (
                            <div className="post-badges ai-badges"><span>{track.ai_disclosure_badge}</span></div>
                          )}
                          <ProtectionBadges protection={track.protection} />
                          {renderTrackTitle(track, { className: "track-name-link click-title" })}
                          <p className="muted">
                            {renderArtistName(track.artist_username)} • {track.genre} • {formatTrackBpm(track.bpm)}
                          </p>
                          {track.audio_file ? (
                            <div className="action-grid">
                              <button className="primary compact" onClick={() => handleTogglePlay(track)}>
                                {currentTrack?.id === track.id && isPlaying ? "Pause" : "Play"}
                              </button>
                              {currentUser && (
                                <button className="secondary compact" onClick={() => openPlaylistPicker(track)}>
                                  Add to Playlist
                                </button>
                              )}
                            </div>
                          ) : track.is_subscriber_only && (
                            renderLockedTrackPrompt(track)
                          )}
                        </div>
                      </article>
                    ))}
                  </section>
                </>
              )}
            </>
          )}
        </>
      )}

      {activePage === "my-music" && (
        <>
          <section id="my-music" className="section-head">
            <div>
              <p className="eyebrow">Your library</p>
              <h2>My Playlists</h2>
              <p className="muted">
                Songs you saved, grouped by artist. Play your saves, explore more from each artist, or turn a batch into a playlist.
              </p>
            </div>
            <div className="action-grid">
              {getMyMusicTracks().length > 0 && (
                <button className="primary compact" type="button" onClick={() => playQueue(getMyMusicTracks(), 0, "My Playlists")}>
                  Play all saved
                </button>
              )}
              <button className="secondary" type="button" onClick={() => goToListenTab("latest")}>Browse latest music</button>
            </div>
          </section>

          {renderMyMusicLayout()}
        </>
      )}

      {activePage === "spaces" && renderSpacesPage()}

      {activePage === "my-scene" && (
        <MyScenePage
          apiFetch={apiFetch}
          currentUser={currentUser}
          initialShowId={mySceneShowId}
          fanChannelUsername={fanChannelUsername}
          onGoToProfile={() => goToPage("profile")}
          onOpenArtistByUsername={openArtistByUsername}
          onOpenArtistFromGig={openArtistFromGig}
          onPurchaseTicket={(product, show) => purchaseProduct(product, show)}
          ownedTicketProductIds={ownedTicketProductIds()}
          products={products}
          refreshSignal={viewRefreshKey}
        />
      )}

      {activePage === "stores" && !currentUser && (
        <section className="space-panel">
          <p className="eyebrow">IndieFund | Stores</p>
          <h2>Stores</h2>
          <p className="muted">Log in to browse merch and music from artists you support.</p>
          <button className="primary" type="button" onClick={() => goToPage("profile")}>Sign up or log in</button>
        </section>
      )}

      {activePage === "stores" && currentUser && (
        <FanStoresPage
          channels={getFanSubscriptionChannels()}
          selectedChannelUsername={fanChannelUsername}
          storeTab={storeTab}
          onOpenArtistByUsername={openArtistByUsername}
          products={products}
          musicProductTypes={new Set(MUSIC_PRODUCT_TYPES)}
          productTypeLabel={productTypeLabel}
          isPurchasableProduct={isPurchasableProduct}
          isCartableProduct={isCartableProduct}
          onAddToCart={addToCart}
          onPurchase={purchaseProduct}
          onPlayPreview={(product) => handleTogglePlay({ ...product, audio_file: product.preview_audio, is_product: true })}
          currentTrack={currentTrack}
          isPlaying={isPlaying}
          renderLockedProductPrompt={renderLockedProductPrompt}
        />
      )}

      {!currentUser?.is_host && (
        <StoreCart
          cartItems={storeCart}
          currentUser={currentUser}
          open={showStoreCart}
          onCheckout={checkoutCart}
          onClose={() => setShowStoreCart(false)}
          onOpenArtist={openArtistByUsername}
          onRemove={removeFromCart}
        />
      )}

      {pendingRelease && (
        <FinalizeReleasePanel
          release={pendingRelease}
          currentUser={currentUser}
          apiFetch={apiFetch}
          onClose={() => setPendingRelease(null)}
          onMessage={setMessage}
          onSealed={() => {
            setPendingRelease(null);
            loadData();
          }}
        />
      )}

      {activePage === "notifications" && (
        <NotificationsPage
          currentUser={currentUser}
          notificationData={notificationData}
          notifications={getNotifications()}
          onDiscover={() => goToPage("listen")}
          onMarkRead={markNotificationsRead}
          onClearAll={clearAllNotifications}
          onClearNotification={clearNotification}
          onOpenArtistByUsername={openArtistByUsername}
          onOpenNotification={openNotification}
        />
      )}

      {activePage === "promote" && (
        <PromotePage
          currentUser={currentUser}
          music={music}
          posts={posts}
          products={products}
          wallet={promotionWallet}
          campaigns={promotionCampaigns}
          genres={promotionGenres}
          targetingSuggestions={promotionTargetingSuggestions}
          artistProfile={getCurrentArtist()}
          onBuyCredits={buyPromotionCredits}
          onCreateCampaign={createPromotionCampaign}
          onCampaignAction={updatePromotionCampaign}
          onUpgradePlan={upgradeArtistPlan}
          onLoadTargetingSuggestions={loadPromotionTargetingSuggestions}
          onSearchTargetArtists={searchPromotionTargetArtists}
        />
      )}

      {activePage === "fans" && currentUser?.is_artist && (
        <FanCrmPage apiFetch={apiFetch} />
      )}

      {activePage === "ads-manager" && currentUser?.is_artist && (
        <AdsManagerPage
          campaigns={growthCampaigns}
          artistPageUrl={getArtistPublicUrl("", getCurrentArtist())}
          busy={growthCampaignBusy}
          onCreateCampaign={createGrowthCampaign}
          onUpdateCampaign={updateGrowthCampaign}
          onDeleteCampaign={deleteGrowthCampaign}
          onUpdateStatus={updateGrowthCampaignStatus}
          onGoToPromote={() => goToPage("promote")}
        />
      )}

      {activePage === "faq" && (
        <section className="faq-page">
          <p className="eyebrow">Help</p>
          <h2>Frequently asked questions</h2>
          <div className="faq-grid">
            <article className="feature-card">
              <h3>Is IndieFund free for fans?</h3>
              <p className="muted">Yes. Browsing, discovery, and following artists are free. You only pay when you choose to support, tip, or buy merch.</p>
            </article>
            <article className="feature-card">
              <h3>How do artists get paid?</h3>
              <p className="muted">Fans subscribe, tip, and buy directly. Artists connect Stripe for payouts; IndieFund keeps a transparent platform fee on each transaction.</p>
            </article>
            <article className="feature-card">
              <h3>What fees does IndieFund charge?</h3>
              <p className="muted">10% on support (5% on paid plans), 0% on tips, 15% on marketplace sales (12% on Studio) and show tickets. Venue door splits on ticketed shows are handled automatically when your space uses a door-percent deal. See your artist dashboard for the full fee schedule.</p>
            </article>
            <article className="feature-card">
              <h3>How do show tickets work?</h3>
              <p className="muted">Artists sell tickets in-app when a space booking is confirmed — no Eventbrite or external merchant needed. Each buyer gets a unique door code; hosts verify it at entry for accurate attendance.</p>
            </article>
            <article className="feature-card">
              <h3>How is this different from streaming?</h3>
              <p className="muted">IndieFund is built for direct fan relationships and sustainable artist businesses — not passive play counts.</p>
            </article>
          </div>
          <p className="muted">Questions? Email <a href={`mailto:${SUPPORT_EMAIL}`}>{SUPPORT_EMAIL}</a></p>
        </section>
      )}

      {LEGAL_PAGE_IDS.has(activePage) && (
        <LegalPageView pageId={activePage} onNavigate={goToPage} />
      )}

      {activePage === "profile" && (
        <ProfilePage
          askBeforeExternalSocial={askBeforeExternalSocial}
          authPanel={authPanel}
          currentUser={currentUser}
          fanEmailSharing={fanEmailSharing}
          fanTotal={fanTotal}
          hideSocialEmbeds={hideSocialEmbeds}
          mailingList={mailingList}
          myTickets={myPurchases.tickets || []}
          myPurchases={myPurchases.results || []}
          mySubscriptions={(subData.subscriptions || []).filter(sub => sub.fan_id === currentUser?.id && sub.active)}
          onManageSupport={(username, profession) => manageSupport(username, profession)}
          onOpenMyMusic={() => goToPage("my-music")}
          onOpenTicketShow={(bookingId) => goToMyScene(bookingId || null)}
          savedCount={savedArtists.length}
          studioSnapshot={currentUser?.is_artist ? getOwnerStudioSnapshot() : null}
          supportedCount={getSupportedArtistUsernames().length}
          onBetaFeedback={submitBetaFeedback}
          betaFeedbackSummary={betaFeedbackSummary}
          onRefreshBetaSummary={loadBetaFeedbackSummary}
          onResolveBetaFeedback={resolveBetaFeedback}
          onExportMailingList={exportMailingList}
          onFanEmailSharingChange={saveFanEmailSharing}
          onLogout={handleLogout}
          onUploadProfileMedia={uploadProfileMedia}
          onOpenPageSettings={() => openStudioTab("settings")}
          onOpenThemeSettings={() => goToPage("profile", true, { tab: "themes" })}
          onOpenTrustSettings={() => openStudioTab("settings")}
          onProfileTabChange={(tab) => {
            if (tab === "settings") {
              goToPage("profile", true, { tab, section: settingsSection || "library" });
              return;
            }
            goToPage("profile", true, { tab });
          }}
          profileTab={profileTab}
          settingsSection={settingsSection}
          onSettingsSectionChange={openSettingsSection}
          themePreview={themePreview}
          onThemePreviewChange={setThemePreview}
          themeSettings={
            currentUser?.is_artist
              ? {
                  variant: "artist",
                  themeName: getCurrentArtist()?.theme_name,
                  studioThemeName: getCurrentArtist()?.studio_theme_name,
                  onSave: saveArtistThemes,
                }
              : currentUser?.is_host
                ? {
                    variant: "host",
                    themeName: currentUser.theme_name,
                    onSave: saveFanTheme,
                  }
                : currentUser
                  ? {
                      variant: "fan",
                      themeName: currentUser.theme_name,
                      onSave: saveFanTheme,
                    }
                  : null
          }
          onOpenPublicPage={() => openArtistHome()}
          onOpenArtistByUsername={openArtistByUsername}
          artistTrustStatus={currentUser?.is_artist ? artistTrustStatus : null}
          pushEnabled={pushEnabled}
          pushSupported={pushSupported}
          onEnablePush={enablePushNotifications}
          onDisablePush={disablePushNotifications}
          onSaved={() => goToPage("saved")}
          onSetAskBeforeExternalSocial={saveExternalSocialPreference}
          onSetGlobalEmailSharing={saveGlobalEmailSharing}
          onSaveDiscoveryLocation={saveDiscoveryLocation}
          onSaveDiscoveryPreferences={saveDiscoveryPreferences}
          onSetHideSocialEmbeds={saveHideSocialEmbedsPreference}
          promotionWallet={promotionWallet}
          spaceHostProfile={spaceHostProfile}
          onSaveHostProfile={saveHostProfile}
        />
      )}

        </>
      )}

      </main>
  , resolveAppShellPageClass()
  );
}

createRoot(document.getElementById("root")).render(
  <>
    <IubendaConsent />
    {!isIubendaConsentConfigured() ? (
      <CookieConsentFallback onOpenCookies={() => { window.location.href = "/?page=cookies"; }} />
    ) : null}
    <App />
  </>
);
