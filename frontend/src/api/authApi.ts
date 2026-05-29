import { apiGet, apiPost } from "@/lib/api";

export interface CaptchaData {
  captcha_id: string;
  image_base64: string;
}

export interface LoginPayload {
  username: string;
  password: string;
  captcha_id: string;
  captcha_code: string;
}

export interface UserInfo {
  id: number;
  username: string;
  display_name: string | null;
  role: string;
}

export interface LoginResult {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: UserInfo;
}

const TOKEN_KEY = "flight_scan_token";

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

export const authApi = {
  getCaptcha(): Promise<CaptchaData> {
    return apiGet<CaptchaData>("/api/auth/captcha");
  },

  login(payload: LoginPayload): Promise<LoginResult> {
    return apiPost<LoginResult>("/api/auth/login", payload);
  },

  logout(): Promise<void> {
    return apiPost<void>("/api/auth/logout");
  },

  getMe(): Promise<UserInfo> {
    return apiGet<UserInfo>("/api/auth/me");
  },
};
