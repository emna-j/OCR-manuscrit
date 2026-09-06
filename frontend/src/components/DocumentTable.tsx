import { Link } from "react-router-dom";
import type { DocumentItem } from "../types";
import { formatBytes, formatDate } from "../utils/format";
import StatusBadge from "./StatusBadge";

export default function DocumentTable({ documents }: { documents: DocumentItem[] }) {
  if (documents.length === 0) {
    return <p className="py-10 text-center text-sm text-slate-500">Aucun document.</p>;
  }

  return (
    <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
      <table className="min-w-full divide-y divide-slate-200 text-sm">
        <thead className="bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500">
          <tr>
            <th className="px-4 py-3 font-medium">Document</th>
            <th className="px-4 py-3 font-medium">Type</th>
            <th className="px-4 py-3 font-medium">Taille</th>
            <th className="px-4 py-3 font-medium">Statut</th>
            <th className="px-4 py-3 font-medium">Date</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {documents.map((doc) => (
            <tr key={doc.id} className="hover:bg-slate-50">
              <td className="px-4 py-3">
                <Link to={`/documents/${doc.id}`} className="font-medium text-indigo-700 hover:underline">
                  {doc.original_filename}
                </Link>
              </td>
              <td className="px-4 py-3 text-slate-600">{doc.content_type}</td>
              <td className="px-4 py-3 text-slate-600">{formatBytes(doc.file_size_bytes)}</td>
              <td className="px-4 py-3">
                <StatusBadge status={doc.status} />
              </td>
              <td className="px-4 py-3 text-slate-600">{formatDate(doc.created_at)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}