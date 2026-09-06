import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import DragDropUpload from "../components/DragDropUpload";
import { useUpload } from "../hooks/useDocuments";
import { useAuth } from "../hooks/useAuth";
import { formatBytes } from "../utils/format";

export default function UploadPage() {
  const upload = useUpload();
  const { isStaff } = useAuth();
  const navigate = useNavigate();
  const [selected, setSelected] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleFile = (file: File) => {
    setSelected(file);
    setError(null);
  };

  const handleUpload = async () => {
    if (!selected) return;
    setError(null);
    try {
      const document = await upload.mutateAsync(selected);
      navigate(`/documents/${document.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Échec de l'upload");
    }
  };

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">Upload d'un document</h1>
        <p className="text-sm text-slate-500">
          Déposez une image ou un PDF contenant du texte manuscrit. Le fichier est validé puis analysé par Gemini.
        </p>
      </div>

      <DragDropUpload onFile={handleFile} disabled={upload.isPending} />

      {selected && (
        <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <div className="flex items-center justify-between">
            <div>
              <p className="font-medium text-slate-900">{selected.name}</p>
              <p className="text-sm text-slate-500">
                {formatBytes(selected.size)} · {selected.type || "inconnu"}
              </p>
            </div>
            <button
              onClick={() => setSelected(null)}
              className="text-sm text-slate-500 hover:text-slate-700"
              disabled={upload.isPending}
            >
              Retirer
            </button>
          </div>

          {error && (
            <p className="mt-3 rounded-lg bg-rose-50 px-3 py-2 text-sm text-rose-700" role="alert">
              {error}
            </p>
          )}

          <div className="mt-4 flex items-center gap-3">
            <button
              onClick={() => void handleUpload()}
              disabled={upload.isPending}
              className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-indigo-700 disabled:opacity-60"
            >
              {upload.isPending ? "Envoi en cours…" : "Uploader"}
            </button>
            {isStaff && (
              <Link to="/documents" className="text-sm font-medium text-slate-600 hover:text-slate-800">
                Annuler
              </Link>
            )}
          </div>
        </div>
      )}

      {!isStaff && (
        <p className="rounded-lg bg-amber-50 px-3 py-2 text-sm text-amber-800">
          Vous êtes en rôle USER : l'analyse automatique est réservée aux analystes. Vous pouvez uploader un document,
          mais son analyse devra être déclenchée par un analyste.
        </p>
      )}
    </div>
  );
}