import type { Sentiment } from "../types";
import { sentimentOf } from "../utils/format";

export default function SentimentBadge({ sentiment }: { sentiment: Sentiment | null | undefined }) {
  const meta = sentimentOf(sentiment);
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${meta.badge}`}>
      {meta.label}
    </span>
  );
}