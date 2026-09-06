import { useMutation, useQueryClient } from "@tanstack/react-query";
import { documentsApi } from "../services/documents";
import type { ReviewRequest } from "../types";

export function useReview(documentId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: ReviewRequest) => documentsApi.review(documentId, body),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["document", documentId] });
      void queryClient.invalidateQueries({ queryKey: ["documents"] });
      void queryClient.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });
}