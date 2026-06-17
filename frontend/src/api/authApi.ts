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
  token_type: string;
  expires_in: number;
  user: UserInfo;
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
