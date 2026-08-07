import React, { useEffect, useState } from "react";

const PLANS = [
  { id: "free", label: "Free" },
  { id: "pro", label: "Artist Pro" },
  { id: "studio", label: "Studio" },
];

function money(value) {
  return `$${Number(value || 0).toFixed(2)}`;
}

/**
 * Public artist pricing page with an interactive keep-vs-fee calculator.
 */
export function PricingCalculatorPage({ apiFetch, onNavigate }) {
  const [plan, setPlan] = useState("free");
  const [supportGmv, setSupportGmv] = useState("1000");
  const [tipsGmv, setTipsGmv] = useState("200");
  const [marketplaceGmv, setMarketplaceGmv] = useState("500");
  const [payload, setPayload] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    const params = new URLSearchParams({
      plan,
      support_gmv: supportGmv || "0",
      tips_gmv: tipsGmv || "0",
      marketplace_gmv: marketplaceGmv || "0",
    });
    apiFetch(`/accounts/fee-schedule/?${params.toString()}`)
      .then(res => res.json().then(data => ({ ok: res.ok, data })))
      .then(({ ok, data }) => {
        if (cancelled) return;
        if (!ok) {
          setError(data.error || "Could not load fee schedule.");
          return;
        }
        setError("");
        setPayload(data);
      })
      .catch(() => {
        if (!cancelled) setError("Could not load fee schedule.");
      });
    return () => {
      cancelled = true;
    };
  }, [apiFetch, plan, supportGmv, tipsGmv, marketplaceGmv]);

  const calculator = payload?.calculator;
  const schedule = payload?.schedule;

  return (
    <section className="pricing-page" aria-label="Pricing and fees">
      <p className="eyebrow">For artists</p>
      <h2>Pricing & fee calculator</h2>
      <p className="muted">
        Transparent take rates. Tips are always fee-free. Paid plans buy down the percentage as you grow.
      </p>

      <div className="pricing-plan-toggle" role="tablist" aria-label="Artist plan">
        {PLANS.map(item => (
          <button
            key={item.id}
            type="button"
            role="tab"
            aria-selected={plan === item.id}
            className={plan === item.id ? "secondary compact is-active" : "secondary compact"}
            onClick={() => setPlan(item.id)}
          >
            {item.label}
          </button>
        ))}
      </div>

      {error ? <p className="muted">{error}</p> : null}

      {schedule && (
        <div className="fee-schedule pricing-fee-schedule">
          <h3>{schedule.plan === "free" ? "Free plan rates" : `${schedule.plan} plan rates`}</h3>
          <ul className="fee-schedule-list">
            {schedule.items.map(item => (
              <li key={item.id}>
                <strong>{item.label}</strong>
                <span>IndieFund {item.platform_percent} · You keep {item.you_keep_percent}</span>
              </li>
            ))}
          </ul>
          {schedule.plan_note ? <p className="muted form-hint">{schedule.plan_note}</p> : null}
        </div>
      )}

      <div className="pricing-calculator feature-card">
        <h3>What you keep</h3>
        <p className="muted">Estimate monthly payouts from support, tips, and store sales.</p>
        <div className="pricing-calculator-inputs">
          <label>
            Monthly support GMV
            <input
              type="number"
              min="0"
              step="1"
              value={supportGmv}
              onChange={event => setSupportGmv(event.target.value)}
              aria-label="Monthly support GMV"
            />
          </label>
          <label>
            Tips GMV
            <input
              type="number"
              min="0"
              step="1"
              value={tipsGmv}
              onChange={event => setTipsGmv(event.target.value)}
              aria-label="Tips GMV"
            />
          </label>
          <label>
            Store / merch GMV
            <input
              type="number"
              min="0"
              step="1"
              value={marketplaceGmv}
              onChange={event => setMarketplaceGmv(event.target.value)}
              aria-label="Store merch GMV"
            />
          </label>
        </div>

        {calculator && (
          <div className="pricing-calculator-results" aria-live="polite">
            <p>
              <strong>You keep {money(calculator.you_keep_total)}</strong>
              <span className="muted"> of {money(calculator.gmv_total)} GMV</span>
            </p>
            <p className="muted">
              IndieFund fees {money(calculator.platform_total)}
              {calculator.effective_rate_percent
                ? ` · effective ${calculator.effective_rate_percent}`
                : ""}
            </p>
            <ul className="fee-schedule-list">
              {calculator.lines.map(line => (
                <li key={line.id}>
                  <strong>{line.label}</strong>
                  <span>
                    Keep {money(line.you_keep)} · Fee {money(line.platform_fee)} ({line.platform_percent})
                  </span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>

      <div className="action-grid">
        <button className="primary" type="button" onClick={() => onNavigate?.("profile")}>
          Create artist account
        </button>
        <button className="secondary" type="button" onClick={() => onNavigate?.("faq")}>
          Back to FAQ
        </button>
      </div>
    </section>
  );
}
