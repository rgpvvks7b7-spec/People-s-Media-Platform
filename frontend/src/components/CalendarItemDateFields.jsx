import React, { useEffect, useMemo, useState } from "react";

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

function sameDay(left, right) {
  return (
    left
    && right
    && left.getFullYear() === right.getFullYear()
    && left.getMonth() === right.getMonth()
    && left.getDate() === right.getDate()
  );
}

function combineDateTime(dateValue, timeValue) {
  if (!dateValue) return "";
  return `${dateValue}T${timeValue || "12:00"}`;
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

export function CalendarItemDateFields({ onValuesChange, endRequired = false }) {
  const today = new Date();
  const [viewMonth, setViewMonth] = useState(() => new Date(today.getFullYear(), today.getMonth(), 1));
  const [activeField, setActiveField] = useState("start");
  const [startDate, setStartDate] = useState("");
  const [startTime, setStartTime] = useState("19:00");
  const [endDate, setEndDate] = useState("");
  const [endTime, setEndTime] = useState("21:00");

  const startsAt = combineDateTime(startDate, startTime);
  const endsAt = endDate ? combineDateTime(endDate, endTime) : "";

  useEffect(() => {
    onValuesChange?.({
      starts_at: startsAt,
      ends_at: endsAt,
      hasStartDate: Boolean(startDate),
      hasEndDate: Boolean(endDate),
    });
  }, [startsAt, endsAt, startDate, endDate, onValuesChange]);

  const monthLabel = viewMonth.toLocaleDateString(undefined, { month: "long", year: "numeric" });
  const startDateObj = parseInputDate(startDate);
  const endDateObj = parseInputDate(endDate);

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
    const nextValue = toInputDate(date);

    if (activeField === "start") {
      setStartDate(nextValue);
      if (endDate && parseInputDate(endDate) < date) {
        setEndDate("");
      } else if (endRequired && !endDate) {
        setEndDate(nextValue);
        setActiveField("end");
      }
      return;
    }

    if (startDate && date < parseInputDate(startDate)) {
      setStartDate(nextValue);
      setEndDate("");
      setActiveField("end");
      return;
    }

    setEndDate(nextValue);
  }

  return (
    <div className="calendar-item-dates">
      <div className="calendar-date-targets">
        <button
          type="button"
          className={`calendar-date-target ${activeField === "start" ? "is-active" : ""}`}
          onClick={() => setActiveField("start")}
        >
          <span>Starts</span>
          <strong>{formatDisplayDate(startDate)}</strong>
        </button>
        <button
          type="button"
          className={`calendar-date-target ${activeField === "end" ? "is-active" : ""}`}
          onClick={() => setActiveField("end")}
        >
          <span>Ends</span>
          <strong>{endDate ? formatDisplayDate(endDate) : (endRequired ? "Pick a date" : "Optional")}</strong>
        </button>
      </div>

      <div className="calendar-picker" aria-label="Choose a date">
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

            const isStart = sameDay(date, startDateObj);
            const isEnd = sameDay(date, endDateObj);
            const isToday = sameDay(date, today);

            return (
              <button
                key={toInputDate(date)}
                type="button"
                className={[
                  "calendar-day",
                  isToday ? "is-today" : "",
                  isStart ? "is-start" : "",
                  isEnd ? "is-end" : "",
                ].filter(Boolean).join(" ")}
                onClick={() => pickDay(date)}
                aria-label={date.toLocaleDateString(undefined, { weekday: "long", month: "long", day: "numeric", year: "numeric" })}
                aria-pressed={isStart || isEnd}
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
              value={startTime}
              onChange={event => setStartTime(event.target.value)}
              onFocus={() => setActiveField("start")}
            />
          </label>
          <label>
            End time
            <input
              type="time"
              value={endTime}
              disabled={!endDate}
              onChange={event => setEndTime(event.target.value)}
              onFocus={() => setActiveField("end")}
            />
          </label>
        </div>

        <p className="muted form-hint">
          {endRequired
            ? "Choose Starts or Ends, pick both days on the calendar, then set your times."
            : "Choose Starts or Ends above, then tap a day. Use the arrows to move between months."}
        </p>
      </div>
    </div>
  );
}
