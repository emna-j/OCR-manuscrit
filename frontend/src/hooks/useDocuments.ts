import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { documentsApi } from "../services/documents";
import type { DocumentStatus } from "../types";

export function useDocuments(status?: DocumentStatus) {
  return useQuery({
    queryKey: ["documents", status ?? "all"],
    queryFn: () => documentsApi.list(status),
  });
}

export function useDocument(id: string) {
  return useQuery({
    queryKey: ["document", id],
    queryFn: () => documentsApi.get(id),
    enabled: Boolean(id),
  });
}

export function useUpload() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (file: File) => documentsApi.upload(file),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["documents"] });
      void queryClient.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });
}

export function useAnalyze() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, force }: { id: string; force?: boolean }) => documentsApi.analyze(id, force),
    onSuccess: (_data, { id }) => {
      void queryClient.invalidateQueries({ queryKey: ["document", id] });
      void queryClient.invalidateQueries({ queryKey: ["documents"] });
      void queryClient.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });
}

export function useDeleteDocument() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => documentsApi.delete(id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["documents"] });
      void queryClient.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });
}