"use client";

import { ChangeEvent, DragEvent, useRef, useState } from "react";
import { ImageIcon } from "@/components/icons";
import { api } from "@/lib/api-client";
import type { PhotoUploadError } from "@/types/api";

interface BatchUploaderProps {
  eventId: string;
  onUploaded: () => void;
  /** Photos encore autorisees par le pack de l'evenement ; null = illimite. */
  remaining?: number | null;
}

// Lots de 10 photos au plus ET de 300 Mo au plus : les photos peuvent peser
// jusqu'a 70 Mo (originaux sans compression, RAW), et nginx refuse une
// requete de plus de 500 Mo (voir nginx/nginx.conf, /api/photos/upload).
const CHUNK_SIZE = 10;
const CHUNK_MAX_BYTES = 300 * 1024 * 1024;
const MAX_FILE_BYTES = 70 * 1024 * 1024;
const ACCEPTED_TYPES = ["image/jpeg", "image/png", "image/webp"];
// RAW des boitiers : reconnus a l'extension (le navigateur ne connait pas
// leur type). Le serveur garde le RAW et en tire un JPEG pleine resolution.
const RAW_EXTENSIONS = [
  ".3fr", ".arw", ".cr2", ".cr3", ".dng", ".erf", ".iiq", ".kdc", ".mef", ".mos", ".mrw",
  ".nef", ".nrw", ".orf", ".pef", ".raf", ".raw", ".rw2", ".rwl", ".sr2", ".srf", ".srw", ".x3f",
];

function isAccepted(file: File): boolean {
  const name = file.name.toLowerCase();
  return ACCEPTED_TYPES.includes(file.type) || RAW_EXTENSIONS.some((ext) => name.endsWith(ext));
}

/** Decoupe en lots de 10 fichiers et 300 Mo au plus. */
function chunksOf(files: File[]): File[][] {
  const chunks: File[][] = [];
  let current: File[] = [];
  let bytes = 0;
  for (const file of files) {
    if (current.length > 0 && (current.length >= CHUNK_SIZE || bytes + file.size > CHUNK_MAX_BYTES)) {
      chunks.push(current);
      current = [];
      bytes = 0;
    }
    current.push(file);
    bytes += file.size;
  }
  if (current.length > 0) chunks.push(current);
  return chunks;
}

export default function BatchUploader({ eventId, onUploaded, remaining = null }: BatchUploaderProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const [progress, setProgress] = useState({ done: 0, total: 0 });
  const [errors, setErrors] = useState<PhotoUploadError[]>([]);

  async function uploadFiles(selected: File[]) {
    // Un dossier glisse-depose peut contenir d'autres fichiers (videos,
    // .xmp...) : ils sont signales, pas envoyes.
    const files = selected.filter((file) => isAccepted(file) && file.size <= MAX_FILE_BYTES);
    const skipped: PhotoUploadError[] = selected
      .filter((file) => !isAccepted(file) || file.size > MAX_FILE_BYTES)
      .map((file) => ({
        filename: file.name,
        error: isAccepted(file)
          ? "Fichier trop volumineux (70 Mo maximum)"
          : "Format non pris en charge (JPEG, PNG, WebP ou RAW)",
      }));

    if (files.length === 0) {
      setErrors(skipped);
      return;
    }

    setUploading(true);
    setErrors([]);
    setProgress({ done: 0, total: files.length });

    const allErrors: PhotoUploadError[] = [...skipped];

    let sent = 0;
    for (const chunk of chunksOf(files)) {
      try {
        const result = await api.uploadPhotos(eventId, chunk);
        allErrors.push(...result.errors);
      } catch (err) {
        chunk.forEach((file) =>
          allErrors.push({
            filename: file.name,
            error: err instanceof Error ? err.message : "Échec de l'upload",
          })
        );
      }
      sent += chunk.length;
      setProgress((p) => ({ ...p, done: Math.min(p.total, sent) }));
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
      <div className="mb-2 flex flex-wrap items-baseline justify-between gap-2">
        <p className="text-sm font-medium text-ink-700">Ajouter des photos</p>
        {remaining !== null && (
          <p className={`text-xs ${remaining === 0 ? "font-semibold text-red-600" : "text-ink-500"}`}>
            {remaining === 0
              ? "Limite du pack atteinte : passez au pack supérieur pour en ajouter"
              : `Encore ${remaining.toLocaleString("fr-FR")} photo${remaining > 1 ? "s" : ""} dans votre pack`}
          </p>
        )}
      </div>
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
          {dragOver ? "Déposez les photos ici" : "Glissez-déposez vos photos ici"}
        </p>
        <p className="text-xs text-ink-500">ou cliquez pour les choisir &middot; JPEG, PNG, WebP ou RAW &middot; 70 Mo max par photo</p>
      </div>
      <input
        ref={inputRef}
        type="file"
        multiple
        accept={[...ACCEPTED_TYPES, ...RAW_EXTENSIONS].join(",")}
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
