"use client";

import { ChangeEvent, DragEvent, useRef, useState } from "react";
import { ImageIcon } from "@/components/icons";
import { api } from "@/lib/api-client";
import { ACCEPTED_TYPES, RAW_EXTENSIONS, chunksOf, isPackLimitError, rejectionReason } from "@/lib/photo-files";
import type { PhotoUploadError } from "@/types/api";

interface BatchUploaderProps {
  eventId: string;
  onUploaded: () => void;
  /** Photos encore autorisees par le pack de l'evenement ; null = illimite. */
  remaining?: number | null;
  /** Pack plein : ouvre la proposition de pack superieur. */
  onLimitReached?: () => void;
}

const LIMIT_MESSAGE = "Limite du pack atteinte : passez au pack supérieur pour l'ajouter";

export default function BatchUploader({ eventId, onUploaded, remaining = null, onLimitReached }: BatchUploaderProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const [progress, setProgress] = useState({ done: 0, total: 0 });
  const [errors, setErrors] = useState<PhotoUploadError[]>([]);
  const full = remaining === 0;

  function openPicker() {
    if (uploading) return;
    if (full && onLimitReached) {
      onLimitReached();
      return;
    }
    inputRef.current?.click();
  }

  async function uploadFiles(selected: File[]) {
    // Un dossier glisse-depose peut contenir d'autres fichiers (videos,
    // .xmp...) : ils sont signales, pas envoyes.
    const valid = selected.filter((file) => rejectionReason(file) === null);
    const skipped: PhotoUploadError[] = selected
      .filter((file) => rejectionReason(file) !== null)
      .map((file) => ({ filename: file.name, error: rejectionReason(file) as string }));

    // Pas d'envoi inutile au-dela du pack (le serveur refuserait ces photos).
    const files = remaining === null ? valid : valid.slice(0, remaining);
    const overLimit = valid.slice(files.length);
    skipped.push(...overLimit.map((file) => ({ filename: file.name, error: LIMIT_MESSAGE })));

    if (files.length === 0) {
      setErrors(skipped.filter((e) => e.error !== LIMIT_MESSAGE));
      if (overLimit.length > 0) onLimitReached?.();
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

    // Les photos refusees pour cause de pack plein ne sont pas listees en
    // erreur : la boite « Passer au pack superieur » les explique.
    const limited = allErrors.filter((e) => e.error === LIMIT_MESSAGE || isPackLimitError(e.error));
    setErrors(allErrors.filter((e) => !limited.includes(e)));
    setUploading(false);
    if (inputRef.current) inputRef.current.value = "";
    onUploaded();
    if (limited.length > 0) onLimitReached?.();
  }

  function handleFiles(e: ChangeEvent<HTMLInputElement>) {
    uploadFiles(Array.from(e.target.files || []));
  }

  function handleDrop(e: DragEvent<HTMLDivElement>) {
    e.preventDefault();
    setDragOver(false);
    if (uploading) return;
    if (full && onLimitReached) {
      onLimitReached();
      return;
    }
    uploadFiles(Array.from(e.dataTransfer.files));
  }

  const percent = progress.total > 0 ? Math.round((progress.done / progress.total) * 100) : 0;

  return (
    <div className="glass rounded-2xl p-4">
      <div className="mb-2 flex flex-wrap items-baseline justify-between gap-2">
        <p className="text-sm font-medium text-ink-700">Ajouter des photos</p>
        {remaining !== null && !full && (
          <p className="text-xs text-ink-500">
            Encore {remaining.toLocaleString("fr-FR")} photo{remaining > 1 ? "s" : ""} dans votre pack
          </p>
        )}
        {full && (
          <button
            type="button"
            onClick={onLimitReached}
            className="rounded-full bg-[#FDE7D9] px-2.5 py-1 text-xs font-semibold text-[#9A3F06]"
          >
            Pack plein · voir les packs
          </button>
        )}
      </div>
      <div
        role="button"
        tabIndex={0}
        onClick={openPicker}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") openPicker();
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
