import React, { useState } from "react";

const PRESETS = ["3", "5", "10"];

/**
 * Contextual tip sheet shown at peak fan moments (full listen, check-in, party end).
 */
export function TipPromptSheet({
  open,
  artistName = "this artist",
  contextLabel = "",
  reason = "tip",
  submitting = false,
  error = "",
  onClose,
  onSubmit,
}) {
  const [amount, setAmount] = useState("5");
  const [message, setMessage] = useState("");

  if (!open) return null;

  const titleId = `tip-prompt-title-${reason}`;

  async function handleSubmit(event) {
    event.preventDefault();
    await onSubmit?.({
      amount,
      message: message.trim(),
      is_public: true,
    });
  }

  return (
    <div className="modal-backdrop" role="presentation" onClick={onClose}>
      <form
        className="support-sheet tip-prompt-sheet"
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        onClick={(event) => event.stopPropagation()}
        onSubmit={handleSubmit}
      >
        <button className="sheet-close" type="button" onClick={onClose} aria-label="Close tip prompt">
          ×
        </button>
        <div className="tab-title-row">
          <div>
            <p className="eyebrow">Say thanks</p>
            <h3 id={titleId}>Tip {artistName}</h3>
            <p className="muted">
              {contextLabel || "Tips go 100% to the artist — IndieFund takes $0."}
            </p>
          </div>
        </div>

        <fieldset className="tip-prompt-presets">
          <legend>Quick amounts</legend>
          {PRESETS.map((value) => (
            <button
              key={value}
              className={amount === value ? "secondary compact active" : "secondary compact"}
              type="button"
              aria-pressed={amount === value}
              onClick={() => setAmount(value)}
            >
              ${value}
            </button>
          ))}
        </fieldset>

        <label htmlFor="tip-prompt-amount">Custom amount</label>
        <input
          id="tip-prompt-amount"
          type="number"
          min="1"
          step="0.01"
          value={amount}
          onChange={(event) => setAmount(event.target.value)}
          required
        />

        <label htmlFor="tip-prompt-message">Optional note</label>
        <textarea
          id="tip-prompt-message"
          maxLength={240}
          value={message}
          onChange={(event) => setMessage(event.target.value)}
          placeholder="Leave a short note"
        />

        {error ? <p className="form-error" role="alert">{error}</p> : null}

        <div className="action-grid">
          <button className="primary" type="submit" disabled={submitting}>
            {submitting ? "Sending…" : `Send $${amount || "0"} tip`}
          </button>
          <button className="secondary" type="button" onClick={onClose} disabled={submitting}>
            Not now
          </button>
        </div>
      </form>
    </div>
  );
}
