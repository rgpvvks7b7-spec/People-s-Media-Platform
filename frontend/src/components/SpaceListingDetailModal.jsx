import React, { useCallback, useEffect, useState } from "react";

/**
 * Full-screen space listing view with photo carousel and structured venue details.
 */
export function SpaceListingDetailModal({
  listing,
  onClose,
  splitLabels = {},
  photoTypeLabels = {},
  formatAvailabilityWindows,
  footer = null,
  onToggleFollow = null,
  followBusy = false,
  onCopyPublicLink = null,
}) {
  const photos = listing?.photos || [];
  const [photoIndex, setPhotoIndex] = useState(0);

  useEffect(() => {
    setPhotoIndex(0);
  }, [listing?.id]);

  const goPrev = useCallback(() => {
    if (photos.length <= 1) return;
    setPhotoIndex(index => (index - 1 + photos.length) % photos.length);
  }, [photos.length]);

  const goNext = useCallback(() => {
    if (photos.length <= 1) return;
    setPhotoIndex(index => (index + 1) % photos.length);
  }, [photos.length]);

  useEffect(() => {
    if (!listing) return undefined;

    function onKeyDown(event) {
      if (event.key === "Escape") onClose();
      if (event.key === "ArrowLeft") goPrev();
      if (event.key === "ArrowRight") goNext();
    }

    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [listing, onClose, goPrev, goNext]);

  if (!listing) return null;

  const activePhoto = photos[photoIndex];
  const splitLabel = splitLabels[listing.split_type] || listing.split_type;
  const hostCutLabel = listing.split_type === "door_percent"
    ? `${listing.host_cut_percent}% door`
    : listing.split_type === "flat_fee"
      ? `$${listing.flat_fee_amount} flat fee`
      : "F&B only (no door split)";

  return (
    <div className="modal-backdrop" role="presentation" onClick={onClose}>
      <section
        className="space-detail-sheet"
        role="dialog"
        aria-modal="true"
        aria-labelledby="space-detail-title"
        data-testid="space-detail-modal"
        onClick={event => event.stopPropagation()}
      >
        <button className="sheet-close" type="button" onClick={onClose} aria-label="Close venue details">
          ×
        </button>

        <div className="space-detail-carousel" data-testid="space-detail-carousel">
          {photos.length > 0 ? (
            <>
              <figure className="space-detail-photo">
                <img
                  src={activePhoto.url}
                  alt={activePhoto.caption || activePhoto.photo_type_label || listing.name}
                />
                <figcaption>
                  <strong>{activePhoto.photo_type_label || photoTypeLabels[activePhoto.photo_type] || "Venue photo"}</strong>
                  {activePhoto.caption && <span>{activePhoto.caption}</span>}
                </figcaption>
              </figure>
              {photos.length > 1 && (
                <>
                  <button
                    type="button"
                    className="space-detail-nav space-detail-nav--prev"
                    aria-label="Previous photo"
                    data-testid="space-photo-prev"
                    onClick={goPrev}
                  >
                    ‹
                  </button>
                  <button
                    type="button"
                    className="space-detail-nav space-detail-nav--next"
                    aria-label="Next photo"
                    data-testid="space-photo-next"
                    onClick={goNext}
                  >
                    ›
                  </button>
                  <div className="space-detail-dots" role="tablist" aria-label="Venue photos">
                    {photos.map((photo, index) => (
                      <button
                        key={photo.id}
                        type="button"
                        role="tab"
                        aria-selected={index === photoIndex}
                        aria-label={`Photo ${index + 1} of ${photos.length}`}
                        className={index === photoIndex ? "active" : ""}
                        onClick={() => setPhotoIndex(index)}
                      />
                    ))}
                  </div>
                  <p className="space-detail-photo-count" aria-live="polite">
                    {photoIndex + 1} / {photos.length}
                  </p>
                </>
              )}
            </>
          ) : (
            <div className="space-detail-photo space-detail-photo--empty">
              <p className="muted">No photos uploaded for this venue yet.</p>
            </div>
          )}
        </div>

        <div className="space-detail-body">
          <header className="space-detail-header">
            <p className="eyebrow">{listing.city || "Local room"} · {listing.capacity} capacity</p>
            <h2 id="space-detail-title">{listing.name}</h2>
            <p className="space-detail-subtitle">{listing.host_business_name} · {splitLabel}</p>
            {(onToggleFollow || onCopyPublicLink) && (
              <div className="action-grid space-detail-actions">
                {onToggleFollow && (
                  <button
                    type="button"
                    className={listing.viewer_following ? "secondary supporting" : "secondary"}
                    onClick={onToggleFollow}
                    disabled={followBusy}
                  >
                    {listing.viewer_following ? "Following venue" : "Follow venue"}
                  </button>
                )}
                {onCopyPublicLink && (
                  <button type="button" className="secondary" onClick={onCopyPublicLink}>
                    Copy venue link
                  </button>
                )}
              </div>
            )}
            {typeof listing.follower_count === "number" && listing.follower_count > 0 && (
              <p className="muted">{listing.follower_count} fan{listing.follower_count === 1 ? "" : "s"} following this room</p>
            )}
          </header>

          <p className="space-detail-description">{listing.description || "Flexible room for independent performers."}</p>

          {(listing.tags?.length > 0 || listing.bar_open || listing.kitchen_open) && (
            <div className="post-badges space-detail-badges">
              {listing.tags?.map(tag => <span key={tag}>{tag.replaceAll("_", " ")}</span>)}
              {listing.bar_open && <span>Bar open</span>}
              {listing.kitchen_open && <span>Kitchen open</span>}
            </div>
          )}

          <dl className="space-detail-facts">
            <div>
              <dt>Availability</dt>
              <dd>{formatAvailabilityWindows ? formatAvailabilityWindows(listing.available_windows) : "Contact host"}</dd>
            </div>
            <div>
              <dt>Host deal</dt>
              <dd>{hostCutLabel}</dd>
            </div>
            {listing.address && (
              <div>
                <dt>Address</dt>
                <dd>{listing.address}</dd>
              </div>
            )}
            {listing.drink_minimum && (
              <div>
                <dt>Drink minimum</dt>
                <dd>{listing.drink_minimum}</dd>
              </div>
            )}
            {listing.last_call && (
              <div>
                <dt>Last call</dt>
                <dd>{listing.last_call}</dd>
              </div>
            )}
            {listing.kitchen_notes && (
              <div>
                <dt>Kitchen</dt>
                <dd>{listing.kitchen_notes}</dd>
              </div>
            )}
            {listing.min_local_supporters > 0 && (
              <div>
                <dt>Local draw</dt>
                <dd>Requires {listing.min_local_supporters}+ local supporters in {listing.city}</dd>
              </div>
            )}
            {listing.booking_mode && (
              <div>
                <dt>Booking</dt>
                <dd>{listing.booking_mode === "instant_book" ? "Instant book when requirements are met" : "Request to book"}</dd>
              </div>
            )}
          </dl>

          {footer}
        </div>
      </section>
    </div>
  );
}

/**
 * Compact photo preview for space listing cards.
 */
export function SpaceListingCardPreview({ listing, photoTypeLabels = {} }) {
  const photos = listing?.photos || [];
  if (photos.length === 0) return null;

  const cover = photos[0];
  const label = cover.photo_type_label || photoTypeLabels[cover.photo_type] || "Venue";

  return (
    <div className="space-card-preview" aria-hidden="true">
      <img src={cover.url} alt="" />
      <span className="space-card-preview-label">
        {photos.length > 1 ? `View ${photos.length} photos` : `View ${label}`}
      </span>
    </div>
  );
}
