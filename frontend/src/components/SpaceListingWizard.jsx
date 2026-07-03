import React, { useState } from "react";
import { SpaceListingAvailabilityPicker } from "./SpaceListingAvailabilityPicker.jsx";

const STEPS = [
  { id: "basics", label: "Room basics", intro: "Start with the room name and how artists should picture the space." },
  { id: "deal", label: "Deal & booking", intro: "Set how you split the door and whether artists book instantly or by request." },
  { id: "photos", label: "Photos", intro: "Stage and audience shots help bands decide if the room fits their show." },
  { id: "availability", label: "Open dates", intro: "Add at least one open date so artists can request a slot." },
  { id: "review", label: "Review", intro: "Check the summary, then save to publish on your host dashboard." },
];

export function SpaceListingWizard({
  defaultCity = "",
  photoTypeLabels = {},
  spaceAvailabilitySlots,
  onAvailabilityChange,
  spacePhotoRows,
  onAddPhoto,
  onUpdatePhoto,
  onRemovePhoto,
  onClose,
  onSubmit,
}) {
  const [stepIndex, setStepIndex] = useState(0);
  const step = STEPS[stepIndex];
  const isFirst = stepIndex === 0;
  const isLast = stepIndex === STEPS.length - 1;

  function goNext(event) {
    event.preventDefault();
    const form = event.currentTarget.closest("form");
    if (!form) return;

    if (step.id === "basics") {
      for (const name of ["name", "city", "address", "capacity", "description"]) {
        const field = form.elements[name];
        if (field && !field.checkValidity()) {
          field.reportValidity();
          return;
        }
      }
    }

    if (step.id === "availability" && spaceAvailabilitySlots.length === 0) {
      form.querySelector("[data-wizard-error='availability']")?.focus();
      return;
    }

    setStepIndex(index => Math.min(index + 1, STEPS.length - 1));
  }

  function goBack(event) {
    event.preventDefault();
    setStepIndex(index => Math.max(index - 1, 0));
  }

  return (
    <div className="modal-backdrop" role="presentation" onClick={onClose}>
      <section
        className="support-sheet space-listing-sheet space-listing-wizard"
        role="dialog"
        aria-modal="true"
        aria-labelledby="space-listing-title"
        onClick={event => event.stopPropagation()}
      >
        <button className="sheet-close" type="button" onClick={onClose} aria-label="Close space listing form">
          ×
        </button>

        <nav className="wizard-steps" aria-label="Room setup steps">
          {STEPS.map((item, index) => (
            <span
              key={item.id}
              className={index === stepIndex ? "wizard-step active" : index < stepIndex ? "wizard-step done" : "wizard-step"}
            >
              {index + 1}. {item.label}
            </span>
          ))}
        </nav>

        <form className="auth-form space-panel space-listing-form" onSubmit={onSubmit}>
          <h2 id="space-listing-title">List your first room</h2>
          <p className="muted wizard-step-intro">{STEPS[stepIndex].intro}</p>

          <div className={step.id === "basics" ? "wizard-panel" : "wizard-panel wizard-panel--hidden"} aria-hidden={step.id !== "basics"}>
            <div className="two-column-form">
              <input name="name" placeholder="Room name e.g. Back Bar Stage" required aria-label="Room name" />
              <input name="city" placeholder="City" defaultValue={defaultCity} required aria-label="City" />
              <input name="address" placeholder="Street address" required aria-label="Address" className="full-span" />
              <input name="capacity" type="number" min="1" placeholder="Capacity" defaultValue="40" required aria-label="Capacity" />
              <input name="tags" placeholder="Tags, comma separated e.g. live music, PA provided" aria-label="Tags" />
            </div>
            <textarea
              name="description"
              placeholder="Describe the room, sound limits, audience fit, and load-in access"
              required
              aria-label="Room description"
            />
            <p className="form-hint muted">Tip: mention backline, curfew, and whether you run a PA or expect bands to bring gear.</p>
          </div>

          <div className={step.id === "deal" ? "wizard-panel" : "wizard-panel wizard-panel--hidden"} aria-hidden={step.id !== "deal"}>
            <div className="two-column-form">
              <select name="split_type" defaultValue="door_percent" aria-label="Split type">
                <option value="door_percent">Door percent split</option>
                <option value="flat_fee">Flat fee</option>
                <option value="fb_only">Food & beverage only</option>
              </select>
              <input name="host_cut_percent" type="number" min="0" max="100" defaultValue="20" aria-label="Host cut percent" />
              <input name="drink_minimum" placeholder="Drink minimum e.g. 1 drink per person" aria-label="Drink minimum" />
              <input name="last_call" placeholder="Last call e.g. 11:30pm" aria-label="Last call" />
              <select name="booking_mode" defaultValue="request" aria-label="Booking mode">
                <option value="request">Request to book</option>
                <option value="instant_book">Instant book</option>
              </select>
              <select name="status" defaultValue="live" aria-label="Listing status">
                <option value="live">Live</option>
                <option value="draft">Draft</option>
              </select>
              <input name="min_local_supporters" type="number" min="0" placeholder="Min local supporters" defaultValue="0" aria-label="Minimum local supporters" />
            </div>
            <p className="form-hint muted full-span">
              Min local supporters: how many subscribers an artist needs in your city before requesting. Use 0 to welcome any artist.
            </p>
            <textarea name="kitchen_notes" placeholder="Kitchen / bar notes (optional)" aria-label="Kitchen notes" />
            <label className="check-row"><input name="bar_open" type="checkbox" defaultChecked /> Bar open during shows</label>
            <label className="check-row"><input name="kitchen_open" type="checkbox" /> Kitchen open during shows</label>
          </div>

          <div className={step.id === "photos" ? "wizard-panel space-photo-upload-block" : "wizard-panel wizard-panel--hidden space-photo-upload-block"} aria-hidden={step.id !== "photos"}>
            <div className="section-head compact">
              <div>
                <p className="eyebrow">Venue photos</p>
                <h4>Show bands where to set up and how the room fits an audience</h4>
              </div>
              <button className="secondary compact" type="button" onClick={onAddPhoto} disabled={spacePhotoRows.length >= 8}>
                Add photo
              </button>
            </div>
            <p className="muted form-hint">Upload a stage shot and an audience view at minimum. Up to 8 photos.</p>
            {spacePhotoRows.map(row => (
              <div className="space-photo-row" key={row.id}>
                <select
                  value={row.photo_type}
                  onChange={event => onUpdatePhoto(row.id, "photo_type", event.target.value)}
                  aria-label="Photo type"
                >
                  {Object.entries(photoTypeLabels).map(([value, label]) => (
                    <option value={value} key={value}>{label}</option>
                  ))}
                </select>
                <input type="file" accept="image/jpeg,image/png,image/webp" data-photo-row={row.id} aria-label="Photo file" />
                <input
                  type="text"
                  placeholder="Caption (optional)"
                  value={row.caption}
                  onChange={event => onUpdatePhoto(row.id, "caption", event.target.value)}
                  aria-label="Photo caption"
                />
                {spacePhotoRows.length > 1 && (
                  <button className="secondary compact" type="button" onClick={() => onRemovePhoto(row.id)}>Remove</button>
                )}
              </div>
            ))}
          </div>

          <div className={step.id === "availability" ? "wizard-panel" : "wizard-panel wizard-panel--hidden"} aria-hidden={step.id !== "availability"}>
            <label>Open dates</label>
            <SpaceListingAvailabilityPicker slots={spaceAvailabilitySlots} onChange={onAvailabilityChange} />
            <p className="form-hint muted">Add recurring or one-off dates when the room is available for gigs.</p>
            {spaceAvailabilitySlots.length === 0 && (
              <p className="notice-inline" data-wizard-error="availability" tabIndex={-1}>
                Add at least one open date before continuing.
              </p>
            )}
          </div>

          <div className={step.id === "review" ? "wizard-panel wizard-review" : "wizard-panel wizard-panel--hidden wizard-review"} aria-hidden={step.id !== "review"}>
            <p className="form-hint">Submitting saves your listing immediately. You can edit photos and availability later from Spaces.</p>
            <ul className="early-access-list">
              <li>Room name, city, address, and description from step 1</li>
              <li>Door split, booking mode, and bar details from step 2</li>
              <li>{spacePhotoRows.length} photo slot{spacePhotoRows.length === 1 ? "" : "s"} ready to upload</li>
              <li>{spaceAvailabilitySlots.length} availability row{spaceAvailabilitySlots.length === 1 ? "" : "s"} added</li>
            </ul>
          </div>

          <div className="sheet-actions wizard-actions">
            <button className="secondary" type="button" onClick={onClose}>Cancel</button>
            {!isFirst && (
              <button className="secondary" type="button" onClick={goBack}>Back</button>
            )}
            {isLast ? (
              <button className="primary" type="submit">Save listing</button>
            ) : (
              <button className="primary" type="button" onClick={goNext}>Continue</button>
            )}
          </div>
        </form>
      </section>
    </div>
  );
}
