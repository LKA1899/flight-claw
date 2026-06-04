import { apiDelete, apiGet, apiPost, apiPut } from "@/lib/api";
import type { ListParams, PageResult } from "@/types/common";
import type { Monitor, MonitorDate, MonitorPayload, MonitorSchedulePayload, PositioningCity, PositioningPayload, TransferCity, TransferPayload } from "@/types/monitor";

export const monitorApi = {
  list: (params: ListParams) => apiGet<PageResult<Monitor>>("/api/monitors", params),
  get: (id: string | number) => apiGet<Monitor>(`/api/monitors/${id}`),
  create: (payload: MonitorPayload) => apiPost<Monitor>("/api/monitors", payload),
  update: (id: string | number, payload: MonitorPayload) => apiPut<Monitor>(`/api/monitors/${id}`, payload),
  remove: (id: string | number) => apiDelete<{ deleted: boolean }>(`/api/monitors/${id}`),
  toggle: (id: string | number) => apiPost<Monitor>(`/api/monitors/${id}/toggle`),
  scanNow: (id: string | number) => apiPost<{ scan_id: number; scan_no: string }>(`/api/monitors/${id}/scan-now`),
  cancelRunningScan: (id: string | number) => apiPost(`/api/monitors/${id}/cancel-running-scan`),
  getSchedule: (id: string | number) => apiGet<MonitorSchedulePayload & { next_scan_time?: string | null; last_scan_time?: string | null; last_scan_status?: string | null }>(`/api/monitors/${id}/schedule`),
  updateSchedule: (id: string | number, payload: MonitorSchedulePayload) => apiPut<Monitor>(`/api/monitors/${id}/schedule`, payload),
  toggleSchedule: (id: string | number) => apiPost<Monitor>(`/api/monitors/${id}/schedule/toggle`),
  dates: (id: string | number, params: ListParams) => apiGet<PageResult<MonitorDate>>(`/api/monitors/${id}/dates`, params),
  addDate: (id: string | number, payload: { depart_date: string; return_date?: string; remark?: string }) => apiPost(`/api/monitors/${id}/dates`, payload),
  batchDates: (id: string | number, payload: { start_date: string; end_date: string; return_start_date?: string; return_end_date?: string; weekdays: number[] }) => apiPost(`/api/monitors/${id}/dates/batch`, payload),
  toggleDate: (dateId: string | number) => apiPut(`/api/monitor-dates/${dateId}/toggle`),
  removeDate: (dateId: string | number) => apiDelete(`/api/monitor-dates/${dateId}`),
  positionings: (id: string | number) => apiGet<PositioningCity[]>(`/api/monitors/${id}/positionings`),
  createPositioning: (id: string | number, payload: PositioningPayload) => apiPost<PositioningCity>(`/api/monitors/${id}/positionings`, payload),
  updatePositioning: (id: string | number, payload: PositioningPayload) => apiPut<PositioningCity>(`/api/positionings/${id}`, payload),
  togglePositioning: (id: string | number) => apiPut(`/api/positionings/${id}/toggle`),
  removePositioning: (id: string | number) => apiDelete(`/api/positionings/${id}`),
  transfers: (id: string | number) => apiGet<TransferCity[]>(`/api/monitors/${id}/transfers`),
  createTransfer: (id: string | number, payload: TransferPayload) => apiPost<TransferCity>(`/api/monitors/${id}/transfers`, payload),
  updateTransfer: (id: string | number, payload: TransferPayload) => apiPut<TransferCity>(`/api/transfers/${id}`, payload),
  toggleTransfer: (id: string | number) => apiPut(`/api/transfers/${id}/toggle`),
  removeTransfer: (id: string | number) => apiDelete(`/api/transfers/${id}`),
};
