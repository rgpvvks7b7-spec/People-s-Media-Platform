import React, { useState } from "react";
import { requestPasskeyAssertion } from "../lib/passkeys.js";

const AI_USAGE_OPTIONS = [
  { value: "human_made", label: "Human-made" },
  { value: "ai_assisted", label: "AI-assisted" },
  { value: "ai_collaborative", label: "AI-collaborative" },
];

export function FinalizeReleasePanel({ release, currentUser, apiFetch, onClose, onSealed, onMessage }) {
  const artistName = currentUser?.display_name || currentUser?.username || "";
  const [rightsOwner, setRightsOwner] = useState(artistName);
  const [aiUsageStatus, setAiUsageStatus] = useState(release?.ai_usage_status || "human_made");
  const [aiTrainingConsent, setAiTrainingConsent] = useState(false);
  const [writerCredits, setWriterCredits] = useState("");
  const [producerCredits, setProducerCredits] = useState("");
  const [originNotes, setOriginNotes] = useState("");
  const [password, setPassword] = useState("");
  const [needPassword, setNeedPassword] = useState(false);
  const [sealing, setSealing] = useState(false);

  if (!release) return null;

  const isVerified = !!currentUser?.is_verified;

  async function handleSeal(event) {
    event.preventDefault();
    if (sealing || !isVerified) return;

    const details = {
      rights_owner: rightsOwner,
      ai_usage_status: aiUsageStatus,
      ai_training_consent: aiTrainingConsent,
      writer_credits: writerCredits,
      producer_credits: producerCredits,
      origin_notes: originNotes,
    };

    setSealing(true);
    try {
      let body;
      const assertion = await requestPasskeyAssertion(apiFetch);
      if (assertion) {
        body = { ...details, approval_method: "passkey", passkey: assertion };
      } else if (password) {
        body = { ...details, approval_method: "password_fallback", password };
      } else {
        setNeedPassword(true);
        onMessage?.("Enter your account password to seal this release, or add a passkey first.");
        return;
      }

      const res = await apiFetch(`/originlock/releases/${release.id}/seal/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (!res.ok) {
        onMessage?.(data.error || "Unable to seal release.");
        if (!assertion) setNeedPassword(true);
        return;
      }
      onMessage?.("Release sealed. Your work is now Origin Locked.");
      onSealed?.(data.origin_lock);
    } finally {
      setSealing(false);
    }
  }

  return (
    <div className="modal-backdrop" role="presentation" onClick={onClose}>
      <section
        className="support-sheet finalize-release-sheet"
        role="dialog"
        aria-modal="true"
        aria-labelledby="finalize-release-title"
        onClick={event => event.stopPropagation()}
      >
        <button className="sheet-close" onClick={onClose} aria-label="Close finalise release">
          ×
        </button>
        <p className="eyebrow">Origin Lock</p>
        <h2 id="finalize-release-title">Finalise Release</h2>
        <p className="muted">
          Your upload is saved but not yet public. Review the details and seal it to publish.
        </p>

        <dl className="finalize-summary">
          <div>
            <dt>File</dt>
            <dd>{release.file_name || release.content_title || "Your upload"}</dd>
          </div>
          <div>
            <dt>Artist</dt>
            <dd>{artistName}</dd>
          </div>
        </dl>

        <form className="finalize-form" onSubmit={handleSeal}>
          <label htmlFor="finalize-rights-owner">Rights owner</label>
          <input
            id="finalize-rights-owner"
            value={rightsOwner}
            onChange={event => setRightsOwner(event.target.value)}
            placeholder="Who owns the rights to this work?"
          />

          <label htmlFor="finalize-ai-usage">AI-use status</label>
          <select
            id="finalize-ai-usage"
            value={aiUsageStatus}
            onChange={event => setAiUsageStatus(event.target.value)}
          >
            {AI_USAGE_OPTIONS.map(option => (
              <option key={option.value} value={option.value}>{option.label}</option>
            ))}
          </select>

          <label className="check-row">
            <input
              type="checkbox"
              checked={aiTrainingConsent}
              onChange={event => setAiTrainingConsent(event.target.checked)}
            />
            Do Not Train: forbid AI training on this work
          </label>

          <label htmlFor="finalize-writer-credits">Writer credits</label>
          <textarea
            id="finalize-writer-credits"
            value={writerCredits}
            onChange={event => setWriterCredits(event.target.value)}
            placeholder="Songwriters, lyricists"
          />

          <label htmlFor="finalize-producer-credits">Producer credits</label>
          <textarea
            id="finalize-producer-credits"
            value={producerCredits}
            onChange={event => setProducerCredits(event.target.value)}
            placeholder="Producers, engineers"
          />

          <label htmlFor="finalize-origin-notes">Origin notes</label>
          <textarea
            id="finalize-origin-notes"
            value={originNotes}
            onChange={event => setOriginNotes(event.target.value)}
            placeholder="Anything else about the origin of this work (optional)"
          />

          {needPassword && (
            <>
              <label htmlFor="finalize-password">Account password</label>
              <input
                id="finalize-password"
                type="password"
                value={password}
                onChange={event => setPassword(event.target.value)}
                placeholder="Confirm it's really you"
                autoComplete="current-password"
              />
            </>
          )}

          <p className="finalize-confirm-text">
            By sealing this release, you confirm this upload is your official work or you have the rights to publish it.
          </p>

          {!isVerified && (
            <p className="finalize-blocked" role="alert">
              Platform verification required before you can seal releases. Your upload stays saved as a draft.
            </p>
          )}

          <div className="action-grid">
            <button className="primary" type="submit" disabled={!isVerified || sealing}>
              {sealing ? "Sealing…" : "Seal Release"}
            </button>
            <button className="secondary" type="button" onClick={onClose}>
              Seal later
            </button>
          </div>
        </form>
      </section>
    </div>
  );
}
