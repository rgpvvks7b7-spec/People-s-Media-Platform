import React, { useEffect, useMemo, useState } from "react";
import { formatAvailabilityWindows } from "./SpaceAvailabilityEditor.jsx";
import {
  clampTime,
  defaultEndTime,
  getStructuredWindows,
  isDateBookable,
  windowForDate,
} from "../lib/spaceAvailability.js";

const WEEKDAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
const SERIES_MAX_DATES = 12;

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

function combineDateTime(dateValue, timeValue) {
  if (!dateValue || !timeValue) return "";
  return `${dateValue}T${timeValue}`;
}

function formatDisplayDate(dateValue) {
  const date = parseInputDate(dateValue);
  if (!date) return "Pick a host date";
  return date.toLocaleDateString(undefined, {
    weekday: "short",
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

export function SpaceBookingDateFields({ availableWindows = [], onValuesChange }) {
  const structuredWindows = useMemo(
    () => getStructuredWindows(availableWindows),
    [availableWindows],
  );
  const today = new Date();
  const [viewMonth, setViewMonth] = useState(() => new Date(today.getFullYear(), today.getMonth(), 1));
  const [selectedDates, setSelectedDates] = useState([]);
  const [startTime, setStartTime] = useState("");
  const [endTime, setEndTime] = useState("");
  const [seriesMode, setSeriesMode] = useState(false);

  const primaryDate = selectedDates[0] || "";
  const activeWindow = primaryDate
    ? windowForDate(parseInputDate(primaryDate), availableWindows)
    : null;

  const dates = useMemo(() => {
    if (!startTime || !endTime || !selectedDates.length) return [];
    return selectedDates
      .slice()
      .sort()
      .map(dateValue => ({
        starts_at: combineDateTime(dateValue, startTime),
        ends_at: combineDateTime(dateValue, endTime),
      }));
  }, [selectedDates, startTime, endTime]);

  const startsAt = dates[0]?.starts_at || "";
  const endsAt = dates[0]?.ends_at || "";

  useEffect(() => {
    onValuesChange?.({
      starts_at: startsAt,
      ends_at: endsAt,
      dates,
      series_mode: seriesMode,
      hasStartDate: Boolean(selectedDates.length && startTime),
      hasEndDate: Boolean(selectedDates.length && endTime),
    });
  }, [startsAt, endsAt, dates, seriesMode, selectedDates, startTime, endTime, onValuesChange]);

  const monthLabel = viewMonth.toLocaleDateString(undefined, { month: "long", year: "numeric" });

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

  function applyWindowTimes(date) {
    const window = windowForDate(date, availableWindows);
    const nextStart = window.start;
    const nextEnd = defaultEndTime(nextStart, window);
    setStartTime(nextStart);
    setEndTime(nextEnd);
  }

  function pickDay(date) {
    if (!isDateBookable(date, availableWindows)) return;

    const nextValue = toInputDate(date);

    if (!seriesMode) {
      setSelectedDates([nextValue]);
      applyWindowTimes(date);
      return;
    }

    if (selectedDates.includes(nextValue)) {
      setSelectedDates(selectedDates.filter(value => value !== nextValue));
      return;
    }
    if (selectedDates.length >= SERIES_MAX_DATES) {
      return;
    }
    if (!selectedDates.length) {
      applyWindowTimes(date);
    }
    setSelectedDates([...selectedDates, nextValue].sort());
  }

  function handleSeriesModeChange(enabled) {
    setSeriesMode(enabled);
    if (!enabled && selectedDates.length > 1) {
      setSelectedDates(selectedDates.slice(0, 1));
    }
  }

  function handleStartTimeChange(value) {
    if (!activeWindow) return;
    const nextStart = clampTime(value, activeWindow.start, activeWindow.end);
    setStartTime(nextStart);
    if (endTime && combineDateTime(primaryDate, endTime) <= combineDateTime(primaryDate, nextStart)) {
      setEndTime(defaultEndTime(nextStart, activeWindow));
    }
  }

  function handleEndTimeChange(value) {
    if (!activeWindow) return;
    setEndTime(clampTime(value, startTime || activeWindow.start, activeWindow.end));
  }

  if (structuredWindows.length === 0) {
    return (
      <div className="calendar-item-dates">
        <p className="muted form-hint">This host has not set bookable days and times yet.</p>
      </div>
    );
  }

  return (
    <div className="calendar-item-dates">
      <p className="muted form-hint">
        Host availability: {formatAvailabilityWindows(availableWindows)}
      </p>

      <label className="space-series-toggle">
        <input
          type="checkbox"
          checked={seriesMode}
          onChange={event => handleSeriesModeChange(event.target.checked)}
        />
        Book a series (up to {SERIES_MAX_DATES} dates)
      </label>

      <div className="calendar-date-targets">
        <div className="calendar-date-target is-active">
          <span>{seriesMode ? "Show dates" : "Show date"}</span>
          <strong>
            {selectedDates.length === 0
              ? "Pick a host date"
              : seriesMode
                ? `${selectedDates.length} date${selectedDates.length === 1 ? "" : "s"} selected`
                : formatDisplayDate(primaryDate)}
          </strong>
          {activeWindow && (
            <span className="calendar-window-label">{activeWindow.start}–{activeWindow.end}</span>
          )}
          {seriesMode && selectedDates.length > 0 && (
            <span className="muted form-hint">
              {selectedDates.map(formatDisplayDate).join(" · ")}
            </span>
          )}
        </div>
      </div>

      <div className="calendar-picker" aria-label="Choose an available host date">
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

            const bookable = isDateBookable(date, availableWindows);
            const dateValue = toInputDate(date);
            const isSelected = selectedDates.includes(dateValue);
            const isToday = dateValue === toInputDate(today);

            return (
              <button
                key={dateValue}
                type="button"
                className={[
                  "calendar-day",
                  isToday ? "is-today" : "",
                  isSelected ? "is-start is-end" : "",
                  !bookable ? "is-disabled" : "",
                ].filter(Boolean).join(" ")}
                onClick={() => pickDay(date)}
                disabled={!bookable}
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
              value={startTime}
              min={activeWindow?.start}
              max={activeWindow?.end}
              disabled={!activeWindow}
              onChange={event => handleStartTimeChange(event.target.value)}
            />
          </label>
          <label>
            End time
            <input
              type="time"
              value={endTime}
              min={startTime || activeWindow?.start}
              max={activeWindow?.end}
              disabled={!activeWindow}
              onChange={event => handleEndTimeChange(event.target.value)}
            />
          </label>
        </div>

        <p className="muted form-hint">
          {seriesMode
            ? "Tap multiple highlighted days for a series. The same start and end times apply to every date."
            : "Only highlighted days match the host schedule. Times must stay within their open window."}
        </p>
      </div>
    </div>
  );
}
