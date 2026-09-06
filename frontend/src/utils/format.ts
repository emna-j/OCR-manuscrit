import type { DocumentStatus, Sentiment } from "../types";

export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} o`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} Ko`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} Mo`;
}

export function formatDate(iso: string): string {
  return new Date(iso).toLocaleString("fr-FR", { dateStyle: "short", timeStyle: "short" });
}

export function toPercent(value: number | null | undefined): string {
  if (value === null || value === undefined) return "—";
  return `${Math.round(value * 100)}%`;
}

export const sentimentMeta: Record<Sentiment, { label: string; badge: string; bar: string }> = {
  positive: { label: "Positif", badge: "bg-emerald-100 text-emerald-800", bar: "bg-emerald-500" },
  negative: { label: "Négatif", badge: "bg-rose-100 text-rose-800", bar: "bg-rose-500" },
  neutral: { label: "Neutre", badge: "bg-slate-200 text-slate-700", bar: "bg-slate-500" },
};

export function sentimentOf(value: Sentiment | null | undefined) {
  if (!value) return { label: "Inconnu", badge: "bg-slate-100 text-slate-500", bar: "bg-slate-300" };
  return sentimentMeta[value];
}

export const statusMeta: Record<DocumentStatus, { label: string; badge: string }> = {
  UPLOADED: { label: "Uploadé", badge: "bg-slate-100 text-slate-700" },
  VALIDATING: { label: "Validation", badge: "bg-amber-100 text-amber-800" },
  PREPROCESSING: { label: "Prétraitement", badge: "bg-amber-100 text-amber-800" },
  OCR_PROCESSING: { label: "Extraction OCR", badge: "bg-amber-100 text-amber-800" },
  TEXT_EXTRACTED: { label: "Texte extrait", badge: "bg-amber-100 text-amber-800" },
  ANALYZING: { label: "Analyse", badge: "bg-amber-100 text-amber-800" },
  ANALYZED: { label: "Analysé", badge: "bg-amber-100 text-amber-800" },
  COMPLETED: { label: "Terminé", badge: "bg-emerald-100 text-emerald-800" },
  REQUIRES_REVIEW: { label: "Revue requise", badge: "bg-orange-100 text-orange-800" },
  REVIEWED: { label: "Revu", badge: "bg-sky-100 text-sky-800" },
  FAILED: { label: "Échec", badge: "bg-rose-100 text-rose-800" },
};