import { compactParams } from "@/lib/utils";
import type { ApiResponse, ListParams } from "@/types/common";

export const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || "";

const CSRF_COOKIE_KEY = "flight_scan_csrf_token";

function getCookie(name: string): string | null {
  const value = document.cookie
    .split("; ")
    .find((part) => part.startsWith(`${name}=`))
    ?.split("=")[1];
  return value ? decodeURIComponent(value) : null;
}

function handleAuthError(): void {
  const currentPath = window.location.pathname;
  if (currentPath !== "/login") {
    window.location.href = `/login?redirect=${encodeURIComponent(currentPath + window.location.search)}`;
  }
}

function buildUrl(path: string, params?: ListParams | Record<string, unknown>) {
  const url = new URL(path, apiBaseUrl || window.location.origin);
  Object.entries(compactParams(params || {})).forEach(([key, value]) => url.searchParams.set(key, value));
  return apiBaseUrl ? url.toString() : `${url.pathname}${url.search}`;
}

async function request<T>(path: string, init?: RequestInit, params?: ListParams | Record<string, unknown>): Promise<T> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  const method = (init?.method || "GET").toUpperCase();
  if (["POST", "PUT", "PATCH", "DELETE"].includes(method)) {
    const csrfToken = getCookie(CSRF_COOKIE_KEY);
    if (csrfToken) {
      headers["X-CSRF-Token"] = csrfToken;
    }
  }
  const response = await fetch(buildUrl(path, params), {
    headers: { ...headers, ...(init?.headers as Record<string, string> || {}) },
    credentials: "include",
    ...init,
  });
  const contentType = response.headers.get("content-type") || "";
  const payload = contentType.includes("application/json") ? ((await response.json()) as ApiResponse<T> | T) : null;

  if (response.status === 401) {
    handleAuthError();
    throw new Error("未登录或登录已过期");
  }

  if (!response.ok) {
    const message = payload && typeof payload === "object" && "detail" in payload
      ? String(payload.detail)
      : (payload && typeof payload === "object" && "message" in payload
        ? String((payload as unknown as Record<string, unknown>).message)
        : response.statusText);
    throw new Error(message || "请求失败");
  }
  if (payload && typeof payload === "object" && "success" in payload) {
    if (!payload.success) {
      const err = payload as unknown as Record<string, unknown>;
      throw new Error(String(err.message || err.detail || "请求失败"));
    }
    return payload.data as T;
  }
  return payload as T;
}

export function apiGet<T>(path: string, params?: ListParams | Record<string, unknown>) {
  return request<T>(path, { method: "GET" }, params);
}

export function apiPost<T>(path: string, body?: unknown) {
  return request<T>(path, { method: "POST", body: body === undefined ? undefined : JSON.stringify(body) });
}

export function apiPut<T>(path: string, body?: unknown) {
  return request<T>(path, { method: "PUT", body: body === undefined ? undefined : JSON.stringify(body) });
}

export function apiDelete<T>(path: string) {
  return request<T>(path, { method: "DELETE" });
}
