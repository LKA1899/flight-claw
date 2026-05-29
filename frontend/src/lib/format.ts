import { format } from "date-fns";

export function formatDateTime(value?: string | null) {
  if (!value) return "—";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : format(date, "yyyy-MM-dd HH:mm");
}

export function formatDate(value?: string | null) {
  if (!value) return "—";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : format(date, "yyyy-MM-dd");
}

export function formatDuration(seconds?: number | null) {
  if (seconds === undefined || seconds === null) return "—";
  if (seconds < 60) return `${seconds}s`;
  const minutes = Math.floor(seconds / 60);
  const rest = seconds % 60;
  return `${minutes}m ${rest}s`;
}

export function formatPrice(value?: number | null, currency = "¥") {
  if (value === undefined || value === null) return "—";
  return `${currency}${Math.round(value)}`;
}

export function formatMinutes(value?: number | null) {
  if (value === undefined || value === null) return "—";
  const hours = Math.floor(value / 60);
  const minutes = value % 60;
  return hours ? `${hours}h ${minutes}m` : `${minutes}m`;
}
