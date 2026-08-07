import React, { useState } from "react";
import { CampaignWizard } from "./CampaignWizard.jsx";

const STATUS_LABELS = {
  draft: "Draft",
  ready: "Ready",
  launched: "Launched",
  paused: "Paused",
  completed: "Completed",
};

const GOAL_LABELS = {
  more_streams: "More streams",
  new_followers: "New followers",
  email_signups: "Email signups",
  merch_sales: "Merch sales",
  ticket_sales: "Ticket sales",
  video_views: "Video views",
};

const NETWORK_LABELS = {
  meta: "Meta",
  google: "Google",
  youtube: "YouTube",
  tiktok: "TikTok",
  spotify: "Spotify",
  reddit: "Reddit",
  pinterest: "Pinterest",
  snapchat: "Snapchat",
  x: "X",
};

function formatMoney(value) {
  const amount = Number(value || 0);
  return Number.isFinite(amount) ? amount.toFixed(2) : "0.00";
}

function formatNumber(value) {
  const amount = Number(value || 0);
  return Number.isFinite(amount) ? amount.toLocaleString() : "0";
}

function CampaignMetrics({ metrics }) {
  if (!metrics) return null;

  return (
    <div className="metrics-grid" aria-label="Campaign metrics">
      <div><span className="muted">Impressions</span><strong>{formatNumber(metrics.impressions)}</strong></div>
      <div><span className="muted">Clicks</span><strong>{formatNumber(metrics.clicks)}</strong></div>
      <div><span className="muted">Follows</span><strong>{formatNumber(metrics.follows)}</strong></div>
      <div><span className="muted">Subscribers</span><strong>{formatNumber(metrics.subscribers)}</strong></div>
      <div><span className="muted">Purchases</span><strong>{formatNumber(metrics.purchases)}</strong></div>
      <div><span className="muted">Revenue</span><strong>${formatMoney(metrics.revenue)}</strong></div>
      <div><span className="muted">Fan value</span><strong>${formatMoney(metrics.fan_value)}</strong></div>
    </div>
  );
}

export function AdsManagerPage({
  campaigns = [],
  artistPageUrl = "",
  busy = false,
  onCreateCampaign,
  onUpdateCampaign,
  onDeleteCampaign,
  onUpdateStatus,
  onGoToPromote,
}) {
  const [showWizard, setShowWizard] = useState(false);
  const [editingCampaign, setEditingCampaign] = useState(null);

  function openCreateWizard() {
    setEditingCampaign(null);
    setShowWizard(true);
  }

  function openEditWizard(campaign) {
    setEditingCampaign(campaign);
    setShowWizard(true);
  }

  function closeWizard() {
    setShowWizard(false);
    setEditingCampaign(null);
  }

  async function handleSubmit(formData, campaignId) {
    if (campaignId) {
      await onUpdateCampaign(campaignId, formData);
    } else {
      await onCreateCampaign(formData);
    }
    closeWizard();
  }

  return (
    <section className="ads-manager-page">
      <header className="section-head tab-title-row ads-manager-head">
        <div>
          <p className="eyebrow">Artist Growth</p>
          <h2>Ads Manager</h2>
          <p className="muted">
            Plan ads for Instagram, YouTube, and more without opening a complicated ad manager.
          </p>
        </div>
        <button className="primary compact" type="button" onClick={openCreateWizard} disabled={busy}>
          New campaign
        </button>
      </header>

      <section className="feature-card ads-manager-note">
        <p className="muted">
          This planner helps you map external ad campaigns step by step. IndieFund never runs external ads for you
          and never adds tracking pixels — you launch campaigns on the ad platforms yourself and log results here.
          For in-platform Discovery ads on IndieFund, use{" "}
          <button className="link-button" type="button" onClick={onGoToPromote}>Promote</button>.
        </p>
      </section>

      {!campaigns.length ? (
        <section className="feature-card ads-manager-empty">
          <h3>Plan your first growth campaign</h3>
          <p className="muted">
            Start with what you are promoting, who should see it, and where fans should land after they click.
          </p>
          <button className="primary" type="button" onClick={openCreateWizard} disabled={busy}>
            Start campaign wizard
          </button>
        </section>
      ) : (
        <div className="ads-manager-list">
          {campaigns.map(campaign => (
            <article className="feature-card campaign-card" key={campaign.id}>
              <div className="campaign-card-head">
                <div>
                  <h3>{campaign.title}</h3>
                  <p className="muted">
                    {GOAL_LABELS[campaign.goal] || campaign.goal}
                    {" · "}
                    ${formatMoney(campaign.budget_daily)}/day for {campaign.duration_days} days
                  </p>
                </div>
                <span className={`status-pill status-pill--${campaign.status}`}>
                  {STATUS_LABELS[campaign.status] || campaign.status}
                </span>
              </div>

              <div className="campaign-network-row">
                {(campaign.ad_networks || []).map(network => (
                  <span className="network-chip active" key={`${campaign.id}-${network}`}>
                    {NETWORK_LABELS[network] || network}
                  </span>
                ))}
              </div>

              <CampaignMetrics metrics={campaign.metrics} />
              {campaign.metrics?.placeholder && (
                <p className="muted form-hint">Preview data — real ad platform connections are coming soon.</p>
              )}

              <div className="campaign-card-actions">
                {(campaign.status === "draft" || campaign.status === "ready") && (
                  <button className="secondary compact" type="button" onClick={() => openEditWizard(campaign)} disabled={busy}>
                    Edit
                  </button>
                )}
                {campaign.status === "draft" && (
                  <button className="secondary compact" type="button" onClick={() => onUpdateStatus(campaign.id, "ready")} disabled={busy}>
                    Mark ready
                  </button>
                )}
                {campaign.status === "ready" && (
                  <button className="secondary compact" type="button" onClick={() => onUpdateStatus(campaign.id, "launched")} disabled={busy}>
                    Mark launched
                  </button>
                )}
                {campaign.status === "launched" && (
                  <button className="secondary compact" type="button" onClick={() => onUpdateStatus(campaign.id, "paused")} disabled={busy}>
                    Pause
                  </button>
                )}
                {campaign.status === "paused" && (
                  <button className="secondary compact" type="button" onClick={() => onUpdateStatus(campaign.id, "launched")} disabled={busy}>
                    Resume
                  </button>
                )}
                <button className="secondary compact" type="button" onClick={() => onDeleteCampaign(campaign.id)} disabled={busy}>
                  Delete
                </button>
              </div>
            </article>
          ))}
        </div>
      )}

      {showWizard && (
        <CampaignWizard
          initialCampaign={editingCampaign}
          artistPageUrl={artistPageUrl}
          busy={busy}
          onClose={closeWizard}
          onSubmit={handleSubmit}
        />
      )}
    </section>
  );
}
