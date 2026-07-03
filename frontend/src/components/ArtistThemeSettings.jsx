import React, { useEffect, useState } from "react";
import { DEFAULT_THEME, DEFAULT_HOST_THEME, getThemeOption, groupThemeOptionsForVariant, normalizeHostThemeId, normalizeThemeId } from "../lib/themes.js";

function ThemePreviewPanel({ label, themeId, sampleTitle = "Your page", audienceNote = "" }) {
  const theme = getThemeOption(themeId);

  return (
    <div className={`theme-live-preview ${normalizeThemeId(themeId)}`} aria-live="polite">
      <div className="theme-live-preview-head">
        <p className="eyebrow">Preview</p>
        <strong>{label}: {theme.label}</strong>
        {audienceNote && <p className="muted theme-preview-audience">{audienceNote}</p>}
      </div>
      <div className="theme-preview-sample">
        <div className="feature-card theme-preview-card">
          <p className="eyebrow">Sample</p>
          <h4>{sampleTitle}</h4>
          <p className="muted">Buttons, cards, and accents use this palette.</p>
          <div className="theme-preview-actions">
            <button type="button" className="primary compact">Primary</button>
            <button type="button" className="secondary compact">Secondary</button>
          </div>
        </div>
      </div>
    </div>
  );
}

function ThemePickerRow({
  activePreviewTarget,
  checked,
  name,
  onChange,
  onPreview,
  previewTarget,
  theme,
  value,
}) {
  const isPreviewing = activePreviewTarget === previewTarget && checked;

  return (
    <div className={`theme-picker-row ${value}${isPreviewing ? " theme-picker-row--previewing" : ""}`}>
      <label className="theme-picker-option">
        <input
          type="radio"
          name={name}
          value={value}
          checked={checked}
          onChange={onChange}
        />
        <span>
          <strong>{theme.label}</strong>
          <small>{theme.blurb}</small>
          <span className="theme-swatch" aria-hidden="true" />
        </span>
      </label>
      <button
        type="button"
        className={isPreviewing ? "primary compact theme-picker-preview-btn" : "secondary compact theme-picker-preview-btn"}
        aria-pressed={isPreviewing}
        onClick={onPreview}
      >
        {isPreviewing ? "Previewing" : "Preview"}
      </button>
    </div>
  );
}

