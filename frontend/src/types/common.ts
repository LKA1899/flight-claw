export type Status = "PENDING" | "QUEUED" | "RUNNING" | "SUCCESS" | "FAILED" | "PARTIAL_SUCCESS" | "SKIPPED" | "CANCEL_REQUESTED" | "CANCELLED" | "ENABLED" | "DISABLED";

export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  message?: string;
  detail?: string;
}

export interface PageResult<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface ListParams {
  page?: number;
  page_size?: number;
  keyword?: string;
  [key: string]: string | number | boolean | undefined;
}
