import { api } from "./api";
import type {
  Analysis,
  DashboardStatistics,
  DocumentDetail,
  DocumentItem,
  DocumentListResponse,
  DocumentStatus,
  ReviewRequest,
} from "../types";

export const documentsApi = {
  list: (status?: DocumentStatus) =>
    api.get<DocumentListResponse>(`/documents${status ? `?status_filter=${status}` : ""}`),
  get: (id: string) => api.get<DocumentDetail>(`/documents/${id}`),
  upload: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return api.postForm<DocumentItem>("/documents/upload", form);
  },
  analyze: (id: string, force?: boolean) =>
    api.post<Analysis>(`/documents/${id}/analyze${force ? "?force=1" : ""}`),
  analysis: (id: string) => api.get<Analysis>(`/documents/${id}/analysis`),
  review: (id: string, body: ReviewRequest) => api.post(`/documents/${id}/review`, body),
  delete: (id: string) => api.delete(`/documents/${id}`),
  dashboard: () => api.get<DashboardStatistics>("/dashboard/statistics"),
};