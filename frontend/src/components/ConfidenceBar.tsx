import { toPercent } from "../utils/format";

export default function ConfidenceBar({ value, color = "bg-indigo-500" }: { value: number | null | undefined; color?: string }) {
  const percent = value === null || value === undefined ? 0 : Math.min(100, Math.round(value * 100));
  return (
    <div className="flex items-center gap-2">
      <div className="h-2 flex-1 overflow-hidden rounded-full bg-slate-200">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${percent}%` }} />
      </div>
      <span className="w-10 text-right text-xs font-medium text-slate-600">{toPercent(value)}</span>
    </div>
  );
}