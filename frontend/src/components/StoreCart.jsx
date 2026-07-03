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
}) {
  if (!open) return null;

  const total = cartItems.reduce((sum, item) => sum + Number(item.price || 0), 0);

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
            <div className="store-cart-footer">
              <strong>Total · ${total.toFixed(2)}</strong>
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
