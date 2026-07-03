import React, { useMemo, useState } from "react";

const WEEKDAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

function pad(value) {
  return String(value).padStart(2, "0");
}

function toInputDate(date) {
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
}

function parseInputDate(value) {
  if (!value) return null;
  const [year, month, day] = value.split("-").map(Number);
  if (!year || !month || !day) return null;
  return new Date(year, month - 1, day);
}

function formatDisplayDate(dateValue) {
  const date = parseInputDate(dateValue);
  if (!date) return "Pick a date";
  return date.toLocaleDateString(undefined, {
    weekday: "short",
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

export function slotsToWindows(slots = []) {
  return slots
    .filter(slot => slot.date && slot.start && slot.end)
    .map(({ date, start, end }) => ({ date, start, end }));
}

export function SpaceListingAvailabilityPicker({ slots, onChange }) {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const [viewMonth, setViewMonth] = useState(() => new Date(today.getFullYear(), today.getMonth(), 1));
  const [draftDate, setDraftDate] = useState("");
  const [draftStart, setDraftStart] = useState("19:00");
  const [draftEnd, setDraftEnd] = useState("23:00");

  const monthLabel = viewMonth.toLocaleDateString(undefined, { month: "long", year: "numeric" });
  const slotDates = useMemo(() => new Set(slots.map(slot => slot.date)), [slots]);

  const days = useMemo(() => {
    const year = viewMonth.getFullYear();
    const month = viewMonth.getMonth();
    const firstDay = new Date(year, month, 1);
    const leadingEmpty = firstDay.getDay();
    const daysInMonth = new Date(year, month + 1, 0).getDate();
    const cells = [];

    for (let index = 0; index < leadingEmpty; index += 1) {
      cells.push(null);
    }
    for (let day = 1; day <= daysInMonth; day += 1) {
      cells.push(new Date(year, month, day));
    }

    return cells;
  }, [viewMonth]);

  function shiftMonth(delta) {
    setViewMonth(current => new Date(current.getFullYear(), current.getMonth() + delta, 1));
  }

  function pickDay(date) {
    if (date < today) return;
    setDraftDate(toInputDate(date));
  }

  function addSlot() {
    if (!draftDate || !draftStart || !draftEnd) return;
    if (draftEnd <= draftStart) return;
    if (slots.some(slot => slot.date === draftDate && slot.start === draftStart && slot.end === draftEnd)) {
      return;
    }

    onChange([
      ...slots,
      { id: `${draftDate}-${draftStart}-${draftEnd}-${Date.now()}`, date: draftDate, start: draftStart, end: draftEnd },
    ]);
    setDraftDate("");
  }

  function removeSlot(slotId) {
    onChange(slots.filter(slot => slot.id !== slotId));
  }

  return (
    <div className="calendar-item-dates space-listing-availability">
      <p className="muted form-hint">
        Pick open dates on the calendar, set hours, then add each date artists can request.
      </p>

      <div className="calendar-date-targets">
        <div className={`calendar-date-target ${draftDate ? "is-active" : ""}`}>
          <span>Selected date</span>
          <strong>{formatDisplayDate(draftDate)}</strong>
        </div>
      </div>

      <div className="calendar-picker" aria-label="Choose availability dates">
        <div className="calendar-picker-head">
          <button
            type="button"
            className="secondary compact calendar-nav"
            onClick={() => shiftMonth(-1)}
            aria-label="Previous month"
          >
            ◀
          </button>
          <strong>{monthLabel}</strong>
          <button
            type="button"
            className="secondary compact calendar-nav"
            onClick={() => shiftMonth(1)}
            aria-label="Next month"
          >
            ▶
          </button>
        </div>

        <div className="calendar-picker-weekdays">
          {WEEKDAYS.map(day => (
            <span key={day}>{day}</span>
          ))}
        </div>

        <div className="calendar-picker-grid">
          {days.map((date, index) => {
            if (!date) {
              return <span key={`pad-${index}`} className="calendar-day calendar-day--empty" aria-hidden="true" />;
            }

            const dateValue = toInputDate(date);
            const isPast = date < today;
            const isSelected = draftDate === dateValue;
            const isScheduled = slotDates.has(dateValue);
            const isToday = dateValue === toInputDate(today);

            return (
              <button
                key={dateValue}
                type="button"
                className={[
                  "calendar-day",
                  isToday ? "is-today" : "",
                  isSelected ? "is-start is-end" : "",
                  isScheduled ? "is-scheduled" : "",
                  isPast ? "is-disabled" : "",
                ].filter(Boolean).join(" ")}
                onClick={() => pickDay(date)}
                disabled={isPast}
                aria-label={date.toLocaleDateString(undefined, { weekday: "long", month: "long", day: "numeric", year: "numeric" })}
                aria-pressed={isSelected}
              >
                {date.getDate()}
              </button>
            );
          })}
        </div>

        <div className="calendar-time-row">
          <label>
            Start time
            <input
              type="time"
              value={draftStart}
              onChange={event => setDraftStart(event.target.value)}
            />
          </label>
          <label>
            End time
            <input
              type="time"
              value={draftEnd}
              onChange={event => setDraftEnd(event.target.value)}
            />
          </label>
        </div>

        <button
          className="primary compact"
          type="button"
          onClick={addSlot}
          disabled={!draftDate || !draftStart || !draftEnd || draftEnd <= draftStart}
        >
          Add this date
        </button>
      </div>

      {slots.length > 0 ? (
        <ul className="space-availability-slots" aria-label="Added availability dates">
          {slots.map(slot => (
            <li className="space-availability-slot" key={slot.id}>
              <div>
                <strong>{formatDisplayDate(slot.date)}</strong>
                <span>{slot.start} – {slot.end}</span>
              </div>
              <button className="secondary compact" type="button" onClick={() => removeSlot(slot.id)}>
                Remove
              </button>
            </li>
          ))}
        </ul>
      ) : (
        <p className="muted form-hint">No dates added yet. Add at least one open date before saving.</p>
      )}
    </div>
  );
}
