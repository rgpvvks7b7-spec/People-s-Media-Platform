import React from "react";

export const WEEKDAYS = [
  { key: "mon", label: "Monday" },
  { key: "tue", label: "Tuesday" },
  { key: "wed", label: "Wednesday" },
  { key: "thu", label: "Thursday" },
  { key: "fri", label: "Friday" },
  { key: "sat", label: "Saturday" },
  { key: "sun", label: "Sunday" },
];

function normalizeWindow(entry) {
  if (typeof entry === "string") {
    return { day: "", start: "", end: "", label: entry.trim() };
  }
  if (entry && typeof entry === "object") {
    return {
      day: String(entry.day || "").toLowerCase(),
      start: String(entry.start || "").trim(),
      end: String(entry.end || "").trim(),
      label: "",
    };
  }
  return { day: "", start: "", end: "", label: String(entry || "") };
}

export function windowsToRows(windows = []) {
  const normalized = (windows || []).map(normalizeWindow);
  return WEEKDAYS.map(day => {
    const match = normalized.find(item => item.day === day.key);
    return {
      key: day.key,
      label: day.label,
      enabled: Boolean(match),
      start: match?.start || "18:00",
      end: match?.end || "22:00",
    };
  });
}

export function rowsToWindows(rows = []) {
  return rows
    .filter(row => row.enabled && row.start && row.end)
    .map(row => ({ day: row.key, start: row.start, end: row.end }));
}

function formatAvailabilityDate(dateValue) {
  const [year, month, day] = String(dateValue || "").split("-").map(Number);
  if (!year || !month || !day) return dateValue;
  return new Date(year, month - 1, day).toLocaleDateString(undefined, {
    weekday: "short",
    month: "short",
    day: "numeric",
  });
}

export function formatAvailabilityWindows(windows = []) {
  const dated = (windows || [])
    .filter(item => item && typeof item === "object" && item.date && item.start && item.end)
    .map(item => `${formatAvailabilityDate(item.date)} ${item.start}–${item.end}`);

  if (dated.length > 0) {
    return dated.join(" · ");
  }

  const payload = rowsToWindows(windowsToRows(windows));
  if (payload.length === 0) return "No availability set";
  return payload
    .map(item => {
      const day = WEEKDAYS.find(dayRow => dayRow.key === item.day);
      return `${day?.label || item.day} ${item.start}–${item.end}`;
    })
    .join(" · ");
}

export function SpaceAvailabilityEditor({ rows, windows = [], onChange, readOnly = false }) {
  if (readOnly) {
    const dated = (windows || [])
      .filter(item => item && typeof item === "object" && item.date && item.start && item.end);

    if (dated.length > 0) {
      return (
        <div className="availability-calendar availability-calendar-readonly" aria-label="Venue availability">
          {dated.map(item => (
            <div className="availability-row availability-row-readonly" key={item.date}>
              <span className="availability-day">{formatAvailabilityDate(item.date)}</span>
              <span className="availability-time">{item.start} – {item.end}</span>
            </div>
          ))}
        </div>
      );
    }

    const active = rows.filter(row => row.enabled);
    if (active.length === 0) {
      return <p className="muted form-hint">No booking windows listed yet.</p>;
    }
    return (
      <div className="availability-calendar availability-calendar-readonly" aria-label="Venue availability">
        {active.map(row => (
          <div className="availability-row availability-row-readonly" key={row.key}>
            <span className="availability-day">{row.label}</span>
            <span className="availability-time">{row.start} – {row.end}</span>
          </div>
        ))}
      </div>
    );
  }

  return (
    <div className="availability-calendar" aria-label="Set weekly availability">
      <p className="muted form-hint">Choose the days and hours artists can request. At least one window is required.</p>
      {rows.map(row => (
        <div className="availability-row" key={row.key}>
          <label className="check-row availability-day-toggle">
            <input
              type="checkbox"
              checked={row.enabled}
              onChange={event => onChange(rows.map(item => (
                item.key === row.key ? { ...item, enabled: event.target.checked } : item
              )))}
            />
            <span>{row.label}</span>
          </label>
          <input
            type="time"
            value={row.start}
            disabled={!row.enabled}
            aria-label={`${row.label} start time`}
            onChange={event => onChange(rows.map(item => (
              item.key === row.key ? { ...item, start: event.target.value } : item
            )))}
          />
          <span className="availability-separator">to</span>
          <input
            type="time"
            value={row.end}
            disabled={!row.enabled}
            aria-label={`${row.label} end time`}
            onChange={event => onChange(rows.map(item => (
              item.key === row.key ? { ...item, end: event.target.value } : item
            )))}
          />
        </div>
      ))}
    </div>
  );
}
