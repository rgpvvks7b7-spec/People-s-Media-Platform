import { getChecklistProgress, getNextChecklistItem } from "../lib/setupChecklist.js";

export function SetupChecklistPanel({
  eyebrow = "Getting started",
  title,
  subtitle,
  items,
  checklistHidden = false,
  onDismiss,
}) {
  const { doneCount, total, complete, percent } = getChecklistProgress(items);
  const nextItem = getNextChecklistItem(items);

  if (complete || !items.length) return null;

  return (
    <>
      {nextItem && (
        <section className="next-best-action" aria-label="Next best action">
          <div>
            <p className="eyebrow">Next best action</p>
            <strong>{nextItem.label}</strong>
            <p className="muted">{nextItem.detail}</p>
          </div>
          <button className="primary compact" type="button" onClick={nextItem.onClick}>
            Do this next
          </button>
        </section>
      )}

      {!checklistHidden && (
        <section className="setup-checklist-panel" aria-label={title}>
          <div className="setup-checklist-panel-head">
            <div>
              <p className="eyebrow">{eyebrow}</p>
              <h3>{title}</h3>
              {subtitle ? <p className="muted">{subtitle}</p> : null}
            </div>
            <div className="setup-checklist-progress" aria-label={`${doneCount} of ${total} steps complete`}>
              <strong>{doneCount}/{total} done</strong>
              <span className="setup-checklist-progress-bar">
                <span style={{ width: `${percent}%` }} />
              </span>
            </div>
            {onDismiss ? (
              <button type="button" className="secondary compact" onClick={onDismiss}>
                Hide checklist
              </button>
            ) : null}
          </div>
          <div className="setup-checklist">
            {items.map(item => (
              <button
                key={item.index}
                type="button"
                className={item.done ? "checklist-item done" : "checklist-item"}
                onClick={item.onClick}
              >
                <span>{item.done ? "✓" : item.index}</span>
                <div>
                  <strong>{item.label}</strong>
                  <small>{item.detail}</small>
                </div>
              </button>
            ))}
          </div>
        </section>
      )}
    </>
  );
}

export function GrowthNextAction({ action }) {
  if (!action) return null;

  return (
    <section className="next-best-action next-best-action--growth" aria-label="Next best action">
      <div>
        <p className="eyebrow">Next best action</p>
        <strong>{action.label}</strong>
        <p className="muted">{action.detail}</p>
      </div>
      <button className="primary compact" type="button" onClick={action.onClick}>
        {action.buttonLabel || "Go"}
      </button>
    </section>
  );
}