export function ArtistThemeSettings({
  activePreviewTarget = null,
  studioThemeName = DEFAULT_THEME,
  themeName = DEFAULT_THEME,
  onPreviewChange,
  onSave,
  variant = "artist",
}) {
  const isHostProfile = variant === "host";
  const isFanProfile = variant === "fan";
  const isArtistProfile = !isHostProfile && !isFanProfile;
  const normalizePersonalTheme = isHostProfile ? normalizeHostThemeId : normalizeThemeId;
  const defaultPersonalTheme = isHostProfile ? DEFAULT_HOST_THEME : DEFAULT_THEME;
  const [fanTheme, setFanTheme] = useState(normalizePersonalTheme(themeName || defaultPersonalTheme));
  const [studioTheme, setStudioTheme] = useState(studioThemeName || DEFAULT_THEME);
  const [saving, setSaving] = useState(false);
  const themeGroups = groupThemeOptionsForVariant(isHostProfile ? "host" : isFanProfile ? "fan" : "artist");
  const allThemes = [
    ...(themeGroups.accessible || []),
    ...(themeGroups.hostAccessible || []),
    ...(themeGroups.platform || []),
    ...(themeGroups.tribute || []),
    ...(themeGroups.host || []),
  ];

  function renderThemeRows(themes, { name, checkedId, onChange, onPreview, previewTarget }) {
    return themes.map(theme => (
      <ThemePickerRow
        key={`${previewTarget}-${theme.id}`}
        activePreviewTarget={activePreviewTarget}
        checked={checkedId === theme.id}
        name={name}
        onChange={() => onChange(theme.id)}
        onPreview={() => onPreview(theme.id)}
        previewTarget={previewTarget}
        theme={theme}
        value={theme.id}
      />
    ));
  }

  useEffect(() => {
    setFanTheme(normalizePersonalTheme(themeName || defaultPersonalTheme));
  }, [themeName, defaultPersonalTheme]);

  useEffect(() => {
    setStudioTheme(studioThemeName || DEFAULT_THEME);
  }, [studioThemeName]);

  function emitPreview(nextFanTheme, nextStudioTheme, target) {
    onPreviewChange?.({
      fanTheme: normalizePersonalTheme(nextFanTheme),
      studioTheme: normalizeThemeId(nextStudioTheme),
      target,
    });
  }

  function previewFanTheme(nextTheme) {
    setFanTheme(nextTheme);
    emitPreview(nextTheme, studioTheme, "fan");
  }

  function previewStudioTheme(nextTheme) {
    setStudioTheme(nextTheme);
    emitPreview(fanTheme, nextTheme, "studio");
  }

  function resetPreview() {
    setFanTheme(normalizePersonalTheme(themeName || defaultPersonalTheme));
    setStudioTheme(studioThemeName || DEFAULT_THEME);
    onPreviewChange?.(null);
  }

  const previewActive = Boolean(activePreviewTarget);
  const previewThemeId = activePreviewTarget === "studio" ? studioTheme : fanTheme;
  const previewLabel = activePreviewTarget === "studio"
    ? "Studio theme (only you)"
    : (isHostProfile ? "Personal theme" : isFanProfile ? "Profile theme" : "Public page theme");
  const previewAudienceNote = isArtistProfile
    ? (activePreviewTarget === "studio"
      ? "Only you see this while editing your page, uploading, or in studio preview. Fans never see it on your public link."
      : "This is what fans and visitors see when they open your public artist page.")
    : "";
  const previewSampleTitle = isHostProfile
    ? "Spaces dashboard"
    : isArtistProfile
      ? (activePreviewTarget === "studio" ? "Your studio view" : "What fans see on your page")
      : "Sample card";
  const hasUnsavedPreview = previewActive && (
    activePreviewTarget === "studio"
      ? normalizeThemeId(studioTheme) !== normalizeThemeId(studioThemeName)
      : normalizePersonalTheme(fanTheme) !== normalizePersonalTheme(themeName)
  );

  async function handleSubmit(event) {
    event.preventDefault();
    setSaving(true);
    try {
      if (isFanProfile || isHostProfile) {
        await onSave({ theme_name: fanTheme });
      } else {
        await onSave({ theme_name: fanTheme, studio_theme_name: studioTheme });
      }
      onPreviewChange?.(null);
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="feature-card artist-theme-settings">
      <p className="eyebrow">{isHostProfile ? "Personal look" : "Page look"}</p>
      <h3>{isHostProfile ? "My theme" : isFanProfile ? "Profile themes" : "Public page & studio themes"}</h3>
      <p className="muted">
        {isHostProfile
          ? "Pick a palette for your Spaces dashboard and account screens. Artists booking your rooms never see this — it is only for you."
          : isFanProfile
            ? "Preview a theme on your profile page, then save when it feels right."
            : "Choose two themes: one for your public artist page that fans see, and one for your private studio view that only you see while editing."}
      </p>

      {previewActive && (
        <ThemePreviewPanel
          label={previewLabel}
          audienceNote={previewAudienceNote}
          sampleTitle={previewSampleTitle}
          themeId={previewThemeId}
        />
      )}

      <form className="settings-form" onSubmit={handleSubmit}>
        {isArtistProfile && (
          <div className="theme-picker-section-head">
            <h4>Public page theme — fans see this</h4>
            <p className="muted">
              The theme you pick below is shown to everyone who visits your artist page from your public link.
            </p>
          </div>
        )}

        {themeGroups.hostAccessible?.length > 0 && (
          <fieldset className="theme-picker-grid">
            <legend>Colour-blind friendly</legend>
            {renderThemeRows(themeGroups.hostAccessible, {
              name: "theme_name",
              checkedId: fanTheme,
              onChange: setFanTheme,
              onPreview: previewFanTheme,
              previewTarget: "fan",
            })}
          </fieldset>
        )}

        {themeGroups.host?.length > 0 && (
          <fieldset className="theme-picker-grid">
            <legend>{isHostProfile ? "Personal themes" : "Venue atmospheres"}</legend>
            {renderThemeRows(themeGroups.host, {
              name: "theme_name",
              checkedId: fanTheme,
              onChange: setFanTheme,
              onPreview: previewFanTheme,
              previewTarget: "fan",
            })}
          </fieldset>
        )}

        {themeGroups.accessible?.length > 0 && (
          <fieldset className="theme-picker-grid">
            <legend>
              {isArtistProfile ? "Accessible — shown to fans" : isFanProfile ? "Accessible profile themes" : "Accessible fan page themes"}
            </legend>
            {renderThemeRows(themeGroups.accessible, {
              name: "theme_name",
              checkedId: fanTheme,
              onChange: setFanTheme,
              onPreview: previewFanTheme,
              previewTarget: "fan",
            })}
          </fieldset>
        )}

        {themeGroups.platform?.length > 0 && (
          <fieldset className="theme-picker-grid">
            <legend>
              {isArtistProfile ? "Platform palettes — shown to fans" : isFanProfile ? "Platform themes" : "Platform fan page themes"}
            </legend>
            {renderThemeRows(themeGroups.platform, {
              name: "theme_name",
              checkedId: fanTheme,
              onChange: setFanTheme,
              onPreview: previewFanTheme,
              previewTarget: "fan",
            })}
          </fieldset>
        )}

        {themeGroups.tribute?.length > 0 && (
          <fieldset className="theme-picker-grid">
            <legend>{isArtistProfile ? "Artist tributes — shown to fans" : "Artist tributes"}</legend>
            {renderThemeRows(themeGroups.tribute, {
              name: "theme_name",
              checkedId: fanTheme,
              onChange: setFanTheme,
              onPreview: previewFanTheme,
              previewTarget: "fan",
            })}
          </fieldset>
        )}

        {isArtistProfile && (
          <>
            <div className="theme-picker-section-head theme-picker-section-head--studio">
              <h4>Studio theme — only visible to you</h4>
              <p className="muted">
                This palette is for your private studio: page settings, uploads, and when you preview your page as yourself. Fans never see it on your public artist page.
              </p>
            </div>
            <fieldset className="theme-picker-grid">
              <legend>Studio palettes — private to you</legend>
              {renderThemeRows(allThemes, {
                name: "studio_theme_name",
                checkedId: studioTheme,
                onChange: setStudioTheme,
                onPreview: previewStudioTheme,
                previewTarget: "studio",
              })}
            </fieldset>
          </>
        )}

        <p className="form-hint">
          {isHostProfile
            ? `Saved theme: ${getThemeOption(normalizeHostThemeId(themeName)).label}. Selected: ${getThemeOption(normalizeHostThemeId(fanTheme)).label}.`
            : isFanProfile
              ? `Saved theme: ${getThemeOption(themeName).label}. Selected: ${getThemeOption(fanTheme).label}.`
              : `Fans see ${getThemeOption(fanTheme).label} on your public page (saved: ${getThemeOption(themeName).label}). Studio — only you: ${getThemeOption(studioTheme).label} (saved: ${getThemeOption(studioThemeName).label}).`}
        </p>

        <div className="theme-picker-actions">
          {hasUnsavedPreview && (
            <button className="secondary compact" type="button" onClick={resetPreview}>
              Reset preview
            </button>
          )}
          <button className="primary compact" type="submit" disabled={saving}>
            {saving ? "Saving…" : (isHostProfile ? "Save theme" : "Save themes")}
          </button>
        </div>
      </form>
    </section>
  );
}
