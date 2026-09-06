import { useCallback, useRef, useState } from "react";

interface DragDropUploadProps {
  onFile: (file: File) => void;
  disabled?: boolean;
  accepted?: string;
}

export default function DragDropUpload({ onFile, disabled, accepted = ".png,.jpg,.jpeg,.pdf" }: DragDropUploadProps) {
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFiles = useCallback(
    (files: FileList | null) => {
      const file = files?.[0];
      if (file) onFile(file);
    },
    [onFile],
  );

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={() => !disabled && inputRef.current?.click()}
      onKeyDown={(e) => e.key === "Enter" && !disabled && inputRef.current?.click()}
      onDragOver={(e) => {
        e.preventDefault();
        setDragging(true);
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={(e) => {
        e.preventDefault();
        setDragging(false);
        if (!disabled) handleFiles(e.dataTransfer.files);
      }}
      className={`cursor-pointer rounded-2xl border-2 border-dashed p-12 text-center transition-colors ${
        dragging ? "border-indigo-500 bg-indigo-50" : "border-slate-300 bg-white hover:border-indigo-400"
      } ${disabled ? "pointer-events-none opacity-60" : ""}`}
    >
      <p className="text-4xl">📄</p>
      <p className="mt-3 text-sm font-medium text-slate-700">
        Glissez-déposez un document ici, ou cliquez pour parcourir
      </p>
      <p className="mt-1 text-xs text-slate-500">PNG, JPG, JPEG, PDF — 10 Mo max</p>
      <input
        ref={inputRef}
        type="file"
        accept={accepted}
        className="hidden"
        onChange={(e) => handleFiles(e.target.files)}
      />
    </div>
  );
}