"use client";

import { ChangeEvent, DragEvent, useRef, useState } from "react";
import { ImageIcon } from "@/components/icons";
import { api } from "@/lib/api-client";
import type { PhotoUploadError } from "@/types/api";

interface BatchUploaderProps {
  eventId: string;
  onUploaded: () => void;
}

// Plus petit que par le passe (20) : chaque photo peut peser jusqu'a 25 Mo
// (pas de compression, qualite originale preservee), un lot de 20 pouvait
// donc friser la limite nginx et prendre plusieurs dizaines de secondes a
// traiter (thumbnail + preview + filigrane + 4 uploads R2 par photo). Des
// lots plus petits = retour visuel plus frequent et marge de securite sur
// les timeouts.
const CHUNK_SIZE = 10;
const ACCEPTED_TYPES = ["image/jpeg", "image/png", "image/webp"];

export default function BatchUploader({ eventId, onUploaded }: BatchUploaderProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const [progress, setProgress] = useState({ done: 0, total: 0 });
  const [errors, setErrors] = useState<PhotoUploadError[]>([]);

  async function uploadFiles(selected: File[]) {
    // Un dossier glisse-depose peut contenir d'autres fichiers (videos,
    // .xmp...) : ils sont signales, pas envoyes.
    const files = selected.filter((file) => ACCEPTED_TYPES.includes(file.type));
    const skipped: PhotoUploadError[] = selected
      .filter((file) => !ACCEPTED_TYPES.includes(file.type))
      .map((file) => ({ filename: file.name, error: "Format non supporte (JPEG, PNG ou WebP uniquement)" }));

    if (files.length === 0) {
      setErrors(skipped);
      return;
    }

    setUploading(true);
    setErrors([]);
    setProgress({ done: 0, total: files.length });

    const allErrors: PhotoUploadError[] = [...skipped];

    for (let i = 0; i < files.length; i += CHUNK_SIZE) {
      const chunk = files.slice(i, i + CHUNK_SIZE);
      try {
        const result = await api.uploadPhotos(eventId, chunk);
        allErrors.push(...result.errors);
      } catch (err) {
        chunk.forEach((file) =>
          allErrors.push({
            filename: file.name,
            error: err instanceof Error ? err.message : "Echec de l'upload",
          })
        );
      }
      setProgress((p) => ({ ...p, done: Math.min(p.total, i + chunk.length) }));
    }

    setErrors(allErrors);
    setUploading(false);
    if (inputRef.current) inputRef.current.value = "";
    onUploaded();
  }

  function handleFiles(e: ChangeEvent<HTMLInputElement>) {
    uploadFiles(Array.from(e.target.files || []));
  }

  function handleDrop(e: DragEvent<HTMLDivElement>) {
    e.preventDefault();
    setDragOver(false);
    if (uploading) return;
    uploadFiles(Array.from(e.dataTransfer.files));
  }

  const percent = progress.total > 0 ? Math.round((progress.done / progress.total) * 100) : 0;

  return (
    <div className="glass rounded-2xl p-4">
      <p className="mb-2 text-sm font-medium text-ink-700">Ajouter des photos</p>
      <div
        role="button"
        tabIndex={0}
        onClick={() => !uploading && inputRef.current?.click()}
        onKeyDown={(e) => {
          if ((e.key === "Enter" || e.key === " ") && !uploading) inputRef.current?.click();
        }}
        onDragOver={(e) => {
          e.preventDefault();
          if (!uploading) setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
        className={`flex cursor-pointer flex-col items-center justify-center gap-2 rounded-xl border-2 border-dashed px-4 py-8 text-center transition ${
          dragOver
            ? "border-brand-accent bg-brand-accent/10"
            : "border-ink-900/15 bg-white/40 hover:border-ink-900/30"
        } ${uploading ? "cursor-wait opacity-70" : ""}`}
      >
        <ImageIcon className="text-2xl text-ink-500" />
        <p className="text-sm font-semibold text-ink-900">
          {dragOver ? "Deposez les photos ici" : "Glissez-deposez vos photos ici"}
        </p>
        <p className="text-xs text-ink-500">ou cliquez pour les choisir &middot; JPEG, PNG, WebP &middot; 25 Mo max par photo</p>
      </div>
      <input
        ref={inputRef}
        type="file"
        multiple
        accept={ACCEPTED_TYPES.join(",")}
        onChange={handleFiles}
        disabled={uploading}
        className="hidden"
      />

      {uploading && (
        <div className="mt-3">
          <div className="mb-1 flex justify-between text-xs text-ink-500">
            <span>Upload en cours...</span>
            <span>
              {progress.done}/{progress.total}
            </span>
          </div>
          <div className="h-1.5 w-full overflow-hidden rounded-full bg-ink-900/10">
            <div
              className="h-full rounded-full bg-brand-accent transition-[width] duration-300"
              style={{ width: `${percent}%` }}
            />
          </div>
        </div>
      )}

      {errors.length > 0 && (
        <div className="mt-3 rounded-lg bg-red-50 p-3 text-sm text-red-700">
          <p className="mb-1 font-medium">{errors.length} fichier(s) rejete(s) :</p>
          <ul className="list-disc pl-5">
            {errors.map((err, i) => (
              <li key={`${err.filename}-${i}`}>
                {err.filename}, {err.error}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
