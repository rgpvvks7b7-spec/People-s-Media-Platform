import React, { useMemo, useState } from "react";
import {
  CAMPAIGN_TYPES,
  getCampaignDefaults,
  getCampaignTypeMeta,
  getStepTip,
} from "../lib/campaignWizardTips.js";

const STEPS = [
  { id: "promote", label: "Promoting", intro: "What are you putting in front of new fans?" },
  { id: "goal", label: "Goal", intro: "Pick the outcome you care about most." },
  { id: "networks", label: "Ad platforms", intro: "Where should your ads show up?" },
  { id: "destination", label: "Destination", intro: "Where should people land after they tap your ad?" },
  { id: "audience", label: "Audience", intro: "Who should see this?" },
  { id: "budget", label: "Budget", intro: "Set a daily budget and how long you want to run." },
  { id: "creative", label: "Creative", intro: "Add the hook and visual that stops the scroll." },
  { id: "review", label: "Review", intro: "Check everything, then save your plan." },
];

function CampaignStepTip({ campaignType, stepId }) {
  const meta = getCampaignTypeMeta(campaignType);
  const tip = getStepTip(campaignType, stepId);
  if (!tip) return null;

  return (
    <aside className="campaign-step-tip" aria-label={`Tip for ${meta.label} campaigns`}>
      <p className="campaign-step-tip-label">
        Tip for <strong>{meta.label}</strong>
        <span className="muted"> · {meta.detail}</span>
      </p>
      <p className="campaign-step-tip-body">{tip}</p>
    </aside>
  );
}

const GOALS = [
  { id: "more_streams", label: "More streams", detail: "Send fans to listen on Spotify or other platforms" },
  { id: "new_followers", label: "New followers", detail: "Grow your social and platform following" },
  { id: "email_signups", label: "Email signups", detail: "Build your mailing list" },
  { id: "merch_sales", label: "Merch sales", detail: "Drive store purchases" },
  { id: "ticket_sales", label: "Ticket sales", detail: "Fill the room for your next show" },
  { id: "video_views", label: "Video views", detail: "Get more eyes on your visual" },
];

const AD_NETWORKS = [
  { id: "meta", label: "Meta", detail: "Instagram & Facebook" },
  { id: "google", label: "Google", detail: "Search & display" },
  { id: "youtube", label: "YouTube", detail: "Video pre-roll & discovery" },
  { id: "tiktok", label: "TikTok", detail: "Short-form video" },
  { id: "spotify", label: "Spotify", detail: "Audio ads & marquee" },
  { id: "reddit", label: "Reddit", detail: "Community targeting" },
  { id: "pinterest", label: "Pinterest", detail: "Visual discovery" },
  { id: "snapchat", label: "Snapchat", detail: "Mobile-first video" },
  { id: "x", label: "X", detail: "Timeline promotion" },
];

const DESTINATION_TYPES = [
  { id: "indiefund_page", label: "IndieFund page", detail: "Your artist hub on IndieFund" },
  { id: "smart_link", label: "Smart link", detail: "Landing page with multiple listen buttons" },
  { id: "streaming_link", label: "Streaming link", detail: "Direct link to Spotify, Apple Music, etc." },
  { id: "store", label: "Store", detail: "Merch or music store page" },
  { id: "signup", label: "Signup page", detail: "Email or fan list capture" },
  { id: "external_url", label: "Other link", detail: "Any URL you control" },
];

