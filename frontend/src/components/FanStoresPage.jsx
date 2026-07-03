import React from "react";
import { ArtistNameLink } from "./ArtistNameLink.jsx";

export function FanStoresPage({
  channels = [],
  selectedChannelUsername = "",
  storeTab = "merch",
  onOpenArtistByUsername,
  products = [],
  musicProductTypes = new Set(),
  productTypeLabel,
  isPurchasableProduct,
  isCartableProduct,
  onAddToCart,
  onPurchase,
  onPlayPreview,
  currentTrack,
  isPlaying,
  renderLockedProductPrompt,
}) {
  const supportedUsernames = new Set(channels.map(channel => channel.username));

  const filtered = products.filter(product => {
    if (!supportedUsernames.has(product.artist_username)) return false;
    if (product.product_type === "event_ticket") return false;
    if (selectedChannelUsername && product.artist_username !== selectedChannelUsername) return false;
    const isMusic = musicProductTypes.has(product.product_type);
    return storeTab === "music-store" ? isMusic : !isMusic;
  });

  return (
    <div className="fan-stores-page">
      {channels.length === 0 && (
        <div className="empty-state">
          <h3>Support an artist to unlock their store</h3>
          <p>Stores appear here once you have an active monthly support subscription.</p>
        </div>
      )}

      {channels.length > 0 && filtered.length === 0 && (
        <div className="empty-state">
          <h3>No {storeTab === "music-store" ? "music products" : "merch"} right now</h3>
          <p>
            {selectedChannelUsername
              ? "Try another artist channel or switch store tabs."
              : "Your supported artists have not listed items in this category yet."}
          </p>
        </div>
      )}

      <div className="product-grid fan-stores-grid">
        {filtered.map(product => (
          <article className="product-card" key={product.id}>
            {product.image && <img src={product.image} alt={product.title} />}
            <div>
              <p className="eyebrow">
                {productTypeLabel(product.product_type)} ·{" "}
                <ArtistNameLink
                  username={product.artist_username}
                  label={product.artist_name || product.artist_username}
                  onOpenArtist={onOpenArtistByUsername}
                />
              </p>
              <h3>{product.title}</h3>
              <p>{product.description}</p>
              <strong>${product.price}</strong>
              {isPurchasableProduct(product) && (
                <div className="product-buy-row">
                  {isCartableProduct(product) && (
                    <button className="secondary compact" type="button" onClick={() => onAddToCart(product)}>Add to cart</button>
                  )}
                  <button className="primary compact" type="button" onClick={() => onPurchase(product)}>Buy now</button>
                </div>
              )}
              {product.preview_audio && (
                <button
                  className="secondary compact"
                  type="button"
                  onClick={() => onPlayPreview(product)}
                >
                  {currentTrack?.id === product.id && currentTrack?.is_product && isPlaying ? "Pause preview" : "Play preview"}
                </button>
              )}
              {!product.can_access && renderLockedProductPrompt?.(product)}
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}
