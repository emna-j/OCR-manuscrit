import { useState } from "react";
import DocumentTable from "../components/DocumentTable";
import Spinner from "../components/Spinner";
import { useDocuments } from "../hooks/useDocuments";
import type { DocumentStatus } from "../types";

const filters: { label: string; value: DocumentStatus | undefined }[] = [
  { label: "Tous", value: undefined },
  { label: "Terminés", value: "COMPLETED" },
  { label: "Revue requise", value: "REQUIRES_REVIEW" },
  { label: "Revus", value: "REVIEWED" },
  { label: "Échecs", value: "FAILED" },
];

export default function DocumentsPage() {
  const [filter, setFilter] = useState<DocumentStatus | undefined>(undefined);
  const { data, isLoading, isError, refetch } = useDocuments(filter);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">Documents</h1>
        <p className="text-sm text-slate-500">Tous les documents soumis à la plateforme.</p>
      </div>

      <div className="flex flex-wrap gap-2">
        {filters.map((f) => (
          <button
            key={f.label}
            onClick={() => setFilter(f.value)}
            className={`rounded-full px-3 py-1.5 text-xs font-medium transition-colors ${
              filter === f.value ? "bg-indigo-600 text-white" : "bg-white text-slate-600 hover:bg-slate-200"
            }`}
          >
            {f.label}
          </button>
        ))}
      </div>

      {isLoading ? (
        <Spinner />
      ) : isError ? (
        <div className="rounded-xl border border-rose-200 bg-rose-50 p-6 text-rose-700">
          <p className="font-medium">Impossible de charger les documents.</p>
          <button onClick={() => void refetch()} className="mt-3 text-sm font-medium underline">
            Réessayer
          </button>
        </div>
      ) : (
        <DocumentTable documents={data?.items ?? []} />
      )}
    </div>
  );
}