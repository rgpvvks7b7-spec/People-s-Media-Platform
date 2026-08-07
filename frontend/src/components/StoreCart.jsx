import React from "react";
import { ArtistNameLink } from "./ArtistNameLink.jsx";

export function StoreCart({
  cartItems = [],
  currentUser,
  onCheckout,
  onClose,
  onOpenArtist,
  onRemove,
  open,
  promotionWallet,
  applyDiscoveryCredits = true,
  onApplyDiscoveryCreditsChange,
}) {
  const total = cartItems.reduce((sum, item) => sum + Number(item.price || 0), 0);
  const balance = Number(promotionWallet?.balance || 0);
  const maxRedeem = Number(promotionWallet?.max_redeem_per_purchase || 10);
  const creditPreview = applyDiscoveryCredits && balance > 0
    ? Math.min(balance, maxRedeem, total)
    : 0;
  const dueNow = Math.max(0, total - creditPreview);

  if (!open) return null;

  return (
    <div className="modal-backdrop store-cart-backdrop" onClick={onClose}>
      <div className="modal-card store-cart-panel" onClick={event => event.stopPropagation()}>
        <div className="tab-title-row">
          <div>
            <p className="eyebrow">Store cart</p>
            <h3>{cartItems.length} item{cartItems.length === 1 ? "" : "s"}</h3>
          </div>
          <button className="secondary compact" type="button" onClick={onClose}>Close</button>
        </div>

        {!currentUser && (
          <p className="muted">Log in to checkout your cart.</p>
        )}

        {cartItems.length === 0 && (
          <div className="empty-state compact">
            <p>Your cart is empty. Add merch or digital items from artist store tabs.</p>
          </div>
        )}

        {cartItems.length > 0 && (
          <>
            <div className="store-cart-list">
              {cartItems.map(item => (
                <div className="store-cart-row" key={item.id}>
                  <div>
                    <strong>{item.title}</strong>
                    <p className="muted">
                      <ArtistNameLink
                        username={item.artist_username}
                        label={item.stage_name || item.artist_username}
                        onOpenArtist={onOpenArtist}
                      />
                      {" · "}${item.price}
                    </p>
                  </div>
                  <button className="secondary compact" type="button" onClick={() => onRemove(item.id)}>Remove</button>
                </div>
              ))}
            </div>
            {currentUser && balance > 0 && (
              <label className="check-row preference-row">
                <input
                  type="checkbox"
                  checked={applyDiscoveryCredits}
                  onChange={event => onApplyDiscoveryCreditsChange?.(event.target.checked)}
                />
                Apply up to ${Math.min(balance, maxRedeem).toFixed(2)} discovery credits
              </label>
            )}
            <div className="store-cart-footer">
              <div>
                <strong>Total · ${total.toFixed(2)}</strong>
                {creditPreview > 0 && (
                  <p className="muted form-hint">
                    Credits −${creditPreview.toFixed(2)} · Pay ${dueNow.toFixed(2)}
                  </p>
                )}
              </div>
              <button className="primary" type="button" disabled={!currentUser} onClick={onCheckout}>
                Checkout cart
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
