import { Link } from "react-router-dom";
import ConfidenceBar from "../components/ConfidenceBar";
import SentimentBadge from "../components/SentimentBadge";
import Spinner from "../components/Spinner";
import StatCard from "../components/StatCard";
import StatusBadge from "../components/StatusBadge";
import { useDashboard } from "../hooks/useDashboard";
import { formatDate, toPercent } from "../utils/format";

export default function DashboardPage() {
  const { data, isLoading, isError, refetch } = useDashboard();

  if (isLoading) return <Spinner label="Chargement du dashboard…" />;
  if (isError || !data) {
    return (
      <div className="rounded-xl border border-rose-200 bg-rose-50 p-6 text-rose-700">
        <p className="font-medium">Impossible de charger les statistiques.</p>
        <button onClick={() => void refetch()} className="mt-3 text-sm font-medium underline">
          Réessayer
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">Dashboard</h1>
        <p className="text-sm text-slate-500">Vue d'ensemble de l'analyse des documents manuscrits.</p>
      </div>

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatCard label="Documents analysés" value={data.total_documents} />
        <StatCard label="Positifs" value={data.positive_count} accent="bg-emerald-50" />
        <StatCard label="Négatifs" value={data.negative_count} accent="bg-rose-50" />
        <StatCard label="Revue requise" value={data.requires_review_count} accent="bg-orange-50" />
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <h2 className="text-sm font-medium text-slate-900">Confiance moyenne</h2>
          <div className="mt-3 space-y-4">
            <div>
              <div className="mb-1 flex justify-between text-xs text-slate-500">
                <span>OCR</span>
                <span>{toPercent(data.average_ocr_confidence)}</span>
              </div>
              <ConfidenceBar value={data.average_ocr_confidence} />
            </div>
            <div>
              <div className="mb-1 flex justify-between text-xs text-slate-500">
                <span>Analyse</span>
                <span>{toPercent(data.average_analysis_confidence)}</span>
              </div>
              <ConfidenceBar value={data.average_analysis_confidence} color="bg-emerald-500" />
            </div>
          </div>
        </div>

        <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <h2 className="text-sm font-medium text-slate-900">Répartition des sentiments</h2>
          <div className="mt-4 grid grid-cols-3 gap-2 text-center">
            <div className="rounded-lg bg-emerald-50 p-3">
              <p className="text-2xl font-semibold text-emerald-700">{data.positive_count}</p>
              <p className="text-xs text-emerald-600">Positif</p>
            </div>
            <div className="rounded-lg bg-rose-50 p-3">
              <p className="text-2xl font-semibold text-rose-700">{data.negative_count}</p>
              <p className="text-xs text-rose-600">Négatif</p>
            </div>
            <div className="rounded-lg bg-slate-100 p-3">
              <p className="text-2xl font-semibold text-slate-700">{data.neutral_count}</p>
              <p className="text-xs text-slate-500">Neutre</p>
            </div>
          </div>
        </div>
      </div>

      <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-sm font-medium text-slate-900">Derniers documents</h2>
          <Link to="/documents" className="text-sm font-medium text-indigo-700 hover:underline">
            Tout voir
          </Link>
        </div>
        {data.recent_documents.length === 0 ? (
          <p className="py-6 text-center text-sm text-slate-500">
            Aucun document pour le moment.{" "}
            <Link to="/upload" className="text-indigo-700 hover:underline">
              En uploader un
            </Link>
            .
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-100 text-sm">
              <tbody className="divide-y divide-slate-100">
                {data.recent_documents.map((doc) => (
                  <tr key={doc.id}>
                    <td className="py-3">
                      <Link to={`/documents/${doc.id}`} className="font-medium text-indigo-700 hover:underline">
                        {doc.original_filename}
                      </Link>
                      <p className="text-xs text-slate-500">{formatDate(doc.created_at)}</p>
                    </td>
                    <td className="py-3">
                      <SentimentBadge sentiment={doc.sentiment} />
                    </td>
                    <td className="py-3 text-slate-600">{toPercent(doc.ocr_confidence)}</td>
                    <td className="py-3">
                      <StatusBadge status={doc.status} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}