function defaultFormValues(initialCampaign = null, artistPageUrl = "") {
  const starterDefaults = getCampaignDefaults("new_song", artistPageUrl);

  if (initialCampaign) {
    return {
      title: initialCampaign.title || "",
      campaign_type: initialCampaign.campaign_type || "new_song",
      goal: initialCampaign.goal || "more_streams",
      ad_networks: initialCampaign.ad_networks || ["meta"],
      destination_type: initialCampaign.destination_type || "smart_link",
      destination_url: initialCampaign.destination_url || "",
      budget_daily: initialCampaign.budget_daily || "10",
      budget_total: initialCampaign.budget_total || "300",
      duration_days: initialCampaign.duration_days || "30",
      audience_description: initialCampaign.audience_description || "",
      similar_artists: (initialCampaign.similar_artists || []).join(", "),
      locations: (initialCampaign.locations || []).join(", "),
      age_min: initialCampaign.age_min ?? "18",
      age_max: initialCampaign.age_max ?? "44",
      creative_headline: initialCampaign.creative_headline || "",
      creative_text: initialCampaign.creative_text || "",
      status: initialCampaign.status || "draft",
    };
  }

  return {
    title: "",
    campaign_type: "new_song",
    goal: starterDefaults.goal,
    ad_networks: ["meta"],
    destination_type: starterDefaults.destination_type,
    destination_url: artistPageUrl,
    budget_daily: "10",
    budget_total: "300",
    duration_days: "30",
    audience_description: "",
    similar_artists: "",
    locations: "United States, Canada, United Kingdom",
    age_min: "18",
    age_max: "44",
    creative_headline: "",
    creative_text: "",
    status: "draft",
  };
}

function labelForOptions(options, value) {
  return options.find(item => item.id === value)?.label || value;
}

