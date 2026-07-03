import { rowsToWindows, windowsToRows } from "../components/SpaceAvailabilityEditor.jsx";

const JS_DAY_KEYS = ["sun", "mon", "tue", "wed", "thu", "fri", "sat"];

function toInputDate(date) {
  const pad = value => String(value).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
}

function getDateSlots(availableWindows = []) {
  return (availableWindows || [])
    .filter(item => item && typeof item === "object" && item.date && item.start && item.end)
    .map(item => ({ date: item.date, start: item.start, end: item.end, type: "date" }));
}

function getWeeklySlots(availableWindows = []) {
  return rowsToWindows(windowsToRows(availableWindows)).map(item => ({ ...item, type: "weekly" }));
}

export function getStructuredWindows(availableWindows = []) {
  const dated = getDateSlots(availableWindows);
  if (dated.length > 0) return dated;
  return getWeeklySlots(availableWindows);
}

export function jsDayKey(date) {
  return JS_DAY_KEYS[date.getDay()];
}

export function windowForDate(date, availableWindows = []) {
  const dateValue = toInputDate(date);
  const dated = getDateSlots(availableWindows);
  if (dated.length > 0) {
    return dated.find(item => item.date === dateValue) || null;
  }

  const key = jsDayKey(date);
  return getWeeklySlots(availableWindows).find(item => item.day === key) || null;
}

export function isDateBookable(date, availableWindows = []) {
  if (!date) return false;
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  if (date < today) return false;

  const dateValue = toInputDate(date);
  const dated = getDateSlots(availableWindows);
  if (dated.length > 0) {
    return dated.some(item => item.date === dateValue);
  }

  return Boolean(windowForDate(date, availableWindows));
}

export function timeToMinutes(value) {
  const [hours, minutes] = String(value || "0:0").split(":").map(Number);
  return (hours * 60) + (minutes || 0);
}

export function clampTime(value, min, max) {
  const current = timeToMinutes(value);
  const lower = timeToMinutes(min);
  const upper = timeToMinutes(max);
  const clamped = Math.min(Math.max(current, lower), upper);
  const hours = Math.floor(clamped / 60);
  const minutes = clamped % 60;
  return `${String(hours).padStart(2, "0")}:${String(minutes).padStart(2, "0")}`;
}

export function defaultEndTime(startTime, window) {
  const startMinutes = timeToMinutes(startTime);
  const endMinutes = timeToMinutes(window.end);
  const preferred = Math.min(startMinutes + 120, endMinutes);
  const hours = Math.floor(preferred / 60);
  const minutes = preferred % 60;
  return `${String(hours).padStart(2, "0")}:${String(minutes).padStart(2, "0")}`;
}

export function validateBookingWindow({ dateValue, startTime, endTime, availableWindows = [] }) {
  const [year, month, day] = String(dateValue || "").split("-").map(Number);
  if (!year || !month || !day) {
    return "Pick an available date on the host calendar.";
  }

  const date = new Date(year, month - 1, day);
  const window = windowForDate(date, availableWindows);
  if (!window) {
    return "That date is not available. Choose a day the host has open.";
  }

  const startMinutes = timeToMinutes(startTime);
  const endMinutes = timeToMinutes(endTime);
  const windowStart = timeToMinutes(window.start);
  const windowEnd = timeToMinutes(window.end);

  if (startMinutes < windowStart || endMinutes > windowEnd) {
    return `Choose a time within the host window (${window.start}–${window.end}).`;
  }
  if (endMinutes <= startMinutes) {
    return "End time must be after start time.";
  }

  return "";
}
