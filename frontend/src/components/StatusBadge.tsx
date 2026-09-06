import type { DocumentStatus } from "../types";
import { statusMeta } from "../utils/format";

export default function StatusBadge({ status }: { status: DocumentStatus }) {
  const meta = statusMeta[status];
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${meta.badge}`}>
      {meta.label}
    </span>
  );
}