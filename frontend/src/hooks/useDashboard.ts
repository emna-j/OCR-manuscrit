import { useQuery } from "@tanstack/react-query";
import { documentsApi } from "../services/documents";

export function useDashboard() {
  return useQuery({
    queryKey: ["dashboard"],
    queryFn: documentsApi.dashboard,
  });
}