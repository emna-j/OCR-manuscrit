import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import ConfidenceBar from "../components/ConfidenceBar";
import SentimentBadge from "../components/SentimentBadge";
import Spinner from "../components/Spinner";
import StatusBadge from "../components/StatusBadge";
import { useAuth } from "../hooks/useAuth";
import { useAnalyze, useDeleteDocument, useDocument } from "../hooks/useDocuments";
import { useReview } from "../hooks/useReview";
import { getToken } from "../services/api";
import type { Sentiment } from "../types";
import { formatBytes, formatDate, toPercent } from "../utils/format";

function useFileUrl(documentId: string, enabled: boolean) {
  const [url, setUrl] = useState<string | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    if (!enabled || !documentId) return;
    let objectUrl: string | null = null;
    let cancelled = false;

    fetch(`/api/documents/${documentId}/file`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
      .then((response) => {
        if (!response.ok) throw new Error("file error");
        return response.blob();
      })
      .then((blob) => {
        if (!cancelled) {
          objectUrl = URL.createObjectURL(blob);
          setUrl(objectUrl);
        }
      })
      .catch(() => !cancelled && setError(true));

    return () => {
      cancelled = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [documentId, enabled]);

  return { url, error };
}

export default function DocumentDetailPage() {
  const { id = "" } = useParams();
  const navigate = useNavigate();
  const { user, isStaff } = useAuth();
  const { data: document, isLoading, isError, refetch } = useDocument(id);
  const analyze = useAnalyze();
  const review = useReview(id);
  const remove = useDeleteDocument();

  const canReview = user !== null && ["ADMIN", "REVIEWER"].includes(user.role);
  const canAnalyze = user !== null && ["ADMIN", "ANALYST"].includes(user.role);

  const [correctedText, setCorrectedText] = useState("");
  const [correctedSentiment, setCorrectedSentiment] = useState<Sentiment | "">("");
  const [correctedCategory, setCorrectedCategory] = useState("");
  const [comment, setComment] = useState("");
  const [reviewError, setReviewError] = useState<string | null>(null);

  const { url: fileUrl, error: fileError } = useFileUrl(id, Boolean(document));

  // Pré-remplit le formulaire de revue avec le résultat actuel.
  useEffect(() => {
    if (document?.analysis) {
      setCorrectedText(document.analysis.extracted_text ?? "");
      setCorrectedSentiment(document.analysis.sentiment ?? "");
      setCorrectedCategory(document.analysis.category ?? "");
    }
  }, [document?.analysis]);

  if (isLoading) return <Spinner />;
  if (isError || !document) {
    return (
      <div className="rounded-xl border border-rose-200 bg-rose-50 p-6 text-rose-700">
        <p className="font-medium">Document introuvable ou accès refusé.</p>
        <button onClick={() => void refetch()} className="mt-3 text-sm font-medium underline">
          Réessayer
        </button>
      </div>
    );
  }

  const analysis = document.analysis;
  const isAnalyzing = ["PREPROCESSING", "OCR_PROCESSING", "TEXT_EXTRACTED", "ANALYZING", "ANALYZED"].includes(
    document.status,
  );
  const needsReview = document.status === "REQUIRES_REVIEW";

  const handleReview = async (decision: "VALIDATED" | "REJECTED") => {
    setReviewError(null);
    try {
      await review.mutateAsync({
        corrected_text: correctedText || undefined,
        corrected_sentiment: correctedSentiment === "" ? undefined : correctedSentiment,
        corrected_category: correctedCategory || undefined,
        comment: comment || undefined,
        decision,
      });
      setComment("");
    } catch (err) {
      setReviewError(err instanceof Error ? err.message : "Échec de la revue");
    }
  };

  const handleDelete = async () => {
    if (!window.confirm("Supprimer définitivement ce document et son analyse ?")) return;
    try {
      await remove.mutateAsync(document.id);
      navigate("/documents");
    } catch {
      // silencieux : l'utilisateur reste sur la page
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-semibold text-slate-900">{document.original_filename}</h1>
            <StatusBadge status={document.status} />
          </div>
          <p className="mt-1 text-sm text-slate-500">
            {document.content_type} · {formatBytes(document.file_size_bytes)} · {formatDate(document.created_at)}
          </p>
          {document.error_reason && (
            <p className="mt-2 text-sm text-rose-600">Motif : {document.error_reason}</p>
          )}
        </div>
        <div className="flex items-center gap-2">
          {canAnalyze && (
            <button
              onClick={() => analyze.mutate({ id: document.id, force: Boolean(analysis) })}
              disabled={analyze.isPending || isAnalyzing}
              className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-indigo-700 disabled:opacity-60"
            >
              {analyze.isPending || isAnalyzing ? "Analyse en cours…" : analysis ? "Ré-analyser" : "Analyser"}
            </button>
          )}
          {analyze.isError && (
            <p className="rounded-lg bg-rose-50 px-3 py-2 text-sm text-rose-700" role="alert">
              L'analyse a échoué : {analyze.error instanceof Error ? analyze.error.message : "erreur inconnue"}
            </p>
          )}
          {(user?.role === "ADMIN" || document.owner_id === user?.id) && (
            <button
              onClick={() => void handleDelete()}
              disabled={remove.isPending}
              className="rounded-lg border border-rose-300 px-4 py-2 text-sm font-medium text-rose-700 transition-colors hover:bg-rose-50 disabled:opacity-60"
            >
              Supprimer
            </button>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Image originale */}
        <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <h2 className="mb-3 text-sm font-medium text-slate-900">Document original</h2>
          {fileError ? (
            <p className="text-sm text-slate-500">Impossible de charger le fichier.</p>
          ) : fileUrl ? (
            <img src={fileUrl} alt="Document original" className="max-h-96 w-full rounded-lg border object-contain" />
          ) : (
            <div className="flex h-48 items-center justify-center text-slate-400">Chargement du fichier…</div>
          )}
        </div>

        {/* Résultats d'analyse */}
        <div className="space-y-6">
          {!analysis ? (
            <div className="rounded-xl border border-slate-200 bg-white p-5 text-sm text-slate-500 shadow-sm">
              {isAnalyzing
                ? "Le document est en cours de traitement…"
                : "Ce document n'a pas encore été analysé."}
            </div>
          ) : (
            <>
              <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
                <h2 className="mb-3 text-sm font-medium text-slate-900">Texte extrait</h2>
                <p className="whitespace-pre-wrap text-sm text-slate-700">
                  {analysis.extracted_text || "—"}
                </p>
              </div>

              <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
                <div className="flex items-center justify-between">
                  <h2 className="text-sm font-medium text-slate-900">Sentiment</h2>
                  <SentimentBadge sentiment={analysis.sentiment} />
                </div>
                <p className="mt-1 text-xs text-slate-500">
                  Confiance : {toPercent(analysis.sentiment_confidence)}
                </p>

                {(analysis.emotions ?? []).length > 0 && (
                  <div className="mt-4">
                    <h3 className="text-xs font-medium uppercase tracking-wide text-slate-500">Émotions</h3>
                    <div className="mt-2 space-y-2">
                      {analysis.emotions.map((emotion, index) => (
                        <div key={index} className="flex items-center justify-between text-sm">
                          <span className="capitalize text-slate-700">{emotion.label}</span>
                          <ConfidenceBar value={emotion.confidence} color="bg-violet-500" />
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {analysis.category && (
                  <p className="mt-4 text-sm text-slate-700">
                    <span className="font-medium">Catégorie :</span> {analysis.category}
                  </p>
                )}
                {(analysis.keywords ?? []).length > 0 && (
                  <div className="mt-2 flex flex-wrap gap-2">
                    {analysis.keywords.map((keyword) => (
                      <span key={keyword} className="rounded-full bg-slate-100 px-2.5 py-0.5 text-xs text-slate-600">
                        {keyword}
                      </span>
                    ))}
                  </div>
                )}
                {analysis.summary && (
                  <p className="mt-4 border-t border-slate-100 pt-3 text-sm text-slate-600">{analysis.summary}</p>
                )}
              </div>

              <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
                <h2 className="mb-3 text-sm font-medium text-slate-900">Confiances</h2>
                <div className="space-y-3">
                  <div>
                    <div className="mb-1 flex justify-between text-xs text-slate-500">
                      <span>Confiance OCR</span>
                      <span>{toPercent(analysis.ocr_confidence)}</span>
                    </div>
                    <ConfidenceBar value={analysis.ocr_confidence} />
                  </div>
                  <div>
                    <div className="mb-1 flex justify-between text-xs text-slate-500">
                      <span>Confiance analyse</span>
                      <span>{toPercent(analysis.analysis_confidence)}</span>
                    </div>
                    <ConfidenceBar value={analysis.analysis_confidence} color="bg-emerald-500" />
                  </div>
                </div>
                {needsReview && (
                  <p className="mt-4 rounded-lg bg-orange-50 px-3 py-2 text-sm text-orange-800">
                    Ce document nécessite une validation humaine (confiance insuffisante).
                  </p>
                )}
              </div>

              {(analysis.pii_detections ?? []).length > 0 && (
                <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
                  <h2 className="mb-3 text-sm font-medium text-slate-900">PII détectées</h2>
                  <div className="space-y-2">
                    {analysis.pii_detections.map((pii) => (
                      <div key={pii.id} className="flex items-center justify-between rounded-lg bg-slate-50 px-3 py-2 text-sm">
                        <span className="font-medium text-slate-700">{pii.pii_type}</span>
                        <span className="text-slate-500">{pii.value}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}

          {document.latest_review && (
            <div className="rounded-xl border border-sky-200 bg-sky-50 p-5">
              <h2 className="text-sm font-medium text-sky-900">Dernière revue</h2>
              <p className="mt-1 text-sm text-sky-800">
                {document.latest_review.decision === "VALIDATED" ? "Validé" : "Rejeté"}
                {document.latest_review.comment ? ` — ${document.latest_review.comment}` : ""}
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Panneau de revue humaine */}
      {canReview && analysis && (
        <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="text-sm font-medium text-slate-900">Revue humaine</h2>
          <p className="mt-1 text-xs text-slate-500">
            Corrigez la transcription, ajustez le sentiment ou la catégorie, puis validez ou rejetez le document.
          </p>

          <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-2">
            <div className="space-y-4">
              <div>
                <label className="block text-xs font-medium uppercase tracking-wide text-slate-500">
                  Texte corrigé
                </label>
                <textarea
                  value={correctedText}
                  onChange={(e) => setCorrectedText(e.target.value)}
                  rows={5}
                  className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                />
              </div>
              <div>
                <label className="block text-xs font-medium uppercase tracking-wide text-slate-500">
                  Sentiment corrigé
                </label>
                <select
                  value={correctedSentiment}
                  onChange={(e) => setCorrectedSentiment(e.target.value as Sentiment | "")}
                  className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none"
                >
                  <option value="">—</option>
                  <option value="positive">Positif</option>
                  <option value="negative">Négatif</option>
                  <option value="neutral">Neutre</option>
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium uppercase tracking-wide text-slate-500">
                  Catégorie corrigée
                </label>
                <input
                  value={correctedCategory}
                  onChange={(e) => setCorrectedCategory(e.target.value)}
                  className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none"
                />
              </div>
            </div>
            <div className="space-y-4">
              <div>
                <label className="block text-xs font-medium uppercase tracking-wide text-slate-500">Commentaire</label>
                <textarea
                  value={comment}
                  onChange={(e) => setComment(e.target.value)}
                  rows={5}
                  placeholder="Ex. : transcription corrigée, erreur de saisie…"
                  className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none"
                />
              </div>
              <div className="flex flex-wrap gap-3 pt-2">
                <button
                  onClick={() => void handleReview("VALIDATED")}
                  disabled={review.isPending}
                  className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-emerald-700 disabled:opacity-60"
                >
                  Valider
                </button>
                <button
                  onClick={() => void handleReview("REJECTED")}
                  disabled={review.isPending}
                  className="rounded-lg border border-rose-300 px-4 py-2 text-sm font-medium text-rose-700 transition-colors hover:bg-rose-50 disabled:opacity-60"
                >
                  Rejeter
                </button>
              </div>
              {reviewError && (
                <p className="rounded-lg bg-rose-50 px-3 py-2 text-sm text-rose-700" role="alert">
                  {reviewError}
                </p>
              )}
              {review.isSuccess && (
                <p className="rounded-lg bg-emerald-50 px-3 py-2 text-sm text-emerald-700">
                  Revue enregistrée.
                </p>
              )}
            </div>
          </div>
        </div>
      )}

      {!isStaff && (
        <p className="text-xs text-slate-500">Vous consultez ce document en lecture seule (rôle USER).</p>
      )}
    </div>
  );
}