export function CampaignWizard({
  initialCampaign = null,
  artistPageUrl = "",
  busy = false,
  onClose,
  onSubmit,
}) {
  const [stepIndex, setStepIndex] = useState(0);
  const [formValues, setFormValues] = useState(() => defaultFormValues(initialCampaign, artistPageUrl));
  const [creativeFile, setCreativeFile] = useState(null);
  const [saveMode, setSaveMode] = useState("draft");

  const step = STEPS[stepIndex];
  const isFirst = stepIndex === 0;
  const isLast = stepIndex === STEPS.length - 1;

  const computedTotal = useMemo(() => {
    const daily = Number(formValues.budget_daily || 0);
    const days = Number(formValues.duration_days || 0);
    if (!Number.isFinite(daily) || !Number.isFinite(days)) return "";
    return (daily * days).toFixed(2);
  }, [formValues.budget_daily, formValues.duration_days]);

  const typeDefaults = useMemo(
    () => getCampaignDefaults(formValues.campaign_type, artistPageUrl),
    [formValues.campaign_type, artistPageUrl],
  );

  function updateField(name, value) {
    setFormValues(current => ({ ...current, [name]: value }));
  }

  function updateCampaignType(campaignType) {
    const defaults = getCampaignDefaults(campaignType, artistPageUrl);
    setFormValues(current => ({
      ...current,
      campaign_type: campaignType,
      goal: defaults.goal,
      destination_type: defaults.destination_type,
      destination_url: campaignType === "artist_page"
        ? artistPageUrl
        : (current.destination_url || artistPageUrl),
    }));
  }

  function toggleNetwork(networkId) {
    setFormValues(current => {
      const selected = new Set(current.ad_networks || []);
      if (selected.has(networkId)) {
        selected.delete(networkId);
      } else {
        selected.add(networkId);
      }
      return { ...current, ad_networks: Array.from(selected) };
    });
  }

  function validateStep(currentStepId) {
    if (currentStepId === "promote" && !formValues.title.trim()) {
      return "Give your campaign a short name.";
    }
    if (currentStepId === "networks" && !(formValues.ad_networks || []).length) {
      return "Choose at least one ad platform.";
    }
    if (currentStepId === "destination" && !formValues.destination_url.trim()) {
      return "Add the link fans should visit.";
    }
    if (currentStepId === "budget") {
      if (Number(formValues.budget_daily) <= 0) return "Daily budget must be greater than zero.";
      if (Number(formValues.duration_days) <= 0) return "Duration must be at least one day.";
    }
    return "";
  }

  function goNext(event) {
    event.preventDefault();
    const error = validateStep(step.id);
    if (error) {
      window.alert(error);
      return;
    }
    setStepIndex(index => Math.min(index + 1, STEPS.length - 1));
  }

  function goBack(event) {
    event.preventDefault();
    setStepIndex(index => Math.max(index - 1, 0));
  }

  function handleSubmit(event) {
    event.preventDefault();
    const error = validateStep("promote") || validateStep("networks") || validateStep("destination") || validateStep("budget");
    if (error) {
      window.alert(error);
      return;
    }

    const formData = new FormData();
    formData.append("title", formValues.title.trim());
    formData.append("campaign_type", formValues.campaign_type);
    formData.append("goal", formValues.goal);
    formData.append("ad_networks", JSON.stringify(formValues.ad_networks || []));
    formData.append("destination_type", formValues.destination_type);
    formData.append("destination_url", formValues.destination_url.trim());
    formData.append("budget_daily", formValues.budget_daily);
    formData.append("budget_total", formValues.budget_total || computedTotal || "0");
    formData.append("duration_days", formValues.duration_days);
    formData.append("audience_description", formValues.audience_description.trim());
    formData.append("similar_artists", JSON.stringify(
      formValues.similar_artists.split(",").map(item => item.trim()).filter(Boolean),
    ));
    formData.append("locations", JSON.stringify(
      formValues.locations.split(",").map(item => item.trim()).filter(Boolean),
    ));
    formData.append("age_min", formValues.age_min);
    formData.append("age_max", formValues.age_max);
    formData.append("creative_headline", formValues.creative_headline.trim());
    formData.append("creative_text", formValues.creative_text.trim());
    formData.append("status", saveMode === "ready" ? "ready" : "draft");
    if (creativeFile) {
      formData.append("creative_file", creativeFile);
    }

    onSubmit(formData, initialCampaign?.id || null);
  }

  return (
    <div className="modal-backdrop" role="presentation" onClick={onClose}>
      <section
        className="support-sheet campaign-wizard-sheet"
        role="dialog"
        aria-modal="true"
        aria-labelledby="campaign-wizard-title"
        onClick={event => event.stopPropagation()}
      >
        <button className="sheet-close" type="button" onClick={onClose} aria-label="Close campaign wizard">
          ×
        </button>

        <nav className="wizard-steps" aria-label="Campaign setup steps">
          {STEPS.map((item, index) => (
            <span
              key={item.id}
              className={index === stepIndex ? "wizard-step active" : index < stepIndex ? "wizard-step done" : "wizard-step"}
            >
              {index + 1}. {item.label}
            </span>
          ))}
        </nav>

        <form className="auth-form campaign-wizard-form" onSubmit={handleSubmit}>
          <h2 id="campaign-wizard-title">{initialCampaign ? "Edit growth campaign" : "Plan a growth campaign"}</h2>
          <p className="muted wizard-step-intro">{step.intro}</p>
          <CampaignStepTip campaignType={formValues.campaign_type} stepId={step.id} />

          <div className={step.id === "promote" ? "wizard-panel" : "wizard-panel wizard-panel--hidden"} aria-hidden={step.id !== "promote"}>
            <label htmlFor="campaign-title">Campaign name</label>
            <input
              id="campaign-title"
              name="title"
              value={formValues.title}
              onChange={event => updateField("title", event.target.value)}
              placeholder={typeDefaults.titlePlaceholder}
              required
            />
            <p className="form-hint muted">Choose what you are putting in front of new fans.</p>
            <div className="campaign-choice-grid" role="radiogroup" aria-label="What are you promoting?">
              {CAMPAIGN_TYPES.map(item => (
                <label key={item.id} className={`campaign-choice-card${formValues.campaign_type === item.id ? " active" : ""}`}>
                  <input
                    type="radio"
                    name="campaign_type"
                    value={item.id}
                    checked={formValues.campaign_type === item.id}
                    onChange={() => updateCampaignType(item.id)}
                  />
                  <strong>{item.label}</strong>
                  <span className="muted">{item.detail}</span>
                </label>
              ))}
            </div>
          </div>

          <div className={step.id === "goal" ? "wizard-panel" : "wizard-panel wizard-panel--hidden"} aria-hidden={step.id !== "goal"}>
            <div className="campaign-choice-grid" role="radiogroup" aria-label="Campaign goal">
              {GOALS.map(item => (
                <label
                  key={item.id}
                  className={`campaign-choice-card${formValues.goal === item.id ? " active" : ""}${typeDefaults.goal === item.id ? " suggested" : ""}`}
                >
                  <input
                    type="radio"
                    name="goal"
                    value={item.id}
                    checked={formValues.goal === item.id}
                    onChange={() => updateField("goal", item.id)}
                  />
                  <strong>{item.label}</strong>
                  {typeDefaults.goal === item.id && <span className="campaign-suggested-tag">Suggested</span>}
                  <span className="muted">{item.detail}</span>
                </label>
              ))}
            </div>
          </div>

          <div className={step.id === "networks" ? "wizard-panel" : "wizard-panel wizard-panel--hidden"} aria-hidden={step.id !== "networks"}>
            <div className="campaign-network-grid" role="group" aria-label="Ad platforms">
              {AD_NETWORKS.map(item => {
                const selected = (formValues.ad_networks || []).includes(item.id);
                return (
                  <button
                    key={item.id}
                    type="button"
                    className={`network-chip${selected ? " active" : ""}`}
                    aria-pressed={selected}
                    onClick={() => toggleNetwork(item.id)}
                  >
                    <strong>{item.label}</strong>
                    <span className="muted">{item.detail}</span>
                  </button>
                );
              })}
            </div>
          </div>

          <div className={step.id === "destination" ? "wizard-panel" : "wizard-panel wizard-panel--hidden"} aria-hidden={step.id !== "destination"}>
            <label htmlFor="destination-type">Destination type</label>
            <select
              id="destination-type"
              name="destination_type"
              value={formValues.destination_type}
              onChange={event => updateField("destination_type", event.target.value)}
            >
              {DESTINATION_TYPES.map(item => (
                <option key={item.id} value={item.id}>{item.label}</option>
              ))}
            </select>
            <label htmlFor="destination-url">Link fans should visit</label>
            <input
              id="destination-url"
              name="destination_url"
              type="url"
              value={formValues.destination_url}
              onChange={event => updateField("destination_url", event.target.value)}
              placeholder="https://"
              required
            />
          </div>

          <div className={step.id === "audience" ? "wizard-panel" : "wizard-panel wizard-panel--hidden"} aria-hidden={step.id !== "audience"}>
            <label htmlFor="audience-description">Describe your ideal fan</label>
            <textarea
              id="audience-description"
              name="audience_description"
              value={formValues.audience_description}
              onChange={event => updateField("audience_description", event.target.value)}
              placeholder={typeDefaults.audiencePlaceholder}
            />
            <label htmlFor="similar-artists">Similar artists</label>
            <input
              id="similar-artists"
              name="similar_artists"
              value={formValues.similar_artists}
              onChange={event => updateField("similar_artists", event.target.value)}
              placeholder="Artist one, Artist two, Artist three"
            />
            <label htmlFor="locations">Locations</label>
            <input
              id="locations"
              name="locations"
              value={formValues.locations}
              onChange={event => updateField("locations", event.target.value)}
              placeholder="United States, Canada, United Kingdom"
            />
            <div className="two-column-form">
              <div>
                <label htmlFor="age-min">Minimum age</label>
                <input
                  id="age-min"
                  name="age_min"
                  type="number"
                  min="13"
                  max="65"
                  value={formValues.age_min}
                  onChange={event => updateField("age_min", event.target.value)}
                />
              </div>
              <div>
                <label htmlFor="age-max">Maximum age</label>
                <input
                  id="age-max"
                  name="age_max"
                  type="number"
                  min="13"
                  max="65"
                  value={formValues.age_max}
                  onChange={event => updateField("age_max", event.target.value)}
                />
              </div>
            </div>
          </div>

          <div className={step.id === "budget" ? "wizard-panel" : "wizard-panel wizard-panel--hidden"} aria-hidden={step.id !== "budget"}>
            <div className="two-column-form">
              <div>
                <label htmlFor="budget-daily">Daily budget (USD)</label>
                <input
                  id="budget-daily"
                  name="budget_daily"
                  type="number"
                  min="1"
                  step="1"
                  value={formValues.budget_daily}
                  onChange={event => updateField("budget_daily", event.target.value)}
                  required
                />
              </div>
              <div>
                <label htmlFor="duration-days">Duration (days)</label>
                <input
                  id="duration-days"
                  name="duration_days"
                  type="number"
                  min="1"
                  step="1"
                  value={formValues.duration_days}
                  onChange={event => updateField("duration_days", event.target.value)}
                  required
                />
              </div>
              <div>
                <label htmlFor="budget-total">Total budget (USD)</label>
                <input
                  id="budget-total"
                  name="budget_total"
                  type="number"
                  min="1"
                  step="1"
                  value={formValues.budget_total}
                  onChange={event => updateField("budget_total", event.target.value)}
                />
              </div>
            </div>
            {computedTotal && (
              <p className="form-hint muted">Suggested total from daily budget: ${computedTotal} over {formValues.duration_days} days.</p>
            )}
          </div>

          <div className={step.id === "creative" ? "wizard-panel" : "wizard-panel wizard-panel--hidden"} aria-hidden={step.id !== "creative"}>
            <label htmlFor="creative-headline">Headline</label>
            <input
              id="creative-headline"
              name="creative_headline"
              value={formValues.creative_headline}
              onChange={event => updateField("creative_headline", event.target.value)}
              placeholder={typeDefaults.creativeHeadlinePlaceholder}
            />
            <label htmlFor="creative-text">Primary text</label>
            <textarea
              id="creative-text"
              name="creative_text"
              value={formValues.creative_text}
              onChange={event => updateField("creative_text", event.target.value)}
              placeholder={typeDefaults.creativeTextPlaceholder}
            />
            <label htmlFor="creative-file">Video or image</label>
            <input
              id="creative-file"
              name="creative_file"
              type="file"
              accept="image/jpeg,image/png,image/webp,video/mp4,video/quicktime"
              onChange={event => setCreativeFile(event.target.files?.[0] || null)}
            />
          </div>

          <div className={step.id === "review" ? "wizard-panel wizard-review" : "wizard-panel wizard-panel--hidden wizard-review"} aria-hidden={step.id !== "review"}>
            <ul className="early-access-list">
              <li><strong>{formValues.title || "Untitled campaign"}</strong> — {labelForOptions(CAMPAIGN_TYPES, formValues.campaign_type)}</li>
              <li>Goal: {labelForOptions(GOALS, formValues.goal)}</li>
              <li>Platforms: {(formValues.ad_networks || []).map(id => labelForOptions(AD_NETWORKS, id)).join(", ") || "None selected"}</li>
              <li>Destination: {labelForOptions(DESTINATION_TYPES, formValues.destination_type)} — {formValues.destination_url || "No link yet"}</li>
              <li>Audience: {formValues.locations || "No locations"} · ages {formValues.age_min}-{formValues.age_max}</li>
              <li>Budget: ${formValues.budget_daily}/day for {formValues.duration_days} days (${formValues.budget_total || computedTotal || "0"} total)</li>
              <li>Creative: {formValues.creative_headline || "No headline yet"}{creativeFile ? ` · ${creativeFile.name}` : ""}</li>
            </ul>
            <p className="form-hint muted">Saving stores your plan inside IndieFund. Real ad platform connections are coming soon.</p>
          </div>

          <div className="sheet-actions wizard-actions">
            <button className="secondary" type="button" onClick={onClose} disabled={busy}>Cancel</button>
            {!isFirst && (
              <button className="secondary" type="button" onClick={goBack} disabled={busy}>Back</button>
            )}
            {isLast ? (
              <>
                <button
                  className="secondary"
                  type="submit"
                  disabled={busy}
                  onClick={() => setSaveMode("draft")}
                >
                  Save draft
                </button>
                <button
                  className="primary"
                  type="submit"
                  disabled={busy}
                  onClick={() => setSaveMode("ready")}
                >
                  Save and mark ready
                </button>
              </>
            ) : (
              <button className="primary" type="button" onClick={goNext} disabled={busy}>Continue</button>
            )}
          </div>
        </form>
      </section>
    </div>
  );
}
