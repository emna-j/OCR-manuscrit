import type { ReactNode } from "react";

interface StatCardProps {
  label: string;
  value: ReactNode;
  accent?: string;
}

export default function StatCard({ label, value, accent = "bg-white" }: StatCardProps) {
  return (
    <div className={`rounded-xl border border-slate-200 p-5 shadow-sm ${accent}`}>
      <p className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</p>
      <p className="mt-2 text-3xl font-semibold text-slate-900">{value}</p>
    </div>
  );
}